"""md_create_po_draft

Original API: md_create_po_draft
Source modified: 2026-08-03 12:07:40.779967
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
    # =====================================================================
    #  SERVER SCRIPT (API)  —  md_create_po_draft
    #  Script Type : API   ·   API Method : md_create_po_draft
    #
    #  Called via POST (not GET, since it creates data):
    #    fetch('/api/method/md_create_po_draft', {
    #      method: 'POST',
    #      headers: {'Content-Type':'application/json','X-Frappe-CSRF-Token': frappe.csrf_token},
    #      body: JSON.stringify({items: [
    #        {item_code, qty, rate, supplier, warehouse}, ...
    #      ]})
    #    })
    #
    #  Groups cart items by supplier and creates one DRAFT Purchase Order
    #  per vendor (docstatus stays 0 — nothing is submitted). Returns the
    #  created PO names. Runs with the calling user's own permissions, so
    #  it will fail with a normal permission error if that user can't
    #  create Purchase Orders — that's expected, not a bug.
    #
    #  HOW TO INSTALL: Setup -> Server Script -> New -> API -> API Method:
    #  md_create_po_draft -> paste this file -> Save.
    # =====================================================================

    args = frappe.form_dict or {}
    raw_items = args.get("items")
    if isinstance(raw_items, str):
        items = frappe.parse_json(raw_items)
    else:
        items = raw_items or []

    if not items:
        frappe.response["message"] = {"error": "No items supplied. Expected {items: [...]}"}
    else:
        by_supplier = {}
        for it in items:
            supplier = it.get("supplier")
            if not supplier:
                continue
            group = by_supplier.setdefault(supplier, [])
            group.append(it)

        created = []
        errors = []
        default_warehouse = frappe.db.get_value("Warehouse", {"warehouse_name": ["like", "%Stores%"]}, "name")
        schedule_date = frappe.utils.add_days(frappe.utils.nowdate(), 7)

        for supplier in by_supplier:
            group = by_supplier[supplier]
            po_items = []
            for it in group:
                item_code = it.get("item_code")
                uom = frappe.db.get_value("Item", item_code, "stock_uom") if item_code else None
                po_items.append({
                    "item_code": item_code,
                    "qty": it.get("qty") or 1,
                    "rate": it.get("rate") or 0,
                    "uom": uom,
                    "schedule_date": schedule_date,
                    "warehouse": it.get("warehouse") or default_warehouse
                })
            try:
                doc = frappe.get_doc({
                    "doctype": "Purchase Order",
                    "supplier": supplier,
                    "transaction_date": frappe.utils.nowdate(),
                    "schedule_date": schedule_date,
                    "set_warehouse": default_warehouse,
                    "items": po_items
                })
                doc.insert()
                created.append({"supplier": supplier, "po": doc.name, "item_count": len(po_items)})
            except Exception as e:
                errors.append({"supplier": supplier, "error": str(e)})

        frappe.response["message"] = {"created": created, "errors": errors}
