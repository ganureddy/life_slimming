"""Read-only dashboard connection, authenticated with each viewer's ERP session.

No connector credentials or shared service account. Remote cookies stay in Redis,
bound to the current local session, and expire after one hour of inactivity.
"""

import hashlib
import json
from datetime import date

import frappe
import requests
from frappe.rate_limiter import rate_limit

ORIGIN = "https://portal.lifescc.com"


def _key():
    if frappe.session.user == "Guest":
        frappe.throw("Sign in to LIFE Portal first.", frappe.AuthenticationError)
    identity = f"{frappe.session.user}:{frappe.session.sid}"
    return "life-remote-erp:" + hashlib.sha256(identity.encode()).hexdigest()


def _save(state):
    frappe.cache.set_value(_key(), state, expires_in_sec=3600)


def _request(method, *, state=None, args=None, login=False):
    with requests.Session() as client:
        if state:
            client.cookies.update(state.get("cookies", {}))
        try:
            response = client.request(
                "POST" if login else "GET",
                f"{ORIGIN}/api/method/{method}",
                data=args if login else None,
                params=None if login else args,
                timeout=(8, 60), allow_redirects=False,
                headers={"Accept": "application/json"},
            )
            body = response.json()
        except (requests.RequestException, ValueError):
            return {"error": "ERP Portal could not be reached. Please retry."}, {}
        if response.status_code == 429:
            return {"error": "Too many attempts. Wait before retrying."}, {}
        if response.status_code in (401, 403):
            return {"error": "ERP sign-in expired, credentials were rejected, or access was denied.",
                    "authentication_required": True}, {}
        if not response.ok or not isinstance(body, dict) or body.get("exc_type") or body.get("exc"):
            return {"error": "ERP Portal could not complete this request. Check your access and retry."}, {}
        return body, requests.utils.dict_from_cookiejar(client.cookies)


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=60)
def connect(usr=None, pwd=None, otp=None):
    key = _key()
    previous = frappe.cache.get_value(key) or {}
    if otp:
        if not previous.get("tmp_id"):
            return {"error": "Verification expired. Enter your password again."}
        args = {"otp": otp, "tmp_id": previous["tmp_id"]}
        state = previous
    else:
        if not usr or not pwd:
            return {"error": "Enter your ERP email and password."}
        frappe.cache.delete_value(key)
        args, state = {"usr": usr, "pwd": pwd}, {}
    body, cookies = _request("login", state=state, args=args, login=True)
    if body.get("error"):
        return {"error": body["error"]}
    if body.get("tmp_id") and body.get("verification"):
        verification = body["verification"]
        if verification.get("token_delivery") is False:
            return {"error": "ERP could not deliver the verification code. Try signing in again."}
        _save({"cookies": cookies, "tmp_id": body["tmp_id"]})
        return {"verification": True, "method": verification.get("method", "OTP")}
    if body.get("message") not in ("Logged In", "No App"):
        return {"error": "ERP sign-in needs attention. Check your account on portal.lifescc.com."}
    state = {"cookies": cookies}
    identity, _ = _request("frappe.auth.get_logged_user", state=state)
    user = identity.get("message")
    if not isinstance(user, str) or user == "Guest":
        return {"error": "ERP did not establish an authenticated session."}
    state["user"] = user
    _save(state)
    return {"connected": True, "user": user}


@frappe.whitelist(methods=["POST"])
def disconnect():
    frappe.cache.delete_value(_key())
    return {"connected": False}


def _branches(state):
    body, _ = _request("frappe.client.get_list", state=state, args={
        "doctype": "Branch", "fields": json.dumps(["name"]),
        "limit_page_length": 0, "order_by": "name asc",
    })
    if body.get("error"):
        return body
    rows = body.get("message")
    if not isinstance(rows, list):
        return {"error": "ERP returned an unexpected branch list."}
    return {"branches": [r["name"] for r in rows
                          if r.get("name") not in (None, "Head Office", "Testing Branch")]}


@frappe.whitelist(methods=["POST"])
def dashboard(branch=None, from_date=None, to_date=None):
    state = frappe.cache.get_value(_key()) or {}
    if not state.get("user"):
        return {"authentication_required": True}
    branches = _branches(state)
    if branches.get("error"):
        return branches
    if not branch:
        return {"connected": True, "user": state["user"], **branches}
    if branch not in branches["branches"]:
        frappe.throw("This branch is not available to your ERP account.", frappe.PermissionError)
    try:
        start, end = date.fromisoformat(from_date), date.fromisoformat(to_date)
        if start > end:
            raise ValueError
    except (TypeError, ValueError):
        frappe.throw("Choose a valid date range.")
    body, _ = _request("branch_command_center", state=state, args={
        "branch": branch, "from_date": start.isoformat(), "to_date": end.isoformat(),
    })
    if body.get("error"):
        return body
    data = body.get("message")
    if not isinstance(data, dict) or data.get("branch") != branch:
        return {"error": "ERP returned an unexpected dashboard response. No figures were assumed."}
    _save(state)
    return {"connected": True, "user": state["user"], "data": data, **branches}
