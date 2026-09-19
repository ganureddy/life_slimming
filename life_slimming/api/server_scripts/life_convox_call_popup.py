"""LIFE ConVox Call Popup API

Original API: life_convox_call_popup
Source modified: 2026-09-17 10:58:42.090050
See ../CATALOG.md for migration notes and validation limits.
"""

import json
import re

import frappe
from frappe.integrations.utils import make_post_request as _make_post_request
from frappe.utils.safe_exec import read_sql as _read_sql
from frappe.utils.safe_exec import call_whitelisted_function as _call_whitelisted
from life_slimming.api._runtime import script_endpoint


@script_endpoint(allow_guest=True)
def run(**kwargs):

    settings = frappe.get_doc("System Settings")
    callbacks_enabled = settings.get("custom_convox_callbacks_enabled")

    if not callbacks_enabled:
        frappe.response["http_status_code"] = 503
        frappe.response["status"] = "error"
        frappe.response["message"] = "ConVox callbacks are disabled."
    else:
        expected_token = settings.get_password(
            "custom_convox_callback_token",
            raise_exception=False
        )
        authorization = frappe.request.headers.get("Authorization") or ""
        convox_token = frappe.request.headers.get("X-ConVox-Token") or ""

        if not expected_token or (
            convox_token != expected_token and
            authorization != "Bearer " + expected_token
        ):
            frappe.response["http_status_code"] = 401
            frappe.response["status"] = "error"
            frappe.response["message"] = "Invalid or expired access token."
        else:
            data = frappe.form_dict
            call_reference = data.get("call_hit_reference_number") or data.get("CALL_REFERENCE_ID")
            agent_id = data.get("agent_id") or data.get("USER_ID")
            mobile_number = data.get("mobile_number") or data.get("MOBILE_NO")

            if not call_reference or not agent_id or not mobile_number:
                frappe.response["http_status_code"] = 400
                frappe.response["status"] = "error"
                frappe.response["message"] = "Invalid parameters or missing fields. Required: agent_id, call_hit_reference_number, mobile_number."
            else:
                existing_name = frappe.db.exists(
                    "ConVox Call Event",
                    {
                        "event_type": "Call Popup",
                        "call_reference": call_reference
                    }
                )

                if existing_name:
                    event = frappe.get_doc("ConVox Call Event", existing_name)
                else:
                    event = frappe.new_doc("ConVox Call Event")
                    event.event_type = "Call Popup"
                    event.call_reference = call_reference

                event.agent_id = agent_id
                event.process_name = data.get("process_name") or data.get("PROCESS_NAME")
                event.mobile_number = mobile_number
                event.lead_id = data.get("lead_id") or data.get("LEAD_ID")
                event.call_datetime = data.get("entry_date") or data.get("CALL_DATE")
                event.call_type = data.get("call_type") or data.get("CALL_TYPE")
                event.station = data.get("station") or data.get("STATION")
                event.received_on = frappe.utils.now_datetime()
                event.payload_json = str(dict(data))

                if existing_name:
                    event.save(ignore_permissions=True)
                else:
                    event.insert(ignore_permissions=True)

                frappe.response["status"] = "success"
                frappe.response["message"] = "Call PopUp received successfully."
                frappe.response["event_id"] = event.name
