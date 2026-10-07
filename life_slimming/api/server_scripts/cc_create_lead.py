"""cc_create_lead

Original API: cc_create_lead
Source modified: 2026-09-17 10:24:41.373281
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
    # Server Script: cc_create_lead
    # Script Type : API   |   API Method: cc_create_lead   |   Allow Guest: NO
    # Replaces the Add New Lead flow (duplicate check via frappe.client.get_list
    # + frappe.client.insert) with ONE server call.
    # Duplicate check uses last-10-digit SUFFIX matching ("%<digits>", anchored
    # at the end) — this also fixes the false-positive you hit earlier where
    # 918959533301 loosely collided with 9959533301 on a last-9 substring match.
    # Authorized managers may choose an existing Lead Owner. For other users,
    # the creator remains the owner. A blank manager selection leaves assignment
    # to the existing Lead before_insert round-robin logic.
    # ═══════════════════════════════════════════════════════════════════

    ALLOWED_ROLES = ["System Manager", "Sales Manager", "Sales User", "Call Center Export"]

    ALLOWED_CREATE_FIELDS = [
        "first_name", "mobile_no", "phone", "email_id", "age", "gender", "city",
        "source", "branch", "lead_assign_to_branch", "enquired_for", "custom_remarks",
        "status", "custom_cc_stage", "custom_media", "custom_posting_date", "category",
        "lead_owner"
    ]

    # Only these roles may CHOOSE the lead owner. Everyone else gets themselves,
    # regardless of what the client sends.
    OWNER_EDIT_ROLES = ["System Manager", "Sales Manager", "Call Center Export"]

    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Not permitted")

    user_roles = frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")
    has_access = False
    for r in ALLOWED_ROLES:
        if r in user_roles:
            has_access = True
            break

    can_choose_owner = False
    for r in OWNER_EDIT_ROLES:
        if r in user_roles:
            can_choose_owner = True
            break
    if not has_access:
        frappe.throw("Not permitted")

    # NOTE: frappe.parse_json is NOT available inside safe_exec (Server Scripts).
    values = frappe.form_dict.get("values")
    if isinstance(values, str):
        try:
            values = json.loads(values or "{}")
        except Exception:
            frappe.throw("values could not be parsed as JSON")
    if not isinstance(values, dict):
        frappe.throw("values must be a JSON object")

    mobile = str(values.get("mobile_no") or "").strip()
    digits = ""
    for ch in mobile:
        if ch.isdigit():
            digits = digits + ch
    digits = digits[-10:]
    if len(digits) != 10:
        frappe.throw("A valid 10-digit mobile number is required")

    # Duplicate check: number ENDS WITH the same 10 digits (handles +91 prefixes,
    # avoids loose substring false-positives)
    dup = frappe.get_all(
        "Lead",
        fields=["name", "lead_name", "status", "lead_owner"],
        or_filters=[
            ["mobile_no", "like", "%" + digits],
            ["phone", "like", "%" + digits]
        ],
        limit_page_length=1
    )

    if dup:
        frappe.response["message"] = {"duplicate": dup[0]}
    else:
        d = {"doctype": "Lead"}
        requested_owner = str(values.get("lead_owner") or "").strip()
        if can_choose_owner:
            if requested_owner:
                owner = frappe.db.get_value("User", requested_owner, "name")
                if not owner:
                    frappe.throw("Choose a valid Lead Owner")
                values["lead_owner"] = owner
            else:
                values.pop("lead_owner", None)
        else:
            values["lead_owner"] = user

        for k in ALLOWED_CREATE_FIELDS:
            if k in values and values[k] not in (None, ""):
                d[k] = values[k]
        d["mobile_no"] = digits
        doc = frappe.get_doc(d)
        doc.insert(ignore_permissions=True)
        frappe.response["message"] = {"created": doc.name, "lead_owner": doc.lead_owner}
