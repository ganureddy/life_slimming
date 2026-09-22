"""ConVox integration. Credentials and SSO encryption stay on the Frappe server."""
import base64
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta
from urllib.parse import quote, urlencode, urlsplit

import frappe
import requests
from werkzeug.wrappers import Response
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from frappe.utils import now_datetime

ORIGIN = "https://lifeslimming.deepijatel.in"
WIDGET_URL = ORIGIN + "/ConVoxCCS/"
API_URL = ORIGIN + "/ConVoxCCS/rest/api"
MANAGERS = {"System Manager", "Sales Manager", "Call Center Export"}
ROLES = MANAGERS | {"Sales User", "Branch Sales Invoice"}
EVENT_FIELDS = ["name", "event_type", "call_reference", "mobile_number", "lead_id", "call_type",
                "call_status", "disposition", "call_duration", "received_on"]
STATUS_MESSAGES = {
    "CL000": "Call request accepted. Answer through the ConVox phone.",
    "GE001": "ConVox rejected the request method. Contact your administrator.",
    "GE002": "ConVox received an empty request. Contact your administrator.",
    "GE003": "ConVox requires an access token. Contact your administrator.",
    "GE004": "ConVox requires a call reference. Contact your administrator.",
    "GE005": "ConVox rejected the call reference format. Contact your administrator.",
    "GE006": "ConVox rejected the call reference length. Contact your administrator.",
    "GE007": "ConVox rejected the access token. Contact your administrator.",
    "GE008": "The ConVox access token expired. Contact your administrator.",
    "GE009": "ConVox rejected the call action. Contact your administrator.",
    "GE010": "ConVox API access is not enabled. Contact ConVox support.",
    "CL001": "The lead needs a valid 10-digit phone number.",
    "CL002": "ConVox requires an agent ID and phone number.",
    "CL003": "Your ConVox agent is unavailable.",
    "CL004": "Set your ConVox agent to Idle before calling.",
    "CL005": "Finish the current call or wrap-up before calling again.",
    "CL006": "Sign in to the ConVox phone before calling.",
    "CL007": "Calling is unavailable outside working hours.",
    "CL008": "This number is on the do-not-call list.",
    "CL009": "The call limit for this number has been reached.",
    "CL010": "No phone channel is available. Please try later.",
    "CL011": "ConVox telephony configuration is invalid. Contact ConVox support.",
}


def _secret(settings, field):
    return settings.get_password(field, raise_exception=False) or ""


def _identity():
    if not frappe.session.user or frappe.session.user == "Guest":
        raise frappe.AuthenticationError("Sign in to LIFE Portal first.")
    if not ROLES.intersection(frappe.get_roles()):
        raise frappe.PermissionError("CC dashboard access is required.")
    return frappe.get_doc("User", frappe.session.user), frappe.get_doc("System Settings")


def _enabled(user, settings):
    return bool(settings.get("custom_convox_integration_enabled") and user.get("custom_convox_enabled"))


def _require_enabled():
    user, settings = _identity()
    if not _enabled(user, settings):
        raise frappe.PermissionError("ConVox calling is not enabled for this account.")
    agent = user.get("custom_convox_agent_id")
    if agent and frappe.db.count("User", {"enabled": 1, "custom_convox_enabled": 1, "custom_convox_agent_id": agent}) != 1:
        raise frappe.ValidationError("Each ConVox agent must map to exactly one enabled portal user.")
    return user, settings


def _url(value, path):
    value = value or ORIGIN + path
    url = urlsplit(value)
    if url.scheme != "https" or url.netloc != urlsplit(ORIGIN).netloc or url.path != path or url.query or url.fragment:
        raise frappe.ValidationError("ConVox URL must use the configured HTTPS domain and documented endpoint.")
    return value


def encrypt_username(username, secret, iv_value, iv_mode):
    """Match the documented PHP SHA-256 key derivation + AES-CBC + PKCS#7.

    The vendor PDF is ambiguous about IV decoding. Require an explicit choice;
    never silently try both modes or use the sample shared secret.
    """
    if not username or not secret or not iv_value:
        raise ValueError("SSO settings are incomplete")
    if iv_mode == "base64":
        iv = base64.b64decode(iv_value, validate=True)
    elif iv_mode == "php_literal_prefix":
        iv = iv_value.encode("utf-8")[:16]
    else:
        raise ValueError("Confirm the ConVox IV mode")
    if len(iv) != 16:
        raise ValueError("ConVox IV must resolve to 16 bytes")
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(username.encode("utf-8")) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return base64.b64encode(encryptor.update(padded) + encryptor.finalize()).decode("ascii")


