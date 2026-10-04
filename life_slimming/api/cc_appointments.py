"""Staff-specific CC scheduling. All times use the site's configured timezone."""
import re
from datetime import datetime, timedelta, time

import frappe
from frappe.utils import get_datetime, getdate, now_datetime
from life_slimming.portal_access import require_module
from life_slimming.api.convox import MANAGERS


def authorize():
    if not frappe.session.user or frappe.session.user == 'Guest':
        raise frappe.AuthenticationError('Sign in to schedule appointments.')
    require_module('leads')


def is_manager():
    return bool(MANAGERS.intersection(frappe.get_roles())) or frappe.session.user == 'Administrator'


def lead_access(name):
    doc = frappe.get_doc('Lead', name)
    if doc.lead_owner != frappe.session.user and not is_manager():
        raise frappe.PermissionError('You can book only leads assigned to you.')
    return doc


def branch_access(branch):
    names = frappe.get_list('Branch', pluck='name', limit_page_length=0)
    if branch not in names:
        raise frappe.PermissionError('This branch is not available to your account.')


def user_name(user):
    return (frappe.get_cached_value('User', user, 'full_name') or user) if user else ''


def role_group(designation):
    text = re.sub(r'[^a-z0-9]+', ' ', (designation or '').lower()).strip()
    text = re.sub(r'\s+', ' ', text).replace('centre', 'center')
    if text in {'area manager', 'area manager trainee', 'trainee area manager'}:
        return 'Area Manager'
    if text in {'manager', 'center manager', 'branch manager', 'assistant center manager',
                'trainee assistant center manager', 'trainee center manager',
                'senior manager', 'senior center manager', 'results manager',
                'cm', 'acm', 'tacm', 'tcm'}:
        return 'Manager'
    if text in {'doctor', 'consultant doctor', 'consulting doctor', 'resident doctor',
                'senior doctor', 'physician', 'dermatologist', 'consultant dermatologist'}:
        return 'Doctor'
    if text in {'dietician', 'dietitian', 'sr dietician', 'sr dietitian',
                'senior dietician', 'senior dietitian', 'consultant dietician',
                'consultant dietitian', 'nutritionist', 'clinical nutritionist'}:
        return 'Dietitian'
    return ''


def mapped_branches(doctype, name, primary, table_field, extra=''):
    branches = {primary} if primary else set()
    meta = frappe.get_meta(doctype)
    field = meta.get_field(table_field)
    if field and field.fieldtype == 'Table' and frappe.get_meta(field.options).has_field('branch'):
        cache = getattr(frappe.local, '_cc_branch_maps', None)
        if cache is None:
            cache = {}; frappe.local._cc_branch_maps = cache
        key = (doctype, table_field)
        if key not in cache:
            mapping = {}
            for row in frappe.get_all(field.options, filters={'parenttype': doctype, 'parentfield': table_field}, fields=['parent', 'branch'], limit_page_length=0):
                mapping.setdefault(row.parent, set()).add(row.branch)
            cache[key] = mapping
        branches.update(cache[key].get(name, set()))
    branches.update(x.strip() for x in re.split(r'[,\n;]', extra or '') if x.strip())
    return branches


def staff_for(branch):
    """Expose only scheduling identity, not HR records, to authorized CC users."""
    employee_fields = ['name', 'employee_name', 'designation', 'branch']
    if frappe.get_meta('Employee').has_field('custom_branch_list'):
        employee_fields.append('custom_branch_list')
    employees = frappe.get_all('Employee', filters={'status': 'Active'}, fields=employee_fields, limit_page_length=0)
    branch_employees = {e.name for e in employees if branch in mapped_branches(
        'Employee', e.name, e.branch, 'custom_employee_branches', e.get('custom_branch_list'))}
    result = {}
    for e in employees:
        group = role_group(e.designation)
        if group and e.name in branch_employees:
            result['Employee:' + e.name] = dict(id='Employee:' + e.name, name=e.employee_name, role=group, designation=e.designation, employee=e.name, practitioner='', practitioners=[])
    if frappe.db.exists('DocType', 'Healthcare Practitioner'):
        meta = frappe.get_meta('Healthcare Practitioner')
        if meta.has_field('employee'):
            for p in frappe.get_all('Healthcare Practitioner', filters={'status': 'Active'}, fields=['name', 'employee'], limit_page_length=0):
                # Practitioner links supply conflict identities, never employee eligibility.
                selected = result.get('Employee:' + (p.get('employee') or ''))
                if selected:
                    selected['practitioners'].append(p.name)
                    selected['practitioner'] = p.name
    return sorted(result.values(), key=lambda x: (x['role'], x['name']))


