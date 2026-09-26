"""md_indent_report_api

Original API: md_indent_report_api
Source modified: 2026-08-03 11:55:24.607893
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
    #  SERVER SCRIPT (API)  —  md_indent_report_api
    #  Script Type : API   ·   API Method : md_indent_report_api
    #
    #  /api/method/md_indent_report_api?from_date=...&to_date=...&warehouse=...
    #
    #  Rebuilds the "HO Stock Ledger / Purchase & GRN / Dispatch / Branch
    #  Position / Returns" report using only fields confirmed to exist:
    #   - Purchased: Purchase Invoice + Purchase Invoice Item (real GST via
    #     grand_total - base_net_total, PO/PR links, paid/due, status)
    #   - Sent to branch: Stock Entry where is_return = 0, Material Transfer,
    #     from_warehouse = HO. Uses custom_stock_released_by / custom_sending_method.
    #   - Returned to HO: Stock Entry where is_return = 1 (a REAL checkbox
    #     field on this doctype — not inferred). Uses custom_received_by,
    #     custom_received_date, remarks / custom_branch_receipt_remarks as
    #     free-text notes (there is no fixed reason/condition enum in your
    #     system, so none is fabricated here).
    #   - Indent linkage: Material Request, using custom_priority,
    #     transfer_status, per_received, custom_stock_entry_reference.
    #   - Branch position: Bin (current balance) + Stock Ledger Entry
    #     (consumption = negative movement).
    #
    #  NOT included — no matching field/doctype: a structured "Damage /
    #  Adjustment Register" with reason codes and approval workflow. If you
    #  have or want a doctype for that, tell me and I'll wire it in.
    #
    #  HOW TO INSTALL: Setup -> Server Script -> New -> API -> API Method:
    #  md_indent_report_api -> paste this file -> Save.
    # =====================================================================

    args = frappe.form_dict or {}
    to_date = args.get("to_date")
    from_date = args.get("from_date")
    warehouse = (args.get("warehouse") or "").strip()
    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.add_months(to_date, -12)

    wh_like = "%" + warehouse + "%"

    # ---------- Purchased at HO ----------
    if warehouse:
        purchased = _read_sql("""
        SELECT pi.name AS invoice, pi.posting_date AS date, pi.supplier AS supplier,
               pii.item_code AS item_code, pii.item_name AS item_name, pii.qty AS qty,
               pii.rate AS rate, pii.amount AS taxable, pi.grand_total AS invoice_total,
               pi.outstanding_amount AS due, pi.status AS status,
               pii.purchase_receipt AS receipt, pii.warehouse AS warehouse
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.docstatus = 1 AND pi.posting_date BETWEEN %(f)s AND %(t)s
              AND pii.warehouse LIKE %(w)s
        ORDER BY pi.posting_date DESC LIMIT 80
    """, {"f": from_date, "t": to_date, "w": wh_like}, as_dict=True)
    else:
        purchased = _read_sql("""
        SELECT pi.name AS invoice, pi.posting_date AS date, pi.supplier AS supplier,
               pii.item_code AS item_code, pii.item_name AS item_name, pii.qty AS qty,
               pii.rate AS rate, pii.amount AS taxable, pi.grand_total AS invoice_total,
               pi.outstanding_amount AS due, pi.status AS status,
               pii.purchase_receipt AS receipt, pii.warehouse AS warehouse
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.docstatus = 1 AND pi.posting_date BETWEEN %(f)s AND %(t)s
        ORDER BY pi.posting_date DESC LIMIT 80
    """, {"f": from_date, "t": to_date}, as_dict=True)

    purchase_totals = _read_sql("""
    SELECT SUM(pii.qty) AS qty, SUM(pi.grand_total) AS worth, COUNT(DISTINCT pi.name) AS invoices,
           COUNT(DISTINCT pi.supplier) AS vendors
    FROM `tabPurchase Invoice Item` pii
    JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
    WHERE pi.docstatus = 1 AND pi.posting_date BETWEEN %(f)s AND %(t)s
