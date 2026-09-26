"""get_media_sale_testing

Original API: get_media_sale_testing
Source modified: 2026-08-17 19:20:26.262798
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

    # get_first_day() returns a date object; comparisons below are string-based
    from_date = str(from_date)
    to_date = str(to_date)

    # loan financier modes -> 15% cut applied after GST removal
    loan_keys = ["bajaj", "sai roshini", "fibe", "carepay", "savein", "loan tap", "uno", "shopse", "liqui"]

    def is_loan(mode):
        m = (mode or "").lower()
        hit = False
        for k in loan_keys:
            if k in m:
                hit = True
        return hit

    result = {}

    def ensure(branch, media):
        if branch not in result:
            result[branch] = {}
        if media not in result[branch]:
            slot = {}
            slot["gross"]       = 0.0
            slot["net"]         = 0.0
            slot["gst"]         = 0.0
            slot["collected"]   = 0.0
            slot["outstanding"] = 0.0
            slot["new_coll"]    = 0.0
            slot["old_coll"]    = 0.0
            slot["inv_new"]     = 0
            slot["inv_old"]     = 0
            result[branch][media] = slot
        return result[branch][media]

    # ---- 1. COLLECTIONS in range (filter on Payment Entry posting_date = Paid date) ----
    coll_rows = _read_sql("""
    SELECT
        pe.branch                                        AS branch,
        pe.mode_of_payment                               AS mode,
        COALESCE(pat.custom_media, tp.media, 'Unknown')  AS media,
        per.allocated_amount                             AS allocated,
        si.base_total_taxes_and_charges                  AS inv_gst,
        si.base_grand_total                              AS inv_total,
        si.posting_date                                  AS si_date
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
        mode   = row.get("mode")
        allocated = float(row.get("allocated") or 0)
        inv_total = float(row.get("inv_total") or 0)
        inv_gst   = float(row.get("inv_gst") or 0)
        slot = ensure(branch, media)

        if inv_total != 0:
            gst_ratio = inv_gst / inv_total
        else:
            gst_ratio = 0.0
        gst_part = allocated * gst_ratio
        net_of_gst = allocated - gst_part

        # Net After = collected without GST, minus 15% for loan financier modes
        if is_loan(mode):
            net_after = net_of_gst * 0.85
        else:
            net_after = net_of_gst

        slot["gst"]       = slot["gst"]       + gst_part
        slot["net"]       = slot["net"]       + net_after
        slot["collected"] = slot["collected"] + allocated

        si_date = str(row.get("si_date"))
        if from_date <= si_date <= to_date:
            slot["new_coll"] = slot["new_coll"] + allocated
        else:
            slot["old_coll"] = slot["old_coll"] + allocated

    # ---- 2. Distinct invoices touched: Gross (invoice value) + Outstanding, once per invoice ----
    inv_rows = _read_sql("""
    SELECT
        si.branch                                        AS branch,
        COALESCE(pat.custom_media, tp.media, 'Unknown')  AS media,
        si.base_grand_total                              AS gross,
        si.outstanding_amount                            AS outstanding,
        si.posting_date                                  AS si_date
    FROM `tabSales Invoice` si
    LEFT JOIN `tabPatient` pat ON pat.name = si.patient
    LEFT JOIN `tabTherapy Plan` tp ON tp.name = si.custom_therapy_plan
    WHERE si.docstatus = 1
      AND si.name IN (
        SELECT DISTINCT per.reference_name
        FROM `tabPayment Entry` pe
        INNER JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
        WHERE pe.docstatus = 1
          AND pe.payment_type = 'Receive'
          AND pe.posting_date BETWEEN %(f)s AND %(t)s
          AND per.reference_doctype = 'Sales Invoice'
      )
""", {"f": from_date, "t": to_date}, as_dict=True)

    for row in inv_rows:
        branch = row.get("branch") or "Unknown"
        media  = row.get("media") or "Unknown"
        slot = ensure(branch, media)
        slot["gross"]       = slot["gross"]       + float(row.get("gross") or 0)
        slot["outstanding"] = slot["outstanding"] + float(row.get("outstanding") or 0)

        si_date = str(row.get("si_date"))
        if from_date <= si_date <= to_date:
            slot["inv_new"] = slot["inv_new"] + 1
        else:
            slot["inv_old"] = slot["inv_old"] + 1

    frappe.response["message"] = result
