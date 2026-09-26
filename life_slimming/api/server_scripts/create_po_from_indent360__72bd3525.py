"""create_po_from_indent360

Original API: create_po_from_indent360
Source modified: 2026-08-18 08:53:10.411416
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
    # =============================================================================
    # Server Script
    # Type      : API
    # API Name  : create_po_from_indent360
    # Allow Guest: No
    # =============================================================================

    cart_text = frappe.form_dict.get("cart") or "[]"
    data = json.loads(cart_text)

    if not data:
        frappe.throw("Cart is empty")

    by_vendor = {}

    for row in data:
        vc = row.get("vendor")

        if not vc:
            continue

        if vc not in by_vendor:
            by_vendor[vc] = []

        by_vendor[vc].append(row)

    created = []
    errors = []

    # -------------------------------------------------------------------------
    # DEFAULT COMPANY
    # -------------------------------------------------------------------------

    company = frappe.db.get_single_value(
        "Global Defaults",
        "default_company"
    )

    if not company:
        try:
            company = frappe.defaults.get_global_default("company")
        except:
            company = None

    if not company:
        frappe.throw("Default Company is not configured")

    # -------------------------------------------------------------------------
    # CREATE ONE PURCHASE ORDER PER SUPPLIER
    # -------------------------------------------------------------------------

    for vc in by_vendor:
        try:
            # -------------------------------------------------------------
            # FIND SUPPLIER BY DOCNAME
            # -------------------------------------------------------------
            supplier = frappe.db.get_value(
                "Supplier",
                vc,
                "name"
            )

            # -------------------------------------------------------------
            # FIND SUPPLIER BY SUPPLIER NAME
            # -------------------------------------------------------------
            if not supplier:
                supplier = frappe.db.get_value(
                    "Supplier",
                    {"supplier_name": vc},
                    "name"
                )

            if not supplier:
                errors.append(
                    "Supplier not found: " + str(vc)
                )
                continue

            # -------------------------------------------------------------
            # CREATE PO
            # -------------------------------------------------------------
            po = frappe.new_doc("Purchase Order")
            po.supplier = supplier
            po.company = company
            po.transaction_date = frappe.utils.nowdate()
            po.schedule_date = frappe.utils.nowdate()

            has_line = False

            # -------------------------------------------------------------
            # ADD ITEMS
            # -------------------------------------------------------------
            for row in by_vendor[vc]:
                item_value = row.get("item")

                if not item_value:
                    continue

                # Find by Item Code / Item docname
                item_code = frappe.db.get_value(
                    "Item",
                    item_value,
                    "name"
                )

                # Find by Item Name
                if not item_code:
                    item_code = frappe.db.get_value(
                        "Item",
                        {"item_name": item_value},
                        "name"
                    )

                if not item_code:
                    errors.append(
                        "Item not found: " + str(item_value)
                    )
                    continue

                qty = row.get("qty") or 0

                try:
                    qty = float(qty)
                except:
                    qty = 0

                if qty <= 0:
                    continue

                rate = row.get("rate") or 0

                try:
                    rate = float(rate)
                except:
                    rate = 0

                po.append(
                    "items",
                    {
                        "item_code": item_code,
                        "qty": qty,
                        "rate": rate,
                        "schedule_date": frappe.utils.nowdate()
                    }
                )

                has_line = True

            # -------------------------------------------------------------
            # NO VALID ITEMS
            # -------------------------------------------------------------
            if not has_line:
                errors.append(
                    "No valid items found for supplier: " + str(supplier)
                )
                continue

            # -------------------------------------------------------------
            # INSERT AS DRAFT
            # -------------------------------------------------------------
            po.insert(ignore_permissions=True)

            created.append(po.name)

        except Exception as e:
            errors.append(
                "Supplier " + str(vc) + ": " + str(e)
            )

    # -------------------------------------------------------------------------
    # RESPONSE
    # -------------------------------------------------------------------------

    frappe.response["message"] = {
        "created": created,
        "errors": errors
    }
