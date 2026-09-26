"""md_live_dashboard_api

Original API: md_live_dashboard_api
Source modified: 2026-08-02 11:46:06.213396
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
    #  SERVER SCRIPT (API)  —  md_live_dashboard_api  (v2, adds branch/warehouse filters)
    #  URL: /api/method/md_live_dashboard_api?from_date=...&to_date=...&branch=Himayathnagar&warehouse=Himayathnagar
    #
    #  `branch`     OPTIONAL — filters Selling (Sales Invoice.branch, exact link field)
    #               and, if the custom field exists, Payment Entry.branch too.
    #  `warehouse`  OPTIONAL — filters Stock Entry (to_warehouse LIKE) and
    #               Stock Balance / Bin (warehouse LIKE). Matches partial
    #               names, so "Himayathnagar" matches "Himayathnagar - LSACPL".
    #
    #  REPLACE the existing md_live_dashboard_api Server Script's `script`
    #  field with this file's contents to upgrade it in place.
    # =====================================================================

    args = frappe.form_dict or {}
    to_date = args.get("to_date")
    from_date = args.get("from_date")
    branch = (args.get("branch") or "").strip()
    warehouse = (args.get("warehouse") or "").strip()
    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.get_first_day(to_date)

    wh_like = "%" + warehouse + "%"
    pe_has_branch = bool(frappe.get_meta("Payment Entry").get_field("branch"))

    # ---------- 1. Payment Entries in range (branch-filterable if field exists) ----------
    if branch and pe_has_branch:
        pe_rows = _read_sql("""
        SELECT COALESCE(payment_type, 'Unknown') AS ptype,
               COUNT(name)                       AS cnt,
               SUM(paid_amount)                  AS amt
        FROM `tabPayment Entry`
        WHERE docstatus = 1
          AND posting_date BETWEEN %(f)s AND %(t)s
          AND branch = %(b)s
        GROUP BY payment_type
        ORDER BY amt DESC
    """, {"f": from_date, "t": to_date, "b": branch}, as_dict=True)
    else:
        pe_rows = _read_sql("""
        SELECT COALESCE(payment_type, 'Unknown') AS ptype,
               COUNT(name)                       AS cnt,
               SUM(paid_amount)                  AS amt
        FROM `tabPayment Entry`
        WHERE docstatus = 1
          AND posting_date BETWEEN %(f)s AND %(t)s
        GROUP BY payment_type
        ORDER BY amt DESC
    """, {"f": from_date, "t": to_date}, as_dict=True)

    pe = []
    pe_total = 0.0
    pe_count = 0
    for r in pe_rows:
        a = float(r.get("amt") or 0)
        c = int(r.get("cnt") or 0)
        pe.append({"type": r.get("ptype"), "count": c, "amt": a})
        pe_total = pe_total + a
        pe_count = pe_count + c

    pe_recent_filters = {"docstatus": ["<", 2]}
    if branch and pe_has_branch:
        pe_recent_filters["branch"] = branch
    pe_recent = frappe.get_all(
        "Payment Entry", filters=pe_recent_filters,
        fields=["name", "posting_date", "party_type", "party", "payment_type", "paid_amount", "status"],
        order_by="posting_date desc, creation desc", limit_page_length=25
    )

    # ---------- 2. Stock Entries in range (warehouse-filterable) ----------
    if warehouse:
        se_rows = _read_sql("""
        SELECT COALESCE(stock_entry_type, 'Unknown') AS stype, docstatus, COUNT(name) AS cnt
        FROM `tabStock Entry`
        WHERE posting_date BETWEEN %(f)s AND %(t)s
          AND (to_warehouse LIKE %(w)s OR from_warehouse LIKE %(w)s)
        GROUP BY stock_entry_type, docstatus
    """, {"f": from_date, "t": to_date, "w": wh_like}, as_dict=True)
        se_recent = _read_sql("""
        SELECT name, posting_date, stock_entry_type, from_warehouse, to_warehouse, docstatus
        FROM `tabStock Entry`
        WHERE (to_warehouse LIKE %(w)s OR from_warehouse LIKE %(w)s)
        ORDER BY posting_date DESC, creation DESC
        LIMIT 25
    """, {"w": wh_like}, as_dict=True)
    else:
        se_rows = _read_sql("""
        SELECT COALESCE(stock_entry_type, 'Unknown') AS stype, docstatus, COUNT(name) AS cnt
        FROM `tabStock Entry`
        WHERE posting_date BETWEEN %(f)s AND %(t)s
        GROUP BY stock_entry_type, docstatus
    """, {"f": from_date, "t": to_date}, as_dict=True)
        se_recent = _read_sql("""
        SELECT name, posting_date, stock_entry_type, from_warehouse, to_warehouse, docstatus
        FROM `tabStock Entry`
        ORDER BY posting_date DESC, creation DESC
        LIMIT 25
    """, {}, as_dict=True)

    se = []
    se_count = 0
    for r in se_rows:
        c = int(r.get("cnt") or 0)
        se.append({"type": r.get("stype"), "docstatus": int(r.get("docstatus") or 0), "count": c})
        se_count = se_count + c

    # ---------- 3. Stock Balance (Bin) — warehouse-filterable ----------
    if warehouse:
        bin_top = _read_sql("""
        SELECT item_code, warehouse, actual_qty, reserved_qty, projected_qty
        FROM `tabBin`
        WHERE actual_qty > 0 AND warehouse LIKE %(w)s
        ORDER BY actual_qty DESC LIMIT 30
    """, {"w": wh_like}, as_dict=True)
        bin_totals = _read_sql("""
        SELECT COUNT(*) AS rows_count, SUM(actual_qty) AS total_qty
        FROM `tabBin` WHERE actual_qty > 0 AND warehouse LIKE %(w)s
    """, {"w": wh_like}, as_dict=True)
    else:
        bin_top = _read_sql("""
        SELECT item_code, warehouse, actual_qty, reserved_qty, projected_qty
        FROM `tabBin`
        WHERE actual_qty > 0
        ORDER BY actual_qty DESC LIMIT 30
    """, {}, as_dict=True)
        bin_totals = _read_sql("""
        SELECT COUNT(*) AS rows_count, SUM(actual_qty) AS total_qty
        FROM `tabBin` WHERE actual_qty > 0
    """, {}, as_dict=True)

    stock_balance = {
        "rows_count": int(bin_totals[0].get("rows_count") or 0) if bin_totals else 0,
        "total_qty": float(bin_totals[0].get("total_qty") or 0) if bin_totals else 0.0,
        "top_items": bin_top
    }

    # ---------- 4. Selling — Sales Invoice (branch-filterable, confirmed field) ----------
    si_filters_range = {"docstatus": 1, "posting_date": ["between", [from_date, to_date]]}
    if branch:
        si_filters_range["branch"] = branch

    branch_clause = ""
    if branch:
        branch_clause = "AND branch = %(b)s"

    si_row = _read_sql("""
    SELECT COUNT(name) AS cnt, SUM(grand_total) AS amt, SUM(outstanding_amount) AS outs
    FROM `tabSales Invoice`
    WHERE docstatus = 1 AND posting_date BETWEEN %(f)s AND %(t)s
    """ + branch_clause + """
