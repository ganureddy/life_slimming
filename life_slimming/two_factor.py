"""MSG91 Flow API override for Frappe 2FA SMS delivery -- FRAPPE v15 VARIANT.

Why this differs from the v16 version:
    Frappe v16 added a `send_token_via_sms` hook. v15 has no such hook, so
    setting it in hooks.py does nothing at all. Instead we rebind
    frappe.twofactor.send_token_via_sms directly. This works because
    process_2fa_for_sms() calls it as a module-level global (v15 line 210),
    so Python resolves the patched name at call time.

Install:
  1. Save as apps/life_slimming/life_slimming/two_factor.py
  2. Append to the BOTTOM of apps/life_slimming/life_slimming/hooks.py:

         try:
             from life_slimming.two_factor import patch as _patch_msg91_2fa
             _patch_msg91_2fa()
         except Exception:
             pass

     Do NOT add `send_token_via_sms = "..."` -- v15 ignores it.
  3. bench --site portal.lifescc.com clear-cache && bench restart

Config lives in SMS Settings > Static Parameters:
    authkey       (tick Header)   MSG91 auth key
    template_id                   MSG91 template id
    short_url                     0
    otp_variable                  the ##name## used in the template
    msg91_debug                   1 to log every response; remove in production
"""

import re

import pyotp
import requests

import frappe
from frappe.utils.background_jobs import enqueue

MSG91_FLOW_URL = "https://control.msg91.com/api/v5/flow"

# Used only when `otp_variable` is not set in SMS Settings.
FALLBACK_VARIABLE_NAMES = ("VAR1", "var1", "OTP", "otp")


def patch():
    """Rebind frappe.twofactor.send_token_via_sms. Idempotent."""
    twofactor = frappe.get_module("frappe.twofactor")

    if getattr(twofactor.send_token_via_sms, "_msg91_patched", False):
        return

    send_otp_via_msg91._msg91_patched = True
    twofactor.send_token_via_sms = send_otp_via_msg91


def send_otp_via_msg91(otpsecret, token=None, phone_no=None):
    """Drop-in replacement. Returns quickly; the HTTP call is queued."""
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
    """Recipient object carrying the OTP under the configured variable name."""
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
        redacted = {
            k: ("<otp>" if k != "mobiles" else v)
            for k, v in payload["recipients"][0].items()
        }
        frappe.log_error(
            title="MSG91 2FA OTP: {0}".format("gateway rejected" if failed else "debug"),
            message="HTTP {0}\n{1}\nrecipient={2}\ntemplate_id={3}".format(
                response.status_code, body, redacted, template_id
            ),
        )