"""accounts_command_centre_reconcile

Original API: accounts_command_centre_reconcile
Source modified: 2026-07-31 12:42:05.937488
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
    # =====================================================================
    #  SERVER SCRIPT  (type = "API")
    #  Name        : accounts_command_centre_reconcile
    #  API Method  : accounts_command_centre_reconcile
    #  Allow Guest : NO
    #
    #  Handles TWO actions for the Bank Reconciliation tab:
    #    action = "suggest"    -> return candidate vouchers for a bank txn
    #    action = "reconcile"  -> link selected voucher(s) to the bank txn
    #                             and mark it reconciled  (WRITES to DB)
    #
    #  safe_exec SAFE:
    #    - uses the frappe document API (frappe.get_doc / .append / .save)
    #      which IS permitted in safe_exec (no python imports, no f-strings,
    #      no tuple-unpack, no augmented dict assignment)
    #    - permission checks enforced via frappe.has_permission
    #
    #  Called from the Web Page:
    #    frappe.call({ method:"accounts_command_centre_reconcile",
    #                  args:{ action:"suggest", bank_transaction:"ACC-BTN-..." }})
    #    frappe.call({ method:"accounts_command_centre_reconcile",
    #                  args:{ action:"reconcile",
    #                         bank_transaction:"ACC-BTN-...",
    #                         vouchers: JSON string of
    #                           [{"payment_document":"Payment Entry",
    #                             "payment_entry":"ACC-PAY-...",
    #                             "amount":12500}] }})
    # =====================================================================

    action = frappe.form_dict.get("action")
    btn_id = frappe.form_dict.get("bank_transaction")

    if not action:
        frappe.response["message"] = {"ok": False, "error": "action is required"}

    elif not btn_id:
        frappe.response["message"] = {"ok": False, "error": "bank_transaction is required"}

    # ---------------------------------------------------------------------
    #  Guard: user must have write permission on Bank Transaction
    # ---------------------------------------------------------------------
    elif not frappe.has_permission("Bank Transaction", "write"):
        frappe.response["message"] = {"ok": False, "error": "Not permitted to reconcile"}

    else:
        # -----------------------------------------------------------------
        #  Load the bank transaction (read its key fields)
        # -----------------------------------------------------------------
        btn = frappe.get_doc("Bank Transaction", btn_id)
        bank_account = btn.bank_account          # the ERPNext Bank Account (link)
        gl_account = None
        if bank_account:
            gl_account = frappe.db.get_value("Bank Account", bank_account, "account")

        unallocated = btn.unallocated_amount or 0
        # direction: deposit means we look for money-in vouchers, withdrawal money-out
        is_deposit = (btn.deposit or 0) > 0
        txn_amount = (btn.deposit or 0) if is_deposit else (btn.withdrawal or 0)

        # =================================================================
        #  ACTION 1 : SUGGEST candidate vouchers
        # =================================================================
        if action == "suggest":
            # window: +/- 7 days around the bank txn date, amount within tolerance
            d_from = frappe.utils.add_days(str(btn.date), -7)
            d_to = frappe.utils.add_days(str(btn.date), 7)

            # ---- Payment Entries against this bank GL account ----------
            # Column identifiers cannot be bound params, so build via
            # concatenation (safe_exec permits + on strings, not .format()).
            if is_deposit:
                pe_field = "paid_to"
                pe_amt_field = "received_amount"
            else:
                pe_field = "paid_from"
                pe_amt_field = "paid_amount"

            pe_sql = (
                "SELECT pe.name AS voucher, 'Payment Entry' AS doctype, "
                "pe.posting_date AS d, pe.party_name AS party, "
                "pe." + pe_amt_field + " AS amount, pe.reference_no AS ref_no, "
                "pe.reference_date AS ref_date "
                "FROM `tabPayment Entry` pe "
                "WHERE pe.docstatus = 1 AND pe.clearance_date IS NULL "
                "AND pe." + pe_field + " = %(gl)s "
                "AND pe.posting_date BETWEEN %(df)s AND %(dt)s "
                "ORDER BY ABS(pe." + pe_amt_field + " - %(amt)s) ASC, pe.posting_date DESC "
                "LIMIT 25"
            )
            pe_rows = _read_sql(pe_sql,
                {"gl": gl_account, "df": d_from, "dt": d_to, "amt": txn_amount},
                as_dict=True)

            # ---- Journal Entries touching this bank GL account ---------
            if is_deposit:
                je_side = "debit_in_account_currency"
            else:
                je_side = "credit_in_account_currency"

            je_sql = (
                "SELECT jea.parent AS voucher, 'Journal Entry' AS doctype, "
                "je.posting_date AS d, je.pay_to_recd_from AS party, "
                "jea." + je_side + " AS amount, je.cheque_no AS ref_no, "
                "je.cheque_date AS ref_date "
                "FROM `tabJournal Entry Account` jea "
                "INNER JOIN `tabJournal Entry` je ON je.name = jea.parent "
                "WHERE je.docstatus = 1 AND jea.account = %(gl)s "
                "AND jea." + je_side + " > 0 "
                "AND je.posting_date BETWEEN %(df)s AND %(dt)s "
                "ORDER BY ABS(jea." + je_side + " - %(amt)s) ASC, je.posting_date DESC "
                "LIMIT 25"
            )
            je_rows = _read_sql(je_sql,
                {"gl": gl_account, "df": d_from, "dt": d_to, "amt": txn_amount},
                as_dict=True)

            # combine candidates; exactness is computed client-side instead
            # of assigning to a dict subscript (safe_exec restriction).
            candidates = []
            for r in pe_rows:
                candidates.append(r)
            for r in je_rows:
                candidates.append(r)

            frappe.response["message"] = {
                "ok": True,
                "bank_transaction": btn_id,
                "date": str(btn.date),
                "description": btn.description,
                "unallocated": unallocated,
                "direction": "deposit" if is_deposit else "withdrawal",
                "txn_amount": txn_amount,
                "candidates": candidates
            }

        # =================================================================
        #  ACTION 2 : RECONCILE  (write link + clearance)
        # =================================================================
        elif action == "reconcile":
            vouchers_raw = frappe.form_dict.get("vouchers")
            if not vouchers_raw:
                frappe.response["message"] = {"ok": False, "error": "vouchers is required"}
            else:
                vouchers = frappe.parse_json(vouchers_raw)
                if not vouchers:
                    frappe.response["message"] = {"ok": False, "error": "no vouchers to reconcile"}
                else:
                    allocated_now = 0
                    linked = []
                    # append each voucher to the Bank Transaction child table
                    for v in vouchers:
                        pay_doctype = v.get("payment_document")
                        pay_name = v.get("payment_entry")
                        amt = v.get("amount") or 0
                        if not pay_doctype or not pay_name or amt <= 0:
                            continue
                        row = btn.append("payment_entries", {})
                        row.payment_document = pay_doctype
                        row.payment_entry = pay_name
                        row.allocated_amount = amt
                        allocated_now = allocated_now + amt
                        linked.append({"doctype": pay_doctype, "name": pay_name, "amount": amt})

                    if not linked:
                        frappe.response["message"] = {"ok": False, "error": "no valid vouchers"}
                    else:
                        # save triggers ERPNext's own allocation + clearance logic
                        btn.save()
                        frappe.db.commit()

                        # re-read updated status
                        updated = frappe.get_doc("Bank Transaction", btn_id)
                        frappe.response["message"] = {
                            "ok": True,
                            "bank_transaction": btn_id,
                            "linked": linked,
                            "allocated_now": allocated_now,
                            "new_status": updated.status,
                            "new_unallocated": updated.unallocated_amount or 0
                        }

        else:
            frappe.response["message"] = {"ok": False, "error": "unknown action"}
