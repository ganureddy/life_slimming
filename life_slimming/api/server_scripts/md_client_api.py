"""md_client_api

Original API: md_client_api
Source modified: 2026-08-19 19:13:11.828326
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
    if not from_date:
        from_date = str(frappe.utils.get_first_day(to_date))
    from_date = str(from_date)

    result = {}

    # ---------- 1. TOP CLIENTS by lifetime value (all-time billed) ----------
    top = _read_sql("""
    SELECT
        si.patient AS patient,
        MAX(si.branch) AS branch,
        SUM(si.base_grand_total) AS lifetime,
        COUNT(si.name) AS invoices,
        MIN(si.posting_date) AS first_visit,
        MAX(si.posting_date) AS last_visit
    FROM `tabSales Invoice` si
    WHERE si.docstatus = 1
      AND si.patient IS NOT NULL
      AND si.patient != ''
    GROUP BY si.patient
    ORDER BY lifetime DESC
    LIMIT 25
""", as_dict=True)

    top_rows = []
    for r in top:
        top_rows.append({
            "patient": r.get("patient"),
            "branch": (r.get("branch") or "").replace(" - LSACPL", ""),
            "lifetime": float(r.get("lifetime") or 0),
            "invoices": int(r.get("invoices") or 0),
            "first_visit": str(r.get("first_visit") or ""),
            "last_visit": str(r.get("last_visit") or "")
        })
    result["top_clients"] = top_rows

    # ---------- 2. NEW vs RETURNING in the selected range ----------
    # For each patient billed in range, is their FIRST-EVER invoice inside the range?
    range_pat = _read_sql("""
    SELECT si.patient AS patient,
           SUM(si.base_grand_total) AS billed_in_range,
           COUNT(si.name) AS inv_in_range
    FROM `tabSales Invoice` si
    WHERE si.docstatus = 1
      AND si.patient IS NOT NULL AND si.patient != ''
      AND si.posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY si.patient
""", {"f": from_date, "t": to_date}, as_dict=True)

    first_ever = _read_sql("""
    SELECT si.patient AS patient, MIN(si.posting_date) AS first_date
    FROM `tabSales Invoice` si
    WHERE si.docstatus = 1
      AND si.patient IS NOT NULL AND si.patient != ''
    GROUP BY si.patient
""", as_dict=True)

    first_map = {}
    for r in first_ever:
        first_map[r.get("patient")] = str(r.get("first_date") or "")

    new_count = 0
    ret_count = 0
    new_value = 0.0
    ret_value = 0.0
    for r in range_pat:
        pat = r.get("patient")
        val = float(r.get("billed_in_range") or 0)
        fd = first_map.get(pat, "")
        if fd and from_date <= fd <= to_date:
            new_count = new_count + 1
            new_value = new_value + val
        else:
            ret_count = ret_count + 1
            ret_value = ret_value + val

    result["new_vs_returning"] = {
        "new_count": new_count, "returning_count": ret_count,
        "new_value": new_value, "returning_value": ret_value,
        "total_clients": new_count + ret_count,
        "total_value": new_value + ret_value
    }

    # ---------- 3. SPEND SEGMENTS (lifetime value bands) ----------
    seg = _read_sql("""
    SELECT
        CASE
            WHEN lv >= 200000 THEN 'A. 2L+'
            WHEN lv >= 100000 THEN 'B. 1L - 2L'
            WHEN lv >= 50000  THEN 'C. 50k - 1L'
            WHEN lv >= 20000  THEN 'D. 20k - 50k'
            ELSE 'E. under 20k'
        END AS band,
        COUNT(*) AS clients,
        SUM(lv) AS value
    FROM (
        SELECT si.patient AS pat, SUM(si.base_grand_total) AS lv
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1 AND si.patient IS NOT NULL AND si.patient != ''
        GROUP BY si.patient
    ) t
    GROUP BY band
    ORDER BY band
""", as_dict=True)

    seg_rows = []
    for r in seg:
        seg_rows.append({
            "band": r.get("band"),
            "clients": int(r.get("clients") or 0),
            "value": float(r.get("value") or 0)
        })
    result["segments"] = seg_rows

    # ---------- 4. BRANCH MIX of clients billed in range ----------
    bmix = _read_sql("""
    SELECT si.branch AS branch,
           COUNT(DISTINCT si.patient) AS clients,
           SUM(si.base_grand_total) AS value
    FROM `tabSales Invoice` si
    WHERE si.docstatus = 1
      AND si.patient IS NOT NULL AND si.patient != ''
      AND si.posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY si.branch
    ORDER BY value DESC
""", {"f": from_date, "t": to_date}, as_dict=True)

    bmix_rows = []
    for r in bmix:
        bmix_rows.append({
            "branch": (r.get("branch") or "Unknown"),
            "clients": int(r.get("clients") or 0),
            "value": float(r.get("value") or 0)
        })
    result["branch_mix"] = bmix_rows

    # ---------- 5. MEDIA MIX (lead source) of clients billed in range ----------
    mmix = _read_sql("""
    SELECT COALESCE(pat.custom_media, 'Unknown') AS media,
           COUNT(DISTINCT si.patient) AS clients,
           SUM(si.base_grand_total) AS value
    FROM `tabSales Invoice` si
    LEFT JOIN `tabPatient` pat ON pat.name = si.patient
    WHERE si.docstatus = 1
      AND si.patient IS NOT NULL AND si.patient != ''
      AND si.posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY COALESCE(pat.custom_media, 'Unknown')
    ORDER BY value DESC
""", {"f": from_date, "t": to_date}, as_dict=True)

    mmix_rows = []
    for r in mmix:
        mmix_rows.append({
            "media": r.get("media") or "Unknown",
            "clients": int(r.get("clients") or 0),
            "value": float(r.get("value") or 0)
        })
    result["media_mix"] = mmix_rows

    result["totals"] = {
        "total_patients": frappe.db.count("Patient"),
        "billing_clients_in_range": result["new_vs_returning"]["total_clients"]
    }
    result["from_date"] = from_date
    result["to_date"] = to_date

    frappe.response["message"] = result
