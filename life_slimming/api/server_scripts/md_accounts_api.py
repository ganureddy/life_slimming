"""md_accounts_api

Original API: md_accounts_api
Source modified: 2026-08-04 15:42:16.005525
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
    #  SERVER SCRIPT (API)  —  md_accounts_api
    #  Script Type : API   ·   API Method : md_accounts_api
    #  URL: /api/method/md_accounts_api?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    #
    #  Returns for the MD dashboard "Accounts" module:
    #   - targets[]      per-branch Target vs Achievement (from Week Achive rows
    #                    whose parent Week Target header overlaps the date range)
    #   - collections{}  from Payment Entry: with-GST (received) and without-GST
    #   - clusters[]     TG / AP rollup of target vs achievement vs collected
    #   - totals{}
    #
    #  safe_exec-safe: dict params only, no None, no reserved aliases,
    #  no try/except, no % literals, no slicing.
    # =====================================================================

    args = frappe.form_dict or {}
    to_date = args.get("to_date")
    from_date = args.get("from_date")
    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.get_first_day(to_date)

    # ---- cluster map (branch NAME -> cluster) ----
    tg_branches = ["Kukatpally", "Himayathnagar", "Gachibowli", "SR Nagar",
                   "Dilsukhnagar", "Madhapur", "Banjara Hills", "Chandanagar"]
    ap_branches = ["Vizag", "Vijayawada", "Nellore"]

    def cluster_of(branch):
        b = branch or ""
        i = 0
        while i < len(ap_branches):
            if b == ap_branches[i]:
                return "AP"
            i = i + 1
        return "TG"

    # ---------- 1. TARGET (child Week Achive, parent overlapping range) --
    # Only the target comes from the sheet; achievement is computed live below
    # from Payment Entry with the GST/loan cut rules.
    tgt_rows = _read_sql("""
    SELECT wa.branch                       AS branch,
           SUM(wa.targeted_amount)         AS target
    FROM `tabWeek Achive` wa
    INNER JOIN `tabWeek Target vs Achive With Cuttings` h ON h.name = wa.parent
    WHERE h.docstatus < 2
      AND h.from_date <= %(t)s
      AND h.to_date   >= %(f)s
    GROUP BY wa.branch
    ORDER BY target DESC
""", {"f": from_date, "t": to_date}, as_dict=True)

    # ---------- 2. COLLECTIONS + ACHIEVEMENT from Payment Entry ----------
    # gross (with GST) = received_amount.
    # ACHIEVEMENT = net of cut: loan modes cut 15%, others cut 5%.
    #   loan mode  -> paid * 0.85
    #   other mode -> paid * 0.95
    # grouped by cost_center + mode_of_payment so the right cut applies.
    loan_modes = ["bajaj card charges", "sai roshini card charges", "fibe finance",
                  "carepay", "savein fintech card charges",
                  "loan tap / uno finance charges", "shopse", "liqui loans charges"]

    pe_rows = _read_sql("""
    SELECT COALESCE(cost_center, 'Unassigned') AS cc,
           COALESCE(mode_of_payment, '')       AS pmode,
           SUM(received_amount)                AS gross
    FROM `tabPayment Entry`
    WHERE docstatus = 1
      AND payment_type = 'Receive'
      AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY cost_center, mode_of_payment
