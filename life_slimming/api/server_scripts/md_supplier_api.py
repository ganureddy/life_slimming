"""md_supplier_api

Original API: md_supplier_api
Source modified: 2026-07-31 05:50:13.395061
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
    #  SERVER SCRIPT (API)  —  md_supplier_api
    #  Script Type : API   ·   API Method : md_supplier_api
    #  URL: /api/method/md_supplier_api?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    #
    #  Supplier balances (outstanding from Purchase Invoice) + supplier
    #  payments made in range (Payment Entry, payment_type = Pay).
    # =====================================================================

    args = frappe.form_dict or {}
    to_date = args.get("to_date")
    from_date = args.get("from_date")
    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.get_first_day(to_date)

    # ---------- 1. outstanding balances by supplier (all open PIs) ----------
    bal_rows = _read_sql("""
    SELECT supplier                     AS supplier,
           SUM(outstanding_amount)      AS outs,
           COUNT(name)                  AS bills
    FROM `tabPurchase Invoice`
    WHERE docstatus = 1
      AND outstanding_amount > 0
    GROUP BY supplier
    ORDER BY outs DESC
    LIMIT 40
""", {}, as_dict=True)
    balances = []
    tot_out = 0.0
    for r in bal_rows:
        o = float(r.get("outs") or 0)
        d = {}
        d["supplier"] = r.get("supplier")
        d["outstanding"] = o
        d["bills"] = int(r.get("bills") or 0)
        balances.append(d)
        tot_out = tot_out + o

    # ---------- 2. supplier payments made in range ----------
    pay_rows = _read_sql("""
    SELECT party                AS supplier,
           SUM(paid_amount)     AS paid,
           COUNT(name)          AS cnt
    FROM `tabPayment Entry`
    WHERE docstatus = 1
      AND payment_type = 'Pay'
      AND party_type = 'Supplier'
      AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY party
    ORDER BY paid DESC
    LIMIT 40
""", {"f": from_date, "t": to_date}, as_dict=True)
    payments = []
    tot_paid = 0.0
    for r in pay_rows:
        p = float(r.get("paid") or 0)
        d = {}
        d["supplier"] = r.get("supplier")
        d["paid"] = p
        d["count"] = int(r.get("cnt") or 0)
        payments.append(d)
        tot_paid = tot_paid + p

    # ---------- 3. purchases billed in range (by supplier) ----------
    bill_rows = _read_sql("""
    SELECT supplier            AS supplier,
           SUM(grand_total)    AS amt,
           COUNT(name)         AS cnt
    FROM `tabPurchase Invoice`
    WHERE docstatus = 1
      AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY supplier
    ORDER BY amt DESC
    LIMIT 40
""", {"f": from_date, "t": to_date}, as_dict=True)
    billed = []
    tot_billed = 0.0
    for r in bill_rows:
        a = float(r.get("amt") or 0)
        d = {}
        d["supplier"] = r.get("supplier")
        d["amt"] = a
        d["count"] = int(r.get("cnt") or 0)
        billed.append(d)
        tot_billed = tot_billed + a

    totals = {}
    totals["outstanding"] = tot_out
    totals["paid_in_range"] = tot_paid
    totals["billed_in_range"] = tot_billed
    totals["supplier_count"] = len(balances)

    out = {}
    out["from_date"] = from_date
    out["to_date"] = to_date
    out["balances"] = balances
    out["payments"] = payments
    out["billed"] = billed
    out["totals"] = totals
    frappe.response["message"] = out
