"""md_my_approvals_api

Original API: md_my_approvals_api
Source modified: 2026-08-07 08:53:08.170000
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
    #  SERVER SCRIPT (API)  —  md_my_approvals_api
    #  Script Type : API   ·   API Method : md_my_approvals_api
    #  URL: /api/method/md_my_approvals_api   [?user=email to preview]
    #
    #  Login-aware approvals. Returns ONLY what is pending for the current
    #  user, across every approval type:
    #    - Discount Approval Request
    #    - P2P (LIFE Client Package Conversion Same Client Package To Package)
    #    - C2C (Client Package Conversion Client To Client)  incl. branch transfer
    #    - Purchase Order / Purchase Invoice (CEO pending)
    #
    #  Routing:
    #    COO  (bhuvan@lifescc.com) -> FINAL stage of P2P & C2C (COO/Management)
    #    MD   (kp@lifescc.com)     -> L4 discounts + Purchase Invoice 'Pending from CEO'
    #  System Manager sees everything pending (admin).
    #
    #  safe_exec-safe: dict params only, no None, no reserved aliases,
    #  no try/except, no % literals, no slicing of function results.
    # =====================================================================

    args = frappe.form_dict or {}
    user = args.get("user")
    if not user:
        user = frappe.session.user
    user = str(user).strip().lower()

    COO_USER = "bhuvan@lifescc.com"
    MD_USER = "kp@lifescc.com"

    # is this user an admin? (sees everything pending)
    rrows = _read_sql("""
    SELECT role FROM `tabHas Role`
    WHERE parent = %(u)s AND parenttype = 'User'
