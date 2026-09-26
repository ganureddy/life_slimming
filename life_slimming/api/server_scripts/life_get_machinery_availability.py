"""Machinery Transfer Availabillity

Original API: life_get_machinery_availability
Source modified: 2026-08-11 18:20:38.976399
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
    # ERPNext Server Script
    # Script Type: API
    # API Method: life_get_machinery_availability
    # Allow Guest: No
    #
    # Purpose:
    # Give authenticated branch users a safe cross-branch machinery directory for
    # raising Machinery Requests. It returns only non-financial inventory identity,
    # category, status and current location. It does not grant Asset document access.

    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Please log in to view machinery availability.", frappe.PermissionError)

    rows = frappe.get_all(
        "Asset",
        filters=[
            ["Asset", "docstatus", "!=", 2],
            ["Asset", "asset_category", "=", "Machinery"],
            ["Asset", "location", "not like", "%Testing%"],
            ["Asset", "status", "not in", ["Sold", "Scrapped", "Cancelled"]]
        ],
        fields=[
            "name",
            "asset_name",
            "item_code",
            "item_name",
            "asset_category",
            "custom_machinery_assets_category",
            "location",
            "status"
        ],
        order_by="location asc, asset_name asc",
        limit_page_length=5000
    )

    frappe.response["message"] = rows
