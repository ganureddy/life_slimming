"""Get Expenditure History

Original API: get_expenditure_history
Source modified: 2026-06-03 23:16:14.793776
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

    ## ═══════════════════════════════════════════════════════════
    ## SERVER SCRIPT 2 — Get Expenditure History (filtered by branch)
    ## ═══════════════════════════════════════════════════════════
    ## Script Type  : API
    ## API Method   : get_expenditure_history
    ## Allow Guest  : NO
    ## Enabled      : YES
    ## ═══════════════════════════════════════════════════════════

    # branch param — if passed, filter by that branch; if empty, return all
    filter_branch = frappe.form_dict.get("branch") or ""

    je_list = frappe.db.get_all(
        "Journal Entry",
        filters=[["user_remark", "like", "Expenditure Entry%"]],
        fields=["name", "posting_date", "user_remark", "total_debit"],
        limit_page_length=500,
        order_by="posting_date desc, creation desc"
    )

    if not je_list:
        frappe.response["message"] = []
    else:
        je_names = [je["name"] for je in je_list]

        acc_rows = frappe.db.get_all(
            "Journal Entry Account",
            filters=[
                ["parent", "in", je_names],
                ["debit_in_account_currency", ">", 0]
            ],
            fields=["parent", "account", "debit_in_account_currency", "user_remark"],
            limit_page_length=2000,
            order_by="idx asc"
        )

        acc_map = {}
        for row in acc_rows:
            p = row["parent"]
            if p not in acc_map:
                acc_map[p] = []
            acc_map[p].append(row)

        result = []

        for je in je_list:
            remark = je.get("user_remark") or ""

            # parse: "Expenditure Entry | Branch: X | MODE | By: Y | Approved: Z"
            parts    = [p.strip() for p in remark.split(" | ")]
            branch   = ""
            pay_mode = ""
            paid_by  = ""
            approved = ""

            for part in parts:
                if part.startswith("Branch: "):
                    branch = part[8:].strip()
                elif part.startswith("By: "):
                    paid_by = part[4:].strip()
                elif part.startswith("Approved: "):
                    approved = part[10:].strip()
                elif (not part.startswith("Expenditure Entry")
                      and not part.startswith("Expenditure |")
                      and branch and not pay_mode and not paid_by):
                    pay_mode = part

            # filter by branch if provided
            if filter_branch and branch != filter_branch:
                continue

            rows  = acc_map.get(je["name"], [])
            items = []

            for row in rows:
                rm = row.get("user_remark") or ""

                et = ""
                dv = ""
                rv = ""
                fn = ""
                bv = False

                dash_idx = rm.find(" - ")
                if dash_idx != -1:
                    et   = rm[:dash_idx].strip()
                    rest = rm[dash_idx + 3:]
                else:
                    et   = rm.strip()
                    rest = ""

                rest_parts = [p.strip() for p in rest.split(" | ")]
                dv = rest_parts[0] if rest_parts else ""

                for rp in rest_parts[1:]:
                    if rp.startswith("Bill: "):
                        bv = True
                        fn = rp[6:].strip()
                    else:
                        rv = rp

                items.append({
                    "et": et,
                    "lv": row.get("account", ""),
                    "dv": dv,
                    "av": row.get("debit_in_account_currency", 0),
                    "rv": rv,
                    "bv": bv,
                    "fn": fn
                })

            if items:
                result.append({
                    "date":       str(je.get("posting_date", "")),
                    "branch":     branch,
                    "je":         je["name"],
                    "paidBy":     paid_by,
                    "approvedBy": approved,
                    "payMode":    pay_mode,
                    "total":      je.get("total_debit", 0),
                    "items":      items
                })

        frappe.response["message"] = result