def _sso_ready(settings):
    try:
        encrypt_username("configuration-check", _secret(settings, "custom_convox_sso_secret"),
                         settings.get("custom_convox_sso_iv"), settings.get("custom_convox_sso_iv_mode"))
        return True
    except (ValueError, TypeError):
        return False


@frappe.whitelist(methods=["POST"])
def config():
    user, settings = _identity()
    enabled = _enabled(user, settings)
    agent = user.get("custom_convox_agent_id")
    unique_agent = bool(agent) and frappe.db.count("User", {
        "enabled": 1, "custom_convox_enabled": 1, "custom_convox_agent_id": agent}) == 1
    token_ready = bool(_secret(settings, "custom_convox_token_key" if settings.get("custom_convox_auto_token_enabled") else "custom_convox_access_token"))
    prefix_ready = bool(user.get("custom_convox_dial_prefix") or settings.get("custom_convox_default_dial_prefix"))
    sso_enabled = bool(settings.get("custom_convox_sso_enabled"))
    sso_ready = sso_enabled and _sso_ready(settings)
    issues = []
    if not settings.get("custom_convox_integration_enabled"):
        issues.append("Enable ConVox in System Settings.")
    if not user.get("custom_convox_enabled"):
        issues.append("Enable ConVox for your User account.")
    if not agent:
        issues.append("Enter your ConVox agent ID in your User account.")
    elif not unique_agent:
        issues.append("Map this ConVox agent ID to exactly one enabled portal user.")
    if not token_ready:
        issues.append("Configure the ConVox token-generation key (automatic mode) or access token in System Settings.")
    if not prefix_ready:
        issues.append("Configure your ConVox dial prefix in System Settings or your User account.")
    if sso_enabled and not sso_ready:
        issues.append("Complete the SSO secret, IV and confirmed IV interpretation in System Settings.")
    can_manage = frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()
    return {"enabled": enabled, "agent_id": agent or "", "setup_issues": issues,
            "can_manage": can_manage,
            "user_settings_url": "/app/user/" + quote(user.name, safe="") if can_manage else None,
            "widget_url": _url(settings.get("custom_convox_widget_url"), "/ConVoxCCS/"),
            "sso_ready": enabled and sso_ready,
            "click_to_call_ready": enabled and unique_agent and token_ready and prefix_ready
                and (not sso_enabled or sso_ready),
            "callbacks_ready": enabled and bool(settings.get("custom_convox_callbacks_enabled"))
                and unique_agent and bool(frappe.db.exists("DocType", "ConVox Call Event")),
            "server_time": str(now_datetime())}


@frappe.whitelist(methods=["POST"])
def widget_session(manual=False):
    user, settings = _require_enabled()
    # Never cache this URL or return the raw secret/IV/access token.
    def result(value):
        return Response(json.dumps({"message": value}), mimetype="application/json",
                        headers={"Cache-Control": "no-store", "Pragma": "no-cache"})
    url = _url(settings.get("custom_convox_widget_url"), "/ConVoxCCS/")
    if frappe.utils.cint(manual) or not settings.get("custom_convox_sso_enabled"):
        return result({"url": url, "mode": "manual"})
    if not _sso_ready(settings):
        raise frappe.ValidationError("ConVox SSO settings need administrator confirmation. Use manual login until configured.")
    username = user.get("custom_convox_sso_username") or user.name
    encrypted = encrypt_username(username, _secret(settings, "custom_convox_sso_secret"),
                                 settings.get("custom_convox_sso_iv"), settings.get("custom_convox_sso_iv_mode"))
    return result({"url": url + "?" + urlencode({"ExternalUserName": encrypted}), "mode": "sso"})


