"""LIFE ConVox Frontend API

Original API: life_convox_frontend
Source modified: 2026-09-17 15:33:58.876662
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

    if frappe.session.user == "Guest":
        frappe.response["http_status_code"] = 403
        frappe.response["status"] = "error"
        frappe.response["message"] = "Login required."
    else:
        action = frappe.form_dict.get("action") or "config"
        user = frappe.get_doc("User", frappe.session.user)
        settings = frappe.get_doc("System Settings")
        enabled = user.get("custom_convox_enabled") or 0
        agent_id = user.get("custom_convox_agent_id") or ""

        if action == "config":
            frappe.response["status"] = "success"
            frappe.response["enabled"] = enabled
            frappe.response["agent_id"] = agent_id
            frappe.response["station"] = user.get("custom_convox_station") or ""
            frappe.response["process"] = user.get("custom_convox_process") or settings.get("custom_convox_default_process") or ""
            frappe.response["queue"] = user.get("custom_convox_queue") or ""
            frappe.response["widget_url"] = settings.get("custom_convox_widget_url") or ""
            frappe.response["toast_seconds"] = settings.get("custom_convox_toast_seconds") or 10
            frappe.response["click_to_call_ready"] = bool(settings.get_password("custom_convox_access_token", raise_exception=False))
        else:
            lead_id = frappe.form_dict.get("lead_id") or ""
            mobile = frappe.form_dict.get("mobile_number") or ""
            call_reference = frappe.form_dict.get("call_reference") or ""
            after = frappe.form_dict.get("after") or ""
            filters = []
            values = {}
            run_query = 1

            if action == "poll":
                if not enabled or not agent_id:
                    frappe.response["status"] = "success"
                    frappe.response["events"] = []
                    run_query = 0
                else:
                    filters.append("agent_id = %(agent_id)s")
                    values["agent_id"] = agent_id
                    filters.append("event_type = 'Call Popup'")
                    if after:
                        filters.append("received_on > %(after)s")
                        values["after"] = after

            elif action == "history":
                match_filters = []
                if lead_id:
                    match_filters.append("lead_id = %(lead_id)s")
                    values["lead_id"] = lead_id
                if mobile:
                    match_filters.append("mobile_number = %(mobile)s")
                    values["mobile"] = mobile
                if call_reference:
                    match_filters.append("call_reference = %(call_reference)s")
                    values["call_reference"] = call_reference
                if match_filters:
                    filters.append("(" + " or ".join(match_filters) + ")")
                else:
                    filters.append("agent_id = %(agent_id)s")
                    values["agent_id"] = agent_id
            else:
                frappe.response["http_status_code"] = 400
                frappe.response["status"] = "error"
                frappe.response["message"] = "Unsupported action."
                run_query = 0

            if action in ("poll", "history") and run_query:
                where_sql = " and ".join(filters) if filters else "1 = 0"
                rows = _read_sql(
                    "select name, event_type, call_reference, agent_id, process_name, mobile_number, lead_id, call_datetime, call_type, station, disposition, call_status, call_mode, call_duration, queue_name, ring_duration, recording_file_name, remarks, received_on from `tabConVox Call Event` where " + where_sql + " order by received_on desc limit 50",
                    values=values,
                    as_dict=True
                )
                frappe.response["status"] = "success"
                frappe.response["events"] = rows
