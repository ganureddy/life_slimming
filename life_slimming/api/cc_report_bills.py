"""Client-linked branch bill evidence for a bounded, authorized report page."""
import json
import frappe
from life_slimming.api._runtime import script_endpoint
from life_slimming.portal_access import require_module
from life_slimming.cc_business_rules import paid_evidence


@script_endpoint(allow_guest=False)
def run(leads=None, **kwargs):
    require_module('ccvisit', tab='visits')
    names = json.loads(leads) if isinstance(leads, str) else leads or []
    if not isinstance(names, list) or len(names) > 200 or any(not isinstance(name, str) for name in names):
        frappe.throw('Choose up to 200 Lead IDs.')
    names = sorted(set(names))
    if not names:
        return {'leads': {}}
    user = frappe.session.user
    roles = frappe.get_roles()
    unrestricted = user == 'Administrator' or 'System Manager' in roles
    filters = {'name': ['in', names]}
    local = str(user).split('@')[0].lower()
    agent_login = local.startswith('lifescc') and local[7:].isdigit()
    if not unrestricted and 'All Leads Reader' not in roles:
        agent_login = agent_login or bool(frappe.db.exists('Lead', {'lead_owner': user}))
        if agent_login:
            filters['lead_owner'] = user
    query = frappe.get_all if unrestricted else frappe.get_list
    permitted = query('Lead', filters=filters, fields=['name'], limit_page_length=200)
    allowed = [row.name for row in permitted]
    evidence = paid_evidence(allowed, include_invoices=True)
    return {'leads': {name: evidence.get(name, {'paid': 0, 'has_bill': False, 'invoices': []}) for name in allowed}}
