"""md_forecast_api

Original API: md_forecast_api
Source modified: 2026-08-04 13:10:26.818898
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
    #  SERVER SCRIPT (API)  —  md_forecast_api
    #  Script Type : API   ·   API Method : md_forecast_api
    #  URL: /api/method/md_forecast_api
    #
    #  Forecasting for the MD dashboard.
    #   A) Cycle projection  — this 6th->5th cycle's revenue & collections
    #      projected to cycle end using the current daily run-rate.
    #   B) Next-cycle forecast — weighted moving average of the last 6
    #      completed cycles, with a light linear-trend adjustment.
    #
    #  Method rationale: revenue here has month-to-month momentum without
    #  wild swings, so a recency-weighted average (weights 1..6 on the last
    #  six months) plus half the average month-over-month delta is both
    #  stable and responsive — more accurate than a flat mean or a noisy
    #  single-month growth rate.
    #
    #  safe_exec-safe: dict params only, no None, no reserved aliases,
    #  no try/except, no % literals, no slicing of function results.
    # =====================================================================

    today = frappe.utils.getdate(frappe.utils.nowdate())
    ty = today.year
    tm = today.month
    td = today.day

    # ---- current 6th->5th cycle window ----
    smonth = tm
    syear = ty
    if td < 6:
        smonth = tm - 1
        if smonth < 1:
            smonth = 12
            syear = syear - 1
    first_start = frappe.utils.get_first_day(frappe.utils.getdate(str(syear) + "-" + str(smonth) + "-01"))
    cyc_from = frappe.utils.add_days(first_start, 5)
    emonth = smonth + 1
    eyear = syear
    if emonth > 12:
        emonth = 1
        eyear = eyear + 1
    first_end = frappe.utils.get_first_day(frappe.utils.getdate(str(eyear) + "-" + str(emonth) + "-01"))
    cyc_to = frappe.utils.add_days(first_end, 4)

    total_days = frappe.utils.date_diff(cyc_to, cyc_from) + 1
    elapsed = frappe.utils.date_diff(today, cyc_from) + 1
    if elapsed < 1:
        elapsed = 1
    if elapsed > total_days:
        elapsed = total_days
    days_left = total_days - elapsed

    # ---- this cycle so far: revenue (Sales Invoice) + collections (Payment Entry) ----
    rev_row = _read_sql("""
    SELECT COALESCE(SUM(grand_total),0) AS rev
    FROM `tabSales Invoice`
    WHERE docstatus = 1 AND posting_date BETWEEN %(f)s AND %(t)s
""", {"f": cyc_from, "t": today}, as_dict=True)
    coll_row = _read_sql("""
    SELECT COALESCE(SUM(received_amount),0) AS coll
    FROM `tabPayment Entry`
    WHERE docstatus = 1 AND payment_type = 'Receive'
      AND posting_date BETWEEN %(f)s AND %(t)s
""", {"f": cyc_from, "t": today}, as_dict=True)

    rev_sofar = float(rev_row[0].get("rev") or 0)
    coll_sofar = float(coll_row[0].get("coll") or 0)

    def project(sofar):
        rate = 0.0
        if elapsed > 0:
            rate = sofar / elapsed
        return sofar + (rate * days_left)

    cycle = {}
    cycle["from"] = str(cyc_from)
    cycle["to"] = str(cyc_to)
    cycle["total_days"] = total_days
    cycle["elapsed"] = elapsed
    cycle["days_left"] = days_left
    cycle["rev_sofar"] = rev_sofar
    cycle["coll_sofar"] = coll_sofar
    cycle["rev_projected"] = project(rev_sofar)
    cycle["coll_projected"] = project(coll_sofar)
    if elapsed > 0:
        cycle["rev_run_rate"] = rev_sofar / elapsed
        cycle["coll_run_rate"] = coll_sofar / elapsed
    else:
        cycle["rev_run_rate"] = 0.0
        cycle["coll_run_rate"] = 0.0

    # ---- last 6 COMPLETED cycles (by calendar month proxy) for trend ----
    # We use month buckets ending before the current cycle start.
    hist_start = frappe.utils.add_months(cyc_from, -6)
    mrev = _read_sql("""
    SELECT YEAR(posting_date) AS yy, MONTH(posting_date) AS mm,
           COALESCE(SUM(grand_total),0) AS rev
    FROM `tabSales Invoice`
    WHERE docstatus = 1
      AND posting_date >= %(s)s AND posting_date < %(e)s
    GROUP BY YEAR(posting_date), MONTH(posting_date)
    ORDER BY YEAR(posting_date) ASC, MONTH(posting_date) ASC
""", {"s": hist_start, "e": cyc_from}, as_dict=True)
    mcoll = _read_sql("""
    SELECT YEAR(posting_date) AS yy, MONTH(posting_date) AS mm,
           COALESCE(SUM(received_amount),0) AS coll
    FROM `tabPayment Entry`
    WHERE docstatus = 1 AND payment_type = 'Receive'
      AND posting_date >= %(s)s AND posting_date < %(e)s
    GROUP BY YEAR(posting_date), MONTH(posting_date)
    ORDER BY YEAR(posting_date) ASC, MONTH(posting_date) ASC
""", {"s": hist_start, "e": cyc_from}, as_dict=True)

    mon_abbr = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def series_of(rows, valkey):
        s = []
        for r in rows:
            yy = int(r.get("yy") or 0)
            mm = int(r.get("mm") or 0)
            yy2 = yy - (yy // 100) * 100
            d = {}
            d["label"] = mon_abbr[mm] + " " + str(yy2)
            d["value"] = float(r.get(valkey) or 0)
            s.append(d)
        return s

    rev_series = series_of(mrev, "rev")
    coll_series = series_of(mcoll, "coll")

    # ---- recency-weighted forecast: weights 1..n on last n months + half avg delta ----
    def forecast(series):
        n = len(series)
        if n == 0:
            return 0.0
        wsum = 0.0
        vsum = 0.0
        i = 0
        while i < n:
            w = i + 1
            vsum = vsum + series[i]["value"] * w
            wsum = wsum + w
            i = i + 1
        wavg = 0.0
        if wsum > 0:
            wavg = vsum / wsum
        # average month-over-month delta
        delta_sum = 0.0
        dc = 0
        j = 1
        while j < n:
            delta_sum = delta_sum + (series[j]["value"] - series[j - 1]["value"])
            dc = dc + 1
            j = j + 1
        avg_delta = 0.0
        if dc > 0:
            avg_delta = delta_sum / dc
        return wavg + (avg_delta / 2.0)

    nxt = {}
    nxt["rev_forecast"] = forecast(rev_series)
    nxt["coll_forecast"] = forecast(coll_series)
    # simple average for comparison
    def simple_avg(series):
        n = len(series)
        if n == 0:
            return 0.0
        s = 0.0
        i = 0
        while i < n:
            s = s + series[i]["value"]
            i = i + 1
        return s / n
    nxt["rev_simple_avg"] = simple_avg(rev_series)
    nxt["coll_simple_avg"] = simple_avg(coll_series)
    nxt["rev_series"] = rev_series
    nxt["coll_series"] = coll_series
    # label the next cycle
    nxt["label"] = mon_abbr[smonth] + " (next cycle)"

    out = {}
    out["cycle"] = cycle
    out["next"] = nxt
    frappe.response["message"] = out
