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
