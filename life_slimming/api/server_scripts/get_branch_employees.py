"""Get Branch Employees

Original API: get_branch_employees
Source modified: 2026-06-03 23:16:14.783764
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
    ## ═══════════════════════════════════════════════════════════
    ## SERVER SCRIPT 1 — Get Branch Employees
    ## ═══════════════════════════════════════════════════════════
    ## Script Type  : API
    ## API Method   : get_branch_employees
    ## Allow Guest  : NO
    ## Enabled      : YES
    ## ═══════════════════════════════════════════════════════════

    branch = frappe.form_dict.get("branch")

    if not branch:
        frappe.response["message"] = {"staff": [], "managers": []}
    else:
        employees = frappe.db.get_all(
            "Employee",
            filters={"branch": branch, "status": "Active"},
            fields=["employee_name", "designation"],
            order_by="employee_name asc"
        )

        staff    = []
        managers = []

        for emp in employees:
            name  = emp.get("employee_name") or ""
            desig = emp.get("designation") or "Staff"
            entry = {"employee_name": name, "designation": desig}
            staff.append(entry)
            d = desig.lower()
            if ("manager" in d or "head" in d or "supervisor" in d
                    or "incharge" in d or "in-charge" in d
                    or "director" in d or "admin" in d):
                managers.append(entry)

        frappe.response["message"] = {
            "staff":    staff,
            "managers": managers if managers else staff
        }