""", {"u": frappe.session.user}, as_dict=True)
    is_admin = 0
    for rr in rrows:
        if rr.get("role") == "System Manager":
            is_admin = 1

    is_coo = 0
    is_md = 0
    if user == COO_USER:
        is_coo = 1
    if user == MD_USER:
        is_md = 1

    out = []

    # ─────────── P2P — pending at COO (final) stage ───────────
    if is_coo == 1 or is_admin == 1:
        prows = _read_sql("""
        SELECT name, name1, client_name, branch, approval_stage,
               approval_display_status, final_approval_status,
               current_package__residual__balance_value_rs AS resid,
               new_package_total_price_rs AS newp,
               reason__remarks_of_conversion AS reason, creation
        FROM `tabLIFE Client Package Conversion Same Client Package To Package`
        WHERE COALESCE(final_approval_status,'') NOT IN ('Approved','Rejected')
          AND approval_stage LIKE %(ops)s
        ORDER BY creation DESC
        LIMIT 200
    """, {"ops": "%Operations Head%"}, as_dict=True)
        for r in prows:
            rec = {}
            rec["src"] = "P2P"
            rec["id"] = r.get("name")
            rec["title"] = r.get("name")
            rec["cn"] = r.get("name1") or r.get("client_name") or r.get("name")
            rec["br"] = r.get("branch") or "-"
            rec["stage"] = r.get("approval_display_status") or r.get("approval_stage") or ""
            rec["reason"] = r.get("reason") or ""
            rec["gross"] = float(r.get("resid") or 0)
            rec["net"] = float(r.get("newp") or 0)
            rec["reqAt"] = str(r.get("creation") or "")
            rec["erp"] = "/app/life-client-package-conversion-same-client-package-to-package/" + str(r.get("name"))
            rec["forWho"] = "COO"
            out.append(rec)

    # ─────────── C2C — pending at COO (final) stage, incl branch transfer ───────────
    if is_coo == 1 or is_admin == 1:
        crows = _read_sql("""
        SELECT name, name1, client_full_name, branch, receiving_branch,
               transfer_type, approval_stage, approval_display_status,
               final_approval_status, conversion_status, total_amount,
               conversion_charges_amount,
               reason__remarks_of__conversion AS reason, creation
        FROM `tabClient Package Conversion Client To Client`
        WHERE COALESCE(final_approval_status,'') NOT IN ('Approved','Rejected')
          AND COALESCE(conversion_status,'') NOT IN ('Approved','Rejected','Completed')
          AND approval_stage LIKE %(coo)s
        ORDER BY creation DESC
        LIMIT 200
    """, {"coo": "%Operations COO%"}, as_dict=True)
        for r in crows:
            rec = {}
            xt = r.get("transfer_type") or ""
            if xt == "Cross Branch Transfer":
                rec["src"] = "B2B"
            else:
                rec["src"] = "C2C"
            rec["id"] = r.get("name")
            rec["title"] = r.get("name")
            rec["cn"] = r.get("name1") or r.get("client_full_name") or r.get("name")
            rec["br"] = r.get("branch") or "-"
            rec["recvBr"] = r.get("receiving_branch") or ""
            rec["xfer"] = xt
            rec["stage"] = r.get("approval_display_status") or r.get("approval_stage") or ""
            rec["reason"] = r.get("reason") or ""
            rec["gross"] = float(r.get("total_amount") or 0)
            rec["net"] = float(r.get("total_amount") or 0)
            rec["benefit"] = float(r.get("conversion_charges_amount") or 0)
            rec["reqAt"] = str(r.get("creation") or "")
            rec["erp"] = "/app/client-package-conversion-client-to-client/" + str(r.get("name"))
            rec["forWho"] = "COO"
            out.append(rec)

    # ─────────── Purchase Orders — pending Ops (COO) ───────────
    if is_coo == 1 or is_admin == 1:
        porows = _read_sql("""
        SELECT name, supplier, grand_total, workflow_state,
               transaction_date, creation
        FROM `tabPurchase Order`
        WHERE workflow_state = 'Pending Ops Approval'
        ORDER BY transaction_date ASC
        LIMIT 200
    """, {}, as_dict=True)
        for r in porows:
            rec = {}
            rec["src"] = "PO"
            rec["id"] = r.get("name")
            rec["title"] = r.get("name")
            rec["cn"] = r.get("supplier") or "-"
            rec["br"] = "-"
            rec["stage"] = "Pending Ops Approval"
            rec["reason"] = ""
            rec["gross"] = float(r.get("grand_total") or 0)
            rec["net"] = float(r.get("grand_total") or 0)
            rec["reqAt"] = str(r.get("transaction_date") or "")
            rec["erp"] = "/app/purchase-order/" + str(r.get("name"))
            rec["forWho"] = "COO"
            out.append(rec)

    # ─────────── Purchase Invoices — COO also sees 'Pending from CEO' ───────────
    if is_coo == 1 or is_admin == 1:
        cpirows = _read_sql("""
        SELECT name, supplier, grand_total, outstanding_amount,
               posting_date, bill_no, workflow_state, creation
        FROM `tabPurchase Invoice`
        WHERE workflow_state = 'Pending from CEO'
        ORDER BY posting_date ASC
        LIMIT 200
    """, {}, as_dict=True)
        for r in cpirows:
            rec = {}
            rec["src"] = "PI"
            rec["id"] = r.get("name")
            rec["title"] = r.get("name")
            rec["cn"] = r.get("supplier") or "-"
            rec["br"] = "-"
            rec["stage"] = "Pending from CEO"
            rec["reason"] = "Bill " + str(r.get("bill_no") or "")
            rec["gross"] = float(r.get("grand_total") or 0)
            rec["net"] = float(r.get("outstanding_amount") or 0)
            rec["reqAt"] = str(r.get("posting_date") or "")
            rec["erp"] = "/app/purchase-invoice/" + str(r.get("name"))
            rec["forWho"] = "COO"
            out.append(rec)

    # ─────────── Discount L4 — pending for MD ───────────
    if is_md == 1 or is_admin == 1:
        drows = _read_sql("""
        SELECT name, request_id, linked_invoice, branch, requested_by,
               bill_total, requested_discount_pct, proposed_final_amount,
               requested_final_amount, reason, creation
        FROM `tabDiscount Approval Request`
        WHERE approval_level = 'L4' AND status = 'Pending'
        ORDER BY creation DESC
        LIMIT 200
    """, {}, as_dict=True)
        for r in drows:
            bt = float(r.get("bill_total") or 0)
            fin = float(r.get("proposed_final_amount") or r.get("requested_final_amount") or 0)
            rec = {}
            rec["src"] = "DISC"
            rec["id"] = r.get("name")
            rec["title"] = r.get("request_id") or r.get("name")
            rec["cn"] = r.get("linked_invoice") or "-"
            rec["br"] = r.get("branch") or "-"
            rec["stage"] = "L4 (MD)"
            rec["reason"] = r.get("reason") or ""
            rec["gross"] = bt
            rec["net"] = fin
            rec["benefit"] = bt - fin
            rec["pct"] = float(r.get("requested_discount_pct") or 0)
            rec["reqAt"] = str(r.get("creation") or "")
            rec["erp"] = "/app/discount-approval-request/" + str(r.get("name"))
            rec["forWho"] = "MD"
            out.append(rec)

    # ─────────── Purchase Invoice — pending from CEO (MD) ───────────
    if is_md == 1 or is_admin == 1:
        pirows = _read_sql("""
        SELECT name, supplier, grand_total, outstanding_amount,
               posting_date, bill_no, workflow_state, creation
        FROM `tabPurchase Invoice`
        WHERE workflow_state = 'Pending from CEO'
        ORDER BY posting_date ASC
        LIMIT 200
    """, {}, as_dict=True)
        for r in pirows:
            rec = {}
            rec["src"] = "PI"
            rec["id"] = r.get("name")
            rec["title"] = r.get("name")
            rec["cn"] = r.get("supplier") or "-"
            rec["br"] = "-"
            rec["stage"] = "Pending from CEO"
            rec["reason"] = "Bill " + str(r.get("bill_no") or "")
            rec["gross"] = float(r.get("grand_total") or 0)
            rec["net"] = float(r.get("outstanding_amount") or 0)
            rec["reqAt"] = str(r.get("posting_date") or "")
            rec["erp"] = "/app/purchase-invoice/" + str(r.get("name"))
            rec["forWho"] = "MD"
            out.append(rec)

    # ─────────── totals ───────────
    n_coo = 0
    n_md = 0
    val = 0.0
    for r in out:
        if r["forWho"] == "COO":
            n_coo = n_coo + 1
        else:
            n_md = n_md + 1
        val = val + r.get("gross", 0)

    totals = {}
    totals["count"] = len(out)
    totals["coo_count"] = n_coo
    totals["md_count"] = n_md
    totals["value"] = val

    resp = {}
    resp["user"] = user
    resp["is_coo"] = is_coo
    resp["is_md"] = is_md
    resp["is_admin"] = is_admin
    resp["approvals"] = out
    resp["totals"] = totals
    frappe.response["message"] = resp
