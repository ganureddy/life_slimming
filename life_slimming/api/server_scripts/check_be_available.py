"""check_be_available

Original API: check_be_available
Source modified: 2026-08-18 19:54:49.581286
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
    today = frappe.utils.nowdate()
    now = frappe.utils.now_datetime()
    now_hour = now.hour

    count = 0
    if now_hour >= 10 and now_hour < 20:
        rows = _read_sql("""
        SELECT COUNT(DISTINCT e.user_id) AS cnt
        FROM `tabAttendance` a
        INNER JOIN `tabEmployee` e ON e.name = a.employee
        WHERE a.attendance_date = %s
          AND a.custom_check_in_time IS NOT NULL
          AND a.custom_check_out_time IS NULL
          AND e.designation = 'Business Executive'
          AND e.status = 'Active'
          AND e.user_id IS NOT NULL
          AND e.user_id != ''
    """, (today,), as_dict=True)
        if rows:
            count = rows[0]["cnt"] or 0

    frappe.response["available"] = count
