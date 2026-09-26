"""report_master_api

Original API: report_master_api
Source modified: 2026-08-21 20:07:44.259642
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
    # # =====================================================================
    # #  SERVER SCRIPT  (API type)
    # #  Name        : report_master_api
    # #  Script Type : API
    # #  API Method  : report_master_api
    # #  Allow Guest : No
    # #  Endpoint    : /api/method/report_master_api?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    # #
    # #  Feeds the LIFE MASTER REPORTS web page (report-master).
    # #  Returns LIVE row-level arrays that the dashboard's report engine
    # #  consumes directly (money + collections + client reports):
    # #     branches[]  invoices[]  clients[]  employees[]  totals{}
    # #
    # #  Reports powered: 1 Executive, 10 Revenue, 12 Invoice Register,
    # #     110-115 Collections/Dues, 20 Enrolment(light), 30 Client Search.
    # #  Clinical reports (21 Results, 22 Card Status) are NOT fed here --
    # #     the frontend marks them "clinical feed pending".
    # #
    # #  safe_exec rules honoured:
    # #    - no try/except, no f-strings, no .format(), no imports
    # #    - no tuple unpacking in for-loops, no augmented assignment (x += y)
    # #    - no frappe.get_roles / frappe.db.commit / frappe.clear_cache
    # #    - % formatting only, explicit reassignment for aggregation
    # #    - frappe.form_dict for params
    # # =====================================================================

    # # ---------- 1. date range ----------
    # args = frappe.form_dict or {}
    # from_date = args.get("from_date")
    # to_date = args.get("to_date")

    # if not to_date:
    #     to_date = frappe.utils.nowdate()
    # if not from_date:
    #     from_date = frappe.utils.add_days(to_date, -30)

    # to_date_end = to_date + " 23:59:59"

    # # ---------- 2. branch master (cost centers) ----------
    # # Excludes group + Testing/Head-Office as requested.
    # EXCLUDE_CC = ["Main - LSACPL", "Testing Branch - LSACPL"]

    # cc_rows = frappe.db.sql("""
    #     SELECT name AS cc, cost_center_name AS cname
    #     FROM `tabCost Center`
    #     WHERE is_group = 0 AND disabled = 0
    #     ORDER BY cost_center_name ASC
    # """, {}, as_dict=True)

    # branches = []
    # cc_ok = {}
    # for r in cc_rows:
    #     cc = r.get("cc")
    #     keep = 1
    #     for x in EXCLUDE_CC:
    #         if cc == x:
    #             keep = 0
    #     if keep == 1:
    #         b = {}
    #         b["cc"] = cc
    #         b["name"] = r.get("cname")
    #         branches.append(b)
    #         cc_ok[cc] = 1

    # # ---------- 3. invoices (row-level) ----------
    # inv_rows = frappe.db.sql("""
    #     SELECT
    #         si.name              AS no,
    #         si.posting_date      AS d,
    #         COALESCE(si.cost_center,'Unassigned') AS cc,
    #         si.patient           AS cli,
    #         si.patient_name      AS cname,
    #         si.customer          AS cust,
    #         si.grand_total       AS tot,
    #         si.base_net_total    AS net,
    #         si.total_taxes_and_charges AS gst,
    #         si.discount_amount   AS dsc,
    #         si.outstanding_amount AS due,
    #         si.status            AS st,
    #         COALESCE(si.custom_incentive_employee_name,'') AS incemp,
    #         COALESCE(si.custom_referring_name,'')          AS refname,
    #         COALESCE(si.ref_practitioner,'')               AS refprac,
    #         COALESCE(p.sex,'')                             AS gender
    #     FROM `tabSales Invoice` si
    #     LEFT JOIN `tabPatient` p ON p.name = si.patient
    #     WHERE si.docstatus = 1
    #       AND si.posting_date BETWEEN %(f)s AND %(t)s
    #     ORDER BY si.posting_date ASC
    # """, {"f": from_date, "t": to_date}, as_dict=True)

    # # specialty (category) per invoice: pick the largest-value item group,
    # # normalised to the 6 dashboard streams. One grouped query, then map.
    # cat_rows = frappe.db.sql("""
    #     SELECT sii.parent AS pno,
    #           COALESCE(ig.name, i.item_group, 'Services') AS grp,
    #           SUM(sii.base_net_amount) AS amt,
    #           SUM(sii.qty) AS qty
    #     FROM `tabSales Invoice Item` sii
    #     INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
    #     LEFT JOIN `tabItem` i ON i.name = sii.item_code
    #     LEFT JOIN `tabItem Group` ig ON ig.name = i.item_group
    #     WHERE si.docstatus = 1
    #       AND si.posting_date BETWEEN %(f)s AND %(t)s
    #     GROUP BY sii.parent, COALESCE(ig.name, i.item_group, 'Services')
    # """, {"f": from_date, "t": to_date}, as_dict=True)

    # # raw item_group -> dashboard stream (dict lookup, no function def)
    # CAT_MAP = {}
    # CAT_MAP["SLIM"] = "SLIMMING"
    # CAT_MAP["SLIMMING"] = "SLIMMING"
    # CAT_MAP["SKIN"] = "SKIN"
    # CAT_MAP["DERMAT"] = "SKIN"
    # CAT_MAP["HAIR"] = "HAIR"
    # CAT_MAP["HT"] = "HAIR TRANSPLANT"
    # CAT_MAP["SERVICES"] = "SLIMMING"
    # CAT_MAP["OPERATIONS"] = "SLIMMING"
    # CAT_MAP["PRODUCTS"] = "SKIN"
    # CAT_MAP["CONSUMABLE"] = "SKIN"
    # CAT_MAP["GENERAL"] = "SKIN"
    # CAT_MAP["GNR"] = "SKIN"

    # # per-invoice: dominant category + sold/qty totals
    # inv_cat = {}
    # inv_qty = {}
    # for r in cat_rows:
    #     pno = r.get("pno")
    #     grp_key = (r.get("grp") or "").upper()
    #     cat = CAT_MAP.get(grp_key, "SLIMMING")
    #     amt = float(r.get("amt") or 0)
    #     q = float(r.get("qty") or 0)
    #     if pno not in inv_cat:
    #         seed = {}
    #         seed["cat"] = cat
    #         seed["amt"] = amt
    #         inv_cat[pno] = seed
    #     else:
    #         cur = inv_cat[pno]
    #         if amt > cur["amt"]:
    #             cur["cat"] = cat
    #             cur["amt"] = amt
    #     if pno not in inv_qty:
    #         inv_qty[pno] = q
    #     else:
    #         inv_qty[pno] = inv_qty[pno] + q

    # # ---------- 3b. Therapy Plan enrichment (media / category / booker) ----------
    # # Sales Invoice links to Therapy Plan via custom_therapy_plan. TP carries
    # # media (Lead Source), category (Healthcare Service Unit), custom_employee_name.
    # # Used as: enquiry SOURCE (media), category FALLBACK, booker reference.
    # # TP category -> dashboard stream (fallback only)
    # TPCAT_MAP = {}
    # TPCAT_MAP["SLIMMING"] = "SLIMMING"
    # TPCAT_MAP["SKIN"] = "SKIN"
    # TPCAT_MAP["DERMAT"] = "SKIN"
    # TPCAT_MAP["HAIR"] = "HAIR"
    # TPCAT_MAP["HAIR TRANSPLANT"] = "HAIR TRANSPLANT"
    # TPCAT_MAP["HT"] = "HAIR TRANSPLANT"

    # tp_rows = frappe.db.sql("""
    #     SELECT si.name AS no,
    #           COALESCE(tp.media,'')  AS media,
    #           COALESCE(tp.category,'') AS tpcat,
    #           COALESCE(tp.custom_employee_name,'') AS booker,
    #           COALESCE(tp.tele_caller,'') AS teller
    #     FROM `tabSales Invoice` si
    #     INNER JOIN `tabTherapy Plan` tp ON tp.name = si.custom_therapy_plan
    #     WHERE si.docstatus = 1
    #       AND si.posting_date BETWEEN %(f)s AND %(t)s
    #       AND si.custom_therapy_plan IS NOT NULL
    #       AND si.custom_therapy_plan != ''
    # """, {"f": from_date, "t": to_date}, as_dict=True)

    # tp_map = {}
    # for r in tp_rows:
    #     no = r.get("no")
    #     d = {}
    #     d["media"] = r.get("media") or ""
    #     # normalise TP category: take first word before ' - ' or ' -LSACPL'
    #     raw = (r.get("tpcat") or "").upper()
    #     tpc = ""
    #     if raw.find("SLIM") > -1:
    #         tpc = "SLIMMING"
    #     elif raw.find("SKIN") > -1 or raw.find("DERMAT") > -1:
    #         tpc = "SKIN"
    #     elif raw.find("HAIR TRANSPLANT") > -1:
    #         tpc = "HAIR TRANSPLANT"
    #     elif raw.find("HAIR") > -1:
    #         tpc = "HAIR"
    #     elif raw.find("LASER") > -1:
    #         tpc = "LASER"
    #     d["tpcat"] = tpc
    #     d["booker"] = r.get("booker") or ""
    #     d["teller"] = r.get("teller") or ""
    #     tp_map[no] = d

    # invoices = []
    # tot_gross = 0.0
    # tot_net = 0.0
    # tot_paid = 0.0
    # tot_due = 0.0
    # tot_inv = 0

    # for r in inv_rows:
    #     cc = r.get("cc")
    #     # skip excluded cost centers
    #     show = 0
    #     if cc in cc_ok:
    #         show = 1
    #     if show == 0:
    #         continue
    #     no = r.get("no")
    #     gross = float(r.get("tot") or 0)
    #     net = float(r.get("net") or 0)
    #     gst = float(r.get("gst") or 0)
    #     dsc = float(r.get("dsc") or 0)
    #     due = float(r.get("due") or 0)
    #     paid = gross - due
    #     catinfo = inv_cat.get(no)
    #     cat = "SLIMMING"
    #     if catinfo:
    #         cat = catinfo["cat"]
    #     # Therapy Plan enrichment (source/media/booker; category fallback)
    #     tpinfo = tp_map.get(no)
    #     media = ""
    #     booker = ""
    #     teller = ""
    #     if tpinfo:
    #         media = tpinfo["media"]
    #         booker = tpinfo["booker"]
    #         teller = tpinfo["teller"]
    #         # fallback: if item-group gave the generic default and TP has a
    #         # concrete category, prefer TP's.
    #         no_items = 0
    #         if catinfo is None:
    #             no_items = 1
    #         if (no_items == 1 or cat == "SLIMMING") and tpinfo["tpcat"]:
    #             cat = tpinfo["tpcat"]
    #     sold = int(inv_qty.get(no) or 0)
    #     dscp = 0.0
    #     base_for_pct = gross + dsc
    #     if base_for_pct > 0:
    #         dscp = round(dsc / base_for_pct * 100.0, 1)
    #     incemp = r.get("incemp") or ""
    #     refname = r.get("refname") or ""
    #     emp = incemp
    #     if not emp:
    #         emp = refname
    #     # 50/50 attribution: when BOTH incentive + referring names are set,
    #     # revenue splits half-half; otherwise full credit to whichever exists.
    #     empsplit = []
    #     if incemp and refname and incemp != refname:
    #         s1 = {}
    #         s1["name"] = incemp
    #         s1["frac"] = 0.5
    #         empsplit.append(s1)
    #         s2 = {}
    #         s2["name"] = refname
    #         s2["frac"] = 0.5
    #         empsplit.append(s2)
    #     else:
    #         who = emp
    #         if who:
    #             s1 = {}
    #             s1["name"] = who
    #             s1["frac"] = 1.0
    #             empsplit.append(s1)
    #     iv = {}
    #     iv["no"] = no
    #     iv["d"] = str(r.get("d"))
    #     iv["cc"] = cc
    #     iv["cli"] = r.get("cli") or r.get("cust")
    #     iv["cname"] = r.get("cname") or ""
    #     iv["gender"] = r.get("gender") or ""
    #     iv["cat"] = cat
    #     iv["tr"] = cat
    #     iv["sess"] = sold
    #     iv["used"] = 0
    #     iv["gross"] = gross
    #     iv["dsc"] = dsc
    #     iv["dscp"] = dscp
    #     iv["net"] = net
    #     iv["gst"] = gst
    #     iv["tot"] = gross
    #     iv["paid"] = paid
    #     iv["due"] = due
    #     iv["emp"] = emp
    #     iv["incemp"] = incemp
    #     iv["refname"] = refname
    #     iv["empsplit"] = empsplit
    #     iv["media"] = media
    #     iv["booker"] = booker
    #     iv["teller"] = teller
    #     iv["st"] = r.get("st")
    #     invoices.append(iv)
    #     tot_gross = tot_gross + gross
    #     tot_net = tot_net + net
    #     tot_paid = tot_paid + paid
    #     tot_due = tot_due + due
    #     tot_inv = tot_inv + 1

    # # ---------- 4. client rollups (from invoices in window) ----------
    # cli_map = {}
    # for iv in invoices:
    #     cid = iv["cli"]
    #     if not cid:
    #         continue
    #     if cid not in cli_map:
    #         c = {}
    #         c["id"] = cid
    #         c["n"] = iv["cname"]
    #         c["cc"] = iv["cc"]
    #         c["cats"] = [iv["cat"]]
    #         c["cat"] = iv["cat"]
    #         c["src"] = iv["media"]
    #         c["bill"] = 0.0
    #         c["paid"] = 0.0
    #         c["due"] = 0.0
    #         c["invCount"] = 0
    #         c["sold"] = 0
    #         cli_map[cid] = c
    #     c = cli_map[cid]
    #     if not c["src"] and iv["media"]:
    #         c["src"] = iv["media"]
    #     c["bill"] = c["bill"] + iv["tot"]
    #     c["paid"] = c["paid"] + iv["paid"]
    #     c["due"] = c["due"] + iv["due"]
    #     c["invCount"] = c["invCount"] + 1
    #     c["sold"] = c["sold"] + iv["sess"]
    #     has = 0
    #     for x in c["cats"]:
    #         if x == iv["cat"]:
    #             has = 1
    #     if has == 0:
    #         c["cats"].append(iv["cat"])

    # clients = []
    # for cid in cli_map:
    #     clients.append(cli_map[cid])

    # # ---------- 5. employees (active) ----------
    # emp_rows = frappe.db.sql("""
    #     SELECT name AS id, employee_name AS n,
    #           COALESCE(gender,'') AS g,
    #           COALESCE(branch,'') AS br,
    #           COALESCE(department,'') AS dept,
    #           COALESCE(designation,'') AS dg,
    #           status AS st,
    #           date_of_joining AS join_d
    #     FROM `tabEmployee`
    #     WHERE status = 'Active'
    #     ORDER BY employee_name ASC
    # """, {}, as_dict=True)

    # employees = []
    # for r in emp_rows:
    #     e = {}
    #     e["id"] = r.get("id")
    #     e["n"] = r.get("n")
    #     e["g"] = r.get("g")
    #     e["br"] = r.get("br")
    #     e["dept"] = r.get("dept")
    #     e["dg"] = r.get("dg")
    #     e["st"] = r.get("st")
    #     e["join"] = str(r.get("join_d") or "")
    #     employees.append(e)

    # # ---------- 6. collections from Payment Entry (cash-in by PE date) ----------
    # # Grouped by cost center + YYYY-MM of PE posting_date.
    # # Three figures per bucket:
    # #   raw       = received_amount
    # #   after_gst = raw * 0.95            (flat 5% GST cut)
    # #   net_cuts  = after_gst, minus an extra 15% on loan-mode rows
    # # Loan modes (per business rule) get the extra 15% cut.
    # LOAN_MODES = {}
    # LOAN_MODES["Bajaj Card Charges"] = 1
    # LOAN_MODES["Sai Roshini Card Charges"] = 1
    # LOAN_MODES["Fibe Finance"] = 1
    # LOAN_MODES["Carepay"] = 1
    # LOAN_MODES["Savein Fintech Card Charges"] = 1
    # LOAN_MODES["Loan Tap / Uno Finance Charges"] = 1
    # LOAN_MODES["ShopSE"] = 1
    # LOAN_MODES["Liqui Loans Charges"] = 1

    # pe_rows = frappe.db.sql("""
    #     SELECT COALESCE(cost_center,'Unassigned') AS cc,
    #           YEAR(posting_date)  AS yy,
    #           MONTH(posting_date) AS mm,
    #           COALESCE(mode_of_payment,'') AS mode,
    #           SUM(received_amount) AS amt
    #     FROM `tabPayment Entry`
    #     WHERE docstatus = 1
    #       AND payment_type = 'Receive'
    #       AND posting_date BETWEEN %(f)s AND %(t)s
    #     GROUP BY cost_center, YEAR(posting_date), MONTH(posting_date), mode_of_payment
    # """, {"f": from_date, "t": to_date}, as_dict=True)

    # # accumulate into cc|YYYY-MM buckets
    # coll_map = {}
    # tot_coll_raw = 0.0
    # tot_coll_gst = 0.0
    # tot_coll_net = 0.0
    # for r in pe_rows:
    #     cc = r.get("cc")
    #     keep = 0
    #     if cc in cc_ok:
    #         keep = 1
    #     if keep == 0:
    #         continue
    #     yy = int(r.get("yy") or 0)
    #     mm = int(r.get("mm") or 0)
    #     mkey = str(yy) + "-" + str(mm)
    #     key = cc + "|" + mkey
    #     amt = float(r.get("amt") or 0)
    #     after_gst = amt * 0.95
    #     is_loan = 0
    #     if r.get("mode") in LOAN_MODES:
    #         is_loan = 1
    #     if is_loan == 1:
    #         net_cuts = after_gst * 0.85
    #     else:
    #         net_cuts = after_gst
    #     if key not in coll_map:
    #         c = {}
    #         c["cc"] = cc
    #         c["mkey"] = mkey
    #         c["raw"] = 0.0
    #         c["after_gst"] = 0.0
    #         c["net_cuts"] = 0.0
    #         coll_map[key] = c
    #     c = coll_map[key]
    #     c["raw"] = c["raw"] + amt
    #     c["after_gst"] = c["after_gst"] + after_gst
    #     c["net_cuts"] = c["net_cuts"] + net_cuts
    #     tot_coll_raw = tot_coll_raw + amt
    #     tot_coll_gst = tot_coll_gst + after_gst
    #     tot_coll_net = tot_coll_net + net_cuts

    # collections = []
    # for key in coll_map:
    #     collections.append(coll_map[key])

    # # ---------- 7. live targets (Week Achive child rows) ----------
    # # Per-branch monthly targets (business month 6th-5th). Multiple parent
    # # docs can share dates -- keep the most recently modified parent per period.
    # tgt_parents = frappe.db.sql("""
    #     SELECT name, from_date, to_date, modified
    #     FROM `tabWeek Target vs Achive With Cuttings`
    #     WHERE to_date >= %(f)s AND from_date <= %(t)s
    #     ORDER BY modified DESC
    # """, {"f": from_date, "t": to_date}, as_dict=True)

    # # pick one parent per (from_date,to_date) period -- first seen = newest
    # period_parent = {}
    # parent_ok = {}
    # for r in tgt_parents:
    #     pkey = str(r.get("from_date")) + "|" + str(r.get("to_date"))
    #     if pkey not in period_parent:
    #         period_parent[pkey] = r.get("name")
    #         parent_ok[r.get("name")] = pkey

    # targets = []
    # if parent_ok:
    #     tgt_rows = frappe.db.sql("""
    #         SELECT wa.parent AS parent,
    #               COALESCE(wa.branch,'') AS branch,
    #               wa.targeted_amount AS tgt,
    #               wa.achievement_amount AS ach,
    #               wa.achievement_percentage AS pct
    #         FROM `tabWeek Achive` wa
    #         WHERE wa.parenttype = 'Week Target vs Achive With Cuttings'
    #         ORDER BY wa.parent ASC
    #     """, {}, as_dict=True)
    #     # map period start/end back onto each row
    #     parent_period = {}
    #     for r in tgt_parents:
    #         parent_period[r.get("name")] = {"f": str(r.get("from_date")), "t": str(r.get("to_date"))}
    #     for r in tgt_rows:
    #         pnm = r.get("parent")
    #         keep = 0
    #         if pnm in parent_ok:
    #             keep = 1
    #         if keep == 0:
    #             continue
    #         pp = parent_period.get(pnm)
    #         d = {}
    #         d["branch"] = r.get("branch")
    #         d["target"] = float(r.get("tgt") or 0)
    #         d["achieved"] = float(r.get("ach") or 0)
    #         d["pct"] = float(r.get("pct") or 0)
    #         if pp:
    #             d["from"] = pp["f"]
    #             d["to"] = pp["t"]
    #         targets.append(d)

    # # ---------- 7b. payments per invoice (for the invoice modal) ----------
    # # PE references linked to invoices posted in the window, with the PE's
    # # mode/date/amount. Powers openInv modal + per-invoice payment mode.
    # pay_ref_rows = frappe.db.sql("""
    #     SELECT per.reference_name AS no,
    #           pe.name           AS pe,
    #           COALESCE(pe.mode_of_payment,'') AS mode,
    #           pe.posting_date   AS d,
    #           per.allocated_amount AS amt
    #     FROM `tabPayment Entry Reference` per
    #     INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
    #     INNER JOIN `tabSales Invoice` si ON si.name = per.reference_name
    #     WHERE pe.docstatus = 1
    #       AND per.reference_doctype = 'Sales Invoice'
    #       AND si.docstatus = 1
    #       AND si.posting_date BETWEEN %(f)s AND %(t)s
    #     ORDER BY pe.posting_date ASC
    # """, {"f": from_date, "t": to_date}, as_dict=True)

    # payments = []
    # for r in pay_ref_rows:
    #     p = {}
    #     p["no"] = r.get("no")
    #     p["pe"] = r.get("pe")
    #     p["mode"] = r.get("mode")
    #     p["d"] = str(r.get("d"))
    #     p["amt"] = float(r.get("amt") or 0)
    #     payments.append(p)

    # # ---------- 8. totals ----------
    # totals = {}
    # totals["gross"] = tot_gross
    # totals["net"] = tot_net
    # totals["due"] = tot_due
    # totals["invoices"] = tot_inv
    # totals["clients"] = len(clients)
    # totals["coll_raw"] = tot_coll_raw
    # totals["coll_after_gst"] = tot_coll_gst
    # totals["coll_net_cuts"] = tot_coll_net

    # # ---------- 9. payload ----------
    # out = {}
    # out["from_date"] = from_date
    # out["to_date"] = to_date
    # out["branches"] = branches
    # out["invoices"] = invoices
    # out["clients"] = clients
    # out["employees"] = employees
    # out["collections"] = collections
    # out["targets"] = targets
    # out["payments"] = payments
    # out["totals"] = totals

    # frappe.response["message"] = out


    # =====================================================================
    #  SERVER SCRIPT  (API type)
    #  Name        : report_master_api
    #  Script Type : API
    #  API Method  : report_master_api
    #  Allow Guest : No
    #  Endpoint    : /api/method/report_master_api?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    #
    #  Feeds the LIFE MASTER REPORTS web page (report-master).
    #  Returns LIVE row-level arrays that the dashboard's report engine
    #  consumes directly (money + collections + client reports):
    #     branches[]  invoices[]  clients[]  employees[]  totals{}
    #
    #  Reports powered: 1 Executive, 10 Revenue, 12 Invoice Register,
    #     110-115 Collections/Dues, 20 Enrolment(light), 30 Client Search.
    #  Clinical reports (21 Results, 22 Card Status) are NOT fed here --
    #     the frontend marks them "clinical feed pending".
    #
    #  safe_exec rules honoured:
    #    - no try/except, no f-strings, no .format(), no imports
    #    - no tuple unpacking in for-loops, no augmented assignment (x += y)
    #    - no frappe.get_roles / frappe.db.commit / frappe.clear_cache
    #    - % formatting only, explicit reassignment for aggregation
    #    - frappe.form_dict for params
    #
    #  PATCH (Aug 2026): CAT_MAP / TPCAT_MAP updated after Item Group renames
    #    so the renamed groups (Skin (Dermatology), Hair Transplant (HT),
    #    Hair Treatment, Consumables, Home Care Products, Slimming) map to the
    #    correct dashboard streams instead of falling through to SLIMMING.
    #    Old keys kept for historical rows.
    # =====================================================================

    # ---------- 1. date range ----------
    args = frappe.form_dict or {}
    from_date = args.get("from_date")
    to_date = args.get("to_date")

    if not to_date:
        to_date = frappe.utils.nowdate()
    if not from_date:
        from_date = frappe.utils.add_days(to_date, -30)

    to_date_end = to_date + " 23:59:59"

    # ---------- 2. branch master (cost centers) ----------
    # Excludes group + Testing/Head-Office as requested.
    EXCLUDE_CC = ["Main - LSACPL", "Testing Branch - LSACPL"]

    cc_rows = _read_sql("""
    SELECT name AS cc, cost_center_name AS cname
    FROM `tabCost Center`
    WHERE is_group = 0 AND disabled = 0
    ORDER BY cost_center_name ASC
""", {}, as_dict=True)

    branches = []
    cc_ok = {}
    for r in cc_rows:
        cc = r.get("cc")
        keep = 1
        for x in EXCLUDE_CC:
            if cc == x:
                keep = 0
        if keep == 1:
            b = {}
            b["cc"] = cc
            b["name"] = r.get("cname")
            branches.append(b)
            cc_ok[cc] = 1

    # ---------- 3. invoices (row-level) ----------
    inv_rows = _read_sql("""
    SELECT
        si.name              AS no,
        si.posting_date      AS d,
        COALESCE(si.cost_center,'Unassigned') AS cc,
        si.patient           AS cli,
        si.patient_name      AS cname,
        si.customer          AS cust,
        si.grand_total       AS tot,
        si.base_net_total    AS net,
        si.total_taxes_and_charges AS gst,
        si.discount_amount   AS dsc,
        si.outstanding_amount AS due,
        si.status            AS st,
        COALESCE(si.custom_incentive_employee_name,'') AS incemp,
        COALESCE(si.custom_referring_name,'')          AS refname,
        COALESCE(si.ref_practitioner,'')               AS refprac,
        COALESCE(p.sex,'')                             AS gender
    FROM `tabSales Invoice` si
    LEFT JOIN `tabPatient` p ON p.name = si.patient
    WHERE si.docstatus = 1
      AND si.posting_date BETWEEN %(f)s AND %(t)s
    ORDER BY si.posting_date ASC
""", {"f": from_date, "t": to_date}, as_dict=True)

    # specialty (category) per invoice: pick the largest-value item group,
    # normalised to the 6 dashboard streams. One grouped query, then map.
    cat_rows = _read_sql("""
    SELECT sii.parent AS pno,
           COALESCE(ig.name, i.item_group, 'Services') AS grp,
           SUM(sii.base_net_amount) AS amt,
           SUM(sii.qty) AS qty
    FROM `tabSales Invoice Item` sii
    INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
    LEFT JOIN `tabItem` i ON i.name = sii.item_code
    LEFT JOIN `tabItem Group` ig ON ig.name = i.item_group
    WHERE si.docstatus = 1
      AND si.posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY sii.parent, COALESCE(ig.name, i.item_group, 'Services')
""", {"f": from_date, "t": to_date}, as_dict=True)

    # raw item_group -> dashboard stream (dict lookup, no function def)
    # NOTE: keys are compared after .upper() on the live item_group name.
    CAT_MAP = {}
    # --- legacy keys (pre-rename data still resolves) ---
    CAT_MAP["SLIM"] = "SLIMMING"
    CAT_MAP["SLIMMING"] = "SLIMMING"
    CAT_MAP["SKIN"] = "SKIN"
    CAT_MAP["DERMAT"] = "SKIN"
    CAT_MAP["HAIR"] = "HAIR"
    CAT_MAP["HT"] = "HAIR TRANSPLANT"
    CAT_MAP["SERVICES"] = "SLIMMING"
    CAT_MAP["OPERATIONS"] = "SLIMMING"
    CAT_MAP["PRODUCTS"] = "SKIN"
    CAT_MAP["CONSUMABLE"] = "SKIN"
    CAT_MAP["GENERAL"] = "SKIN"
    CAT_MAP["GNR"] = "SKIN"
    # --- new keys after Item Group renames (Aug 2026) ---
    CAT_MAP["SKIN (DERMATOLOGY)"] = "SKIN"
    CAT_MAP["HAIR TRANSPLANT (HT)"] = "HAIR TRANSPLANT"
    CAT_MAP["HAIR TREATMENT"] = "HAIR"
    CAT_MAP["CONSUMABLES"] = "SKIN"
    CAT_MAP["HOME CARE PRODUCTS"] = "SKIN"

    # per-invoice: dominant category + sold/qty totals
    inv_cat = {}
    inv_qty = {}
    for r in cat_rows:
        pno = r.get("pno")
        grp_key = (r.get("grp") or "").upper()
        cat = CAT_MAP.get(grp_key, "SLIMMING")
        amt = float(r.get("amt") or 0)
        q = float(r.get("qty") or 0)
        if pno not in inv_cat:
            seed = {}
            seed["cat"] = cat
            seed["amt"] = amt
            inv_cat[pno] = seed
        else:
            cur = inv_cat[pno]
            if amt > cur["amt"]:
                cur["cat"] = cat
                cur["amt"] = amt
        if pno not in inv_qty:
            inv_qty[pno] = q
        else:
            inv_qty[pno] = inv_qty[pno] + q

    # ---------- 3b. Therapy Plan enrichment (media / category / booker) ----------
    # Sales Invoice links to Therapy Plan via custom_therapy_plan. TP carries
    # media (Lead Source), category (Healthcare Service Unit), custom_employee_name.
    # Used as: enquiry SOURCE (media), category FALLBACK, booker reference.
    # TP category -> dashboard stream (fallback only)
    TPCAT_MAP = {}
    # --- legacy keys ---
    TPCAT_MAP["SLIMMING"] = "SLIMMING"
    TPCAT_MAP["SKIN"] = "SKIN"
    TPCAT_MAP["DERMAT"] = "SKIN"
    TPCAT_MAP["HAIR"] = "HAIR"
    TPCAT_MAP["HAIR TRANSPLANT"] = "HAIR TRANSPLANT"
    TPCAT_MAP["HT"] = "HAIR TRANSPLANT"
    # --- new keys after Item Group renames (Aug 2026) ---
    TPCAT_MAP["SKIN (DERMATOLOGY)"] = "SKIN"
    TPCAT_MAP["HAIR TRANSPLANT (HT)"] = "HAIR TRANSPLANT"
    TPCAT_MAP["HAIR TREATMENT"] = "HAIR"

    tp_rows = _read_sql("""
    SELECT si.name AS no,
           COALESCE(tp.media,'')  AS media,
           COALESCE(tp.category,'') AS tpcat,
           COALESCE(tp.custom_employee_name,'') AS booker,
           COALESCE(tp.tele_caller,'') AS teller
    FROM `tabSales Invoice` si
    INNER JOIN `tabTherapy Plan` tp ON tp.name = si.custom_therapy_plan
    WHERE si.docstatus = 1
      AND si.posting_date BETWEEN %(f)s AND %(t)s
      AND si.custom_therapy_plan IS NOT NULL
      AND si.custom_therapy_plan != ''
""", {"f": from_date, "t": to_date}, as_dict=True)

    tp_map = {}
    for r in tp_rows:
        no = r.get("no")
        d = {}
        d["media"] = r.get("media") or ""
        # normalise TP category: take first word before ' - ' or ' -LSACPL'
        raw = (r.get("tpcat") or "").upper()
        tpc = ""
        if raw.find("SLIM") > -1:
            tpc = "SLIMMING"
        elif raw.find("SKIN") > -1 or raw.find("DERMAT") > -1:
            tpc = "SKIN"
        elif raw.find("HAIR TRANSPLANT") > -1:
            tpc = "HAIR TRANSPLANT"
        elif raw.find("HAIR") > -1:
            tpc = "HAIR"
        elif raw.find("LASER") > -1:
            tpc = "LASER"
        d["tpcat"] = tpc
        d["booker"] = r.get("booker") or ""
        d["teller"] = r.get("teller") or ""
        tp_map[no] = d

    invoices = []
    tot_gross = 0.0
    tot_net = 0.0
    tot_paid = 0.0
    tot_due = 0.0
    tot_inv = 0

    for r in inv_rows:
        cc = r.get("cc")
        # skip excluded cost centers
        show = 0
        if cc in cc_ok:
            show = 1
        if show == 0:
            continue
        no = r.get("no")
        gross = float(r.get("tot") or 0)
        net = float(r.get("net") or 0)
        gst = float(r.get("gst") or 0)
        dsc = float(r.get("dsc") or 0)
        due = float(r.get("due") or 0)
        paid = gross - due
        catinfo = inv_cat.get(no)
        cat = "SLIMMING"
        if catinfo:
            cat = catinfo["cat"]
        # Therapy Plan enrichment (source/media/booker; category fallback)
        tpinfo = tp_map.get(no)
        media = ""
        booker = ""
        teller = ""
        if tpinfo:
            media = tpinfo["media"]
            booker = tpinfo["booker"]
            teller = tpinfo["teller"]
            # fallback: if item-group gave the generic default and TP has a
            # concrete category, prefer TP's.
            no_items = 0
            if catinfo is None:
                no_items = 1
            if (no_items == 1 or cat == "SLIMMING") and tpinfo["tpcat"]:
                cat = tpinfo["tpcat"]
        sold = int(inv_qty.get(no) or 0)
        dscp = 0.0
        base_for_pct = gross + dsc
        if base_for_pct > 0:
            dscp = round(dsc / base_for_pct * 100.0, 1)
        incemp = r.get("incemp") or ""
        refname = r.get("refname") or ""
        emp = incemp
        if not emp:
            emp = refname
        # 50/50 attribution: when BOTH incentive + referring names are set,
        # revenue splits half-half; otherwise full credit to whichever exists.
        empsplit = []
        if incemp and refname and incemp != refname:
            s1 = {}
            s1["name"] = incemp
            s1["frac"] = 0.5
            empsplit.append(s1)
            s2 = {}
            s2["name"] = refname
            s2["frac"] = 0.5
            empsplit.append(s2)
        else:
            who = emp
            if who:
                s1 = {}
                s1["name"] = who
                s1["frac"] = 1.0
                empsplit.append(s1)
        iv = {}
        iv["no"] = no
        iv["d"] = str(r.get("d"))
        iv["cc"] = cc
        iv["cli"] = r.get("cli") or r.get("cust")
        iv["cname"] = r.get("cname") or ""
        iv["gender"] = r.get("gender") or ""
        iv["cat"] = cat
        iv["tr"] = cat
        iv["sess"] = sold
        iv["used"] = 0
        iv["gross"] = gross
        iv["dsc"] = dsc
        iv["dscp"] = dscp
        iv["net"] = net
        iv["gst"] = gst
        iv["tot"] = gross
        iv["paid"] = paid
        iv["due"] = due
        iv["emp"] = emp
        iv["incemp"] = incemp
        iv["refname"] = refname
        iv["empsplit"] = empsplit
        iv["media"] = media
        iv["booker"] = booker
        iv["teller"] = teller
        iv["st"] = r.get("st")
        invoices.append(iv)
        tot_gross = tot_gross + gross
        tot_net = tot_net + net
        tot_paid = tot_paid + paid
        tot_due = tot_due + due
        tot_inv = tot_inv + 1

    # ---------- 4. client rollups (from invoices in window) ----------
    cli_map = {}
    for iv in invoices:
        cid = iv["cli"]
        if not cid:
            continue
        if cid not in cli_map:
            c = {}
            c["id"] = cid
            c["n"] = iv["cname"]
            c["cc"] = iv["cc"]
            c["cats"] = [iv["cat"]]
            c["cat"] = iv["cat"]
            c["src"] = iv["media"]
            c["bill"] = 0.0
            c["paid"] = 0.0
            c["due"] = 0.0
            c["invCount"] = 0
            c["sold"] = 0
            cli_map[cid] = c
        c = cli_map[cid]
        if not c["src"] and iv["media"]:
            c["src"] = iv["media"]
        c["bill"] = c["bill"] + iv["tot"]
        c["paid"] = c["paid"] + iv["paid"]
        c["due"] = c["due"] + iv["due"]
        c["invCount"] = c["invCount"] + 1
        c["sold"] = c["sold"] + iv["sess"]
        has = 0
        for x in c["cats"]:
            if x == iv["cat"]:
                has = 1
        if has == 0:
            c["cats"].append(iv["cat"])

    clients = []
    for cid in cli_map:
        clients.append(cli_map[cid])

    # ---------- 5. employees (active) ----------
    emp_rows = _read_sql("""
    SELECT name AS id, employee_name AS n,
           COALESCE(gender,'') AS g,
           COALESCE(branch,'') AS br,
           COALESCE(department,'') AS dept,
           COALESCE(designation,'') AS dg,
           status AS st,
           date_of_joining AS join_d
    FROM `tabEmployee`
    WHERE status = 'Active'
    ORDER BY employee_name ASC
""", {}, as_dict=True)

    employees = []
    for r in emp_rows:
        e = {}
        e["id"] = r.get("id")
        e["n"] = r.get("n")
        e["g"] = r.get("g")
        e["br"] = r.get("br")
        e["dept"] = r.get("dept")
        e["dg"] = r.get("dg")
        e["st"] = r.get("st")
        e["join"] = str(r.get("join_d") or "")
        employees.append(e)

    # ---------- 6. collections from Payment Entry (cash-in by PE date) ----------
    # Grouped by cost center + YYYY-MM of PE posting_date.
    # Three figures per bucket:
    #   raw       = received_amount
    #   after_gst = raw * 0.95            (flat 5% GST cut)
    #   net_cuts  = after_gst, minus an extra 15% on loan-mode rows
    # Loan modes (per business rule) get the extra 15% cut.
    LOAN_MODES = {}
    LOAN_MODES["Bajaj Card Charges"] = 1
    LOAN_MODES["Sai Roshini Card Charges"] = 1
    LOAN_MODES["Fibe Finance"] = 1
    LOAN_MODES["Carepay"] = 1
    LOAN_MODES["Savein Fintech Card Charges"] = 1
    LOAN_MODES["Loan Tap / Uno Finance Charges"] = 1
    LOAN_MODES["ShopSE"] = 1
    LOAN_MODES["Liqui Loans Charges"] = 1

    pe_rows = _read_sql("""
    SELECT COALESCE(cost_center,'Unassigned') AS cc,
           YEAR(posting_date)  AS yy,
           MONTH(posting_date) AS mm,
           COALESCE(mode_of_payment,'') AS mode,
           SUM(received_amount) AS amt
    FROM `tabPayment Entry`
    WHERE docstatus = 1
      AND payment_type = 'Receive'
      AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY cost_center, YEAR(posting_date), MONTH(posting_date), mode_of_payment
""", {"f": from_date, "t": to_date}, as_dict=True)

    # accumulate into cc|YYYY-MM buckets
    coll_map = {}
    tot_coll_raw = 0.0
    tot_coll_gst = 0.0
    tot_coll_net = 0.0
    for r in pe_rows:
        cc = r.get("cc")
        keep = 0
        if cc in cc_ok:
            keep = 1
        if keep == 0:
            continue
        yy = int(r.get("yy") or 0)
        mm = int(r.get("mm") or 0)
        mkey = str(yy) + "-" + str(mm)
        key = cc + "|" + mkey
        amt = float(r.get("amt") or 0)
        after_gst = amt * 0.95
        is_loan = 0
        if r.get("mode") in LOAN_MODES:
            is_loan = 1
        if is_loan == 1:
            net_cuts = after_gst * 0.85
        else:
            net_cuts = after_gst
        if key not in coll_map:
            c = {}
            c["cc"] = cc
            c["mkey"] = mkey
            c["raw"] = 0.0
            c["after_gst"] = 0.0
            c["net_cuts"] = 0.0
            coll_map[key] = c
        c = coll_map[key]
        c["raw"] = c["raw"] + amt
        c["after_gst"] = c["after_gst"] + after_gst
        c["net_cuts"] = c["net_cuts"] + net_cuts
        tot_coll_raw = tot_coll_raw + amt
        tot_coll_gst = tot_coll_gst + after_gst
        tot_coll_net = tot_coll_net + net_cuts

    collections = []
    for key in coll_map:
        collections.append(coll_map[key])

    # ---------- 7. live targets (Week Achive child rows) ----------
    # Per-branch monthly targets (business month 6th-5th). Multiple parent
    # docs can share dates -- keep the most recently modified parent per period.
    tgt_parents = _read_sql("""
    SELECT name, from_date, to_date, modified
    FROM `tabWeek Target vs Achive With Cuttings`
    WHERE to_date >= %(f)s AND from_date <= %(t)s
    ORDER BY modified DESC
""", {"f": from_date, "t": to_date}, as_dict=True)

    # pick one parent per (from_date,to_date) period -- first seen = newest
    period_parent = {}
    parent_ok = {}
    for r in tgt_parents:
        pkey = str(r.get("from_date")) + "|" + str(r.get("to_date"))
        if pkey not in period_parent:
            period_parent[pkey] = r.get("name")
            parent_ok[r.get("name")] = pkey

    targets = []
    if parent_ok:
        tgt_rows = _read_sql("""
        SELECT wa.parent AS parent,
               COALESCE(wa.branch,'') AS branch,
               wa.targeted_amount AS tgt,
               wa.achievement_amount AS ach,
               wa.achievement_percentage AS pct
        FROM `tabWeek Achive` wa
        WHERE wa.parenttype = 'Week Target vs Achive With Cuttings'
        ORDER BY wa.parent ASC
    """, {}, as_dict=True)
        # map period start/end back onto each row
        parent_period = {}
        for r in tgt_parents:
            parent_period[r.get("name")] = {"f": str(r.get("from_date")), "t": str(r.get("to_date"))}
        for r in tgt_rows:
            pnm = r.get("parent")
            keep = 0
            if pnm in parent_ok:
                keep = 1
            if keep == 0:
                continue
            pp = parent_period.get(pnm)
            d = {}
            d["branch"] = r.get("branch")
            d["target"] = float(r.get("tgt") or 0)
            d["achieved"] = float(r.get("ach") or 0)
            d["pct"] = float(r.get("pct") or 0)
            if pp:
                d["from"] = pp["f"]
                d["to"] = pp["t"]
            targets.append(d)

    # ---------- 7b. payments per invoice (for the invoice modal) ----------
    # PE references linked to invoices posted in the window, with the PE's
    # mode/date/amount. Powers openInv modal + per-invoice payment mode.
    pay_ref_rows = _read_sql("""
    SELECT per.reference_name AS no,
           pe.name           AS pe,
           COALESCE(pe.mode_of_payment,'') AS mode,
           pe.posting_date   AS d,
           per.allocated_amount AS amt
    FROM `tabPayment Entry Reference` per
    INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
    INNER JOIN `tabSales Invoice` si ON si.name = per.reference_name
    WHERE pe.docstatus = 1
      AND per.reference_doctype = 'Sales Invoice'
      AND si.docstatus = 1
      AND si.posting_date BETWEEN %(f)s AND %(t)s
    ORDER BY pe.posting_date ASC
""", {"f": from_date, "t": to_date}, as_dict=True)

    payments = []
    for r in pay_ref_rows:
        p = {}
        p["no"] = r.get("no")
        p["pe"] = r.get("pe")
        p["mode"] = r.get("mode")
        p["d"] = str(r.get("d"))
        p["amt"] = float(r.get("amt") or 0)
        payments.append(p)

    # ---------- 8. totals ----------
    totals = {}
    totals["gross"] = tot_gross
    totals["net"] = tot_net
    totals["due"] = tot_due
    totals["invoices"] = tot_inv
    totals["clients"] = len(clients)
    totals["coll_raw"] = tot_coll_raw
    totals["coll_after_gst"] = tot_coll_gst
    totals["coll_net_cuts"] = tot_coll_net

    # ---------- 9. payload ----------
    out = {}
    out["from_date"] = from_date
    out["to_date"] = to_date
    out["branches"] = branches
    out["invoices"] = invoices
    out["clients"] = clients
    out["employees"] = employees
    out["collections"] = collections
    out["targets"] = targets
    out["payments"] = payments
    out["totals"] = totals

    frappe.response["message"] = out
