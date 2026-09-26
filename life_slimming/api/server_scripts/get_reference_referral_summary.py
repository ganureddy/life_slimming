"""get_reference_referral_summary

Original API: None
Source modified: 2026-06-03 23:16:14.723028
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

    if not from_date or not to_date:
        frappe.response["message"] = []
    else:
        frappe.response["message"] = _read_sql("""
        SELECT
            branch,
            COUNT(invoice) AS invoice_count,
            SUM(total_paid) AS total_paid
        FROM (
            SELECT
                si.name AS invoice,
                si.branch,
                SUM(per.allocated_amount) AS total_paid
            FROM
                `tabSales Invoice` si
            JOIN
                `tabPayment Entry Reference` per
                ON per.reference_name = si.name
            JOIN
                `tabPayment Entry` pe
                ON pe.name = per.parent
            WHERE
                si.docstatus = 1
                AND pe.docstatus = 1
                AND si.media = 'Reference'
                AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
            GROUP BY
                si.name, si.branch
            HAVING
                total_paid > 10000
        ) t
        GROUP BY branch
        ORDER BY total_paid DESC
    """, {
            "from_date": from_date,
            "to_date": to_date
        }, as_dict=True)
