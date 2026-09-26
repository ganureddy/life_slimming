"""md_360_api

Original API: md_360_api
Source modified: 2026-08-02 11:45:46.296722
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
    #  SERVER SCRIPT (API)  —  md_360_api  (v2 — full Vendor 360)
    #  Script Type : API   ·   API Method : md_360_api
    #
    #  /api/method/md_360_api?type=search&q=...
    #  /api/method/md_360_api?type=item&code=ITEM-CODE
    #  /api/method/md_360_api?type=vendor&code=SUPPLIER-NAME
    #
    #  Vendor 360 now mirrors the demo report using REAL fields:
    #   - Profile: Supplier's custom_* fields (branch, area manager, phone,
    #     relation manager, bank details, HO/local address, "with LIFE
    #     from", payment methods, materials provided, preference rank) plus
    #     standard gstin/pan/mobile_no/email_id.
    #   - Items Supplied: from Purchase Invoice Item, split into HO stock
    #     (warehouse LIKE '%Stores%') vs Branch stock (everything else),
    #     using live Bin data.
    #   - Payment Ledger: one row per Purchase Invoice with GST estimated
    #     as grand_total - base_net_total (works for tax-inclusive setups).
    #   - Payments Released: real Payment Entry Reference rows against this
    #     supplier's invoices (date, mode, reference no, allocated amount).
    #   - Branch Ranking / "Where material goes": Stock Entry (Material
    #     Transfer) rows moving this vendor's items out to branch
    #     warehouses — a genuine proxy for consumption, since Purchase
    #     Invoices land centrally at Stores first.
    #   - Timeline: merges Purchase (invoice) events and Dispatch (transfer)
    #     events, sorted by date.
    #
    #  NOT included — no matching real doctype: "Complaints" and "Returns"
    #  reason codes (e.g. "Damaged packing", "Near expiry") from the demo
    #  report are fictional; nothing in your system tracks that per-vendor
    #  today. Tell me the doctype if you have one and I'll wire it in.
    #
    #  REPLACE the existing md_360_api Server Script's `script` field with
    #  this file's contents to upgrade it in place.
    # =====================================================================

    args = frappe.form_dict or {}
    qtype = (args.get("type") or "").strip()
    code = (args.get("code") or "").strip()
    q = (args.get("q") or "").strip()

    out = {"type": qtype}


    def is_ho(warehouse):
        return bool(warehouse) and "stores" in warehouse.lower()


    if qtype == "search":
        like = "%" + q + "%"
        items = _read_sql("""
        SELECT item_code, item_name, item_group, stock_uom
        FROM `tabItem`
        WHERE disabled = 0 AND (item_code LIKE %(l)s OR item_name LIKE %(l)s)
        ORDER BY item_name LIMIT 15
    """, {"l": like}, as_dict=True)
        suppliers = _read_sql("""
        SELECT name, supplier_name, supplier_group
        FROM `tabSupplier`
        WHERE disabled = 0 AND (name LIKE %(l)s OR supplier_name LIKE %(l)s)
        ORDER BY supplier_name LIMIT 15
    """, {"l": like}, as_dict=True)
        out["items"] = items
        out["suppliers"] = suppliers

    elif qtype == "item":
        item_doc = frappe.db.get_value(
            "Item", code, ["item_code", "item_name", "item_group", "stock_uom", "description"], as_dict=True
        )
        stock_by_wh = _read_sql("""
        SELECT warehouse, actual_qty, reserved_qty, projected_qty
        FROM `tabBin`
        WHERE item_code = %(c)s AND actual_qty != 0
        ORDER BY actual_qty DESC
    """, {"c": code}, as_dict=True)
        total_qty = sum(float(r.get("actual_qty") or 0) for r in stock_by_wh)

        purchase_hist = _read_sql("""
        SELECT pi.name AS invoice, pi.posting_date AS date, pi.supplier AS supplier,
               pii.qty AS qty, pii.rate AS rate, pii.amount AS amount, pii.warehouse AS warehouse
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pii.item_code = %(c)s AND pi.docstatus = 1
        ORDER BY pi.posting_date DESC LIMIT 40
    """, {"c": code}, as_dict=True)

        top_vendors = _read_sql("""
        SELECT pi.supplier AS supplier, COUNT(DISTINCT pi.name) AS invoices,
               SUM(pii.qty) AS qty, SUM(pii.amount) AS amount
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pii.item_code = %(c)s AND pi.docstatus = 1
        GROUP BY pi.supplier ORDER BY amount DESC LIMIT 10
    """, {"c": code}, as_dict=True)

        movement = _read_sql("""
        SELECT posting_date, voucher_type, voucher_no, warehouse, actual_qty, qty_after_transaction
        FROM `tabStock Ledger Entry`
        WHERE item_code = %(c)s AND is_cancelled = 0
        ORDER BY posting_date DESC, creation DESC LIMIT 40
    """, {"c": code}, as_dict=True)

        out["item"] = item_doc
        out["stock_by_warehouse"] = stock_by_wh
        out["total_qty"] = total_qty
        out["purchase_history"] = purchase_hist
        out["top_vendors"] = top_vendors
        out["movement"] = movement

    elif qtype == "vendor":
      try:
        # ---------- Profile (all real Supplier fields) ----------
        profile = frappe.db.get_value("Supplier", code, [
            "name", "supplier_name", "supplier_group", "supplier_type", "gstin", "pan",
            "mobile_no", "email_id", "on_hold", "disabled",
            "custom_branch", "custom_area_manager", "custom_phone_number", "custom_company_number",
            "custom_dealer_number", "custom_relation_manager", "custom_rm_phone", "custom_whatsapp",
            "custom_bank_name", "custom_account_number", "custom_ifsc_code", "custom_bank_branch",
            "custom_ho_address", "custom_local_address", "custom_with_life_from",
            "custom_payment_methods", "custom_materials_provided", "custom_preference_rank"
        ], as_dict=True)

        vendor_age = None
        if profile and profile.get("custom_with_life_from"):
            start = profile["custom_with_life_from"]
            if isinstance(start, str):
                start = frappe.utils.getdate(start)
            today = frappe.utils.getdate()
            years = today.year - start.year - ((today.month, today.day) < (start.month, start.day))
            months = (today.month - start.month) % 12
            vendor_age = str(years) + "y " + str(months) + "m"

        # ---------- Summary ----------
        summary = _read_sql("""
        SELECT COUNT(name) AS cnt, SUM(grand_total) AS amt, SUM(outstanding_amount) AS outs
        FROM `tabPurchase Invoice`
        WHERE supplier = %(c)s AND docstatus = 1
    """, {"c": code}, as_dict=True)
        summary = summary[0] if summary else {"cnt": 0, "amt": 0, "outs": 0}
        po_count = frappe.db.count("Purchase Order", {"supplier": code, "docstatus": 1})
        qty_supplied_rows = _read_sql("""
        SELECT SUM(pii.qty) AS q FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.supplier = %(c)s AND pi.docstatus = 1
    """, {"c": code}, as_dict=True)
        qty_supplied = float((qty_supplied_rows[0].get("q") if qty_supplied_rows else 0) or 0)

        # ---------- Items Supplied (HO vs Branch stock split) ----------
        items_raw = _read_sql("""
        SELECT pii.item_code AS item_code, pii.item_name AS item_name, it.item_group AS category,
               SUM(pii.qty) AS qty, SUM(pii.amount) AS amount, COUNT(DISTINCT pi.name) AS invoices,
               MAX(pi.posting_date) AS last_supply
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        LEFT JOIN `tabItem` it ON it.item_code = pii.item_code
        WHERE pi.supplier = %(c)s AND pi.docstatus = 1
        GROUP BY pii.item_code, pii.item_name, it.item_group
        ORDER BY amount DESC LIMIT 40
    """, {"c": code}, as_dict=True)

        item_codes = []
        for r in items_raw:
            if r.get("item_code"):
                item_codes.append(r["item_code"])

        last_rate_map = {}
        bin_map = {}
        if item_codes:
            rates = _read_sql("""
            SELECT pii.item_code AS item_code, pii.rate AS rate, pi.posting_date AS date
            FROM `tabPurchase Invoice Item` pii
            JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
            WHERE pi.supplier = %(c)s AND pi.docstatus = 1 AND pii.item_code IN %(items)s
            ORDER BY pi.posting_date DESC
        """, {"c": code, "items": tuple(item_codes)}, as_dict=True)
            for r in rates:
                if r["item_code"] not in last_rate_map:
                    last_rate_map[r["item_code"]] = r["rate"]

            bins = _read_sql("""
            SELECT item_code, warehouse, actual_qty FROM `tabBin`
            WHERE item_code IN %(items)s AND actual_qty != 0
        """, {"items": tuple(item_codes)}, as_dict=True)
            for r in bins:
                m = bin_map.setdefault(r["item_code"], {"ho": 0.0, "branch": 0.0, "value": 0.0})
                if is_ho(r["warehouse"]):
                    m["ho"] = m["ho"] + float(r["actual_qty"] or 0)
                else:
                    m["branch"] = m["branch"] + float(r["actual_qty"] or 0)

        items_supplied = []
        for r in items_raw:
            bm = bin_map.get(r["item_code"], {"ho": 0.0, "branch": 0.0})
            rate = float(last_rate_map.get(r["item_code"]) or 0)
            items_supplied.append({
                "item_code": r["item_code"], "item_name": r["item_name"], "category": r.get("category"),
                "invoices": int(r.get("invoices") or 0), "qty": float(r.get("qty") or 0),
                "amount": float(r.get("amount") or 0), "last_rate": rate,
                "last_supply": r.get("last_supply"),
                "ho_stock": bm["ho"], "branch_stock": bm["branch"],
                "stock_worth": (bm["ho"] + bm["branch"]) * rate
            })

        # ---------- Payment Ledger (one row per invoice, GST estimated) ----------
        ledger = _read_sql("""
        SELECT pi.name AS invoice, pi.posting_date AS date, pi.due_date AS due_date,
               pi.grand_total AS invoice_total, pi.base_net_total AS taxable,
               pi.outstanding_amount AS due, pi.status AS status,
               (pi.grand_total - pi.outstanding_amount) AS paid,
               GROUP_CONCAT(DISTINCT pii.item_code SEPARATOR ', ') AS items,
               SUM(pii.qty) AS qty
        FROM `tabPurchase Invoice` pi
        JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
        WHERE pi.supplier = %(c)s AND pi.docstatus = 1
        GROUP BY pi.name
        ORDER BY pi.posting_date DESC LIMIT 60
    """, {"c": code}, as_dict=True)
        for r in ledger:
            r["gst"] = float(r.get("invoice_total") or 0) - float(r.get("taxable") or 0)
            r["po"] = ""

        # ---------- Payments Released ----------
        payments = _read_sql("""
        SELECT pe.posting_date AS date, pe.name AS payment_no, per.reference_name AS against_invoice,
               per.allocated_amount AS amount, pe.mode_of_payment AS mode, pe.reference_no AS reference
        FROM `tabPayment Entry Reference` per
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE pe.docstatus = 1 AND pe.party_type = 'Supplier' AND pe.party = %(c)s
              AND per.reference_doctype = 'Purchase Invoice'
        ORDER BY pe.posting_date DESC LIMIT 60
    """, {"c": code}, as_dict=True)

        # ---------- Branch Ranking: where this vendor's material goes ----------
        branch_rank = []
        branch_detail = []
        if item_codes:
            transfers = _read_sql("""
            SELECT se.to_warehouse AS warehouse, SUM(sed.qty) AS qty, SUM(sed.basic_amount) AS amount
            FROM `tabStock Entry Detail` sed
            JOIN `tabStock Entry` se ON se.name = sed.parent
            WHERE se.docstatus = 1 AND se.stock_entry_type = 'Material Transfer'
                  AND se.to_warehouse IS NOT NULL AND sed.item_code IN %(items)s
            GROUP BY se.to_warehouse ORDER BY qty DESC LIMIT 20
        """, {"items": tuple(item_codes)}, as_dict=True)
            inhand = _read_sql("""
            SELECT warehouse, SUM(actual_qty) AS qty FROM `tabBin`
            WHERE item_code IN %(items)s AND actual_qty > 0 GROUP BY warehouse
        """, {"items": tuple(item_codes)}, as_dict=True)
            inhand_map = {}
            for r in inhand:
                inhand_map[r["warehouse"]] = float(r["qty"] or 0)

            idx = 0
            for r in transfers:
                idx = idx + 1
                wh = r["warehouse"]
                branch_rank.append({
                    "rank": idx, "branch": wh, "qty": float(r.get("qty") or 0),
                    "amount": float(r.get("amount") or 0)
                })
                branch_detail.append({
                    "rank": idx, "branch": wh, "qty_received": float(r.get("qty") or 0),
                    "value": float(r.get("amount") or 0), "in_hand_now": inhand_map.get(wh, 0.0)
                })

        # ---------- Timeline: merge purchases + dispatches ----------
        timeline = []
        for r in ledger[:30]:
            due_txt = "Rs " + str(int(r.get("due") or 0))
            purchased_text = ("Purchased " + str(int(r.get("qty") or 0)) + " qty across " +
                str(r.get("items") or "items") + " — invoice " + str(r["invoice"]) +
                " (" + str(r["status"]) + ", due " + due_txt + ")")
            timeline.append({
                "date": r["date"], "type": "purchase",
                "text": purchased_text
            })
        if item_codes:
            dispatches = _read_sql("""
            SELECT se.posting_date AS date, se.to_warehouse AS warehouse, se.name AS voucher,
                   SUM(sed.qty) AS qty, SUM(sed.basic_amount) AS amount
            FROM `tabStock Entry Detail` sed
            JOIN `tabStock Entry` se ON se.name = sed.parent
            WHERE se.docstatus = 1 AND se.stock_entry_type = 'Material Transfer'
                  AND se.to_warehouse IS NOT NULL AND sed.item_code IN %(items)s
            GROUP BY se.name, se.posting_date, se.to_warehouse
            ORDER BY se.posting_date DESC LIMIT 30
        """, {"items": tuple(item_codes)}, as_dict=True)
            for r in dispatches:
                amt_txt = "Rs " + str(int(r.get("amount") or 0))
                sent_text = ("Sent " + str(int(r.get("qty") or 0)) + " to " + str(r.get("warehouse")) +
                    " — " + amt_txt + " (" + str(r.get("voucher")) + ")")
                timeline.append({
                    "date": r["date"], "type": "dispatch",
                    "text": sent_text
                })

        def sort_key(ev):
            return str(ev["date"] or "")

        timeline_sorted = sorted(timeline, key=sort_key, reverse=True)
        timeline_sorted = timeline_sorted[:60]

        out["profile"] = profile
        out["vendor_age"] = vendor_age
        out["summary"] = {
            "po_count": po_count, "invoice_count": int(summary.get("cnt") or 0),
            "qty_supplied": qty_supplied, "invoice_value": float(summary.get("amt") or 0),
            "paid": float(summary.get("amt") or 0) - float(summary.get("outs") or 0),
            "due": float(summary.get("outs") or 0)
        }
        out["items_supplied"] = items_supplied
        out["payment_ledger"] = ledger
        out["payments_released"] = payments
        out["branch_ranking"] = branch_rank
        out["branch_detail"] = branch_detail
        out["timeline"] = timeline_sorted
      except Exception as e:
        out["error"] = str(e)

    else:
        out["error"] = "type must be one of: search, item, vendor"

    frappe.response["message"] = out
