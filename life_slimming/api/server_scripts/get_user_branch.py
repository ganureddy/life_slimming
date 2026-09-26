"""Get Current User's Branch

Original API: get_user_branch
Source modified: 2026-06-03 23:16:14.846679
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
    ## ═══════════════════════════════════════════════════════════
    ## SERVER SCRIPT — Get Current User's Branch
    ## ═══════════════════════════════════════════════════════════
    ## Script Type  : API
    ## API Method   : get_user_branch
    ## Allow Guest  : NO
    ## Enabled      : YES
    ## ═══════════════════════════════════════════════════════════
    ## Uses frappe.get_all with ignore_permissions=True so branch
    ## staff never get "Not Permitted" errors on any lookup.
    ## ═══════════════════════════════════════════════════════════

    current_user = frappe.session.user
    branch = ""
    is_admin = False

    # ── STEP 1: Check if System Manager ──────────────────────────────────────────
    # frappe.get_all() supports ignore_permissions=True (db.get_value does NOT)
    roles = frappe.get_all(
        "Has Role",
        filters={"parent": current_user, "parenttype": "User", "role": "System Manager"},
        fields=["name"],
        limit=1,
        ignore_permissions=True
    )
    is_admin = len(roles) > 0

    # Admins see all branches — return early
    if is_admin:
        frappe.response["message"] = {"branch": "", "is_admin": True}
        raise SystemExit

    # ── STEP 2: Get branch from Employee record linked to this user ───────────────
    employees = frappe.get_all(
        "Employee",
        filters={"user_id": current_user, "status": "Active"},
        fields=["branch"],
        limit=1,
        ignore_permissions=True
    )
    if employees and employees[0].get("branch"):
        branch = employees[0]["branch"]

    # ── STEP 3: Fallback — User Permission table ──────────────────────────────────
    if not branch:
        perms = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Branch"},
            fields=["for_value"],
            limit=1,
            ignore_permissions=True
        )
        if perms and perms[0].get("for_value"):
            branch = perms[0]["for_value"]

    # ── RESPOND ───────────────────────────────────────────────────────────────────
    frappe.response["message"] = {
        "branch": branch,
        "is_admin": False
    }
