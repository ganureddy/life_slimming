"""stock_indent_360_api

Original API: stock_indent_360_api
Source modified: 2026-09-12 16:27:18.283592
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
    # LIFE Indent & Stock Report 360 - Live Data API

    args = frappe.form_dict or {}

    from_date = args.get("from_date") or frappe.utils.add_days(frappe.utils.today(), -365)
    to_date = args.get("to_date") or frappe.utils.today()
    branch_filter = (args.get("branch") or "").strip()
    item_group_filter = (args.get("item_group") or "").strip()

    HO_WH = "Stores - LSACPL"

    def fnum(v):
        try:
            return float(v or 0)
        except:
            return 0.0

    def clean(v):
        return v if v is not None else ""

    warehouse_rows = _read_sql("""
    SELECT name, warehouse_name, parent_warehouse, is_group, disabled
    FROM `tabWarehouse`
    WHERE IFNULL(disabled,0)=0
      AND IFNULL(is_group,0)=0
      AND name != %(ho)s
      AND LOWER(name) NOT LIKE '%%testing%%'
      AND LOWER(IFNULL(warehouse_name,'')) NOT LIKE '%%testing%%'
    ORDER BY warehouse_name, name
""", {"ho": HO_WH}, as_dict=True)

    branches = []
    for w in warehouse_rows:
        branches.append({
            "code": w.name,
            "name": w.warehouse_name or w.name,
            "city": ""
        })

    item_where = """
    IFNULL(i.disabled,0)=0
    AND IFNULL(i.is_stock_item,0)=1
"""
    item_vals = {}

    if item_group_filter:
        item_where += " AND (i.item_group=%(item_group)s OR i.custom_main_category=%(item_group)s)"
        item_vals["item_group"] = item_group_filter

    item_rows = _read_sql("""
    SELECT
        i.item_code,
        i.item_name,
        i.item_group,
        i.custom_main_category,
        i.custom_stock_type,
        i.stock_uom,
        i.valuation_rate,
        i.last_purchase_rate,
        i.safety_stock
    FROM `tabItem` i
    WHERE {where}
    ORDER BY i.item_name
""".format(where=item_where), item_vals, as_dict=True)

    items = []
    item_codes = []

    for i in item_rows:
        item_codes.append(i.item_code)
        items.append({
            "code": i.item_code,
            "name": i.item_name or i.item_code,
            "cat": i.custom_main_category or i.item_group or "",
            "type": i.custom_stock_type or "",
            "unit": i.stock_uom or "Nos",
            "rate": fnum(i.last_purchase_rate) or fnum(i.valuation_rate),
            "rl": fnum(i.safety_stock)
        })

    cats = []
    for i in items:
        c = i.get("cat")
        if c and c not in cats:
            cats.append(c)
    cats.sort()

    ho_stock = {}
    branch_stock = {}

    if item_codes:
        bin_rows = _read_sql("""
        SELECT b.item_code, b.warehouse, SUM(IFNULL(b.actual_qty,0)) AS actual_qty
        FROM `tabBin` b
        WHERE b.item_code IN %(items)s
        GROUP BY b.item_code, b.warehouse
    """, {"items": tuple(item_codes)}, as_dict=True)

        allowed_branch_codes = {}
        for b in branches:
            allowed_branch_codes[b["code"]] = 1

        for r in bin_rows:
            ic = r.item_code
            wh = r.warehouse
            qty = fnum(r.actual_qty)

            if wh == HO_WH:
                ho_stock[ic] = qty
            elif allowed_branch_codes.get(wh):
                if ic not in branch_stock:
                    branch_stock[ic] = {}
                branch_stock[ic][wh] = qty

    for ic in item_codes:
        if ic not in ho_stock:
            ho_stock[ic] = 0
        if ic not in branch_stock:
            branch_stock[ic] = {}

    mr_where = """
    mr.transaction_date BETWEEN %(from_date)s AND %(to_date)s
    AND mr.docstatus < 2
