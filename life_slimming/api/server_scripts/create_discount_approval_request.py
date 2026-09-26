"""Discount approval test new billing

Original API: create_discount_approval_request
Source modified: 2026-09-03 06:23:47.946170
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
    invoice_name = frappe.form_dict.get("invoice_name")
    selected_approver = frappe.form_dict.get("selected_approver")
    approval_level = (frappe.form_dict.get("approval_level") or "L1").strip()
    requested_pct = frappe.utils.flt(frappe.form_dict.get("requested_discount_pct"), 2)
    requested_final = frappe.utils.flt(frappe.form_dict.get("requested_final_amount"), 2)
    reason = (frappe.form_dict.get("reason") or "").strip()

    if not invoice_name:
        frappe.throw("Sales Invoice is required.")
    if not selected_approver:
        frappe.throw("Select a discount approver.")
    if not reason:
        frappe.throw("Discount reason is required.")
    if approval_level not in ("L1", "L2", "L3", "L4"):
        frappe.throw("Invalid approval level.")

    inv = frappe.get_doc("Sales Invoice", invoice_name)
    if inv.docstatus != 0:
        frappe.throw("Discount can only be requested while the invoice is Draft.")

    if frappe.db.exists("Discount Approval Request", {
        "linked_invoice": invoice_name,
        "status": "Pending"
    }):
        frappe.throw("A discount request is already pending for this invoice.")

    if frappe.db.exists("Discount Approval Request", {
        "linked_invoice": invoice_name,
        "approval_level": approval_level,
        "status": "Approved"
    }):
        frappe.throw(approval_level + " has already approved this invoice.")

    # The first request permanently establishes the GST-inclusive calculation base.
    first_bill_total = frappe.db.get_value(
        "Discount Approval Request",
        {"linked_invoice": invoice_name},
        "bill_total",
        order_by="creation asc"
    )

    original_grand_total = frappe.utils.flt(first_bill_total, 2)
    if original_grand_total <= 0:
        original_grand_total = frappe.utils.flt(inv.grand_total, 2)
    if original_grand_total <= 0:
        frappe.throw("Original Grand Total including GST could not be identified.")

    current_grand_total = frappe.utils.flt(inv.grand_total, 2)

    approved_rows = frappe.get_all(
        "Discount Approval Request",
        filters={"linked_invoice": invoice_name, "status": "Approved"},
        fields=["approval_level", "approved_discount_pct", "requested_discount_pct"]
    )

    normal_pct_used = 0
    for row in approved_rows:
        if row.approval_level in ("L1", "L2", "L3"):
            row_pct = frappe.utils.flt(
                row.approved_discount_pct or row.requested_discount_pct,
                2
            )
            normal_pct_used += row_pct

    if approval_level == "L4":
        if requested_final <= 0:
            frappe.throw("Enter the exact L4 final amount including GST.")
        if requested_final >= current_grand_total:
            frappe.throw(
                "L4 final amount must be less than the current Grand Total including GST."
            )
        requested_pct = round(
            (original_grand_total - requested_final)
            / original_grand_total * 100,
            2
        )
    else:
        requested_final = 0
        if requested_pct <= 0:
            frappe.throw("Enter a discount percentage.")
        if requested_pct > 5:
            frappe.throw("One approval level can approve a maximum of 5%.")
        if normal_pct_used + requested_pct > 15:
            frappe.throw("L1 + L2 + L3 combined discount cannot exceed 15%.")

    if selected_approver == frappe.session.user and approval_level == "L4":
        frappe.throw("L4 cannot be self-approved.")

    req = frappe.new_doc("Discount Approval Request")
    req.linked_invoice = invoice_name
    req.requested_by = frappe.session.user
    req.selected_approver = selected_approver
    req.bill_total = original_grand_total
    req.branch = inv.get("branch") or ""
    req.reason = reason
    req.status = "Pending"
    req.approval_level = approval_level
    req.requested_discount_pct = requested_pct
    req.requested_final_amount = requested_final
    req.insert(ignore_permissions=True)

    inv.discount_locked = 1
    inv.approval_workflow_status = "Pending Approval"
    inv.after_approval_grand_total = 0
    inv.save(ignore_permissions=True)

    frappe.response["message"] = {
        "status": "success",
        "request": req.name,
        "invoice_name": invoice_name,
        "approval_level": approval_level,
        "original_grand_total": original_grand_total,
        "current_grand_total": current_grand_total,
        "requested_discount_pct": requested_pct,
        "requested_final_amount": requested_final
    }
