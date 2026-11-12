"""Add consultant attribution only to invoices already authorized by the report."""
import frappe


def enrich_consultants(rows):
    plans = sorted({row.get('therapy_plan') for row in rows if row.get('therapy_plan')})
    if not plans or not frappe.db.exists('DocType', 'Therapy Plan'):
        return
    meta = frappe.get_meta('Therapy Plan')
    if not meta.has_field('consultant_name'):
        return
    fields = ['name', 'consultant_name']
    if meta.has_field('custom_employee_name'):
        fields.append('custom_employee_name')
    mapping = {}
    for start in range(0, len(plans), 500):
        for plan in frappe.get_all('Therapy Plan', filters={'name':['in',plans[start:start+500]]}, fields=fields, limit_page_length=500):
            mapping[plan.name] = plan
    for row in rows:
        plan = mapping.get(row.get('therapy_plan'))
        if plan:
            row['consultant_id'] = plan.get('consultant_name') or ''
            row['consultant_name'] = plan.get('custom_employee_name') or row['consultant_id']
            row['consultant_basis'] = 'Therapy Plan.consultant_name'


def enrich_appointment_consultants(appointments, invoices):
    """Enrich authorized appointments in batches, never scan the full Lead master.

    Match a linked Therapy Plan first, then Patient.custom_employee_id. Unresolved
    appointments remain in totals and are explicitly marked as unmapped.
    """
    records = [dict(row) for row in appointments if row.get('custom_appointment_date_and_time')]
    if not records:
        return []
    leads = {row['name'] for row in records}
    by_lead = {}
    if frappe.db.exists('DocType', 'Patient'):
        meta = frappe.get_meta('Patient')
        fields = ['name', *[field for field in ('custom_lead', 'custom_employee_id', 'customer', 'mobile', 'patient_name') if meta.has_field(field)]]
        names = sorted(leads)
        if meta.has_field('custom_lead'):
            for start in range(0, len(names), 400):
                patients = frappe.get_all('Patient', filters={'custom_lead': ['in', names[start:start+400]]},
                    fields=fields, order_by='modified desc, name asc', limit_page_length=10000)
                for patient in patients:
                    by_lead.setdefault(patient.custom_lead, patient)
        missing = [row for row in records if row['name'] not in by_lead]
        pool = {}
        for field, values in [('customer', {row.get('customer') for row in missing if row.get('customer')}),
                              ('mobile', {str(row.get('mobile_no') or '') for row in missing if row.get('mobile_no')})]:
            if not meta.has_field(field):
                continue
            if field == 'mobile':
                import re
                values |= {re.sub(r'\D', '', value)[-10:] for value in values}
            values = sorted(values)
            for start in range(0, len(values), 400):
                try:
                    matches = frappe.get_list('Patient', filters={field: ['in', values[start:start+400]]},
                        fields=fields, order_by='modified desc, name asc', limit_page_length=10001)
                except frappe.PermissionError:
                    matches = []
                if len(matches) <= 10000:
                    pool.update({row.name: row for row in matches})
        for row in missing:
            patient = choose_patient(row, list(pool.values()))
            if patient:
                by_lead[row['name']] = patient
    invoice_by_lead = {}
    for invoice in invoices:
        if invoice.get('lead') and invoice.get('consultant_id'):
            invoice_by_lead.setdefault(invoice['lead'], invoice)
    plans_by_patient = {}
    if by_lead and frappe.db.exists('DocType', 'Therapy Plan'):
        meta = frappe.get_meta('Therapy Plan')
        if meta.has_field('patient') and meta.has_field('consultant_name'):
            patient_ids = sorted({row.name for row in by_lead.values()})
            plan_fields = ['name', 'patient', 'consultant_name', 'creation', 'modified']
            if meta.has_field('start_date'):
                plan_fields.append('start_date')
            for start in range(0, len(patient_ids), 400):
                for plan in frappe.get_all('Therapy Plan', filters={'patient': ['in', patient_ids[start:start+400]], 'docstatus': ['!=', 2]},
                        fields=plan_fields, order_by='creation desc, name desc', limit_page_length=10000):
                    plans_by_patient.setdefault(plan.patient, []).append(plan)
    attribution = {}
    for row in records:
        invoice = invoice_by_lead.get(row['name']) or {}
        patient = by_lead.get(row['name']) or {}
        plan = choose_appointment_plan(row, plans_by_patient.get(patient.get('name'), []))
        consultant = invoice.get('consultant_id') or plan.get('consultant_name') or patient.get('custom_employee_id') or row.get('custom_consulting_doctor') or ''
        basis = 'Therapy Plan.consultant_name' if invoice or plan else 'Patient.custom_employee_id' if patient.get('custom_employee_id') else 'Lead.custom_consulting_doctor' if consultant else ''
        status = ' '.join(str(row.get('custom_appointment_status') or '').lower().replace('–',' ').replace('-',' ').split())
        if not consultant and status in ('not visited', 'visited not booked'):
            consultant = row.get('custom_status_updated_by_employee') or row.get('custom_status_updated_by_name') or ''
            if consultant:
                basis = 'Lead status updater (no linked consultant)'
        attribution[row['name']] = (consultant, basis)
    branches = sorted({row.get('branch') or row.get('lead_assign_to_branch') for row in records} - {None, ''})
    employees = []
    if branches and frappe.db.exists('DocType', 'Employee'):
        for start in range(0, len(branches), 400):
            employees.extend(frappe.get_all('Employee', filters={'branch': ['in', branches[start:start+400]], 'status': 'Active'},
                fields=['name', 'employee_name', 'designation', 'branch', 'reports_to'], limit_page_length=10000))
    # Include directly linked consultants who work across branches.
    ids = sorted({str(value[0]).strip() for value in attribution.values()} - {''})
    known = {row.name for row in employees}
    ids = [name for name in ids if name not in known]
    for start in range(0, len(ids), 400):
        employees.extend(frappe.get_all('Employee', filters={'name': ['in', ids[start:start+400]], 'status': 'Active'},
            fields=['name', 'employee_name', 'designation', 'branch', 'reports_to'], limit_page_length=400))
    practitioner_to_employee = {}
    unresolved = sorted(set(ids) - {row.name for row in employees})
    if unresolved and frappe.db.exists('DocType', 'Healthcare Practitioner') and frappe.get_meta('Healthcare Practitioner').has_field('employee'):
        for start in range(0, len(unresolved), 400):
            try:
                practitioners = frappe.get_list('Healthcare Practitioner', filters={'name': ['in', unresolved[start:start+400]]}, fields=['name', 'employee'], limit_page_length=400)
            except frappe.PermissionError:
                practitioners = []
            practitioner_to_employee.update({row.name: row.employee for row in practitioners if row.employee})
        missing_employee_ids = sorted(set(practitioner_to_employee.values()) - {row.name for row in employees})
        for start in range(0, len(missing_employee_ids), 400):
            employees.extend(frappe.get_all('Employee', filters={'name': ['in', missing_employee_ids[start:start+400]], 'status': 'Active'},
                fields=['name', 'employee_name', 'designation', 'branch', 'reports_to'], limit_page_length=400))
    employee_by_id = {row.name: row for row in employees}
    employee_by_name = {}
    for employee in employees:
        employee_by_name.setdefault(' '.join(str(employee.employee_name or '').lower().split()), []).append(employee)
    manager_ranks = {'senior manager': 1, 'center manager': 2, 'centre manager': 2, 'branch manager': 3, 'manager': 4}
    def rank(employee):
        designation = str(employee.designation or '').strip().lower()
        return manager_ranks.get(designation, next((n+4 for title,n in manager_ranks.items() if title in designation), 999))
    managers = {}
    for employee in sorted(employees, key=lambda row: (rank(row), row.employee_name or row.name)):
        if rank(employee) < 999:
            managers.setdefault(employee.branch, employee)
    for row in records:
        invoice = invoice_by_lead.get(row['name']) or {}
        patient = by_lead.get(row['name']) or {}
        consultant_id, basis = attribution[row['name']]
        employee = employee_by_id.get(practitioner_to_employee.get(consultant_id, consultant_id))
        if not employee:
            matches = employee_by_name.get(' '.join(str(consultant_id).lower().split()), [])
            if len(matches) == 1:
                employee = matches[0]
        branch = row.get('branch') or row.get('lead_assign_to_branch') or ''
        manager = managers.get(branch)
        row.update(consultant_id=employee.name if employee else '',
            consultant_name=employee.employee_name if employee else 'Consultant Unmapped',
            consultant_designation=employee.designation if employee else '',
            consultant_basis=basis,
            manager_id=manager.name if manager else '', manager_name=manager.employee_name if manager else 'Manager Unmapped',
            consultant_eligible=bool(employee))
    return records