"""
    mr_vals = {"from_date": from_date, "to_date": to_date}

    if branch_filter:
        if branch_filter == "HO":
            mr_where += " AND mr.set_from_warehouse=%(ho)s"
            mr_vals["ho"] = HO_WH
        else:
            mr_where += " AND (mr.set_warehouse=%(branch)s OR mr.set_from_warehouse=%(branch)s)"
            mr_vals["branch"] = branch_filter

    if item_group_filter:
        mr_where += """
        AND EXISTS (
            SELECT 1
            FROM `tabMaterial Request Item` mri2
            INNER JOIN `tabItem` it2 ON it2.item_code=mri2.item_code
            WHERE mri2.parent=mr.name
              AND (it2.item_group=%(item_group)s OR it2.custom_main_category=%(item_group)s)
        )
    """
        mr_vals["item_group"] = item_group_filter

    mr_rows = _read_sql("""
    SELECT
        mr.name,
        mr.transaction_date,
        mr.schedule_date,
        mr.material_request_type,
        mr.status,
        mr.workflow_state,
        mr.set_from_warehouse,
        mr.set_warehouse,
        mr.custom_client_name,
        mr.custom_therapy_id,
        mr.custom_material_request_by,
        mr.custom_priority,
        mr.custom_stock_request_type,
        mr.custom_stock_request_status,
        mr.custom_stock_entry_reference,
        mr.custom_patient_appointment,
        mr.custom_expected_client_name,
        mr.custom_expected_client_phone,
        mr.custom_expected_joining_date,
        mr.custom_expected_treatment_category,
        mr.custom_expected_sessions,
        mri.item_code,
        mri.item_name,
        mri.qty,
        mri.stock_uom,
        IFNULL(mri.ordered_qty,0) AS ordered_qty,
        IFNULL(mri.received_qty,0) AS received_qty
    FROM `tabMaterial Request` mr
    INNER JOIN `tabMaterial Request Item` mri ON mri.parent=mr.name
    WHERE {where}
    ORDER BY mr.transaction_date DESC, mr.name DESC, mri.idx
""".format(where=mr_where), mr_vals, as_dict=True)

    material_requests = []
    for r in mr_rows:
        material_requests.append({
            "request_id": r.name,
            "date": str(r.transaction_date or ""),
            "required_by": str(r.schedule_date or ""),
            "purpose": clean(r.material_request_type),
            "status": clean(r.custom_stock_request_status or r.workflow_state or r.status),
            "erp_status": clean(r.status),
            "workflow_state": clean(r.workflow_state),
            "source_warehouse": clean(r.set_from_warehouse),
            "target_warehouse": clean(r.set_warehouse),
            "branch": clean(r.set_warehouse),
            "client": clean(r.custom_client_name),
            "therapy_id": clean(r.custom_therapy_id),
            "request_by": clean(r.custom_material_request_by),
            "priority": clean(r.custom_priority) or "Normal",
            "request_type": clean(r.custom_stock_request_type),
            "stock_entry": clean(r.custom_stock_entry_reference),
            "appointment": clean(r.custom_patient_appointment),
            "expected_client": clean(r.custom_expected_client_name),
            "expected_phone": clean(r.custom_expected_client_phone),
            "expected_joining_date": str(r.custom_expected_joining_date or ""),
            "expected_treatment_category": clean(r.custom_expected_treatment_category),
            "expected_sessions": fnum(r.custom_expected_sessions),
            "item": r.item_code,
            "item_name": r.item_name or r.item_code,
            "qty": fnum(r.qty),
            "ordered_qty": fnum(r.ordered_qty),
            "received_qty": fnum(r.received_qty),
            "unit": clean(r.stock_uom)
        })

    se_where = """
    se.docstatus=1
    AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
"""
    se_vals = {"from_date": from_date, "to_date": to_date}

    if branch_filter and branch_filter != "HO":
        se_where += " AND (sed.s_warehouse=%(branch)s OR sed.t_warehouse=%(branch)s)"
        se_vals["branch"] = branch_filter

    stock_entry_rows = _read_sql("""
    SELECT
        se.name,
        se.posting_date,
        se.posting_time,
        se.stock_entry_type,
        se.purpose,
        se.material_request,
        sed.item_code,
        sed.item_name,
        sed.qty,
        sed.basic_rate,
        sed.basic_amount,
        sed.s_warehouse,
        sed.t_warehouse
    FROM `tabStock Entry` se
    INNER JOIN `tabStock Entry Detail` sed ON sed.parent=se.name
    WHERE {where}
    ORDER BY se.posting_date DESC, se.posting_time DESC, se.name DESC, sed.idx
