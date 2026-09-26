"""cc_lead_owner_history

Original API: cc_lead_owner_history
Source modified: 2026-08-16 03:04:20.420992
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

    ids_raw = frappe.form_dict.get("lead_ids") or "[]"
    if isinstance(ids_raw, str):
        try:
            lead_ids = json.loads(ids_raw)
        except Exception:
            lead_ids = []
    else:
        lead_ids = ids_raw
    if not isinstance(lead_ids, list):
        lead_ids = []
    lead_ids = lead_ids[:400]

    out = {}
    for lid in lead_ids:
        current_owner = frappe.db.get_value("Lead", lid, "lead_owner") or ""
        versions = frappe.get_all(
            "Version",
            filters={"ref_doctype": "Lead", "docname": lid},
            fields=["data"],
            order_by="creation asc",
            limit_page_length=500
        )
        transitions = []
        for v in versions:
            raw = v.get("data")
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except Exception:
                continue
            changed = parsed.get("changed") or []
            for ch in changed:
                if not ch:
                    continue
                if len(ch) >= 3 and ch[0] == "lead_owner":
                    transitions.append([ch[1], ch[2]])

        if transitions:
            first_owner = transitions[0][0] or transitions[0][1] or current_owner
            last_owner = transitions[-1][1] or current_owner
            change_count = len(transitions)
        else:
            first_owner = current_owner
            last_owner = current_owner
            change_count = 0

        out[lid] = {
            "first_owner": first_owner or "",
            "last_owner": last_owner or current_owner or "",
            "change_count": change_count
        }

    frappe.response["message"] = out
