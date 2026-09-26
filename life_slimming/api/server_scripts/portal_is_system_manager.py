"""portal_is_system_manager

Original API: portal_is_system_manager
Source modified: 2026-08-14 12:07:07.907502
See ../CATALOG.md for migration notes and validation limits.
"""

import json
import re

import frappe
from frappe.integrations.utils import make_post_request as _make_post_request
from frappe.utils.safe_exec import read_sql as _read_sql
from frappe.utils.safe_exec import call_whitelisted_function as _call_whitelisted
from life_slimming.api._runtime import script_endpoint


@script_endpoint(allow_guest=False)
def run(**kwargs):
    # ============================================================
    # SERVER SCRIPT  (type: API)
    # Name: portal_is_system_manager
    # API method name: portal_is_system_manager
    # Returns {"is_sys_mgr": 1/0, "roles":[...]} for the LOGGED-IN user.
    # Safe: only reports the caller's own roles.
    #
    # Create it: Desk > Server Script > New
    #   Script Type = API
    #   API Method  = portal_is_system_manager
    #   (paste the body below)
    #   Enable "Allow Guest" = OFF
    # ============================================================

    roles = frappe.get_roles(frappe.session.user)
    frappe.response["message"] = {
        "user": frappe.session.user,
        "is_sys_mgr": 1 if ("System Manager" in roles or frappe.session.user == "Administrator") else 0,
        "roles": roles,
    }
