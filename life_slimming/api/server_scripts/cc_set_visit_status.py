"""cc_set_visit_status

Original API: cc_set_visit_status
Source modified: 2026-08-23 12:46:07.981345
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
    # Server Script  ·  Type: API  ·  API Method: cc_set_visit_status
    # Sets ONLY custom_visit_status on a Lead.
    # safe_exec-compliant: no imports, no f-strings, no .format(), no db.commit(),
    # no doc= permission kwarg, % formatting only.

    lead = frappe.form_dict.get("lead")
    visit_status = frappe.form_dict.get("visit_status")

    allowed = ["", "Pending", "Visited", "Not Visited", "Rescheduled", "Cancelled"]

    if not lead:
        frappe.throw("Missing lead id")

    if visit_status not in allowed:
        frappe.throw("Invalid visit status: %s" % visit_status)

    if not frappe.db.exists("Lead", lead):
        frappe.throw("Lead not found: %s" % lead)

    frappe.db.set_value("Lead", lead, "custom_visit_status", visit_status)

    frappe.response["message"] = {
        "ok": True,
        "lead": lead,
        "custom_visit_status": visit_status
    }