def interval(start, duration, current=None):
    try:
        duration = int(duration)
        start = get_datetime(start)
    except (ValueError, TypeError):
        raise frappe.ValidationError('Choose a valid appointment date, time and duration.')
    if duration not in (45, 60):
        raise frappe.ValidationError('Choose a 45-minute or 60-minute session. Minimum duration is 45 minutes.')
    end = start + timedelta(minutes=duration)
    if start < (current or now_datetime()):
        raise frappe.ValidationError('This time slot has already passed. Choose a future slot.')
    if start.minute % 15 or start.second or start.microsecond:
        raise frappe.ValidationError('Appointments must start on a 15-minute boundary.')
    if start.time() < time(10) or end.date() != start.date() or end.time() > time(20):
        raise frappe.ValidationError('The complete session must fit between 10:00 AM and 8:00 PM.')
    return start, end


def overlaps(start, end, other_start, other_end):
    return start < other_end and end > other_start


def resource_appointments(resource, day, practitioner='', lock=False):
    # No branch filter: the same employee cannot be booked in two branches at once.
    sql = """SELECT name, scheduled_time, appointment_time, duration, customer_name,
        party, lead_owner, branch, custom_cc_resource, custom_cc_staff_name,
        custom_cc_staff_role FROM `tabAppointment`
        WHERE status != 'Closed' AND scheduled_time >= %(day)s AND scheduled_time < %(next)s
        AND (custom_cc_resource = %(resource)s"""
    args = dict(day=str(getdate(day)), next=str(getdate(day) + timedelta(days=1)), resource=resource)
    if practitioner:
        sql += ' OR custom_consultation_taken_by IN %(practitioners)s'
        args['practitioners'] = tuple(practitioner if isinstance(practitioner, list) else [practitioner])
    sql += ') ORDER BY scheduled_time, name' + (' FOR UPDATE' if lock else '')
    rows = frappe.db.sql(sql, args, as_dict=True)
    for r in rows:
        if not r.appointment_time:
            r.appointment_time = get_datetime(r.scheduled_time) + timedelta(minutes=60 if r.duration == '1 Hour' else int(re.sub(r'\D', '', r.duration or '') or 45))
    if practitioner and frappe.db.exists('DocType', 'Patient Appointment'):
        for r in frappe.get_all('Patient Appointment', filters={'practitioner': ['in', practitioner if isinstance(practitioner, list) else [practitioner]], 'appointment_date': str(getdate(day)), 'status': ['not in', ['Cancelled', 'No Show']]}, fields=['name', 'appointment_date', 'appointment_time', 'duration', 'branch'], limit_page_length=0):
            start = get_datetime(str(r.appointment_date) + ' ' + str(r.appointment_time or '00:00:00'))
            rows.append(frappe._dict(name=r.name, scheduled_time=start, appointment_time=start + timedelta(minutes=int(r.duration or 45)), branch=r.branch))
    return rows