""", {"f": from_date, "t": to_date, "b": branch}, as_dict=True)
    si = {"count": 0, "amt": 0.0, "outstanding": 0.0}
    if si_row:
        si["count"] = int(si_row[0].get("cnt") or 0)
        si["amt"] = float(si_row[0].get("amt") or 0)
        si["outstanding"] = float(si_row[0].get("outs") or 0)

    si_status_rows = frappe.get_all(
        "Sales Invoice", filters=si_filters_range,
        fields=["status", "count(name) as cnt", "sum(grand_total) as amt"],
        group_by="status", order_by="amt desc"
    )

    si_recent = frappe.get_all(
        "Sales Invoice", filters={"docstatus": 1, "branch": branch} if branch else {"docstatus": 1},
        fields=["name", "posting_date", "customer", "grand_total", "outstanding_amount", "status"],
        order_by="posting_date desc, creation desc", limit_page_length=25
    )

    totals = {
        "pe_amt": pe_total, "pe_count": pe_count, "se_count": se_count,
        "stock_rows": stock_balance["rows_count"], "stock_qty": stock_balance["total_qty"],
        "si_amt": si["amt"], "si_outstanding": si["outstanding"], "si_count": si["count"]
    }

    out = {
        "from_date": from_date, "to_date": to_date, "branch": branch, "warehouse": warehouse,
        "payment_entry": {"by_type": pe, "recent": pe_recent},
        "stock_entry": {"by_type": se, "recent": se_recent},
        "stock_balance": stock_balance,
        "selling": {"summary": si, "by_status": si_status_rows, "recent": si_recent},
        "totals": totals
    }
    frappe.response["message"] = out
