import frappe
import frappe.sessions


@frappe.whitelist(allow_guest=True)
def token():
    return frappe.local.session.data.csrf_token