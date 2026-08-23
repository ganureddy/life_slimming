"""MSG91 Flow API override for Frappe 2FA SMS delivery (v2).

Changes from v1:
  * The template variable name is no longer hardcoded to VAR1. Set a static
    parameter `otp_variable` in SMS Settings to pin it. If unset, the OTP is
    sent under several common aliases at once -- MSG91 ignores names that do
    not exist in the template, so whichever one matches will render.
  * Set a static parameter `msg91_debug` = 1 in SMS Settings to log every
    MSG91 response body to Error Log, not just failures. Turn it off once
    delivery is confirmed.

Install:
  1. Save as apps/life_slimming/life_slimming/two_factor.py (replacing v1)
  2. hooks.py should already contain:
         send_token_via_sms = "life_slimming.two_factor.send_otp_via_msg91"
  3. bench --site health.lifescc.com clear-cache && bench restart
"""

import re

import pyotp
import requests

import frappe
from frappe.utils.background_jobs import enqueue

MSG91_FLOW_URL = "https://control.msg91.com/api/v5/flow"

# Tried together when `otp_variable` is not configured in SMS Settings.
FALLBACK_VARIABLE_NAMES = ("VAR1", "var1", "OTP", "otp")


def send_otp_via_msg91(otpsecret, token=None, phone_no=None):
    """Hook target. Returns quickly; the HTTP call is queued."""
    if not phone_no:
        return False

    settings = frappe.get_doc("SMS Settings", "SMS Settings")
    if not settings.sms_gateway_url:
        return False

    mobile = re.sub(r"\D", "", str(phone_no))
    if len(mobile) == 10:  # bare Indian number, add country code
        mobile = "91" + mobile

    otp = pyotp.HOTP(otpsecret).at(int(token))

    enqueue(
        method="life_slimming.two_factor.dispatch_msg91_otp",
        queue="short",
        timeout=300,
        is_async=True,
        now=False,
        mobile=mobile,
        otp=otp,
    )
    return True


def build_recipient(mobile, otp, static):
    """Recipient object carrying the OTP under the configured variable name(s)."""
    recipient = {"mobiles": mobile}

    configured = (static.get("otp_variable") or "").strip()
    names = [configured] if configured else list(FALLBACK_VARIABLE_NAMES)

    for name in names:
        recipient[name] = otp

    return recipient


def dispatch_msg91_otp(mobile, otp):
    """Runs in the background worker."""
    settings = frappe.get_doc("SMS Settings", "SMS Settings")
    static = {d.parameter: d.value for d in settings.get("parameters")}

    authkey = static.get("authkey")
    template_id = static.get("template_id")
    if not (authkey and template_id):
        frappe.log_error(
            title="MSG91 2FA OTP: missing config",
            message="authkey or template_id absent from SMS Settings parameters",
        )
        return

    payload = {
        "template_id": template_id,
        "short_url": static.get("short_url", "0"),
        "realTimeResponse": "1",
        "recipients": [build_recipient(mobile, otp, static)],
    }

    try:
        response = requests.post(
            settings.sms_gateway_url or MSG91_FLOW_URL,
            json=payload,
            headers={
                "authkey": authkey,
                "content-type": "application/json",
                "accept": "application/json",
            },
            timeout=30,
        )
    except Exception:
        frappe.log_error(title="MSG91 2FA OTP: request failed")
        return

    body = response.text or ""
    failed = (
        response.status_code >= 300
        or '"type":"error"' in body
        or '"type": "error"' in body
    )
    debug = str(static.get("msg91_debug") or "").strip() in ("1", "true", "True")

    if failed or debug:
        redacted = frappe.parse_json(frappe.as_json(payload))
        redacted["recipients"] = [
            {k: ("<otp>" if k != "mobiles" else v) for k, v in payload["recipients"][0].items()}
        ]
        frappe.log_error(
            title="MSG91 2FA OTP: {0}".format("gateway rejected" if failed else "debug"),
            message="HTTP {0}\n{1}\npayload={2}".format(
                response.status_code, body, frappe.as_json(redacted)
            ),
        )