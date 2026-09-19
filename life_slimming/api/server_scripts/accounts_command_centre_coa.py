"""accounts_command_centre_coa

Original API: accounts_command_centre_coa
Source modified: 2026-09-01 17:31:31.774801
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
    #  Name        : accounts_command_centre_coa
    #  Allow Guest : NO
    #
    #  Real Chart of Accounts + live ledger balances, optionally filtered
    #  by cost center. Powers the Chart of Accounts and Ledger Books tabs.
    #
    #  safe_exec SAFE: no .format(), no f-strings, no imports.
    #  Args: cost_center (optional, "ALL" or a cost center name)
    #        upto (optional posting date, default today)
    # =====================================================================

    cc     = frappe.form_dict.get("cost_center")
    upto   = frappe.form_dict.get("upto")
    if not cc:
        cc = "ALL"
    BRANCH_CC_MAP = {
        "HO": "Main - LSACPL",
        "MP": "Madhapur - LSACPL",
        "BH": "Banjara Hills - LSACPL",
        "CN": "Chandanagar - LSACPL",
        "CHN": "Chandanagar - LSACPL",
        "SRN": "SR Nagar - LSACPL",
        "HN": "Himayathnagar - LSACPL",
        "DN": "Dilsukhnagar - LSACPL",
        "DSK": "Dilsukhnagar - LSACPL",
        "GB": "Gachibowli - LSACPL",
        "GCB": "Gachibowli - LSACPL",
        "KP": "Kukatpally - LSACPL",
        "VW": "Vijayawada - LSACPL",
        "VJA": "Vijayawada - LSACPL",
        "VZ": "Vizag - LSACPL",
        "NLR": "Nellore - LSACPL"
    }
    if cc != "ALL":
        mapped_cc = BRANCH_CC_MAP.get(cc)
        if mapped_cc:
            cc = mapped_cc
        if not frappe.db.exists("Cost Center", cc):
            frappe.throw("Unknown branch / Cost Center: " + str(cc))

    if not upto:
        upto = frappe.utils.nowdate()

    use_cc = 0
    if cc != "ALL":
        use_cc = 1

    # ---------------------------------------------------------------------
    # 1+2. FULL CHART OF ACCOUNTS with live balances computed inline.
    #    Balance = SUM(debit) - SUM(credit) from GL Entry per account,
    #    optionally filtered by cost center. Done as correlated subqueries
    #    so we never assign to a dict subscript (safe_exec restriction).
    # ---------------------------------------------------------------------
    cc_clause = ""
    if use_cc:
        cc_clause = " AND gle.cost_center = %(cc)s "

    acc_sql = (
        "SELECT acc.name AS acc, acc.account_name AS label, "
        "acc.account_number AS num, acc.parent_account AS parent, "
        "acc.root_type AS root, acc.account_type AS atype, "
        "COALESCE((SELECT SUM(gle.debit) FROM `tabGL Entry` gle "
        "  WHERE gle.account = acc.name AND gle.is_cancelled = 0 "
        "  AND gle.posting_date <= %(upto)s " + cc_clause + "),0) AS dr, "
        "COALESCE((SELECT SUM(gle.credit) FROM `tabGL Entry` gle "
        "  WHERE gle.account = acc.name AND gle.is_cancelled = 0 "
        "  AND gle.posting_date <= %(upto)s " + cc_clause + "),0) AS cr, "
        "COALESCE((SELECT SUM(gle.debit) - SUM(gle.credit) FROM `tabGL Entry` gle "
        "  WHERE gle.account = acc.name AND gle.is_cancelled = 0 "
        "  AND gle.posting_date <= %(upto)s " + cc_clause + "),0) AS balance "
        "FROM `tabAccount` acc "
        "WHERE acc.is_group = 0 "
        "ORDER BY acc.root_type, acc.account_number, acc.account_name"
    )
    accounts = _read_sql(acc_sql, {"upto": upto, "cc": cc}, as_dict=True)

    # ---------------------------------------------------------------------
    # 3. ROOT-TYPE TOTALS (Asset / Liability / Equity / Income / Expense)
    # ---------------------------------------------------------------------
    root_totals = _read_sql("""
    SELECT acc.root_type AS root,
           SUM(gle.debit) - SUM(gle.credit) AS balance
    FROM `tabGL Entry` gle
    INNER JOIN `tabAccount` acc ON acc.name = gle.account
    WHERE gle.is_cancelled = 0
      AND gle.posting_date <= %(upto)s
    GROUP BY acc.root_type
""", {"upto": upto}, as_dict=True)

    # ---------------------------------------------------------------------
    # 4. CASH POSITION: single cash ledger 173001, split by COST CENTER.
    #    (Branch separation is by cost center, not by separate accounts.)
    # ---------------------------------------------------------------------
    CASH_ACCOUNT = "173001 - Cash in Hand - LSACPL"

    branch_cash = _read_sql("""
    SELECT COALESCE(gle.cost_center, 'Unassigned') AS label,
           SUM(gle.debit) AS dr,
           SUM(gle.credit) AS cr,
           SUM(gle.debit) - SUM(gle.credit) AS balance
    FROM `tabGL Entry` gle
    WHERE gle.account = %(cash)s
      AND gle.is_cancelled = 0
      AND gle.posting_date <= %(upto)s
    GROUP BY COALESCE(gle.cost_center, 'Unassigned')
    ORDER BY balance DESC
""", {"cash": CASH_ACCOUNT, "upto": upto}, as_dict=True)

    # total cash-in-hand across all cost centers (net)
    cash_total = _read_sql("""
    SELECT SUM(gle.debit) - SUM(gle.credit) AS balance
    FROM `tabGL Entry` gle
    WHERE gle.account = %(cash)s
      AND gle.is_cancelled = 0
      AND gle.posting_date <= %(upto)s
""", {"cash": CASH_ACCOUNT, "upto": upto}, as_dict=True)

    # ---------------------------------------------------------------------
    # 5. COST CENTER list (for the filter dropdown)
    # ---------------------------------------------------------------------
    cost_centers = _read_sql("""
    SELECT name AS cc, cost_center_name AS label
    FROM `tabCost Center`
    WHERE is_group = 0
    ORDER BY cost_center_name
""", as_dict=True)

    # ---------------------------------------------------------------------
    # RESPONSE
    # ---------------------------------------------------------------------
    frappe.response["message"] = {
        "meta": {"cost_center": cc, "upto": upto,
                 "account_count": len(accounts),
                 "generated_at": frappe.utils.now()},
        "accounts": accounts,
        "root_totals": root_totals,
        "branch_cash": branch_cash,
        "cash_total": (cash_total[0].get("balance") if cash_total else 0),
        "cost_centers": cost_centers
    }
