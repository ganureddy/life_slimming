"""cluster_dashboard_api

Original API: cluster_dashboard_api
Source modified: 2026-08-27 12:17:37.554461
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
    #  SERVER SCRIPT (API) — cluster_dashboard_api
    #  URL: /api/method/cluster_dashboard_api?from_date=...&to_date=...&cluster=...
    #
    #  Create as: Server Script > New
    #    Script Type : API
    #    API Method  : cluster_dashboard_api
    #
    #  WHAT YOU MUST FILL IN BELOW before this is correct:
    #    CLUSTER_MAP   — which branches belong to which cluster
    #    USER_CLUSTER  — which Cluster Head user sees which cluster
    #  Your 11 active branches (from Branch doctype) are listed in
    #  ALL_BRANCHES below so you can just copy/paste names into groups.
    # =====================================================================

    args = frappe.form_dict or {}
    to_date = args.get("to_date")
    from_date = args.get("from_date")
    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.get_first_day(to_date)

    # ---------------------------------------------------------------
    # CONFIG — EDIT THIS SECTION
    # ---------------------------------------------------------------

    ALL_BRANCHES = [
        "Kukatpally", "Madhapur", "Himayathnagar", "Vijayawada",
        "SR Nagar", "Chandanagar", "Gachibowli", "Vizag",
        "Nellore", "Dilsukhnagar", "Banjara Hills"
    ]

    # Group the branches above into clusters. Example:
    # CLUSTER_MAP = {
    #     "Hyderabad Central": ["Kukatpally", "Madhapur", "Gachibowli"],
    #     "Hyderabad South":   ["Himayathnagar", "Banjara Hills", "SR Nagar", "Chandanagar", "Dilsukhnagar"],
    #     "AP Coastal":        ["Vijayawada", "Vizag", "Nellore"],
    # }
    CLUSTER_MAP = {}

    # Map each Cluster Head's login email to the cluster they should land on.
    # Example:
    # USER_CLUSTER = {
    #     "clusterhead1@lifescc.com": "Hyderabad Central",
    # }
    USER_CLUSTER = {}

    # ---------------------------------------------------------------
    # RESOLVE WHICH BRANCHES TO SHOW
    # ---------------------------------------------------------------

    requested = (args.get("cluster") or "").strip()
    user = frappe.session.user

    if requested and requested in CLUSTER_MAP:
        branches = CLUSTER_MAP[requested]
        cluster_name = requested
    elif requested == "ALL":
        branches = ALL_BRANCHES
        cluster_name = "All Branches"
    elif user in USER_CLUSTER and USER_CLUSTER.get(user) in CLUSTER_MAP:
        cluster_name = USER_CLUSTER.get(user)
        branches = CLUSTER_MAP[cluster_name]
    else:
        branches = ALL_BRANCHES
        cluster_name = "All Branches"

    pe_has_branch = bool(frappe.get_meta("Payment Entry").get_field("branch"))

    rows = []
    totals = {
        "sales_amt": 0.0,
        "sales_count": 0,
        "outstanding": 0.0,
        "collections": 0.0
    }

    for b in branches:

        si = _read_sql("""
        SELECT COUNT(name) AS cnt, SUM(grand_total) AS amt, SUM(outstanding_amount) AS outs
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND posting_date BETWEEN %(f)s AND %(t)s AND branch = %(b)s
    """, {"f": from_date, "t": to_date, "b": b}, as_dict=True)

        if pe_has_branch:
            pe = _read_sql("""
            SELECT SUM(paid_amount) AS amt
            FROM `tabPayment Entry`
            WHERE docstatus = 1 AND posting_date BETWEEN %(f)s AND %(t)s
              AND branch = %(b)s AND payment_type = 'Receive'
        """, {"f": from_date, "t": to_date, "b": b}, as_dict=True)
        else:
            pe = [{"amt": 0}]

        s_amt = float(si[0].get("amt") or 0) if si else 0.0
        s_cnt = int(si[0].get("cnt") or 0) if si else 0
        s_out = float(si[0].get("outs") or 0) if si else 0.0
        c_amt = float(pe[0].get("amt") or 0) if pe else 0.0

        rows.append({
            "branch": b,
            "sales_amt": s_amt,
            "sales_count": s_cnt,
            "outstanding": s_out,
            "collections": c_amt
        })

        totals["sales_amt"] = totals["sales_amt"] + s_amt
        totals["sales_count"] = totals["sales_count"] + s_cnt
        totals["outstanding"] = totals["outstanding"] + s_out
        totals["collections"] = totals["collections"] + c_amt

    out = {
        "cluster": cluster_name,
        "branches": branches,
        "from_date": from_date,
        "to_date": to_date,
        "rows": rows,
        "totals": totals,
        "available_clusters": list(CLUSTER_MAP.keys())
    }

    frappe.response["message"] = out
