"""lifescc.billing.collect_payment_v4

Original API: lifescc.billing.collect_payment_v4
Source modified: 2026-10-09 11:46:48.632982
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
    # Server Script: LIFE Billing Collect Payment v4 Loan Video
    # Type: API
    # API Method: lifescc.billing.collect_payment_v4
    # Allow Guest: No

    args = frappe.form_dict
    si_name = args.get("sales_invoice")
    ref_dt = args.get("reference_date") or frappe.utils.today()
    COMPANY = "Life Slimming And Cosmetic Pvt Ltd"
    LOAN_MODES = [
        "Bajaj Card Charges", "Carepay", "Fibe Finance", "ShopSE",
        "Savein Fintech Card Charges", "Sai Roshini Card Charges",
        "Liqui Loans Charges", "Loan Tap / Uno Finance Charges",
    ]
    LOAN_MIN = 20000

    def fail(msg):
        frappe.response["message"] = {"error": msg}

    def mop_account(mop):
        return frappe.db.get_value(
            "Mode of Payment Account",
            {"parent": mop, "company": COMPANY},
            "default_account",
        )

    loan_docs = {}
    raw_docs = args.get("loan_docs")
    if raw_docs:
        try:
            parsed_docs = json.loads(raw_docs) if isinstance(raw_docs, str) else raw_docs
            for d in (parsed_docs or []):
                mode = d.get("mode_of_payment")
                if mode:
                    loan_docs[mode] = d
        except Exception:
            loan_docs = {}

    rows = []
    parse_error = ""
    raw_payments = args.get("payments")
    if raw_payments:
        try:
            parsed = json.loads(raw_payments) if isinstance(raw_payments, str) else raw_payments
        except Exception as e:
            parsed = []
            parse_error = "Could not read payment rows: " + str(e)
        for p in (parsed or []):
            amount = frappe.utils.flt(p.get("amount"), 2)
            if amount > 0:
                rows.append({
                    "mode": p.get("mode_of_payment") or "Cash",
                    "amount": amount,
                    "ref": (p.get("reference_no") or "").strip(),
                })
    else:
        amount = frappe.utils.flt(args.get("amount"), 2)
        if amount > 0:
            rows.append({
                "mode": args.get("mode_of_payment") or "Cash",
                "amount": amount,
                "ref": (args.get("reference_no") or "").strip(),
            })

    if not si_name:
        fail("Sales Invoice is required")
    elif parse_error:
        fail(parse_error)
    elif not rows:
        fail("Enter at least one payment amount")
    else:
        si = frappe.db.get_value(
            "Sales Invoice", si_name,
            ["name", "customer", "patient", "patient_name", "branch", "outstanding_amount", "docstatus"],
            as_dict=True,
        )
        if not si:
            fail("Sales Invoice not found")
        elif si.docstatus != 1:
            fail("Invoice is not submitted")
        else:
            total = 0
            for row in rows:
                total += row["amount"]

            problem = ""
            if total > frappe.utils.flt(si.outstanding_amount, 2) + 0.5:
                problem = "Total entered exceeds outstanding " + str(si.outstanding_amount)

            for row in rows:
                if problem:
                    continue
                mode = row["mode"]
                if mode != "Cash" and not row["ref"]:
                    problem = "Reference number is required for " + mode
                elif not mop_account(mode):
                    problem = "No default account is set for mode '" + mode + "'."
                elif mode in LOAN_MODES:
                    d = loan_docs.get(mode) or {}
                    if row["amount"] < LOAN_MIN:
                        problem = mode + " needs at least " + str(LOAN_MIN) + " on that row."
                    elif not (d.get("aadhaar_card") or "").strip():
                        problem = "Aadhaar Card is mandatory for " + mode
                    elif not (d.get("pan_card") or "").strip():
                        problem = "PAN Card is mandatory for " + mode
                    elif not (d.get("transaction_id") or "").strip():
                        problem = "Transaction ID is mandatory for " + mode
                    elif not (d.get("do_screenshot") or "").strip():
                        problem = "D.O Screenshot is mandatory for " + mode
                    elif not (d.get("aadhaar_image") or "").strip():
                        problem = "Aadhaar Card Image is mandatory for " + mode
                    elif not (d.get("pan_image") or "").strip():
                        problem = "PAN Card Image is mandatory for " + mode
                    elif not (d.get("consent_image") or "").strip():
                        problem = "Loan Consent Image is mandatory for " + mode
                    elif not (d.get("consent_video") or "").strip():
                        problem = "Loan Declaration Video is mandatory for " + mode

            if problem:
                fail(problem)
            else:
                created = []
                allocated_total = 0
                remaining = frappe.utils.flt(si.outstanding_amount, 2)
                try:
                    for row in rows:
                        alloc = row["amount"]
                        if alloc > remaining:
                            alloc = remaining
                        if alloc <= 0:
                            continue

                        mode = row["mode"]
                        pe = frappe.get_doc({
                            "doctype": "Payment Entry",
                            "payment_type": "Receive",
                            "posting_date": frappe.utils.today(),
                            "company": COMPANY,
                            "mode_of_payment": mode,
                            "party_type": "Customer",
                            "party": si.customer,
                            "branch": si.branch,
                            "paid_to": mop_account(mode),
                            "paid_amount": row["amount"],
                            "received_amount": row["amount"],
                            "source_exchange_rate": 1,
                            "target_exchange_rate": 1,
                            "reference_no": row["ref"] or None,
                            "reference_date": ref_dt if row["ref"] else None,
                            "references": [{
                                "reference_doctype": "Sales Invoice",
                                "reference_name": si.name,
                                "allocated_amount": alloc,
                            }],
                        })

                        if mode in LOAN_MODES:
                            d = loan_docs.get(mode) or {}
                            pe.custom_aadhaar_card = d.get("aadhaar_card")
                            pe.custom_pan_card = d.get("pan_card")
                            pe.custom_transaction_id = d.get("transaction_id")
                            pe.custom_loan_consent_video = d.get("consent_video")
                            pe.append("custom_loan_details_form", {
                                "do_screenshot": d.get("do_screenshot"),
                                "aaadhar_card_image": d.get("aadhaar_image"),
                                "pancard_image": d.get("pan_image"),
                            })
                            pe.append("custom_loan_form_images", {
                                "attach_image": d.get("consent_image"),
                                "upload_date": frappe.utils.today(),
                            })

                        pe.insert(ignore_permissions=False)
                        pe.submit()
                        created.append(pe.name)
                        allocated_total += alloc
                        remaining -= alloc
                except Exception as e:
                    frappe.db.rollback()
                    if created:
                        fail(
                            "Payment partly recorded — these were created: " + ", ".join(created) +
                            ". Remaining rows failed: " + str(e) +
                            ". Check the invoice before retrying."
                        )
                    else:
                        fail("Payment failed, nothing was saved: " + str(e))
                else:
                    frappe.db.commit()
                    new_out = frappe.utils.flt(
                        frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"), 2
                    )
                    frappe.response["message"] = {
                        "payment_entries": created,
                        "allocated": allocated_total,
                        "outstanding": new_out,
                        "status": "Paid" if new_out <= 0 else "Partly Paid",
                    }
