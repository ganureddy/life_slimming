"""On-demand PD form / visit details for a permitted report lead."""
import frappe
from life_slimming.api._runtime import script_endpoint
from life_slimming.portal_access import require_module
from life_slimming.api.server_scripts.cc_walkin_details import run as walkin_details


@script_endpoint(allow_guest=False)
def run(lead=None, **kwargs):
    require_module('ccvisit', tab='visits')
    if not isinstance(lead, str) or not lead.strip():
        frappe.throw('Choose a Lead.')
    lead = lead.strip()
    user = frappe.session.user
    unrestricted = user == 'Administrator' or 'System Manager' in frappe.get_roles()
    filters = {'name': lead}
    if not unrestricted and 'All Leads Reader' not in frappe.get_roles() and frappe.db.exists('Lead', {'lead_owner': user}):
        filters['lead_owner'] = user
    query = frappe.get_all if unrestricted else frappe.get_list
    if not query('Lead', filters=filters, fields=['name'], limit_page_length=1):
        frappe.throw('This Lead is outside your report access.', frappe.PermissionError)
    walkin_details(lead=lead)
    return frappe.response.get('message')
