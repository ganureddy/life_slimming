"""get_collection_gst_data

Original API: get_collection_gst_data
Source modified: 2026-09-16 17:47:49.061148
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
        frappe.throw("From Date and To Date are required")

    if str(from_date) > str(to_date):
        frappe.throw("From Date cannot be after To Date")

    result = {}

    # Always initialise every configured branch so the dashboard does not disappear
    # on zero-collection days. This site's Branch DocType has no disabled field.
    # Testing Branch is intentionally excluded.
    branches = _read_sql("""
    SELECT name
    FROM `tabBranch`
    WHERE LOWER(TRIM(name)) NOT IN ('testing branch', 'testing')
    ORDER BY name
""", as_dict=True)

    for branch_row in branches:
        result[branch_row.name] = {}

    # Collection is based on submitted Receive Payment Entries and their exact
    # Sales Invoice allocations. Branch falls back to the invoice when PE.branch
    # is blank.
    data = _read_sql("""
    SELECT
        COALESCE(
            NULLIF(TRIM(pe.branch), ''),
            NULLIF(TRIM(si.branch), ''),
            NULLIF(TRIM(si.custom_transfer_branch), ''),
            'Unknown'
        ) AS branch,
        COALESCE(NULLIF(TRIM(pe.mode_of_payment), ''), 'Unknown') AS mode_of_payment,
        IFNULL(si.base_total_taxes_and_charges, 0) AS invoice_gst,
        IFNULL(si.base_grand_total, 0) AS invoice_total,
        IFNULL(per.allocated_amount, 0) AS allocated_amount,
        si.posting_date AS si_date,
        pe.posting_date AS pe_date
    FROM `tabPayment Entry` pe
    INNER JOIN `tabPayment Entry Reference` per
        ON per.parent = pe.name
       AND per.parenttype = 'Payment Entry'
    INNER JOIN `tabSales Invoice` si
        ON si.name = per.reference_name
       AND si.docstatus = 1
    WHERE pe.docstatus = 1
      AND pe.payment_type = 'Receive'
      AND pe.posting_date >= %s
      AND pe.posting_date <= %s
      AND per.reference_doctype = 'Sales Invoice'
      AND IFNULL(per.allocated_amount, 0) != 0
      AND LOWER(TRIM(COALESCE(NULLIF(pe.branch, ''), NULLIF(si.branch, ''), NULLIF(si.custom_transfer_branch, ''), 'Unknown')))
          NOT IN ('testing branch', 'testing')
    ORDER BY branch, mode_of_payment
""", (from_date, to_date), as_dict=True)

    for row in data:
        branch = row.branch or "Unknown"
        mode = row.mode_of_payment or "Unknown"

        if branch not in result:
            result[branch] = {}

        if mode not in result[branch]:
            result[branch][mode] = {
                "net": 0,
                "gst": 0,
                "total": 0,
                "new_sale": 0,
                "old_sale": 0,
                "gst_count": {}
            }

        invoice_total = float(row.invoice_total or 0)
        invoice_gst = float(row.invoice_gst or 0)
        allocated = float(row.allocated_amount or 0)

        # Protect the report from invalid/zero-value invoices.
        if invoice_total > 0:
            gst_ratio = invoice_gst / invoice_total
            if gst_ratio < 0:
                gst_ratio = 0
            if gst_ratio > 1:
                gst_ratio = 1
        else:
            gst_ratio = 0

        gst_part = allocated * gst_ratio
        net_part = allocated - gst_part

        bucket = result[branch][mode]
        bucket["net"] = bucket["net"] + net_part
        bucket["gst"] = bucket["gst"] + gst_part
        bucket["total"] = bucket["total"] + allocated

        if str(row.si_date) == str(row.pe_date):
            bucket["new_sale"] = bucket["new_sale"] + allocated
        else:
            bucket["old_sale"] = bucket["old_sale"] + allocated

        base_amount = invoice_total - invoice_gst
        if base_amount > 0:
            gst_percent = round((invoice_gst / base_amount) * 100)
        else:
            gst_percent = 0

        gst_key = str(gst_percent)
        if gst_key not in bucket["gst_count"]:
            bucket["gst_count"][gst_key] = 0
        bucket["gst_count"][gst_key] = bucket["gst_count"][gst_key] + 1

    frappe.response["message"] = result
