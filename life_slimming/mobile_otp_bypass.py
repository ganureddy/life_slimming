"""Single-use recovery codes issued by the LIFE mobile Access Control API."""

import functools
import hashlib
import hmac
import json
import re

import frappe
from frappe.utils import get_datetime, now_datetime
from frappe.rate_limiter import rate_limit

STORE = "LIFE_MOBILE_BYPASS_STORE"
MARKER = "<!--LIFE_BYPASS:"


def _read_store():
    rows = frappe.get_all("Note", filters={"title": STORE}, fields=["name"], limit_page_length=1)
    if not rows:
        return None, {}
    # Serialize consumption with other database writers, including the v5 API.
    content = frappe.db.sql("select content from `tabNote` where name=%s for update", rows[0].name)[0][0]
    start = content.index(MARKER) + len(MARKER)
    end = content.index("-->", start)
    return rows[0].name, json.loads(content[start:end])


def _matching_code(data, target, purpose, code):
    if not re.fullmatch(r"[0-9]{6}", str(code)):
        return None
    for item in data.get("codes", []):
        if (item.get("target") != target or item.get("purpose") != purpose
                or item.get("used") or not item.get("exp")):
            continue
        if get_datetime(item["exp"]) < now_datetime():
            continue
        digest = hashlib.sha256(f'{item.get("salt")}|{code}'.encode()).hexdigest()
        if hmac.compare_digest(digest, str(item.get("hash", ""))):
            return item
    return None


def _redeem_login(user, code):
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return False
    name, data = _read_store()
    item = _matching_code(data, user.lower(), "login", code)
    if item is None:
        return False
    stamp = str(now_datetime())[:19]
    item.update(used=1, used_by=user, used_at=stamp)
    data.setdefault("audit", []).append({"at": stamp, "by": user, "event": "redeem", "target": user.lower(), "info": "login"})
    data["audit"] = data["audit"][-500:]
    content = MARKER + json.dumps(data).replace("-->", "--\\u003e") + "-->\n<p>LIFE mobile bypass store. Managed by Access Control. Do not edit by hand.</p>"
    frappe.db.set_value("Note", name, "content", content)
    # Persist consumption before the login machinery commits or rolls back.
    frappe.db.commit()
    return True


def install():
    """Install once per worker via before_request, without modifying Frappe."""
    import frappe.twofactor as twofactor
    import frappe.auth as auth

    original = twofactor.confirm_otp_token
    if getattr(original, "_life_mobile_bypass", False):
        return

    @functools.wraps(original)
    def confirm_otp_token(login_manager, otp=None, tmp_id=None):
        code = otp or frappe.form_dict.get("otp")
        challenge = tmp_id or frappe.form_dict.get("tmp_id")
        user = login_manager.user
        if code and challenge:
            cached_user = frappe.safe_decode(frappe.cache.get(challenge + "_usr"))
            secret = frappe.cache.get(challenge + "_otp_secret")
            if cached_user == user and secret:
                try:
                    accepted = _redeem_login(user, code)
                except Exception:
                    frappe.db.rollback()
                    accepted = False
                    frappe.log_error(title="Login recovery code validation failed")
                if accepted:
                    from frappe.auth import get_login_attempt_tracker
                    for suffix in ("_token", "_usr", "_pwd", "_otp_secret"):
                        frappe.cache.delete(challenge + suffix)
                    get_login_attempt_tracker(user).add_success_attempt()
                    return True
        return original(login_manager, otp=otp, tmp_id=tmp_id)

    confirm_otp_token._life_mobile_bypass = True
    twofactor.confirm_otp_token = confirm_otp_token
    # v15 imports this function into auth rather than resolving the module name.
    auth.confirm_otp_token = confirm_otp_token


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=5, seconds=300)
def verify_billing_bypass(mobile, code):
    """Redeem a billing recovery code and grant the normal registration proof."""
    from frappe.core.doctype.server_script.server_script_utils import get_server_script_map
    from life_slimming.user_wise_roles import OTP_EXPIRY

    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw("Please login", frappe.PermissionError)
    mobile = re.sub(r"\D", "", str(mobile))
    if len(mobile) == 12 and mobile.startswith("91"):
        mobile = mobile[2:]
    elif len(mobile) == 11 and mobile.startswith("0"):
        mobile = mobile[1:]
    code = str(code).strip()
    if not re.fullmatch(r"[6-9][0-9]{9}", mobile):
        frappe.throw("Enter a valid 10-digit Indian mobile number.")
    _, data = _read_store()
    # v5 itself does not filter by purpose. Never consume a login code here.
    if _matching_code(data, "billing", "billing", code) is None:
        frappe.throw("Invalid or expired billing code.")
    script_name = get_server_script_map().get("_api", {}).get("life_mobile_bypass_v5")
    if not script_name:
        frappe.throw("Billing recovery service is unavailable.")
    saved_form, saved_response = frappe.local.form_dict, frappe.local.response
    try:
        frappe.local.form_dict = frappe._dict(action="redeem", target="billing", code=code, mobile=mobile)
        frappe.local.response = frappe._dict()
        frappe.get_doc("Server Script", script_name).execute_method()
        result = frappe.local.response.get("message") or {}
    finally:
        frappe.local.form_dict, frappe.local.response = saved_form, saved_response
    if result.get("ok") != 1 or result.get("purpose") != "billing":
        frappe.throw("Invalid or expired billing code.")
    frappe.cache.set_value(f"client_otp_verified::{frappe.session.user}::{mobile}", 1, expires_in_sec=OTP_EXPIRY)
    return {"verified": True, "mobile": mobile}
