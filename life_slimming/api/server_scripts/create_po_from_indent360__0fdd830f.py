"""Stores 360

Original API: create_po_from_indent360
Source modified: 2026-09-12 11:33:38.394769
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
    # LIFE Stock 360 - Create Draft Purchase Orders

    raw_cart = frappe.form_dict.get("cart") or "[]"
    cart = frappe.parse_json(raw_cart)

    if not isinstance(cart, list) or not cart:
        frappe.throw("No items received.")

    company = frappe.defaults.get_user_default("Company")

    if not company:
        companies = frappe.get_all("Company", pluck="name", limit=1)
        company = companies[0] if companies else None

    if not company:
        frappe.throw("No Company found.")

    by_supplier = {}

    for row in cart:
        item_code = (row.get("item") or "").strip()
        qty = float(row.get("qty") or 0)
        rate = float(row.get("rate") or 0)
        supplier = (row.get("vendor") or "").strip()

        if not item_code or qty <= 0:
            continue

        if not frappe.db.exists("Item", item_code):
            continue

        if not supplier:
            links = frappe.get_all(
                "Item Supplier",
                filters={"parent": item_code},
                fields=["supplier"],
                order_by="idx asc",
                limit=1
            )
            supplier = links[0].supplier if links else ""

        if not supplier:
            continue

        if not frappe.db.exists("Supplier", supplier):
            continue

        if supplier not in by_supplier:
            by_supplier[supplier] = []

        by_supplier[supplier].append({
            "item_code": item_code,
            "qty": qty,
            "rate": rate
        })

    created = []
    errors = []

    for supplier in by_supplier:
        try:
            po = frappe.new_doc("Purchase Order")
            po.company = company
            po.supplier = supplier
            po.transaction_date = frappe.utils.today()
            po.schedule_date = frappe.utils.add_days(frappe.utils.today(), 7)

            for r in by_supplier[supplier]:
                child = po.append("items", {})
                child.item_code = r["item_code"]
                child.qty = r["qty"]
                child.schedule_date = po.schedule_date

                if r["rate"] > 0:
                    child.rate = r["rate"]

            po.insert()
            created.append(po.name)

        except Exception as e:
            errors.append(supplier + ": " + str(e))

    frappe.response["message"] = {
        "created": created,
        "errors": errors
    }
