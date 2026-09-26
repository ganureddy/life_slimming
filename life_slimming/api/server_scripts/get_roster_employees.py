"""get_roster_employees

Original API: get_roster_employees
Source modified: 2026-07-25 18:27:34.692036
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
    # ============================================================================
    # SERVER SCRIPT  |  Script Type: API  |  API Method: get_roster_employees
    # ----------------------------------------------------------------------------
    # HOW TO INSTALL (do this once):
    #   Desk > Server Script > New
    #     Script Type : API
    #     API Method  : get_roster_employees
    #     Allow Guest : No
    #     Enabled     : Yes
    #   Paste EVERYTHING below the line into the Script field, Save.
    #
    # WHY THIS EXISTS
    #   The roster's client-side frappe.client.get_list('Employee', ...) call is
    #   filtered by the branch account's "Allow: User" user permissions, because
    #   Employee has a user_id link to User. That hides every employee whose
    #   user_id the branch login cannot "see" - so a branch user saw only a
    #   subset while an admin saw all.
    #
    #   This API returns employees driven PURELY by Employee.branch, using raw
    #   SQL (frappe.db.sql), which does NOT apply user-permission filtering.
    #   Branch access is still enforced below, so a branch user still cannot pull
    #   another branch's staff.
    #
    # safe_exec safe: no f-strings, no imports, no tuple unpacking,
    #                 no augmented dict assignment, no frappe.get_roles().
    # ============================================================================

    branch = frappe.form_dict.get("branch")
    if not branch:
        frappe.throw("branch required")

    # --- Branch access check (keeps the branch boundary intact) ----------------
    is_sysmgr = frappe.db.exists("Has Role",
        {"parent": frappe.session.user, "role": "System Manager"})

    if not is_sysmgr:
        allowed = [d.for_value for d in frappe.get_all("User Permission",
            filters={"user": frappe.session.user, "allow": "Branch"},
            fields=["for_value"])]
        # If the user has Branch permissions at all, the requested branch must be
        # one of them. If they have none, they are unrestricted on Branch and may
        # pull any branch (same rule the main dashboard API uses).
        if allowed and branch not in allowed:
            frappe.throw("Not permitted for this branch")

    # --- Employee list, driven only by Employee.branch -------------------------
    # Raw SQL bypasses the user_id-based user-permission filter on purpose.
    rows = _read_sql("""
    SELECT
        name,
        employee_name,
        designation,
        company,
        department,
        branch
    FROM `tabEmployee`
    WHERE branch = %(b)s
      AND status = 'Active'
    ORDER BY department ASC, employee_name ASC
""", {"b": branch}, as_dict=True)

    frappe.response["message"] = rows