""", {"f": from_date, "t": to_date}, as_dict=True)
    pt = purchase_totals[0] if purchase_totals else {}

    # ---------- Sent out to branches (Stock Entry, not a return) ----------
    sent = _read_sql("""
    SELECT se.name AS voucher, se.posting_date AS date, se.from_warehouse AS from_wh,
           se.to_warehouse AS to_wh, sed.item_code AS item_code, sed.item_name AS item_name,
           sed.qty AS qty, sed.basic_rate AS rate, sed.basic_amount AS worth,
           se.custom_stock_released_by AS released_by, se.custom_sending_method AS method,
           se.docstatus AS docstatus
    FROM `tabStock Entry Detail` sed
    JOIN `tabStock Entry` se ON se.name = sed.parent
    WHERE se.docstatus = 1 AND se.stock_entry_type = 'Material Transfer'
          AND (se.is_return IS NULL OR se.is_return = 0)
          AND se.posting_date BETWEEN %(f)s AND %(t)s
          AND se.to_warehouse IS NOT NULL
    ORDER BY se.posting_date DESC LIMIT 80
""", {"f": from_date, "t": to_date}, as_dict=True)

    sent_totals = _read_sql("""
    SELECT SUM(sed.qty) AS qty, SUM(sed.basic_amount) AS worth, COUNT(DISTINCT se.name) AS vouchers
    FROM `tabStock Entry Detail` sed
    JOIN `tabStock Entry` se ON se.name = sed.parent
    WHERE se.docstatus = 1 AND se.stock_entry_type = 'Material Transfer'
          AND (se.is_return IS NULL OR se.is_return = 0)
          AND se.posting_date BETWEEN %(f)s AND %(t)s AND se.to_warehouse IS NOT NULL
""", {"f": from_date, "t": to_date}, as_dict=True)
    st = sent_totals[0] if sent_totals else {}

    # ---------- Indent (Material Request) linkage ----------
    indents = _read_sql("""
    SELECT mr.name AS indent_no, mr.transaction_date AS requested_date, mr.schedule_date AS required_by,
           mr.set_warehouse AS branch, mr.status AS status, mr.custom_priority AS priority,
           mr.transfer_status AS transfer_status, mr.per_received AS per_received,
           mr.custom_stock_entry_reference AS stock_entry
    FROM `tabMaterial Request` mr
    WHERE mr.docstatus < 2 AND mr.transaction_date BETWEEN %(f)s AND %(t)s
    ORDER BY mr.transaction_date DESC LIMIT 80
""", {"f": from_date, "t": to_date}, as_dict=True)

    # ---------- Returned to HO (real is_return flag) ----------
    returned = _read_sql("""
    SELECT se.name AS voucher, se.posting_date AS date, se.from_warehouse AS from_wh,
           se.to_warehouse AS to_wh, sed.item_code AS item_code, sed.item_name AS item_name,
           sed.qty AS qty, sed.basic_amount AS worth, se.custom_received_by AS received_by,
           se.custom_received_date AS received_date, se.remarks AS remarks,
           se.custom_branch_receipt_remarks AS branch_remarks, se.docstatus AS docstatus
    FROM `tabStock Entry Detail` sed
    JOIN `tabStock Entry` se ON se.name = sed.parent
    WHERE se.docstatus = 1 AND se.is_return = 1
          AND se.posting_date BETWEEN %(f)s AND %(t)s
    ORDER BY se.posting_date DESC LIMIT 80
""", {"f": from_date, "t": to_date}, as_dict=True)

    returned_totals = _read_sql("""
    SELECT SUM(sed.qty) AS qty, SUM(sed.basic_amount) AS worth, COUNT(DISTINCT se.name) AS vouchers
    FROM `tabStock Entry Detail` sed
    JOIN `tabStock Entry` se ON se.name = sed.parent
    WHERE se.docstatus = 1 AND se.is_return = 1 AND se.posting_date BETWEEN %(f)s AND %(t)s
