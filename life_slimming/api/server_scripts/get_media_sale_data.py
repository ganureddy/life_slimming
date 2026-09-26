"""get_media_sale_data

Original API: get_media_sale_data
Source modified: 2026-08-17 19:20:48.592311
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

    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.get_first_day(to_date)

    from_date = str(from_date)
    to_date = str(to_date)

    result = {}

    def ensure(branch, media):
        if branch not in result:
            result[branch] = {}
        if media not in result[branch]:
            slot = {}
            slot["gross"]    = 0.0
            slot["net"]      = 0.0
            slot["gst"]      = 0.0
            slot["coll"]     = 0.0
            slot["new_sale"] = 0.0
            slot["old_sale"] = 0.0
            slot["invoices"] = 0
            result[branch][media] = slot
        return result[branch][media]

    gross_rows = _read_sql("""
    SELECT
        si.branch                                        AS branch,
        COALESCE(pat.custom_media, tp.media, 'Unknown')  AS media,
        SUM(si.base_grand_total)                         AS gross,
        SUM(si.base_net_total)                           AS net,
        SUM(si.base_total_taxes_and_charges)             AS gst,
        COUNT(si.name)                                   AS inv
    FROM `tabSales Invoice` si
    LEFT JOIN `tabPatient` pat ON pat.name = si.patient
    LEFT JOIN `tabTherapy Plan` tp ON tp.name = si.custom_therapy_plan
    WHERE si.docstatus = 1
      AND si.posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY si.branch, COALESCE(pat.custom_media, tp.media, 'Unknown')
""", {"f": from_date, "t": to_date}, as_dict=True)

    for row in gross_rows:
        branch = row.get("branch") or "Unknown"
        media  = row.get("media") or "Unknown"
        slot = ensure(branch, media)
        slot["gross"]    = slot["gross"]    + float(row.get("gross") or 0)
        slot["net"]      = slot["net"]      + float(row.get("net") or 0)
        slot["gst"]      = slot["gst"]      + float(row.get("gst") or 0)
        slot["invoices"] = slot["invoices"] + int(row.get("inv") or 0)

    coll_rows = _read_sql("""
    SELECT
        pe.branch                                        AS branch,
        COALESCE(pat.custom_media, tp.media, 'Unknown')  AS media,
        per.allocated_amount                             AS allocated,
        si.posting_date                                  AS si_date,
        pe.posting_date                                  AS pe_date
    FROM `tabPayment Entry` pe
    INNER JOIN `tabPayment Entry Reference` per
        ON per.parent = pe.name
    INNER JOIN `tabSales Invoice` si
        ON si.name = per.reference_name
    LEFT JOIN `tabPatient` pat ON pat.name = si.patient
    LEFT JOIN `tabTherapy Plan` tp ON tp.name = si.custom_therapy_plan
    WHERE pe.docstatus = 1
      AND pe.payment_type = 'Receive'
      AND pe.posting_date BETWEEN %(f)s AND %(t)s
      AND per.reference_doctype = 'Sales Invoice'
""", {"f": from_date, "t": to_date}, as_dict=True)

    for row in coll_rows:
        branch = row.get("branch") or "Unknown"
        media  = row.get("media") or "Unknown"
        allocated = float(row.get("allocated") or 0)
        slot = ensure(branch, media)
        slot["coll"] = slot["coll"] + allocated
        si_date = str(row.get("si_date"))
        pe_date = str(row.get("pe_date"))
        if si_date == pe_date:
            slot["new_sale"] = slot["new_sale"] + allocated
        else:
            slot["old_sale"] = slot["old_sale"] + allocated

    frappe.response["message"] = result
