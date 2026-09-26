"""api for expendtiure

Original API: expenditure_api
Source modified: 2026-06-03 23:16:14.859434
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
    # No imports allowed at the top
    action = frappe.form_dict.get("action")

    # ── GET BRANCHES ──────────────────────────────────────────
    if action == "get_branches":
        frappe.response["data"] = frappe.get_all(
            "Branch",
            fields=["name"],
            order_by="name asc",
            limit=200,
            ignore_permissions=True
        )

    # ── GET EMPLOYEES ─────────────────────────────────────────
    elif action == "get_employees":
        branch = frappe.form_dict.get("branch", "")
        filters = {"status": "Active"}
        if branch:
            filters["branch"] = branch

        frappe.response["data"] = frappe.get_all(
            "Employee",
            fields=["name", "employee_name", "designation"],
            filters=filters,
            order_by="employee_name asc",
            limit=200,
            ignore_permissions=True
        )

    # ── GET PAYMENTS ──────────────────────────────────────────
    elif action == "get_payments":
        from_date = frappe.form_dict.get("from_date", "")
        to_date   = frappe.form_dict.get("to_date", "")
        branch    = frappe.form_dict.get("branch", "")

        filters = {
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]]
        }
        if branch:
            filters["branch"] = branch

        frappe.response["data"] = frappe.get_all(
            "Payment Entry",
            fields=["branch", "mode_of_payment", "paid_amount"],
            filters=filters,
            limit=5000,
            ignore_permissions=True
        )

    # ── GET JOURNAL ENTRIES ───────────────────────────────────
    elif action == "get_je_history":
        from_date = frappe.form_dict.get("from_date", "")
        to_date   = frappe.form_dict.get("to_date", "")
        branch    = frappe.form_dict.get("branch", "")

        je_filters = [
            ["docstatus", "=", 1],
            ["posting_date", ">=", from_date],
            ["posting_date", "<=", to_date],
            ["user_remark", "like", "Expenditure%"]
        ]
        if branch:
            je_filters.append(["user_remark", "like", "%Branch:" + branch + "%"])

        jes = frappe.get_all(
            "Journal Entry",
            fields=["name", "posting_date", "user_remark"],
            filters=je_filters,
            order_by="posting_date desc",
            limit=500,
            ignore_permissions=True
        )

        je_names = [j["name"] for j in jes]
        lines = []

        if je_names:
            lines = frappe.get_all(
                "Journal Entry Account",
                fields=["parent", "account", "debit_in_account_currency", "user_remark"],
                filters=[
                    ["parent", "in", je_names],
                    ["debit_in_account_currency", ">", 0]
                ],
                limit=5000,
                ignore_permissions=True
            )

        frappe.response["data"] = {"jes": jes, "lines": lines}

    # ── VALIDATE ACCOUNTS ─────────────────────────────────────
    elif action == "validate_accounts":
        names = frappe.parse_json(frappe.form_dict.get("names", "[]"))

        frappe.response["data"] = frappe.get_all(
            "Account",
            fields=["name", "is_group"],
            filters={"name": ["in", names]},
            limit=50,
            ignore_permissions=True
        )

    # ── CREATE & SUBMIT JOURNAL ENTRY (🔥 DUPLICATE SAFE) ─────
    elif action == "create_je":

        payload = frappe.parse_json(frappe.form_dict.get("payload", "{}"))

        posting_date = payload.get("posting_date")
        user_remark  = payload.get("user_remark")
        accounts     = payload.get("accounts")

        if not posting_date or not accounts:
            frappe.throw("Missing required data")

        # 🔥 UNIQUE KEY (idempotency)
        unique_key = frappe.generate_hash(user_remark + str(posting_date), 16)

        # 🔍 CHECK IF ALREADY EXISTS
        existing = frappe.db.get_value(
            "Journal Entry",
            {"custom_unique_key": unique_key},
            "name"
        )

        if existing:
            frappe.response["data"] = {
                "name": existing,
                "status": "duplicate_prevented"
            }
            raise SystemExit   # ✅ REQUIRED

        # 🧾 CREATE JE
        doc = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "multi_currency": 1,
            "posting_date": posting_date,
            "user_remark": user_remark,
            "custom_unique_key": unique_key,
            "accounts": accounts
        })

        try:
            doc.insert(ignore_permissions=True)
            doc.submit()

        except frappe.DuplicateEntryError:
            # 🔁 HANDLE RACE CONDITION
            existing = frappe.db.get_value(
                "Journal Entry",
                {"custom_unique_key": unique_key},
                "name"
            )

            frappe.response["data"] = {
                "name": existing,
                "status": "race_handled"
            }
            raise SystemExit   # ✅ REQUIRED

        frappe.response["data"] = {
            "name": doc.name,
            "status": "created"
        }

    # ── DEFAULT ───────────────────────────────────────────────
    else:
        frappe.response["data"] = {"error": "Unknown action: " + str(action)}