""", {"f": from_date, "t": to_date}, as_dict=True)
    rt = returned_totals[0] if returned_totals else {}

    # ---------- Branch-wise position ----------
    branch_position = _read_sql("""
    SELECT se.to_warehouse AS branch,
           COUNT(DISTINCT se.name) AS indents,
           SUM(sed.qty) AS received_qty, SUM(sed.basic_amount) AS received_worth
    FROM `tabStock Entry Detail` sed
    JOIN `tabStock Entry` se ON se.name = sed.parent
    WHERE se.docstatus = 1 AND se.stock_entry_type = 'Material Transfer'
          AND (se.is_return IS NULL OR se.is_return = 0)
          AND se.posting_date BETWEEN %(f)s AND %(t)s AND se.to_warehouse IS NOT NULL
    GROUP BY se.to_warehouse ORDER BY received_worth DESC LIMIT 20
""", {"f": from_date, "t": to_date}, as_dict=True)

    branch_returns = _read_sql("""
    SELECT se.from_warehouse AS branch, SUM(sed.qty) AS qty, SUM(sed.basic_amount) AS worth
    FROM `tabStock Entry Detail` sed
    JOIN `tabStock Entry` se ON se.name = sed.parent
    WHERE se.docstatus = 1 AND se.is_return = 1 AND se.posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY se.from_warehouse
""", {"f": from_date, "t": to_date}, as_dict=True)
    returns_map = {}
    for r in branch_returns:
        returns_map[r["branch"]] = {"qty": float(r.get("qty") or 0), "worth": float(r.get("worth") or 0)}

    branch_bin = _read_sql("""
    SELECT warehouse, SUM(actual_qty) AS qty, SUM(stock_value) AS worth
    FROM `tabBin` WHERE actual_qty != 0 GROUP BY warehouse
""", {}, as_dict=True)
    bin_map = {}
    for r in branch_bin:
        bin_map[r["warehouse"]] = {"qty": float(r.get("qty") or 0), "worth": float(r.get("worth") or 0)}

    branch_position_out = []
    for r in branch_position:
        br = r["branch"]
        rec_qty = float(r.get("received_qty") or 0)
        ret = returns_map.get(br, {"qty": 0.0, "worth": 0.0})
        bal = bin_map.get(br, {"qty": 0.0, "worth": 0.0})
        consumed = rec_qty - ret["qty"] - bal["qty"]
        if consumed < 0:
            consumed = 0
        burn_pct = 0.0
        if rec_qty > 0:
            burn_pct = (consumed / rec_qty) * 100
        branch_position_out.append({
            "branch": br, "indents": int(r.get("indents") or 0),
            "received_qty": rec_qty, "received_worth": float(r.get("received_worth") or 0),
            "returned_qty": ret["qty"], "returned_worth": ret["worth"],
            "consumed_qty": consumed, "bal_qty": bal["qty"], "bal_worth": bal["worth"],
            "burn_pct": burn_pct
        })

    # ---------- HO Stock Ledger (per item roll-up) ----------
    ho_ledger = _read_sql("""
    SELECT pii.item_code AS item_code, pii.item_name AS item_name,
           SUM(pii.qty) AS purchased_qty, SUM(pii.amount) AS purchase_worth
    FROM `tabPurchase Invoice Item` pii
    JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
    WHERE pi.docstatus = 1 AND pi.posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY pii.item_code, pii.item_name
    ORDER BY purchase_worth DESC LIMIT 60
