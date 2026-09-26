"""apply_invoice_discount_NET_FINAL_V2

Original API: apply_invoice_discount_NET_FINAL_V2
Source modified: 2026-09-07 23:10:20.010752
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
    # Server Script name: LIFE Apply Exact Discount Request v2
    # Type: API
    # API Method: apply_invoice_discount_NET_FINAL_V2
    # Allow Guest: No

    request_name_input = (frappe.form_dict.get("request_name") or "").strip()
    invoice_name = frappe.form_dict.get("invoice_name")
    approved_amount = frappe.utils.flt(
        frappe.form_dict.get("approved_amount"),
        2
    )
    approver = frappe.session.user


    # ============================================================
    # BASIC VALIDATION
    # ============================================================

    if not invoice_name:
        frappe.throw("Sales Invoice is required.")

    inv = frappe.get_doc(
        "Sales Invoice",
        invoice_name
    )

    if inv.docstatus != 0:
        frappe.throw(
            "Discount can only be approved while the invoice is Draft."
        )


    # ============================================================
    # FIND THE PENDING APPROVAL REQUEST
    # ============================================================

    if request_name_input:
        request_name = request_name_input
        req = frappe.get_doc("Discount Approval Request", request_name)
        if req.linked_invoice != invoice_name:
            frappe.throw("Approval request does not belong to this Sales Invoice.")
        if req.status != "Pending":
            frappe.throw("This Discount Approval Request is no longer Pending.")
    else:
        request_name = frappe.db.get_value(
            "Discount Approval Request",
            {"linked_invoice": invoice_name, "status": "Pending"},
            "name",
            order_by="creation asc"
        )
        if not request_name:
            frappe.throw("No pending Discount Approval Request was found.")
        req = frappe.get_doc("Discount Approval Request", request_name)

    level = req.approval_level or "L1"

    is_l4 = (
        level == "L4"
        or frappe.utils.flt(
            req.requested_final_amount,
            2
        ) > 0
    )


    # ============================================================
    # APPROVER VALIDATION
    # ============================================================

    GLOBAL_DISCOUNT_APPROVERS = (
        "Administrator",
        "bhuvan@lifescc.com",
        "narendhar@lifescc.com"
    )

    if approver not in GLOBAL_DISCOUNT_APPROVERS:
        if req.selected_approver != approver:
            frappe.throw(
                "You are not the selected approver."
            )

    if is_l4 and approver == req.requested_by:
        frappe.throw(
            "L4 cannot be self-approved."
        )


    # ============================================================
    # ORIGINAL GRAND TOTAL INCLUDING GST
    # ============================================================

    original_grand_total = frappe.utils.flt(
        req.bill_total,
        2
    )

    if original_grand_total <= 0:

        first_total = frappe.db.get_value(
            "Discount Approval Request",
            {
                "linked_invoice": invoice_name
            },
            "bill_total",
            order_by="creation asc"
        )

        original_grand_total = frappe.utils.flt(
            first_total,
            2
        )

    if original_grand_total <= 0:
        original_grand_total = frappe.utils.flt(
            inv.grand_total,
            2
        )

    if original_grand_total <= 0:
        frappe.throw(
            "Original Grand Total including GST could not be identified."
        )


    # ============================================================
    # GET PREVIOUS APPROVED L1/L2/L3 PERCENTAGES
    # ============================================================

    approved_rows = frappe.get_all(
        "Discount Approval Request",
        filters={
            "linked_invoice": invoice_name,
            "status": "Approved"
        },
        fields=[
            "approval_level",
            "approved_discount_pct",
            "requested_discount_pct"
        ],
        order_by="creation asc"
    )

    previous_normal_pct = 0

    for row in approved_rows:

        if row.approval_level in (
            "L1",
            "L2",
            "L3"
        ):

            row_pct = frappe.utils.flt(
                row.requested_discount_pct
                or row.approved_discount_pct,
                2
            )

            previous_normal_pct += row_pct

    previous_normal_pct = frappe.utils.flt(
        previous_normal_pct,
        2
    )


    # ============================================================
    # CALCULATE TARGET DISCOUNT
    # ============================================================

    if is_l4:

        this_pct = 0

        target_final = approved_amount

        if target_final <= 0:
            target_final = frappe.utils.flt(
                req.requested_final_amount,
                2
            )

        if target_final <= 0:
            frappe.throw(
                "Enter the exact L4 final amount including GST."
            )

        current_grand_total = frappe.utils.flt(
            inv.grand_total,
            2
        )

        if target_final >= current_grand_total:
            frappe.throw(
                "L4 final amount must be less than the current "
                "Grand Total ₹"
                + str(current_grand_total)
                + "."
            )

        if target_final >= original_grand_total:
            frappe.throw(
                "L4 final amount must be less than the original "
                "Grand Total ₹"
                + str(original_grand_total)
                + "."
            )

        discount_amount = frappe.utils.flt(
            original_grand_total - target_final,
            2
        )

        if discount_amount <= 0:
            frappe.throw(
                "Calculated L4 discount is invalid."
            )

        discount_pct = frappe.utils.flt(
            (
                discount_amount
                / original_grand_total
            ) * 100,
            4
        )

    else:

        this_pct = frappe.utils.flt(
            req.requested_discount_pct,
            2
        )

        if this_pct <= 0:
            frappe.throw(
                "Requested discount percentage is invalid."
            )

        if this_pct > 5:
            frappe.throw(
                "Each L1, L2 or L3 approval cannot exceed 5%."
            )

        discount_pct = frappe.utils.flt(
            previous_normal_pct + this_pct,
            2
        )

        if discount_pct > 15:
            frappe.throw(
                "L1 + L2 + L3 combined discount cannot exceed 15%."
            )

        discount_amount = frappe.utils.flt(
            original_grand_total
            * discount_pct
            / 100,
            2
        )

        target_final = frappe.utils.flt(
            original_grand_total
            - discount_amount,
            2
        )


    # ============================================================
    # APPLY DISCOUNT
    #
    # ERPNext distributes Grand Total discount over items and taxes.
    # This can produce small paise/rupee differences because every
    # item and GST row is rounded separately.
    # ============================================================

    attempt = 0
    saved_final = 0
    difference = 0

    while attempt < 10:

        inv.apply_discount_on = "Grand Total"

        inv.discount_amount = frappe.utils.flt(
            discount_amount,
            2
        )

        inv.approver_discount_amount = frappe.utils.flt(
            discount_amount,
            2
        )

        inv.after_approval_grand_total = 0
        inv.approval_workflow_status = "Approved"
        inv.discount_locked = 0

        inv.run_method(
            "calculate_taxes_and_totals"
        )

        inv.after_approval_grand_total = 0

        inv.save(
            ignore_permissions=True
        )

        inv.reload()

        saved_final = frappe.utils.flt(
            inv.grand_total,
            2
        )

        difference = frappe.utils.flt(
            saved_final - target_final,
            2
        )

        if abs(difference) <= 0.02:
            break

        # ERPNext total is higher than target:
        # increase the discount.
        #
        # ERPNext total is lower than target:
        # reduce the discount.

        discount_amount = frappe.utils.flt(
            discount_amount + difference,
            2
        )

        if discount_amount < 0:
            discount_amount = 0

        if discount_amount > original_grand_total:
            discount_amount = original_grand_total

        attempt += 1


    # ============================================================
    # FINAL ROUNDING VALIDATION
    #
    # L1/L2/L3 are percentage approvals. The requested commercial
    # percentage must remain exact, but ERPNext's saved Grand Total
    # is accepted because tax/item rounding can cause a small
    # difference.
    #
    # L4 is an exact final-amount approval, so a maximum ₹2 rounding
    # difference is permitted.
    # ============================================================

    saved_final = frappe.utils.flt(
        inv.grand_total,
        2
    )

    final_difference = abs(
        frappe.utils.flt(
            saved_final - target_final,
            2
        )
    )

    if is_l4 and final_difference > 2:
        frappe.throw(
            "ERPNext could not match the approved L4 final amount "
            "after GST rounding. Expected ₹"
            + str(target_final)
            + ", calculated ₹"
            + str(saved_final)
            + ". Difference ₹"
            + str(final_difference)
            + "."
        )


    # ============================================================
    # STORE COMMERCIAL APPROVAL VALUES
    # ============================================================

    actual_discount_amount = frappe.utils.flt(
        inv.discount_amount,
        2
    )

    if is_l4:

        cumulative_pct = 0

        if original_grand_total > 0:

            cumulative_pct = frappe.utils.flt(
                (
                    original_grand_total
                    - saved_final
                )
                / original_grand_total
                * 100,
                4
            )

        approved_request_pct = cumulative_pct

    else:

        # Store the exact requested commercial percentage.
        # Example:
        # L1 = 5
        # L2 = 5
        # L3 = 5
        # Total = 15

        cumulative_pct = frappe.utils.flt(
            previous_normal_pct + this_pct,
            2
        )

        approved_request_pct = this_pct


    # ============================================================
    # UPDATE SALES INVOICE
    # ============================================================

    inv.approver_discount_amount = actual_discount_amount
    inv.total_approver_discount_pct = cumulative_pct
    inv.after_approval_grand_total = 0
    inv.approval_workflow_status = "Approved"
    inv.discount_locked = 0

    inv.discount_remarks = (
        level
        + " approval. Discount calculated on original "
        + "Grand Total including GST. Original: ₹"
        + str(original_grand_total)
        + ", approved percentage: "
        + str(approved_request_pct)
        + "%, cumulative percentage: "
        + str(cumulative_pct)
        + "%, ERPNext discount: ₹"
        + str(actual_discount_amount)
        + ", expected final: ₹"
        + str(target_final)
        + ", saved final: ₹"
        + str(saved_final)
    )

    inv.save(
        ignore_permissions=True
    )

    inv.reload()

    saved_final = frappe.utils.flt(
        inv.grand_total,
        2
    )

    actual_discount_amount = frappe.utils.flt(
        inv.discount_amount,
        2
    )


    # ============================================================
    # UPDATE APPROVAL REQUEST
    # ============================================================

    frappe.db.set_value(
        "Discount Approval Request",
        req.name,
        {
            "status": "Approved",
            "approved_discount_pct": approved_request_pct,
            "approved_final_amount": saved_final,
            "approved_by": approver,
            "approved_at": frappe.utils.now_datetime()
        },
        update_modified=False
    )


    # ============================================================
    # API RESPONSE
    # ============================================================

    frappe.response["message"] = {
        "status": "success",
        "invoice_name": invoice_name,
        "approval_request": req.name,
        "approval_level": level,
        "is_l4": is_l4,
        "original_grand_total": original_grand_total,
        "grand_total": saved_final,
        "final_amount": saved_final,
        "target_grand_total": target_final,
        "rounding_difference": frappe.utils.flt(
            saved_final - target_final,
            2
        ),
        "disc_amt": actual_discount_amount,
        "disc_pct": cumulative_pct,
        "approved_request_pct": approved_request_pct,
        "apply_discount_on": inv.apply_discount_on
    }
