"""Read-only CC billing access and explicit junk lead recovery."""
import frappe
from life_slimming.portal_access import require_module


@frappe.whitelist()
def invoices(query='', start=0, name=None):
    require_module('leads')
    if name:
        doc = frappe.get_doc('Sales Invoice', name)
        result = {key: doc.get(key) for key in (
            'name', 'customer_name', 'posting_date', 'branch', 'status',
            'grand_total', 'outstanding_amount', 'currency')}
        result['items'] = [{key: item.get(key) for key in
                            ('name', 'item_name', 'qty', 'rate', 'amount')} for item in doc.items]
        return result
    term = str(query or '').strip()
    filters = []
    or_filters = [[field, 'like', '%' + term + '%'] for field in
                  ('name', 'customer_name', 'patient')] if term else None
    return frappe.get_all('Sales Invoice', filters=filters, or_filters=or_filters,
        fields=['name', 'customer_name', 'posting_date', 'branch', 'status',
                'grand_total', 'outstanding_amount', 'currency'],
        order_by='posting_date desc, name desc', limit_start=max(0, int(start)), limit_page_length=40)


@frappe.whitelist(methods=['POST'])
def recover_junk(lead):
    require_module('leads')
    frappe.db.sql('SELECT name FROM `tabLead` WHERE name=%s FOR UPDATE', lead)
    doc = frappe.get_doc('Lead', lead)
    if doc.get('custom_cc_sub_status') not in ('Junk/Wrong Call', 'Not Enquired'):
        frappe.throw('Only junk leads can be recovered here.')
    if doc.get('custom_appointment_status') == 'Visited Booked':
        frappe.throw('Booked clients cannot be reopened here.')
    doc.update({'status': 'Lead', 'custom_cc_stage': 'UNTOUCHED', 'custom_cc_sub_status': ''})
    doc.flags.ignore_version = False
    doc.save(ignore_permissions=True)
    doc.add_comment('Info', 'Junk lead unlocked for review by ' + frappe.session.user)
    return {'name': doc.name}


UPDATE_FIELDS = {
    'status': 'Lead status', 'lead_owner': 'Assigned agent',
    'custom_cc_stage': 'CC stage', 'custom_cc_sub_status': 'Call outcome',
    'custom_next_followup_date': 'Next follow-up',
    'custom_appointment_date_and_time': 'Appointment',
    'custom_appointment_status': 'Appointment status',
    'custom_call_count': 'Call count', 'custom_last_call_time': 'Last call',
    'custom_cc_chat_returned': 'New Lead to the Same Agent',
    'custom_convox_call_status': 'Call status',
    'custom_convox_disposition': 'Call disposition',
}


@frappe.whitelist()
def lead_updates(from_date, to_date, start=0):
    """Return dated saved changes within the viewer's current lead scope."""
    import json
    from frappe.utils import getdate, add_days

    require_module('leads')
    if not from_date or not to_date:
        frappe.throw('Choose a start date and end date.')
    first, last = getdate(from_date), getdate(to_date)
    if first > last:
        frappe.throw('Start date must be on or before end date.')
    manager = frappe.session.user == 'Administrator' or bool(
        set(frappe.get_roles(frappe.session.user)) &
        {'System Manager', 'Sales Manager', 'Call Center Export'})
    offset = max(0, int(start))
    params = {'first': first, 'until': add_days(last, 1),
              'user': frappe.session.user, 'start': offset}
    scope = '' if manager else ' AND l.lead_owner = %(user)s'
    records = frappe.db.sql('''
        SELECT v.name, v.creation, v.owner, v.data, v.docname AS lead,
               l.lead_name, l.lead_owner
        FROM `tabVersion` v INNER JOIN `tabLead` l ON l.name = v.docname
        WHERE v.ref_doctype = 'Lead' AND v.creation >= %(first)s
          AND v.creation < %(until)s''' + scope + '''
        ORDER BY v.creation DESC, v.name DESC LIMIT 51 OFFSET %(start)s
    ''', params, as_dict=True)
    rows = []
    for record in records[:50]:
        try:
            data = json.loads(record.get('data') or '{}')
        except (TypeError, ValueError):
            data = {}
        changed = (data.get('changed') or []) if isinstance(data, dict) else []
        changes = []
        for change in changed if isinstance(changed, list) else []:
            if isinstance(change, list) and len(change) >= 3 and isinstance(change[0], str) and change[0] in UPDATE_FIELDS:
                changes.append({'field': change[0], 'label': UPDATE_FIELDS[change[0]],
                                'before': change[1], 'after': change[2]})
        rows.append({key: record.get(key) for key in
                     ('name', 'creation', 'owner', 'lead', 'lead_name', 'lead_owner')})
        rows[-1]['changes'] = changes
    return {'rows': rows, 'more': len(records) > 50, 'start': offset,
            'scoped_to_owner': not manager}