""", {"f": from_date, "t": to_date}, as_dict=True)

    item_codes = []
    for r in ho_ledger:
        if r.get("item_code"):
            item_codes.append(r["item_code"])

    sent_map = {}
    returned_map = {}
    bin_item_map = {}
    if item_codes:
        sent_rows = _read_sql("""
        SELECT sed.item_code AS item_code, SUM(sed.qty) AS qty, SUM(sed.basic_amount) AS worth,
               COUNT(DISTINCT se.name) AS cnt
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON se.name = sed.parent
        WHERE se.docstatus = 1 AND se.stock_entry_type = 'Material Transfer'
              AND (se.is_return IS NULL OR se.is_return = 0)
              AND se.posting_date BETWEEN %(f)s AND %(t)s AND sed.item_code IN %(items)s
        GROUP BY sed.item_code
    """, {"f": from_date, "t": to_date, "items": tuple(item_codes)}, as_dict=True)
        for r in sent_rows:
            sent_map[r["item_code"]] = r

        ret_rows = _read_sql("""
        SELECT sed.item_code AS item_code, SUM(sed.qty) AS qty
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON se.name = sed.parent
        WHERE se.docstatus = 1 AND se.is_return = 1
              AND se.posting_date BETWEEN %(f)s AND %(t)s AND sed.item_code IN %(items)s
        GROUP BY sed.item_code
    """, {"f": from_date, "t": to_date, "items": tuple(item_codes)}, as_dict=True)
        for r in ret_rows:
            returned_map[r["item_code"]] = float(r.get("qty") or 0)

        bin_rows = _read_sql("""
        SELECT item_code, warehouse, actual_qty, stock_value FROM `tabBin`
        WHERE item_code IN %(items)s AND actual_qty != 0
    """, {"items": tuple(item_codes)}, as_dict=True)
        for r in bin_rows:
            m = bin_item_map.setdefault(r["item_code"], {"ho_qty": 0.0, "ho_worth": 0.0, "branch_qty": 0.0})
            if r["warehouse"] and "stores" in r["warehouse"].lower():
                m["ho_qty"] = m["ho_qty"] + float(r["actual_qty"] or 0)
                m["ho_worth"] = m["ho_worth"] + float(r["stock_value"] or 0)
            else:
                m["branch_qty"] = m["branch_qty"] + float(r["actual_qty"] or 0)

    ho_ledger_out = []
    for r in ho_ledger:
        ic = r["item_code"]
        sm = sent_map.get(ic, {})
        bm = bin_item_map.get(ic, {"ho_qty": 0.0, "ho_worth": 0.0, "branch_qty": 0.0})
        ho_ledger_out.append({
            "item_code": ic, "item_name": r["item_name"],
            "purchased_qty": float(r.get("purchased_qty") or 0), "purchase_worth": float(r.get("purchase_worth") or 0),
            "sent_count": int(sm.get("cnt") or 0), "sent_qty": float(sm.get("qty") or 0), "sent_worth": float(sm.get("worth") or 0),
            "returned_qty": returned_map.get(ic, 0.0),
            "ho_bal_qty": bm["ho_qty"], "ho_bal_worth": bm["ho_worth"], "branch_bal_qty": bm["branch_qty"]
        })

    frappe.response["message"] = {
        "from_date": from_date, "to_date": to_date,
        "kpis": {
            "purchased_qty": float(pt.get("qty") or 0), "purchased_worth": float(pt.get("worth") or 0),
            "purchased_invoices": int(pt.get("invoices") or 0), "purchased_vendors": int(pt.get("vendors") or 0),
            "sent_qty": float(st.get("qty") or 0), "sent_worth": float(st.get("worth") or 0), "sent_vouchers": int(st.get("vouchers") or 0),
            "returned_qty": float(rt.get("qty") or 0), "returned_worth": float(rt.get("worth") or 0), "returned_vouchers": int(rt.get("vouchers") or 0)
        },
        "ho_ledger": ho_ledger_out,
        "purchased": purchased,
        "sent": sent,
        "indents": indents,
        "returned": returned,
        "branch_position": branch_position_out
    }
