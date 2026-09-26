"""lifescc.billing.submit_invoice

Original API: lifescc.billing.submit_invoice
Source modified: 2026-07-27 12:11:16.389891
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
    # ═══════════════════════════════════════════════════════════════════
    # SERVER SCRIPT  #7   ·   lifescc.billing.submit_invoice
    # Type: API   ·   Method: lifescc.billing.submit_invoice   ·   Guest: No
    #
    # Submits a DRAFT Sales Invoice from the billing page.
    # Used when:
    #   - the branch does NOT want a discount → submit straight away, then
    #     collect the payment; or
    #   - all discount approvals are done → submit the approved bill.
    #
    # Guard rails (mirroring the Sales Invoice discount client script):
    #   - refuses while discount_locked = 1 (an approval is still pending)
    #   - refuses if the invoice is not a draft
    # ═══════════════════════════════════════════════════════════════════

    args = frappe.form_dict
    invoice_name = args.get("invoice_name")


    def fail(msg):
        frappe.response["message"] = {"error": msg}


    if not invoice_name:
        fail("Invoice is required")

    else:
        si = frappe.db.get_value(
            "Sales Invoice", invoice_name,
            ["name", "docstatus", "discount_locked", "approval_workflow_status",
             "grand_total", "rounded_total", "outstanding_amount"],
            as_dict=True,
        )
        if not si:
            fail("Invoice not found")

        elif si.docstatus == 1:
            fail("This invoice is already submitted")

        elif si.docstatus == 2:
            fail("This invoice is cancelled")

        elif si.discount_locked == 1:
            fail("Invoice is locked — a discount approval is still pending. "
                 "Approve or reject it first.")

        else:
            # a pending request is a hard stop even if the lock flag was cleared
            pending = frappe.db.get_value(
                "Discount Approval Request",
                {"linked_invoice": invoice_name, "status": "Pending"},
                "name",
            )
            if pending:
                fail("A discount request is still pending approval on this bill.")
            else:
                doc = frappe.get_doc("Sales Invoice", invoice_name)
                doc.submit()
                frappe.db.commit()

                fresh = frappe.db.get_value(
                    "Sales Invoice", invoice_name,
                    ["grand_total", "rounded_total", "outstanding_amount", "status"],
                    as_dict=True,
                )
                frappe.response["message"] = {
                    "sales_invoice": invoice_name,
                    "grand_total": float(fresh.rounded_total or fresh.grand_total or 0),
                    "outstanding": float(fresh.outstanding_amount or 0),
                    "status": fresh.status or "Submitted",
                }