def validate_booking(doc, method=None):
    if not doc.get('custom_cc_booking'): return
    authorize()
    if doc.status == 'Closed':
        if not is_manager() and doc.lead_owner != frappe.session.user:
            raise frappe.PermissionError('You cannot close another agent’s booking.')
        return
    branch_access(doc.branch)
    selected = next((x for x in staff_for(doc.branch) if x['id'] == doc.custom_cc_resource), None)
    if not selected: raise frappe.ValidationError('This staff member is not available at the selected branch.')
    lead = lead_access(doc.party)
    if doc.duration not in ('45 Minutes', '1 Hour'):
        raise frappe.ValidationError('A session must be 45 or 60 minutes.')
    start, end = interval(doc.scheduled_time, 60 if doc.duration == '1 Hour' else 45)
    kind, name = selected['id'].split(':', 1)
    # Row locks survive until the request commits, including simultaneous agent requests.
    frappe.db.sql('SELECT name FROM `tab' + kind + '` WHERE name=%s FOR UPDATE', name)
    frappe.db.sql('SELECT name FROM `tabLead` WHERE name=%s FOR UPDATE', lead.name)
    for row in resource_appointments(selected['id'], start.date(), selected.get('practitioners') or selected['practitioner'], lock=True):
        if row.name != doc.name and overlaps(start, end, get_datetime(row.scheduled_time), get_datetime(row.appointment_time)):
            raise frappe.ValidationError('This staff member is already booked during this time. Refresh the calendar and choose another slot.')
    duplicate = frappe.db.sql("""SELECT name FROM `tabAppointment` WHERE appointment_with='Lead' AND party=%s
        AND status != 'Closed' AND scheduled_time < %s AND appointment_time > %s AND name != %s FOR UPDATE""", (lead.name, end, start, doc.name or ''))
    if duplicate: raise frappe.ValidationError('This lead already has an overlapping appointment.')
    doc.scheduled_time, doc.appointment_time = start, end
    doc.date, doc.time = start.date(), start.time()
    doc.custom_cc_staff_name, doc.custom_cc_staff_role = selected['name'], selected.get('designation') or selected['role']
    doc.custom_consultation_taken_by = selected['practitioner'] or None
    doc.custom_employee_name = selected['name']
    doc.customer_name, doc.customer_phone_number = lead.lead_name, lead.mobile_no
    if doc.is_new(): doc.lead_owner = lead.lead_owner
    elif doc.has_value_changed('lead_owner'): raise frappe.ValidationError('The appointment lead owner cannot be changed.')


@frappe.whitelist(methods=['POST'])
def bootstrap(branch=None, query='', selected_lead=None):
    authorize()
    branches = frappe.get_list('Branch', pluck='name', order_by='name', limit_page_length=0)
    staff = []
    if branch:
        branch_access(branch)
        staff = staff_for(branch)
    filters = {} if is_manager() else {'lead_owner': frappe.session.user}
    search = str(query or '').strip()[:100]
    leads = frappe.get_list('Lead', filters=filters, or_filters={x: ['like', '%' + search + '%'] for x in ['name', 'lead_name', 'mobile_no']} if search else None,
        fields=['name', 'lead_name', 'mobile_no', 'lead_owner'], order_by='modified desc', limit_page_length=30, ignore_permissions=True)
    if selected_lead and not any(row.name == selected_lead for row in leads):
        selected = lead_access(selected_lead)
        leads.append(frappe._dict({key: selected.get(key) for key in ['name', 'lead_name', 'mobile_no', 'lead_owner']}))
    for row in leads:
        row['lead_owner_name'] = user_name(row.lead_owner)
    current = None
    if selected_lead:
        selected = lead_access(selected_lead)
        if selected.get('custom_appointment'):
            candidate = frappe.get_doc('Appointment', selected.custom_appointment)
            if candidate.party == selected_lead and candidate.get('custom_cc_booking') and candidate.status == 'Open':
                current = dict(name=candidate.name, modified=str(candidate.modified), branch=candidate.branch,
                    start=str(candidate.scheduled_time), duration=60 if candidate.duration == '1 Hour' else 45,
                    resource=candidate.custom_cc_resource, staff=candidate.custom_cc_staff_name)
    return dict(appointment=current, branches=branches, staff=staff, leads=leads, today=str(now_datetime().date()), timezone=frappe.utils.get_system_timezone(), user=frappe.session.user)


