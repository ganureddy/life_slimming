"""User check for Approvals Report

Original API: life_approval_report_user_context
Source modified: 2026-08-17 14:35:46.465633
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
    # ================================================================
    # Server Script Type : API
    # API Method         : life_approval_report_user_context
    # Allow Guest        : OFF
    # Purpose            : Secure logged-in user context for Website report
    # ================================================================

    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Please login to access the Approvals Report.")

    roles = []
    role_rows = frappe.get_all(
        "Has Role",
        filters={
            "parent": user,
            "parenttype": "User"
        },
        fields=["role"],
        limit_page_length=500
    )

    for row in role_rows:
        role = row.get("role")
        if role and role not in roles:
            roles.append(role)

    if user == "Administrator" and "System Manager" not in roles:
        roles.append("System Manager")

    branch_permissions = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Branch"
        },
        fields=[
            "for_value",
            "is_default",
            "applicable_for",
            "hide_descendants"
        ],
        order_by="is_default desc, creation asc",
        limit_page_length=500
    )

    employee_rows = frappe.get_all(
        "Employee",
        filters={
            "user_id": user,
            "status": "Active"
        },
        fields=[
            "name",
            "employee_name",
            "user_id",
            "designation",
            "branch"
        ],
        order_by="modified desc",
        limit_page_length=1
    )

    employee = employee_rows[0] if employee_rows else None

    user_info = {
        "name": user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
        "role_profile_name": frappe.db.get_value("User", user, "role_profile_name") or "",
        "module_profile": frappe.db.get_value("User", user, "module_profile") or ""
    }

    frappe.response["message"] = {
        "user": user,
        "roles": roles,
        "is_elevated": 1 if (user == "Administrator" or "System Manager" in roles) else 0,
        "user_info": user_info,
        "employee": employee,
        "branch_permissions": branch_permissions
    }
