"""md_crm_api

Original API: md_crm_api
Source modified: 2026-08-04 13:09:18.455547
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
    #  SERVER SCRIPT (API)  —  md_crm_api
    #  Script Type : API   ·   API Method : md_crm_api
    #  URL: /api/method/md_crm_api?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    #
    #  CRM funnel — leads -> contacted -> booked -> converted, grouped
    #  three ways: by agent (lead_owner), by source, by branch.
    #
    #  Funnel definitions:
    #    leads      = every lead created in range
    #    contacted  = custom_call_count > 0 OR custom_cc_stage <> 'UNTOUCHED'
    #    booked     = custom_appointment_status IN ('Booked','Visited Booked')
    #    converted  = status = 'Converted' OR custom_appointment_status = 'Visited Booked'
    #
    #  safe_exec-safe: dict params only, no None, no reserved aliases,
    #  no try/except, no % literals, no slicing of function results.
    # =====================================================================

    args = frappe.form_dict or {}
    to_date = args.get("to_date")
    from_date = args.get("from_date")
    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.get_first_day(to_date)
    to_end = to_date + " 23:59:59"

    # ---- a reusable grouped-funnel query builder over a column ----
    def funnel_by(col):
        q = ("SELECT COALESCE(" + col + ", 'Unassigned') AS grp, "
             "COUNT(name) AS leads, "
             "SUM(CASE WHEN COALESCE(custom_call_count,0) > 0 "
             "         OR COALESCE(custom_cc_stage,'UNTOUCHED') <> 'UNTOUCHED' "
             "    THEN 1 ELSE 0 END) AS contacted, "
             "SUM(CASE WHEN custom_appointment_status IN ('Booked','Visited Booked') "
             "    THEN 1 ELSE 0 END) AS booked, "
             "SUM(CASE WHEN status = 'Converted' "
             "         OR custom_appointment_status = 'Visited Booked' "
             "    THEN 1 ELSE 0 END) AS converted "
             "FROM `tabLead` "
             "WHERE creation BETWEEN %(f)s AND %(t)s "
             "GROUP BY " + col + " "
             "ORDER BY leads DESC "
             "LIMIT 60")
        rows = _read_sql(q, {"f": from_date, "t": to_end}, as_dict=True)
        out_rows = []
        for r in rows:
            ld = int(r.get("leads") or 0)
            ct = int(r.get("contacted") or 0)
            bk = int(r.get("booked") or 0)
            cv = int(r.get("converted") or 0)
            d = {}
            d["name"] = r.get("grp")
            d["leads"] = ld
            d["contacted"] = ct
            d["booked"] = bk
            d["converted"] = cv
            if ld > 0:
                d["conv_pct"] = round(cv * 100.0 / ld, 1)
                d["contact_pct"] = round(ct * 100.0 / ld, 1)
                d["book_pct"] = round(bk * 100.0 / ld, 1)
            else:
                d["conv_pct"] = 0.0
                d["contact_pct"] = 0.0
                d["book_pct"] = 0.0
            out_rows.append(d)
        return out_rows

    by_agent = funnel_by("lead_owner")
    by_source = funnel_by("source")
    by_branch = funnel_by("branch")

    # ---- overall totals ----
    tot = _read_sql("""
    SELECT COUNT(name) AS leads,
           SUM(CASE WHEN COALESCE(custom_call_count,0) > 0
                     OR COALESCE(custom_cc_stage,'UNTOUCHED') <> 'UNTOUCHED'
               THEN 1 ELSE 0 END) AS contacted,
           SUM(CASE WHEN custom_appointment_status IN ('Booked','Visited Booked')
               THEN 1 ELSE 0 END) AS booked,
           SUM(CASE WHEN status = 'Converted'
                     OR custom_appointment_status = 'Visited Booked'
               THEN 1 ELSE 0 END) AS converted
    FROM `tabLead`
    WHERE creation BETWEEN %(f)s AND %(t)s
""", {"f": from_date, "t": to_end}, as_dict=True)

    totals = {}
    if len(tot) > 0:
        tl = int(tot[0].get("leads") or 0)
        tc = int(tot[0].get("contacted") or 0)
        tb = int(tot[0].get("booked") or 0)
        tv = int(tot[0].get("converted") or 0)
        totals["leads"] = tl
        totals["contacted"] = tc
        totals["booked"] = tb
        totals["converted"] = tv
        if tl > 0:
            totals["conv_pct"] = round(tv * 100.0 / tl, 1)
            totals["contact_pct"] = round(tc * 100.0 / tl, 1)
            totals["book_pct"] = round(tb * 100.0 / tl, 1)
        else:
            totals["conv_pct"] = 0.0
            totals["contact_pct"] = 0.0
            totals["book_pct"] = 0.0
    else:
        totals["leads"] = 0
        totals["contacted"] = 0
        totals["booked"] = 0
        totals["converted"] = 0
        totals["conv_pct"] = 0.0
        totals["contact_pct"] = 0.0
        totals["book_pct"] = 0.0

    out = {}
    out["from_date"] = from_date
    out["to_date"] = to_date
    out["by_agent"] = by_agent
    out["by_source"] = by_source
    out["by_branch"] = by_branch
    out["totals"] = totals
    frappe.response["message"] = out