@frappe.whitelist(methods=['POST'])
def calendar(branch, date, resource='', duration=45, appointment=None):
    authorize(); branch_access(branch)
    editing = editable_appointment(appointment) if appointment else None
    day = getdate(date)
    if day < now_datetime().date() or day > now_datetime().date() + timedelta(days=365):
        raise frappe.ValidationError('Choose a date from today through the next 12 months.')
    staff = staff_for(branch)
    if resource: staff = [x for x in staff if x['id'] == resource]
    if resource and not staff: raise frappe.ValidationError('Select a staff member from this branch.')
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        raise frappe.ValidationError('Select a valid session duration.')
    if duration not in (45, 60): raise frappe.ValidationError('Select a 45-minute or 60-minute session.')
    now = now_datetime(); schedules = []
    resources = [person['id'] for person in staff]
    practitioners = list({p for person in staff for p in person.get('practitioners', [])})
    all_busy = []
    if resources:
        all_busy = frappe.db.sql("""SELECT name, scheduled_time, appointment_time, duration, customer_name,
            party, lead_owner, branch, custom_cc_resource, custom_consultation_taken_by, custom_cc_booking, status
            FROM `tabAppointment` WHERE status != 'Closed' AND scheduled_time >= %(day)s
            AND scheduled_time < %(next)s AND (custom_cc_resource IN %(resources)s
            OR custom_consultation_taken_by IN %(practitioners)s) ORDER BY scheduled_time""",
            dict(day=str(day), next=str(day + timedelta(days=1)), resources=tuple(resources), practitioners=tuple(practitioners or [''])), as_dict=True)
        for r in all_busy:
            if not r.appointment_time:
                minutes = 60 if r.duration == '1 Hour' else int(re.sub(r'\D', '', r.duration or '') or 45)
                r.appointment_time = get_datetime(r.scheduled_time) + timedelta(minutes=minutes)
    if practitioners and frappe.db.exists('DocType', 'Patient Appointment'):
        for r in frappe.get_all('Patient Appointment', filters={'practitioner': ['in', practitioners], 'appointment_date': str(day), 'status': ['not in', ['Cancelled', 'No Show']]}, fields=['name', 'practitioner', 'appointment_time', 'duration', 'branch'], limit_page_length=0):
            start = get_datetime(str(day) + ' ' + str(r.appointment_time or '00:00:00'))
            all_busy.append(frappe._dict(name=r.name, custom_consultation_taken_by=r.practitioner, scheduled_time=start, appointment_time=start + timedelta(minutes=int(r.duration or 45)), branch=r.branch))
    for person in staff:
        busy = [r for r in all_busy if r.get('custom_cc_resource') == person['id'] or (r.get('custom_consultation_taken_by') and r.custom_consultation_taken_by in person.get('practitioners', []))]
        slots = []
        start = datetime.combine(day, time(10))
        while start + timedelta(minutes=duration) <= datetime.combine(day, time(20)):
            end = start + timedelta(minutes=duration)
            occupied = any(overlaps(start, end, get_datetime(r.scheduled_time), get_datetime(r.appointment_time)) for r in busy if not (editing and r.get('custom_cc_booking') and r.name == editing.name))
            slots.append(dict(start=str(start), end=str(end), available=start > now and not occupied, reason='Time passed' if start <= now else ('Booked' if occupied else 'Available')))
            start += timedelta(minutes=15)
        events = []
        for r in busy:
            allowed = is_manager() or r.get('lead_owner') == frappe.session.user
            events.append(dict(editable=bool(allowed and r.get('custom_cc_booking') and r.get('status') == 'Open'), name=r.name if allowed else '', start=str(r.scheduled_time), end=str(r.appointment_time), branch=r.branch,
                client=r.get('customer_name') if allowed else 'Booked', agent=r.get('lead_owner') if allowed else '', agent_name=user_name(r.get('lead_owner')) if allowed else '', lead=r.get('party') if allowed else ''))
        schedules.append(dict(staff=person, slots=slots, events=events))
    return dict(schedules=schedules, date=str(day), now=str(now))


