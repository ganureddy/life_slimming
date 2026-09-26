"""Machinery request create Permission

Original API: life_create_machinery_request
Source modified: 2026-08-12 15:27:54.412458
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
    # API Method: life_create_machinery_request
    # Allow Guest: No
    #
    # This API does NOT bypass permissions. Give the Chanda Nagar branch role
    # Select, Read and Create permission on Machinery Request in Role Permission
    # Manager. The API returns a clean message instead of a frappe.client.insert
    # permission traceback when Create permission is missing.

    user = frappe.session.user

    if not user or user == "Guest":
        frappe.response["message"] = {
            "ok": False,
            "message": "Please log in to raise a Machinery Request."
        }
    else:
        requesting_branch = frappe.form_dict.get("requesting_branch")
        preferred_source_branch = frappe.form_dict.get("preferred_source_branch")
        source_warehouse = frappe.form_dict.get("source_warehouse")
        allocated_asset = frappe.form_dict.get("allocated_asset")
        request_date = frappe.form_dict.get("request_date")
        required_by = frappe.form_dict.get("required_by")
        requested_by = frappe.form_dict.get("requested_by")
        requested_by_name = frappe.form_dict.get("requested_by_name")
        priority = frappe.form_dict.get("priority")
        requested_item = frappe.form_dict.get("requested_item")
        asset_category = frappe.form_dict.get("asset_category") or "Machinery"
        machinery_category = frappe.form_dict.get("machinery_category")
        quantity = frappe.form_dict.get("quantity") or 1
        requirement_reason = frappe.form_dict.get("requirement_reason")
        additional_remarks = frappe.form_dict.get("additional_remarks")

        if not requested_by or requested_by == "__CURRENT_USER__":
            current_employee = frappe.db.get_value(
                "Employee",
                {"user_id": user, "status": "Active"},
                ["name", "employee_name"],
                as_dict=1
            )
            if current_employee:
                requested_by = current_employee.get("name")
                requested_by_name = current_employee.get("employee_name") or requested_by

        if not requesting_branch or not preferred_source_branch or not source_warehouse or not allocated_asset or not required_by or not requested_by or not requested_item or not requirement_reason:
            frappe.response["message"] = {
                "ok": False,
                "message": "Requesting branch, source branch, source warehouse, machinery, requested by, required date and reason are required."
            }
        else:
            doc = frappe.get_doc({
                "doctype": "Machinery Request",
                "naming_series": "MREQ-.YYYY.-.#####",
                "requesting_branch": requesting_branch,
                "preferred_source_branch": preferred_source_branch,
                "source_warehouse": source_warehouse,
                "allocated_asset": allocated_asset,
                "request_date": request_date,
                "required_by": required_by,
                "requested_by": requested_by,
                "custom_requested_by_name": requested_by_name,
                "priority": priority,
                "requested_item": requested_item,
                "asset_category": asset_category,
                "machinery_category": machinery_category,
                "quantity": quantity,
                "requirement_reason": requirement_reason,
                "additional_remarks": additional_remarks,
                "request_status": "Pending Approval"
            })

            # doc.insert() performs ERPNext's normal Create permission check.
            # No ignore_permissions flag is used.
            doc.insert()

            # Notify only the three authorised Machinery Request approvers. The
            # email opens the dashboard Approvals Desk; it does not grant broad
            # Branch access or expose unrelated branch records.
            approval_recipients = [
                "bhuvan@lifescc.com",
                "surya@lifescc.com",
                "lokakavyareddy3@gmail.com"
            ]
            dashboard_link = frappe.utils.get_url("/asset-master?open=approvals&request=" + doc.name)
            frappe.sendmail(
                recipients=approval_recipients,
                subject="Machinery Request Approval Required · " + doc.name,
                message=(
                    "<p>A new Machinery Request requires your approval.</p>"
                    "<p><b>Request:</b> " + doc.name + "<br>"
                    "<b>Requesting Branch:</b> " + (doc.requesting_branch or "-") + "<br>"
                    "<b>Requested Item:</b> " + (doc.requested_item or "-") + "<br>"
                    "<b>Required By:</b> " + str(doc.required_by or "-") + "<br>"
                    "<b>Priority:</b> " + (doc.priority or "-") + "</p>"
                    "<p><a href='" + dashboard_link + "' style='background:#1e5b35;color:#fff;padding:10px 16px;text-decoration:none;border-radius:5px'>Open Approval Dashboard</a></p>"
                ),
                reference_doctype="Machinery Request",
                reference_name=doc.name,
                now=True
            )

            frappe.response["message"] = {
                "ok": True,
                "doc": {
                    "name": doc.name,
                    "request_status": doc.request_status
                }
            }
