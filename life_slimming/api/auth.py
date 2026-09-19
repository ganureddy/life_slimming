"""Public login UI configuration. Authentication remains in Frappe's login API."""

import frappe
from frappe.sessions import get_csrf_token
from frappe.utils import cint


@frappe.whitelist(allow_guest=True, methods=["GET"])
def login_context():
    method = frappe.get_system_settings("two_factor_method")
    return {
        "authenticated": frappe.session.user != "Guest",
        "csrf_token": get_csrf_token(),
        "password_login_enabled": not cint(
            frappe.get_system_settings("disable_user_pass_login")
        ),
        "two_factor_method": method,
        "challenge_seconds": 300 if method in ("SMS", "Email") else 180,
    }
