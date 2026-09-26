"""Machinery Request and Transfer flow

Original API: life_get_machinery_transfers
Source modified: 2026-08-13 11:47:30.893658
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
    # API Method: life_get_machinery_transfers
    # Allow Guest: No
    # Disabled: No

    if frappe.session.user == "Guest":
        frappe.throw("Login is required.")

    user = frappe.session.user
    role_rows = frappe.db.get_all(
        "Has Role",
        filters={"parent": user, "parenttype": "User"},
        fields=["role"],
        limit_page_length=500
    )
    roles = []
    for role_row in role_rows:
        if role_row.get("role"):
            roles.append(role_row.get("role"))

    global_access = user == "Administrator" or "System Manager" in roles or "Stock Manager" in roles or "Sales Manager" in roles

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

    action = frappe.form_dict.get("action")

    # frappe.db.has_column is not exposed inside Frappe v15 Server Script safe_exec.
    # Check the DocType metadata records instead.
    workflow_state_exists = bool(
        frappe.db.get_value("DocField", {"parent": "Machinery Transfer", "fieldname": "workflow_state"}, "name") or
        frappe.db.get_value("Custom Field", {"dt": "Machinery Transfer", "fieldname": "workflow_state"}, "name")
    )
    transfer_status_exists = bool(
        frappe.db.get_value("DocField", {"parent": "Machinery Transfer", "fieldname": "transfer_status"}, "name") or
        frappe.db.get_value("Custom Field", {"dt": "Machinery Transfer", "fieldname": "transfer_status"}, "name")
    )

    if action == "create_from_request":
        request_name = frappe.form_dict.get("request_name")
        if not request_name:
            frappe.throw("Machinery Request and transfer data are required.")

        request_row = frappe.db.get_value(
            "Machinery Request",
            request_name,
            ["name", "request_status", "requesting_branch", "requested_by", "required_by",
             "requirement_reason", "additional_remarks", "allocated_source_branch",
             "allocated_asset", "source_warehouse", "target_warehouse", "quantity",
             "machinery_transfer"],
            as_dict=1
        )
        if not request_row:
            frappe.throw("Machinery Request was not found.")
        if request_row.get("request_status") not in ["Approved", "Asset Allocated"]:
            frappe.throw("This Machinery Request is not ready for transfer.")
        if request_row.get("machinery_transfer"):
            frappe.throw("A Machinery Transfer is already linked to this request.")
        if request_row.get("allocated_source_branch") not in allowed_branches and not global_access:
            frappe.throw("Only the allocated source branch can create this Machinery Transfer.")

        requested_by = frappe.form_dict.get("requested_by")
        request_date_and_time = frappe.form_dict.get("request_date_and_time")
        transfer_reason = frappe.form_dict.get("transfer_reason")
        remarks = frappe.form_dict.get("remarks")
        target_warehouse = frappe.form_dict.get("target_warehouse")
        condition_before_transfer = frappe.form_dict.get("condition_before_transfer")
        final_confirmation = frappe.form_dict.get("final_confirmation")
        protocol = frappe.form_dict.get("pre_shipping_and_packaging_protocol")
        if not requested_by or not transfer_reason or not target_warehouse or not condition_before_transfer:
            frappe.throw("Requested By, Transfer Reason, Target Warehouse and Condition Before Transfer are required.")
        if not target_warehouse:
            frappe.throw("Target Warehouse is required.")
        if request_row.get("target_warehouse") and target_warehouse != request_row.get("target_warehouse"):
            frappe.throw("Target Warehouse does not match the approved request.")

        asset_category = frappe.db.get_value("Asset", request_row.get("allocated_asset"), "asset_category")
        if asset_category != "Machinery":
            frappe.throw("Only an Asset from Asset Category Machinery can be transferred.")
        if str(final_confirmation) not in ["1", "True", "true"] or not protocol:
            frappe.throw("Complete the Pre-Shipping & Packaging Protocol before submitting.")

        asset_details = frappe.db.get_value(
            "Asset", request_row.get("allocated_asset"),
            ["asset_name", "item_name"],
            as_dict=1
        )
        transfer_data = {
            "doctype": "Machinery Transfer",
            "naming_series": "MAT-TRF-.YYYY.-.#####",
            "source_branch": request_row.get("allocated_source_branch"),
            "target_branch": request_row.get("requesting_branch"),
            "request_date_and_time": request_date_and_time,
            "required_by": request_row.get("required_by"),
            "transfer_reason": transfer_reason,
            "requested_by": requested_by,
            "source_warehouse": request_row.get("source_warehouse"),
            "target_warehouse": target_warehouse,
            "remarks": remarks,
            "pre_shipping_and_packaging_protocol": protocol,
            "bubble_wrap_verified": frappe.form_dict.get("bubble_wrap_verified"),
            "bubble_wrap_na": frappe.form_dict.get("bubble_wrap_na"),
            "total_wrap_layers": frappe.form_dict.get("total_wrap_layers"),
            "shipping_box_verified": frappe.form_dict.get("shipping_box_verified"),
            "shipping_box_na": frappe.form_dict.get("shipping_box_na"),
            "box_serial_no": frappe.form_dict.get("box_serial_no"),
            "all_items_accounted": frappe.form_dict.get("all_items_accounted"),
            "items_missing": frappe.form_dict.get("items_missing"),
            "items_qty_packed": frappe.form_dict.get("items_qty_packed"),
            "final_confirmation": final_confirmation,
            "machinery": [{
                "asset": request_row.get("allocated_asset"),
                "asset_name": (asset_details.get("asset_name") or asset_details.get("item_name") or "") if asset_details else "",
                "quantity": request_row.get("quantity") or 1,
                "condition_before_transfer": condition_before_transfer
            }]
        }
        transfer_doc = frappe.get_doc(transfer_data)
        transfer_doc.flags.ignore_permissions = True
        transfer_doc.insert(ignore_permissions=True)

        # Do not create DocShare rows here. Frappe requires the submitting branch
        # user to hold broad Role Permission "Share", which is intentionally not
        # granted. Dashboard access remains limited below to records whose source
        # or target branch belongs to the logged-in user's permitted branches.

        transfer_updates = {}
        # Machinery Request approval is the only approval gate. Once the approved
        # request becomes a Machinery Transfer and the mandatory protocol is
        # confirmed, it is immediately Ready for Dispatch.
        if workflow_state_exists:
            transfer_updates["workflow_state"] = "Ready for Dispatch"
        if transfer_status_exists:
            transfer_updates["transfer_status"] = "Ready for Dispatch"
        if transfer_updates:
            frappe.db.set_value("Machinery Transfer", transfer_doc.name, transfer_updates)
            for update_key in transfer_updates:
                transfer_doc.set(update_key, transfer_updates[update_key])

        frappe.db.set_value("Machinery Request", request_name, {
            "request_status": "Transfer Created",
            "machinery_transfer": transfer_doc.name,
            "target_warehouse": target_warehouse
        })
        frappe.response["message"] = transfer_doc.as_dict()

    elif action == "apply_workflow":
        transfer_name = frappe.form_dict.get("transfer_name")
        workflow_action = frappe.form_dict.get("workflow_action")
        transfer_row = frappe.db.get_value(
            "Machinery Transfer", transfer_name,
            ["name", "source_branch", "target_branch", "workflow_state", "transfer_status"],
            as_dict=1
        )
        if not transfer_row:
            frappe.throw("Machinery Transfer was not found.")
        source_access = transfer_row.get("source_branch") in allowed_branches
        target_access = transfer_row.get("target_branch") in allowed_branches
        if workflow_action in ["Send for Approval", "Approve", "Reject"]:
            frappe.throw("Machinery Transfer approval is disabled. Approval is required only on the linked Machinery Request.")
        elif workflow_action in ["Dispatch Transfer", "Complete Transfer"]:
            if not source_access and not global_access:
                frappe.throw("Only the Source Branch can dispatch this machinery.")
            current_state = transfer_row.get("workflow_state") or transfer_row.get("transfer_status")
            if current_state not in ["Ready for Dispatch", "Approved"]:
                frappe.throw("Complete the Pre-Shipping & Packaging Protocol and mark the transfer Ready for Dispatch before dispatching it.")
            next_state = "In Transit"
        elif workflow_action == "Confirm Received":
            if not target_access and not global_access:
                frappe.throw("Only the Target Branch can confirm receipt of this machinery.")
            current_state = transfer_row.get("workflow_state") or transfer_row.get("transfer_status")
            if current_state != "In Transit":
                frappe.throw("The machinery must be In Transit before receipt can be confirmed.")
            transfer_doc = frappe.get_doc("Machinery Transfer", transfer_name)
            target_branch = transfer_doc.target_branch
            target_location = frappe.db.get_value("Location", target_branch, "name")
            if not target_location:
                target_key = (target_branch or "").lower().replace(" ", "").replace("-", "").replace(".", "")
                location_rows = frappe.db.get_all("Location", fields=["name"], limit_page_length=1000)
                for location_row in location_rows:
                    location_name = location_row.get("name") or ""
                    location_key = location_name.lower().replace(" ", "").replace("-", "").replace(".", "")
                    if target_key and location_key == target_key:
                        target_location = location_name
                        break
            if not target_location:
                frappe.throw("A matching Asset Location was not found for Target Branch " + target_branch + ".")
            for machinery_row in transfer_doc.machinery:
                asset_category = frappe.db.get_value("Asset", machinery_row.asset, "asset_category")
                if asset_category != "Machinery":
                    frappe.throw("Only Machinery-category Assets can be completed in this transfer.")
                frappe.db.set_value("Asset", machinery_row.asset, "location", target_location)
            linked_requests = frappe.db.get_all(
                "Machinery Request",
                filters={"machinery_transfer": transfer_name},
                fields=["name"],
                limit_page_length=20
            )
            for linked_request in linked_requests:
                frappe.db.set_value("Machinery Request", linked_request.get("name"), "request_status", "Completed")
            next_state = "Completed"
        elif workflow_action == "Not Received":
            if not target_access and not global_access:
                frappe.throw("Only the Target Branch can report that machinery was not received.")
            current_state = transfer_row.get("workflow_state") or transfer_row.get("transfer_status")
            if current_state != "In Transit":
                frappe.throw("Only an In Transit transfer can be marked Not Received.")
            receipt_reason = (frappe.form_dict.get("receipt_reason") or "").strip()
            if not receipt_reason:
                frappe.throw("Not Received reason is required.")
            existing_remarks = frappe.db.get_value("Machinery Transfer", transfer_name, "remarks") or ""
            frappe.db.set_value(
                "Machinery Transfer",
                transfer_name,
                "remarks",
                existing_remarks + "\n\nTarget Branch Not Received: " + receipt_reason
            )
            next_state = "Not Received"
        else:
            frappe.throw("Unsupported workflow action.")

        workflow_updates = {}
        if workflow_state_exists:
            workflow_updates["workflow_state"] = next_state
        if transfer_status_exists:
            workflow_updates["transfer_status"] = next_state
        if workflow_updates:
            frappe.db.set_value("Machinery Transfer", transfer_name, workflow_updates)
        updated_doc = frappe.get_doc("Machinery Transfer", transfer_name)
        frappe.response["message"] = updated_doc.as_dict()

    else:

        requested_fields = [
        "name", "naming_series", "source_branch", "target_branch",
        "request_date_and_time", "required_by", "transfer_reason",
        "transfer_status", "workflow_state", "remarks", "requested_by",
        "source_warehouse", "target_warehouse",
        "pre_shipping_and_packaging_protocol", "bubble_wrap_verified",
        "bubble_wrap_na", "total_wrap_layers", "shipping_box_verified",
        "shipping_box_na", "box_serial_no", "all_items_accounted",
        "items_missing", "items_qty_packed", "final_confirmation",
        "creation", "modified", "owner", "modified_by", "docstatus"
    ]

        doctype_field_rows = frappe.db.get_all(
        "DocField",
        filters={"parent": "Machinery Transfer", "parenttype": "DocType"},
        fields=["fieldname"],
        limit_page_length=1000
    )
        custom_field_rows = frappe.db.get_all(
        "Custom Field",
        filters={"dt": "Machinery Transfer"},
        fields=["fieldname"],
        limit_page_length=1000
    )
        available_fields = ["name", "creation", "modified", "owner", "modified_by", "docstatus", "idx"]
        for field_row in doctype_field_rows:
            if field_row.get("fieldname") and field_row.get("fieldname") not in available_fields:
                available_fields.append(field_row.get("fieldname"))
        for field_row in custom_field_rows:
            if field_row.get("fieldname") and field_row.get("fieldname") not in available_fields:
                available_fields.append(field_row.get("fieldname"))

        fields = []
        for fieldname in requested_fields:
            if fieldname in available_fields:
                fields.append(fieldname)

        rows = frappe.db.get_all(
        "Machinery Transfer",
        filters={"docstatus": ["!=", 2]},
        fields=fields,
        order_by="modified desc",
        limit_page_length=5000
    )

        visible_rows = []
        employee_name_cache = {}
        for row in rows:
            permitted = global_access or row.get("source_branch") in allowed_branches or row.get("target_branch") in allowed_branches
            if permitted:
                employee_id = row.get("requested_by")
                if employee_id:
                    if employee_id not in employee_name_cache:
                        employee_name_cache[employee_id] = frappe.db.get_value("Employee", employee_id, "employee_name") or ""
                    row["requested_by_name"] = employee_name_cache.get(employee_id) or ""
                visible_rows.append(row)

        transfer_name = frappe.form_dict.get("transfer_name")
        if transfer_name:
            selected = None
            for row in visible_rows:
                if row.get("name") == transfer_name:
                    selected = row
                    break
            if not selected:
                frappe.throw("You are not permitted to view this Machinery Transfer.")
            transfer_doc = frappe.get_doc("Machinery Transfer", transfer_name)
            transfer_result = transfer_doc.as_dict()
            employee_id = transfer_result.get("requested_by")
            transfer_result["requested_by_name"] = frappe.db.get_value("Employee", employee_id, "employee_name") if employee_id else ""
            frappe.response["message"] = transfer_result
        else:
            frappe.response["message"] = visible_rows
