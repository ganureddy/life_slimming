"""md_command_center_api

Original API: md_command_center_api
Source modified: 2026-08-26 12:12:50.501136
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
    #  SERVER SCRIPT  (API type)
    #  Name        : md_command_center_api
    #  Script Type : API
    #  API Method  : md_command_center_api
    #  Allow Guest : No  (dashboard runs as a logged-in MD/COO user)
    #  Endpoint    : /api/method/md_command_center_api?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    #
    #  Feeds the MD / Founder Command Dashboard (Web Page: md-dashboard).
    #  The frontend applyLive() consumes these keys:
    #    from_date, to_date, branches[], series[], verticals[], people{},
    #    approvals{discount,p2p,c2c}, area_managers[], top_performers[],
    #    roles[], lead_channels[], attrition[], totals{}
    #
    #  safe_exec rules honoured:
    #    - no f-strings, no imports, no tuple unpacking
    #    - no augmented dict assignment (d[k] = d[k] + v spelled out)
    #    - no frappe.get_roles / no bench access
    #    - only frappe.db.sql / frappe.utils helpers
    # =====================================================================

    # ---------- 1. resolve date range ----------
    args = frappe.form_dict or {}
    from_date = args.get("from_date")
    to_date = args.get("to_date")

    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.get_first_day(to_date)

    # 12-month window start for the trend series
    series_start = frappe.utils.add_months(frappe.utils.get_first_day(to_date), -11)

    # =====================================================================
    #  PART A  ·  md_command_center_api  ·  ADD LIVE PER-BRANCH NET (real tax)
    # =====================================================================
    #  WHAT THIS DOES
    #  The dashboard was showing "Net" as gross x 0.95 (a flat 5% guess).
    #  You asked for LIVE per-invoice tax where available. ERPNext already
    #  stores the true pre-tax value on every Sales Invoice as `base_net_total`
    #  (grand_total minus its own tax rows). Summing that per cost center gives
    #  the real net with the actual tax each invoice carried -- no ÷1.05 guess.
    #
    #  HOW TO APPLY  (System Console is not needed -- this is a Server Script edit)
    #  1. Open  Server Script  ->  md_command_center_api
    #  2. Find section "# ---------- 2. core money by cost center ..."
    #  3. Replace the inv_rows SQL + the loop that builds branches with the
    #     block below (it just adds  SUM(base_net_total) AS net  and b["net"]).
    #  4. Add the tot_net accumulator + totals["net"] line (shown at bottom).
    #  5. Save.  (No bench, no cache clear needed for Server Scripts.)
    #
    #  safe_exec safe: no imports, no f-strings, no tuple-unpack, no aug-assign.
    # =====================================================================


    # ---------- 2. core money by cost center (Sales Invoice) ----------
    # CHANGED: added SUM(base_net_total) AS net  -> real per-invoice net
    inv_rows = _read_sql("""
    SELECT
        COALESCE(cost_center, 'Unassigned')  AS cc,
        SUM(grand_total)                     AS gross,
        SUM(base_net_total)                  AS net,
        SUM(outstanding_amount)              AS outs,
        COUNT(name)                          AS inv
    FROM `tabSales Invoice`
    WHERE docstatus = 1
      AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY cost_center
    ORDER BY gross DESC
""", {"f": from_date, "t": to_date}, as_dict=True)

    branches = []
    tot_gross = 0.0
    tot_net = 0.0          # NEW
    tot_coll = 0.0
    tot_out = 0.0
    tot_inv = 0

    for r in inv_rows:
        g = float(r.get("gross") or 0)
        nt = float(r.get("net") or 0)     # NEW real net
        o = float(r.get("outs") or 0)
        n = int(r.get("inv") or 0)
        b = {}
        b["cc"] = r.get("cc")
        b["gross"] = g
        b["net"] = nt                     # NEW  -> frontend reads b.net
        b["coll"] = 0.0
        b["out"] = o
        b["inv"] = n
        branches.append(b)
        tot_gross = tot_gross + g
        tot_net = tot_net + nt            # NEW
        tot_out = tot_out + o
        tot_inv = tot_inv + n

    # NOTE: when you add PE-only cost centers later in section 2b, also set
    #       nb["net"] = 0.0  on those synthetic rows (they have no invoices).
    #       Add this one line inside that existing block:
    #           nb["net"] = 0.0


    # ---------- 15. totals block  (ADD ONE LINE) ----------
    # Leave everything you already have; just add:

    # ---------- 2b. real collections from Payment Entry (received) ----------
    # invoice paid_amount is not written back here, so collections come from
    # Payment Entry (payment_type = Receive), grouped by cost center.
    pe_rows = _read_sql("""
    SELECT COALESCE(cost_center, 'Unassigned') AS cc,
           SUM(received_amount)                AS coll
    FROM `tabPayment Entry`
    WHERE docstatus = 1
      AND payment_type = 'Receive'
      AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY cost_center
