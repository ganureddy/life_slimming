"""dues_recovery_save

Original API: dues_recovery_save
Source modified: 2026-07-25 23:09:36.418398
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

    args = frappe.form_dict
    inv = args.get("invoice_no") or args.get("inv") or ""
    if not inv:
        frappe.response["message"] = {"ok": 0, "error": "invoice_no missing"}
    else:
        col_amt_raw = args.get("collected_amount") or args.get("colAmt") or ""
        cmt_amt_raw = args.get("committed_amount") or args.get("cmtAmt") or ""

        col_amt = 0
        if col_amt_raw not in (None, "", "null"):
            try:
                col_amt = float(col_amt_raw)
            except Exception:
                col_amt = 0

        cmt_amt = 0
        if cmt_amt_raw not in (None, "", "null"):
            try:
                cmt_amt = float(cmt_amt_raw)
            except Exception:
                cmt_amt = 0

        col_on = args.get("collected_on") or args.get("colDate") or ""
        cmt_by = args.get("committed_by") or args.get("cmtDate") or ""
        if not col_on:
            col_on = None
        if not cmt_by:
            cmt_by = None

        vals = {
            "branch": args.get("branch") or "",
            "manager_status": args.get("manager_status") or args.get("st") or "PENDING",
            "collected_amount": col_amt,
            "collected_on": col_on,
            "mode_of_payment": args.get("mode_of_payment") or args.get("mode") or "",
            "committed_amount": cmt_amt,
            "committed_by": cmt_by,
            "reason": args.get("reason") or "",
            "remark": args.get("remark") or "",
            "updated_by_user": frappe.session.user,
        }

        if frappe.db.exists("Dues Recovery Update", inv):
            d = frappe.get_doc("Dues Recovery Update", inv)
            for k in vals:
                d.set(k, vals[k])
            d.save(ignore_permissions=True)
        else:
            d = frappe.new_doc("Dues Recovery Update")
            d.invoice_no = inv
            for k in vals:
                d.set(k, vals[k])
            d.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.response["message"] = {"ok": 1, "invoice_no": inv}
