"""Machinery Request Approvals

Original API: life_get_machinery_requests
Source modified: 2026-08-12 14:40:18.994686
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
    # API Method: life_get_machinery_requests
    # Allow Guest: No
    # Disabled: No

    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Login is required.")

    approvers = [
        "bhuvan@lifescc.com",
        "surya@lifescc.com",
        "lokakavyareddy3@gmail.com"
    ]
    is_approver = user in approvers or user == "Administrator"

    allowed_branches = []
    permission_rows = frappe.db.get_all(
        "User Permission",
        filters={"user": user, "allow": "Branch"},
        fields=["for_value"],
        limit_page_length=500
    )
    for permission_row in permission_rows:
        branch_value = permission_row.get("for_value")
        if branch_value and branch_value not in allowed_branches:
            allowed_branches.append(branch_value)

    employee_rows = frappe.db.get_all(
        "Employee",
        filters={"user_id": user, "status": "Active"},
        fields=["branch"],
        limit_page_length=20
    )
    for employee_row in employee_rows:
        branch_value = employee_row.get("branch")
        if branch_value and branch_value not in allowed_branches:
            allowed_branches.append(branch_value)

    action = (frappe.form_dict.get("action") or "").strip()
    request_name = (frappe.form_dict.get("request_name") or "").strip()

    request_fields = [
        "name", "naming_series", "requesting_branch", "requested_by",
        "custom_requested_by_name", "request_date", "required_by", "priority",
        "requested_item", "asset_category", "machinery_category", "quantity",
        "requirement_reason", "additional_remarks", "preferred_source_branch",
        "allocated_source_branch", "allocated_asset", "source_warehouse",
        "target_warehouse", "machinery_transfer", "request_status",
        "rejection_reason", "sales_manager_approved_by", "sales_manager_approved_on",
        "stock_manager_approved_by", "stock_manager_approved_on", "approved_by",
        "approved_on", "rejected_by", "rejected_on", "creation", "modified",
        "owner", "modified_by", "docstatus"
    ]

    doctype_fields = frappe.db.get_all(
        "DocField",
        filters={"parent": "Machinery Request", "parenttype": "DocType"},
        fields=["fieldname"],
        limit_page_length=1000
    )
    custom_fields = frappe.db.get_all(
        "Custom Field",
        filters={"dt": "Machinery Request"},
        fields=["fieldname"],
        limit_page_length=1000
    )
    available_fields = ["name", "creation", "modified", "owner", "modified_by", "docstatus", "idx"]
    for field_row in doctype_fields + custom_fields:
        fieldname = field_row.get("fieldname")
        if fieldname and fieldname not in available_fields:
            available_fields.append(fieldname)
    fields = []
    for fieldname in request_fields:
        if fieldname in available_fields:
            fields.append(fieldname)

    if action in ["approve", "reject"]:
        if not is_approver:
            frappe.throw("Only Bhuvan, Surya or Lokakavyareddy can approve or reject a Machinery Request.")
        if not request_name:
            frappe.throw("Machinery Request ID is required.")
        request_row = frappe.db.get_value("Machinery Request", request_name, fields, as_dict=1)
        if not request_row:
            frappe.throw("Machinery Request was not found.")
        current_status = request_row.get("request_status") or ""
        if current_status in ["Transfer Created", "Completed", "Rejected"]:
            frappe.throw("This Machinery Request cannot be changed from " + current_status + ".")

        if action == "approve":
            source_branch = request_row.get("preferred_source_branch") or request_row.get("allocated_source_branch") or ""
            updates = {
                "request_status": "Approved",
                "allocated_source_branch": source_branch,
                "approved_by": user,
                "approved_on": frappe.utils.now()
            }
        else:
            rejection_reason = (frappe.form_dict.get("rejection_reason") or "").strip()
            if not rejection_reason:
                frappe.throw("Rejection reason is required.")
            updates = {
                "request_status": "Rejected",
                "rejection_reason": rejection_reason,
                "rejected_by": user,
                "rejected_on": frappe.utils.now()
            }
        safe_updates = {}
        for fieldname in updates:
            if fieldname in available_fields:
                safe_updates[fieldname] = updates[fieldname]
        frappe.db.set_value("Machinery Request", request_name, safe_updates, update_modified=True)
        frappe.response["message"] = frappe.db.get_value("Machinery Request", request_name, fields, as_dict=1)

    elif action == "save_source_allocation":
        if not request_name:
            frappe.throw("Machinery Request ID is required.")
        request_row = frappe.db.get_value("Machinery Request", request_name, fields, as_dict=1)
        if not request_row:
            frappe.throw("Machinery Request was not found.")
        allocated_source_branch = (frappe.form_dict.get("allocated_source_branch") or "").strip()
        source_access = allocated_source_branch in allowed_branches
        if not is_approver and not source_access:
            frappe.throw("Only an authorised approver or the allocated Source Branch can save this allocation.")
        if request_row.get("request_status") not in ["Approved", "Asset Allocated"]:
            frappe.throw("The Machinery Request must be approved before allocation.")
        allocated_asset = (frappe.form_dict.get("allocated_asset") or "").strip()
        source_warehouse = (frappe.form_dict.get("source_warehouse") or "").strip()
        target_warehouse = (frappe.form_dict.get("target_warehouse") or "").strip()
        if not allocated_source_branch or not allocated_asset or not source_warehouse or not target_warehouse:
            frappe.throw("Source Branch, exact Machinery Asset, Source Warehouse and Target Warehouse are required.")
        if frappe.db.get_value("Asset", allocated_asset, "asset_category") != "Machinery":
            frappe.throw("Only an Asset from Asset Category Machinery can be allocated.")
        frappe.db.set_value("Machinery Request", request_name, {
            "request_status": "Asset Allocated",
            "allocated_source_branch": allocated_source_branch,
            "allocated_asset": allocated_asset,
            "source_warehouse": source_warehouse,
            "target_warehouse": target_warehouse
        }, update_modified=True)
        frappe.response["message"] = frappe.db.get_value("Machinery Request", request_name, fields, as_dict=1)

    else:
        rows = frappe.db.get_all(
            "Machinery Request",
            filters={"docstatus": ["!=", 2]},
            fields=fields,
            order_by="modified desc",
            limit_page_length=5000
        )
        visible_rows = []
        for row in rows:
            requesting_access = row.get("requesting_branch") in allowed_branches
            source_status = row.get("request_status") in ["Approved", "Asset Allocated", "Transfer Created", "Completed"]
            source_access = source_status and row.get("allocated_source_branch") in allowed_branches
            pending_for_approver = is_approver and row.get("request_status") not in ["Completed", "Rejected"]
            if requesting_access or source_access or pending_for_approver:
                visible_rows.append(row)
        if request_name:
            selected = None
            for row in visible_rows:
                if row.get("name") == request_name:
                    selected = row
                    break
            if not selected:
                frappe.throw("You are not permitted to view this Machinery Request.")
            frappe.response["message"] = selected
        else:
            frappe.response["message"] = visible_rows
