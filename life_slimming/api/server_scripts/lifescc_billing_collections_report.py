"""lifescc.billing.collections_report

Original API: lifescc.billing.collections_report
Source modified: 2026-07-27 11:49:32.259519
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
    # ═══════════════════════════════════════════════════════════════════
    # SERVER SCRIPT  ·  lifescc.billing.collections_report  ·  FIXED
    # Type: API   ·   Method: lifescc.billing.collections_report
    #
    # FIX: safe_exec blocks the ".format" attribute
    #      ("SyntaxError: format is an unsafe attribute"), which made the
    #      Collections tab return 500. The SQL is now assembled with plain
    #      string concatenation instead of str.format(). Logic unchanged.
    # ═══════════════════════════════════════════════════════════════════

    from_date = frappe.form_dict.get("from_date")
    to_date = frappe.form_dict.get("to_date")
    branch = (frappe.form_dict.get("branch") or "").strip()

    if not from_date or not to_date:
        frappe.throw("from_date and to_date are required")

    # This report uses raw SQL, so Frappe's DocType permissions do not filter
    # its rows. Apply the same Branch User Permissions returned by bootstrap.
    permitted = frappe.get_all(
        "User Permission",
        filters={"user": frappe.session.user, "allow": "Branch"},
        fields=["for_value"], limit_page_length=0,
    )
    allowed_branches = []
    for permission in permitted:
        name = permission.get("for_value")
        if name and name not in ("Head Office", "Testing Branch") and name not in allowed_branches:
            allowed_branches.append(name)
    if allowed_branches and branch and branch not in allowed_branches:
        frappe.throw("You do not have access to this branch.", frappe.PermissionError)

    branch_cond_inv = ""
    branch_cond_pe = ""
    params = {"from_date": from_date, "to_date": to_date}
    if branch:
        branch_cond_inv = "AND si.branch = %(branch)s"
        branch_cond_pe = "AND pe.branch = %(branch)s"
        params["branch"] = branch
    elif allowed_branches:
        placeholders = []
        for index, name in enumerate(allowed_branches):
            key = "allowed_branch_" + str(index)
            params[key] = name
            placeholders.append("%(" + key + ")s")
        branch_cond_inv = "AND si.branch IN (" + ",".join(placeholders) + ")"
        branch_cond_pe = "AND pe.branch IN (" + ",".join(placeholders) + ")"

    # ── BILLED side: Sales Invoice totals for the period, split by GST flag ──
    billed_sql = (
        "SELECT "
        "  si.branch AS branch, "
        "  SUM(CASE WHEN IFNULL(si.total_taxes_and_charges,0) > 0 "
        "           THEN si.base_grand_total ELSE 0 END) AS billed_gst, "
        "  SUM(CASE WHEN IFNULL(si.total_taxes_and_charges,0) <= 0 "
        "           THEN si.base_grand_total ELSE 0 END) AS billed_nongst, "
        "  SUM(IFNULL(si.base_grand_total,0)) AS billed_total, "
        "  SUM(IFNULL(si.base_net_total,0)) AS billed_ex_gst, "
        "  SUM(IFNULL(si.outstanding_amount,0)) AS outstanding "
        "FROM `tabSales Invoice` si "
        "WHERE si.docstatus = 1 "
        "  AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s "
        + branch_cond_inv +
        " GROUP BY si.branch"
    )
    billed_rows = _read_sql(billed_sql, params, as_dict=True)

    # ── COLLECTED side: Payment Entry (Receive) joined to referenced invoices ──
    collected_sql = (
        "SELECT "
        "  pe.branch AS branch, "
        "  SUM(CASE WHEN IFNULL(si.total_taxes_and_charges,0) > 0 "
        "           THEN per.allocated_amount ELSE 0 END) AS collected_gst, "
        "  SUM(CASE WHEN IFNULL(si.total_taxes_and_charges,0) <= 0 "
        "           THEN per.allocated_amount ELSE 0 END) AS collected_nongst "
        "FROM `tabPayment Entry` pe "
        "INNER JOIN `tabPayment Entry Reference` per "
        "  ON per.parent = pe.name AND per.reference_doctype = 'Sales Invoice' "
        "INNER JOIN `tabSales Invoice` si "
        "  ON si.name = per.reference_name "
        "WHERE pe.docstatus = 1 "
        "  AND pe.payment_type = 'Receive' "
        "  AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s "
        + branch_cond_pe +
        " GROUP BY pe.branch"
    )
    collected_rows = _read_sql(collected_sql, params, as_dict=True)

    # ── merge the two sides on branch name ──
    merged = {}
    BLANK = {"billed_gst": 0, "billed_nongst": 0, "billed_total": 0,
             "billed_ex_gst": 0, "outstanding": 0,
             "collected_gst": 0, "collected_nongst": 0}

    for r in billed_rows:
        b = r.branch or "—"
        if b not in merged:
            row = {"branch": b}
            for k in BLANK:
                row[k] = 0
            merged[b] = row
        merged[b]["billed_gst"] = r.billed_gst or 0
        merged[b]["billed_nongst"] = r.billed_nongst or 0
        merged[b]["billed_total"] = r.billed_total or 0
        merged[b]["billed_ex_gst"] = r.billed_ex_gst or 0
        merged[b]["outstanding"] = r.outstanding or 0

    for r in collected_rows:
        b = r.branch or "—"
        if b not in merged:
            row = {"branch": b}
            for k in BLANK:
                row[k] = 0
            merged[b] = row
        merged[b]["collected_gst"] = r.collected_gst or 0
        merged[b]["collected_nongst"] = r.collected_nongst or 0

    # derived: total paid, and paid excluding GST (GST portion is 5%)
    for b in merged:
        row = merged[b]
        paid = (row["collected_gst"] or 0) + (row["collected_nongst"] or 0)
        row["collected_total"] = paid
        # GST-bearing collections carry 5% tax; strip it for the ex-GST view
        row["collected_ex_gst"] = round(
            (row["collected_gst"] or 0) / 1.05 + (row["collected_nongst"] or 0), 2
        )

    rows = sorted(merged.values(), key=lambda x: x["branch"])

    frappe.response["message"] = {"rows": rows}
