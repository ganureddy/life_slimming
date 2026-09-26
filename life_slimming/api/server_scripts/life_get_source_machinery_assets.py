"""Machonery Request Assets

Original API: life_get_source_machinery_assets
Source modified: 2026-08-09 12:46:14.693644
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
    # API Method: life_get_source_machinery_assets
    # Allow Guest: No
    # Disabled: No

    if frappe.session.user == "Guest":
        frappe.throw("Login is required.")

    # Selector-only information for active Machinery Assets. Financial,
    # depreciation, purchase and valuation fields are intentionally excluded.
    assets = frappe.db.get_all(
        "Asset",
        filters={
            "docstatus": ["!=", 2],
            "asset_category": "Machinery"
        },
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
        order_by="asset_name asc",
        limit_page_length=5000
    )

    frappe.response["message"] = assets
