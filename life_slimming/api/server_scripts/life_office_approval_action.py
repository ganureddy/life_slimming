"""LIFE Office Approval Action

Original API: life_office_approval_action
Source modified: 2026-09-17 20:31:58.578000
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
    # LIFE Office approval action
    # Authenticated API. Guest access is disabled.
    # Testers are added later through the controlled activation installer.

    INTEGRATION_USER = "lifeoffice@lifescc.com"

    # Intentionally empty during foundation installation.
    # No live approval can be processed until exact ERP login emails are added.
    TESTER_EMAILS = []

    ALLOWED_DOCTYPES = [
        "Discount Approval Request",
        "Client Package Conversion Client To Client",
        "LIFE Client Package Conversion Same Client Package To Package",
    ]

    OPS_USERS = [
        "kishore@lifescc.com",
        "viveka@lifescc.com",
        "audit@lifescc.com",
    ]

    COO_USERS = ["bhuvan@lifescc.com"]

    args = frappe.form_dict or {}
    session_user = str(frappe.session.user or "").strip().lower()

    if session_user != INTEGRATION_USER:
        frappe.throw("This method can only be called by the LIFE Office integration user.")

    if len(TESTER_EMAILS) == 0:
        frappe.throw("LIFE Office approval actions are not activated. No tester emails are configured.")

    request_name = str(args.get("request") or args.get("name") or "").strip()
    stage_seen = str(args.get("stage") or "").strip()
    action = str(args.get("action") or "").strip().lower()
    remarks = str(args.get("remarks") or "").strip()
    acted_by = str(args.get("acted_by") or "").strip().lower()
    requested_doctype = str(args.get("doctype") or "").strip()

    if not request_name:
        frappe.throw("request is required.")
    if not stage_seen:
        frappe.throw("stage is required.")
    if action not in ["approve", "reject"]:
        frappe.throw("action must be Approve or Reject.")
    if action == "reject" and not remarks:
        frappe.throw("remarks are required when rejecting.")
    if not acted_by:
        frappe.throw("acted_by is required.")
    if acted_by not in TESTER_EMAILS:
        frappe.throw("This ERP user is not enabled as a LIFE Office tester.")

    if not frappe.db.exists("User", {"name": acted_by, "enabled": 1}):
        frappe.throw("acted_by is not an enabled ERP User: " + acted_by)

    resolved_doctype = ""
    if requested_doctype:
        if requested_doctype not in ALLOWED_DOCTYPES:
            frappe.throw("Unsupported approval DocType: " + requested_doctype)
        if not frappe.db.exists(requested_doctype, request_name):
            frappe.throw("Approval request not found: " + request_name)
        resolved_doctype = requested_doctype
    else:
        matches = []
        for candidate_doctype in ALLOWED_DOCTYPES:
            if frappe.db.exists(candidate_doctype, request_name):
                matches.append(candidate_doctype)
        if len(matches) == 0:
            frappe.throw("Approval request not found: " + request_name)
        if len(matches) > 1:
            frappe.throw("Request ID is ambiguous; send doctype explicitly.")
        resolved_doctype = matches[0]

    doc = frappe.get_doc(resolved_doctype, request_name)
    now_value = frappe.utils.now()
    today_value = frappe.utils.today()
    actor_full_name = frappe.db.get_value("User", acted_by, "full_name") or acted_by
    actor_employee = frappe.db.get_value(
        "Employee",
        {"user_id": acted_by, "status": "Active"},
        "name",
    )

    current_stage = ""
    if resolved_doctype == "Discount Approval Request":
        current_stage = str(doc.get("approval_level") or "").strip()
    else:
        current_stage = str(doc.get("approval_stage") or "").strip()

    if stage_seen.lower() != current_stage.lower():
        frappe.throw(
            "Approval stage changed. LIFE Office showed '"
            + stage_seen
            + "' but ERP is now at '"
            + current_stage
            + "'. Refresh before acting."
        )

    already_done = 0
    if resolved_doctype == "Discount Approval Request":
        if str(doc.get("status") or "") != "Pending":
            already_done = 1
    else:
        if current_stage in ["Approved", "Rejected"]:
            already_done = 1
        if str(doc.get("final_approval_status") or "") in ["Approved", "Rejected"]:
            already_done = 1

    if already_done == 1:
        frappe.throw("This request has already been processed.")

    authorized = 0

    if resolved_doctype == "Discount Approval Request":
        selected_approver = str(doc.get("selected_approver") or "").strip().lower()
        if selected_approver and selected_approver == acted_by:
            authorized = 1
        master_match = frappe.db.exists(
            "Discount Approver Master",
            {
                "user": acted_by,
                "approval_level": current_stage,
                "is_active": 1,
            },
        )
        if master_match:
            authorized = 1

    elif resolved_doctype == "LIFE Client Package Conversion Same Client Package To Package":
        stage_lower = current_stage.lower()
        if "centre manager" in stage_lower or "center manager" in stage_lower:
            employee_match = frappe.db.exists(
                "Employee",
                {
                    "user_id": acted_by,
                    "status": "Active",
                    "branch": doc.get("branch"),
                    "designation": ["in", ["Center Manager", "Centre Manager", "Senior Manager", "ACM"]],
                },
            )
            if employee_match:
                authorized = 1
        elif "operations head" in stage_lower:
            if acted_by in OPS_USERS:
                authorized = 1
        elif "coo" in stage_lower or "management" in stage_lower:
            if acted_by in COO_USERS:
                authorized = 1

    elif resolved_doctype == "Client Package Conversion Client To Client":
        stage_lower = current_stage.lower()
        if "centre manager" in stage_lower or "center manager" in stage_lower:
            employee_match = frappe.db.exists(
                "Employee",
                {
                    "user_id": acted_by,
                    "status": "Active",
                    "branch": doc.get("branch"),
                    "designation": ["in", ["Center Manager", "Centre Manager", "Senior Manager", "ACM"]],
                },
            )
            if employee_match:
                authorized = 1
        elif "operations manager" in stage_lower or "audit team" in stage_lower:
            if acted_by in OPS_USERS:
                authorized = 1
        elif "operations coo" in stage_lower or "coo" in stage_lower:
            if acted_by in COO_USERS:
                authorized = 1

    if authorized != 1:
        frappe.throw("The acting ERP user is not authorized for the current approval stage.")

    old_stage = current_stage

    if resolved_doctype == "Discount Approval Request":
        doc.status = "Approved" if action == "approve" else "Rejected"
        doc.approved_by = acted_by
        doc.approved_at = now_value
        if action == "approve":
            doc.approved_final_amount = float(
                doc.get("proposed_final_amount")
                or doc.get("requested_final_amount")
                or 0
            )
            doc.approved_discount_pct = float(doc.get("requested_discount_pct") or 0)
            if remarks:
                doc.approver_note = remarks
        else:
            doc.rejection_reason = remarks

    elif resolved_doctype == "LIFE Client Package Conversion Same Client Package To Package":
        stage_lower = current_stage.lower()
        doc.flags.life_office_acted_by = acted_by
        if action == "reject":
            doc.final_approval_status = "Rejected"
            doc.approval_stage = "Rejected"
            doc.automation_status = "Skipped"
            if doc.meta.has_field("coo_management_remarks"):
                doc.coo_management_remarks = remarks
        elif "centre manager" in stage_lower or "center manager" in stage_lower:
            doc.approved_by_name = actor_full_name
            doc.approved_date = now_value
            doc.centre_manager_remarks = remarks
            doc.current_tab_step = 3
            doc.approval_stage = "Operations Head Approval Pending"
        elif "operations head" in stage_lower:
            doc.authorised_name = actor_full_name
            doc.authorised_date = now_value
            doc.operations_final_remarks = remarks
            doc.current_tab_step = 4
            doc.approval_stage = "COO / Management Approval Pending"
        else:
            doc.coo_management_name = actor_full_name
            doc.coo_management_date = now_value
            doc.coo_management_remarks = remarks
            doc.current_tab_step = 5
            doc.final_approval_status = "Approved"
            doc.approval_stage = "Approved"

    elif resolved_doctype == "Client Package Conversion Client To Client":
        stage_lower = current_stage.lower()
        if action == "reject":
            doc.final_approval_status = "Rejected"
            doc.approval_stage = "Rejected"
            doc.conversion_status = "Rejected"
            doc.automation_status = "Skipped"
            doc.rejected_by_name = actor_full_name
            doc.rejection_remarks = remarks
        elif "centre manager" in stage_lower or "center manager" in stage_lower:
            if not actor_employee:
                frappe.throw("The Centre Manager ERP User is not linked to an active Employee.")
            doc.centre_manager_name = actor_employee
            doc.centre_manager_date = today_value
            doc.centre_manager_decision = "Approved"
            doc.centre_manager_remarks = remarks
            doc.custom_centre_manager_action_datetime = now_value
            doc.current_tab_step = 2
            doc.approval_stage = "Operations Manager Approval Pending"
            doc.conversion_status = "Operations Manager Approval Pending"
        elif "operations manager" in stage_lower:
            if not actor_employee:
                frappe.throw("The Operations Manager ERP User is not linked to an active Employee.")
            doc.operations_manager_name = actor_employee
            doc.operations_manager_date = today_value
            doc.operations_manager_decision = "Approved"
            doc.operations_manager_remarks = remarks
            doc.current_tab_step = 3
            doc.approval_stage = "Audit Team Approval Pending"
            doc.conversion_status = "Audit Team Approval Pending"
        elif "audit team" in stage_lower:
            doc.audit_team__corporate_team_name = actor_full_name
            doc.audit_team__corporate_team_date = today_value
            doc.audit_team_decision = "Approved"
            doc.audit_team_remarks = remarks
            doc.custom_audit_team_action_datetime = now_value
            doc.current_tab_step = 3
            doc.approval_stage = "Operations COO Final Decision Pending"
            doc.conversion_status = "Operations COO Final Decision Pending"
        else:
            doc.operations_coo__management_name = actor_full_name
            doc.operations_coo__management_date = today_value
            doc.custom_coo_management_action_datetime = now_value
            doc.current_tab_step = 4
            doc.final_approval_status = "Approved"
            doc.approval_stage = "Approved"
            doc.conversion_status = "Approved"

    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)

    doc.add_comment(
        "Info",
        "LIFE Office "
        + action.title()
        + " by "
        + acted_by
        + ". Stage shown: "
        + old_stage
        + ". Remarks: "
        + (remarks or "None"),
    )

    frappe.response["message"] = {
        "ok": True,
        "request": doc.name,
        "doctype": resolved_doctype,
        "action": action.title(),
        "acted_by": acted_by,
        "previous_stage": old_stage,
        "current_stage": doc.get("approval_stage") or doc.get("approval_level") or "",
        "status": doc.get("status") or doc.get("final_approval_status") or "",
        "message": "Approval action processed by ERP.",
    }
