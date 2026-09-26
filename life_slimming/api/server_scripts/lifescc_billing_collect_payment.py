"""lifescc.billing.collect_payment

Original API: lifescc.billing.collect_payment
Source modified: 2026-07-29 03:56:05.810402
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
    # SERVER SCRIPT  #3   ·   lifescc.billing.collect_payment   ·   v3
    # Type: API   ·   Method: lifescc.billing.collect_payment   ·   Guest: No
    #
    # v3 — SPLIT PAYMENTS: one collection can be settled with several modes
    #      at once (e.g. 5,000 Cash + 10,000 Credit Card). One Payment Entry
    #      is created per mode, each allocated against the same invoice.
    #      If any one fails, the whole collection is rolled back.
    #
    # Args
    #   sales_invoice   (required)
    #   payments        JSON list: [{mode_of_payment, amount, reference_no}, ...]
    #                   (the older single-mode args still work)
    #   loan fields     aadhaar_card, pan_card, transaction_id,
    #                   do_screenshot, aadhaar_image, pan_image, consent_image
    # ═══════════════════════════════════════════════════════════════════

    # NOTE: safe_exec forbids "import" (ImportError: __import__ not found).
    # It DOES provide a `json` global with loads/dumps, so json.loads works
    # directly. frappe.parse_json is NOT available inside safe_exec.

    args = frappe.form_dict

    si_name = args.get("sales_invoice")
    ref_dt = args.get("reference_date") or frappe.utils.today()

    COMPANY = "Life Slimming And Cosmetic Pvt Ltd"

    LOAN_MODES = [
        "Bajaj Card Charges", "Carepay", "Fibe Finance", "ShopSE",
        "Savein Fintech Card Charges", "Sai Roshini Card Charges",
        "Liqui Loans Charges", "Loan Tap / Uno Finance Charges",
    ]

    LOAN_MIN = 25000

    # Per-mode loan documents: [{mode_of_payment, aadhaar_card, pan_card,
    # transaction_id, do_screenshot, aadhaar_image, pan_image, consent_image}]
    loan_docs = {}
    raw_docs = args.get("loan_docs")
    if raw_docs:
        try:
            parsed_docs = json.loads(raw_docs) if isinstance(raw_docs, str) else raw_docs
            for d in (parsed_docs or []):
                m = d.get("mode_of_payment")
                if m:
                    loan_docs[m] = d
        except Exception:
            loan_docs = {}

    # legacy single-set fallback
    aadhaar_card   = (args.get("aadhaar_card") or "").strip()
    pan_card       = (args.get("pan_card") or "").strip()
    transaction_id = (args.get("transaction_id") or "").strip()
    do_screenshot  = (args.get("do_screenshot") or "").strip()
    aadhaar_image  = (args.get("aadhaar_image") or "").strip()
    pan_image      = (args.get("pan_image") or "").strip()
    consent_image  = (args.get("consent_image") or "").strip()


    def docs_for(mode):
        d = loan_docs.get(mode)
        if d:
            return d
        return {
            "aadhaar_card": aadhaar_card, "pan_card": pan_card,
            "transaction_id": transaction_id, "do_screenshot": do_screenshot,
            "aadhaar_image": aadhaar_image, "pan_image": pan_image,
            "consent_image": consent_image,
        }


    def fail(msg):
        frappe.response["message"] = {"error": msg}


    def mop_account(mop, company):
        return frappe.db.get_value(
            "Mode of Payment Account",
            {"parent": mop, "company": company},
            "default_account",
        )


    # ── read the payment rows (split format, or legacy single) ──
    rows = []
    raw = args.get("payments")
    parse_error = ""
    if raw:
        if isinstance(raw, str):
            try:
                # safe_exec provides `json` as a global (loads/dumps). It does
                # NOT allow "import json", and frappe.parse_json is unavailable.
                parsed = json.loads(raw)
            except Exception as e:
                parsed = []
                parse_error = "Could not read the payment rows: " + str(e)
        else:
            parsed = raw
        for p in (parsed or []):
            amt = float(p.get("amount") or 0)
            if amt > 0:
                rows.append({
                    "mode": p.get("mode_of_payment") or "Cash",
                    "amount": amt,
                    "ref": (p.get("reference_no") or "").strip(),
                })
    else:
        amt = float(args.get("amount") or 0)
        if amt > 0:
            rows.append({
                "mode": args.get("mode_of_payment") or "Cash",
                "amount": amt,
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
            ["name", "customer", "patient_name", "branch",
             "outstanding_amount", "docstatus"],
            as_dict=True,
        )
        if not si:
            fail("Sales Invoice not found")
        elif si.docstatus != 1:
            fail("Invoice is not submitted")
        else:
            total = 0
            for r in rows:
                total += r["amount"]

            problem = ""
            if total > float(si.outstanding_amount or 0) + 0.5:
                problem = "Total entered exceeds the outstanding " + str(si.outstanding_amount)

            for r in rows:
                if problem:
                    continue
                if r["mode"] != "Cash" and not r["ref"]:
                    problem = "Reference number is required for " + r["mode"]
                elif not mop_account(r["mode"], COMPANY):
                    problem = ("No default account set for mode '" + r["mode"] +
                               "'. Set it in Mode of Payment.")
                elif r["mode"] in LOAN_MODES:
                    if r["amount"] < LOAN_MIN:
                        problem = (r["mode"] + " needs at least " + str(LOAN_MIN) +
                                   " on that row (got " + str(r["amount"]) + ")")
                    else:
                        d = docs_for(r["mode"])
                        if not (d.get("aadhaar_card") or "").strip():
                            problem = "Aadhaar Card is mandatory for " + r["mode"]
                        elif not (d.get("pan_card") or "").strip():
                            problem = "PAN Card is mandatory for " + r["mode"]
                        elif not (d.get("transaction_id") or "").strip():
                            problem = "Transaction ID is mandatory for " + r["mode"]
                        elif not (d.get("do_screenshot") or "").strip():
                            problem = "D.O Screenshot is mandatory for " + r["mode"]
                        elif not (d.get("aadhaar_image") or "").strip():
                            problem = "Aadhaar Card Image is mandatory for " + r["mode"]
                        elif not (d.get("pan_image") or "").strip():
                            problem = "PAN Card Image is mandatory for " + r["mode"]
                        elif not (d.get("consent_image") or "").strip():
                            problem = "Loan Consent Image is mandatory for " + r["mode"]

            if problem:
                fail(problem)
            else:
                created = []
                allocated_total = 0
                remaining = float(si.outstanding_amount or 0)

                try:
                    for r in rows:
                        alloc = r["amount"]
                        if alloc > remaining:
                            alloc = remaining
                        if alloc <= 0:
                            continue

                        paid_to = mop_account(r["mode"], COMPANY)
                        pe = frappe.get_doc({
                            "doctype": "Payment Entry",
                            "payment_type": "Receive",
                            "posting_date": frappe.utils.today(),
                            "company": COMPANY,
                            "mode_of_payment": r["mode"],
                            "party_type": "Customer",
                            "party": si.customer,
                            "branch": si.branch,
                            "paid_to": paid_to,
                            "paid_amount": r["amount"],
                            "received_amount": r["amount"],
                            "source_exchange_rate": 1,
                            "target_exchange_rate": 1,
                            "reference_no": r["ref"] or None,
                            "reference_date": ref_dt if r["ref"] else None,
                            "references": [{
                                "reference_doctype": "Sales Invoice",
                                "reference_name": si.name,
                                "allocated_amount": alloc,
                            }],
                        })

                        if r["mode"] in LOAN_MODES:
                            d = docs_for(r["mode"])
                            pe.custom_aadhaar_card   = d.get("aadhaar_card")
                            pe.custom_pan_card       = d.get("pan_card")
                            pe.custom_transaction_id = d.get("transaction_id")
                            pe.append("custom_loan_details_form", {
                                "do_screenshot": d.get("do_screenshot"),
                                "aaadhar_card_image": d.get("aadhaar_image"),
                                "pancard_image": d.get("pan_image"),
                            })
                            # "Loan Form Images".upload_date is a DATE field whose
                            # doctype default is the string "Now" — MySQL rejects
                            # that for a date column, so set a real date here.
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
                        # A submitted Payment Entry posts GL entries, so the
                        # rollback may not remove the earlier ones. Tell the
                        # user exactly what already exists so nothing is
                        # silently double-collected.
                        fail("Payment partly recorded — these were created: " +
                             ", ".join(created) +
                             ". The remaining rows FAILED: " + str(e) +
                             " — check the invoice before retrying.")
                    else:
                        fail("Payment failed, nothing was saved: " + str(e))
                else:
                    frappe.db.commit()
                    new_out = float(
                        frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount") or 0
                    )
                    frappe.response["message"] = {
                        "payment_entries": created,
                        "allocated": allocated_total,
                        "outstanding": new_out,
                        "status": "Paid" if new_out <= 0 else "Partly Paid",
                    }
