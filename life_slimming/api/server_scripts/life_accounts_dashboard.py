"""life_accounts_dashboard

Original API: life_accounts_dashboard
Source modified: 2026-07-15 05:48:22.486139
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
    COMPANY = "Life Slimming And Cosmetic Pvt Ltd"

    if frappe.session.user == "Guest":
        frappe.throw("Login required")

    action = frappe.form_dict.get("action") or "summary"
    from_date = frappe.form_dict.get("from_date")
    to_date = frappe.form_dict.get("to_date")

    if action == "bootstrap":
        accounts = _read_sql("""
        SELECT name, account_name, parent_account, root_type,
               is_group, account_type, account_number
        FROM `tabAccount`
        WHERE company = %s AND disabled = 0
        ORDER BY lft ASC
    """, (COMPANY,), as_dict=1)

        ccs = _read_sql("""
        SELECT name, cost_center_name, is_group
        FROM `tabCost Center`
        WHERE company = %s AND disabled = 0 AND is_group = 0
        ORDER BY cost_center_name ASC
    """, (COMPANY,), as_dict=1)

        frappe.response["message"] = {"accounts": accounts, "cost_centers": ccs}

    elif action == "summary":
        if not from_date or not to_date:
            frappe.throw("from_date and to_date are required")
        fd = frappe.utils.getdate(from_date)
        td = frappe.utils.getdate(to_date)

        pl = _read_sql("""
        SELECT account, IFNULL(cost_center, '') AS cost_center,
               SUM(debit) AS dr, SUM(credit) AS cr
        FROM `tabGL Entry`
        WHERE is_cancelled = 0 AND company = %s
          AND posting_date BETWEEN %s AND %s
        GROUP BY account, cost_center
    """, (COMPANY, fd, td), as_dict=1)

        bs = _read_sql("""
        SELECT account, IFNULL(cost_center, '') AS cost_center,
               SUM(debit) AS dr, SUM(credit) AS cr
        FROM `tabGL Entry`
        WHERE is_cancelled = 0 AND company = %s
          AND posting_date <= %s
        GROUP BY account, cost_center
    """, (COMPANY, td), as_dict=1)

        recent = _read_sql("""
        SELECT posting_date, account, IFNULL(cost_center,'') AS cost_center,
               debit, credit, voucher_type, voucher_no, remarks
        FROM `tabGL Entry`
        WHERE is_cancelled = 0 AND company = %s
          AND posting_date BETWEEN %s AND %s
        ORDER BY posting_date DESC, creation DESC
        LIMIT 40
    """, (COMPANY, fd, td), as_dict=1)

        frappe.response["message"] = {"pl": pl, "bs": bs, "recent": recent}

    elif action == "ledger":
        account = frappe.form_dict.get("account")
        cc = frappe.form_dict.get("cost_center")
        if not account or not from_date or not to_date:
            frappe.throw("account, from_date and to_date are required")
        fd = frappe.utils.getdate(from_date)
        td = frappe.utils.getdate(to_date)

        if cc:
            opening = _read_sql("""
            SELECT IFNULL(SUM(debit),0) AS dr, IFNULL(SUM(credit),0) AS cr
            FROM `tabGL Entry`
            WHERE is_cancelled = 0 AND company = %s AND account = %s
              AND cost_center = %s AND posting_date < %s
        """, (COMPANY, account, cc, fd), as_dict=1)
            rows = _read_sql("""
            SELECT posting_date, IFNULL(cost_center,'') AS cost_center,
                   debit, credit, voucher_type, voucher_no, against, remarks
            FROM `tabGL Entry`
            WHERE is_cancelled = 0 AND company = %s AND account = %s
              AND cost_center = %s AND posting_date BETWEEN %s AND %s
            ORDER BY posting_date ASC, creation ASC
            LIMIT 1000
        """, (COMPANY, account, cc, fd, td), as_dict=1)
        else:
            opening = _read_sql("""
            SELECT IFNULL(SUM(debit),0) AS dr, IFNULL(SUM(credit),0) AS cr
            FROM `tabGL Entry`
            WHERE is_cancelled = 0 AND company = %s AND account = %s
              AND posting_date < %s
        """, (COMPANY, account, fd), as_dict=1)
            rows = _read_sql("""
            SELECT posting_date, IFNULL(cost_center,'') AS cost_center,
                   debit, credit, voucher_type, voucher_no, against, remarks
            FROM `tabGL Entry`
            WHERE is_cancelled = 0 AND company = %s AND account = %s
              AND posting_date BETWEEN %s AND %s
            ORDER BY posting_date ASC, creation ASC
            LIMIT 1000
        """, (COMPANY, account, fd, td), as_dict=1)

        frappe.response["message"] = {"opening": opening[0] if opening else {"dr": 0, "cr": 0}, "rows": rows}

    elif action == "expenditures":
        if not from_date or not to_date:
            frappe.throw("from_date and to_date are required")
        fd = frappe.utils.getdate(from_date)
        td = frappe.utils.getdate(to_date)
        branch = frappe.form_dict.get("branch")

        if branch:
            rows = _read_sql("""
            SELECT je.name, je.posting_date, je.custom_branch,
                   je.total_debit AS amount, je.user_remark,
                   je.custom_bill_recipt AS bill,
                   jea.account AS cash_account,
                   IFNULL(jea.cost_center,'') AS cost_center,
                   jea.credit
            FROM `tabJournal Entry` je
            INNER JOIN `tabJournal Entry Account` jea
                ON jea.parent = je.name AND jea.credit > 0
            WHERE je.docstatus = 1 AND je.company = %s
              AND je.posting_date BETWEEN %s AND %s
              AND je.user_remark LIKE %s
              AND jea.cost_center = %s
            ORDER BY je.posting_date DESC, je.creation DESC
            LIMIT 500
        """, (COMPANY, fd, td, "Expenditure%", branch), as_dict=1)
        else:
            rows = _read_sql("""
            SELECT je.name, je.posting_date, je.custom_branch,
                   je.total_debit AS amount, je.user_remark,
                   je.custom_bill_recipt AS bill,
                   jea.account AS cash_account,
                   IFNULL(jea.cost_center,'') AS cost_center,
                   jea.credit
            FROM `tabJournal Entry` je
            INNER JOIN `tabJournal Entry Account` jea
                ON jea.parent = je.name AND jea.credit > 0
            WHERE je.docstatus = 1 AND je.company = %s
              AND je.posting_date BETWEEN %s AND %s
              AND je.user_remark LIKE %s
            ORDER BY je.posting_date DESC, je.creation DESC
            LIMIT 500
        """, (COMPANY, fd, td, "Expenditure%"), as_dict=1)

        frappe.response["message"] = {"rows": rows}

    else:
        frappe.throw("Unknown action: %s" % action)