def _access_token(settings):
    if not settings.get("custom_convox_auto_token_enabled"):
        return _secret(settings, "custom_convox_access_token")
    key = _secret(settings, "custom_convox_token_key")
    if not key:
        raise frappe.ValidationError("Configure the ConVox token-generation key in System Settings.")
    # The vendor returns the existing valid token, or generates a replacement.
    # Retrieve before each new dial instead of caching against an unspecified timezone.
    # Never log credentials or persist returned calling tokens in browser storage.
    try:
        response = requests.post(ORIGIN + "/ConVoxCCS/rest/secureToken",
            headers={"Content-Type": "application/json", "Access-Token": key},
            timeout=(5, 8), allow_redirects=False)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        raise frappe.ValidationError("Could not retrieve the ConVox calling token. No call was sent. Try again or contact ConVox support.") from None
    token = data.get("REFRESH_TOKEN") if isinstance(data, dict) else None
    if (not isinstance(data, dict) or str(data.get("STATUS", "")).upper() != "SUCCESS"
            or not isinstance(token, str) or not token or len(token) > 8192
            or any(character.isspace() for character in token)):
        raise frappe.ValidationError("ConVox rejected token generation or returned an invalid token. No call was sent. Check the token-generation key with ConVox support.")
    return token


def normalize_phone(raw):
    number = re.sub(r"[\s()+.-]", "", str(raw or ""))
    if len(number) == 12 and number.startswith("91"):
        number = number[2:]
    elif len(number) == 11 and number.startswith("0"):
        number = number[1:]
    if not re.fullmatch(r"[0-9]{10}", number):
        raise frappe.ValidationError("The lead needs a valid 10-digit phone number.")
    return number


def _lead(lead_id):
    if not isinstance(lead_id, str) or not lead_id or len(lead_id) > 140:
        raise frappe.ValidationError("Select a lead before calling.")
    lead = frappe.get_doc("Lead", lead_id)
    # Same owner/manager policy as cc_get_leads; agents may have SELECT-only Lead permissions.
    if lead.get("lead_owner") != frappe.session.user and not MANAGERS.intersection(frappe.get_roles()):
        raise frappe.PermissionError("You may only call leads assigned to you.")
    return lead


def _lead_number(lead):
    if not lead.get("mobile_no"):
        raise frappe.ValidationError("Save a mobile number on this lead before calling.")
    return normalize_phone(lead.get("mobile_no"))


@frappe.whitelist(methods=["POST"])
def call_target(lead_id):
    _require_enabled()
    lead = _lead(lead_id)
    return {"lead_id": lead.name, "phone_number": _lead_number(lead)}


@frappe.whitelist(methods=["POST"])
def click_to_call(lead_id, request_id):
    user, settings = _require_enabled()
    lead = _lead(lead_id)
    if not re.fullmatch(r"[a-f0-9]{32}", str(request_id or "")):
        raise frappe.ValidationError("Invalid call request identifier.")
    agent = user.get("custom_convox_agent_id")
    prefix = user.get("custom_convox_dial_prefix") or settings.get("custom_convox_default_dial_prefix")
    token_ready = _secret(settings, "custom_convox_token_key" if settings.get("custom_convox_auto_token_enabled") else "custom_convox_access_token")
    if not agent or not prefix or not token_ready:
        raise frappe.ValidationError("Ask your administrator to configure your agent ID, dial prefix and ConVox access token.")
    number = _lead_number(lead)
    url = _url(settings.get("custom_convox_api_url"), "/ConVoxCCS/rest/api")
    # Lock by agent, deduplicate by UI request ID; reserve before contacting the PBX.
    cache = frappe.cache
    agent_key = "convox-call:" + hashlib.sha256(str(agent).encode()).hexdigest()
    request_key = agent_key + ":" + request_id
    with cache.lock(agent_key + ":lock", timeout=45, blocking_timeout=1):
        previous = cache.get_value(request_key)
        if previous:
            return previous
        if cache.get_value(agent_key):
            return {"success": False, "status": "BUSY", "message": "A call was requested recently. Check the phone before trying again."}
        try:
            token = _access_token(settings)
        except frappe.ValidationError as error:
            return {"success": False, "status": "TOKEN_ERROR", "message": str(error)}
        refno = "LIFE" + secrets.token_hex(8).upper()
        pending = {"success": False, "status": "UNKNOWN", "refno": refno,
                   "message": "Call outcome is unconfirmed. Check the ConVox phone before making another call."}
        cache.set_value(request_key, pending, expires_in_sec=86400)
        cache.set_value(agent_key, True, expires_in_sec=30)
        try:
            response = requests.post(url, json={"action": "CALL", "userid": agent,
                "phone_number": number, "dial_prefix": str(prefix), "refno": refno},
                headers={"Content-Type": "application/json", "Access-Token": token},
                timeout=(5, 15), allow_redirects=False)
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError):
            return pending  # Never automatically retry a call or expose upstream exceptions/tokens.
        status = str(result.get("STATUS", "UNKNOWN")).strip() if isinstance(result, dict) else "UNKNOWN"
        answer = {"success": status == "CL000", "status": status, "refno": refno,
                  "message": STATUS_MESSAGES.get(status, "ConVox could not confirm the call. Check the phone or contact your administrator.")}
        cache.set_value(request_key, answer, expires_in_sec=86400)
        return answer


