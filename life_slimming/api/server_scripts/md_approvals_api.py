"""md_approvals_api

Original API: md_approvals_api
Source modified: 2026-08-26 12:13:06.758893
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
    #  SERVER SCRIPT (API)  —  md_approvals_api
    #  Script Type : API   ·   API Method : md_approvals_api
    #  Allow Guest : No
    #
    #  MD approval desk. Two queues + live approve/reject writes.
    #   Queues (action=list, default):
    #     - Purchase Invoices at workflow_state = 'Pending from CEO'
    #     - Discount Approval Requests at approval_level = 'L4', status = Pending
    #   Actions:
    #     - action=approve  &kind=pi|disc  &name=DOCNAME  [&note=...]
    #     - action=reject   &kind=pi|disc  &name=DOCNAME  [&note=...]
    #
    #  MD approve = final: PI -> 'Approved', Discount -> 'Approved'.
    #  Reject:            PI -> 'Rejected', Discount -> 'Rejected'.
    #
    #  Writes use frappe.db.set_value (safe_exec-friendly, no doc.submit()).
    #  Guarded: only acts if the document is still in its expected pending state.
    #
    #  safe_exec-safe: dict params only, no None, no reserved aliases,
    #  no try/except, no % literals, no slicing.
    # =====================================================================

    args = frappe.form_dict or {}
    action = args.get("action")
    if not action:
        action = "list"
    action = str(action).strip().lower()

    user = frappe.session.user
    now = frappe.utils.now()

    PI_PENDING = "Pending from CEO"
    DISC_LEVEL = "L4"

    # ---- who is allowed to APPROVE / REJECT (write) ----
    # Reading the queue is open to any logged-in user; writing is gated.
    # Edit this list to control who can act from the dashboard.
    ALLOWED_WRITE_ROLES = ["System Manager", "Head of Accounts", "life_discount_l4"]

    def can_write():
        rrows = _read_sql("""
        SELECT role FROM `tabHas Role`
        WHERE parent = %(u)s AND parenttype = 'User'
    """, {"u": user}, as_dict=True)
        have = {}
        for rr in rrows:
            have[rr.get("role")] = 1
        i = 0
        while i < len(ALLOWED_WRITE_ROLES):
            if ALLOWED_WRITE_ROLES[i] in have:
                return 1
            i = i + 1
        return 0

    # ---------------------------------------------------------------------
    #  LIST — build both queues
    # ---------------------------------------------------------------------
    def build_list():
        result = {}

        # --- Purchase Invoices pending CEO ---
        pi_rows = _read_sql("""
        SELECT name, supplier, grand_total, outstanding_amount,
              posting_date, bill_no, workflow_state, status
        FROM `tabPurchase Invoice`
        WHERE workflow_state = %(s)s
        ORDER BY posting_date ASC
        LIMIT 200
    """, {"s": PI_PENDING}, as_dict=True)
        pis = []
        pi_total = 0.0
        for r in pi_rows:
            a = float(r.get("grand_total") or 0)
            d = {}
            d["kind"] = "pi"
            d["id"] = r.get("name")
            d["supplier"] = r.get("supplier")
            d["amount"] = a
            d["outstanding"] = float(r.get("outstanding_amount") or 0)
            d["date"] = str(r.get("posting_date") or "")
            d["bill_no"] = r.get("bill_no") or ""
            d["state"] = r.get("workflow_state") or ""
            d["erp"] = "/app/purchase-invoice/" + str(r.get("name"))
            pis.append(d)
            pi_total = pi_total + a

        # --- Discount Approval Requests at L4 ---
        disc_rows = _read_sql("""
        SELECT name, request_id, linked_invoice, branch, requested_by,
              bill_total, requested_discount_pct, requested_final_amount,
              proposed_final_amount, approval_level, selected_approver, reason
        FROM `tabDiscount Approval Request`
        WHERE approval_level = %(l)s
          AND status = 'Pending'
        ORDER BY creation DESC
        LIMIT 200
    """, {"l": DISC_LEVEL}, as_dict=True)
        discs = []
        disc_total = 0.0
        for r in disc_rows:
            bt = float(r.get("bill_total") or 0)
            fin = float(r.get("proposed_final_amount") or r.get("requested_final_amount") or 0)
            d = {}
            d["kind"] = "disc"
            d["id"] = r.get("name")
            d["req"] = r.get("request_id") or r.get("name")
            d["invoice"] = r.get("linked_invoice") or ""
            d["branch"] = r.get("branch") or ""
            d["by"] = r.get("requested_by") or ""
            d["bill"] = bt
            d["final"] = fin
            d["benefit"] = bt - fin
            d["pct"] = float(r.get("requested_discount_pct") or 0)
            d["approver"] = r.get("selected_approver") or ""
            d["reason"] = r.get("reason") or ""
            d["erp"] = "/app/discount-approval-request/" + str(r.get("name"))
            discs.append(d)
            disc_total = disc_total + bt

        totals = {}
        totals["pi_count"] = len(pis)
        totals["pi_value"] = pi_total
        totals["disc_count"] = len(discs)
        totals["disc_value"] = disc_total
        totals["total_count"] = len(pis) + len(discs)

        result["purchase_invoices"] = pis
        result["discounts"] = discs
        result["totals"] = totals
        result["user"] = user
        result["can_write"] = can_write()
        return result


    # ---------------------------------------------------------------------
    #  APPROVE / REJECT — guarded writes
    # ---------------------------------------------------------------------
    def act_pi(name, approve, note):
        row = _read_sql("""
        SELECT name, workflow_state, docstatus
        FROM `tabPurchase Invoice`
        WHERE name = %(n)s
        LIMIT 1
    """, {"n": name}, as_dict=True)
        if len(row) == 0:
            frappe.throw("Purchase Invoice not found: " + str(name))
        state = row[0].get("workflow_state") or ""
        if state != PI_PENDING:
            frappe.throw("This Purchase Invoice is not pending CEO approval (state: " + str(state) + ").")

        if approve:
            frappe.db.set_value("Purchase Invoice", name, "workflow_state", "Approved", update_modified=True)
        else:
            frappe.db.set_value("Purchase Invoice", name, "workflow_state", "Rejected", update_modified=True)

        res = {}
        res["ok"] = True
        res["id"] = name
        if approve:
            res["new_state"] = "Approved"
        else:
            res["new_state"] = "Rejected"
        return res


    def act_disc(name, approve, note):
        row = _read_sql("""
        SELECT name, status, approval_level, bill_total,
              proposed_final_amount, requested_final_amount, requested_discount_pct
        FROM `tabDiscount Approval Request`
        WHERE name = %(n)s
        LIMIT 1
    """, {"n": name}, as_dict=True)
        if len(row) == 0:
            frappe.throw("Discount Approval Request not found: " + str(name))
        st = row[0].get("status") or ""
        if st != "Pending":
            frappe.throw("This discount request is not pending (status: " + str(st) + ").")

        if approve:
            fin = float(row[0].get("proposed_final_amount") or row[0].get("requested_final_amount") or 0)
            pct = float(row[0].get("requested_discount_pct") or 0)
            frappe.db.set_value("Discount Approval Request", name, "status", "Approved", update_modified=True)
            frappe.db.set_value("Discount Approval Request", name, "approved_by", user, update_modified=False)
            frappe.db.set_value("Discount Approval Request", name, "approved_at", now, update_modified=False)
            frappe.db.set_value("Discount Approval Request", name, "approved_final_amount", fin, update_modified=False)
            frappe.db.set_value("Discount Approval Request", name, "approved_discount_pct", pct, update_modified=False)
            if note:
                frappe.db.set_value("Discount Approval Request", name, "approver_note", note, update_modified=False)
        else:
            frappe.db.set_value("Discount Approval Request", name, "status", "Rejected", update_modified=True)
            frappe.db.set_value("Discount Approval Request", name, "approved_by", user, update_modified=False)
            frappe.db.set_value("Discount Approval Request", name, "approved_at", now, update_modified=False)
            if note:
                frappe.db.set_value("Discount Approval Request", name, "rejection_reason", note, update_modified=False)

        res = {}
        res["ok"] = True
        res["id"] = name
        if approve:
            res["new_state"] = "Approved"
        else:
            res["new_state"] = "Rejected"
        return res


    # ---------------------------------------------------------------------
    #  DISPATCH
    # ---------------------------------------------------------------------
    if action == "list":
        out = build_list()
    elif action == "approve" or action == "reject":
        if can_write() == 0:
            frappe.throw("You are not authorised to approve or reject. Ask an admin to grant you the required role.")
        kind = str(args.get("kind") or "").strip().lower()
        name = str(args.get("name") or "").strip()
        note = str(args.get("note") or "").strip()
        approve = (action == "approve")
        if not name:
            frappe.throw("Document name is required.")
        if kind == "pi":
            out = act_pi(name, approve, note)
        elif kind == "disc":
            out = act_disc(name, approve, note)
        else:
            frappe.throw("Unknown kind: " + str(kind) + " (expected pi or disc).")
    else:
        frappe.throw("Unknown action: " + str(action))

    frappe.response["message"] = out