""".format(where=se_where), se_vals, as_dict=True)

    dispatch = []
    returns = []
    adjust = []

    for r in stock_entry_rows:
        q = fnum(r.qty)
        rate = fnum(r.basic_rate)
        val = fnum(r.basic_amount) or q * rate
        src = clean(r.s_warehouse)
        tgt = clean(r.t_warehouse)

        base = {
            "ref": r.name,
            "date": str(r.posting_date or ""),
            "time": str(r.posting_time or ""),
            "item": r.item_code,
            "item_name": r.item_name or r.item_code,
            "qty": q,
            "rate": rate,
            "val": val,
            "source": src,
            "target": tgt,
            "material_request": clean(r.material_request),
            "entry_type": clean(r.stock_entry_type or r.purpose)
        }

        if src == HO_WH and tgt and tgt != HO_WH:
            x = dict(base)
            x["branch"] = tgt
            x["reqQty"] = q
            x["reqDate"] = str(r.posting_date or "")
            x["reqBy"] = ""
            x["recvDate"] = str(r.posting_date or "")
            x["recvTime"] = str(r.posting_time or "")
            x["recvBy"] = ""
            x["priority"] = "Normal"
            x["takenD"] = 0
            x["takenH"] = 0
            x["status"] = "Received"
            dispatch.append(x)
        elif tgt == HO_WH and src and src != HO_WH:
            x = dict(base)
            x["branch"] = src
            returns.append(x)
        elif src and tgt and src != tgt:
            x = dict(base)
            x["branch"] = tgt
            x["reqQty"] = q
            x["reqDate"] = str(r.posting_date or "")
            x["reqBy"] = ""
            x["recvDate"] = str(r.posting_date or "")
            x["recvTime"] = str(r.posting_time or "")
            x["recvBy"] = ""
            x["priority"] = "Normal"
            x["takenD"] = 0
            x["takenH"] = 0
            x["status"] = "Received"
            dispatch.append(x)
        else:
            x = dict(base)
            x["loc"] = tgt or src
            adjust.append(x)

    purchase_rows = _read_sql("""
    SELECT
        pr.name AS receipt,
        pr.posting_date,
        pr.supplier,
        pr.supplier_name,
        pri.purchase_order,
        pri.item_code,
        pri.item_name,
        pri.qty,
        pri.rate,
        pri.amount,
        pri.warehouse
    FROM `tabPurchase Receipt` pr
    INNER JOIN `tabPurchase Receipt Item` pri ON pri.parent=pr.name
    WHERE pr.docstatus=1
      AND pr.posting_date BETWEEN %(from_date)s AND %(to_date)s
    ORDER BY pr.posting_date DESC, pr.name DESC, pri.idx
""", {"from_date": from_date, "to_date": to_date}, as_dict=True)

    purchases = []
    for r in purchase_rows:
        purchases.append({
            "inv": r.receipt,
            "po": clean(r.purchase_order),
            "date": str(r.posting_date or ""),
            "vendor": clean(r.supplier),
            "vendor_name": clean(r.supplier_name or r.supplier),
            "item": r.item_code,
            "item_name": r.item_name or r.item_code,
            "qty": fnum(r.qty),
            "rate": fnum(r.rate),
            "val": fnum(r.amount),
            "gt": fnum(r.amount),
            "paid": 0,
            "due": 0,
            "warehouse": clean(r.warehouse)
        })

    draft_pi_rows = _read_sql("""
    SELECT
        pi.name,
        pi.posting_date,
        pi.supplier,
        pi.supplier_name,
        IFNULL(pi.total_qty,0) AS total_qty,
        IFNULL(pi.grand_total,0) AS grand_total,
        IFNULL(pi.total_taxes_and_charges,0) AS tax
    FROM `tabPurchase Invoice` pi
    WHERE pi.docstatus=0
      AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
    ORDER BY pi.posting_date DESC, pi.name DESC
""", {"from_date": from_date, "to_date": to_date}, as_dict=True)

    draft_purchases = []
    for r in draft_pi_rows:
        draft_purchases.append({
            "inv": r.name,
            "date": str(r.posting_date or ""),
            "vendor": clean(r.supplier),
            "vendor_name": clean(r.supplier_name or r.supplier),
            "qty": fnum(r.total_qty),
            "gt": fnum(r.grand_total),
            "tax": fnum(r.tax),
            "status": "Draft"
        })

    supplier_rows = _read_sql("""
    SELECT name, supplier_name, supplier_group, country, disabled, creation
    FROM `tabSupplier`
    ORDER BY supplier_name, name
""", as_dict=True)

    suppliers = []
    for s in supplier_rows:
        suppliers.append({
            "code": s.name,
            "name": s.supplier_name or s.name,
            "phone": "",
            "since": str(s.creation.date() if s.creation else ""),
            "city": clean(s.country),
            "rm": "",
            "rmPhone": "",
            "terms": "",
            "level": clean(s.supplier_group),
            "rating": 0,
            "blocked": bool(s.disabled)
        })

    item_vendors = {}

    if item_codes:
        iv_rows = _read_sql("""
        SELECT parent AS item_code, supplier
        FROM `tabItem Supplier`
        WHERE parent IN %(items)s
        ORDER BY parent, idx
    """, {"items": tuple(item_codes)}, as_dict=True)

        for r in iv_rows:
            if r.item_code not in item_vendors:
                item_vendors[r.item_code] = []
            if r.supplier and r.supplier not in item_vendors[r.item_code]:
                item_vendors[r.item_code].append(r.supplier)

    for ic in item_codes:
        if ic not in item_vendors:
            item_vendors[ic] = []

    today = frappe.utils.getdate(frappe.utils.today())
    if today.day >= 6:
        business_from = frappe.utils.getdate(str(today.year) + "-" + str(today.month).zfill(2) + "-06")
    else:
        prev_month = frappe.utils.add_months(today, -1)
        business_from = frappe.utils.getdate(str(prev_month.year) + "-" + str(prev_month.month).zfill(2) + "-06")

    business_to = frappe.utils.add_days(frappe.utils.add_months(business_from, 1), -1)

    po_rows = _read_sql("""
    SELECT
        poi.item_code,
        SUM(IFNULL(poi.qty,0)) AS ordered_qty,
        SUM(GREATEST(IFNULL(poi.qty,0)-IFNULL(poi.received_qty,0),0)) AS pending_qty
    FROM `tabPurchase Order` po
    INNER JOIN `tabPurchase Order Item` poi ON poi.parent=po.name
    WHERE po.docstatus=1
      AND po.transaction_date BETWEEN %(bf)s AND %(bt)s
    GROUP BY poi.item_code
