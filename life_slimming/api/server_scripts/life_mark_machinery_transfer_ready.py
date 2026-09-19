"""Machinery Trasfer

Original API: life_mark_machinery_transfer_ready
Source modified: 2026-08-12 13:49:51.886571
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
    # ERPNext Server Script
    # Script Type: API
    # API Method: life_mark_machinery_transfer_ready
    # Allow Guest: No
    #
    # Install this together with dashboard V105. It removes the obsolete transfer
    # approval position after create_from_request and moves the transfer directly
    # to Ready for Dispatch. Machinery Request approval remains unchanged.

    user = frappe.session.user
    transfer_name = frappe.form_dict.get("transfer_name")

    if not user or user == "Guest":
        frappe.throw("Please log in to update a Machinery Transfer.")

    if not transfer_name:
        frappe.throw("Machinery Transfer ID is required.")

    transfer = frappe.get_doc("Machinery Transfer", transfer_name)

    # Route-level authorization is intentionally narrower than broad Branch User
    # Permission. Only an active user belonging to the exact Source Branch, or an
    # authorised manager, can perform this action. Target and unrelated branches
    # cannot update the transfer. No ignore_permissions flag is used.
    roles = []
    role_rows = frappe.db.get_all(
        "Has Role",
        filters={"parent": user, "parenttype": "User"},
        fields=["role"],
        limit_page_length=500
    )
    for role_row in role_rows:
        role_name = role_row.get("role")
        if role_name and role_name not in roles:
            roles.append(role_name)

    manager_access = (
        user == "Administrator" or
        "System Manager" in roles or
        "Stock Manager" in roles or
        "Sales Manager" in roles
    )

    user_branches = []
    employee_rows = frappe.db.get_all(
        "Employee",
        filters={"user_id": user, "status": "Active"},
        fields=["branch"],
        limit_page_length=20
    )
    for employee_row in employee_rows:
        branch_value = employee_row.get("branch")
        if branch_value and branch_value not in user_branches:
            user_branches.append(branch_value)

    permission_rows = frappe.db.get_all(
        "User Permission",
        filters={"user": user, "allow": "Branch"},
        fields=["for_value"],
        limit_page_length=500
    )
    for permission_row in permission_rows:
        branch_value = permission_row.get("for_value")
        if branch_value and branch_value not in user_branches:
            user_branches.append(branch_value)

    source_access = transfer.get("source_branch") in user_branches
    if not source_access and not manager_access:
        frappe.throw("Only the Source Branch or an authorised manager can mark this Machinery Transfer Ready for Dispatch.")

    current_position = transfer.get("transfer_status") or transfer.get("workflow_state") or ""

    if current_position in ["Dispatched", "In Transit", "Received", "Installation Pending", "Installed & Tested", "Completed", "Rejected", "Cancelled"]:
        frappe.throw("This Machinery Transfer cannot be moved back to Ready for Dispatch from " + current_position + ".")

    # Update both fields in one database operation. This intentionally avoids an
    # invalid intermediate state such as Pending Stock Manager Approval, which is
    # no longer part of the configured Workflow.
    frappe.db.set_value(
        "Machinery Transfer",
        transfer_name,
        {
            "transfer_status": "Ready for Dispatch",
            "workflow_state": "Ready for Dispatch"
        },
        update_modified=True
    )

    frappe.response["message"] = {
        "name": transfer_name,
        "transfer_status": "Ready for Dispatch",
        "workflow_state": "Ready for Dispatch"
    }
