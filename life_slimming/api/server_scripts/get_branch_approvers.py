"""get_branch_approvers

Original API: get_branch_approvers
Source modified: 2026-09-04 18:49:43.096760
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
    # invoice_name = frappe.form_dict.get("invoice_name")
    # current_user = frappe.session.user

    # # Build blocked set from prior DARs
    # blocked = set()
    # approved_count = 0

    # if invoice_name:
    #     all_dars = frappe.get_all(
    #         "Discount Approval Request",
    #         filters={
    #             "linked_invoice": invoice_name,
    #             "status": ["in", ["Pending", "Approved"]]
    #         },
    #         fields=["selected_approver", "approved_by", "status", "approval_level"],
    #         ignore_permissions=True
    #     )

    #     for dar in all_dars:
    #         if dar.get("selected_approver"):
    #             blocked.add(dar["selected_approver"])
    #         if dar.get("approved_by"):
    #             blocked.add(dar["approved_by"])
    #         if dar.get("status") == "Approved":
    #             approved_count += 1

    # # Check how much discount is already approved
    # already_approved_pct = 0.0
    # if invoice_name:
    #     inv_pct = frappe.db.get_value("Sales Invoice", invoice_name, "total_approver_discount_pct")
    #     already_approved_pct = float(inv_pct or 0)

    # # Check if L3 already approved — no more escalation needed
    # l3_approved = False
    # if invoice_name:
    #     l3_dar = frappe.db.exists("Discount Approval Request", {
    #         "linked_invoice": invoice_name,
    #         "status": "Approved",
    #         "approval_level": "L3"
    #     })
    #     if l3_dar:
    #         l3_approved = True

    # # If L3 already approved → no more approvers needed
    # if l3_approved:
    #     frappe.response["message"] = []

    # else:
    #     # Fetch all approvers from master
    #     all_managers = frappe.get_all(
    #         "Discount Approver Master",
    #         fields=["user", "full_name", "approval_level", "designation"],
    #         ignore_permissions=True
    #     )

    #     result = []
    #     current_user_in_master = False

    #     for m in all_managers:
    #         user = m.get("user")
    #         if user in blocked:
    #             continue

    #         level = m.get("approval_level") or "L1"

    #         # If 3 approvals done OR 15% used → only L3 allowed
    #         if (approved_count >= 3 or already_approved_pct >= 15) and level != "L3":
    #             continue

    #         if user == current_user:
    #             current_user_in_master = True
    #             if level != "L3":
    #                 m["full_name"] = (m.get("full_name") or user) + " (Self - 5% Max)"
    #                 m["approval_level"] = "L1"
    #             result.insert(0, m)
    #         else:
    #             result.append(m)

    #     # Add self-approval only if < 15% used and < 3 approvals done
    #     if not current_user_in_master and current_user not in blocked and already_approved_pct < 15 and approved_count < 3:
    #         user_full_name = frappe.db.get_value("User", current_user, "full_name") or current_user
    #         result.insert(0, {
    #             "user": current_user,
    #             "full_name": user_full_name + " (Self - 5% Max)",
    #             "approval_level": "L1",
    #             "designation": "Self Approval"
    #         })

    #     frappe.response["message"] = result






    # invoice_name = frappe.form_dict.get("invoice_name")
    # current_user = frappe.session.user

    # # Build blocked set from prior DARs
    # blocked = set()
    # approved_count = 0

    # if invoice_name:
    #     all_dars = frappe.get_all(
    #         "Discount Approval Request",
    #         filters={
    #             "linked_invoice": invoice_name,
    #             "status": ["in", ["Pending", "Approved"]]
    #         },
    #         fields=["selected_approver", "approved_by", "status", "approval_level"],
    #         ignore_permissions=True
    #     )

    #     for dar in all_dars:
    #         if dar.get("selected_approver"):
    #             blocked.add(dar["selected_approver"])
    #         if dar.get("approved_by"):
    #             blocked.add(dar["approved_by"])
    #         if dar.get("status") == "Approved":
    #             approved_count += 1

    # # Check how much discount is already approved
    # already_approved_pct = 0.0
    # if invoice_name:
    #     inv_pct = frappe.db.get_value("Sales Invoice", invoice_name, "total_approver_discount_pct")
    #     already_approved_pct = float(inv_pct or 0)

    # # Check if L4 (MD / unlimited) already approved -- no more escalation needed
    # l4_approved = False
    # if invoice_name:
    #     l4_dar = frappe.db.exists("Discount Approval Request", {
    #         "linked_invoice": invoice_name,
    #         "status": "Approved",
    #         "approval_level": "L4"
    #     })
    #     if l4_dar:
    #         l4_approved = True

    # # If L4 already approved -> no more approvers needed
    # if l4_approved:
    #     frappe.response["message"] = []

    # else:
    #     # Fetch all approvers from master
    #     all_managers = frappe.get_all(
    #         "Discount Approver Master",
    #         fields=["user", "full_name", "approval_level", "designation"],
    #         ignore_permissions=True
    #     )

    #     result = []
    #     current_user_in_master = False

    #     for m in all_managers:
    #         user = m.get("user")
    #         if user in blocked:
    #             continue

    #         level = m.get("approval_level") or "L1"

    #         # If 3 cascading approvals (L1+L2+L3) done OR 15% used -> only L4 allowed
    #         if (approved_count >= 3 or already_approved_pct >= 15) and level != "L4":
    #             continue

    #         if user == current_user:
    #             current_user_in_master = True
    #             if level != "L4":
    #                 m["full_name"] = (m.get("full_name") or user) + " (Self - 5% Max)"
    #                 m["approval_level"] = "L1"
    #             result.insert(0, m)
    #         else:
    #             result.append(m)

    #     # Add self-approval only if < 15% used and < 3 approvals done
    #     if not current_user_in_master and current_user not in blocked and already_approved_pct < 15 and approved_count < 3:
    #         user_full_name = frappe.db.get_value("User", current_user, "full_name") or current_user
    #         result.insert(0, {
    #             "user": current_user,
    #             "full_name": user_full_name + " (Self - 5% Max)",
    #             "approval_level": "L1",
    #             "designation": "Self Approval"
    #         })

    #     frappe.response["message"] = result








    invoice_name = frappe.form_dict.get("invoice_name")
    current_user = frappe.session.user

    # Users already used for this invoice
    blocked = set()
    approved_count = 0

    if invoice_name:
        approval_requests = frappe.get_all(
            "Discount Approval Request",
            filters={
                "linked_invoice": invoice_name,
                "status": ["in", ["Pending", "Approved"]]
            },
            fields=[
                "selected_approver",
                "approved_by",
                "status",
                "approval_level"
            ],
            ignore_permissions=True
        )

        for approval_request in approval_requests:
            selected_approver = approval_request.get("selected_approver")
            approved_by = approval_request.get("approved_by")

            if selected_approver:
                blocked.add(selected_approver)

            if approved_by:
                blocked.add(approved_by)

            if approval_request.get("status") == "Approved":
                approved_count += 1


    # Get already-approved discount percentage
    already_approved_pct = 0.0

    if invoice_name:
        approved_percentage = frappe.db.get_value(
            "Sales Invoice",
            invoice_name,
            "total_approver_discount_pct"
        )

        already_approved_pct = float(approved_percentage or 0)


    # Check whether L4 approval is already completed
    l4_approved = False

    if invoice_name:
        l4_request = frappe.db.exists(
            "Discount Approval Request",
            {
                "linked_invoice": invoice_name,
                "status": "Approved",
                "approval_level": "L4"
            }
        )

        if l4_request:
            l4_approved = True


    # No further approvers after L4 approval
    if l4_approved:
        frappe.response["message"] = []

    else:
        # IMPORTANT:
        # Only approvers with Is Active checked will be fetched
        active_approvers = frappe.get_all(
            "Discount Approver Master",
            filters={
                "is_active": 1
            },
            fields=[
                "user",
                "full_name",
                "approval_level",
                "designation",
                "email",
                "monthly_ceiling",
                "is_active"
            ],
            order_by="approval_level asc, full_name asc",
            ignore_permissions=True
        )

        result = []

        for approver in active_approvers:
            user = approver.get("user")

            # Skip invalid master rows
            if not user:
                continue

            # Skip approvers already used for this invoice
            if user in blocked:
                continue

            approval_level = approver.get("approval_level") or "L1"

            # After 3 approvals or 15% total discount,
            # show only L4 approvers
            if (
                approved_count >= 3
                or already_approved_pct >= 15
            ) and approval_level != "L4":
                continue

            # Current active approver can self-approve as L1,
            # except when configured as L4
            if user == current_user:
                if approval_level != "L4":
                    approver["full_name"] = (
                        approver.get("full_name") or user
                    ) + " (Self - 5% Max)"

                    approver["approval_level"] = "L1"

                result.insert(0, approver)

            else:
                result.append(approver)

        frappe.response["message"] = result
