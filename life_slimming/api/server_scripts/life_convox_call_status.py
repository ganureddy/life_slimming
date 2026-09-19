"""LIFE ConVox Call Status API

Original API: life_convox_call_status
Source modified: 2026-09-17 15:33:58.926182
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
            call_reference = data.get("CALL_REFERENCE_ID") or data.get("call_hit_reference_number")
            agent_id = data.get("USER_ID") or data.get("agent_id")
            mobile_number = data.get("MOBILE_NO") or data.get("mobile_number")

            if not call_reference or not mobile_number:
                frappe.response["http_status_code"] = 400
                frappe.response["status"] = "error"
                frappe.response["message"] = "Invalid parameters or missing fields. Required: CALL_REFERENCE_ID, MOBILE_NO."
            else:
                existing_name = frappe.db.exists(
                    "ConVox Call Event",
                    {
                        "event_type": "Call Status",
                        "call_reference": call_reference
                    }
                )

                if existing_name:
                    event = frappe.get_doc("ConVox Call Event", existing_name)
                else:
                    event = frappe.new_doc("ConVox Call Event")
                    event.event_type = "Call Status"
                    event.call_reference = call_reference

                event.agent_id = agent_id
                event.process_name = data.get("PROCESS_NAME") or data.get("process_name")
                event.mobile_number = mobile_number
                event.lead_id = data.get("LEAD_ID") or data.get("lead_id")
                event.call_datetime = data.get("CALL_DATE") or data.get("entry_date")
                event.station = data.get("STATION") or data.get("station")
                event.disposition = data.get("DISPOSITION")
                event.disposition_2 = data.get("disposition2")
                event.disposition_3 = data.get("disposition3")
                event.call_status = data.get("CALL_STATUS")
                event.call_mode = data.get("CALL_MODE")
                event.call_duration = data.get("CALL_DURATION")
                event.completed_by = data.get("COMPLETED_BY")
                event.queue_name = data.get("QUEUE_NAME")
                event.queue_duration = data.get("QUEUE_DURATION")
                event.ring_duration = data.get("RING_DURATION")
                event.followup_time = data.get("FOLLOWUP_TIME")
                event.list_id = data.get("LIST_ID")
                event.did = data.get("DID")
                event.recording_file_name = data.get("RECORDING_FILE_NAME") or data.get("recording_file_name") or data.get("recording_url")
                if event.recording_file_name:
                    event.recording_available = 1
                    event.recording_received_on = frappe.utils.now_datetime() or data.get("recording_file_name") or data.get("recording_url")
                if event.recording_file_name:
                    event.recording_available = 1
                    event.recording_received_on = frappe.utils.now_datetime() or data.get("recording_file_name") or data.get("recording_url")
                if event.recording_file_name:
                    event.recording_available = 1
                    event.recording_received_on = frappe.utils.now_datetime() or data.get("recording_file_name") or data.get("recording_url")
                if event.recording_file_name:
                    event.recording_available = 1
                    event.recording_received_on = frappe.utils.now_datetime() or data.get("recording_file_name") or data.get("recording_url")
                if event.recording_file_name:
                    event.recording_available = 1
                    event.recording_received_on = frappe.utils.now_datetime() or data.get("recording_file_name") or data.get("recording_url")
                if event.recording_file_name:
                    event.recording_available = 1
                    event.recording_received_on = frappe.utils.now_datetime()
                event.remarks = data.get("remarks")
                event.received_on = frappe.utils.now_datetime()
                event.payload_json = str(dict(data))

                if existing_name:
                    event.save(ignore_permissions=True)
                else:
                    event.insert(ignore_permissions=True)

                frappe.response["status"] = "success"
                frappe.response["message"] = "Call status updated successfully."
                frappe.response["event_id"] = event.name