def choose_patient(record, patients):
    """Same exact-link/customer/mobile-and-name precedence as the reference."""
    import re
    def phone(value):
        return re.sub(r'\D', '', str(value or ''))[-10:]
    def name(value):
        return ' '.join(str(value or '').strip().lower().split())
    for field, value in (('name', record.get('patient') or record.get('custom_patient')),
                         ('custom_lead', record.get('name'))):
        if value:
            found = next((row for row in patients if row.get(field) == value), None)
            if found:
                return found
    if record.get('customer'):
        matches = [row for row in patients if row.get('customer') == record['customer']]
        if len(matches) == 1:
            return matches[0]
    mobile = phone(record.get('mobile_no'))
    if not mobile:
        return None
    matches = [row for row in patients if phone(row.get('mobile')) == mobile]
    if len(matches) == 1:
        return matches[0]
    return next((row for row in matches if name(row.get('patient_name')) == name(record.get('lead_name'))), None)


def choose_appointment_plan(record, plans):
    from datetime import date
    def distance(plan):
        try:
            days = (date.fromisoformat(str(plan.get('start_date') or plan.get('creation'))[:10]) -
                date.fromisoformat(str(record.get('custom_appointment_date_and_time'))[:10])).days
        except (ValueError, TypeError):
            days = 999999
        return (0 if -1 <= days <= 45 else 1, abs(days))
    # Stable secondary ordering matches the reference's most-recent modified tie-break.
    ordered = sorted(plans, key=lambda plan: str(plan.get('modified') or ''), reverse=True)
    return min(ordered, key=distance) if ordered else {}