""", {"f": from_date, "t": to_date}, as_dict=True)

    pe_map = {}
    for r in pe_rows:
        c = float(r.get("coll") or 0)
        pe_map[r.get("cc")] = c
        tot_coll = tot_coll + c

    # attach collections to branch rows; add PE-only cost centers too
    for b in branches:
        if b["cc"] in pe_map:
            b["coll"] = pe_map[b["cc"]]
    for cc_key in pe_map:
        seen = 0
        for b in branches:
            if b["cc"] == cc_key:
                seen = 1
        if seen == 0:
            nb = {}
            nb["cc"] = cc_key
            nb["gross"] = 0.0
            nb["coll"] = pe_map[cc_key]
            nb["out"] = 0.0
            nb["inv"] = 0
            branches.append(nb)

    # ---------- 3. per-branch active client counts (distinct patients) ----------
    cli_rows = _read_sql("""
    SELECT COALESCE(cost_center,'Unassigned') AS cc,
           COUNT(DISTINCT patient) AS clients
    FROM `tabSales Invoice`
    WHERE docstatus = 1
      AND posting_date BETWEEN %(f)s AND %(t)s
      AND patient IS NOT NULL
    GROUP BY cost_center
""", {"f": from_date, "t": to_date}, as_dict=True)

    cli_map = {}
    for r in cli_rows:
        cli_map[r.get("cc")] = int(r.get("clients") or 0)

    for b in branches:
        if b["cc"] in cli_map:
            b["clients"] = cli_map[b["cc"]]

    # ---------- 4. 12-month company trend (revenue + collections) ----------
    # Revenue from Sales Invoice; collections from Payment Entry (received).
    ser_rows = _read_sql("""
    SELECT YEAR(posting_date)  AS yy,
           MONTH(posting_date) AS mm,
           SUM(grand_total)/100000  AS rev
    FROM `tabSales Invoice`
    WHERE docstatus = 1
      AND posting_date >= %(s)s AND posting_date <= %(t)s
    GROUP BY YEAR(posting_date), MONTH(posting_date)
    ORDER BY YEAR(posting_date) ASC, MONTH(posting_date) ASC
""", {"s": series_start, "t": to_date}, as_dict=True)

    pe_ser = _read_sql("""
    SELECT YEAR(posting_date)  AS yy,
           MONTH(posting_date) AS mm,
           SUM(received_amount)/100000 AS coll
    FROM `tabPayment Entry`
    WHERE docstatus = 1
      AND payment_type = 'Receive'
      AND posting_date >= %(s)s AND posting_date <= %(t)s
    GROUP BY YEAR(posting_date), MONTH(posting_date)
""", {"s": series_start, "t": to_date}, as_dict=True)

    pe_ser_map = {}
    for r in pe_ser:
        yk = str(int(r.get("yy") or 0)) + "-" + str(int(r.get("mm") or 0))
        pe_ser_map[yk] = float(r.get("coll") or 0)

    mon_abbr = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    series = []
    for r in ser_rows:
        yy = int(r.get("yy") or 0)
        mm = int(r.get("mm") or 0)
        yy2 = yy - (yy // 100) * 100
        lbl = mon_abbr[mm] + " " + str(yy2)
        s = {}
        s["m"] = lbl
        s["rev"] = float(r.get("rev") or 0)
        ykey = str(yy) + "-" + str(mm)
        s["coll"] = pe_ser_map.get(ykey, 0.0)
        series.append(s)

    # ---------- 5. verticals (revenue by item group) ----------
    vert_rows = _read_sql("""
    SELECT COALESCE(i.item_group, 'Other') AS name,
           SUM(sii.base_net_amount)        AS amt
    FROM `tabSales Invoice Item` sii
    INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
    LEFT JOIN `tabItem` i ON i.name = sii.item_code
    WHERE si.docstatus = 1
      AND si.posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY i.item_group
    ORDER BY amt DESC
    LIMIT 8
""", {"f": from_date, "t": to_date}, as_dict=True)

    verticals = []
    for r in vert_rows:
        v = {}
        v["name"] = r.get("name")
        v["amt"] = float(r.get("amt") or 0)
        verticals.append(v)

    # ---------- 6. people: headcount by branch (Active employees) ----------
    ppl_rows = _read_sql("""
    SELECT COALESCE(branch, 'Unassigned') AS branch,
           COUNT(name) AS total,
           SUM(CASE WHEN gender = 'Male' THEN 1 ELSE 0 END) AS male
    FROM `tabEmployee`
    WHERE status = 'Active'
    GROUP BY branch
