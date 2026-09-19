"""create_multiple_discount_approval_requests_v2

Original API: create_multiple_discount_approval_requests_v2
Source modified: 2026-09-07 23:10:48.464301
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
    # Server Script name: LIFE Create Multiple Discount Approval Requests v2
    # Script Type: API
    # API Method: create_multiple_discount_approval_requests_v2
    # Allow Guest: No

    invoice_name = (frappe.form_dict.get("invoice_name") or "").strip()
    raw_requests = frappe.form_dict.get("requests")

    if not invoice_name:
        frappe.throw("Sales Invoice is required.")

    try:
        requests = json.loads(raw_requests) if isinstance(raw_requests, str) else raw_requests
    except Exception:
        requests = []

    if not requests:
        frappe.throw("Select at least one discount approval.")
    if len(requests) > 3:
        frappe.throw("Only L1, L2 and L3 can be requested together.")

    inv = frappe.get_doc("Sales Invoice", invoice_name)
    if inv.docstatus != 0:
        frappe.throw("Discount can only be requested while the invoice is Draft.")

    original_grand_total = frappe.utils.flt(inv.grand_total, 2)
    first_bill_total = frappe.db.get_value(
        "Discount Approval Request",
        {"linked_invoice": invoice_name},
        "bill_total",
        order_by="creation asc"
    )
    if frappe.utils.flt(first_bill_total, 2) > 0:
        original_grand_total = frappe.utils.flt(first_bill_total, 2)
    if original_grand_total <= 0:
        frappe.throw("Original Grand Total including GST could not be identified.")

    existing = frappe.get_all(
        "Discount Approval Request",
        filters={"linked_invoice": invoice_name},
        fields=["name", "approval_level", "selected_approver", "status"]
    )
    used_levels = {}
    used_approvers = {}
    for row in existing:
        if row.status in ("Pending", "Approved"):
            used_levels[row.approval_level or "L1"] = 1
            if row.selected_approver:
                used_approvers[row.selected_approver] = 1

    clean = []
    batch_levels = {}
    batch_approvers = {}
    total_pct = 0

    for item in requests:
        level = (item.get("approval_level") or "").strip()
        approver = (item.get("selected_approver") or "").strip()
        pct = frappe.utils.flt(item.get("requested_discount_pct"), 2)
        reason = (item.get("reason") or "").strip()

        if level not in ("L1", "L2", "L3"):
            frappe.throw("Only L1, L2 and L3 may be requested together. Use the existing L4 flow separately.")
        if used_levels.get(level) or batch_levels.get(level):
            frappe.throw(level + " is already Pending/Approved or selected twice.")
        if not approver:
            frappe.throw("Select an approver for " + level + ".")
        if used_approvers.get(approver) or batch_approvers.get(approver):
            frappe.throw("The same approver cannot be used twice: " + approver)
        if pct <= 0 or pct > 5:
            frappe.throw(level + " discount must be greater than 0 and not more than 5%.")
        if not reason:
            frappe.throw("Reason is required for " + level + ".")

        master = frappe.db.get_value(
            "Discount Approver Master",
            {"user": approver, "is_active": 1},
            ["user", "approval_level"],
            as_dict=True
        )
        if approver == frappe.session.user and level == "L1":
            pass
        elif not master:
            frappe.throw(approver + " is not an active Discount Approver.")
        elif (master.approval_level or "L1") != level:
            frappe.throw(approver + " belongs to " + str(master.approval_level) + ", not " + level + ".")

        total_pct += pct
        batch_levels[level] = 1
        batch_approvers[approver] = 1
        clean.append({
            "approval_level": level,
            "selected_approver": approver,
            "requested_discount_pct": pct,
            "reason": reason
        })

    approved_rows = frappe.get_all(
        "Discount Approval Request",
        filters={"linked_invoice": invoice_name, "status": "Approved"},
        fields=["approval_level", "approved_discount_pct", "requested_discount_pct"]
    )
    approved_pct = 0
    for row in approved_rows:
        if row.approval_level in ("L1", "L2", "L3"):
            approved_pct += frappe.utils.flt(row.approved_discount_pct or row.requested_discount_pct, 2)

    if approved_pct + total_pct > 15:
        frappe.throw("Approved plus newly requested L1/L2/L3 discount cannot exceed 15%.")

    created = []
    for item in clean:
        req = frappe.new_doc("Discount Approval Request")
        req.linked_invoice = invoice_name
        req.requested_by = frappe.session.user
        req.selected_approver = item["selected_approver"]
        req.bill_total = original_grand_total
        req.branch = inv.get("branch") or ""
        req.reason = item["reason"]
        req.status = "Pending"
        req.approval_level = item["approval_level"]
        req.requested_discount_pct = item["requested_discount_pct"]
        req.requested_final_amount = 0
        req.insert(ignore_permissions=True)
        created.append({
            "name": req.name,
            "approval_level": req.approval_level,
            "selected_approver": req.selected_approver,
            "requested_discount_pct": req.requested_discount_pct
        })

    inv.discount_locked = 1
    inv.approval_workflow_status = "Pending Approval"
    inv.after_approval_grand_total = 0
    inv.save(ignore_permissions=True)

    frappe.response["message"] = {
        "status": "success",
        "invoice_name": invoice_name,
        "original_grand_total": original_grand_total,
        "count": len(created),
        "requests": created
    }
