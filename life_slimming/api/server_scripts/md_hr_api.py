"""md_hr_api

Original API: md_hr_api
Source modified: 2026-08-01 18:40:00.643537
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
    #  SERVER SCRIPT (API)  —  md_hr_api
    #  Script Type : API   ·   API Method : md_hr_api
    #  URL: /api/method/md_hr_api?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    #
    #  HR module: attendance present/absent per branch over the range,
    #  today's snapshot, active headcount, and this-month birthdays.
    #  Attendance has no branch column, so it joins to Employee.
    # =====================================================================

    args = frappe.form_dict or {}
    to_date = args.get("to_date")
    from_date = args.get("from_date")
    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.get_first_day(to_date)
    today = frappe.utils.nowdate()

    # ---------- 1. attendance in range, by branch (join Employee for branch) ----
    att_rows = _read_sql("""
    SELECT COALESCE(e.branch, 'Unassigned') AS branch,
           SUM(CASE WHEN a.status = 'Present'    THEN 1 ELSE 0 END) AS present,
           SUM(CASE WHEN a.status = 'Absent'     THEN 1 ELSE 0 END) AS absent,
           SUM(CASE WHEN a.status = 'On Leave'   THEN 1 ELSE 0 END) AS onleave,
           SUM(CASE WHEN a.status = 'Half Day'   THEN 1 ELSE 0 END) AS half,
           COUNT(a.name)                                            AS total
    FROM `tabAttendance` a
    LEFT JOIN `tabEmployee` e ON e.name = a.employee
    WHERE a.docstatus = 1
      AND a.attendance_date BETWEEN %(f)s AND %(t)s
    GROUP BY e.branch
    ORDER BY total DESC
""", {"f": from_date, "t": to_date}, as_dict=True)

    branches = []
    tot_p = 0
    tot_a = 0
    tot_l = 0
    for r in att_rows:
        p = int(r.get("present") or 0)
        ab = int(r.get("absent") or 0)
        lv = int(r.get("onleave") or 0)
        hf = int(r.get("half") or 0)
        tt = int(r.get("total") or 0)
        d = {}
        d["branch"] = r.get("branch")
        d["present"] = p
        d["absent"] = ab
        d["leave"] = lv
        d["half"] = hf
        d["total"] = tt
        if tt > 0:
            d["pct"] = round(p * 100.0 / tt, 1)
        else:
            d["pct"] = 0.0
        branches.append(d)
        tot_p = tot_p + p
        tot_a = tot_a + ab
        tot_l = tot_l + lv

    # ---------- 2. today's snapshot ----------
    today_row = _read_sql("""
    SELECT SUM(CASE WHEN status = 'Present'  THEN 1 ELSE 0 END) AS present,
           SUM(CASE WHEN status = 'Absent'   THEN 1 ELSE 0 END) AS absent,
           SUM(CASE WHEN status = 'On Leave' THEN 1 ELSE 0 END) AS onleave,
           COUNT(name)                                          AS total
    FROM `tabAttendance`
    WHERE docstatus = 1 AND attendance_date = %(d)s
""", {"d": today}, as_dict=True)
    today_snap = {}
    if len(today_row) > 0:
        today_snap["present"] = int(today_row[0].get("present") or 0)
        today_snap["absent"] = int(today_row[0].get("absent") or 0)
        today_snap["leave"] = int(today_row[0].get("onleave") or 0)
        today_snap["total"] = int(today_row[0].get("total") or 0)
    else:
        today_snap["present"] = 0
        today_snap["absent"] = 0
        today_snap["leave"] = 0
        today_snap["total"] = 0

    # ---------- 3. active headcount by department ----------
    dept_rows = _read_sql("""
    SELECT COALESCE(department, 'Unassigned') AS dept,
           COUNT(name) AS cnt
    FROM `tabEmployee`
    WHERE status = 'Active'
    GROUP BY department
    ORDER BY cnt DESC
    LIMIT 15
""", {}, as_dict=True)
    departments = []
    head_total = 0
    for r in dept_rows:
        c = int(r.get("cnt") or 0)
        d = {}
        d["dept"] = r.get("dept")
        d["count"] = c
        departments.append(d)
        head_total = head_total + c

    # ---------- 4. birthdays this month (by MONTH of date_of_birth) ----------
    cur_month = frappe.utils.getdate(today).month
    bday_rows = _read_sql("""
    SELECT employee_name AS ename,
           COALESCE(branch, '') AS branch,
           date_of_birth        AS dob,
           DAY(date_of_birth)   AS dday
    FROM `tabEmployee`
    WHERE status = 'Active'
      AND date_of_birth IS NOT NULL
      AND MONTH(date_of_birth) = %(m)s
    ORDER BY DAY(date_of_birth) ASC
""", {"m": cur_month}, as_dict=True)
    birthdays = []
    for r in bday_rows:
        d = {}
        d["name"] = r.get("ename")
        d["branch"] = r.get("branch")
        d["day"] = int(r.get("dday") or 0)
        d["dob"] = r.get("dob")
        birthdays.append(d)

    totals = {}
    totals["present"] = tot_p
    totals["absent"] = tot_a
    totals["leave"] = tot_l
    totals["headcount"] = head_total
    totals["today_present"] = today_snap["present"]
    totals["today_absent"] = today_snap["absent"]
    totals["birthdays"] = len(birthdays)

    out = {}
    out["from_date"] = from_date
    out["to_date"] = to_date
    out["branches"] = branches
    out["today"] = today_snap
    out["departments"] = departments
    out["birthdays"] = birthdays
    out["totals"] = totals
    frappe.response["message"] = out