""", {}, as_dict=True)

    people = {}
    for r in ppl_rows:
        key = r.get("branch")
        d = {}
        d["total"] = int(r.get("total") or 0)
        d["male"] = int(r.get("male") or 0)
        people[key] = d

    # ---------- 7. roles: headcount by designation ----------
    role_rows = _read_sql("""
    SELECT COALESCE(designation, 'Unassigned') AS role,
           COUNT(name) AS cnt
    FROM `tabEmployee`
    WHERE status = 'Active'
    GROUP BY designation
    ORDER BY cnt DESC
    LIMIT 12
""", {}, as_dict=True)

    roles = []
    for r in role_rows:
        d = {}
        d["role"] = r.get("role")
        d["count"] = int(r.get("cnt") or 0)
        roles.append(d)

    # ---------- 8. area managers + trainee AMs (from designation) ----------
    am_rows = _read_sql("""
    SELECT name AS emp, employee_name AS ename,
           COALESCE(branch,'') AS branch,
           COALESCE(designation,'') AS desig
    FROM `tabEmployee`
    WHERE status = 'Active'
      AND designation IN ('Area Manager', 'Area Manager (Trainee)',
                          'Area Slimming Manager')
    ORDER BY designation ASC
""", {}, as_dict=True)

    area_managers = []
    for r in am_rows:
        d = {}
        d["emp"] = r.get("emp")
        d["name"] = r.get("ename")
        d["branch"] = r.get("branch")
        dg = (r.get("desig") or "").lower()
        if dg.find("trainee") > -1:
            d["trainee"] = 1
        else:
            d["trainee"] = 0
        area_managers.append(d)

    # ---------- 8b. branch heads (Center Manager / Clinic Manager) ----------
    # branch names differ from cost-center names, so key is normalised
    # (lowercase, spaces stripped) and matched on the frontend via ccToCode.
    head_rows = _read_sql("""
    SELECT employee_name AS ename,
           COALESCE(branch,'') AS branch,
           COALESCE(designation,'') AS desig
    FROM `tabEmployee`
    WHERE status = 'Active'
      AND designation IN ('Center Manager', 'Clinic Manager',
                          'CM(TRAINEE)', 'Assistant Centre Manager', 'ACM')
    ORDER BY FIELD(designation,
                   'Center Manager','Clinic Manager','CM(TRAINEE)',
                   'Assistant Centre Manager','ACM') ASC
""", {}, as_dict=True)

    branch_heads = {}
    for r in head_rows:
        br = r.get("branch") or ""
        key = br.lower().replace(" ", "")
        # first (most senior by FIELD order) head wins per branch
        if key and key not in branch_heads:
            h = {}
            h["name"] = r.get("ename")
            h["branch"] = br
            h["role"] = r.get("desig")
            branch_heads[key] = h

    # ---------- 9. attrition per branch (Notice/Resigned/Left vs active) ----------
    attr_rows = _read_sql("""
    SELECT COALESCE(branch,'Unassigned') AS branch,
           COUNT(name) AS total,
           SUM(CASE WHEN status IN ('Left','Suspended')
                     OR custom_employment_status IN ('Notice','Resigned')
                THEN 1 ELSE 0 END) AS leaving
    FROM `tabEmployee`
    GROUP BY branch
""", {}, as_dict=True)

    attrition = []
    for r in attr_rows:
        tot = int(r.get("total") or 0)
        lv = int(r.get("leaving") or 0)
        d = {}
        d["branch"] = r.get("branch")
        if tot > 0:
            d["pct"] = round(float(lv) / float(tot) * 100.0, 1)
        else:
            d["pct"] = 0.0
        attrition.append(d)

    # ---------- 10. top performers (custom_incentive_employee_name) ----------
    tp_rows = _read_sql("""
    SELECT custom_incentive_employee_name AS name,
           COALESCE(cost_center,'') AS branch,
           SUM(grand_total) AS rev,
           COUNT(name) AS inv
    FROM `tabSales Invoice`
    WHERE docstatus = 1
      AND posting_date BETWEEN %(f)s AND %(t)s
      AND custom_incentive_employee_name IS NOT NULL
      AND custom_incentive_employee_name != ''
    GROUP BY custom_incentive_employee_name, cost_center
    ORDER BY rev DESC
    LIMIT 10
