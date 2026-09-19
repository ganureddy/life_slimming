"""md_vendor_ageing_api

Original API: md_vendor_ageing_api
Source modified: 2026-08-04 13:08:55.191774
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
    #  SERVER SCRIPT (API)  —  md_vendor_ageing_api
    #  Script Type : API   ·   API Method : md_vendor_ageing_api
    #  URL (summary): /api/method/md_vendor_ageing_api
    #  URL (detail) : /api/method/md_vendor_ageing_api?supplier=NAME
    #  URL (invoice): /api/method/md_vendor_ageing_api?invoice=PINV-...
    #
    #  Accounts-payable ageing from open Purchase Invoices (outstanding > 0).
    #   Buckets (by age from posting_date): Current(0), 1-30, 31-60, 60+.
    #   Also days overdue past due_date.
    #   Detail action returns each open invoice for a supplier + its items.
    #
    #  safe_exec-safe: dict params only, no None, no reserved aliases,
    #  no try/except, no % literals, no slicing of function results.
    # =====================================================================

    args = frappe.form_dict or {}
    supplier = args.get("supplier")
    invoice = args.get("invoice")
    today = frappe.utils.nowdate()

    # ---------- MODE: single invoice detail (items) ----------
    if invoice:
        inv = str(invoice).strip()
        head = _read_sql("""
        SELECT name, supplier, posting_date, due_date, grand_total,
               outstanding_amount, status, bill_no
        FROM `tabPurchase Invoice`
        WHERE name = %(n)s
        LIMIT 1
    """, {"n": inv}, as_dict=True)
        items = _read_sql("""
        SELECT item_code, item_name, qty, rate, amount
        FROM `tabPurchase Invoice Item`
        WHERE parent = %(n)s
        ORDER BY amount DESC
    """, {"n": inv}, as_dict=True)
        idet = []
        for r in items:
            d = {}
            d["item"] = r.get("item_name") or r.get("item_code")
            d["qty"] = float(r.get("qty") or 0)
            d["rate"] = float(r.get("rate") or 0)
            d["amount"] = float(r.get("amount") or 0)
            idet.append(d)
        hd = {}
        if len(head) > 0:
            h = head[0]
            hd["name"] = h.get("name")
            hd["supplier"] = h.get("supplier")
            hd["posting_date"] = str(h.get("posting_date") or "")
            hd["due_date"] = str(h.get("due_date") or "")
            hd["grand_total"] = float(h.get("grand_total") or 0)
            hd["outstanding"] = float(h.get("outstanding_amount") or 0)
            hd["status"] = h.get("status")
            hd["bill_no"] = h.get("bill_no") or ""
        out = {}
        out["invoice"] = hd
        out["items"] = idet
        frappe.response["message"] = out

    # ---------- MODE: one supplier — list open invoices ----------
    elif supplier:
        sup = str(supplier).strip()
        inv_rows = _read_sql("""
        SELECT name, posting_date, due_date, grand_total,
               outstanding_amount, status, bill_no
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1
          AND outstanding_amount > 0
          AND supplier = %(s)s
        ORDER BY due_date ASC
    """, {"s": sup}, as_dict=True)
        invs = []
        tot = 0.0
        for r in inv_rows:
            o = float(r.get("outstanding_amount") or 0)
            pdate = r.get("posting_date")
            ddate = r.get("due_date")
            age = 0
            if pdate:
                age = frappe.utils.date_diff(today, pdate)
            overdue = 0
            if ddate:
                od = frappe.utils.date_diff(today, ddate)
                if od > 0:
                    overdue = od
            d = {}
            d["invoice"] = r.get("name")
            d["posting_date"] = str(pdate or "")
            d["due_date"] = str(ddate or "")
            d["grand_total"] = float(r.get("grand_total") or 0)
            d["outstanding"] = o
            d["age"] = age
            d["overdue"] = overdue
            d["status"] = r.get("status")
            d["bill_no"] = r.get("bill_no") or ""
            d["erp"] = "/app/purchase-invoice/" + str(r.get("name"))
            invs.append(d)
            tot = tot + o
        out = {}
        out["supplier"] = sup
        out["invoices"] = invs
        out["outstanding"] = tot
        frappe.response["message"] = out

    # ---------- MODE: summary — supplier-wise ageing buckets ----------
    else:
        rows = _read_sql("""
        SELECT supplier, posting_date, due_date, outstanding_amount
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1
          AND outstanding_amount > 0
    """, {}, as_dict=True)

        sup_map = {}
        tot_current = 0.0
        tot_b1 = 0.0
        tot_b2 = 0.0
        tot_b3 = 0.0
        tot_all = 0.0
        tot_overdue = 0.0

        for r in rows:
            s = r.get("supplier") or "Unknown"
            o = float(r.get("outstanding_amount") or 0)
            pdate = r.get("posting_date")
            ddate = r.get("due_date")
            age = 0
            if pdate:
                age = frappe.utils.date_diff(today, pdate)
            overdue_amt = 0.0
            if ddate:
                od = frappe.utils.date_diff(today, ddate)
                if od > 0:
                    overdue_amt = o

            if s not in sup_map:
                d = {}
                d["supplier"] = s
                d["current"] = 0.0
                d["b1"] = 0.0
                d["b2"] = 0.0
                d["b3"] = 0.0
                d["total"] = 0.0
                d["overdue"] = 0.0
                d["bills"] = 0
                sup_map[s] = d
            e = sup_map[s]
            # bucket by age from posting_date
            if age <= 0:
                e["current"] = e["current"] + o
                tot_current = tot_current + o
            elif age <= 30:
                e["b1"] = e["b1"] + o
                tot_b1 = tot_b1 + o
            elif age <= 60:
                e["b2"] = e["b2"] + o
                tot_b2 = tot_b2 + o
            else:
                e["b3"] = e["b3"] + o
                tot_b3 = tot_b3 + o
            e["total"] = e["total"] + o
            e["overdue"] = e["overdue"] + overdue_amt
            e["bills"] = e["bills"] + 1
            tot_all = tot_all + o
            tot_overdue = tot_overdue + overdue_amt

        # to list + sort by total desc (selection sort, no lambda)
        suppliers = []
        for k in sup_map:
            suppliers.append(sup_map[k])
        n = len(suppliers)
        a = 0
        while a < n:
            mx = a
            b = a + 1
            while b < n:
                if suppliers[b]["total"] > suppliers[mx]["total"]:
                    mx = b
                b = b + 1
            if mx != a:
                tmp = suppliers[a]
                suppliers[a] = suppliers[mx]
                suppliers[mx] = tmp
            a = a + 1

        totals = {}
        totals["current"] = tot_current
        totals["b1"] = tot_b1
        totals["b2"] = tot_b2
        totals["b3"] = tot_b3
        totals["total"] = tot_all
        totals["overdue"] = tot_overdue
        totals["supplier_count"] = len(suppliers)

        out = {}
        out["suppliers"] = suppliers
        out["totals"] = totals
        out["as_on"] = today
        frappe.response["message"] = out
