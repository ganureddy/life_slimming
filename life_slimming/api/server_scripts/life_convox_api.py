"""LIFE ConVox Click To Call API

Original API: life_convox_api
Source modified: 2026-09-17 09:36:47.369089
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

    # ============================================================
    # LIFE CONVOX CLICK-TO-CALL API
    # API Method: life_convox_api
    # ============================================================

    output = {
        "success": False,
        "status": "ERROR",
        "message": "Unable to process ConVox request."
    }

    current_user = frappe.session.user

    if not current_user or current_user == "Guest":
        frappe.throw("Please sign in before starting a call.")

    action = frappe.form_dict.get("action") or "click_to_call"

    if action != "click_to_call":
        frappe.throw("Unsupported ConVox action.")

    lead_id = frappe.form_dict.get("lead_id")

    if not lead_id:
        frappe.throw("Please select a Lead before starting the call.")

    if not frappe.db.exists("Lead", lead_id):
        frappe.throw("Lead not found: " + str(lead_id))

    user = frappe.get_doc("User", current_user)

    if not user.get("custom_convox_enabled"):
        frappe.throw(
            "ConVox calling is not enabled for your User account."
        )

    agent_id = user.get("custom_convox_agent_id")

    if not agent_id:
        frappe.throw(
            "ConVox Agent User ID is missing in your User account."
        )

    settings = frappe.get_doc("System Settings", "System Settings")

    if not settings.get("custom_convox_integration_enabled"):
        frappe.throw(
            "ConVox Integration is disabled in System Settings."
        )

    api_url = settings.get("custom_convox_api_url")

    if not api_url:
        frappe.throw(
            "ConVox Click-to-Call API URL is missing."
        )

    access_token = settings.get_password(
        "custom_convox_access_token"
    )

    if not access_token:
        frappe.throw(
            "ConVox Access Token is missing in System Settings."
        )

    dial_prefix = (
        user.get("custom_convox_dial_prefix")
        or settings.get("custom_convox_default_dial_prefix")
    )

    if not dial_prefix:
        frappe.throw(
            "ConVox Dial Prefix is not configured."
        )

    process_name = (
        user.get("custom_convox_process_name")
        or settings.get("custom_convox_default_process_name")
    )

    lead = frappe.get_doc("Lead", lead_id)

    raw_mobile = (
        lead.get("mobile_no")
        or lead.get("phone")
        or lead.get("custom_mobile_number")
        or ""
    )

    mobile_number = ""

    for character in str(raw_mobile):
        if character >= "0" and character <= "9":
            mobile_number = mobile_number + character

    if len(mobile_number) > 10:
        mobile_number = mobile_number[-10:]

    if len(mobile_number) != 10:
        frappe.throw(
            "Lead must have a valid 10-digit mobile number."
        )

    reference_hash = frappe.generate_hash(length=12)
    reference_clean = ""

    for character in reference_hash:
        if (
            (character >= "a" and character <= "z")
            or (character >= "A" and character <= "Z")
            or (character >= "0" and character <= "9")
            or character == "_"
        ):
            reference_clean = reference_clean + character

    reference_clean = reference_clean.upper()

    refno = "LIFE" + reference_clean

    if len(refno) > 20:
        refno = refno[:20]

    if len(refno) < 6:
        frappe.throw(
            "Unable to generate a valid ConVox reference."
        )

    payload = {
        "action": "CALL",
        "userid": agent_id,
        "phone_number": mobile_number,
        "dial_prefix": str(dial_prefix),
        "refno": refno
    }

    headers = {
        "Content-Type": "application/json",
        "Access-Token": access_token
    }

    api_response = None
    api_error = None

    try:
        api_response = _make_post_request(
            api_url,
            headers=headers,
            json=payload
        )
    except Exception as error:
        api_error = str(error)

    if api_error:
        output = {
            "success": False,
            "status": "CONNECTION_ERROR",
            "message": (
                "Could not connect to the ConVox server. "
                + api_error
            ),
            "lead_id": lead_id,
            "refno": refno
        }

    else:
        response_status = ""
        response_message = ""

        if isinstance(api_response, dict):
            response_status = (
                api_response.get("STATUS")
                or api_response.get("status")
                or ""
            )

            response_message = (
                api_response.get("MESSAGE")
                or api_response.get("message")
                or ""
            )
        else:
            response_message = str(api_response)

        response_status = str(response_status).strip()

        status_messages = {
            "CL000": "Call request accepted successfully.",
            "GE001": "Only the POST method is allowed.",
            "GE002": "ConVox received an empty request.",
            "GE003": "Access-Token header is missing.",
            "GE004": "Call reference number is missing.",
            "GE005": "Call reference format is invalid.",
            "GE006": "Call reference must contain 6 to 20 characters.",
            "GE007": "ConVox Access Token is invalid.",
            "GE008": "ConVox Access Token has expired.",
            "GE009": "ConVox action is invalid.",
            "GE010": "ConVox APIs are not enabled.",
            "CL001": "Mobile number must contain exactly 10 digits.",
            "CL002": "Agent User ID and mobile number are mandatory.",
            "CL003": "The requested ConVox agent is unavailable.",
            "CL004": "The requested ConVox agent is not idle.",
            "CL005": "The agent is ringing or in wrap-up.",
            "CL006": "The ConVox agent is not logged in.",
            "CL007": "The call was attempted outside working hours.",
            "CL008": "The mobile number is on the DNC list.",
            "CL009": "The call limit for this mobile number was exceeded.",
            "CL010": "No PRI channel is currently available.",
            "CL011": "ConVox asterisk variables are invalid."
        }

        final_message = (
            status_messages.get(response_status)
            or response_message
            or "ConVox returned an unknown response."
        )

        call_success = response_status == "CL000"

        if call_success:
            frappe.db.set_value(
                "User",
                current_user,
                {
                    "custom_convox_last_call_reference": refno,
                    "custom_convox_last_call_status": response_status,
                    "custom_convox_last_call_time": frappe.utils.now(),
                    "custom_convox_last_call_lead": lead_id
                },
                update_modified=False
            )

        output = {
            "success": call_success,
            "status": response_status or "UNKNOWN",
            "message": final_message,
            "lead_id": lead_id,
            "lead_name": (
                lead.get("lead_name")
                or lead.get("first_name")
                or lead_id
            ),
            "refno": refno,
            "agent_id": agent_id,
            "process_name": process_name,
            "station": user.get("custom_convox_station"),
            "queue_name": user.get("custom_convox_queue_name")
        }

    frappe.response["message"] = output