@frappe.whitelist(methods=["POST"])
def poll(after=None):
    user, settings = _require_enabled()
    agent = user.get("custom_convox_agent_id")
    if not agent or not settings.get("custom_convox_callbacks_enabled") or not frappe.db.exists("DocType", "ConVox Call Event"):
        return {"events": [], "cursor": str(now_datetime())}
    now = now_datetime()
    try:
        stamp, _, name = str(after or now).partition("|")
        since = datetime.fromisoformat(stamp)
        if since.tzinfo or (name and not re.fullmatch(r"[A-Za-z0-9_-]{1,140}", name)):
            raise ValueError()
    except ValueError:
        raise frappe.ValidationError("Invalid callback cursor.")
    since = max(now - timedelta(hours=24), min(since, now))
    rows = frappe.db.sql(
        "SELECT " + ", ".join(EVENT_FIELDS) + " FROM `tabConVox Call Event` "
        "WHERE agent_id = %(agent)s AND received_on <= %(now)s "
        "AND (received_on > %(since)s OR (received_on = %(since)s AND name > %(name)s)) "
        "ORDER BY received_on ASC, name ASC LIMIT 100",
        {"agent": agent, "now": now, "since": since, "name": name}, as_dict=True)
    # Stable composite cursor handles batches sharing a timestamp. A short overlap
    # on the final page catches transactions that committed during this request.
    cursor = (str(rows[-1].received_on) + "|" + rows[-1].name) if len(rows) == 100 else str(now - timedelta(seconds=2))
    return {"events": rows, "cursor": cursor}


@frappe.whitelist(methods=["POST"])
def history(lead_id=None, mobile_number=None, call_reference=None):
    user, settings = _require_enabled()
    agent = user.get("custom_convox_agent_id")
    if not agent or not frappe.db.exists("DocType", "ConVox Call Event"):
        return {"events": []}
    filters = {"agent_id": agent}
    if lead_id:
        _lead(lead_id)
        filters["lead_id"] = lead_id
    if mobile_number:
        filters["mobile_number"] = normalize_phone(mobile_number)
    if call_reference:
        filters["call_reference"] = str(call_reference)[:140]
    return {"events": frappe.get_all("ConVox Call Event", filters=filters,
        fields=EVENT_FIELDS, order_by="received_on desc", limit_page_length=50)}


