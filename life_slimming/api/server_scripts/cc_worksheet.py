"""cc_worksheet

Original API: cc_worksheet
Source modified: 2026-07-31 05:55:38.130652
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
    # Server Script — cc_worksheet
    # Script Type : API   |   API Method: cc_worksheet   |   Allow Guest: NO
    #
    # Backs the Excel-like "My Worksheet" tab in the CC dashboard.
    #   list / save / delete, all scoped to frappe.session.user.

    MANAGER_ROLES = ["System Manager", "Sales Manager"]

    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Not permitted")

    user_roles = frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")

    is_manager = False
    for r in MANAGER_ROLES:
        if r in user_roles:
            is_manager = True
            break

    ALLOWED_ROLES = ["System Manager", "Sales Manager", "Sales User", "Call Center Export"]
    has_access = False
    for r in ALLOWED_ROLES:
        if r in user_roles:
            has_access = True
            break
    if not has_access:
        frappe.throw("Not permitted")


    def mask_mobile(v):
        return str(v or "").strip()


    action = frappe.form_dict.get("action") or "list"

    if action == "list":
        ws_filters = {} if is_manager else {"owner": user}
        rows = frappe.get_all(
            "CC Worksheet",
            filters=ws_filters,
            fields=["name", "owner", "client_name", "mobile", "area", "enquired_for",
                    "status", "posting_date", "followup_date", "notes", "row_order", "modified"],
            order_by="owner asc, row_order asc, creation asc",
            limit_page_length=2000
        )
        out = []
        for r in rows:
            out.append({
                "name": r.get("name"),
                "owner": r.get("owner") or "",
                "client_name": r.get("client_name") or "",
                "mobile": mask_mobile(r.get("mobile")),
                "area": r.get("area") or "",
                "enquired_for": r.get("enquired_for") or "",
                "status": r.get("status") or "",
                "posting_date": str(r.get("posting_date") or ""),
                "followup_date": str(r.get("followup_date") or ""),
                "notes": r.get("notes") or "",
                "row_order": r.get("row_order") or 0
            })
        frappe.response["message"] = {"rows": out, "masked": 0, "manager_view": 1 if is_manager else 0, "me": user}

    elif action == "save":
        payload = frappe.form_dict.get("rows")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload or "[]")
            except Exception:
                frappe.throw("rows could not be parsed as JSON")
        if not isinstance(payload, list):
            frappe.throw("rows must be a JSON list")

        FIELDS = ["client_name", "mobile", "area", "enquired_for", "status",
                  "posting_date", "followup_date", "notes", "row_order"]

        saved = 0
        created = 0
        for row in payload:
            if not isinstance(row, dict):
                continue
            name = row.get("name")

            vals = {}
            for f in FIELDS:
                if f in row:
                    vals[f] = row.get(f)
            if "mobile" in vals and "X" in str(vals.get("mobile") or "").upper():
                del vals["mobile"]

            if name:
                existing_owner = frappe.db.get_value("CC Worksheet", name, "owner")
                if existing_owner != user and not is_manager:
                    continue
                doc = frappe.get_doc("CC Worksheet", name)
                for k in vals:
                    doc.set(k, vals.get(k))
                doc.save(ignore_permissions=True)
                saved += 1
            else:
                if not (vals.get("client_name") or "").strip():
                    continue
                doc = frappe.new_doc("CC Worksheet")
                for k in vals:
                    doc.set(k, vals.get(k))
                doc.insert(ignore_permissions=True)
                created += 1

        frappe.db.commit()
        frappe.response["message"] = {"saved": saved, "created": created}

    elif action == "delete":
        name = frappe.form_dict.get("name")
        if not name:
            frappe.throw("name is required")
        existing_owner = frappe.db.get_value("CC Worksheet", name, "owner")
        if existing_owner != user and not is_manager:
            frappe.throw("Not permitted: that row is not yours")
        frappe.delete_doc("CC Worksheet", name, ignore_permissions=True)
        frappe.db.commit()
        frappe.response["message"] = {"deleted": name}

    else:
        frappe.throw("Unknown action")
