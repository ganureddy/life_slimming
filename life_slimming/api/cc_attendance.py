"""Read CC attendance and punch times using the portal's lead access scope."""
import frappe
from frappe.utils import nowdate, getdate, date_diff
from life_slimming.portal_access import require_module
from life_slimming.api._runtime import script_endpoint


@script_endpoint(allow_guest=False)
def snapshot(from_date=None, to_date=None, **kwargs):
    try:
        require_module('leads')
    except frappe.PermissionError:
        require_module('ccvisit')
    user = frappe.session.user
    manager = user == 'Administrator' or bool(set(frappe.get_roles()).intersection({'System Manager', 'Call Center Export', 'Sales Manager'}))
    start, end = getdate(from_date or nowdate()), getdate(to_date or nowdate())
    if end < start or date_diff(end, start) > 62:
        frappe.throw('Choose an attendance range of up to 63 days.')
    filters = {'status': 'Active', **({'branch': 'Ho CC'} if manager else {'user_id': user})}
    employees = frappe.get_all('Employee', filters=filters,
        fields=['name', 'employee_name', 'designation', 'department', 'user_id'], order_by='employee_name asc', limit_page_length=1000)
    ids = [e.name for e in employees]
    rows = []
    if ids:
        fields = ['name', 'employee', 'attendance_date', 'status']
        meta = frappe.get_meta('Attendance')
        fields += [field for field in ('custom_check_in_time', 'custom_check_out_time', 'working_hours') if meta.has_field(field)]
        rows = frappe.get_all('Attendance', filters={'employee': ['in', ids], 'attendance_date': ['between', [start, end]], 'docstatus': ['<', 2]},
            fields=fields, order_by='attendance_date desc, employee asc', limit_page_length=65000)
    return {'employees': employees, 'rows': rows, 'manager': manager, 'today': nowdate(), 'user': user}
