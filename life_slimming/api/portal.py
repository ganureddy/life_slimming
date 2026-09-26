"""Session bootstrap for the separate Vue portal; no remote ERP credentials."""

import json

import frappe
from frappe.sessions import get_csrf_token


@frappe.whitelist()
def bootstrap():
    user = frappe.get_doc("User", frappe.session.user)
    roles = frappe.get_roles(user.name)
    # Custom fields/settings may not have been installed on a development site.
    portal_role = user.get("custom_portal_role") or ""
    access_config = None
    if frappe.db.exists("DocType", "Portal Access Settings"):
        settings = frappe.get_doc("Portal Access Settings")
        if settings.has_permission("read"):
            try:
                access_config = json.loads(settings.get("access_config") or "null")
            except (ValueError, TypeError):
                pass

    return {
        "user": user.name,
        "full_name": user.full_name or user.name,
        "roles": roles,
        "portal_role": portal_role,
        "access_config": access_config,
        "csrf_token": get_csrf_token(),
    }
