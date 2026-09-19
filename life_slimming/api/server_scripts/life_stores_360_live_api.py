"""life_stores_360_live_api

Original API: life_stores_360_live_api
Source modified: 2026-09-16 15:18:45.468857
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
    # V24.2 HOTFIX: item_history uses signed_purchase_amount defined in the same scope; no undefined purchase_amount reference.
    # LIFE STORES 360 - V25.12 SAFE_EXEC PO FIX - NO RESTRICTED PERMISSION API
    # Server Script Type: API
    # API Method: life_stores_360_live_api
    # Allow Guest: No
    #
    # action=item_history + item_code=... returns history for one item.
    # Without action it returns the fast dashboard payload.
    # V24 rule: never infer Therapy Session item consumption; unknown numeric values remain null.
    # V24 movement rule: classify submitted Stock Entry Detail rows by actual source/target warehouses, not by a text purpose label.
    # Procurement receipt values come from Purchase Receipt; financial values come only from submitted Purchase Invoice.

    args = frappe.form_dict or {}
    action = (args.get("action") or "main").strip().lower()

    if action == "create_purchase_orders":
        # REAL ERP ACTION: create Draft Purchase Orders from Stores 360.
        # One Draft PO per supplier. Never auto-submit.
        if frappe.session.user == "Guest":
            frappe.throw("Please sign in before creating Purchase Orders.")

        # IMPORTANT: Server Script safe_exec does not expose frappe.get_roles()
        # or frappe.has_permission(). Do not call either here.
        # po.insert() below performs the normal document permission/validation checks
        # for the currently logged-in user.

        # V25.13 SAFE_EXEC: this site does not expose frappe.parse_json().
        # Receive cart rows as simple indexed form fields from the webpage instead.
        try:
            cart_count = int(args.get("cart_count") or 0)
        except:
            cart_count = 0

        cart_rows = []
        row_index = 0
        while row_index < cart_count:
            prefix = "cart_" + str(row_index) + "_"
            item_code = (args.get(prefix + "item") or "").strip()
            supplier = (args.get(prefix + "supplier") or "").strip()
            item_name = (args.get(prefix + "item_name") or "").strip()
            priority = (args.get(prefix + "priority") or "").strip()
            try:
                qty = float(args.get(prefix + "qty") or 0)
            except:
                qty = 0
            try:
                rate = float(args.get(prefix + "rate") or 0)
            except:
                rate = 0

            if item_code or supplier or qty:
                cart_rows.append({
                    "item": item_code,
                    "item_name": item_name,
                    "qty": qty,
                    "rate": rate,
                    "vendorCode": supplier,
                    "priority": priority
                })
            row_index = row_index + 1

        if not cart_rows:
            frappe.throw("The next order list is empty.")

        company = ""
        try:
            company = frappe.defaults.get_user_default("Company") or ""
        except:
            company = ""
        if not company:
            try:
                company = frappe.db.get_single_value("Global Defaults", "default_company") or ""
            except:
                company = ""
        if not company:
            frappe.throw("Default Company is not configured.")

        company_currency = frappe.db.get_value("Company", company, "default_currency") or "INR"

        ho_warehouse = "Stores - LSACPL"
        if not frappe.db.exists("Warehouse", ho_warehouse):
            ho_warehouse = ""

        transaction_date = frappe.utils.today()
        schedule_date = frappe.utils.add_days(transaction_date, 7)

        grouped = {}
        for row in cart_rows:
            if not isinstance(row, dict):
                continue

            supplier = (row.get("vendorCode") or row.get("supplier") or row.get("vendor") or "").strip()
            item_code = (row.get("item") or row.get("item_code") or "").strip()
            try:
                qty = float(row.get("qty") or 0)
            except:
                qty = 0
            try:
                rate = float(row.get("rate") or 0)
            except:
                rate = 0

            if not item_code:
                frappe.throw("Item Code is missing in the next order list.")
            if qty <= 0:
                frappe.throw("Order Qty must be greater than zero for item " + item_code)
            if not frappe.db.exists("Item", item_code):
                frappe.throw("Item not found: " + item_code)

            item_state = frappe.db.get_value("Item", item_code, ["disabled", "is_purchase_item"], as_dict=True) or {}
            if int(item_state.get("disabled") or 0):
                frappe.throw("Item is disabled: " + item_code)
            if item_state.get("is_purchase_item") is not None and not int(item_state.get("is_purchase_item") or 0):
                frappe.throw("Item is not enabled for Purchase: " + item_code)

            # If the UI could not resolve the supplier, use the Item Supplier child table.
            if not supplier and frappe.db.exists("DocType", "Item Supplier"):
                supplier = frappe.db.get_value("Item Supplier", {"parent": item_code}, "supplier") or ""
            if not supplier:
                frappe.throw("Supplier is missing for item " + item_code + ". Select a Supplier in Next Order List.")
            if not frappe.db.exists("Supplier", supplier):
                frappe.throw("Supplier not found: " + supplier)

            if supplier not in grouped:
                grouped[supplier] = []
            grouped[supplier].append({"item_code": item_code, "qty": qty, "rate": rate})

        if not grouped:
            frappe.throw("No valid items were found in the next order list.")

        created = []
        for supplier in grouped:
            po_data = {
                "doctype": "Purchase Order",
                "supplier": supplier,
                "company": company,
                "transaction_date": transaction_date,
                "schedule_date": schedule_date,
                "currency": company_currency,
                "conversion_rate": 1,
                "items": []
            }

            po_meta = frappe.get_meta("Purchase Order")
            if po_meta.has_field("naming_series"):
                ns = frappe.db.get_value("Property Setter", {"doc_type": "Purchase Order", "field_name": "naming_series", "property": "options"}, "value") or ""
                if not ns:
                    try:
                        ns = po_meta.get_field("naming_series").options or ""
                    except:
                        ns = ""
                if ns:
                    po_data["naming_series"] = str(ns).split("\n")[0].strip()

            if ho_warehouse and po_meta.has_field("set_warehouse"):
                po_data["set_warehouse"] = ho_warehouse

            for row in grouped[supplier]:
                item_row = {
                    "item_code": row.get("item_code"),
                    "qty": row.get("qty"),
                    "schedule_date": schedule_date
                }
                if float(row.get("rate") or 0) > 0:
                    item_row["rate"] = float(row.get("rate") or 0)
                if ho_warehouse:
                    item_row["warehouse"] = ho_warehouse
                po_data["items"].append(item_row)

            try:
                po = frappe.get_doc(po_data)
                # Let ERPNext populate supplier name, title, price-list/currency defaults,
                # addresses, taxes and other standard defaults before validation.
                try:
                    po.run_method("set_missing_values")
                except:
                    pass
                if not po.get("currency"):
                    po.currency = company_currency
                if not po.get("conversion_rate"):
                    po.conversion_rate = 1

                # Save under the logged-in user's normal Purchase Order permissions.
                po.insert()

                created.append({
                    "name": po.name,
                    "supplier": supplier,
                    "item_count": len(grouped[supplier]),
                    "grand_total": float(po.get("grand_total") or 0),
                    "docstatus": int(po.docstatus or 0),
                    "workflow_state": po.get("workflow_state") or "",
                    "status": po.get("status") or "Draft"
                })
            except Exception as e:
                frappe.throw("Purchase Order could not be created for supplier " + supplier + ": " + str(e))

        frappe.response["message"] = {
            "ok": True,
            "message": str(len(created)) + " Draft Purchase Order(s) created.",
            "created": created,
            "company": company,
            "warehouse": ho_warehouse,
            "transaction_date": transaction_date,
            "schedule_date": schedule_date
        }

    elif action == "item_history":
        # Central warehouse must also be defined in item_history scope.
        # Previously it existed only in the main dashboard branch, causing:
        # NameError: name 'HO_WH' is not defined
        HO_WH = "Stores - LSACPL"

        item_code = (args.get("item_code") or "").strip()

        if not item_code:
            frappe.response["message"] = {
                "ok": False,
                "message": "item_code is required"
            }
        else:

            def fnum(v):
                try:
                    return float(v or 0)
                except:
                    return 0.0

            def sval(v):
                return "" if v is None else str(v)

            def has_field(doctype, fieldname):
                try:
                    return bool(frappe.get_meta(doctype).has_field(fieldname))
                except:
                    return False

            purchases = []
            dispatch = []
            returns = []
            consumption = []
            adjust = []

            # --------------------------------------------------------
            # 1. PURCHASE RECEIPT HISTORY FOR THIS ITEM ONLY
            # --------------------------------------------------------

            pr_item_fields = [
                "name",
                "parent",
                "item_code",
                "item_name",
                "qty",
                "received_qty",
                "stock_qty",
                "stock_uom",
                "rate",
                "amount",
                "warehouse",
                "material_request",
                "material_request_item",
                "purchase_order"
            ]

            pr_item_meta = frappe.get_meta("Purchase Receipt Item")
            pr_item_fields = [
                x for x in pr_item_fields
                if x in ["name", "parent"] or pr_item_meta.has_field(x)
            ]

            pr_items = frappe.get_all(
                "Purchase Receipt Item",
                filters={"item_code": item_code},
                fields=pr_item_fields,
                order_by="parent desc",
                limit_page_length=0
            )

            pr_names = []
            for row in pr_items:
                parent_name = row.get("parent") or ""
                if parent_name and parent_name not in pr_names:
                    pr_names.append(parent_name)

            pr_header_map = {}

            if pr_names:
                pr_headers = frappe.get_all(
                    "Purchase Receipt",
                    filters={
                        "name": ["in", pr_names],
                        "docstatus": 1
                    },
                    fields=[
                        "name",
                        "posting_date",
                        "posting_time",
                        "supplier",
                        "supplier_name",
                        "is_return",
                        "return_against",
                        "status"
                    ],
                    order_by="posting_date desc, posting_time desc",
                    limit_page_length=0
                )

                for header in pr_headers:
                    pr_header_map[header.get("name")] = header

            for row in pr_items:
                header = pr_header_map.get(row.get("parent"))
                if not header:
                    continue

                # Purchase Qty must match the Purchase Receipt Item accepted Qty field.
                # received_qty is gross receipt and stock_qty is Stock-UOM converted qty,
                # so neither should drive the Purchased Qty shown in the report.
                qty = fnum(row.get("qty"))

                # ERP returns reduce purchased quantity. Keep one consistent signed value
                # even if an older return row happens to store a positive qty.
                if header.get("is_return"):
                    qty = -abs(qty)

                rate = fnum(row.get("rate"))
                amount = fnum(row.get("amount"))

                # Keep Purchase Receipt value signed exactly like quantity.
                # Use a local name that is defined in this exact item-history scope.
                signed_purchase_amount = -abs(amount) if header.get("is_return") else amount

                purchases.append({
                    "inv": header.get("name") or "",
                    "po": row.get("purchase_order") or "",
                    "date": sval(header.get("posting_date")),
                    "time": sval(header.get("posting_time")),
                    "vendor": header.get("supplier") or "",
                    "vendor_name": header.get("supplier_name") or header.get("supplier") or "",
                    "item": item_code,
                    "item_name": row.get("item_name") or item_code,
                    "qty": qty,
                    "rate": rate,
                    "val": signed_purchase_amount,
                    "gt": amount,
                    "tax": 0,
                    "paid": 0,
                    "due": 0,
                    "warehouse": row.get("warehouse") or "",
                    "material_request": row.get("material_request") or "",
                    "material_request_item": row.get("material_request_item") or "",
                    "status": header.get("status") or ""
                })

            # --------------------------------------------------------
            # 2. STOCK ENTRY HISTORY FOR THIS ITEM ONLY
            # --------------------------------------------------------

            se_detail_meta = frappe.get_meta("Stock Entry Detail")

            se_detail_fields = [
                "name",
                "parent",
                "item_code",
                "item_name",
                "qty",
                "basic_rate",
                "basic_amount",
                "s_warehouse",
                "t_warehouse",
                "material_request",
                "material_request_item",
                "stock_uom",
                "uom"
            ]

            for optional_field in [
                "custom_received_qty",
                "custom_client_name",
                "custom_package_number"
            ]:
                if se_detail_meta.has_field(optional_field):
                    se_detail_fields.append(optional_field)

            se_items = frappe.get_all(
                "Stock Entry Detail",
                filters={"item_code": item_code},
                fields=se_detail_fields,
                order_by="parent desc",
                limit_page_length=0
            )

            se_names = []
            for row in se_items:
                parent_name = row.get("parent") or ""
                if parent_name and parent_name not in se_names:
                    se_names.append(parent_name)

            se_header_map = {}

            if se_names:
                se_fields = [
                    "name",
                    "posting_date",
                    "posting_time",
                    "stock_entry_type",
                    "purpose",
                    "docstatus",
                    "owner",
                    "modified_by"
                ]

                se_meta = frappe.get_meta("Stock Entry")

                for optional_field in [
                    "from_warehouse",
                    "to_warehouse",
                    "workflow_state",
                    "custom_stock_release_date",
                    "custom_stock_released_by",
                    "custom_sending_method",
                    "custom_delivery_reference",
                    "custom_received_by",
                    "custom_received_date"
                ]:
                    if se_meta.has_field(optional_field):
                        se_fields.append(optional_field)

                se_headers = frappe.get_all(
                    "Stock Entry",
                    filters={
                        "name": ["in", se_names],
                        "docstatus": 1
                    },
                    fields=se_fields,
                    order_by="posting_date desc, posting_time desc",
                    limit_page_length=0
                )

                for header in se_headers:
                    se_header_map[header.get("name")] = header

            for row in se_items:
                header = se_header_map.get(row.get("parent"))
                if not header:
                    continue

                purpose = (
                    header.get("purpose")
                    or header.get("stock_entry_type")
                    or ""
                )

                # Do not rely on purpose == "Material Transfer". Custom Stock Entry
                # Types can still represent a real warehouse-to-warehouse transfer.
                # The actual Stock Entry Detail source/target warehouses are the
                # authoritative movement evidence. Material Issue/Receipt rows with
                # one side blank naturally do not qualify below.
                src = (
                    row.get("s_warehouse")
                    or header.get("from_warehouse")
                    or ""
                )

                tgt = (
                    row.get("t_warehouse")
                    or header.get("to_warehouse")
                    or ""
                )

                # Real branch consumption is a submitted Material Issue from a branch
                # warehouse with no target warehouse. This is exact stock-ledger evidence,
                # not an inferred Therapy Session quantity.
                movement_text = (
                    sval(header.get("purpose")) + " " +
                    sval(header.get("stock_entry_type"))
                ).strip().lower()

                if "testing" in (src + " " + tgt).lower():
                    continue

                qty = fnum(row.get("qty"))
                rate = fnum(row.get("basic_rate"))
                value = fnum(row.get("basic_amount")) or qty * rate

                if src and not tgt and src != HO_WH and "material issue" in movement_text:
                    consumption.append({
                        "ref": row.get("parent") or "",
                        "date": sval(header.get("posting_date"))[:10],
                        "time": sval(header.get("posting_time")),
                        "item": item_code,
                        "item_name": row.get("item_name") or item_code,
                        "qty": abs(qty),
                        "rate": rate,
                        "val": abs(value),
                        "branch": src,
                        "source": src,
                        "target": "",
                        "entry_type": header.get("stock_entry_type") or header.get("purpose") or "Material Issue",
                        "purpose": purpose,
                        "material_request": row.get("material_request") or "",
                        "material_request_item": row.get("material_request_item") or "",
                        "client": row.get("custom_client_name") or "",
                        "package": row.get("custom_package_number") or "",
                        "status": "Posted"
                    })
                    continue

                # Dispatch / Return requires both source and target warehouses.
                if not src or not tgt or src == tgt:
                    continue

                receipt_confirmed = bool(
                    sval(header.get("custom_received_by")).strip()
                    or sval(header.get("custom_received_date")).strip()
                )

                received_qty = 0
                if receipt_confirmed:
                    received_qty = max(
                        fnum(row.get("custom_received_qty")),
                        0
                    )

                movement = {
                    "ref": row.get("parent") or "",
                    "date": sval(
                        header.get("custom_stock_release_date")
                        or header.get("posting_date")
                    )[:10],
                    "time": sval(header.get("posting_time")),
                    "item": item_code,
                    "item_name": row.get("item_name") or item_code,
                    "qty": qty,
                    "rate": rate,
                    "val": value,
                    "source": src,
                    "target": tgt,
                    "entry_type": header.get("stock_entry_type") or header.get("purpose") or "",
                    "purpose": purpose,
                    "material_request": row.get("material_request") or "",
                    "material_request_item": row.get("material_request_item") or "",
                    "received_qty": received_qty,
                    "received_by": header.get("custom_received_by") or "",
                    "received_on": sval(header.get("custom_received_date")),
                    "status": "Received" if receipt_confirmed else "Posted — receipt acknowledgement pending"
                }

                if tgt == HO_WH and src != HO_WH:
                    movement["movement_type"] = "Return to HO"
                    movement["branch"] = src
                    movement["rid"] = movement["ref"]
                    movement["reason"] = "Stock Entry transfer back to HO"
                    movement["cond"] = ""
                    movement["status"] = "Posted"
                    returns.append(movement)

                else:
                    # HO -> Branch and Branch -> Branch are both real outward
                    # warehouse transfers. Keep the exact source and target so the UI
                    # does not pretend every transfer originated from HO.
                    movement["movement_type"] = "HO to Branch" if src == HO_WH else "Branch to Branch"
                    movement["branch"] = tgt
                    movement["ind"] = movement["material_request"] or movement["ref"]
                    movement["challan"] = movement["ref"]
                    movement["reqDate"] = movement["date"]
                    movement["reqQty"] = qty
                    movement["recvDate"] = sval(header.get("custom_received_date"))[:10]
                    movement["recvTime"] = ""
                    movement["recvBy"] = header.get("custom_received_by") or ""
                    dispatch.append(movement)

            # --------------------------------------------------------
            # 3. REAL MISSING / DAMAGE ADJUSTMENT HISTORY
            # --------------------------------------------------------

            if frappe.db.exists(
                "DocType",
                "LIFE Stock Receipt Adjustment Item"
            ):
                adj_meta = frappe.get_meta(
                    "LIFE Stock Receipt Adjustment Item"
                )

                adj_fields = [
                    "name",
                    "parent",
                    "item_code",
                    "item_name",
                    "released_qty",
                    "received_qty",
                    "missing_qty",
                    "damaged_qty",
                    "return_to_source_qty",
                    "source_warehouse",
                    "target_warehouse",
                    "discrepancy_type",
                    "row_status"
                ]

                for optional_field in [
                    "discrepancy_remarks",
                    "evidence"
                ]:
                    if adj_meta.has_field(optional_field):
                        adj_fields.append(optional_field)

                adj_rows = frappe.get_all(
                    "LIFE Stock Receipt Adjustment Item",
                    filters={"item_code": item_code},
                    fields=adj_fields,
                    order_by="parent desc",
                    limit_page_length=0
                )

                adj_parent_names = []
                for row in adj_rows:
                    parent_name = row.get("parent") or ""
                    if (
                        parent_name
                        and parent_name not in adj_parent_names
                    ):
                        adj_parent_names.append(parent_name)

                adj_parent_map = {}

                if (
                    adj_parent_names
                    and frappe.db.exists(
                        "DocType",
                        "LIFE Stock Receipt Adjustment Request"
                    )
                ):
                    parent_meta = frappe.get_meta(
                        "LIFE Stock Receipt Adjustment Request"
                    )

                    parent_fields = [
                        "name",
                        "creation",
                        "modified",
                        "status",
                        "stock_entry"
                    ]

                    for optional_field in [
                        "reported_on",
                        "approved_on",
                        "approved_by",
                        "target_branch"
                    ]:
                        if parent_meta.has_field(optional_field):
                            parent_fields.append(optional_field)

                    parent_rows = frappe.get_all(
                        "LIFE Stock Receipt Adjustment Request",
                        filters={
                            "name": ["in", adj_parent_names]
                        },
                        fields=parent_fields,
                        limit_page_length=0
                    )

                    for parent_row in parent_rows:
                        adj_parent_map[
                            parent_row.get("name")
                        ] = parent_row

                for row in adj_rows:
                    parent = (
                        adj_parent_map.get(row.get("parent"))
                        or {}
                    )

                    missing_qty = fnum(
                        row.get("missing_qty")
                    )
                    damaged_qty = fnum(
                        row.get("damaged_qty")
                    )

                    adjustment_qty = (
                        missing_qty + damaged_qty
                    )

                    if adjustment_qty <= 0:
                        continue

                    reported_date = sval(
                        parent.get("reported_on")
                        or parent.get("approved_on")
                        or parent.get("creation")
                    )[:10]

                    adjust.append({
                        "aid": row.get("parent") or "",
                        "ref": parent.get("stock_entry") or "",
                        "date": reported_date,
                        "item": item_code,
                        "item_name": row.get("item_name") or item_code,
                        "loc": row.get("target_warehouse") or "",
                        "qty": adjustment_qty,
                        "missing_qty": missing_qty,
                        "damaged_qty": damaged_qty,
                        "return_qty": fnum(
                            row.get("return_to_source_qty")
                        ),
                        "reason": (
                            row.get("discrepancy_type")
                            or "Stock discrepancy"
                        ),
                        "status": (
                            row.get("row_status")
                            or parent.get("status")
                            or ""
                        ),
                        "approvedBy": (
                            parent.get("approved_by")
                            or ""
                        )
                    })

            frappe.response["message"] = {
                "ok": True,
                "item_code": item_code,
                "purchases": purchases,
                "dispatch": dispatch,
                "returns": returns,
                "consumption": consumption,
                "adjust": adjust,
                "counts": {
                    "purchases": len(purchases),
                    "dispatch": len(dispatch),
                    "returns": len(returns),
                    "consumption": len(consumption),
                    "adjustments": len(adjust)
                }
            }

    else:

        from_date = args.get("from_date") or args.get("from") or frappe.utils.add_days(frappe.utils.today(), -30)
        to_date = args.get("to_date") or args.get("to") or frappe.utils.today()
        branch_filter = (args.get("branch") or "").strip()
        item_group_filter = (args.get("item_group") or "").strip()

        HO_WH = "Stores - LSACPL"

        def fnum(v):
            try:
                return float(v or 0)
            except:
                return 0.0

        def sval(v):
            return "" if v is None else str(v)

        def has_field(doctype, fieldname):
            try:
                return bool(frappe.get_meta(doctype).has_field(fieldname))
            except:
                return False

        def pick_field(doctype, choices):
            for f in choices:
                if has_field(doctype, f):
                    return f
            return None

        def get_doc_value(doc, fieldname, default=""):
            try:
                v = doc.get(fieldname)
                return default if v is None else v
            except:
                return default


        # ============================================================
        # 1. WAREHOUSES / BRANCHES
        # ============================================================

        warehouse_filters = {
            "disabled": 0,
            "is_group": 0
        }

        warehouse_fields = ["name", "warehouse_name", "parent_warehouse"]

        warehouse_rows = frappe.get_all(
            "Warehouse",
            filters=warehouse_filters,
            fields=warehouse_fields,
            order_by="warehouse_name asc, name asc",
            limit_page_length=0
        )

        branches = []
        branch_codes = {}

        for w in warehouse_rows:
            name = w.get("name") or ""
            label = w.get("warehouse_name") or name

            if not name:
                continue

            low = (name + " " + label).lower()

            if "testing" in low:
                continue

            if name == HO_WH:
                continue

            branch_codes[name] = 1

            branches.append({
                "code": name,
                "name": label,
                "parent": w.get("parent_warehouse") or ""
            })


        # ============================================================
        # 2. ITEMS
        # ============================================================

        item_fields = [
            "item_code",
            "item_name",
            "item_group",
            "stock_uom",
            "valuation_rate",
            "last_purchase_rate",
            "safety_stock",
            "disabled",
            "is_stock_item"
        ]

        optional_item_fields = [
            "custom_main_category",
            "custom_stock_type",
            "custom_supplier_group",
            "custom_purchase_pack_options",
            "custom_issue_pack_to_branch",
            "custom_units_per_issue_pack",
            "custom_material_role"
        ]

        for f in optional_item_fields:
            if has_field("Item", f):
                item_fields.append(f)

        item_filters = {
            "disabled": 0,
            "is_stock_item": 1
        }

        item_rows = frappe.get_all(
            "Item",
            filters=item_filters,
            fields=item_fields,
            order_by="item_name asc, item_code asc",
            limit_page_length=0
        )

        items = []
        item_codes = []
        categories = []

        for i in item_rows:
            cat = i.get("custom_main_category") or i.get("item_group") or ""

            if item_group_filter and cat != item_group_filter and i.get("item_group") != item_group_filter:
                continue

            code = i.get("item_code")
            if not code:
                continue

            item_codes.append(code)

            if cat and cat not in categories:
                categories.append(cat)

            items.append({
                "code": code,
                "name": i.get("item_name") or code,
                "cat": cat,
                "item_group": i.get("item_group") or "",
                "type": i.get("custom_stock_type") or "",
                "unit": i.get("stock_uom") or "Nos",
                "rate": fnum(i.get("last_purchase_rate")) or fnum(i.get("valuation_rate")),
                "valuation_rate": fnum(i.get("valuation_rate")),
                "last_purchase_rate": fnum(i.get("last_purchase_rate")),
                "rl": fnum(i.get("safety_stock")),
                "supplier_group": i.get("custom_supplier_group") or "",
                "purchase_pack_options": i.get("custom_purchase_pack_options") or "",
                "issue_pack_to_branch": i.get("custom_issue_pack_to_branch") or "",
                "units_per_issue_pack": fnum(i.get("custom_units_per_issue_pack")),
                "material_role": i.get("custom_material_role") or ""
            })

        categories.sort()


        # ============================================================
        # 3. BIN / CURRENT STOCK
        # ============================================================

        ho_stock = {}
        branch_stock = {}
        bin_detail = []

        if item_codes:
            bin_rows = frappe.get_all(
                "Bin",
                filters={"item_code": ["in", item_codes]},
                fields=[
                    "item_code",
                    "warehouse",
                    "actual_qty",
                    "projected_qty",
                    "reserved_qty",
                    "ordered_qty",
                    "indented_qty",
                    "reserved_qty_for_production"
                ],
                limit_page_length=0
            )
        else:
            bin_rows = []

        for b in bin_rows:
            ic = b.get("item_code")
            wh = b.get("warehouse") or ""

            if not ic or not wh:
                continue

            if "testing" in wh.lower():
                continue

            actual = fnum(b.get("actual_qty"))

            if wh == HO_WH:
                ho_stock[ic] = ho_stock.get(ic, 0) + actual

            elif branch_codes.get(wh):
                if ic not in branch_stock:
                    branch_stock[ic] = {}
                branch_stock[ic][wh] = branch_stock[ic].get(wh, 0) + actual

            # bin_detail intentionally omitted in fast dashboard mode

        for ic in item_codes:
            if ic not in ho_stock:
                ho_stock[ic] = 0
            if ic not in branch_stock:
                branch_stock[ic] = {}


        # ============================================================
        # 4. MATERIAL REQUESTS
        #    Uses only fields that actually exist in your doctype.
        # ============================================================

        mr_meta = frappe.get_meta("Material Request")

        mr_fields = [
            "name",
            "transaction_date",
            "schedule_date",
            "material_request_type",
            "status",
            "docstatus",
            "owner",
            "modified_by",
            "creation",
            "modified"
        ]

        for f in [
            "workflow_state",
            "set_from_warehouse",
            "set_warehouse",
            "company"
        ]:
            if mr_meta.has_field(f):
                mr_fields.append(f)

        # Add custom fields only if they REALLY exist
        mr_custom_candidates = [
            "custom_client_name",
            "custom_therapy_id",
            "custom_material_request_by",
            "custom_priority",
            "custom_stock_request_type",
            "custom_stock_request_status",
            "custom_stock_entry_reference",
            "custom_patient_appointment",
            "custom_expected_client_name",
            "custom_expected_client_phone",
            "custom_expected_joining_date",
            "custom_expected_treatment_category",
            "custom_expected_sessions",
            "branch"
        ]

        for f in mr_custom_candidates:
            if mr_meta.has_field(f):
                mr_fields.append(f)

        mr_filters = [
            ["transaction_date", ">=", from_date],
            ["transaction_date", "<=", to_date],
            ["docstatus", "<", 2],
            ["material_request_type", "=", "Material Transfer"]
        ]

        material_request_headers = frappe.get_all(
            "Material Request",
            filters=mr_filters,
            fields=mr_fields,
            order_by="transaction_date desc, name desc",
            limit_page_length=0
        )

        mri_meta = frappe.get_meta("Material Request Item")

        mri_fields = ["name", "parent", "idx"]

        for f in [
            "item_code",
            "item_name",
            "qty",
            "stock_qty",
            "stock_uom",
            "uom",
            "warehouse",
            "from_warehouse",
            "ordered_qty",
            "received_qty",
            "custom_approved_qty",
            "schedule_date",
            "conversion_factor"
        ]:
            if mri_meta.has_field(f):
                mri_fields.append(f)

        mr_names = [x.get("name") for x in material_request_headers if x.get("name")]

        if mr_names:
            material_request_items = frappe.get_all(
                "Material Request Item",
                filters={"parent": ["in", mr_names]},
                fields=mri_fields,
                order_by="parent asc, idx asc",
                limit_page_length=0
            )
        else:
            material_request_items = []

        mr_item_map = {}

        for row in material_request_items:
            p = row.get("parent")
            if p not in mr_item_map:
                mr_item_map[p] = []
            mr_item_map[p].append(row)

        material_requests = []
        stock_requests = []

        for mr in material_request_headers:
            mr_name = mr.get("name")
            rows = mr_item_map.get(mr_name, [])

            source_wh = mr.get("set_from_warehouse") or ""
            target_wh = mr.get("set_warehouse") or ""

            # If parent warehouse fields are empty, use child fields.
            if not source_wh and rows:
                source_wh = rows[0].get("from_warehouse") or ""

            if not target_wh and rows:
                target_wh = rows[0].get("warehouse") or ""

            # Branch is target warehouse by default.
            branch_value = mr.get("branch") or target_wh or source_wh

            if branch_filter:
                if branch_filter == "HO":
                    if source_wh != HO_WH and target_wh != HO_WH:
                        continue
                elif branch_value != branch_filter and source_wh != branch_filter and target_wh != branch_filter:
                    continue

            for r in rows:
                item_code = r.get("item_code") or ""

                if item_group_filter and item_code:
                    matched = False
                    for it in items:
                        if it["code"] == item_code:
                            matched = True
                            break
                    if not matched:
                        continue

                qty = fnum(r.get("qty") if r.get("qty") is not None else r.get("stock_qty"))
                ordered_qty = fnum(r.get("ordered_qty"))
                received_qty = fnum(r.get("received_qty"))

                approved_qty = None
                if mri_meta.has_field("custom_approved_qty"):
                    approved_raw = r.get("custom_approved_qty")
                    if approved_raw is not None:
                        approved_qty = fnum(approved_raw)

                status = (
                    mr.get("custom_stock_request_status")
                    or mr.get("workflow_state")
                    or mr.get("status")
                    or ""
                )

                request_type = (
                    mr.get("custom_stock_request_type")
                    or mr.get("material_request_type")
                    or ""
                )

                priority = mr.get("custom_priority") or "Normal"

                row_data = {
                    "request_id": mr_name,
                    "material_request_item": r.get("name") or "",
                    "date": sval(mr.get("transaction_date")),
                    "required_by": sval(r.get("schedule_date") or mr.get("schedule_date")),
                    "purpose": mr.get("material_request_type") or "",
                    "status": status,
                    "erp_status": mr.get("status") or "",
                    "workflow_state": mr.get("workflow_state") or "",
                    "source_warehouse": source_wh or r.get("from_warehouse") or "",
                    "target_warehouse": target_wh or r.get("warehouse") or "",
                    "branch": branch_value,
                    "client": mr.get("custom_client_name") or "",
                    "therapy_id": mr.get("custom_therapy_id") or "",
                    "request_by": mr.get("custom_material_request_by") or mr.get("owner") or "",
                    "priority": priority,
                    "request_type": request_type,
                    "stock_entry": mr.get("custom_stock_entry_reference") or "",
                    "appointment": mr.get("custom_patient_appointment") or "",
                    "expected_client": mr.get("custom_expected_client_name") or "",
                    "expected_phone": mr.get("custom_expected_client_phone") or "",
                    "expected_joining_date": sval(mr.get("custom_expected_joining_date")),
                    "expected_treatment_category": mr.get("custom_expected_treatment_category") or "",
                    "expected_sessions": fnum(mr.get("custom_expected_sessions")),
                    "item": item_code,
                    "item_name": r.get("item_name") or item_code,
                    "qty": qty,
                    "ordered_qty": ordered_qty,
                    "approved_qty": approved_qty,
                    "received_qty": received_qty,
                    "pending_qty": max(qty - received_qty, 0),
                    "unit": r.get("stock_uom") or r.get("uom") or "",
                    "owner": mr.get("owner") or "",
                    "modified_by": mr.get("modified_by") or ""
                }

                material_requests.append(row_data)

                stock_requests.append({
                    "id": mr_name,
                    "req": mr_name,
                    "date": row_data["date"],
                    "reqDate": row_data["date"],
                    "needDate": row_data["required_by"],
                    "br": row_data["branch"],
                    "branch": row_data["branch"],
                    "src": row_data["source_warehouse"],
                    "source": row_data["source_warehouse"],
                    "client": row_data["client"],
                    "therapy": row_data["therapy_id"],
                    "appointment": row_data["appointment"],
                    "requestBy": row_data["request_by"],
                    "reqBy": row_data["request_by"],
                    "priority": row_data["priority"],
                    "stockType": row_data["request_type"],
                    "requestType": row_data["request_type"],
                    "status": row_data["status"],
                    "item": row_data["item"],
                    "itemName": row_data["item_name"],
                    "qty": qty,
                    "reqQty": qty,
                    "approvedQty": approved_qty,
                    "recQty": received_qty,
                    "receivedQty": received_qty,
                    "pendingQty": max(qty - received_qty, 0),
                    "unit": row_data["unit"],
                    "stockEntry": row_data["stock_entry"],
                    "expectedClient": row_data["expected_client"],
                    "expectedPhone": row_data["expected_phone"],
                    "expectedJoiningDate": row_data["expected_joining_date"],
                    "expectedTreatmentCategory": row_data["expected_treatment_category"],
                    "expectedSessions": row_data["expected_sessions"]
                })


        # ============================================================
        # 5. SPECIAL MATERIAL REQUEST DETAIL + CLIENT / THERAPY MAPPING
        #    This is the real link for client-wise stock requests.
        # ============================================================

        special_request_details = []
        special_request_parents = []
        special_parent_doctype = ""
        special_detail_by_parent = {}
        therapy_plan_map = {}

        if frappe.db.exists("DocType", "Special Material Request Detail"):
            parent_candidates = frappe.get_all(
                "DocField",
                filters={
                    "fieldtype": "Table",
                    "options": "Special Material Request Detail"
                },
                fields=["parent", "fieldname"],
                limit_page_length=0
            )

            if parent_candidates:
                special_parent_doctype = parent_candidates[0].get("parent") or ""

            detail_filters = {}

            # In the current stock workflow this child table is normally attached
            # directly to Material Request. Restricting to the already-loaded MRs
            # keeps the API fast even when historical data is large.
            if special_parent_doctype == "Material Request" and mr_names:
                detail_filters = {"parent": ["in", mr_names]}

            detail_rows = frappe.get_all(
                "Special Material Request Detail",
                filters=detail_filters,
                fields=[
                    "name",
                    "parent",
                    "parenttype",
                    "parentfield",
                    "idx",
                    "therapy_plan",
                    "therapy_detail_row",
                    "therapy_type",
                    "sales_invoices",
                    "branch",
                    "booked_sessions",
                    "completed_sessions",
                    "remaining_sessions"
                ],
                order_by="parent asc, idx asc",
                limit_page_length=0
            )

            therapy_plan_ids = []

            for detail_row in detail_rows:
                detail_parent = detail_row.get("parent") or ""

                detail_data = {
                    "name": detail_row.get("name") or "",
                    "parent": detail_parent,
                    "parenttype": detail_row.get("parenttype") or "",
                    "parentfield": detail_row.get("parentfield") or "",
                    "therapy_plan": detail_row.get("therapy_plan") or "",
                    "therapy_detail_row": detail_row.get("therapy_detail_row") or "",
                    "therapy_type": detail_row.get("therapy_type") or "",
                    "sales_invoices": detail_row.get("sales_invoices") or "",
                    "branch": detail_row.get("branch") or "",
                    "booked_sessions": int(detail_row.get("booked_sessions") or 0),
                    "completed_sessions": int(detail_row.get("completed_sessions") or 0),
                    "remaining_sessions": int(detail_row.get("remaining_sessions") or 0)
                }

                special_request_details.append(detail_data)

                if detail_parent not in special_detail_by_parent:
                    special_detail_by_parent[detail_parent] = []
                special_detail_by_parent[detail_parent].append(detail_data)

                therapy_plan_id = detail_data.get("therapy_plan") or ""
                if therapy_plan_id and therapy_plan_id not in therapy_plan_ids:
                    therapy_plan_ids.append(therapy_plan_id)

            if therapy_plan_ids and frappe.db.exists("DocType", "Therapy Plan"):
                therapy_plan_meta = frappe.get_meta("Therapy Plan")
                therapy_plan_fields = ["name", "patient", "patient_name", "status", "start_date"]

                for therapy_field in ["therapy_plan_template", "company"]:
                    if therapy_plan_meta.has_field(therapy_field):
                        therapy_plan_fields.append(therapy_field)

                therapy_plan_rows = frappe.get_all(
                    "Therapy Plan",
                    filters={"name": ["in", therapy_plan_ids]},
                    fields=therapy_plan_fields,
                    limit_page_length=0
                )

                for therapy_row in therapy_plan_rows:
                    therapy_plan_map[therapy_row.get("name")] = therapy_row

            # Enrich each Material Request line with the Patient/Therapy data from
            # Special Material Request Detail -> Therapy Plan -> Patient.
            for request_row in material_requests:
                request_name = request_row.get("request_id") or ""
                request_details = special_detail_by_parent.get(request_name, [])

                if request_details:
                    first_detail = request_details[0]
                    patient_id = ""
                    patient_name = ""
                    therapy_names = []
                    therapy_types = []
                    branch_name = ""
                    booked_sessions = 0
                    completed_sessions = 0
                    remaining_sessions = 0

                    for request_detail in request_details:
                        therapy_plan_id = request_detail.get("therapy_plan") or ""
                        therapy_row = therapy_plan_map.get(therapy_plan_id) or {}

                        if therapy_plan_id and therapy_plan_id not in therapy_names:
                            therapy_names.append(therapy_plan_id)

                        therapy_type = request_detail.get("therapy_type") or ""
                        if therapy_type and therapy_type not in therapy_types:
                            therapy_types.append(therapy_type)

                        if not patient_id:
                            patient_id = therapy_row.get("patient") or ""
                            patient_name = therapy_row.get("patient_name") or ""

                        if not branch_name:
                            branch_name = request_detail.get("branch") or ""

                        booked_sessions += int(request_detail.get("booked_sessions") or 0)
                        completed_sessions += int(request_detail.get("completed_sessions") or 0)
                        remaining_sessions += int(request_detail.get("remaining_sessions") or 0)

                    if patient_id:
                        request_row["client"] = patient_id
                    if therapy_names:
                        request_row["therapy_id"] = ", ".join(therapy_names)
                    if branch_name:
                        request_row["branch_name"] = branch_name

                    request_row["patient_name"] = patient_name
                    request_row["therapy_type"] = ", ".join(therapy_types)
                    request_row["booked_sessions"] = booked_sessions
                    request_row["completed_sessions"] = completed_sessions
                    request_row["remaining_sessions"] = remaining_sessions
                    request_row["execution_evidence"] = "Yes" if completed_sessions > 0 else "No"
                    request_row["executed_qty"] = None

            for request_row in stock_requests:
                request_name = request_row.get("req") or request_row.get("id") or ""
                request_details = special_detail_by_parent.get(request_name, [])

                if request_details:
                    patient_id = ""
                    patient_name = ""
                    therapy_names = []
                    therapy_types = []
                    branch_name = ""
                    booked_sessions = 0
                    completed_sessions = 0
                    remaining_sessions = 0

                    for request_detail in request_details:
                        therapy_plan_id = request_detail.get("therapy_plan") or ""
                        therapy_row = therapy_plan_map.get(therapy_plan_id) or {}

                        if therapy_plan_id and therapy_plan_id not in therapy_names:
                            therapy_names.append(therapy_plan_id)

                        therapy_type = request_detail.get("therapy_type") or ""
                        if therapy_type and therapy_type not in therapy_types:
                            therapy_types.append(therapy_type)

                        if not patient_id:
                            patient_id = therapy_row.get("patient") or ""
                            patient_name = therapy_row.get("patient_name") or ""

                        if not branch_name:
                            branch_name = request_detail.get("branch") or ""

                        booked_sessions += int(request_detail.get("booked_sessions") or 0)
                        completed_sessions += int(request_detail.get("completed_sessions") or 0)
                        remaining_sessions += int(request_detail.get("remaining_sessions") or 0)

                    if patient_id:
                        request_row["client"] = patient_id
                    if therapy_names:
                        request_row["therapy"] = ", ".join(therapy_names)
                    if branch_name:
                        request_row["branchName"] = branch_name

                    request_row["patientName"] = patient_name
                    request_row["therapyType"] = ", ".join(therapy_types)
                    request_row["bookedSessions"] = booked_sessions
                    request_row["completedSessions"] = completed_sessions
                    request_row["remainingSessions"] = remaining_sessions
                    request_row["executionEvidence"] = "Yes" if completed_sessions > 0 else "No"
                    request_row["executedQty"] = None

            # FAST MODE:
            # Special request parent diagnostics are not required by Stores 360.
            special_request_parents = []


        # ============================================================
        # 6. STOCK ENTRIES / MOVEMENT
        # ============================================================

        se_fields = [
            "name",
            "posting_date",
            "posting_time",
            "stock_entry_type",
            "purpose",
            "docstatus",
            "owner",
            "modified_by"
        ]

        for se_optional_field in [
            "material_request",
            "workflow_state",
            "from_warehouse",
            "to_warehouse",
            "custom_stock_release_date",
            "custom_stock_released_by",
            "custom_sending_method",
            "custom_delivery_reference",
            "custom_received_by",
            "custom_received_date"
        ]:
            if has_field("Stock Entry", se_optional_field):
                se_fields.append(se_optional_field)

        stock_entries = frappe.get_all(
            "Stock Entry",
            filters=[
                ["docstatus", "=", 1],
                ["posting_date", ">=", from_date],
                ["posting_date", "<=", to_date]
            ],
            fields=se_fields,
            order_by="posting_date desc, posting_time desc, name desc",
            limit_page_length=0
        )

        se_names = [x.get("name") for x in stock_entries if x.get("name")]

        sed_fields = ["name", "parent", "idx"]

        sed_meta = frappe.get_meta("Stock Entry Detail")

        for f in [
            "item_code",
            "item_name",
            "qty",
            "basic_rate",
            "basic_amount",
            "s_warehouse",
            "t_warehouse",
            "material_request",
            "material_request_item",
            "stock_uom",
            "uom",
            "custom_received_qty",
            "custom_client_name",
            "custom_package_number"
        ]:
            if sed_meta.has_field(f):
                sed_fields.append(f)

        if se_names:
            se_detail_rows = frappe.get_all(
                "Stock Entry Detail",
                filters={"parent": ["in", se_names]},
                fields=sed_fields,
                order_by="parent asc, idx asc",
                limit_page_length=0
            )
        else:
            se_detail_rows = []

        se_header_map = {}
        for h in stock_entries:
            se_header_map[h.get("name")] = h

        dispatch = []
        returns = []
        consumption = []
        adjust = []

        released_by_request_item = {}
        received_by_request_item = {}
        released_by_request_code = {}
        received_by_request_code = {}
        entry_by_request_code = {}
        receipt_state_by_request_code = {}

        for r in se_detail_rows:
            h = se_header_map.get(r.get("parent")) or {}

            src = r.get("s_warehouse") or h.get("from_warehouse") or ""
            tgt = r.get("t_warehouse") or h.get("to_warehouse") or ""

            movement_text = (
                sval(h.get("purpose")) + " " +
                sval(h.get("stock_entry_type"))
            ).strip().lower()

            if "testing" in (src + " " + tgt).lower():
                continue

            if branch_filter and branch_filter != "HO":
                if src != branch_filter and tgt != branch_filter:
                    continue

            qty = fnum(r.get("qty"))
            rate = fnum(r.get("basic_rate"))
            amount = fnum(r.get("basic_amount")) or qty * rate

            # Exact branch consumption: submitted Material Issue, branch source, no target.
            # Do not infer consumption from dispatch minus Bin or from Therapy Session counts.
            if src and not tgt and src != HO_WH and "material issue" in movement_text:
                consumption.append({
                    "ref": r.get("parent") or "",
                    "date": sval(h.get("posting_date"))[:10],
                    "time": sval(h.get("posting_time")),
                    "item": r.get("item_code") or "",
                    "item_name": r.get("item_name") or r.get("item_code") or "",
                    "qty": abs(qty),
                    "rate": rate,
                    "val": abs(amount),
                    "branch": src,
                    "source": src,
                    "target": "",
                    "entry_type": h.get("stock_entry_type") or h.get("purpose") or "Material Issue",
                    "purpose": h.get("purpose") or "",
                    "material_request": r.get("material_request") or h.get("material_request") or "",
                    "material_request_item": r.get("material_request_item") or "",
                    "client": r.get("custom_client_name") or "",
                    "package": r.get("custom_package_number") or "",
                    "owner": h.get("owner") or "",
                    "status": "Posted"
                })
                continue

            # Dispatch / Return requires a real warehouse-to-warehouse transfer.
            if not src or not tgt or src == tgt:
                continue

            request_name = r.get("material_request") or h.get("material_request") or ""
            request_item = r.get("material_request_item") or ""
            item_code = r.get("item_code") or ""
            entry_name = r.get("parent") or ""

            receipt_confirmed = bool(
                sval(h.get("custom_received_by")).strip()
                or sval(h.get("custom_received_date")).strip()
            )

            actual_received_qty = 0
            if receipt_confirmed:
                actual_received_qty = max(fnum(r.get("custom_received_qty")), 0)

            base = {
                "ref": entry_name,
                "date": sval(h.get("custom_stock_release_date") or h.get("posting_date")),
                "time": sval(h.get("posting_time")),
                "item": item_code,
                "item_name": r.get("item_name") or item_code,
                "qty": qty,
                "released_qty": qty,
                "received_qty": actual_received_qty,
                "rate": rate,
                "val": amount,
                "source": src,
                "target": tgt,
                "material_request": request_name,
                "material_request_item": request_item,
                "entry_type": h.get("stock_entry_type") or h.get("purpose") or "",
                "owner": h.get("owner") or "",
                "modified_by": h.get("modified_by") or "",
                "released_by": h.get("custom_stock_released_by") or h.get("owner") or "",
                "released_on": sval(h.get("custom_stock_release_date") or h.get("posting_date")),
                "received_by": h.get("custom_received_by") or "",
                "received_on": sval(h.get("custom_received_date")),
                "sending_method": h.get("custom_sending_method") or "",
                "delivery_reference": h.get("custom_delivery_reference") or "",
                "workflow_state": h.get("workflow_state") or "",
                "client": r.get("custom_client_name") or "",
                "package": r.get("custom_package_number") or ""
            }

            if tgt == HO_WH and src != HO_WH:
                x = dict(base)
                x["movement_type"] = "Return to HO"
                x["branch"] = src
                x["rid"] = entry_name
                x["reason"] = "Stock Entry transfer back to HO"
                x["cond"] = ""
                x["status"] = "Posted"
                returns.append(x)

            else:
                x = dict(base)
                x["movement_type"] = "HO to Branch" if src == HO_WH else "Branch to Branch"
                x["branch"] = tgt
                x["ind"] = request_name or entry_name
                x["challan"] = entry_name
                x["reqQty"] = qty
                x["reqDate"] = base["date"]
                x["reqBy"] = ""
                x["recvDate"] = sval(h.get("custom_received_date"))
                x["recvTime"] = ""
                x["recvBy"] = h.get("custom_received_by") or ""
                x["priority"] = ""
                x["status"] = "Received" if receipt_confirmed else "Posted — receipt acknowledgement pending"
                dispatch.append(x)

            if request_item:
                released_by_request_item[request_item] = released_by_request_item.get(request_item, 0) + qty
                received_by_request_item[request_item] = received_by_request_item.get(request_item, 0) + actual_received_qty

            if request_name and item_code:
                request_key = request_name + "||" + item_code
                released_by_request_code[request_key] = released_by_request_code.get(request_key, 0) + qty
                received_by_request_code[request_key] = received_by_request_code.get(request_key, 0) + actual_received_qty
                if entry_name:
                    entry_by_request_code[request_key] = entry_name
                if receipt_confirmed:
                    receipt_state_by_request_code[request_key] = "Received"
                elif not receipt_state_by_request_code.get(request_key):
                    receipt_state_by_request_code[request_key] = "Pending Receipt"

        for request_row in material_requests:
            request_name = request_row.get("request_id") or ""
            request_item = request_row.get("material_request_item") or ""
            item_code = request_row.get("item") or ""

            released_qty = 0
            received_qty = 0

            if request_item:
                released_qty = fnum(released_by_request_item.get(request_item))
                received_qty = fnum(received_by_request_item.get(request_item))

            request_key = request_name + "||" + item_code if request_name and item_code else ""

            if request_key:
                if not released_qty:
                    released_qty = fnum(released_by_request_code.get(request_key))
                if not received_qty:
                    received_qty = fnum(received_by_request_code.get(request_key))

            request_qty = fnum(request_row.get("qty"))
            request_row["released_qty"] = released_qty
            request_row["received_qty"] = received_qty
            request_row["pending_receipt_qty"] = max(released_qty - received_qty, 0)
            request_row["pending_qty"] = max(request_qty - received_qty, 0)
            request_row["receipt_status"] = receipt_state_by_request_code.get(request_key) or ("Pending Release" if request_qty > 0 else "")
            if request_row["receipt_status"] == "Received":
                request_row["receipt_reconciliation_diff"] = max(released_qty - received_qty, 0)
            else:
                request_row["receipt_reconciliation_diff"] = None

            if request_key and not request_row.get("stock_entry"):
                request_row["stock_entry"] = entry_by_request_code.get(request_key) or ""

        for request_row in stock_requests:
            request_name = request_row.get("req") or request_row.get("id") or ""
            item_code = request_row.get("item") or ""
            request_key = request_name + "||" + item_code if request_name and item_code else ""

            released_qty = fnum(released_by_request_code.get(request_key))
            received_qty = fnum(received_by_request_code.get(request_key))
            request_qty = fnum(request_row.get("reqQty") or request_row.get("qty"))

            request_row["releasedQty"] = released_qty
            request_row["recQty"] = received_qty
            request_row["receivedQty"] = received_qty
            request_row["pendingReceiptQty"] = max(released_qty - received_qty, 0)
            request_row["pendingQty"] = max(request_qty - received_qty, 0)
            request_row["receiptStatus"] = receipt_state_by_request_code.get(request_key) or ("Pending Release" if request_qty > 0 else "")
            if request_row["receiptStatus"] == "Received":
                request_row["receiptReconciliationDiff"] = max(released_qty - received_qty, 0)
            else:
                request_row["receiptReconciliationDiff"] = None

            if request_key and not request_row.get("stockEntry"):
                request_row["stockEntry"] = entry_by_request_code.get(request_key) or ""


        # ============================================================
        # 7. PURCHASE RECEIPTS
        #    Exact ERPNext fields confirmed from your doctypes.
        # ============================================================

        purchase_receipts = frappe.get_all(
            "Purchase Receipt",
            filters=[
                ["docstatus", "=", 1],
                ["posting_date", ">=", from_date],
                ["posting_date", "<=", to_date]
            ],
            fields=[
                "name",
                "posting_date",
                "posting_time",
                "supplier",
                "supplier_name",
                "status",
                "is_return",
                "return_against"
            ],
            order_by="posting_date desc, posting_time desc, name desc",
            limit_page_length=0
        )

        pr_names = [x.get("name") for x in purchase_receipts if x.get("name")]

        if pr_names:
            pr_items = frappe.get_all(
                "Purchase Receipt Item",
                filters={"parent": ["in", pr_names]},
                fields=[
                    "name",
                    "parent",
                    "idx",
                    "item_code",
                    "item_name",
                    "received_qty",
                    "qty",
                    "rejected_qty",
                    "stock_qty",
                    "stock_uom",
                    "rate",
                    "amount",
                    "warehouse",
                    "from_warehouse",
                    "material_request",
                    "material_request_item",
                    "purchase_order",
                    "purchase_order_item"
                ],
                order_by="parent asc, idx asc",
                limit_page_length=0
            )
        else:
            pr_items = []

        pr_header_map = {}
        for h in purchase_receipts:
            pr_header_map[h.get("name")] = h

        purchases = []
        purchase_receipt_lines = []
        pr_received_by_mr_item = {}
        pr_received_by_mr_itemcode = {}

        for r in pr_items:
            h = pr_header_map.get(r.get("parent")) or {}

            wh = r.get("warehouse") or ""
            if "testing" in wh.lower():
                continue

            if branch_filter and branch_filter != "HO":
                if wh != branch_filter and (r.get("from_warehouse") or "") != branch_filter:
                    continue

            item_code = r.get("item_code") or ""
            qty = fnum(r.get("qty"))
            received_qty = fnum(r.get("received_qty"))
            rejected_qty = fnum(r.get("rejected_qty"))
            stock_qty = fnum(r.get("stock_qty"))
            rate = fnum(r.get("rate"))
            amount = fnum(r.get("amount"))

            mr = r.get("material_request") or ""
            mri = r.get("material_request_item") or ""

            # Correct Purchase Qty source for this dashboard:
            # Purchase Receipt Item.qty = accepted/purchased quantity shown on the PR.
            # received_qty = gross receipt (before rejection) and stock_qty = Stock-UOM
            # conversion, so they are kept as audit fields but do NOT replace qty.
            is_return = int(h.get("is_return") or 0)
            usable_qty = -abs(qty) if is_return else qty
            gross_received_qty = received_qty if received_qty else (abs(qty) + rejected_qty)
            if is_return and gross_received_qty:
                gross_received_qty = -abs(gross_received_qty)

            # Return values must reduce Purchase Worth as well.
            purchase_amount = -abs(amount) if is_return else amount

            purchase_line = {
                "receipt": r.get("parent") or "",
                "date": sval(h.get("posting_date")),
                "time": sval(h.get("posting_time")),
                "status": h.get("status") or "",
                "is_return": is_return,
                "return_against": h.get("return_against") or "",
                "supplier": h.get("supplier") or "",
                "supplier_name": h.get("supplier_name") or h.get("supplier") or "",
                "item": item_code,
                "item_name": r.get("item_name") or item_code,
                "warehouse": wh,
                "from_warehouse": r.get("from_warehouse") or "",
                "material_request": mr,
                "material_request_item": mri,
                "purchase_order": r.get("purchase_order") or "",
                "purchase_order_item": r.get("purchase_order_item") or "",
                "received_qty": gross_received_qty,
                "usable_qty": usable_qty,
                "rejected_qty": rejected_qty,
                "stock_qty": stock_qty,
                "uom": r.get("stock_uom") or "",
                "rate": rate,
                "amount": purchase_amount
            }

            purchase_receipt_lines.append(purchase_line)

            purchases.append({
                "inv": r.get("parent") or "",
                "po": r.get("purchase_order") or "",
                "mr": mr,
                "mr_item": mri,
                "date": sval(h.get("posting_date")),
                "vendor": h.get("supplier") or "",
                "vendor_name": h.get("supplier_name") or h.get("supplier") or "",
                "item": item_code,
                "item_name": r.get("item_name") or item_code,
                "qty": usable_qty,
                "received_qty": gross_received_qty,
                "rejected_qty": rejected_qty,
                "rate": rate,
                "val": purchase_amount,
                "gt": None,
                "paid": None,
                "due": None,
                "warehouse": wh,
                "status": h.get("status") or ""
            })

            # Best link: exact Material Request Item row.
            if mri:
                pr_received_by_mr_item[mri] = pr_received_by_mr_item.get(mri, 0) + usable_qty

            # Fallback when child row link is unavailable.
            if mr and item_code:
                k = mr + "||" + item_code
                pr_received_by_mr_itemcode[k] = pr_received_by_mr_itemcode.get(k, 0) + usable_qty


        # Purchase Receipt is procurement receipt into Stores. Do not use it to
        # overwrite branch transfer received quantities. Keep exact PR quantity
        # only as a procurement reference.
        for r in material_requests:
            mr_name = r.get("request_id") or ""
            item_code = r.get("item") or ""
            mr_item_name = r.get("material_request_item") or ""
            pr_qty = 0
            if mr_item_name:
                pr_qty = fnum(pr_received_by_mr_item.get(mr_item_name))
            if not pr_qty and mr_name and item_code:
                pr_qty = fnum(pr_received_by_mr_itemcode.get(mr_name + "||" + item_code))
            if pr_qty:
                r["purchase_receipt_qty"] = pr_qty

        for r in stock_requests:
            mr_name = r.get("req") or r.get("id") or ""
            item_code = r.get("item") or ""
            pr_qty = fnum(pr_received_by_mr_itemcode.get(mr_name + "||" + item_code)) if mr_name and item_code else 0
            if pr_qty:
                r["purchaseReceiptQty"] = pr_qty


        # ============================================================
        # 7A. LIFETIME PURCHASE RECEIPT QUANTITY FOR HO STOCK LEDGER
        #     Purchased Qty on the HO Stock Ledger is an all-time procurement
        #     figure. It must not shrink when the report From/To period changes.
        #     Source: submitted Purchase Receipt Item.qty. Purchase Returns reduce it.
        # ============================================================

        lifetime_purchases = []

        lifetime_pr_headers = frappe.get_all(
            "Purchase Receipt",
            filters=[["docstatus", "=", 1]],
            fields=[
                "name", "posting_date", "posting_time", "supplier",
                "supplier_name", "status", "is_return", "return_against"
            ],
            order_by="posting_date desc, posting_time desc, name desc",
            limit_page_length=0
        )

        lifetime_pr_names = [x.get("name") for x in lifetime_pr_headers if x.get("name")]
        lifetime_pr_header_map = {}
        for h in lifetime_pr_headers:
            lifetime_pr_header_map[h.get("name")] = h

        if lifetime_pr_names:
            lifetime_pr_items = frappe.get_all(
                "Purchase Receipt Item",
                filters={"parent": ["in", lifetime_pr_names]},
                fields=[
                    "parent", "idx", "item_code", "item_name", "qty",
                    "rate", "amount", "warehouse", "purchase_order"
                ],
                order_by="parent asc, idx asc",
                limit_page_length=0
            )
        else:
            lifetime_pr_items = []

        for r in lifetime_pr_items:
            h = lifetime_pr_header_map.get(r.get("parent")) or {}
            wh = r.get("warehouse") or ""

            # Testing warehouse is never part of LIFE Stores 360.
            if "testing" in wh.lower():
                continue

            item_code = r.get("item_code") or ""
            if not item_code:
                continue

            qty = fnum(r.get("qty"))
            amount = fnum(r.get("amount"))
            is_return = int(h.get("is_return") or 0)

            purchase_qty = -abs(qty) if is_return else qty
            purchase_amount = -abs(amount) if is_return else amount

            lifetime_purchases.append({
                "inv": r.get("parent") or "",
                "po": r.get("purchase_order") or "",
                "date": sval(h.get("posting_date")),
                "vendor": h.get("supplier") or "",
                "vendor_name": h.get("supplier_name") or h.get("supplier") or "",
                "item": item_code,
                "item_name": r.get("item_name") or item_code,
                "qty": purchase_qty,
                "rate": fnum(r.get("rate")),
                "val": purchase_amount,
                "warehouse": wh,
                "status": h.get("status") or "",
                "is_return": is_return,
                "return_against": h.get("return_against") or ""
            })


        # ============================================================
        # 8. DRAFT PURCHASE INVOICES
        #    FAST MODE: not required by Stores 360 initial payload.
        # ============================================================

        draft_purchases = []


        # ============================================================
        # 8A. SUBMITTED PURCHASE INVOICE FINANCIALS
        # ============================================================

        vendor_financials = {}
        purchase_invoice_rows = []

        submitted_pi_fields = [
            "name",
            "posting_date",
            "supplier",
            "supplier_name",
            "grand_total",
            "outstanding_amount",
            "status",
            "docstatus"
        ]

        for pi_optional_field in ["due_date", "total_qty", "total_taxes_and_charges"]:
            if has_field("Purchase Invoice", pi_optional_field):
                submitted_pi_fields.append(pi_optional_field)

        submitted_pi_rows = frappe.get_all(
            "Purchase Invoice",
            filters=[
                ["docstatus", "=", 1],
                ["posting_date", ">=", from_date],
                ["posting_date", "<=", to_date]
            ],
            fields=submitted_pi_fields,
            order_by="posting_date desc, name desc",
            limit_page_length=0
        )

        for pi_row in submitted_pi_rows:
            supplier_code = pi_row.get("supplier") or ""
            grand_total = fnum(pi_row.get("grand_total"))
            outstanding = max(fnum(pi_row.get("outstanding_amount")), 0)
            paid = max(grand_total - outstanding, 0)

            purchase_invoice_rows.append({
                "inv": pi_row.get("name") or "",
                "date": sval(pi_row.get("posting_date")),
                "due_date": sval(pi_row.get("due_date")),
                "vendor": supplier_code,
                "vendor_name": pi_row.get("supplier_name") or supplier_code,
                "qty": fnum(pi_row.get("total_qty")),
                "grand_total": grand_total,
                "paid": paid,
                "due": outstanding,
                "tax": fnum(pi_row.get("total_taxes_and_charges")),
                "status": pi_row.get("status") or ""
            })

            if supplier_code:
                vf = vendor_financials.get(supplier_code)
                if not vf:
                    vf = {
                        "vendor": supplier_code,
                        "billed": 0,
                        "paid": 0,
                        "due": 0,
                        "invoices": 0,
                        "open_invoices": 0,
                        "last_invoice_date": "",
                        "next_due_date": ""
                    }
                    vendor_financials[supplier_code] = vf

                vf["billed"] = fnum(vf.get("billed")) + grand_total
                vf["paid"] = fnum(vf.get("paid")) + paid
                vf["due"] = fnum(vf.get("due")) + outstanding
                vf["invoices"] = int(vf.get("invoices") or 0) + 1
                if outstanding > 0:
                    vf["open_invoices"] = int(vf.get("open_invoices") or 0) + 1

                invoice_date = sval(pi_row.get("posting_date"))
                if invoice_date > sval(vf.get("last_invoice_date")):
                    vf["last_invoice_date"] = invoice_date

                due_date_value = sval(pi_row.get("due_date"))
                if outstanding > 0 and due_date_value:
                    current_due_date = sval(vf.get("next_due_date"))
                    if not current_due_date or due_date_value < current_due_date:
                        vf["next_due_date"] = due_date_value


        # ============================================================
        # 8B. LIFETIME SUBMITTED PURCHASE INVOICE FINANCIALS
        #     Separate from the selected report period.
        # ============================================================

        vendor_financials_lifetime = {}

        lifetime_pi_fields = [
            "name",
            "posting_date",
            "supplier",
            "grand_total",
            "outstanding_amount",
            "docstatus"
        ]

        if has_field("Purchase Invoice", "due_date"):
            lifetime_pi_fields.append("due_date")

        lifetime_pi_rows = frappe.get_all(
            "Purchase Invoice",
            filters=[["docstatus", "=", 1]],
            fields=lifetime_pi_fields,
            order_by="posting_date desc, name desc",
            limit_page_length=0
        )

        for pi_row in lifetime_pi_rows:
            supplier_code = pi_row.get("supplier") or ""
            if not supplier_code:
                continue

            grand_total = fnum(pi_row.get("grand_total"))
            outstanding = max(fnum(pi_row.get("outstanding_amount")), 0)
            paid = max(grand_total - outstanding, 0)

            vf = vendor_financials_lifetime.get(supplier_code)
            if not vf:
                vf = {
                    "vendor": supplier_code,
                    "billed": 0,
                    "paid": 0,
                    "due": 0,
                    "invoices": 0,
                    "open_invoices": 0,
                    "last_invoice_date": "",
                    "next_due_date": ""
                }
                vendor_financials_lifetime[supplier_code] = vf

            vf["billed"] = fnum(vf.get("billed")) + grand_total
            vf["paid"] = fnum(vf.get("paid")) + paid
            vf["due"] = fnum(vf.get("due")) + outstanding
            vf["invoices"] = int(vf.get("invoices") or 0) + 1

            if outstanding > 0:
                vf["open_invoices"] = int(vf.get("open_invoices") or 0) + 1

            invoice_date = sval(pi_row.get("posting_date"))
            if invoice_date > sval(vf.get("last_invoice_date")):
                vf["last_invoice_date"] = invoice_date

            due_date_value = sval(pi_row.get("due_date"))
            if outstanding > 0 and due_date_value:
                current_due_date = sval(vf.get("next_due_date"))
                if not current_due_date or due_date_value < current_due_date:
                    vf["next_due_date"] = due_date_value


        # ============================================================
        # 9. SUPPLIERS / ITEM SUPPLIERS
        # ============================================================

        supplier_fields = [
            "name",
            "supplier_name",
            "supplier_group",
            "country",
            "disabled",
            "creation"
        ]

        for supplier_optional_field in [
            "supplier_type",
            "mobile_no",
            "email_id",
            "website",
            "payment_terms",
            "on_hold",
            "custom_branch",
            "custom_area_manager",
            "custom_phone_number",
            "custom_company_number",
            "custom_dealer_number",
            "custom_relation_manager",
            "custom_rm_phone",
            "custom_whatsapp",
            "custom_with_life_from",
            "custom_payment_methods",
            "custom_materials_provided",
            "custom_alternative_vendors"
        ]:
            if has_field("Supplier", supplier_optional_field):
                supplier_fields.append(supplier_optional_field)

        suppliers_raw = frappe.get_all(
            "Supplier",
            fields=supplier_fields,
            order_by="supplier_name asc, name asc",
            limit_page_length=0
        )

        suppliers = []

        for s in suppliers_raw:
            supplier_code = s.get("name") or ""
            finance = vendor_financials.get(supplier_code) or {}
            lifetime_finance = vendor_financials_lifetime.get(supplier_code) or {}

            suppliers.append({
                "code": supplier_code,
                "name": s.get("supplier_name") or supplier_code,
                "phone": s.get("custom_phone_number") or s.get("mobile_no") or "",
                "mobile": s.get("mobile_no") or "",
                "email": s.get("email_id") or "",
                "since": sval(s.get("custom_with_life_from") or s.get("creation")),
                "city": s.get("country") or "",
                "branch": s.get("custom_branch") or "",
                "areaManager": s.get("custom_area_manager") or "",
                "rm": s.get("custom_relation_manager") or "",
                "rmPhone": s.get("custom_rm_phone") or "",
                "whatsapp": s.get("custom_whatsapp") or "",
                "terms": s.get("payment_terms") or s.get("custom_payment_methods") or "",
                "level": s.get("supplier_group") or "",
                "supplierType": s.get("supplier_type") or "",
                "website": s.get("website") or "",
                "materials": s.get("custom_materials_provided") or "",
                "rating": 0,
                "blocked": bool(s.get("disabled") or s.get("on_hold")),
                "billed": fnum(finance.get("billed")),
                "paid": fnum(finance.get("paid")),
                "due": fnum(finance.get("due")),
                "invoiceCount": int(finance.get("invoices") or 0),
                "openInvoiceCount": int(finance.get("open_invoices") or 0),
                "lastInvoiceDate": finance.get("last_invoice_date") or "",
                "nextDueDate": finance.get("next_due_date") or "",
                "lifetimeBilled": fnum(lifetime_finance.get("billed")),
                "lifetimePaid": fnum(lifetime_finance.get("paid")),
                "lifetimeDue": fnum(lifetime_finance.get("due")),
                "lifetimeInvoiceCount": int(lifetime_finance.get("invoices") or 0),
                "lifetimeOpenInvoiceCount": int(lifetime_finance.get("open_invoices") or 0),
                "lifetimeLastInvoiceDate": lifetime_finance.get("last_invoice_date") or "",
                "lifetimeNextDueDate": lifetime_finance.get("next_due_date") or ""
            })

        item_vendors = {}

        for ic in item_codes:
            item_vendors[ic] = []

        if item_codes and frappe.db.exists("DocType", "Item Supplier"):
            isup_rows = frappe.get_all(
                "Item Supplier",
                filters={"parent": ["in", item_codes]},
                fields=["parent", "supplier", "idx"],
                order_by="parent asc, idx asc",
                limit_page_length=0
            )

            for r in isup_rows:
                ic = r.get("parent")
                sp = r.get("supplier")

                if ic and sp and sp not in item_vendors.get(ic, []):
                    if ic not in item_vendors:
                        item_vendors[ic] = []
                    item_vendors[ic].append(sp)


        # ============================================================
        # 10. PURCHASE ORDER - BUSINESS MONTH 6TH TO 5TH
        # ============================================================

        today = frappe.utils.getdate(frappe.utils.today())

        if today.day >= 6:
            business_from = frappe.utils.getdate(
                str(today.year) + "-" + str(today.month).zfill(2) + "-06"
            )
        else:
            prev_month = frappe.utils.add_months(today, -1)
            business_from = frappe.utils.getdate(
                str(prev_month.year) + "-" + str(prev_month.month).zfill(2) + "-06"
            )

        business_to = frappe.utils.add_days(
            frappe.utils.add_months(business_from, 1),
            -1
        )

        po_headers = frappe.get_all(
            "Purchase Order",
            filters=[
                ["docstatus", "=", 1],
                ["transaction_date", ">=", business_from],
                ["transaction_date", "<=", business_to]
            ],
            fields=["name", "transaction_date", "supplier"],
            limit_page_length=0
        )

        po_names = [x.get("name") for x in po_headers if x.get("name")]

        po_ordered_month = {}
        po_pending_month = {}

        if po_names:
            poi_meta = frappe.get_meta("Purchase Order Item")
            poi_fields = ["parent", "item_code", "qty"]

            for f in ["received_qty", "stock_qty"]:
                if poi_meta.has_field(f):
                    poi_fields.append(f)

            po_items = frappe.get_all(
                "Purchase Order Item",
                filters={"parent": ["in", po_names]},
                fields=poi_fields,
                limit_page_length=0
            )

            for r in po_items:
                ic = r.get("item_code") or ""
                if not ic:
                    continue

                qty = fnum(r.get("qty"))
                received = fnum(r.get("received_qty"))

                po_ordered_month[ic] = po_ordered_month.get(ic, 0) + qty
                po_pending_month[ic] = po_pending_month.get(ic, 0) + max(qty - received, 0)


        # ============================================================
        # 11. CLIENT / PATIENT DATA
        # ============================================================

        client_ids = []

        for r in stock_requests:
            c = r.get("client")
            if c and c not in client_ids:
                client_ids.append(c)

        clients = []

        if client_ids and frappe.db.exists("DocType", "Patient"):
            patient_meta = frappe.get_meta("Patient")
            patient_fields = ["name"]

            for f in [
                "patient_name",
                "mobile",
                "mobile_no",
                "branch_name",
                "branch",
                "sex",
                "dob"
            ]:
                if patient_meta.has_field(f):
                    patient_fields.append(f)

            patient_rows = frappe.get_all(
                "Patient",
                filters={"name": ["in", client_ids]},
                fields=patient_fields,
                limit_page_length=0
            )

            for p in patient_rows:
                clients.append({
                    "id": p.get("name") or "",
                    "name": p.get("patient_name") or p.get("name") or "",
                    "mob": p.get("mobile") or p.get("mobile_no") or "",
                    "br": p.get("branch_name") or p.get("branch") or "",
                    "sex": p.get("sex") or "",
                    "dob": sval(p.get("dob"))
                })



        # ============================================================
        # 12. LIFE STOCK RECEIPT ADJUSTMENTS
        #     Real branch receipt / discrepancy data
        # ============================================================

        receipt_adjustments = []
        receipt_adjustment_items = []
        receipt_adjustment_map = {}

        if frappe.db.exists("DocType", "LIFE Stock Receipt Adjustment Request"):
            ar_fields = [
                "name",
                "status",
                "stock_entry",
                "material_request",
                "company",
                "source_warehouse",
                "target_warehouse",
                "target_branch",
                "reported_by",
                "reported_by_name",
                "reported_on",
                "branch_receipt_remarks",
                "evidence",
                "total_released_qty",
                "total_received_qty",
                "total_missing_qty",
                "total_damaged_qty",
                "total_return_to_source_qty",
                "stock_manager_remarks",
                "approved_by",
                "approved_on",
                "submitted_stock_entry",
                "correction_requested_by",
                "correction_requested_on",
                "rejected_by",
                "rejected_on",
                "creation",
                "modified"
            ]

            ar_filters = []

            adjustment_meta = frappe.get_meta("LIFE Stock Receipt Adjustment Request")
            if adjustment_meta.has_field("reported_on"):
                ar_filters.append(["reported_on", ">=", from_date + " 00:00:00"])
                ar_filters.append(["reported_on", "<=", to_date + " 23:59:59"])

            if branch_filter and branch_filter != "HO":
                ar_filters.append(["target_warehouse", "=", branch_filter])

            ar_headers = frappe.get_all(
                "LIFE Stock Receipt Adjustment Request",
                filters=ar_filters,
                fields=ar_fields,
                order_by="reported_on desc, modified desc",
                limit_page_length=0
            )

            ar_names = [x.get("name") for x in ar_headers if x.get("name")]

            if ar_names and frappe.db.exists("DocType", "LIFE Stock Receipt Adjustment Item"):
                ari_fields = [
                    "name",
                    "parent",
                    "idx",
                    "stock_entry_detail",
                    "item_code",
                    "item_name",
                    "uom",
                    "source_warehouse",
                    "target_warehouse",
                    "released_qty",
                    "received_qty",
                    "missing_qty",
                    "damaged_qty",
                    "return_to_source_qty",
                    "discrepancy_type",
                    "row_status",
                    "discrepancy_remarks",
                    "evidence"
                ]

                ar_items = frappe.get_all(
                    "LIFE Stock Receipt Adjustment Item",
                    filters={"parent": ["in", ar_names]},
                    fields=ari_fields,
                    order_by="parent asc, idx asc",
                    limit_page_length=0
                )
            else:
                ar_items = []

            ar_item_map = {}

            for r in ar_items:
                p = r.get("parent")
                if p not in ar_item_map:
                    ar_item_map[p] = []
                ar_item_map[p].append(r)

            for h in ar_headers:
                hname = h.get("name")
                rows = ar_item_map.get(hname, [])

                receipt_adjustments.append({
                    "name": hname or "",
                    "status": h.get("status") or "",
                    "stock_entry": h.get("stock_entry") or "",
                    "material_request": h.get("material_request") or "",
                    "company": h.get("company") or "",
                    "source_warehouse": h.get("source_warehouse") or "",
                    "target_warehouse": h.get("target_warehouse") or "",
                    "target_branch": h.get("target_branch") or "",
                    "reported_by": h.get("reported_by") or "",
                    "reported_by_name": h.get("reported_by_name") or "",
                    "reported_on": sval(h.get("reported_on")),
                    "branch_receipt_remarks": h.get("branch_receipt_remarks") or "",
                    "evidence": h.get("evidence") or "",
                    "total_released_qty": fnum(h.get("total_released_qty")),
                    "total_received_qty": fnum(h.get("total_received_qty")),
                    "total_missing_qty": fnum(h.get("total_missing_qty")),
                    "total_damaged_qty": fnum(h.get("total_damaged_qty")),
                    "total_return_to_source_qty": fnum(h.get("total_return_to_source_qty")),
                    "stock_manager_remarks": h.get("stock_manager_remarks") or "",
                    "approved_by": h.get("approved_by") or "",
                    "approved_on": sval(h.get("approved_on")),
                    "submitted_stock_entry": h.get("submitted_stock_entry") or "",
                    "correction_requested_by": h.get("correction_requested_by") or "",
                    "correction_requested_on": sval(h.get("correction_requested_on")),
                    "rejected_by": h.get("rejected_by") or "",
                    "rejected_on": sval(h.get("rejected_on")),
                    "items_count": len(rows)
                })

                for r in rows:
                    row = {
                        "adjustment_request": hname or "",
                        "status": h.get("status") or "",
                        "stock_entry": h.get("stock_entry") or "",
                        "material_request": h.get("material_request") or "",
                        "target_branch": h.get("target_branch") or "",
                        "reported_by": h.get("reported_by_name") or h.get("reported_by") or "",
                        "reported_on": sval(h.get("reported_on")),
                        "approved_by": h.get("approved_by") or "",
                        "approved_on": sval(h.get("approved_on")),
                        "stock_entry_detail": r.get("stock_entry_detail") or "",
                        "item": r.get("item_code") or "",
                        "item_name": r.get("item_name") or r.get("item_code") or "",
                        "uom": r.get("uom") or "",
                        "source_warehouse": r.get("source_warehouse") or h.get("source_warehouse") or "",
                        "target_warehouse": r.get("target_warehouse") or h.get("target_warehouse") or "",
                        "released_qty": fnum(r.get("released_qty")),
                        "received_qty": fnum(r.get("received_qty")),
                        "missing_qty": fnum(r.get("missing_qty")),
                        "damaged_qty": fnum(r.get("damaged_qty")),
                        "return_to_source_qty": fnum(r.get("return_to_source_qty")),
                        "discrepancy_type": r.get("discrepancy_type") or "",
                        "row_status": r.get("row_status") or "",
                        "remarks": r.get("discrepancy_remarks") or "",
                        "evidence": r.get("evidence") or ""
                    }

                    receipt_adjustment_items.append(row)

                    # Key by Material Request + Item so Stores 360 request lines
                    # can show real branch usable received quantity.
                    mr_key = row["material_request"] + "||" + row["item"]

                    if row["material_request"] and row["item"]:
                        receipt_adjustment_map[mr_key] = row

                    # Also key by original Stock Entry + Item as fallback.
                    se_key = row["stock_entry"] + "||" + row["item"]

                    if row["stock_entry"] and row["item"]:
                        receipt_adjustment_map[se_key] = row


        # Enrich Material Request / Stock Request rows with real receipt adjustment data.
        for r in material_requests:
            key1 = (r.get("request_id") or "") + "||" + (r.get("item") or "")
            key2 = (r.get("stock_entry") or "") + "||" + (r.get("item") or "")

            adjrow = receipt_adjustment_map.get(key1) or receipt_adjustment_map.get(key2)

            if adjrow:
                r["released_qty"] = fnum(adjrow.get("released_qty"))
                r["received_qty"] = fnum(adjrow.get("received_qty"))
                r["missing_qty"] = fnum(adjrow.get("missing_qty"))
                r["damaged_qty"] = fnum(adjrow.get("damaged_qty"))
                r["return_to_source_qty"] = fnum(adjrow.get("return_to_source_qty"))
                r["pending_receipt_qty"] = max(fnum(adjrow.get("released_qty")) - fnum(adjrow.get("received_qty")), 0)
                r["pending_qty"] = max(fnum(r.get("qty")) - fnum(adjrow.get("received_qty")), 0)
                r["receipt_adjustment"] = adjrow.get("adjustment_request") or ""
                r["receipt_status"] = adjrow.get("row_status") or adjrow.get("status") or ""
                r["discrepancy_type"] = adjrow.get("discrepancy_type") or ""
                r["discrepancy_remarks"] = adjrow.get("remarks") or ""
                r["receipt_evidence"] = adjrow.get("evidence") or ""
                r["receipt_reported_by"] = adjrow.get("reported_by") or ""
                r["receipt_reported_on"] = adjrow.get("reported_on") or ""
                r["receipt_reconciliation_diff"] = max(
                    fnum(adjrow.get("released_qty"))
                    - fnum(adjrow.get("received_qty"))
                    - fnum(adjrow.get("missing_qty"))
                    - fnum(adjrow.get("damaged_qty")),
                    0
                )

        for r in stock_requests:
            key1 = (r.get("req") or r.get("id") or "") + "||" + (r.get("item") or "")
            key2 = (r.get("stockEntry") or "") + "||" + (r.get("item") or "")

            adjrow = receipt_adjustment_map.get(key1) or receipt_adjustment_map.get(key2)

            if adjrow:
                released = fnum(adjrow.get("released_qty"))
                received = fnum(adjrow.get("received_qty"))
                missing = fnum(adjrow.get("missing_qty"))
                damaged = fnum(adjrow.get("damaged_qty"))
                returned = fnum(adjrow.get("return_to_source_qty"))
                req_qty = fnum(r.get("reqQty") or r.get("qty"))

                r["releasedQty"] = released
                r["recQty"] = received
                r["receivedQty"] = received
                r["missingQty"] = missing
                r["damagedQty"] = damaged
                r["returnQty"] = returned
                r["pendingReceiptQty"] = max(released - received, 0)
                r["pendingQty"] = max(req_qty - received, 0)
                r["receiptAdjustment"] = adjrow.get("adjustment_request") or ""
                r["receiptStatus"] = adjrow.get("row_status") or adjrow.get("status") or ""
                r["discrepancyType"] = adjrow.get("discrepancy_type") or ""
                r["discrepancyRemarks"] = adjrow.get("remarks") or ""
                r["receiptEvidence"] = adjrow.get("evidence") or ""
                r["receiptReportedBy"] = adjrow.get("reported_by") or ""
                r["receiptReportedOn"] = adjrow.get("reported_on") or ""
                r["receiptReconciliationDiff"] = max(
                    released - received - missing - damaged,
                    0
                )



        # ============================================================
        # LIVE REPORT NORMALIZATION
        # ============================================================

        # Do not treat every Material Receipt / Material Issue as damage.
        # Damage / adjustment in Stores 360 must come from the dedicated
        # LIFE Stock Receipt Adjustment workflow.
        ADJUST = []

        item_rate_map_live = {}
        for item_row_live in items:
            item_rate_map_live[item_row_live.get("code")] = fnum(item_row_live.get("rate"))

        for receipt_row_live in receipt_adjustment_items:
            missing_qty_live = fnum(receipt_row_live.get("missing_qty"))
            damaged_qty_live = fnum(receipt_row_live.get("damaged_qty"))
            adjust_qty_live = missing_qty_live + damaged_qty_live

            if adjust_qty_live <= 0:
                continue

            item_code_live = receipt_row_live.get("item") or ""
            item_rate_live = fnum(item_rate_map_live.get(item_code_live))

            ADJUST.append({
                "aid": receipt_row_live.get("adjustment_request") or "",
                "ref": receipt_row_live.get("stock_entry") or "",
                "date": (receipt_row_live.get("reported_on") or "")[:10],
                "item": item_code_live,
                "item_name": receipt_row_live.get("item_name") or item_code_live,
                "loc": receipt_row_live.get("target_warehouse") or "",
                "qty": adjust_qty_live,
                "rate": item_rate_live,
                "val": adjust_qty_live * item_rate_live,
                "missing_qty": missing_qty_live,
                "damaged_qty": damaged_qty_live,
                "reason": receipt_row_live.get("discrepancy_type") or "Stock discrepancy",
                "approvedBy": receipt_row_live.get("approved_by") or "",
                "approved_by": receipt_row_live.get("approved_by") or "",
                "status": receipt_row_live.get("row_status") or receipt_row_live.get("status") or "Adjusted",
                "row_status": receipt_row_live.get("row_status") or "",
                "remarks": receipt_row_live.get("remarks") or "",
                "evidence": receipt_row_live.get("evidence") or ""
            })


        # Add the fields expected by the existing Stores 360 renderer.
        for dispatch_row_live in dispatch:
            if not dispatch_row_live.get("ind"):
                dispatch_row_live["ind"] = dispatch_row_live.get("material_request") or dispatch_row_live.get("ref") or ""
            if not dispatch_row_live.get("challan"):
                dispatch_row_live["challan"] = dispatch_row_live.get("ref") or ""
            if not dispatch_row_live.get("reqDate"):
                dispatch_row_live["reqDate"] = dispatch_row_live.get("date") or ""
            if dispatch_row_live.get("reqQty") is None:
                dispatch_row_live["reqQty"] = fnum(dispatch_row_live.get("qty"))
            if not dispatch_row_live.get("priority"):
                dispatch_row_live["priority"] = "Normal"
            if dispatch_row_live.get("takenD") is None:
                dispatch_row_live["takenD"] = 0
            if dispatch_row_live.get("takenH") is None:
                dispatch_row_live["takenH"] = 0
            if not dispatch_row_live.get("status"):
                dispatch_row_live["status"] = "Received"
            if not dispatch_row_live.get("recvDate"):
                dispatch_row_live["recvDate"] = dispatch_row_live.get("date") or ""
            if not dispatch_row_live.get("recvTime"):
                dispatch_row_live["recvTime"] = dispatch_row_live.get("time") or ""
            if not dispatch_row_live.get("recvBy"):
                dispatch_row_live["recvBy"] = dispatch_row_live.get("modified_by") or ""


        for receipt_row_live in returns:
            if not receipt_row_live.get("rid"):
                receipt_row_live["rid"] = receipt_row_live.get("ref") or ""
            if not receipt_row_live.get("reason"):
                receipt_row_live["reason"] = "Returned to HO"
            if not receipt_row_live.get("cond"):
                receipt_row_live["cond"] = "Good — restocked"
            if not receipt_row_live.get("status"):
                receipt_row_live["status"] = "Accepted"
            if not receipt_row_live.get("recvBy"):
                receipt_row_live["recvBy"] = receipt_row_live.get("modified_by") or ""


        for purchase_row_live in purchases:
            if purchase_row_live.get("tax") is None:
                purchase_row_live["tax"] = 0
            if purchase_row_live.get("gt") is None:
                purchase_row_live["gt"] = fnum(purchase_row_live.get("val"))
            if purchase_row_live.get("paid") is None:
                purchase_row_live["paid"] = 0
            if purchase_row_live.get("due") is None:
                purchase_row_live["due"] = max(fnum(purchase_row_live.get("gt")) - fnum(purchase_row_live.get("paid")), 0)

            grand_total_live = fnum(purchase_row_live.get("gt"))
            paid_total_live = fnum(purchase_row_live.get("paid"))

            if grand_total_live > 0 and paid_total_live >= grand_total_live:
                purchase_row_live["payStatus"] = "Paid"
            elif paid_total_live > 0:
                purchase_row_live["payStatus"] = "Partial"
            else:
                purchase_row_live["payStatus"] = "Unpaid"

            purchase_row_live["qc"] = purchase_row_live.get("qc") or "Received"
            purchase_row_live["grn"] = purchase_row_live.get("grn") or purchase_row_live.get("inv") or ""
            purchase_row_live["recvDate"] = purchase_row_live.get("recvDate") or purchase_row_live.get("date") or ""
            purchase_row_live["recvBy"] = purchase_row_live.get("recvBy") or ""


        # ============================================================
        # 13. LIFE STOCK REQUEST SETTINGS
        # ============================================================

        life_stock_settings = {
            "enable_monthly_indent_exception": 0
        }

        if frappe.db.exists("DocType", "LIFE Stock Request Settings"):
            try:
                life_stock_settings["enable_monthly_indent_exception"] = int(
                    frappe.db.get_single_value(
                        "LIFE Stock Request Settings",
                        "enable_monthly_indent_exception"
                    ) or 0
                )
            except:
                life_stock_settings["enable_monthly_indent_exception"] = 0


        # ============================================================
        # 14. STOCK LEDGER SUMMARY
        #     FAST MODE: not loaded on the normal Stores 360 dashboard.
        #     Stock Ledger is a very large table and was adding seconds
        #     to every refresh although the current UI does not use it.
        # ============================================================

        stock_ledger_summary = []


        # ============================================================
        # CURRENT LOGGED-IN USER
        # ============================================================

        current_user_id = sval(frappe.session.user)

        current_user_info = {
            "email": current_user_id,
            "full_name": current_user_id,
            "employee": "",
            "employee_name": "",
            "designation": "",
            "branch": "",
            "user_image": ""
        }

        if current_user_id and current_user_id != "Guest":

            user_row = frappe.db.get_value(
                "User",
                current_user_id,
                ["full_name", "user_image"],
                as_dict=True
            ) or {}

            current_user_info["full_name"] = (
                sval(user_row.get("full_name"))
                or current_user_id
            )

            current_user_info["user_image"] = sval(
                user_row.get("user_image")
            )

            employee_row = frappe.db.get_value(
                "Employee",
                {
                    "user_id": current_user_id,
                    "status": "Active"
                },
                ["name", "employee_name", "designation", "branch"],
                as_dict=True
            ) or {}

            if employee_row:

                current_user_info["employee"] = sval(
                    employee_row.get("name")
                )

                current_user_info["employee_name"] = sval(
                    employee_row.get("employee_name")
                )

                current_user_info["designation"] = sval(
                    employee_row.get("designation")
                )

                current_user_info["branch"] = sval(
                    employee_row.get("branch")
                )

                if current_user_info["employee_name"]:
                    current_user_info["full_name"] = (
                        current_user_info["employee_name"]
                    )


        # ============================================================
        # 15. RESPONSE
        # ============================================================

        frappe.response["message"] = {
            "meta": {
                "from_date": sval(from_date),
                "to_date": sval(to_date),
                "business_from": sval(business_from),
                "business_to": sval(business_to),
                "ho_warehouse": HO_WH,
                "ho_wh": HO_WH,
                "categories": categories,
                "cats": categories,
                "counts": {
                    "branches": len(branches),
                    "items": len(items),
                    "stock_request_lines": len(stock_requests),
                    "stock_dispatch_lines": len(dispatch),
                    "stock_return_lines": len(returns),
                    "branch_consumption_lines": len(consumption),
                    "stock_adjustment_lines": len(adjust),
                    "purchase_lines": len(purchases),
                    "clients": len(clients)
                },
                "fast_mode": 1,
                "version": "V25_REAL_BRANCH_CONSUMPTION"
            },

            "current_user": current_user_info,

            "branches": branches,
            "items": items,
            "suppliers": suppliers,
            "item_vendors": item_vendors,

            "ho_stock": ho_stock,
            "branch_stock": branch_stock,

            "stock_requests": stock_requests,

            "dispatch": dispatch,
            "returns": returns,
            "consumption": consumption,
            "adjust": adjust,

            "purchases": purchases,
            "lifetime_purchases": lifetime_purchases,
            "purchase_invoices": purchase_invoice_rows,
            "vendor_financials": vendor_financials,
            "vendor_financials_lifetime": vendor_financials_lifetime,

            "clients": clients,

            "data_quality": {
                "requested_qty": "Material Request Item.qty",
                "released_qty": "Submitted Stock Entry Detail.qty",
                "received_qty": "Stock Entry Detail.custom_received_qty only after branch receipt confirmation",
                "missing_damaged_return": "LIFE Stock Receipt Adjustment Item",
                "execution_status": "Therapy Session counts are not converted to item quantity. Consumed Qty uses only submitted branch Material Issue Stock Entry Detail.qty.",
                "vendor_financials": "Selected-period submitted Purchase Invoice grand_total/outstanding_amount",
                "vendor_financials_lifetime": "All submitted Purchase Invoice grand_total/outstanding_amount",
                "historical_consumption": "Submitted Material Issue Stock Entry Detail.qty from branch warehouse with no target warehouse; no inferred consumption",
                "approved_qty": "Material Request Item.custom_approved_qty",
                "purchase_qty": "Submitted Purchase Receipt Item.qty; Purchase Returns deducted",
            "receipt_diff": "Released - Received - Missing - Damaged, only after receipt evidence exists"
            }
        }