""", {"f": from_date, "t": to_date}, as_dict=True)

    coll_map = {}
    ach_map = {}
    for r in pe_rows:
        nm = (r.get("cc") or "").replace(" - LSACPL", "").strip()
        gross = float(r.get("gross") or 0)
        mode = (r.get("pmode") or "").lower().strip()
        is_loan = 0
        j = 0
        while j < len(loan_modes):
            if loan_modes[j] == mode:
                is_loan = 1
            j = j + 1
        if is_loan == 1:
            ach = gross * 0.85
        else:
            ach = gross * 0.95
        if nm not in coll_map:
            coll_map[nm] = 0.0
            ach_map[nm] = 0.0
        coll_map[nm] = coll_map[nm] + gross
        ach_map[nm] = ach_map[nm] + ach

    # ---------- 3. assemble per-branch target rows + achievement ----------
    targets = []
    tot_target = 0.0
    tot_ach = 0.0
    tot_def = 0.0
    tot_coll_g = 0.0
    for r in tgt_rows:
        br = r.get("branch") or "Unknown"
        tg = float(r.get("target") or 0)
        ac = ach_map.get(br, 0.0)
        df = tg - ac
        coll_g = coll_map.get(br, 0.0)
        d = {}
        d["branch"] = br
        d["cluster"] = cluster_of(br)
        d["target"] = tg
        d["achieved"] = ac
        d["deficit"] = df
        if tg > 0:
            d["pct"] = round(ac / tg * 100.0, 1)
        else:
            d["pct"] = 0.0
        d["coll_gst"] = coll_g
        d["coll_net"] = round(coll_g / 1.05, 2)
        targets.append(d)
        tot_target = tot_target + tg
        tot_ach = tot_ach + ac
        tot_def = tot_def + df
        tot_coll_g = tot_coll_g + coll_g

    # branches that had collections but no target row — still surface them
    for nm in coll_map:
        seen = 0
        for d in targets:
            if d["branch"] == nm:
                seen = 1
        if seen == 0:
            cg = coll_map[nm]
            acn = ach_map.get(nm, 0.0)
            d = {}
            d["branch"] = nm
            d["cluster"] = cluster_of(nm)
            d["target"] = 0.0
            d["achieved"] = acn
            d["deficit"] = 0.0 - acn
            d["pct"] = 0.0
            d["coll_gst"] = cg
            d["coll_net"] = round(cg / 1.05, 2)
            targets.append(d)
            tot_coll_g = tot_coll_g + cg
            tot_ach = tot_ach + acn

    # ---------- 4. cluster rollup ----------
    cl_tg = {}
    cl_tg["id"] = "TG"
    cl_tg["name"] = "Telangana Cluster"
    cl_tg["heads"] = "Teena, Bindu, Radhika"
    cl_tg["target"] = 0.0
    cl_tg["achieved"] = 0.0
    cl_tg["coll_gst"] = 0.0
    cl_ap = {}
    cl_ap["id"] = "AP"
    cl_ap["name"] = "Andhra Cluster"
    cl_ap["heads"] = "Navya"
    cl_ap["target"] = 0.0
    cl_ap["achieved"] = 0.0
    cl_ap["coll_gst"] = 0.0

    for d in targets:
        if d["cluster"] == "AP":
            cl_ap["target"] = cl_ap["target"] + d["target"]
            cl_ap["achieved"] = cl_ap["achieved"] + d["achieved"]
            cl_ap["coll_gst"] = cl_ap["coll_gst"] + d["coll_gst"]
        else:
            cl_tg["target"] = cl_tg["target"] + d["target"]
            cl_tg["achieved"] = cl_tg["achieved"] + d["achieved"]
            cl_tg["coll_gst"] = cl_tg["coll_gst"] + d["coll_gst"]

    clusters = []
    for c in [cl_tg, cl_ap]:
        if c["target"] > 0:
            c["pct"] = round(c["achieved"] / c["target"] * 100.0, 1)
        else:
            c["pct"] = 0.0
        c["coll_net"] = round(c["coll_gst"] / 1.05, 2)
        clusters.append(c)

    # ---------- 5. totals ----------
    totals = {}
    totals["target"] = tot_target
    totals["achieved"] = tot_ach
    totals["deficit"] = tot_def
    totals["coll_gst"] = tot_coll_g
    totals["coll_net"] = round(tot_coll_g / 1.05, 2)
    if tot_target > 0:
        totals["pct"] = round(tot_ach / tot_target * 100.0, 1)
    else:
        totals["pct"] = 0.0

    out = {}
    out["from_date"] = from_date
    out["to_date"] = to_date
    out["targets"] = targets
    out["clusters"] = clusters
    out["totals"] = totals
    frappe.response["message"] = out
