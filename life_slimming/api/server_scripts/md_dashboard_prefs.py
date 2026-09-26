"""md_dashboard_prefs

Original API: md_dashboard_prefs
Source modified: 2026-08-19 19:12:58.225524
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
    # Per-user dashboard preferences stored in Redis cache (sandbox-safe).
    user = frappe.session.user
    action = frappe.form_dict.get("action") or "get"
    bucket = "md_dashboard_prefs"

    cache = frappe.cache()

    if action == "save":
        payload = frappe.form_dict.get("data") or ""
        if len(payload) > 60000:
            frappe.response["message"] = {"ok": 0, "error": "too large"}
        else:
            cache.hset(bucket, user, payload)
            frappe.response["message"] = {"ok": 1, "saved": 1}
    else:
        val = cache.hget(bucket, user)
        if val is None:
            val = ""
        if not isinstance(val, str):
            try:
                val = val.decode("utf-8")
            except Exception:
                val = str(val)
        frappe.response["message"] = {"ok": 1, "data": val}