def receive_callback(event_type, data):
    """Called by existing POST-only callback routes; authenticate before writes."""
    settings = frappe.get_doc("System Settings")
    def fail(code, message):
        frappe.response["http_status_code"] = code
        return {"status": "error", "message": message}
    if not settings.get("custom_convox_callbacks_enabled"):
        return fail(503, "ConVox callbacks are disabled.")
    headers = frappe.request.headers
    # Standard Frappe OAuth validates Bearer tokens before this handler executes.
    # An optional shared-header mode remains compatible with earlier ConVox setups.
    oauth_user = settings.get("custom_convox_callback_user")
    oauth_ok = bool(oauth_user and frappe.session.user == oauth_user and
                    str(headers.get("Authorization", "")).lower().startswith("bearer "))
    expected = _secret(settings, "custom_convox_callback_token")
    supplied = headers.get("X-ConVox-Token", "")
    shared_ok = bool(expected and supplied and hmac.compare_digest(expected.encode(), supplied.encode()))
    if not (oauth_ok or shared_ok):
        return fail(401, "Invalid or expired access token.")
    is_popup = event_type == "Call Popup"
    required = (["agent_id", "call_hit_reference_number", "mobile_number", "process_name", "lead_id", "entry_date", "call_type", "station"]
                if is_popup else ["CALL_REFERENCE_ID", "MOBILE_NO", "PROCESS_NAME", "CALL_DATE", "USER_ID", "CALL_STATUS"])
    if any(not str(data.get(key) or "").strip() for key in required):
        return fail(400, "Missing required callback fields: " + ", ".join(required))
    if any(len(str(value)) > 10000 for value in data.values()) or len(json.dumps(data, default=str)) > 64000:
        return fail(400, "Callback payload is too large.")
    agent = str(data["agent_id" if is_popup else "USER_ID"])
    if frappe.db.count("User", {"enabled": 1, "custom_convox_enabled": 1, "custom_convox_agent_id": agent}) != 1:
        return fail(400, "Agent is not mapped to an enabled portal user.")
    reference = str(data["call_hit_reference_number" if is_popup else "CALL_REFERENCE_ID"])
    if len(reference) > 140:
        return fail(400, "Invalid call reference.")
    try:
        mobile = normalize_phone(data["mobile_number" if is_popup else "MOBILE_NO"])
        call_date = datetime.fromisoformat(str(data["entry_date" if is_popup else "CALL_DATE"]))
        if call_date.tzinfo:
            raise ValueError()
        durations = {key: int(data.get(key) or 0) for key in ("CALL_DURATION", "QUEUE_DURATION", "RING_DURATION")}
        if any(value < 0 for value in durations.values()):
            raise ValueError()
    except (ValueError, TypeError, frappe.ValidationError):
        return fail(400, "Invalid phone number, timestamp or duration.")
    if not frappe.db.exists("DocType", "ConVox Call Event"):
        return fail(503, "ConVox event storage is not installed.")
    name = hashlib.sha256((event_type + ":" + reference).encode()).hexdigest()
    with frappe.cache.lock("convox-event:" + name, timeout=10, blocking_timeout=2):
        exists = frappe.db.exists("ConVox Call Event", name)
        event = frappe.get_doc("ConVox Call Event", name) if exists else frappe.new_doc("ConVox Call Event")
        payload = json.dumps(data, sort_keys=True, default=str)
        if exists and event.get("payload_json") == payload:
            return {"status": "success", "message": "Call event already received.", "event_id": name}
        event.name = name
        event.event_type, event.call_reference, event.agent_id = event_type, reference, agent
        event.mobile_number, event.call_datetime = mobile, call_date
        mapping = {"process_name": "process_name" if is_popup else "PROCESS_NAME",
            "lead_id": "lead_id" if is_popup else "LEAD_ID", "call_type": "call_type",
            "station": "station" if is_popup else "STATION", "disposition": "DISPOSITION",
            "disposition_2": "disposition2", "disposition_3": "disposition3", "call_status": "CALL_STATUS",
            "call_mode": "CALL_MODE", "completed_by": "COMPLETED_BY", "queue_name": "QUEUE_NAME",
            "list_id": "LIST_ID", "did": "DID", "remarks": "remarks", "recording_file_name": "RECORDING_FILE_NAME"}
        for field, key in mapping.items():
            if key in data:
                setattr(event, field, str(data[key] or "")[:10000 if field in {"remarks", "recording_file_name"} else 140])
        for key, value in durations.items():
            setattr(event, key.lower(), value)
        followup = data.get("FOLLOWUP_TIME")
        if followup:
            try:
                event.followup_time = datetime.fromisoformat(str(followup))
            except ValueError:
                return fail(400, "Invalid follow-up timestamp.")
        event.received_on, event.payload_json = now_datetime(), payload
        event.save(ignore_permissions=True) if exists else event.insert(ignore_permissions=True, set_name=name)
    return {"status": "success", "message": "Call event received successfully.", "event_id": name}
