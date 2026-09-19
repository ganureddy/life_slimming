"""Machinery Request Source Warehouse

Original API: life_get_source_warehouses
Source modified: 2026-08-09 12:45:40.984936
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
    # API Method: life_get_source_warehouses
    # Allow Guest: No
    # Disabled: No

    if frappe.session.user == "Guest":
        frappe.throw("Login is required.")

    # Return only Link-selector information. No quantities, valuation, bins,
    # transactions or other stock data are exposed by this endpoint.
    warehouses = frappe.db.get_all(
        "Warehouse",
        filters={
            "is_group": 0,
            "disabled": 0
        },
        fields=[
            "name",
            "warehouse_name"
        ],
        order_by="warehouse_name asc",
        limit_page_length=1000
    )

    frappe.response["message"] = warehouses
