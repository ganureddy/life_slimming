"""accounts_command_centre_ledger

Original API: accounts_command_centre_ledger
Source modified: 2026-09-01 17:30:54.632279
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
    #  Name        : accounts_command_centre_ledger
    #  Allow Guest : NO
    #
    #  General Ledger + Profit & Loss + Bank Account ledgers.
    #  All GL-based reads, filtered by cost center + date range.
    #
    #  safe_exec SAFE: no .format(), no f-strings, no imports,
    #  no dict-subscript assignment. SQL built via + concatenation.
    #
    #  Args:
    #    mode        : "ledger" | "pl" | "bank"  (default "pl")
    #    account     : (ledger mode) specific GL account, optional
    #    cost_center : "ALL" or a cost center, optional
    #    from_date   : YYYY-MM-DD (default month start)
    #    to_date     : YYYY-MM-DD (default today)
    # =====================================================================

    mode    = frappe.form_dict.get("mode")
    account = frappe.form_dict.get("account")
    cc      = frappe.form_dict.get("cost_center")
    fd      = frappe.form_dict.get("from_date")
    td      = frappe.form_dict.get("to_date")

    if not mode:
        mode = "pl"
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

    if not td:
        td = frappe.utils.nowdate()
    if not fd:
        fd = td[:7] + "-01"

    use_cc = 0
    if cc != "ALL":
        use_cc = 1

    cc_clause = ""
    if use_cc:
        cc_clause = " AND gle.cost_center = %(cc)s "

    params = {"cc": cc, "fd": fd, "td": td, "account": account}

    # =====================================================================
    #  MODE 1 : GENERAL LEDGER (transaction list for an account or all)
    # =====================================================================
    if mode == "ledger":
        led_sql = (
            "SELECT gle.posting_date AS d, gle.account AS account, "
            "gle.cost_center AS cc, gle.voucher_type AS vtype, "
            "gle.voucher_no AS voucher, gle.against AS against, "
            "gle.debit AS debit, gle.credit AS credit, "
            "gle.remarks AS remarks "
            "FROM `tabGL Entry` gle "
            "WHERE gle.is_cancelled = 0 "
            "AND gle.posting_date BETWEEN %(fd)s AND %(td)s " + cc_clause
        )
        if account:
            led_sql = led_sql + " AND gle.account = %(account)s "
        led_sql = led_sql + " ORDER BY gle.posting_date DESC, gle.creation DESC LIMIT 500"
        entries = _read_sql(led_sql, params, as_dict=True)

        # running totals for the filtered set
        tot_sql = (
            "SELECT SUM(gle.debit) AS dr, SUM(gle.credit) AS cr "
            "FROM `tabGL Entry` gle "
            "WHERE gle.is_cancelled = 0 "
            "AND gle.posting_date BETWEEN %(fd)s AND %(td)s " + cc_clause
        )
        if account:
            tot_sql = tot_sql + " AND gle.account = %(account)s "
        totals = _read_sql(tot_sql, params, as_dict=True)

        # distinct accounts for the picker
        accounts = _read_sql("""
        SELECT name AS acc, account_name AS label
        FROM `tabAccount` WHERE is_group = 0
        ORDER BY account_name
    """, as_dict=True)

        frappe.response["message"] = {
            "mode": "ledger",
            "meta": {"cost_center": cc, "from_date": fd, "to_date": td, "account": account},
            "entries": entries,
            "totals": (totals[0] if totals else {}),
            "accounts": accounts
        }

    # =====================================================================
    #  MODE 2 : PROFIT & LOSS  (Income vs Expense by account)
    # =====================================================================
    elif mode == "pl":
        # income accounts (credit positive)
        inc_sql = (
            "SELECT acc.name AS acc, acc.account_name AS label, "
            "SUM(gle.credit) - SUM(gle.debit) AS amount "
            "FROM `tabGL Entry` gle "
            "INNER JOIN `tabAccount` acc ON acc.name = gle.account "
            "WHERE gle.is_cancelled = 0 AND acc.root_type = 'Income' "
            "AND gle.posting_date BETWEEN %(fd)s AND %(td)s " + cc_clause +
            " GROUP BY acc.name, acc.account_name "
            "HAVING amount <> 0 ORDER BY amount DESC"
        )
        income = _read_sql(inc_sql, params, as_dict=True)

        # expense accounts (debit positive)
        exp_sql = (
            "SELECT acc.name AS acc, acc.account_name AS label, "
            "SUM(gle.debit) - SUM(gle.credit) AS amount "
            "FROM `tabGL Entry` gle "
            "INNER JOIN `tabAccount` acc ON acc.name = gle.account "
            "WHERE gle.is_cancelled = 0 AND acc.root_type = 'Expense' "
            "AND gle.posting_date BETWEEN %(fd)s AND %(td)s " + cc_clause +
            " GROUP BY acc.name, acc.account_name "
            "HAVING amount <> 0 ORDER BY amount DESC"
        )
        expense = _read_sql(exp_sql, params, as_dict=True)

        inc_total = _read_sql(
            "SELECT SUM(gle.credit) - SUM(gle.debit) AS t "
            "FROM `tabGL Entry` gle INNER JOIN `tabAccount` acc ON acc.name = gle.account "
            "WHERE gle.is_cancelled = 0 AND acc.root_type = 'Income' "
            "AND gle.posting_date BETWEEN %(fd)s AND %(td)s " + cc_clause,
            params, as_dict=True)
        exp_total = _read_sql(
            "SELECT SUM(gle.debit) - SUM(gle.credit) AS t "
            "FROM `tabGL Entry` gle INNER JOIN `tabAccount` acc ON acc.name = gle.account "
            "WHERE gle.is_cancelled = 0 AND acc.root_type = 'Expense' "
            "AND gle.posting_date BETWEEN %(fd)s AND %(td)s " + cc_clause,
            params, as_dict=True)

        it = (inc_total[0].get("t") or 0) if inc_total else 0
        et = (exp_total[0].get("t") or 0) if exp_total else 0

        frappe.response["message"] = {
            "mode": "pl",
            "meta": {"cost_center": cc, "from_date": fd, "to_date": td},
            "income": income,
            "expense": expense,
            "income_total": it,
            "expense_total": et,
            "net_profit": it - et
        }

    # =====================================================================
    #  MODE 4 : REPORTS  (Balance Sheet + P&L summary, ERPNext-standard)
    # =====================================================================
    elif mode == "reports":
        # Balance Sheet: Asset / Liability / Equity balances up to to_date
        bs = _read_sql("""
        SELECT acc.root_type AS root, acc.name AS acc, acc.account_name AS label,
               SUM(gle.debit) - SUM(gle.credit) AS balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.is_cancelled = 0
          AND acc.root_type IN ('Asset','Liability','Equity')
          AND gle.posting_date <= %(td)s
        GROUP BY acc.root_type, acc.name, acc.account_name
        HAVING balance <> 0
        ORDER BY acc.root_type, balance DESC
    """, {"td": td}, as_dict=True)

        bs_totals = _read_sql("""
        SELECT acc.root_type AS root,
               SUM(gle.debit) - SUM(gle.credit) AS balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.is_cancelled = 0
          AND acc.root_type IN ('Asset','Liability','Equity')
          AND gle.posting_date <= %(td)s
        GROUP BY acc.root_type
    """, {"td": td}, as_dict=True)

        # P&L totals for the period (income - expense = profit -> equity)
        pl_period = _read_sql("""
        SELECT acc.root_type AS root,
               SUM(gle.credit) - SUM(gle.debit) AS credit_bal,
               SUM(gle.debit) - SUM(gle.credit) AS debit_bal
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.is_cancelled = 0
          AND acc.root_type IN ('Income','Expense')
          AND gle.posting_date BETWEEN %(fd)s AND %(td)s
        GROUP BY acc.root_type
    """, {"fd": fd, "td": td}, as_dict=True)

        frappe.response["message"] = {
            "mode": "reports",
            "meta": {"from_date": fd, "to_date": td},
            "balance_sheet": bs,
            "bs_totals": bs_totals,
            "pl_period": pl_period
        }

    # =====================================================================
    #  MODE 3 : BANK ACCOUNTS  (bank-type account ledgers + balances)
    # =====================================================================
    else:
        # all bank-type GL accounts with running balance up to to_date
        banks = _read_sql("""
        SELECT acc.name AS acc, acc.account_name AS label,
               COALESCE((
                   SELECT SUM(g.debit) - SUM(g.credit)
                   FROM `tabGL Entry` g
                   WHERE g.account = acc.name AND g.is_cancelled = 0
                     AND g.posting_date <= %(td)s
               ),0) AS balance,
               COALESCE((
                   SELECT SUM(g.debit) - SUM(g.credit)
                   FROM `tabGL Entry` g
                   WHERE g.account = acc.name AND g.is_cancelled = 0
                     AND g.posting_date BETWEEN %(fd)s AND %(td)s
               ),0) AS period_movement
        FROM `tabAccount` acc
        WHERE acc.account_type = 'Bank' AND acc.is_group = 0
        ORDER BY acc.account_name
    """, {"fd": fd, "td": td}, as_dict=True)

        # recent bank transactions (GL entries against bank accounts)
        bank_txns = _read_sql("""
        SELECT gle.posting_date AS d, gle.account AS account,
               gle.voucher_type AS vtype, gle.voucher_no AS voucher,
               gle.against AS against, gle.debit AS debit,
               gle.credit AS credit, gle.remarks AS remarks
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.is_cancelled = 0 AND acc.account_type = 'Bank'
          AND gle.posting_date BETWEEN %(fd)s AND %(td)s
        ORDER BY gle.posting_date DESC, gle.creation DESC
        LIMIT 200
    """, {"fd": fd, "td": td}, as_dict=True)

        frappe.response["message"] = {
            "mode": "bank",
            "meta": {"from_date": fd, "to_date": td},
            "banks": banks,
            "bank_txns": bank_txns
        }