""", {"f": from_date, "t": to_date}, as_dict=True)

    top_performers = []
    for r in tp_rows:
        d = {}
        d["name"] = r.get("name")
        d["branch"] = r.get("branch")
        d["rev"] = float(r.get("rev") or 0)
        d["inv"] = int(r.get("inv") or 0)
        top_performers.append(d)

    # ---------- 11. lead channels (source-wise) ----------
    # Leads created in range, grouped by source. (No try/except — safe_exec's
    # RestrictedPython rejects exception handlers, which was the 500.)
    lead_channels = []
    lead_rows = _read_sql("""
    SELECT COALESCE(source,'Unknown') AS src,
           COUNT(name) AS leads
    FROM `tabLead`
    WHERE creation BETWEEN %(f)s AND %(t)s
    GROUP BY source
    ORDER BY leads DESC
    LIMIT 8
""", {"f": from_date, "t": to_date + " 23:59:59"}, as_dict=True)
    for r in lead_rows:
        d = {}
        d["src"] = r.get("src")
        d["leads"] = int(r.get("leads") or 0)
        d["conv"] = 0.0
        lead_channels.append(d)

    # ---------- 12. approvals: discount (Discount Approval Request) ----------
    disc_pending = []
    disc_rows = _read_sql("""
    SELECT name, request_id, linked_invoice, branch, requested_by,
           bill_total, approval_level, selected_approver,
           requested_discount_pct, reason
    FROM `tabDiscount Approval Request`
    WHERE status = 'Pending'
    ORDER BY creation DESC
    LIMIT 100
""", {}, as_dict=True)

    for r in disc_rows:
        d = {}
        d["id"] = r.get("request_id") or r.get("name")
        d["invoice"] = r.get("linked_invoice")
        d["branch"] = r.get("branch")
        d["by"] = r.get("requested_by")
        d["approver"] = r.get("selected_approver")
        d["bill"] = float(r.get("bill_total") or 0)
        d["pct"] = float(r.get("requested_discount_pct") or 0)
        d["level"] = r.get("approval_level")
        d["reason"] = r.get("reason")
        disc_pending.append(d)

    # ---------- 13. approvals: P2P (same client package->package) ----------
    p2p_pending = []
    p2p_rows = _read_sql("""
    SELECT name, client_name, name1, branch,
           final_amount_payable, approval_stage
    FROM `tabLIFE Client Package Conversion Same Client Package To Package`
    WHERE COALESCE(final_approval_status,'') = ''
    ORDER BY creation DESC
    LIMIT 100
""", {}, as_dict=True)

    for r in p2p_rows:
        d = {}
        d["id"] = r.get("name")
        d["client"] = r.get("name1") or r.get("client_name")
        d["branch"] = r.get("branch")
        d["amount"] = float(r.get("final_amount_payable") or 0)
        d["stage"] = r.get("approval_stage")
        p2p_pending.append(d)

    # ---------- 14. approvals: C2C (client -> client transfer) ----------
    c2c_pending = []
    c2c_rows = _read_sql("""
    SELECT name, client_full_name, name1, branch, receiving_branch,
           total_amount, conversion_status
    FROM `tabClient Package Conversion Client To Client`
    WHERE COALESCE(conversion_status,'') NOT IN ('Approved','Rejected','Completed')
    ORDER BY creation DESC
    LIMIT 100
""", {}, as_dict=True)

    for r in c2c_rows:
        d = {}
        d["id"] = r.get("name")
        d["client"] = r.get("name1") or r.get("client_full_name")
        d["branch"] = r.get("branch")
        d["to_branch"] = r.get("receiving_branch")
        d["amount"] = float(r.get("total_amount") or 0)
        d["stage"] = r.get("conversion_status")
        c2c_pending.append(d)

    approvals = {}
    disc_block = {}
    disc_block["pending"] = disc_pending
    p2p_block = {}
    p2p_block["pending"] = p2p_pending
    c2c_block = {}
    c2c_block["pending"] = c2c_pending
    approvals["discount"] = disc_block
    approvals["p2p"] = p2p_block
    approvals["c2c"] = c2c_block

    # ---------- 15. totals block ----------
    totals = {}
    totals["gross"] = tot_gross
    totals["collections"] = tot_coll
    totals["outstanding"] = tot_out
    totals["invoices"] = tot_inv
    totals["disc_pending"] = len(disc_pending)
    totals["p2p_pending"] = len(p2p_pending)
    totals["c2c_pending"] = len(c2c_pending)
    totals["approvals_pending"] = len(disc_pending) + len(p2p_pending) + len(c2c_pending)
    totals["net"] = tot_net
    # ---------- 16. final payload ----------
    out = {}
    out["from_date"] = from_date
    out["to_date"] = to_date
    out["branches"] = branches
    out["series"] = series
    out["verticals"] = verticals
    out["people"] = people
    out["roles"] = roles
    out["area_managers"] = area_managers
    out["branch_heads"] = branch_heads
    out["attrition"] = attrition
    out["top_performers"] = top_performers
    out["lead_channels"] = lead_channels
    out["approvals"] = approvals
    out["totals"] = totals

    frappe.response["message"] = out
