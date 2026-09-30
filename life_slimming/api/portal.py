"""Session bootstrap for the separate Vue portal; no remote ERP credentials."""

import hashlib

import frappe
from frappe.sessions import get_csrf_token
from life_slimming.portal_access import access_settings


@frappe.whitelist()
def bootstrap():
    user = frappe.get_doc("User", frappe.session.user)
    roles = frappe.get_roles(user.name)
    # Custom fields/settings may not have been installed on a development site.
    portal_role = user.get("custom_portal_role") or ""
    access_config = access_settings()

    return {
        "user": user.name,
        "session_id": hashlib.sha256(frappe.session.sid.encode()).hexdigest()[:24],
        "full_name": user.full_name or user.name,
        "roles": roles,
        "portal_role": portal_role,
        "access_config": access_config,
        "csrf_token": get_csrf_token(),
    }
