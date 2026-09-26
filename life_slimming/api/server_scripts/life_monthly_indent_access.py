"""Monthly indent access for branches

Original API: life_monthly_indent_access
Source modified: 2026-07-25 01:37:08.489188
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
    # Server Script Type: API
    # API Method: life_monthly_indent_access
    # Allow Guest: Disabled
    #
    # Purpose:
    # - Every authenticated user can read the shared Monthly Indent exception state.
    # - Only the approved HO / Store Manager users can change it.
    # - The value is stored in the Single DocType:
    #     LIFE Stock Request Settings.enable_monthly_indent_exception

    user = str(frappe.session.user or "").strip()
    user_key = user.lower()

    if not user or user_key == "guest":
        frappe.throw("Please log in to access Monthly Indent settings.", frappe.PermissionError)

    action = str(frappe.form_dict.get("action") or "get").strip().lower()

    settings_doctype = "LIFE Stock Request Settings"
    settings_field = "enable_monthly_indent_exception"

    allowed_users = [
        "bhuvan@lifescc.com",
        "inventory@lifescc.com",
        "lokakavyareddy3@gmail.com",
        "narendhar@lifescc.com",
        "administrator",
        "yaswanthkumaryy1234@gmail.com"
    ]

    current_value = frappe.db.get_single_value(
        settings_doctype,
        settings_field
    )

    enabled = 1 if str(current_value or "0").strip().lower() in [
        "1",
        "true",
        "yes",
        "on"
    ] else 0

    if action == "set":
        if user_key not in allowed_users:
            frappe.throw(
                "Only authorized HO / Store Manager users can change Monthly Indent exception access.",
                frappe.PermissionError
            )

        requested_value = str(
            frappe.form_dict.get("enabled") or "0"
        ).strip().lower()

        enabled = 1 if requested_value in [
            "1",
            "true",
            "yes",
            "on"
        ] else 0

        frappe.db.set_single_value(
            settings_doctype,
            settings_field,
            enabled
        )

    elif action != "get":
        frappe.throw("Invalid action. Use get or set.")

    frappe.response["message"] = {
        "enabled": enabled,
        "updated_by": user if action == "set" else "",
        "source": "LIFE Stock Request Settings"
    }
