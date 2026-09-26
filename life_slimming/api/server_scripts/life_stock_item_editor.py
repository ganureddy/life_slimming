"""life_stock_item_editor

Original API: life_stock_item_editor
Source modified: 2026-09-10 17:49:34.764773
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

    action = (frappe.form_dict.get("action") or "get").strip()
    item_code = (frappe.form_dict.get("item_code") or "").strip()
    current_user = frappe.session.user

    if current_user == "Guest":
        frappe.throw("Please log in.")

    if not item_code:
        frappe.throw("Item Code is required.")

    if not frappe.db.exists("Item", item_code):
        frappe.throw("Item " + item_code + " was not found.")

    can_edit = False

    if current_user == "Administrator":
        can_edit = True

    if frappe.db.exists(
        "Has Role",
        {
            "parent": current_user,
            "parenttype": "User",
            "role": "System Manager"
        }
    ):
        can_edit = True

    if frappe.db.exists(
        "Has Role",
        {
            "parent": current_user,
            "parenttype": "User",
            "role": "Stock Manager"
        }
    ):
        can_edit = True

    if action == "get":
        item = frappe.get_doc(
            "Item",
            item_code
        )

        frappe.response["message"] = {
            "success": True,
            "can_edit": can_edit,
            "item": {
                "item_code": item.name,
                "item_name": item.item_name or "",
                "item_group": item.item_group or "",
                "custom_sub_group": item.custom_sub_group or "",
                "stock_uom": item.stock_uom or "",
                "standard_rate": item.standard_rate or 0,
                "valuation_rate": item.valuation_rate or 0,
                "disabled": item.disabled or 0,
                "description": item.description or ""
            }
        }

    elif action == "save":
        if not can_edit:
            frappe.throw(
                "Only Stock Manager or System Manager can edit Item details."
            )

        item_group = (
            frappe.form_dict.get("item_group") or ""
        ).strip()

        custom_sub_group = (
            frappe.form_dict.get("custom_sub_group") or ""
        ).strip()

        stock_uom = (
            frappe.form_dict.get("stock_uom") or ""
        ).strip()

        standard_rate_text = (
            frappe.form_dict.get("standard_rate") or "0"
        )

        valuation_rate_text = (
            frappe.form_dict.get("valuation_rate") or "0"
        )

        enabled_text = str(
            frappe.form_dict.get("enabled") or "0"
        ).strip()

        disabled_value = 0

        if enabled_text != "1":
            disabled_value = 1

        if not item_group:
            frappe.throw("Item Category is required.")

        if not stock_uom:
            frappe.throw("Stock UOM is required.")

        if not frappe.db.exists(
            "Item Group",
            item_group
        ):
            frappe.throw(
                "Item Category "
                + item_group
                + " does not exist."
            )

        if not frappe.db.exists(
            "UOM",
            stock_uom
        ):
            frappe.throw(
                "UOM "
                + stock_uom
                + " does not exist."
            )

        try:
            standard_rate = float(
                standard_rate_text
            )
        except Exception:
            frappe.throw(
                "Selling Rate must be a valid number."
            )

        try:
            valuation_rate = float(
                valuation_rate_text
            )
        except Exception:
            frappe.throw(
                "Valuation Rate must be a valid number."
            )

        if standard_rate < 0:
            frappe.throw(
                "Selling Rate cannot be negative."
            )

        if valuation_rate < 0:
            frappe.throw(
                "Valuation Rate cannot be negative."
            )

        frappe.db.set_value(
            "Item",
            item_code,
            {
                "item_group": item_group,
                "custom_sub_group": custom_sub_group,
                "stock_uom": stock_uom,
                "standard_rate": standard_rate,
                "valuation_rate": valuation_rate,
                "disabled": disabled_value
            }
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "success": True,
            "message": "Item updated successfully.",
            "item_code": item_code,
            "item_group": item_group,
            "custom_sub_group": custom_sub_group,
            "stock_uom": stock_uom,
            "standard_rate": standard_rate,
            "valuation_rate": valuation_rate,
            "disabled": disabled_value
        }

    else:
        frappe.throw("Invalid action.")
