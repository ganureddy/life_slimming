"""Idle exemptions shared by Desk, legacy pages and the Vue portal."""

import frappe
from frappe.sessions import get_expiry_in_seconds


DEFAULT_EXEMPT_USERS = ("narendhar@lifescc.com", "life@gmail.com")


def idle_logout_exempt():
    users = frappe.conf.get("life_idle_logout_exempt_users", DEFAULT_EXEMPT_USERS)
    if isinstance(users, str):
        users = users.split(",")
    user = str(frappe.session.user or "").strip().lower()
    return user not in ("", "guest") and user in {
        str(value).strip().lower() for value in (users or [])
    }


@frappe.whitelist(methods=["GET"])
def heartbeat():
    # A normal authenticated request renews the existing Frappe session.
    # It cannot recreate an expired session or bypass explicit logout.
    return {
        "idle_logout_exempt": idle_logout_exempt(),
        "heartbeat_seconds": max(1, min(60, get_expiry_in_seconds() // 3)),
    }
