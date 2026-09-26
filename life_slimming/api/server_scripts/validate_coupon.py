"""validate_coupon

Original API: validate_coupon
Source modified: 2026-08-23 13:36:17.203108
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
    args = frappe.form_dict
    code = (args.get("coupon_code") or "").strip()
    mobile = (args.get("mobile") or "").strip()

    def last10(v):
        digits = ""
        for ch in str(v or ""):
            if ch.isdigit():
                digits += ch
        if len(digits) > 10:
            digits = digits[-10:]
        return digits

    def fail(msg):
        frappe.response["message"] = {"valid": 0, "error": msg}

    coupon = None

    if code:
        if frappe.db.exists("Web Coupon", code):
            coupon = frappe.get_doc("Web Coupon", code)
    elif mobile:
        m10 = last10(mobile)
        actives = frappe.get_all("Web Coupon",
            filters={"status": "Active"},
            fields=["name", "client_mobile"], order_by="creation desc", limit_page_length=0)
        for a in actives:
            if last10(a.get("client_mobile")) == m10:
                coupon = frappe.get_doc("Web Coupon", a["name"])
                break

    if not coupon:
        if code:
            fail("No coupon found for this code.")
        else:
            fail("No active coupon found for this number.")
    else:
        today = frappe.utils.getdate(frappe.utils.today())
        problem = None
        if coupon.status == "Used":
            problem = "This coupon has already been used."
        elif coupon.status == "Expired" or coupon.status == "Cancelled":
            problem = "This coupon is " + str(coupon.status).lower() + "."
        elif coupon.valid_until and frappe.utils.getdate(coupon.valid_until) < today:
            problem = "This coupon expired on " + str(coupon.valid_until) + "."
        elif mobile and coupon.client_mobile and last10(coupon.client_mobile) != last10(mobile):
            problem = "This coupon belongs to a different phone number."

        if problem:
            fail(problem)
        else:
            frappe.response["message"] = {
                "valid": 1,
                "coupon_code": coupon.coupon_code,
                "discount_type": coupon.discount_type,
                "discount_value": float(coupon.discount_value or 0),
                "min_spend": float(coupon.get("min_spend") or 0),
                "client_name": coupon.client_name or "",
                "client_mobile": coupon.client_mobile or "",
                "valid_until": str(coupon.valid_until or ""),
                "max_discount_amount": float(coupon.max_discount_amount or 0)
            }
