"""md_target_daily_api

Original API: md_target_daily_api
Source modified: 2026-08-01 19:21:05.366265
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
    #  SERVER SCRIPT (API)  —  md_target_daily_api
    #  Script Type : API   ·   API Method : md_target_daily_api
    #  URL: /api/method/md_target_daily_api?branch=Banjara Hills
    #       [&from_date=YYYY-MM-DD&to_date=YYYY-MM-DD]
    #
    #  Deficit-method daily target tracker for ONE branch, mirroring the
    #  Branch Command Center "Target & Realisation" modal (D.daily object).
    #
    #  Cycle = 6th of a month -> 5th of the next (company standard).
    #  monthly target = branch's targeted_amount from the Week Achive row
    #  whose parent Week Target sheet overlaps the cycle.
    #  daily collected = Payment Entry (Receive), branch's cost center.
    #
    #  Deficit method: target that day = (target - collected so far) /
    #                  days still remaining (incl. that day).
    #
    #  safe_exec-safe: dict params only, no None, no reserved aliases,
    #  no try/except, no % literals, no slicing of function results.
    # =====================================================================

    args = frappe.form_dict or {}
    branch = args.get("branch")
    if not branch:
        frappe.throw("branch is required")
    branch = str(branch).strip()

    # ---- resolve the 6th->5th cycle that contains 'today' (or to_date) ----
    anchor = args.get("to_date")
    if not anchor:
        anchor = frappe.utils.nowdate()
    adate = frappe.utils.getdate(anchor)
    ay = adate.year
    am = adate.month
    ad = adate.day
    # cycle start month: this month if day>=6 else previous month
    smonth = am
    syear = ay
    if ad < 6:
        smonth = am - 1
        if smonth < 1:
            smonth = 12
            syear = syear - 1
    # start = 6th of (syear, smonth); build via first-day + 5 days
    first_of_start = frappe.utils.get_first_day(frappe.utils.getdate(str(syear) + "-" + str(smonth) + "-01"))
    cyc_from = frappe.utils.add_days(first_of_start, 5)
    # end = 5th of next month
    emonth = smonth + 1
    eyear = syear
    if emonth > 12:
        emonth = 1
        eyear = eyear + 1
    first_of_end = frappe.utils.get_first_day(frappe.utils.getdate(str(eyear) + "-" + str(emonth) + "-01"))
    cyc_to = frappe.utils.add_days(first_of_end, 4)

    today = frappe.utils.getdate(frappe.utils.nowdate())

    # ---- monthly target for this branch (overlapping Week Target sheet) ----
    tgt_rows = _read_sql("""
    SELECT SUM(wa.targeted_amount) AS target
    FROM `tabWeek Achive` wa
    INNER JOIN `tabWeek Target vs Achive With Cuttings` h ON h.name = wa.parent
    WHERE wa.branch = %(b)s
      AND h.docstatus < 2
      AND h.from_date <= %(t)s
      AND h.to_date   >= %(f)s
""", {"b": branch, "f": cyc_from, "t": cyc_to}, as_dict=True)
    target = 0.0
    if len(tgt_rows) > 0:
        target = float(tgt_rows[0].get("target") or 0)

    # ---- daily collections from Payment Entry (cost center matches branch) ----
    # branch names differ from cost-center names; match on a normalised LIKE.
    bkey = branch.lower().replace(" ", "")
    day_rows = _read_sql("""
    SELECT posting_date            AS d,
           SUM(received_amount)    AS got
    FROM `tabPayment Entry`
    WHERE docstatus = 1
      AND payment_type = 'Receive'
      AND posting_date BETWEEN %(f)s AND %(t)s
      AND REPLACE(LOWER(COALESCE(cost_center,'')), ' ', '') LIKE %(bk)s
    GROUP BY posting_date
""", {"f": cyc_from, "t": cyc_to, "bk": "%" + bkey + "%"}, as_dict=True)

    got_map = {}
    for r in day_rows:
        got_map[str(r.get("d"))] = float(r.get("got") or 0)

    # ---- walk each day of the cycle, deficit method ----
    total_days = frappe.utils.date_diff(cyc_to, cyc_from) + 1
    days = []
    collected_so_far = 0.0
    hit_days = 0
    miss_days = 0
    i = 0
    while i < total_days:
        dcur = frappe.utils.add_days(cyc_from, i)
        dstr = str(dcur)
        is_future = 0
        if frappe.utils.getdate(dcur) > today:
            is_future = 1
        days_remaining = total_days - i
        remaining_target = target - collected_so_far
        if remaining_target < 0:
            remaining_target = 0.0
        req = 0.0
        if days_remaining > 0:
            req = remaining_target / days_remaining
        got = got_map.get(dstr, 0.0)
        diff = got - req
        row = {}
        row["d"] = dstr
        row["req"] = req
        row["got"] = got
        row["diff"] = diff
        row["future"] = is_future
        if is_future == 0:
            collected_so_far = collected_so_far + got
            row["cum"] = collected_so_far
            if got >= req:
                row["hit"] = 1
                hit_days = hit_days + 1
            else:
                row["hit"] = 0
                miss_days = miss_days + 1
        else:
            row["cum"] = collected_so_far
            row["hit"] = 0
        days.append(row)
        i = i + 1

    achieved = collected_so_far
    gap = target - achieved
    if gap < 0:
        gap = 0.0
    pct = 0.0
    if target > 0:
        pct = round(achieved / target * 100.0, 1)

    # days left = future days remaining in cycle (incl today if not past)
    days_left = 0
    j = 0
    while j < len(days):
        if days[j]["future"] == 1:
            days_left = days_left + 1
        j = j + 1
    if days_left < 1:
        days_left = 1

    req_per_day = gap / days_left

    # elapsed days for run rate
    elapsed = 0
    k = 0
    while k < len(days):
        if days[k]["future"] == 0:
            elapsed = elapsed + 1
        k = k + 1
    run_rate = 0.0
    if elapsed > 0:
        run_rate = achieved / elapsed
    projected = achieved + (run_rate * days_left)
    on_track = 0
    if projected >= target:
        on_track = 1

    daily = {}
    daily["branch"] = branch
    daily["pct"] = pct
    daily["achieved"] = achieved
    daily["target"] = target
    daily["gap"] = gap
    daily["req_per_day"] = req_per_day
    daily["days_left"] = days_left
    daily["run_rate"] = run_rate
    daily["projected"] = projected
    daily["on_track"] = on_track
    daily["hit_days"] = hit_days
    daily["miss_days"] = miss_days
    daily["total_days"] = total_days
    daily["cycle_from"] = str(cyc_from)
    daily["cycle_to"] = str(cyc_to)
    daily["days"] = days

    frappe.response["message"] = daily
