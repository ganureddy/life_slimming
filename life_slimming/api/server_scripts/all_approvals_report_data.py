"""all_approvals_report_data

Original API: all_approvals_report_data
Source modified: 2026-08-07 14:22:52.868204
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


    # frm = frappe.form_dict.get("from_date")
    # to = frappe.form_dict.get("to_date")
    # br = frappe.form_dict.get("branch")

    # start = None
    # end = None
    # if frm:
    #     start = frm + " 00:00:00"
    # if to:
    #     end = to + " 23:59:59"

    # def crange(f):
    #     if start and end:
    #         f["creation"] = ["between", [start, end]]
    #     elif start:
    #         f["creation"] = [">=", start]
    #     elif end:
    #         f["creation"] = ["<=", end]
    #     return f

    # out = []

    # # ─────────────────────────── 1. DISCOUNT APPROVAL ───────────────────────────
    # df = crange({})
    # if br:
    #     df["branch"] = br
    # drows = frappe.get_all("Discount Approval Request",
    #     filters=df,
    #     fields=["name", "request_id", "linked_invoice", "branch", "requested_by",
    #         "bill_total", "approval_level", "selected_approver",
    #         "requested_discount_pct", "requested_final_amount", "proposed_final_amount",
    #         "approved_discount_pct", "approved_final_amount", "approved_by", "approved_at",
    #         "approver_note", "reason", "rejection_reason", "status", "creation"],
    #     order_by="creation desc", limit_page_length=0)
    # for r in drows:
    #     stt = r.get("status") or "Pending"
    #     st = "PEND"
    #     if stt == "Approved":
    #         st = "OK"
    #     elif stt == "Rejected":
    #         st = "RJ"
    #     elif stt == "Expired":
    #         st = "RJ"
    #     billt = r.get("bill_total") or 0
    #     finamt = r.get("approved_final_amount") or r.get("proposed_final_amount") or r.get("requested_final_amount") or 0
    #     disc = billt - finamt
    #     rec = {}
    #     rec["src"] = "DISC"
    #     rec["id"] = r.get("name")
    #     rec["title"] = r.get("request_id") or r.get("name")
    #     rec["cn"] = r.get("linked_invoice") or "—"
    #     rec["br"] = r.get("branch") or "—"
    #     rec["emp"] = (r.get("requested_by") or "").split("@")[0]
    #     rec["st"] = st
    #     rec["stageTxt"] = (r.get("approval_level") or "") + " · " + stt
    #     rec["level"] = r.get("approval_level") or ""
    #     rec["reqAt"] = str(r.get("creation") or "")
    #     rec["a1Name"] = r.get("approved_by") or ""
    #     rec["a1At"] = str(r.get("approved_at") or "")
    #     rec["a1Rem"] = r.get("approver_note") or ""
    #     rec["reason"] = r.get("reason") or ""
    #     rec["rejRem"] = r.get("rejection_reason") or ""
    #     rec["gross"] = billt
    #     rec["net"] = finamt
    #     rec["benefit"] = disc
    #     rec["pctReq"] = r.get("requested_discount_pct") or 0
    #     rec["pctApr"] = r.get("approved_discount_pct") or 0
    #     out.append(rec)

    # # ─────────────────────────── 2. P2P CONVERSION ──────────────────────────────
    # pf = crange({})
    # if br:
    #     pf["branch"] = br
    # prows = frappe.get_all("LIFE Client Package Conversion Same Client Package To Package",
    #     filters=pf,
    #     fields=["name", "client_name", "name1", "branch", "owner",
    #         "approval_stage", "approval_display_status", "final_approval_status",
    #         "current_package__residual__balance_value_rs", "new_package_total_price_rs",
    #         "difference_payable_by_client_new_package_price__residual_value",
    #         "approved_by_name", "approved_date", "centre_manager_remarks",
    #         "authorised_name", "authorised_date", "operations_final_remarks",
    #         "coo_management_name", "coo_management_date", "coo_management_remarks",
    #         "reason__remarks_of_conversion", "original_invoice__bill_numbers", "creation"],
    #     order_by="creation desc", limit_page_length=0)
    # for r in prows:
    #     stage = r.get("approval_stage") or ""
    #     fin = r.get("final_approval_status") or ""
    #     st = "L1"
    #     if fin == "Approved" or stage == "Approved":
    #         st = "OK"
    #     elif fin == "Rejected" or stage == "Rejected":
    #         st = "RJ"
    #     elif "COO" in stage:
    #         st = "L3"
    #     elif "Operations Head" in stage:
    #         st = "L2"
    #     elif "Centre Manager" in stage:
    #         st = "L1"
    #     resid = r.get("current_package__residual__balance_value_rs") or 0
    #     newp = r.get("new_package_total_price_rs") or 0
    #     rec = {}
    #     rec["src"] = "P2P"
    #     rec["id"] = r.get("name")
    #     rec["title"] = r.get("name")
    #     rec["cn"] = r.get("name1") or r.get("client_name") or r.get("name")
    #     rec["br"] = r.get("branch") or "—"
    #     rec["emp"] = (r.get("owner") or "").split("@")[0]
    #     rec["st"] = st
    #     rec["stageTxt"] = r.get("approval_display_status") or stage
    #     rec["reqAt"] = str(r.get("creation") or "")
    #     rec["a1Name"] = r.get("approved_by_name") or ""
    #     rec["a1At"] = str(r.get("approved_date") or "")
    #     rec["a1Rem"] = r.get("centre_manager_remarks") or ""
    #     rec["a2Name"] = r.get("authorised_name") or ""
    #     rec["a2At"] = str(r.get("authorised_date") or "")
    #     rec["a2Rem"] = r.get("operations_final_remarks") or ""
    #     rec["a3Name"] = r.get("coo_management_name") or ""
    #     rec["a3At"] = str(r.get("coo_management_date") or "")
    #     rec["a3Rem"] = r.get("coo_management_remarks") or ""
    #     rec["reason"] = r.get("reason__remarks_of_conversion") or ""
    #     rec["bills"] = r.get("original_invoice__bill_numbers") or ""
    #     rec["gross"] = resid
    #     rec["net"] = newp
    #     rec["benefit"] = resid - newp
    #     rec["diff"] = r.get("difference_payable_by_client_new_package_price__residual_value") or 0
    #     out.append(rec)

    # # ─────────────────────────── 3. C2C CONVERSION ──────────────────────────────
    # cf = crange({})
    # if br:
    #     cf["branch"] = br
    # crows = frappe.get_all("Client Package Conversion Client To Client",
    #     filters=cf,
    #     fields=["name", "name1", "client_full_name", "client_name", "branch",
    #         "receiving_branch", "transfer_type", "conversion_status", "approval_stage",
    #         "approval_display_status", "final_approval_status", "total_amount",
    #         "conversion_charges_amount",
    #         "centre_manager_decision", "centre_manager_name", "centre_manager_date",
    #         "centre_manager_remarks",
    #         "audit_team_decision", "audit_team__corporate_team_name",
    #         "audit_team__corporate_team_date", "audit_team_remarks",
    #         "operations_coo__management_name", "operations_coo__management_date",
    #         "rejected_by_name", "rejected_by_role", "rejection_remarks",
    #         "reason__remarks_of__conversion", "original_invoice__bill_numbers", "creation"],
    #     order_by="creation desc", limit_page_length=0)
    # for r in crows:
    #     stage = r.get("approval_stage") or r.get("conversion_status") or ""
    #     fin = r.get("final_approval_status") or ""
    #     st = "L1"
    #     if fin == "Approved" or stage == "Approved" or stage == "Completed":
    #         st = "OK"
    #     elif fin == "Rejected" or stage == "Rejected":
    #         st = "RJ"
    #     elif "COO" in stage or "Operations COO" in stage:
    #         st = "L3"
    #     elif "Audit" in stage:
    #         st = "L2"
    #     else:
    #         st = "L1"
    #     rec = {}
    #     rec["src"] = "C2C"
    #     rec["id"] = r.get("name")
    #     rec["title"] = r.get("name")
    #     rec["cn"] = r.get("name1") or r.get("client_full_name") or r.get("name")
    #     rec["br"] = r.get("branch") or "—"
    #     rec["recvBr"] = r.get("receiving_branch") or ""
    #     rec["xfer"] = r.get("transfer_type") or ""
    #     rec["emp"] = r.get("branch") or ""
    #     rec["st"] = st
    #     rec["stageTxt"] = r.get("approval_display_status") or stage
    #     rec["reqAt"] = str(r.get("creation") or "")
    #     rec["a1Name"] = r.get("centre_manager_name") or ""
    #     rec["a1At"] = str(r.get("centre_manager_date") or "")
    #     rec["a1Rem"] = r.get("centre_manager_remarks") or ""
    #     rec["a2Name"] = r.get("audit_team__corporate_team_name") or ""
    #     rec["a2At"] = str(r.get("audit_team__corporate_team_date") or "")
    #     rec["a2Rem"] = r.get("audit_team_remarks") or ""
    #     rec["a3Name"] = r.get("operations_coo__management_name") or ""
    #     rec["a3At"] = str(r.get("operations_coo__management_date") or "")
    #     rec["a3Rem"] = ""
    #     rec["reason"] = r.get("reason__remarks_of__conversion") or ""
    #     rec["rejName"] = r.get("rejected_by_name") or ""
    #     rec["rejRole"] = r.get("rejected_by_role") or ""
    #     rec["rejRem"] = r.get("rejection_remarks") or ""
    #     rec["bills"] = r.get("original_invoice__bill_numbers") or ""
    #     rec["gross"] = r.get("total_amount") or 0
    #     rec["net"] = r.get("total_amount") or 0
    #     rec["benefit"] = r.get("conversion_charges_amount") or 0
    #     out.append(rec)

    # # ─────────────────────────── 4. PURCHASE ORDER ──────────────────────────────
    # # PO has no branch field — branch filter skips PO entirely when a branch is chosen
    # porows = []
    # if not br:
    #     pof = crange({})
    #     porows = frappe.get_all("Purchase Order",
    #         filters=pof,
    #         fields=["name", "supplier", "grand_total", "workflow_state", "status",
    #             "owner", "transaction_date", "creation"],
    #         order_by="creation desc", limit_page_length=0)
    # for r in porows:
    #     ws = r.get("workflow_state") or r.get("status") or ""
    #     st = "PEND"
    #     low = ws.lower()
    #     if "reject" in low:
    #         st = "RJ"
    #     elif "approved" in low or "to receive" in low or "completed" in low or ws == "Submitted":
    #         st = "OK"
    #     elif "pending" in low or "draft" in low:
    #         st = "PEND"
    #     rec = {}
    #     rec["src"] = "PO"
    #     rec["id"] = r.get("name")
    #     rec["title"] = r.get("name")
    #     rec["cn"] = r.get("supplier") or "—"
    #     rec["br"] = "—"
    #     rec["emp"] = (r.get("owner") or "").split("@")[0]
    #     rec["st"] = st
    #     rec["stageTxt"] = ws
    #     rec["reqAt"] = str(r.get("creation") or "")
    #     rec["gross"] = r.get("grand_total") or 0
    #     rec["net"] = r.get("grand_total") or 0
    #     rec["benefit"] = 0
    #     out.append(rec)

    # frappe.response["message"] = {"data": out, "count": len(out)}





























    # ═══════════════════════════════════════════════════════════════════════════
    #  SERVER SCRIPT  (paste into: Server Script  →  all_approvals_report_data)
    # ───────────────────────────────────────────────────────────────────────────
    #  Script Type : API
    #  API Method  : all_approvals_report_data
    #  Enabled     : ✓        Allow Guest : ✗
    # ───────────────────────────────────────────────────────────────────────────
    #  WHAT CHANGED (role-wise support):
    #   • returns  me       = logged-in email
    #   • returns  myRoles  = list of the user's Frappe roles
    #   • returns  myView   = the role-view auto-selected for this user
    #   • each record gets   pendRole  = which role owns it RIGHT NOW
    #                         (CM / AUDIT / OPS / COO / DISC_L1..L4 / PO / "" when closed)
    # ═══════════════════════════════════════════════════════════════════════════

    frm = frappe.form_dict.get("from_date")
    to = frappe.form_dict.get("to_date")
    br = frappe.form_dict.get("branch")

    start = None
    end = None
    if frm:
        start = frm + " 00:00:00"
    if to:
        end = to + " 23:59:59"

    def crange(f):
        if start and end:
            f["creation"] = ["between", [start, end]]
        elif start:
            f["creation"] = [">=", start]
        elif end:
            f["creation"] = ["<=", end]
        return f

    # ─── who is asking ────────────────────────────────────────────────────────
    # NOTE: frappe.get_roles() is blocked in safe_exec, so read the Has Role
    # child table directly (parenttype = User, parent = the user's email).
    me = frappe.session.user
    roles = []
    rrows = frappe.get_all("Has Role",
        filters={"parenttype": "User", "parent": me},
        fields=["role"], limit_page_length=0)
    for rr in rrows:
        rn = rr.get("role")
        if rn:
            roles.append(rn)

    out = []

    # ─────────────────────────── 1. DISCOUNT APPROVAL ─────────────────────────
    df = crange({})
    if br:
        df["branch"] = br
    drows = frappe.get_all("Discount Approval Request",
        filters=df,
        fields=["name", "request_id", "linked_invoice", "branch", "requested_by",
            "bill_total", "approval_level", "selected_approver",
            "requested_discount_pct", "requested_final_amount", "proposed_final_amount",
            "approved_discount_pct", "approved_final_amount", "approved_by", "approved_at",
            "approver_note", "reason", "rejection_reason", "status", "creation"],
        order_by="creation desc", limit_page_length=0)
    for r in drows:
        stt = r.get("status") or "Pending"
        st = "PEND"
        if stt == "Approved":
            st = "OK"
        elif stt == "Rejected":
            st = "RJ"
        elif stt == "Expired":
            st = "RJ"
        billt = r.get("bill_total") or 0
        finamt = r.get("approved_final_amount") or r.get("proposed_final_amount") or r.get("requested_final_amount") or 0
        disc = billt - finamt
        lvl = (r.get("approval_level") or "").strip()
        pend = ""
        if st == "PEND":
            pend = "DISC_" + (lvl.upper().replace(" ", "") or "L1")
        rec = {}
        rec["src"] = "DISC"
        rec["id"] = r.get("name")
        rec["title"] = r.get("request_id") or r.get("name")
        rec["cn"] = r.get("linked_invoice") or "—"
        rec["br"] = r.get("branch") or "—"
        rec["emp"] = (r.get("requested_by") or "").split("@")[0]
        rec["st"] = st
        rec["pendRole"] = pend
        rec["stageTxt"] = (r.get("approval_level") or "") + " · " + stt
        rec["level"] = r.get("approval_level") or ""
        rec["reqAt"] = str(r.get("creation") or "")
        rec["a1Name"] = r.get("approved_by") or ""
        rec["a1At"] = str(r.get("approved_at") or "")
        rec["a1Rem"] = r.get("approver_note") or ""
        rec["reason"] = r.get("reason") or ""
        rec["rejRem"] = r.get("rejection_reason") or ""
        rec["gross"] = billt
        rec["net"] = finamt
        rec["benefit"] = disc
        rec["pctReq"] = r.get("requested_discount_pct") or 0
        rec["pctApr"] = r.get("approved_discount_pct") or 0
        out.append(rec)

    # ─────────────────────────── 2. P2P CONVERSION ────────────────────────────
    pf = crange({})
    if br:
        pf["branch"] = br
    prows = frappe.get_all("LIFE Client Package Conversion Same Client Package To Package",
        filters=pf,
        fields=["name", "client_name", "name1", "branch", "owner",
            "approval_stage", "approval_display_status", "final_approval_status",
            "current_package__residual__balance_value_rs", "new_package_total_price_rs",
            "difference_payable_by_client_new_package_price__residual_value",
            "approved_by_name", "approved_date", "centre_manager_remarks",
            "authorised_name", "authorised_date", "operations_final_remarks",
            "coo_management_name", "coo_management_date", "coo_management_remarks",
            "reason__remarks_of_conversion", "original_invoice__bill_numbers", "creation"],
        order_by="creation desc", limit_page_length=0)
    for r in prows:
        stage = r.get("approval_stage") or ""
        fin = r.get("final_approval_status") or ""
        st = "L1"
        if fin == "Approved" or stage == "Approved":
            st = "OK"
        elif fin == "Rejected" or stage == "Rejected":
            st = "RJ"
        elif "COO" in stage:
            st = "L3"
        elif "Operations Head" in stage:
            st = "L2"
        elif "Centre Manager" in stage:
            st = "L1"
        pend = ""
        if st == "L1":
            pend = "CM"
        elif st == "L2":
            pend = "OPS"
        elif st == "L3":
            pend = "COO"
        resid = r.get("current_package__residual__balance_value_rs") or 0
        newp = r.get("new_package_total_price_rs") or 0
        rec = {}
        rec["src"] = "P2P"
        rec["id"] = r.get("name")
        rec["title"] = r.get("name")
        rec["cn"] = r.get("name1") or r.get("client_name") or r.get("name")
        rec["br"] = r.get("branch") or "—"
        rec["emp"] = (r.get("owner") or "").split("@")[0]
        rec["st"] = st
        rec["pendRole"] = pend
        rec["stageTxt"] = r.get("approval_display_status") or stage
        rec["reqAt"] = str(r.get("creation") or "")
        rec["a1Name"] = r.get("approved_by_name") or ""
        rec["a1At"] = str(r.get("approved_date") or "")
        rec["a1Rem"] = r.get("centre_manager_remarks") or ""
        rec["a2Name"] = r.get("authorised_name") or ""
        rec["a2At"] = str(r.get("authorised_date") or "")
        rec["a2Rem"] = r.get("operations_final_remarks") or ""
        rec["a3Name"] = r.get("coo_management_name") or ""
        rec["a3At"] = str(r.get("coo_management_date") or "")
        rec["a3Rem"] = r.get("coo_management_remarks") or ""
        rec["reason"] = r.get("reason__remarks_of_conversion") or ""
        rec["bills"] = r.get("original_invoice__bill_numbers") or ""
        rec["gross"] = resid
        rec["net"] = newp
        rec["benefit"] = resid - newp
        rec["diff"] = r.get("difference_payable_by_client_new_package_price__residual_value") or 0
        out.append(rec)

    # ─────────────────────────── 3. C2C CONVERSION ────────────────────────────
    cf = crange({})
    if br:
        cf["branch"] = br
    crows = frappe.get_all("Client Package Conversion Client To Client",
        filters=cf,
        fields=["name", "name1", "client_full_name", "client_name", "branch",
            "receiving_branch", "transfer_type", "conversion_status", "approval_stage",
            "approval_display_status", "final_approval_status", "total_amount",
            "conversion_charges_amount",
            "centre_manager_decision", "centre_manager_name", "centre_manager_date",
            "centre_manager_remarks",
            "audit_team_decision", "audit_team__corporate_team_name",
            "audit_team__corporate_team_date", "audit_team_remarks",
            "operations_coo__management_name", "operations_coo__management_date",
            "rejected_by_name", "rejected_by_role", "rejection_remarks",
            "reason__remarks_of__conversion", "original_invoice__bill_numbers", "creation"],
        order_by="creation desc", limit_page_length=0)
    for r in crows:
        stage = r.get("approval_stage") or r.get("conversion_status") or ""
        fin = r.get("final_approval_status") or ""
        st = "L1"
        if fin == "Approved" or stage == "Approved" or stage == "Completed":
            st = "OK"
        elif fin == "Rejected" or stage == "Rejected":
            st = "RJ"
        elif "COO" in stage or "Operations COO" in stage:
            st = "L3"
        elif "Audit" in stage:
            st = "L2"
        else:
            st = "L1"
        pend = ""
        if st == "L1":
            pend = "CM"
        elif st == "L2":
            pend = "AUDIT"
        elif st == "L3":
            pend = "COO"
        rec = {}
        rec["src"] = "C2C"
        rec["id"] = r.get("name")
        rec["title"] = r.get("name")
        rec["cn"] = r.get("name1") or r.get("client_full_name") or r.get("name")
        rec["br"] = r.get("branch") or "—"
        rec["recvBr"] = r.get("receiving_branch") or ""
        rec["xfer"] = r.get("transfer_type") or ""
        rec["emp"] = r.get("branch") or ""
        rec["st"] = st
        rec["pendRole"] = pend
        rec["stageTxt"] = r.get("approval_display_status") or stage
        rec["reqAt"] = str(r.get("creation") or "")
        rec["a1Name"] = r.get("centre_manager_name") or ""
        rec["a1At"] = str(r.get("centre_manager_date") or "")
        rec["a1Rem"] = r.get("centre_manager_remarks") or ""
        rec["a2Name"] = r.get("audit_team__corporate_team_name") or ""
        rec["a2At"] = str(r.get("audit_team__corporate_team_date") or "")
        rec["a2Rem"] = r.get("audit_team_remarks") or ""
        rec["a3Name"] = r.get("operations_coo__management_name") or ""
        rec["a3At"] = str(r.get("operations_coo__management_date") or "")
        rec["a3Rem"] = ""
        rec["reason"] = r.get("reason__remarks_of__conversion") or ""
        rec["rejName"] = r.get("rejected_by_name") or ""
        rec["rejRole"] = r.get("rejected_by_role") or ""
        rec["rejRem"] = r.get("rejection_remarks") or ""
        rec["bills"] = r.get("original_invoice__bill_numbers") or ""
        rec["gross"] = r.get("total_amount") or 0
        rec["net"] = r.get("total_amount") or 0
        rec["benefit"] = r.get("conversion_charges_amount") or 0
        out.append(rec)

    # ─────────────────────────── 4. PURCHASE ORDER ────────────────────────────
    # PO has no branch field — branch filter skips PO entirely when a branch is chosen
    porows = []
    if not br:
        pof = crange({})
        porows = frappe.get_all("Purchase Order",
            filters=pof,
            fields=["name", "supplier", "grand_total", "workflow_state", "status",
                "owner", "transaction_date", "creation"],
            order_by="creation desc", limit_page_length=0)
    for r in porows:
        ws = r.get("workflow_state") or r.get("status") or ""
        st = "PEND"
        low = ws.lower()
        if "reject" in low:
            st = "RJ"
        elif "approved" in low or "to receive" in low or "completed" in low or ws == "Submitted":
            st = "OK"
        elif "pending" in low or "draft" in low:
            st = "PEND"
        rec = {}
        rec["src"] = "PO"
        rec["id"] = r.get("name")
        rec["title"] = r.get("name")
        rec["cn"] = r.get("supplier") or "—"
        rec["br"] = "—"
        rec["emp"] = (r.get("owner") or "").split("@")[0]
        rec["st"] = st
        rec["pendRole"] = "PO" if st == "PEND" else ""
        rec["stageTxt"] = ws
        rec["reqAt"] = str(r.get("creation") or "")
        rec["gross"] = r.get("grand_total") or 0
        rec["net"] = r.get("grand_total") or 0
        rec["benefit"] = 0
        out.append(rec)

    # ─────────────────────────── 5. MATERIAL REQUEST ──────────────────────────
    # Flow: Draft → Pending Inventory (Stock Manager) → Approved / Rejected / Cancelled
    mrrows = []
    if not br:
        mrf = crange({})
        mrrows = frappe.get_all("Material Request",
            filters=mrf,
            fields=["name", "workflow_state", "status", "material_request_type",
                "transaction_date", "owner", "creation"],
            order_by="creation desc", limit_page_length=0)
    for r in mrrows:
        ws = (r.get("workflow_state") or r.get("status") or "").strip()
        low = ws.lower()
        st = "PEND"
        pend = "STOCK"
        if "reject" in low or "cancel" in low:
            st = "RJ"
            pend = ""
        elif ws == "Approved":
            st = "OK"
            pend = ""
        elif "draft" in low:
            st = "PEND"
            pend = "MR_DRAFT"
        elif "pending" in low:
            st = "PEND"
            pend = "STOCK"
        rec = {}
        rec["src"] = "MR"
        rec["id"] = r.get("name")
        rec["title"] = r.get("name")
        rec["cn"] = r.get("material_request_type") or "Material Request"
        rec["br"] = "—"
        rec["emp"] = (r.get("owner") or "").split("@")[0]
        rec["st"] = st
        rec["pendRole"] = pend
        rec["stageTxt"] = ws
        rec["reqAt"] = str(r.get("creation") or "")
        rec["gross"] = 0
        rec["net"] = 0
        rec["benefit"] = 0
        out.append(rec)

    # ─────────────────────────── 6. PURCHASE INVOICE ──────────────────────────
    # Workflow currently inactive — most PIs have no pending state.
    # Records with workflow_state = a "pending" value show as pending to Accounts.
    pirows = []
    if not br:
        pif = crange({})
        pirows = frappe.get_all("Purchase Invoice",
            filters=pif,
            fields=["name", "supplier", "grand_total", "workflow_state", "status",
                "owner", "posting_date", "creation"],
            order_by="creation desc", limit_page_length=0)
    for r in pirows:
        ws = (r.get("workflow_state") or "").strip()
        low = ws.lower()
        st = "OK"
        pend = ""
        if "reject" in low:
            st = "RJ"
        elif "pending" in low or "ceo" in low or "draft" in low:
            st = "PEND"
            pend = "ACCT"
        elif ws == "Approved" or ws == "":
            st = "OK"
        rec = {}
        rec["src"] = "PI"
        rec["id"] = r.get("name")
        rec["title"] = r.get("name")
        rec["cn"] = r.get("supplier") or "—"
        rec["br"] = "—"
        rec["emp"] = (r.get("owner") or "").split("@")[0]
        rec["st"] = st
        rec["pendRole"] = pend
        rec["stageTxt"] = ws or (r.get("status") or "")
        rec["reqAt"] = str(r.get("creation") or "")
        rec["gross"] = r.get("grand_total") or 0
        rec["net"] = r.get("grand_total") or 0
        rec["benefit"] = 0
        out.append(rec)

    # ─── auto-pick a default role view from the user's roles ──────────────────
    # priority: discount levels → purchase → accounts/coo → else ALL
    myView = "ALL"
    if "System Manager" in roles or "Administrator" in roles:
        myView = "ALL"
    elif "life_discount_l3" in roles:
        myView = "DISC_L3"
    elif "life_discount_l2" in roles:
        myView = "DISC_L2"
    elif "life_discount_l1" in roles:
        myView = "DISC_L1"
    elif "Purchase Manager" in roles or "Purchase User" in roles or "Purchase Master Manager" in roles:
        myView = "PO"
    elif "Stock Manager" in roles or "Stock User" in roles:
        myView = "STOCK"
    elif "Auditor" in roles:
        myView = "AUDIT"
    elif "Accounts Manager" in roles or "Head of Accounts" in roles or "Accounts User" in roles:
        myView = "ACCT"

    frappe.response["message"] = {
        "data": out,
        "count": len(out),
        "me": me,
        "myRoles": roles,
        "myView": myView
    }