""", {"bf": business_from, "bt": business_to}, as_dict=True)

    po_ordered_month = {}
    po_pending_month = {}
    for r in po_rows:
        po_ordered_month[r.item_code] = fnum(r.ordered_qty)
        po_pending_month[r.item_code] = fnum(r.pending_qty)

    client_ids = []
    for r in material_requests:
        c = r.get("client")
        if c and c not in client_ids:
            client_ids.append(c)

    clients = []
    if client_ids:
        patient_rows = _read_sql("""
        SELECT name, patient_name, mobile, branch_name
        FROM `tabPatient`
        WHERE name IN %(clients)s
    """, {"clients": tuple(client_ids)}, as_dict=True)

        for p in patient_rows:
            clients.append({
                "id": p.name,
                "name": p.patient_name or p.name,
                "mob": clean(p.mobile),
                "br": clean(p.branch_name)
            })

    stock_requests = []

    for r in material_requests:
        req_qty = fnum(r.get("qty"))
        rec_qty = fnum(r.get("received_qty"))

        if rec_qty <= 0 and r.get("stock_entry"):
            se_sum = _read_sql("""
            SELECT SUM(IFNULL(qty,0))
            FROM `tabStock Entry Detail`
            WHERE parent=%s AND item_code=%s
        """, (r.get("stock_entry"), r.get("item")))
            if se_sum and se_sum[0][0]:
                rec_qty = fnum(se_sum[0][0])

        stock_requests.append({
            "id": r.get("request_id"),
            "req": r.get("request_id"),
            "date": r.get("date"),
            "reqDate": r.get("date"),
            "needDate": r.get("required_by"),
            "br": r.get("branch"),
            "branch": r.get("branch"),
            "src": r.get("source_warehouse"),
            "source": r.get("source_warehouse"),
            "client": r.get("client"),
            "therapy": r.get("therapy_id"),
            "appointment": r.get("appointment"),
            "requestBy": r.get("request_by"),
            "reqBy": r.get("request_by"),
            "priority": r.get("priority"),
            "stockType": r.get("request_type"),
            "requestType": r.get("request_type"),
            "status": r.get("status"),
            "item": r.get("item"),
            "itemName": r.get("item_name"),
            "qty": req_qty,
            "reqQty": req_qty,
            "recQty": rec_qty,
            "receivedQty": rec_qty,
            "pendingQty": max(req_qty - rec_qty, 0),
            "unit": r.get("unit"),
            "stockEntry": r.get("stock_entry"),
            "expectedClient": r.get("expected_client"),
            "expectedPhone": r.get("expected_phone"),
            "expectedJoiningDate": r.get("expected_joining_date"),
            "expectedTreatmentCategory": r.get("expected_treatment_category"),
            "expectedSessions": r.get("expected_sessions")
        })

    frappe.response["message"] = {
        "meta": {
            "ho_wh": HO_WH,
            "from_date": str(from_date),
            "to_date": str(to_date),
            "business_from": str(business_from),
            "business_to": str(business_to),
            "cats": cats,
            "counts": {
                "items": len(items),
                "branches": len(branches),
                "purchases": len(purchases),
                "dispatch": len(dispatch),
                "returns": len(returns),
                "material_requests": len(material_requests),
                "stock_requests": len(stock_requests)
            }
        },
        "branches": branches,
        "items": items,
        "suppliers": suppliers,
        "item_vendors": item_vendors,
        "ho_stock": ho_stock,
        "branch_stock": branch_stock,
        "purchases": purchases,
        "draft_purchases": draft_purchases,
        "dispatch": dispatch,
        "returns": returns,
        "adjust": adjust,
        "complaints": [],
        "bookings": [],
        "material_requests": material_requests,
        "stock_requests": stock_requests,
        "clients": clients,
        "po_ordered_month": po_ordered_month,
        "po_pending_month": po_pending_month
    }
