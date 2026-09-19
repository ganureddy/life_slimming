"""roster_employees

Original API: roster_employees
Source modified: 2026-08-07 09:27:30.565509
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
    # SERVER SCRIPT  (create in: Server Script list)
    #   Script Type : API
    #   API Method  : roster_employees
    #   Allow Guest : No
    # Endpoint becomes: /api/method/roster_employees?branch=<Branch>
    #
    # Purpose: return ALL active employees for a branch, bypassing the
    # User-Permission-on-user_id filter that hides staff from branch logins.
    # Pass branch = "ALL" (or empty) to get every active employee across
    # branches (used by the roster submission-status cards).
    #
    # safe_exec compliant: no imports, no f-strings, no .format(),
    # no tuple-unpack, no leading-underscore names, no commit.
    # ============================================================

    br = frappe.form_dict.get("branch")

    flt = {"status": "Active"}
    if br and br != "ALL" and br != "":
        flt["branch"] = br

    rows = frappe.db.get_all(
        "Employee",
        filters=flt,
        fields=["name", "employee_name", "designation", "company", "department", "branch"],
        order_by="department asc, employee_name asc",
        limit_page_length=0,
        ignore_permissions=True
    )

    frappe.response["message"] = rows