@frappe.whitelist(methods=['POST'])
def book(lead, branch, resource, start, duration, request_id):
    authorize(); lead_access(lead); branch_access(branch)
    if not re.fullmatch('[a-f0-9]{32}', str(request_id or '')): raise frappe.ValidationError('Invalid booking request. Refresh and try again.')
    start, end = interval(start, duration)
    previous = frappe.db.get_value('Appointment', {'custom_cc_request': request_id}, ['name', 'party', 'owner', 'branch', 'custom_cc_resource', 'scheduled_time', 'duration'], as_dict=True)
    if previous:
        if previous.party != lead or previous.owner != frappe.session.user or previous.branch != branch or previous.custom_cc_resource != resource or get_datetime(previous.scheduled_time) != start or previous.duration != ('1 Hour' if int(duration) == 60 else '45 Minutes'):
            raise frappe.ValidationError('This booking request was already used. Refresh the calendar.')
        return dict(name=previous.name, already_booked=True)
    doc = frappe.get_doc(dict(doctype='Appointment', custom_cc_booking=1, custom_cc_request=request_id,
        custom_cc_resource=resource, branch=branch, scheduled_time=start, duration='1 Hour' if int(duration)==60 else '45 Minutes',
        status='Open', appointment_with='Lead', party=lead, customer_name=lead))
    doc.insert(ignore_permissions=True)
    sync_lead(doc)
    return dict(name=doc.name, start=str(start), end=str(end), staff=doc.custom_cc_staff_name)


def sync_lead(doc):
    frappe.db.set_value('Lead', doc.party, {'custom_appointment_date_and_time': doc.scheduled_time,
        'custom_appointment_status': 'Booked', 'lead_assign_to_branch': doc.branch, 'branch': doc.branch,
        'custom_appointment': doc.name, 'custom_appointment_duration': doc.duration,
        'status': 'Appointment Booked', 'custom_cc_stage': 'SUCCESS',
        'custom_cc_sub_status': 'Appointment Booked',
        'custom_consulting_doctor': doc.custom_consultation_taken_by})


def editable_appointment(name):
    doc = frappe.get_doc('Appointment', name)
    if not doc.get('custom_cc_booking') or doc.appointment_with != 'Lead' or doc.status != 'Open':
        raise frappe.ValidationError('Only open CC appointments can be rescheduled.')
    lead_access(doc.party)
    branch_access(doc.branch)
    return doc


@frappe.whitelist(methods=['POST'])
def reschedule(appointment, branch, resource, start, duration, modified):
    authorize()
    doc = editable_appointment(appointment)
    branch_access(branch)
    start, end = interval(start, duration)
    # Serialize edits and reject stale dialogs rather than overwriting another change.
    frappe.db.sql('SELECT name FROM `tabAppointment` WHERE name=%s FOR UPDATE', doc.name)
    doc.reload()
    editable_appointment(doc.name)
    if str(doc.modified) != str(modified):
        raise frappe.ValidationError('This appointment changed. Reopen it to see the latest details.')
    doc.branch, doc.custom_cc_resource = branch, resource
    doc.scheduled_time = start
    doc.duration = '1 Hour' if int(duration) == 60 else '45 Minutes'
    doc.save(ignore_permissions=True)
    sync_lead(doc)
    return dict(name=doc.name, start=str(start), end=str(end), staff=doc.custom_cc_staff_name)



def enrich_lead_appointments(rows):
    """Attach booking details only to leads already authorized by the caller."""
    names = [row.get('custom_appointment') for row in rows if row.get('custom_appointment')]
    if not names:
        return
    appointments = frappe.get_all('Appointment', filters={'name': ['in', names]},
        fields=['name', 'party', 'scheduled_time', 'appointment_time', 'custom_cc_staff_name',
                'custom_cc_staff_role', 'custom_cc_resource'], limit_page_length=0)
    by_name = {row.name: row for row in appointments}
    for row in rows:
        appointment = by_name.get(row.get('custom_appointment'))
        if not appointment or appointment.party != row.name:
            continue
        row['cc_consultation_employee'] = appointment.custom_cc_staff_name or ''
        row['cc_consultation_designation'] = appointment.custom_cc_staff_role or ''
        row['cc_appointment_end'] = str(appointment.appointment_time or '')
        row['cc_appointment_start'] = str(appointment.scheduled_time or '')
