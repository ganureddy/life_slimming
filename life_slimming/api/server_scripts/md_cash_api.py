"""md_cash_api

Original API: md_cash_api
Source modified: 2026-08-19 19:12:37.991137
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
    from_date = frappe.form_dict.get("from_date")
    to_date = frappe.form_dict.get("to_date")

    today = str(frappe.utils.nowdate())
    if not to_date:
        to_date = today
    to_date = str(to_date)

    result = {}

    # ================= TREASURY =================
    # GL Entry has cost_center (not branch). One cash ledger holds all branches,
    # split by cost_center. So we report BOTH by-branch (cost center) and by-account.

    # ---- account type lookup ----
    acc_types = _read_sql("""
    SELECT name, account_type
    FROM `tabAccount`
    WHERE is_group = 0 AND account_type IN ('Cash', 'Bank')
""", as_dict=True)
    type_map = {}
    for a in acc_types:
        type_map[a.get("name")] = a.get("account_type") or "Cash"

    # ---- balances grouped by (account, cost_center) up to a date ----
    def gl_grouped(cut):
        return _read_sql("""
        SELECT gle.account AS account, gle.cost_center AS cc,
               COALESCE(SUM(gle.debit - gle.credit), 0) AS bal
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.is_cancelled = 0
          AND gle.posting_date <= %(d)s
          AND acc.is_group = 0
          AND acc.account_type IN ('Cash', 'Bank')
        GROUP BY gle.account, gle.cost_center
    """, {"d": cut}, as_dict=True)

    rows_today = gl_grouped(today)
    rows_asof  = gl_grouped(to_date)

    def clean_cc(cc):
        if not cc:
            return "Unassigned"
        return cc.replace(" - LSACPL", "").strip()

    def clean_acc(a):
        return (a or "").replace(" - LSACPL", "").strip()

    # ---- aggregate per ACCOUNT and per BRANCH(cost center), for both dates ----
    acct_today = {}
    acct_asof  = {}
    br_today   = {}
    br_asof    = {}

    for r in rows_today:
        a = r.get("account"); cc = clean_cc(r.get("cc")); v = float(r.get("bal") or 0)
        atype = type_map.get(a, "Cash")
        acct_today[a] = acct_today.get(a, 0.0) + v
        key = (cc, atype)
        br_today[key] = br_today.get(key, 0.0) + v

    for r in rows_asof:
        a = r.get("account"); cc = clean_cc(r.get("cc")); v = float(r.get("bal") or 0)
        atype = type_map.get(a, "Cash")
        acct_asof[a] = acct_asof.get(a, 0.0) + v
        key = (cc, atype)
        br_asof[key] = br_asof.get(key, 0.0) + v

    # ---- per-account table ----
    acct_rows = []
    bank_today = 0.0; bank_asof = 0.0; cash_today = 0.0; cash_asof = 0.0
    all_a = {}
    for a in acct_today: all_a[a] = 1
    for a in acct_asof: all_a[a] = 1
    for a in all_a:
        bt = acct_today.get(a, 0.0); ba = acct_asof.get(a, 0.0)
        if bt == 0 and ba == 0:
            continue
        atype = type_map.get(a, "Cash")
        acct_rows.append({"account": clean_acc(a), "type": atype, "today": bt, "asof": ba})
        if atype == "Bank":
            bank_today += bt; bank_asof += ba
        else:
            cash_today += bt; cash_asof += ba
    def keyToday(r):
        return r["today"]
    acct_rows = sorted(acct_rows, key=keyToday, reverse=True)

    # ---- per-branch (cost center) table ----
    br_map = {}
    all_k = {}
    for k in br_today: all_k[k] = 1
    for k in br_asof: all_k[k] = 1
    for k in all_k:
        cc = k[0]; atype = k[1]
        if cc not in br_map:
            br_map[cc] = {"branch": cc, "cash_today": 0.0, "cash_asof": 0.0,
                          "bank_today": 0.0, "bank_asof": 0.0}
        bt = br_today.get(k, 0.0); ba = br_asof.get(k, 0.0)
        if atype == "Bank":
            br_map[cc]["bank_today"] += bt; br_map[cc]["bank_asof"] += ba
        else:
            br_map[cc]["cash_today"] += bt; br_map[cc]["cash_asof"] += ba

    branch_rows = []
    for cc in br_map:
        r = br_map[cc]
        r["total_today"] = r["cash_today"] + r["bank_today"]
        r["total_asof"]  = r["cash_asof"] + r["bank_asof"]
        if r["total_today"] == 0 and r["total_asof"] == 0:
            continue
        branch_rows.append(r)
    def keyTot(r):
        return r["total_today"]
    branch_rows = sorted(branch_rows, key=keyTot, reverse=True)

    result["accounts"] = acct_rows
    result["branch_cash"] = branch_rows
    result["treasury"] = {
        "bank_today": bank_today, "bank_asof": bank_asof,
        "cash_today": cash_today, "cash_asof": cash_asof,
        "total_today": bank_today + cash_today,
        "total_asof": bank_asof + cash_asof,
        "account_count": len(acct_rows),
        "branch_count": len(branch_rows)
    }

    # ================= RECEIVABLES AGEING (by branch) =================
    inv = _read_sql("""
    SELECT
        si.branch AS branch,
        SUM(si.outstanding_amount) AS total,
        SUM(CASE WHEN DATEDIFF(%(d)s, si.posting_date) <= 0 THEN si.outstanding_amount ELSE 0 END) AS cur,
        SUM(CASE WHEN DATEDIFF(%(d)s, si.posting_date) BETWEEN 1 AND 30 THEN si.outstanding_amount ELSE 0 END) AS b1,
        SUM(CASE WHEN DATEDIFF(%(d)s, si.posting_date) BETWEEN 31 AND 60 THEN si.outstanding_amount ELSE 0 END) AS b2,
        SUM(CASE WHEN DATEDIFF(%(d)s, si.posting_date) > 60 THEN si.outstanding_amount ELSE 0 END) AS b3,
        SUM(CASE WHEN si.due_date IS NOT NULL AND DATEDIFF(%(d)s, si.due_date) > 0 THEN si.outstanding_amount ELSE 0 END) AS overdue,
        COUNT(si.name) AS bills
    FROM `tabSales Invoice` si
    WHERE si.docstatus = 1
      AND si.outstanding_amount > 0
    GROUP BY si.branch
""", {"d": to_date}, as_dict=True)

    age_rows = []
    tot = {"current": 0.0, "b1": 0.0, "b2": 0.0, "b3": 0.0, "total": 0.0, "overdue": 0.0, "bills": 0}
    for row in inv:
        b = row.get("branch") or "Unknown"
        slot = {
            "branch": b,
            "current": float(row.get("cur") or 0),
            "b1": float(row.get("b1") or 0),
            "b2": float(row.get("b2") or 0),
            "b3": float(row.get("b3") or 0),
            "total": float(row.get("total") or 0),
            "overdue": float(row.get("overdue") or 0),
            "bills": int(row.get("bills") or 0)
        }
        age_rows.append(slot)
        tot["current"] += slot["current"]; tot["b1"] += slot["b1"]; tot["b2"] += slot["b2"]
        tot["b3"] += slot["b3"]; tot["total"] += slot["total"]; tot["overdue"] += slot["overdue"]
        tot["bills"] += slot["bills"]
    def keyAgeTot(r):
        return r["total"]
    age_rows = sorted(age_rows, key=keyAgeTot, reverse=True)

    result["ageing"] = age_rows
    result["ageing_totals"] = tot
    result["as_on"] = to_date
    result["today"] = today

    frappe.response["message"] = result
