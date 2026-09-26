"""lead_owner_names

Original API: lead_owner_names
Source modified: 2026-08-25 05:28:11.463926
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
    raw = frappe.form_dict.get("leads")
    lead_names = []
    if isinstance(raw, (list, tuple)):
        lead_names = list(raw)
    elif isinstance(raw, str):
        txt = raw.strip()
        if txt.startswith("["):
            txt = txt[1:]
        if txt.endswith("]"):
            txt = txt[:-1]
        for part in txt.split(","):
            cleaned = part.strip().strip(chr(34)).strip(chr(39)).strip()
            if cleaned:
                lead_names.append(cleaned)

    def derive_cat(enq, interests):
        blob = (str(enq or "") + " " + str(interests or "")).lower()
        if "hair" in blob:
            return "Hair"
        if "skin" in blob or "laser" in blob:
            return "Skin"
        if "slim" in blob or "weight" in blob or "cryo" in blob or "fat" in blob:
            return "Slimming"
        return ""

    out = {}
    if lead_names:
        lead_rows = frappe.get_all("Lead",
            filters={"name": ["in", lead_names]},
            fields=["name", "lead_owner", "custom_status_updated_by_name",
                    "enquired_for", "custom_treatment_interests",
                    "custom_appointment_status", "custom_visit_status", "custom_remarks"],
            ignore_permissions=True, limit_page_length=0)
        owner_ids = []
        for row in lead_rows:
            if row.get("lead_owner"):
                owner_ids.append(row.get("lead_owner"))
        name_map = {}
        if owner_ids:
            user_rows = frappe.get_all("User",
                filters={"name": ["in", owner_ids]},
                fields=["name", "full_name"],
                ignore_permissions=True, limit_page_length=0)
            for u in user_rows:
                name_map[u.get("name")] = u.get("full_name") or u.get("name")
        for row in lead_rows:
            owner = row.get("lead_owner")
            if owner:
                owner_name = name_map.get(owner, owner)
            else:
                owner_name = row.get("custom_status_updated_by_name") or ""
            out[row.get("name")] = {
                "owner": owner_name,
                "category": derive_cat(row.get("enquired_for"), row.get("custom_treatment_interests")),
                "appt_status": row.get("custom_appointment_status") or "",
                "visit_status": row.get("custom_visit_status") or "",
                "remarks": row.get("custom_remarks") or ""
            }

    frappe.response["message"] = out
