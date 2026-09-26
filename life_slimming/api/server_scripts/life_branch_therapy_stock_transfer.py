"""life_branch_therapy_stock_transfer

Original API: life_branch_therapy_stock_transfer
Source modified: 2026-09-11 00:00:02.207242
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

    action = (frappe.form_dict.get("action") or "").strip()
    current_user = frappe.session.user

    if current_user == "Guest":
        frappe.throw("Please log in.")

    branch_map = {
        "Banjara Hills": {
            "source": "Banjarahills Main Store - LSACPL",
            "target": "Banjarahills Sub Store - LSACPL"
        },
        "Banjarahills": {
            "source": "Banjarahills Main Store - LSACPL",
            "target": "Banjarahills Sub Store - LSACPL"
        },
        "Chandanagar": {
            "source": "Chandanagar Main Store - LSACPL",
            "target": "Chandanagar Sub Store - LSACPL"
        },
        "Chandhanagar": {
            "source": "Chandanagar Main Store - LSACPL",
            "target": "Chandanagar Sub Store - LSACPL"
        },
        "Dilsukhnagar": {
            "source": "Dilsukhnagar Main Store - LSACPL",
            "target": "Dilsukhnagar Sub Store - LSACPL"
        },
        "Gachibowli": {
            "source": "Gachibowli Main Store - LSACPL",
            "target": "Gachibowli Sub Store - LSACPL"
        },
        "Himayathnagar": {
            "source": "Himayathnagar Main Store - LSACPL",
            "target": "Himayathnagar Sub Store - LSACPL"
        },
        "Himayatnagar": {
            "source": "Himayathnagar Main Store - LSACPL",
            "target": "Himayathnagar Sub Store - LSACPL"
        },
        "Kukatpally": {
            "source": "Kukatpally Main Store - LSACPL",
            "target": "Kukatpally Sub Store - LSACPL"
        },
        "Madhapur": {
            "source": "Madhapur Main Store - LSACPL",
            "target": "Madhapur Sub Store - LSACPL"
        },
        "Nellore": {
            "source": "Nellore Main Store - LSACPL",
            "target": "Nellore Sub Store - LSACPL"
        },
        "SR Nagar": {
            "source": "SR Nagar Main Store - LSACPL",
            "target": "SR Nagar Sub Store - LSACPL"
        },
        "Vijayawada": {
            "source": "Vijayawada Main Store - LSACPL",
            "target": "Vijayawada Sub Store - LSACPL"
        },
        "Vizag": {
            "source": "Vizag Main Store - LSACPL",
            "target": "Vizag Sub Store - LSACPL"
        }
    }

    is_manager = False

    if current_user == "Administrator":
        is_manager = True

    if frappe.db.exists(
        "Has Role",
        {
            "parent": current_user,
            "parenttype": "User",
            "role": "System Manager"
        }
    ):
        is_manager = True

    if frappe.db.exists(
        "Has Role",
        {
            "parent": current_user,
            "parenttype": "User",
            "role": "Stock Manager"
        }
    ):
        is_manager = True


    def get_user_branch():
        if is_manager:
            return ""

        branch = frappe.db.get_value(
            "User Permission",
            {
                "user": current_user,
                "allow": "Branch",
                "applicable_for": ["in", ["", None, "Therapy Session"]]
            },
            "for_value"
        )

        if not branch:
            branch = frappe.db.get_value(
                "User Permission",
                {
                    "user": current_user,
                    "allow": "Branch"
                },
                "for_value"
            )

        return branch or ""


    if action == "session":
        session_id = (
            frappe.form_dict.get("therapy_session") or ""
        ).strip()

        if not session_id:
            frappe.throw("Therapy Session ID is required.")

        session = frappe.db.get_value(
            "Therapy Session",
            session_id,
            [
                "name",
                "patient",
                "branch",
                "docstatus"
            ],
            as_dict=True
        )

        if not session:
            frappe.throw(
                "Therapy Session "
                + session_id
                + " was not found."
            )

        if int(session.docstatus or 0) != 1:
            frappe.throw(
                "Therapy Session must be submitted before transferring stock."
            )

        branch = (session.branch or "").strip()

        if branch == "Testing Branch":
            frappe.throw(
                "Testing Branch is not allowed."
            )

        if branch not in branch_map:
            frappe.throw(
                "Main Store and Sub Store mapping is missing for branch "
                + branch
                + "."
            )

        user_branch = get_user_branch()

        if (
            not is_manager
            and user_branch
            and user_branch != branch
        ):
            frappe.throw(
                "You can transfer stock only for your permitted branch "
                + user_branch
                + "."
            )

        patient_name = ""

        if session.patient:
            patient_name = frappe.db.get_value(
                "Patient",
                session.patient,
                "patient_name"
            ) or session.patient

        items = frappe.get_all(
            "Item",
            filters={
                "disabled": 0,
                "is_stock_item": 1
            },
            fields=[
                "name as item_code",
                "item_name",
                "stock_uom"
            ],
            order_by="item_name asc",
            limit_page_length=2000
        )

        frappe.response["message"] = {
            "success": True,
            "therapy_session": session.name,
            "client_id": session.patient or "",
            "client_name": patient_name,
            "branch": branch,
            "source_warehouse": branch_map[branch]["source"],
            "target_warehouse": branch_map[branch]["target"],
            "items": items
        }


    elif action == "availability":
        item_code = (
            frappe.form_dict.get("item_code") or ""
        ).strip()

        source_warehouse = (
            frappe.form_dict.get("source_warehouse") or ""
        ).strip()

        available_qty = frappe.db.get_value(
            "Bin",
            {
                "item_code": item_code,
                "warehouse": source_warehouse
            },
            "actual_qty"
        ) or 0

        frappe.response["message"] = {
            "success": True,
            "available_qty": available_qty
        }


    elif action == "transfer":
        session_id = (
            frappe.form_dict.get("therapy_session") or ""
        ).strip()

        item_codes_text = (
            frappe.form_dict.get("item_codes") or ""
        )

        quantities_text = (
            frappe.form_dict.get("quantities") or ""
        )

        if not session_id:
            frappe.throw("Therapy Session ID is required.")

        session = frappe.db.get_value(
            "Therapy Session",
            session_id,
            [
                "name",
                "patient",
                "branch",
                "docstatus"
            ],
            as_dict=True
        )

        if not session:
            frappe.throw(
                "Therapy Session was not found."
            )

        if int(session.docstatus or 0) != 1:
            frappe.throw(
                "Therapy Session must be submitted."
            )

        branch = (session.branch or "").strip()

        if branch not in branch_map:
            frappe.throw(
                "Warehouse mapping is missing for "
                + branch
                + "."
            )

        user_branch = get_user_branch()

        if (
            not is_manager
            and user_branch
            and user_branch != branch
        ):
            frappe.throw(
                "You cannot transfer stock for another branch."
            )

        client_name = ""

        if session.patient:
            client_name = frappe.db.get_value(
                "Patient",
                session.patient,
                "patient_name"
            ) or session.patient

        if not client_name:
            frappe.throw(
                "Client Name is missing in the Therapy Session."
            )

        source_warehouse = branch_map[branch]["source"]
        target_warehouse = branch_map[branch]["target"]

        item_codes = item_codes_text.split("\n")
        quantities = quantities_text.split("\n")

        if len(item_codes) != len(quantities):
            frappe.throw(
                "Item and quantity rows do not match."
            )

        stock_items = []
        row_number = 0

        for item_code in item_codes:
            item_code = (item_code or "").strip()

            quantity_text = ""

            if row_number < len(quantities):
                quantity_text = (
                    quantities[row_number] or ""
                ).strip()

            row_number = row_number + 1

            if not item_code:
                continue

            try:
                quantity = float(quantity_text)
            except Exception:
                frappe.throw(
                    "Transfer quantity must be a valid number for "
                    + item_code
                    + "."
                )

            if quantity <= 0:
                frappe.throw(
                    "Transfer quantity must be greater than zero for "
                    + item_code
                    + "."
                )

            item = frappe.db.get_value(
                "Item",
                item_code,
                [
                    "name",
                    "item_name",
                    "stock_uom",
                    "disabled",
                    "is_stock_item"
                ],
                as_dict=True
            )

            if not item:
                frappe.throw(
                    "Item "
                    + item_code
                    + " was not found."
                )

            if int(item.disabled or 0) == 1:
                frappe.throw(
                    "Item "
                    + item_code
                    + " is disabled."
                )

            if int(item.is_stock_item or 0) != 1:
                frappe.throw(
                    item_code
                    + " is not a stock item."
                )

            available_qty = frappe.db.get_value(
                "Bin",
                {
                    "item_code": item_code,
                    "warehouse": source_warehouse
                },
                "actual_qty"
            ) or 0

            if float(available_qty) < quantity:
                frappe.throw(
                    "Insufficient stock for "
                    + item_code
                    + ". Available: "
                    + str(available_qty)
                    + ", Requested: "
                    + str(quantity)
                )

            stock_items.append({
                "item_code": item_code,
                "item_name": item.item_name or item_code,
                "qty": quantity,
                "uom": item.stock_uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": 1,
                "s_warehouse": source_warehouse,
                "t_warehouse": target_warehouse
            })

        if not stock_items:
            frappe.throw(
                "Add at least one item."
            )

        remarks = (
            "LIFE_BRANCH_THERAPY_TRANSFER"
            + " | Therapy Session: "
            + session_id
            + " | Client: "
            + client_name
            + " | Client ID: "
            + str(session.patient or "")
            + " | Branch: "
            + branch
        )

        stock_entry = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Transfer",
            "purpose": "Material Transfer",
            "from_warehouse": source_warehouse,
            "to_warehouse": target_warehouse,
            "remarks": remarks,
            "items": stock_items
        })

        stock_entry.insert(
            ignore_permissions=True
        )

        stock_entry.submit()

        frappe.db.commit()

        frappe.response["message"] = {
            "success": True,
            "stock_entry": stock_entry.name,
            "therapy_session": session_id,
            "client_name": client_name,
            "branch": branch,
            "source_warehouse": source_warehouse,
            "target_warehouse": target_warehouse,
            "item_count": len(stock_items)
        }


    elif action == "history":
        filters = {
            "docstatus": 1,
            "purpose": "Material Transfer",
            "remarks": [
                "like",
                "%LIFE_BRANCH_THERAPY_TRANSFER%"
            ]
        }

        if not is_manager:
            filters["owner"] = current_user

        entries = frappe.get_all(
            "Stock Entry",
            filters=filters,
            fields=[
                "name",
                "posting_date",
                "posting_time",
                "from_warehouse",
                "to_warehouse",
                "remarks",
                "owner",
                "modified"
            ],
            order_by="creation desc",
            limit_page_length=200
        )

        frappe.response["message"] = {
            "success": True,
            "entries": entries
        }

    else:
        frappe.throw("Invalid action.")
