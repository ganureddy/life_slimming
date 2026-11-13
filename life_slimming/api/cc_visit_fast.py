"""Bounded, appointment-only reads for the visit report's initial view."""
import frappe

LIMIT = 10000
APPOINTMENT_FIELDS = [
    'name', 'lead_name', 'mobile_no', 'lead_owner', 'branch', 'lead_assign_to_branch',
    'custom_appointment_date_and_time', 'custom_appointment_status', 'status',
]


def read_appointments(from_date, to_date, owner_filter, unrestricted, agent_login, calendar=False, detail_fields=None, visit_history=False):
    # The calling report has already authenticated and resolved owner permissions.
    query = frappe.get_all if unrestricted or agent_login else frappe.get_list
    filters = {
        'custom_appointment_date_and_time': ['between', [from_date + ' 00:00:00', to_date + ' 23:59:59']],
        'lead_owner': owner_filter or ['is', 'set'],
    }
    if calendar:
        rows = query('Lead', filters=filters,
            fields=['date(custom_appointment_date_and_time) as day', 'branch', 'lead_assign_to_branch',
                    'lead_owner', 'custom_appointment_status', 'count(name) as count'],
            group_by='date(custom_appointment_date_and_time), branch, lead_assign_to_branch, lead_owner, custom_appointment_status',
            order_by='day asc', limit_page_length=LIMIT + 1)
        return {'ok': True, 'view': 'calendar', 'days': rows[:LIMIT],
                'truncated': len(rows) > LIMIT, 'restricted_to_owner': bool(owner_filter)}
    fields = list(detail_fields or APPOINTMENT_FIELDS)
    if 'custom_visit_status' not in fields and frappe.get_meta('Lead').has_field('custom_visit_status'):
        fields.append('custom_visit_status')
    rows = query('Lead', fields=fields, filters=filters,
        order_by='custom_appointment_date_and_time desc, name asc', limit_page_length=LIMIT + 1)
    history_complete = None
    if visit_history:
        try:
            history_complete = enrich_visit_ordinals(rows[:LIMIT], to_date, query, owner_filter)
        except Exception:
            # A history failure must not hide the permitted appointment schedule.
            history_complete = False
            for row in rows[:LIMIT]:
                row['lifeVisit'] = None
    names = {}
    if rows:
        owners = list({row.get('lead_owner') for row in rows[:LIMIT] if row.get('lead_owner')})
        for start in range(0, len(owners), 500):
            for owner in frappe.get_all('User', filters={'name':['in',owners[start:start+500]]}, fields=['name','full_name'], limit_page_length=500):
                names[owner.name] = owner.full_name or owner.name
    truncated = len(rows) > LIMIT
    return {'ok': True, 'view': 'appointments', 'rows': rows[:LIMIT],
            'count': min(len(rows), LIMIT), 'total': len(rows), 'total_is_lower_bound': truncated,
            'truncated': truncated, 'restricted_to_owner': bool(owner_filter),
            'visit_history_complete': history_complete, 'agent_names': names, 'ranking_rows': [], 'financial_events': [], 'marketing_agencies': []}


def apply_visit_ordinals(rows, history):
    """Reference history rule: one plus earlier explicit walk-ins on the same phone."""
    from bisect import bisect_left
    by_phone = {}
    seen = set()
    for lead in history:
        if lead.get('name') in seen:
            continue
        seen.add(lead.get('name'))
        status = str(lead.get('custom_appointment_status') or lead.get('custom_visit_status') or lead.get('status') or '').lower()
        status = ' '.join(status.replace('–', ' ').replace('—', ' ').replace('-', ' ').replace('&', ' ').split())
        if status in ('visited', 'visited booked', 'visited not booked'):
            by_phone.setdefault(lead.get('mobile_no'), []).append(str(lead.get('custom_appointment_date_and_time') or ''))
    for stamps in by_phone.values():
        stamps.sort()
    for row in rows:
        phone = row.get('mobile_no')
        row['lifeVisit'] = 1 + bisect_left(by_phone.get(phone, []), str(row.get('custom_appointment_date_and_time') or '')) if phone else None


def enrich_visit_ordinals(rows, end_date, query, owner_filter):
    mobiles = sorted({row.get('mobile_no') for row in rows if row.get('mobile_no')})
    history = []
    fields = ['name', 'mobile_no', 'custom_appointment_date_and_time', 'custom_appointment_status', 'status']
    if frappe.get_meta('Lead').has_field('custom_visit_status'):
        fields.append('custom_visit_status')
    for offset in range(0, len(mobiles), 400):
        remaining = 30000 - len(history)
        filters = {'mobile_no': ['in', mobiles[offset:offset+400]],
            'custom_appointment_date_and_time': ['<', end_date + ' 23:59:59']}
        if owner_filter:
            filters['lead_owner'] = owner_filter
        batch = query('Lead', fields=fields, filters=filters,
            order_by='custom_appointment_date_and_time asc, name asc', limit_page_length=remaining+1)
        if len(batch) > remaining:
            for row in rows:
                row['lifeVisit'] = None
            return False
        history.extend(batch)
    apply_visit_ordinals(rows, history)
    return True
