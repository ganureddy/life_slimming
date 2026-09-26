"""md_employee_sales_api

Original API: md_employee_sales_api
Source modified: 2026-08-05 11:22:36.080780
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
    #  SERVER SCRIPT (API)  —  md_employee_sales_api
    #  Script Type : API   ·   API Method : md_employee_sales_api
    #  URL: /api/method/md_employee_sales_api?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    #
    #  Mirrors the "REFERRAL REPORT - FIXED" Query Report:
    #   - INNER JOIN Therapy Plan on si.therapy_plan_reference_id
    #   - paid  = SUM(Payment Entry Reference allocated_amount), submitted PEs
    #             whose posting_date is in range
    #   - net   = paid / 1.05   (flat GST removal, same as the report)
    #   - split : both referring + incentive names -> half net each
    #             one name -> 100% net to that person
    #
    #  Adds category-wise (Therapy Plan category: Slimming, Skin...) and
    #  media-wise (Therapy Plan media / Lead Source) net-sales breakdowns.
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

    rows = _read_sql("""
    SELECT si.name                                       AS inv,
           si.branch                                     AS branch,
           COALESCE(tp.category, 'Uncategorised')        AS category,
           COALESCE(tp.media, 'Unknown')                 AS media,
           COALESCE(si.custom_referring_name, '')        AS refname,
           COALESCE(si.custom_incentive_employee_name,'')AS incname,
           pay.paid                                      AS paid
    FROM `tabSales Invoice` si
    INNER JOIN `tabTherapy Plan` tp
        ON tp.name = si.therapy_plan_reference_id
    INNER JOIN (
        SELECT per.reference_name AS sinv,
               SUM(per.allocated_amount) AS paid
        FROM `tabPayment Entry Reference` per
        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent AND pe.docstatus = 1
        WHERE per.reference_doctype = 'Sales Invoice'
          AND pe.posting_date BETWEEN %(f)s AND %(t)s
        GROUP BY per.reference_name
        HAVING SUM(per.allocated_amount) > 0
    ) pay ON pay.sinv = si.name
    WHERE si.docstatus = 1
      AND (COALESCE(si.custom_referring_name, '') <> ''
           OR COALESCE(si.custom_incentive_employee_name, '') <> '')
""", {"f": from_date, "t": to_date}, as_dict=True)

    def nkey(s):
        v = (s or "").lower().strip()
        parts = v.split()
        return " ".join(parts)

    emp = {}
    cat_map = {}
    media_map = {}
    tot_net = 0.0
    tot_inv = 0

    def add_emp(raw_name, amount, branch, is_ref, is_inc):
        key = nkey(raw_name)
        if key == "":
            return
        if key not in emp:
            d = {}
            d["display"] = (raw_name or "").strip()
            d["credit"] = 0.0
            d["invoices"] = 0
            d["as_ref"] = 0
            d["as_inc"] = 0
            d["top_branch"] = branch
            emp[key] = d
        e = emp[key]
        disp = (raw_name or "").strip()
        if len(disp) > len(e["display"]):
            e["display"] = disp
        e["credit"] = e["credit"] + amount
        e["invoices"] = e["invoices"] + 1
        if is_ref == 1:
            e["as_ref"] = e["as_ref"] + 1
        if is_inc == 1:
            e["as_inc"] = e["as_inc"] + 1

    def add_bucket(bmap, name, amount):
        k = name or "Unknown"
        if k not in bmap:
            bmap[k] = 0.0
        bmap[k] = bmap[k] + amount

    for r in rows:
        paid = float(r.get("paid") or 0)
        if paid <= 0:
            continue
        net = paid / 1.05
        ref = (r.get("refname") or "").strip()
        inc = (r.get("incname") or "").strip()
        br = (r.get("branch") or "").strip()
        cat = r.get("category") or "Uncategorised"
        med = r.get("media") or "Unknown"
        has_ref = 0
        has_inc = 0
        if ref != "":
            has_ref = 1
        if inc != "":
            has_inc = 1
        tot_inv = tot_inv + 1
        tot_net = tot_net + net
        add_bucket(cat_map, cat, net)
        add_bucket(media_map, med, net)
        if has_ref == 1 and has_inc == 1:
            half = net / 2.0
            add_emp(ref, half, br, 1, 0)
            add_emp(inc, half, br, 0, 1)
        elif has_ref == 1:
            add_emp(ref, net, br, 1, 0)
        elif has_inc == 1:
            add_emp(inc, net, br, 0, 1)

    emp_list = []
    for k in emp:
        e = emp[k]
        d = {}
        d["name"] = e["display"]
        d["credit"] = e["credit"]
        d["invoices"] = e["invoices"]
        d["as_ref"] = e["as_ref"]
        d["as_inc"] = e["as_inc"]
        d["branch"] = e["top_branch"]
        emp_list.append(d)

    def sort_desc(lst, field):
        n = len(lst)
        a = 0
        while a < n:
            mx = a
            b = a + 1
            while b < n:
                if lst[b][field] > lst[mx][field]:
                    mx = b
                b = b + 1
            if mx != a:
                tmp = lst[a]
                lst[a] = lst[mx]
                lst[mx] = tmp
            a = a + 1
        return lst

    sort_desc(emp_list, "credit")
    top = []
    c = 0
    while c < len(emp_list) and c < 60:
        top.append(emp_list[c])
        c = c + 1

    def map_to_list(bmap):
        out_l = []
        for k in bmap:
            d = {}
            d["name"] = k
            d["net"] = bmap[k]
            out_l.append(d)
        sort_desc(out_l, "net")
        return out_l

    by_category = map_to_list(cat_map)
    by_media = map_to_list(media_map)

    out = {}
    out["from_date"] = from_date
    out["to_date"] = to_date
    out["employees"] = top
    out["by_category"] = by_category
    out["by_media"] = by_media
    out["total_net"] = tot_net
    out["total_invoices"] = tot_inv
    out["employee_count"] = len(emp_list)
    frappe.response["message"] = out
