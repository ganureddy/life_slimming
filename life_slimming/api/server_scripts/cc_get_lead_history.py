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
    # A failed call against an already-booked lead deliberately does not change
    # the appointment state.  It is instead written to the append-only activity
    # log, so include that log here as part of the customer-facing history.
    # Otherwise the dialog only shows the next-follow-up field Version and hides
    # the actual call outcome (for example, "No Response").
    activities = frappe.get_all(
        "CC Lead Activity Log",
        filters={"lead": lead},
        fields=["event_time", "erp_user", "action", "new_status", "next_followup", "change_json"],
        order_by="event_time asc",
        limit_page_length=200,
    )
    track = frappe.db.get_value(
        "LIFE CC Lead Track", lead,
        ["last_call_result", "last_call_at", "modified_by"],
        as_dict=True,
    ) or {}
    last_call_at = str(track.get("last_call_at") or "")
    latest_call_added = False
    activity_rows = []
    for activity in activities:
        event_time = str(activity.get("event_time") or "")
        is_latest_call = (
            activity.get("action") == "call"
            and last_call_at
            and event_time[:19] == last_call_at[:19]
        )
        if is_latest_call:
            latest_call_added = True
        activity_rows.append({
            "creation": event_time,
            "owner": activity.get("erp_user") or "User",
            "history_type": "activity",
            "activity_action": activity.get("action") or "Activity",
            "call_result": track.get("last_call_result") if is_latest_call else "",
            "new_status": activity.get("new_status") or "",
            "next_followup": str(activity.get("next_followup") or ""),
        })

    # Older records can pre-date the activity log.  The track still has the
    # latest saved outcome, so expose it once rather than hiding it entirely.
    if last_call_at and track.get("last_call_result") and not latest_call_added:
        activity_rows.append({
            "creation": last_call_at,
            "owner": track.get("modified_by") or "User",
            "history_type": "activity",
            "activity_action": "call",
            "call_result": track.get("last_call_result"),
            "new_status": "",
            "next_followup": "",
        })

    history = rows + activity_rows
    history.sort(key=lambda row: str(row.get("creation") or ""))
    frappe.response["message"] = history
