"""md_stock_api

Original API: md_stock_api
Source modified: 2026-07-31 05:49:09.361797
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
    #  SERVER SCRIPT (API)  —  md_stock_api
    #  Script Type : API   ·   API Method : md_stock_api
    #  URL: /api/method/md_stock_api?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    #
    #  Purchase Order / Purchase Invoice / Purchase Receipt / Material Request
    #  summaries in range + open (pending) documents.
    #  NB: stock is largely company-wide (PO cost_center is usually null),
    #  so this module is not branch-split.
    # =====================================================================

    args = frappe.form_dict or {}
    to_date = args.get("to_date")
    from_date = args.get("from_date")
    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.get_first_day(to_date)

    # ---------- 1. Purchase Orders in range (by status) ----------
    po_rows = _read_sql("""
    SELECT COALESCE(status, 'Unknown') AS stat,
           COUNT(name)                 AS cnt,
           SUM(grand_total)            AS amt
    FROM `tabPurchase Order`
    WHERE docstatus < 2
      AND transaction_date BETWEEN %(f)s AND %(t)s
    GROUP BY status
    ORDER BY amt DESC
""", {"f": from_date, "t": to_date}, as_dict=True)

    po = []
    po_total = 0.0
    po_count = 0
    for r in po_rows:
        a = float(r.get("amt") or 0)
        c = int(r.get("cnt") or 0)
        d = {}
        d["status"] = r.get("stat")
        d["count"] = c
        d["amt"] = a
        po.append(d)
        po_total = po_total + a
        po_count = po_count + c

    # ---------- 2. Purchase Invoices in range ----------
    pi_row = _read_sql("""
    SELECT COUNT(name)               AS cnt,
           SUM(grand_total)          AS amt,
           SUM(outstanding_amount)   AS outs
    FROM `tabPurchase Invoice`
    WHERE docstatus = 1
      AND posting_date BETWEEN %(f)s AND %(t)s
""", {"f": from_date, "t": to_date}, as_dict=True)
    pi = {}
    if len(pi_row) > 0:
        pi["count"] = int(pi_row[0].get("cnt") or 0)
        pi["amt"] = float(pi_row[0].get("amt") or 0)
        pi["outstanding"] = float(pi_row[0].get("outs") or 0)
    else:
        pi["count"] = 0
        pi["amt"] = 0.0
        pi["outstanding"] = 0.0

    # ---------- 3. Purchase Receipts in range ----------
    pr_row = _read_sql("""
    SELECT COUNT(name)      AS cnt,
           SUM(grand_total) AS amt
    FROM `tabPurchase Receipt`
    WHERE docstatus = 1
      AND posting_date BETWEEN %(f)s AND %(t)s
""", {"f": from_date, "t": to_date}, as_dict=True)
    pr = {}
    if len(pr_row) > 0:
        pr["count"] = int(pr_row[0].get("cnt") or 0)
        pr["amt"] = float(pr_row[0].get("amt") or 0)
    else:
        pr["count"] = 0
        pr["amt"] = 0.0

    # ---------- 4. Material Requests in range (by type) ----------
    mr_rows = _read_sql("""
    SELECT COALESCE(material_request_type, 'Other') AS mtype,
           COALESCE(status, 'Unknown')              AS stat,
           COUNT(name)                              AS cnt
    FROM `tabMaterial Request`
    WHERE docstatus < 2
      AND transaction_date BETWEEN %(f)s AND %(t)s
    GROUP BY material_request_type, status
""", {"f": from_date, "t": to_date}, as_dict=True)
    mr = []
    mr_count = 0
    for r in mr_rows:
        c = int(r.get("cnt") or 0)
        d = {}
        d["mtype"] = r.get("mtype")
        d["status"] = r.get("stat")
        d["count"] = c
        mr.append(d)
        mr_count = mr_count + c

    # ---------- 5. Open POs pending receipt (any date) ----------
    open_rows = _read_sql("""
    SELECT name, supplier, grand_total, status, transaction_date, per_received
    FROM `tabPurchase Order`
    WHERE docstatus = 1
      AND status IN ('To Receive and Bill', 'To Receive')
    ORDER BY transaction_date ASC
    LIMIT 50
""", {}, as_dict=True)
    open_po = []
    open_val = 0.0
    for r in open_rows:
        a = float(r.get("grand_total") or 0)
        d = {}
        d["id"] = r.get("name")
        d["supplier"] = r.get("supplier")
        d["amt"] = a
        d["status"] = r.get("status")
        d["date"] = r.get("transaction_date")
        d["received"] = float(r.get("per_received") or 0)
        open_po.append(d)
        open_val = open_val + a

    totals = {}
    totals["po_amt"] = po_total
    totals["po_count"] = po_count
    totals["pi_amt"] = pi["amt"]
    totals["pi_outstanding"] = pi["outstanding"]
    totals["pr_amt"] = pr["amt"]
    totals["mr_count"] = mr_count
    totals["open_po_count"] = len(open_po)
    totals["open_po_value"] = open_val

    out = {}
    out["from_date"] = from_date
    out["to_date"] = to_date
    out["po"] = po
    out["pi"] = pi
    out["pr"] = pr
    out["mr"] = mr
    out["open_po"] = open_po
    out["totals"] = totals
    frappe.response["message"] = out
