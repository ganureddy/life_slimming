"""cc_get_lead_history

Original API: cc_get_lead_history
Source modified: 2026-07-15 12:49:46.662254
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
    # ═══════════════════════════════════════════════════════════════════
    # Server Script: cc_get_lead_history
    # Script Type : API   |   API Method: cc_get_lead_history   |   Allow Guest: NO
    # Replaces frappe.client.get_list on Version (the Lead History timeline).
    # Version normally needs System Manager read — this makes the timeline
    # work for every agent regardless of their Lead/Version permissions.
    # ═══════════════════════════════════════════════════════════════════

    ALLOWED_ROLES = ["System Manager", "Sales Manager", "Sales User", "Call Center Export"]

    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Not permitted")

    user_roles = frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")
    has_access = False
    for r in ALLOWED_ROLES:
        if r in user_roles:
            has_access = True
            break
    if not has_access:
        frappe.throw("Not permitted")

    lead = frappe.form_dict.get("lead")
    if not lead:
        frappe.throw("lead is required")

    rows = frappe.get_all(
        "Version",
        filters={"ref_doctype": "Lead", "docname": lead},
        fields=["name", "creation", "owner", "data"],
        order_by="creation asc",
        limit_page_length=200
    )
    frappe.response["message"] = rows
