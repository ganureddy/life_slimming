"""Machinary Transfer

Original API: get_store_warehouses_for_transfer
Source modified: 2026-06-03 23:16:15.479150
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
    txt = frappe.form_dict.get("txt") or ""
    txt = txt.lower()

    warehouses = frappe.get_all(
        "Warehouse",
        filters={
            "disabled": 0,
            "is_group": 0
        },
        fields=["name"],
        order_by="name asc",
        ignore_permissions=True
    )

    result = []

    for w in warehouses:
        name = w.name or ""
        name_lower = name.lower()

        if (
            "store warehouse" in name_lower
            or "stores warehouse" in name_lower
            or "main stores" in name_lower
        ):
            if txt in name_lower:
                result.append(name)

    frappe.response["message"] = result
