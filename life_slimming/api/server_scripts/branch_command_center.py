"""branch_command_center

Original API: branch_command_center
Source modified: 2026-09-11 08:18:35.500245
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
    # # Server Script 1  |  Script Type: API  |  API Method: branch_command_center

    # branch = frappe.form_dict.get("branch")
    # if not branch:
    #     frappe.throw("branch required")

    # is_sysmgr = frappe.db.exists("Has Role",
    #     {"parent": frappe.session.user, "role": "System Manager"})
    # if not is_sysmgr:
    #     allowed = [d.for_value for d in frappe.get_all("User Permission",
    #         filters={"user": frappe.session.user, "allow": "Branch"}, fields=["for_value"])]
    #     if allowed and branch not in allowed:
    #         frappe.throw("Not permitted for this branch")

    # # Loan / finance modes get GST stripped, then an extra 15% deduction
    # LOAN_MODES = ("Carepay", "Fibe Finance", "ShopSE", "Liqui Loans Charges",
    #               "Loan Tap / Uno Finance Charges", "Savein Fintech Card Charges",
    #               "Sai Roshini Card Charges", "Bajaj Card Charges")


    # def get_counselor_performance(branch, from_date, to_date):
    #     """
    #     Counselor performance = actual money COLLECTED, attributed to the
    #     counselor via the real link chain:

    #         Payment Entry
    #           -> Payment Entry Reference (child table: allocated_amount per invoice)
    #           -> Sales Invoice (therapy_plan_reference_id)
    #           -> Therapy Plan (custom_employee_name = counselor)

    #     This replaces attributing performance to Therapy Plan billed value,
    #     since Payment Entry itself has no counselor/employee field
    #     (custom_counsellor / custom_employee / custom_counselor_name do not
    #     exist on Payment Entry). allocated_amount correctly splits a single
    #     payment across multiple invoices/counselors where relevant.
    #     """
    #     rows = frappe.db.sql("""
    #         SELECT
    #             tp.custom_employee_name AS n,
    #             SUM(per.allocated_amount) AS gross,
    #             COUNT(DISTINCT tp.name) AS conv
    #         FROM `tabPayment Entry Reference` per
    #         JOIN `tabPayment Entry` pe
    #             ON pe.name = per.parent
    #         JOIN `tabSales Invoice` si
    #             ON si.name = per.reference_name
    #             AND per.reference_doctype = 'Sales Invoice'
    #         JOIN `tabTherapy Plan` tp
    #             ON tp.name = si.therapy_plan_reference_id
    #         WHERE pe.docstatus = 1
    #             AND pe.branch = %(b)s
    #             AND pe.posting_date BETWEEN %(f)s AND %(t)s
    #             AND IFNULL(tp.custom_employee_name,'') != ''
    #         GROUP BY tp.custom_employee_name
    #         ORDER BY gross DESC
    #     """, {"b": branch, "f": from_date, "t": to_date}, as_dict=True)

    #     emps = []
    #     for e in rows:
    #         gross = float(e["gross"] or 0)
    #         if gross == 0:
    #             continue
    #         ex_gst = gross / 1.05
    #         gst = gross - ex_gst
    #         designation = frappe.db.get_value("Employee",
    #             {"employee_name": e["n"], "status": "Active"}, "designation") or ""
    #         emps.append({
    #             "n": e["n"],
    #             "dg": designation,
    #             "gross": round(gross, 2),
    #             "gst": round(gst, 2),
    #             "net": round(ex_gst, 2),
    #             "conv": e["conv"],
    #         })
    #     return emps


    # range_from = frappe.form_dict.get("from_date")
    # range_to = frappe.form_dict.get("to_date")

    # # ============================================================
    # # RANGE PATH: custom date-range data for dashboard
    # # ============================================================
    # if range_from and range_to:
    #     # Get payment modes in range with detailed breakdown
    #     pm_range = frappe.db.sql("""SELECT mode_of_payment AS m, SUM(paid_amount) AS v
    #         FROM `tabPayment Entry`
    #         WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    #         GROUP BY mode_of_payment ORDER BY v DESC""",
    #         {"b": branch, "f": range_from, "t": range_to}, as_dict=True)

    #     modes = []
    #     tot_gross = 0.0
    #     tot_exgst = 0.0
    #     tot_final = 0.0
    #     tot_gst = 0.0
    #     tot_cut = 0.0

    #     for r in pm_range:
    #         gross = float(r["v"] or 0)
    #         ex_gst = gross / 1.05
    #         gst = gross - ex_gst
    #         is_loan = r["m"] in LOAN_MODES
    #         if is_loan:
    #             cut_amt = ex_gst * 0.15
    #             final = ex_gst - cut_amt
    #         else:
    #             cut_amt = 0
    #             final = ex_gst

    #         modes.append({
    #             "mode": r["m"] or "Unknown",
    #             "gross": round(gross, 2),
    #             "gst": round(gst, 2),
    #             "ex_gst": round(ex_gst, 2),
    #             "is_loan": is_loan,
    #             "cut_amt": round(cut_amt, 2),
    #             "final": round(final, 2),
    #         })
    #         tot_gross += gross
    #         tot_gst += gst
    #         tot_exgst += ex_gst
    #         tot_cut += cut_amt
    #         tot_final += final

    #     # Get target for range - sum of weekly targets that overlap
    #     tgt_rows = frappe.db.sql("""
    #         SELECT DISTINCT wa.targeted_amount AS amt, wt.from_date AS f, wt.to_date AS t
    #         FROM `tabWeek Achive` wa
    #         JOIN `tabWeek Target vs Achive With Cuttings` wt ON wt.name = wa.parent
    #         WHERE wa.branch=%(b)s AND wt.from_date <= %(t)s AND wt.to_date >= %(f)s
    #     """, {"b": branch, "f": range_from, "t": range_to}, as_dict=True)
    #     target_range = sum(float(r["amt"] or 0) for r in tgt_rows)

    #     # ============================================================
    #     # COUNSELOR PERFORMANCE (actual collections, via Payment Entry
    #     # Reference -> Sales Invoice -> Therapy Plan)
    #     # ============================================================
    #     counselor_emps = get_counselor_performance(branch, range_from, range_to)

    #     frappe.response["message"] = {
    #         "range": {
    #             "from": range_from,
    #             "to": range_to,
    #             "target": round(target_range, 2),
    #             "target_rows": len(tgt_rows),
    #             "achieved_gross": round(tot_gross, 2),
    #             "achieved_gst": round(tot_gst, 2),
    #             "achieved_ex_gst": round(tot_exgst, 2),
    #             "achieved_cut": round(tot_cut, 2),
    #             "achieved_final": round(tot_final, 2),
    #             "modes": modes,
    #             "emps": counselor_emps,
    #         }
    #     }

    # # ============================================================
    # # NORMAL PATH: full dashboard payload
    # # ============================================================
    # else:
    #     today = frappe.utils.nowdate()
    #     d = frappe.utils.getdate(today)

    #     # Month cycle: 6th to 5th of next month
    #     if d.day >= 6:
    #         cyc_start = frappe.utils.get_first_day(d).replace(day=6)
    #     else:
    #         cyc_start = frappe.utils.add_months(frappe.utils.get_first_day(d), -1).replace(day=6)
    #     cyc_end = frappe.utils.add_days(frappe.utils.add_months(cyc_start, 1), -1)
    #     d14 = frappe.utils.add_days(today, -13)

    #     # Get target
    #     tgt = frappe.db.sql("""
    #         SELECT wa.targeted_amount AS amt, wt.from_date AS f, wt.to_date AS t
    #         FROM `tabWeek Achive` wa
    #         JOIN `tabWeek Target vs Achive With Cuttings` wt ON wt.name = wa.parent
    #         WHERE wa.branch = %(b)s AND %(t)s BETWEEN wt.from_date AND wt.to_date
    #         ORDER BY wt.from_date DESC, wt.modified DESC LIMIT 1
    #     """, {"b": branch, "t": today}, as_dict=True)
    #     if not tgt:
    #         tgt = frappe.db.sql("""
    #             SELECT wa.targeted_amount AS amt, wt.from_date AS f, wt.to_date AS t
    #             FROM `tabWeek Achive` wa
    #             JOIN `tabWeek Target vs Achive With Cuttings` wt ON wt.name = wa.parent
    #             WHERE wa.branch = %(b)s AND wt.from_date <= %(t)s
    #             ORDER BY wt.from_date DESC, wt.modified DESC LIMIT 1
    #         """, {"b": branch, "t": today}, as_dict=True)
    #     target = tgt[0]["amt"] if tgt else 0
    #     t_from = str(tgt[0]["f"]) if tgt else str(cyc_start)
    #     t_to = str(tgt[0]["t"]) if tgt else str(cyc_end)

    #     # TARGET ACHIEVEMENT = COLLECTIONS (Payment Entry) ONLY
    #     achieved_rows = frappe.db.sql("""SELECT mode_of_payment AS m, SUM(paid_amount) AS v
    #         FROM `tabPayment Entry`
    #         WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    #         GROUP BY mode_of_payment""",
    #         {"b": branch, "f": t_from, "t": t_to}, as_dict=True)

    #     achieved = 0.0
    #     achieved_gross = 0.0
    #     achieved_gst = 0.0
    #     achieved_exgst = 0.0
    #     achieved_cut = 0.0

    #     for r in achieved_rows:
    #         gross = float(r["v"] or 0)
    #         ex_gst = gross / 1.05
    #         gst = gross - ex_gst
    #         achieved_gross += gross
    #         achieved_gst += gst
    #         achieved_exgst += ex_gst

    #         if r["m"] in LOAN_MODES:
    #             cut = ex_gst * 0.15
    #             achieved_cut += cut
    #             achieved += ex_gst - cut
    #         else:
    #             achieved += ex_gst

    #     # ============================================================
    #     # COUNSELOR PERFORMANCE (actual collections, via Payment Entry
    #     # Reference -> Sales Invoice -> Therapy Plan)
    #     # ============================================================
    #     counselor_emps = get_counselor_performance(branch, t_from, t_to)

    #     # Daily collections (for chart - from Payment Entry)
    #     days = frappe.db.sql("""SELECT posting_date AS d, SUM(paid_amount) AS g
    #         FROM `tabPayment Entry`
    #         WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    #         GROUP BY posting_date ORDER BY posting_date""",
    #         {"b": branch, "f": d14, "t": today}, as_dict=True)

    #     # Payment mode breakdown by day
    #     pm = frappe.db.sql("""SELECT posting_date AS d, mode_of_payment AS m, SUM(paid_amount) AS v
    #         FROM `tabPayment Entry`
    #         WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    #         GROUP BY posting_date, mode_of_payment""",
    #         {"b": branch, "f": d14, "t": today}, as_dict=True)

    #     # TODAY'S COLLECTIONS (Payment Entry)
    #     paid_today = frappe.db.sql("""SELECT IFNULL(SUM(paid_amount),0) FROM `tabPayment Entry`
    #         WHERE docstatus=1 AND branch=%(b)s AND posting_date=%(t)s""",
    #         {"b": branch, "t": today})[0][0]

    #     # Payment-mode breakdown for TODAY
    #     pm_today = frappe.db.sql("""SELECT mode_of_payment AS m, SUM(paid_amount) AS v
    #         FROM `tabPayment Entry`
    #         WHERE docstatus=1 AND branch=%(b)s AND posting_date=%(t)s
    #         GROUP BY mode_of_payment ORDER BY v DESC""",
    #         {"b": branch, "t": today}, as_dict=True)

    #     pm_today_detail = []
    #     for r in pm_today:
    #         gross = float(r["v"] or 0)
    #         ex_gst = gross / 1.05
    #         gst = gross - ex_gst
    #         is_loan = r["m"] in LOAN_MODES
    #         if is_loan:
    #             cut = ex_gst * 0.15
    #             final = ex_gst - cut
    #         else:
    #             cut = 0
    #             final = ex_gst
    #         pm_today_detail.append({
    #             "m": r["m"] or "Unknown",
    #             "v": round(gross, 2),
    #             "gst": round(gst, 2),
    #             "ex_gst": round(ex_gst, 2),
    #             "is_loan": is_loan,
    #             "cut": round(cut, 2),
    #             "final": round(final, 2)
    #         })

    #     # MTD COLLECTIONS (Payment Entry) with GST breakdown
    #     paid_mtd_rows = frappe.db.sql("""SELECT mode_of_payment AS m, SUM(paid_amount) AS v
    #         FROM `tabPayment Entry`
    #         WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    #         GROUP BY mode_of_payment""",
    #         {"b": branch, "f": cyc_start, "t": cyc_end}, as_dict=True)

    #     paid_mtd_gross = 0.0
    #     paid_mtd_exgst = 0.0
    #     paid_mtd_gst = 0.0
    #     for r in paid_mtd_rows:
    #         gross = float(r["v"] or 0)
    #         ex_gst = gross / 1.05
    #         gst = gross - ex_gst
    #         paid_mtd_gross += gross
    #         paid_mtd_exgst += ex_gst
    #         paid_mtd_gst += gst

    #     # Today's collections with GST breakdown
    #     paid_today_rows = frappe.db.sql("""SELECT mode_of_payment AS m, SUM(paid_amount) AS v
    #         FROM `tabPayment Entry`
    #         WHERE docstatus=1 AND branch=%(b)s AND posting_date=%(t)s
    #         GROUP BY mode_of_payment""",
    #         {"b": branch, "t": today}, as_dict=True)

    #     paid_today_gross = 0.0
    #     paid_today_exgst = 0.0
    #     paid_today_gst = 0.0
    #     for r in paid_today_rows:
    #         gross = float(r["v"] or 0)
    #         ex_gst = gross / 1.05
    #         gst = gross - ex_gst
    #         paid_today_gross += gross
    #         paid_today_exgst += ex_gst
    #         paid_today_gst += gst

    #     # Pending balances (from Sales Invoice - outstanding)
    #     pend = frappe.db.sql("""SELECT customer AS c, COUNT(DISTINCT name) AS inv, SUM(grand_total) AS pkg,
    #         SUM(grand_total - outstanding_amount) AS paid, SUM(outstanding_amount) AS due,
    #         DATEDIFF(%(t)s, MIN(posting_date)) AS days
    #         FROM `tabSales Invoice`
    #         WHERE docstatus=1 AND branch=%(b)s AND outstanding_amount > 0
    #         GROUP BY customer ORDER BY due DESC LIMIT 25""",
    #         {"b": branch, "t": today}, as_dict=True)

    #     # Media sources (from Therapy Plan)
    #     media = frappe.db.sql("""SELECT IFNULL(media,'Unknown') AS m, COUNT(name) AS c,
    #         IFNULL(SUM(custom_total_plan_amount),0) AS v FROM `tabTherapy Plan`
    #         WHERE branch=%(b)s AND start_date BETWEEN %(f)s AND %(t)s
    #         GROUP BY media ORDER BY v DESC""",
    #         {"b": branch, "f": cyc_start, "t": cyc_end}, as_dict=True)

    #     # Appointments
    #     AP_CASE = """
    #         SUM(CASE WHEN custom_appointment_status='Visited Booked' THEN 1 ELSE 0 END) AS visited_booked,
    #         SUM(CASE WHEN custom_appointment_status='Visited Not Booked' THEN 1 ELSE 0 END) AS visited_not_booked,
    #         SUM(CASE WHEN custom_appointment_status='Not Visited' THEN 1 ELSE 0 END) AS not_visited,
    #         SUM(CASE WHEN IFNULL(custom_appointment_status,'') IN ('','Not Booked','Booked') THEN 1 ELSE 0 END) AS booked,
    #         SUM(CASE WHEN custom_appointment_status='Cancelled' THEN 1 ELSE 0 END) AS cancelled,
    #         COUNT(*) AS total
    #     """

    #     ap_today = frappe.db.sql("SELECT" + AP_CASE + """
    #         FROM `tabLead`
    #         WHERE custom_appointment_date_and_time IS NOT NULL
    #           AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
    #           AND DATE(custom_appointment_date_and_time)=%(t)s""",
    #         {"b": branch, "t": today}, as_dict=True)[0]

    #     ap_cycle = frappe.db.sql("SELECT" + AP_CASE + """
    #         FROM `tabLead`
    #         WHERE custom_appointment_date_and_time IS NOT NULL
    #           AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
    #           AND DATE(custom_appointment_date_and_time) BETWEEN %(f)s AND %(t)s""",
    #         {"b": branch, "f": cyc_start, "t": cyc_end}, as_dict=True)[0]

    #     ap_branch_summary = frappe.db.sql("SELECT IFNULL(branch,'Head Office') AS branch," + AP_CASE + """
    #         FROM `tabLead`
    #         WHERE custom_appointment_date_and_time IS NOT NULL
    #           AND DATE(custom_appointment_date_and_time) BETWEEN %(f)s AND %(t)s
    #         GROUP BY IFNULL(branch,'Head Office') ORDER BY branch""",
    #         {"f": cyc_start, "t": cyc_end}, as_dict=True)

    #     # Leads
    #     leads = frappe.db.sql("""SELECT COUNT(*) t,
    #         SUM(CASE WHEN custom_appointment_status IN ('Visited Booked','Visited Not Booked') THEN 1 ELSE 0 END) w,
    #         SUM(CASE WHEN custom_appointment_status='Visited Booked' THEN 1 ELSE 0 END) bk,
    #         SUM(CASE WHEN custom_cc_stage='FOLLOW-UP' THEN 1 ELSE 0 END) fu
    #         FROM `tabLead`
    #         WHERE custom_posting_date=%(t)s AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)""",
    #         {"b": branch, "t": today}, as_dict=True)[0]

    #     # Walk-ins
    #     walkins = frappe.db.sql("""SELECT name AS id, lead_name AS n, lead_owner AS by_,
    #         TIME_FORMAT(custom_appointment_date_and_time,'%%H:%%i') AS t,
    #         IFNULL(NULLIF(custom_appointment_status,''),'Not Booked') AS st
    #         FROM `tabLead`
    #         WHERE (branch=%(b)s OR lead_assign_to_branch=%(b)s)
    #           AND DATE(custom_appointment_date_and_time)=%(t)s
    #         ORDER BY custom_appointment_date_and_time LIMIT 12""",
    #         {"b": branch, "t": today}, as_dict=True)

    #     # Attendance
    #     att = frappe.db.sql("""SELECT e.employee_name AS n, e.designation AS dg,
    #         IFNULL(a.status,'Absent') AS st,
    #         TIME_FORMAT(a.custom_check_in_time,'%%H:%%i') AS pin,
    #         TIME_FORMAT(a.custom_check_out_time,'%%H:%%i') AS pout
    #         FROM `tabEmployee` e
    #         LEFT JOIN `tabAttendance` a ON a.employee=e.name AND a.attendance_date=%(t)s AND a.docstatus < 2
    #         WHERE e.status='Active' AND e.branch=%(b)s
    #         ORDER BY e.employee_name LIMIT 25""",
    #         {"b": branch, "t": today}, as_dict=True)

    #     # Stock
    #     wpat = "%" + branch.replace(" ", "") + "%"
    #     stock = frappe.db.sql("""SELECT SUM(CASE WHEN b.actual_qty <= 0 THEN 1 ELSE 0 END) AS zero,
    #         COUNT(*) AS items, IFNULL(SUM(b.stock_value),0) AS val
    #         FROM `tabBin` b JOIN `tabItem` i ON i.name = b.item_code
    #         WHERE REPLACE(b.warehouse,' ','') LIKE %(w)s AND i.is_stock_item = 1""",
    #         {"w": wpat}, as_dict=True)[0]

    #     stock_zero_items = frappe.db.sql("""SELECT i.item_name AS n, b.item_code AS code
    #         FROM `tabBin` b JOIN `tabItem` i ON i.name = b.item_code
    #         WHERE REPLACE(b.warehouse,' ','') LIKE %(w)s AND i.is_stock_item = 1
    #           AND b.actual_qty <= 0
    #         ORDER BY i.item_name LIMIT 300""",
    #         {"w": wpat}, as_dict=True)

    #     # Grievances
    #     grv = frappe.db.sql("""SELECT IFNULL(SUM(status='Open'),0) AS open_,
    #         IFNULL(SUM(status='Escalated'),0) AS esc,
    #         IFNULL(SUM(priority='Red' AND status!='Closed'),0) AS red,
    #         IFNULL(SUM(status='Closed'),0) AS closed
    #         FROM `tabGrievance Ticket` WHERE branch=%(b)s""",
    #         {"b": branch}, as_dict=True)[0]

    #     # Worklist
    #     work = frappe.db.sql("""SELECT COUNT(*) AS open_,
    #         SUM(CASE WHEN date < %(t)s THEN 1 ELSE 0 END) AS over_,
    #         SUM(CASE WHEN priority='High' THEN 1 ELSE 0 END) AS hi,
    #         SUM(CASE WHEN date = %(t)s THEN 1 ELSE 0 END) AS due
    #         FROM `tabToDo` WHERE status='Open' AND allocated_to=%(u)s""",
    #         {"t": today, "u": frappe.session.user}, as_dict=True)[0]

    #     frappe.response["message"] = {
    #         "branch": branch,
    #         "cycle": [str(cyc_start), str(cyc_end)],
    #         "target": target,
    #         "target_window": [t_from, t_to],
    #         "achieved": achieved,
    #         "achieved_gross": achieved_gross,
    #         "achieved_gst": achieved_gst,
    #         "achieved_exgst": achieved_exgst,
    #         "achieved_cut": achieved_cut,
    #         "days": days,
    #         "pm": pm,
    #         "paid_today_gross": paid_today_gross,
    #         "paid_today_exgst": paid_today_exgst,
    #         "paid_today_gst": paid_today_gst,
    #         "paid_mtd_gross": paid_mtd_gross,
    #         "paid_mtd_exgst": paid_mtd_exgst,
    #         "paid_mtd_gst": paid_mtd_gst,
    #         "pm_today": pm_today,
    #         "pm_today_detail": pm_today_detail,
    #         "emps": counselor_emps,
    #         "pend": pend,
    #         "media": media,
    #         "ap_today": ap_today,
    #         "ap_cycle": ap_cycle,
    #         "ap_branch_summary": ap_branch_summary,
    #         "leads": leads,
    #         "walkins": walkins,
    #         "att": att,
    #         "stock": stock,
    #         "stock_zero_items": stock_zero_items,
    #         "grv": grv,
    #         "work": work
    #     }
































    # # Server Script  |  Script Type: API  |  API Method: branch_command_center
    # # v16 - UNIFIED WINDOW
    # #
    # # WHAT CHANGED vs the live version
    # # --------------------------------
    # # 1. ONE code path. The old script had a "range path" that returned ONLY
    # #    {"range": {...}} - so Appointments, Media, Leads, Walk-ins, Pending,
    # #    Attendance, Stock, Grievance and Worklist all went BLANK the moment a
    # #    custom date range was applied. Now everything is computed once against
    # #    a single window (win_from -> win_to) and the full payload is always
    # #    returned. The "range" key is still emitted when a range is active so
    # #    the existing JS range branch keeps working.
    # #
    # # 2. win_from / win_to = the picked range if supplied, else the current
    # #    6th-to-5th billing cycle. Every date-scoped query uses it.
    # #
    # # 3. PENDING BALANCES are now date-scoped. Previously the Sales Invoice
    # #    outstanding query had NO date filter at all, so "Pending" showed the
    # #    same all-time number no matter what dates you picked.
    # #
    # # 4. TARGET is the sum of Week Target rows overlapping the window, so it
    # #    moves with the picked dates. Achieved stays Payment Entry collections.
    # #
    # # 5. MEDIA / SOURCE now returns gross + gst + ex_gst + invoiced totals per
    # #    source, so the tile can show with-GST and without-GST side by side.
    # #
    # # 6. ap_branch_summary is now scoped to the SELECTED BRANCH only (it used
    # #    to query every branch, ignoring the selector).
    # #
    # # 7. Appointment + Lead status buckets match the "Branch Wise CC
    # #    Appointments" block's kpGetStatus() exactly:
    # #       '' / 'Not Booked' / 'Booked' -> booked  (CC booked, awaiting visit)
    # #       'Visited Booked'             -> visited_booked
    # #       'Visited Not Booked'         -> visited_not_booked
    # #       'Not Visited'                -> not_visited
    # #       'Cancelled'                  -> cancelled
    # #
    # # safe_exec safe: no f-strings, no imports, no tuple unpacking,
    # # no augmented dict assignment, no frappe.get_roles().

    # branch = frappe.form_dict.get("branch")
    # if not branch:
    #     frappe.throw("branch required")

    # is_sysmgr = frappe.db.exists("Has Role",
    #     {"parent": frappe.session.user, "role": "System Manager"})
    # if not is_sysmgr:
    #     allowed = [d.for_value for d in frappe.get_all("User Permission",
    #         filters={"user": frappe.session.user, "allow": "Branch"}, fields=["for_value"])]
    #     if allowed and branch not in allowed:
    #         frappe.throw("Not permitted for this branch")

    # LOAN_MODES = ("Carepay", "Fibe Finance", "ShopSE", "Liqui Loans Charges",
    #               "Loan Tap / Uno Finance Charges", "Savein Fintech Card Charges",
    #               "Sai Roshini Card Charges", "Bajaj Card Charges")

    # AP_CASE = """
    #     SUM(CASE WHEN custom_appointment_status='Visited Booked' THEN 1 ELSE 0 END) AS visited_booked,
    #     SUM(CASE WHEN custom_appointment_status='Visited Not Booked' THEN 1 ELSE 0 END) AS visited_not_booked,
    #     SUM(CASE WHEN custom_appointment_status='Not Visited' THEN 1 ELSE 0 END) AS not_visited,
    #     SUM(CASE WHEN IFNULL(custom_appointment_status,'') IN ('','Not Booked','Booked') THEN 1 ELSE 0 END) AS booked,
    #     SUM(CASE WHEN custom_appointment_status='Cancelled' THEN 1 ELSE 0 END) AS cancelled,
    #     COUNT(*) AS total
    # """


    # def get_counselor_performance(branch, from_date, to_date):
    #     rows = frappe.db.sql("""
    #         SELECT
    #             tp.custom_employee_name AS n,
    #             SUM(per.allocated_amount) AS gross,
    #             COUNT(DISTINCT tp.name) AS conv
    #         FROM `tabPayment Entry Reference` per
    #         JOIN `tabPayment Entry` pe ON pe.name = per.parent
    #         JOIN `tabSales Invoice` si ON si.name = per.reference_name
    #             AND per.reference_doctype = 'Sales Invoice'
    #         JOIN `tabTherapy Plan` tp ON tp.name = si.therapy_plan_reference_id
    #         WHERE pe.docstatus = 1
    #             AND pe.branch = %(b)s
    #             AND pe.posting_date BETWEEN %(f)s AND %(t)s
    #             AND IFNULL(tp.custom_employee_name,'') != ''
    #         GROUP BY tp.custom_employee_name
    #         ORDER BY gross DESC
    #     """, {"b": branch, "f": from_date, "t": to_date}, as_dict=True)

    #     emps = []
    #     for e in rows:
    #         gross = float(e["gross"] or 0)
    #         if gross == 0:
    #             continue
    #         ex_gst = gross / 1.05
    #         gst = gross - ex_gst
    #         designation = frappe.db.get_value("Employee",
    #             {"employee_name": e["n"], "status": "Active"}, "designation") or ""
    #         emps.append({
    #             "n": e["n"],
    #             "dg": designation,
    #             "gross": round(gross, 2),
    #             "gst": round(gst, 2),
    #             "net": round(ex_gst, 2),
    #             "conv": e["conv"],
    #         })
    #     return emps


    # # ============================================================
    # # WINDOW RESOLUTION - one window drives every query below
    # # ============================================================
    # today = frappe.utils.nowdate()
    # d = frappe.utils.getdate(today)

    # if d.day >= 6:
    #     cyc_start = frappe.utils.get_first_day(d).replace(day=6)
    # else:
    #     cyc_start = frappe.utils.add_months(frappe.utils.get_first_day(d), -1).replace(day=6)
    # cyc_end = frappe.utils.add_days(frappe.utils.add_months(cyc_start, 1), -1)

    # range_from = frappe.form_dict.get("from_date")
    # range_to = frappe.form_dict.get("to_date")
    # has_range = 1 if (range_from and range_to) else 0

    # if has_range:
    #     win_from = range_from
    #     win_to = range_to
    # else:
    #     win_from = str(cyc_start)
    #     win_to = str(cyc_end)

    # d14 = frappe.utils.add_days(win_to, -13)

    # # ============================================================
    # # TARGET - sum of weekly target rows overlapping the window
    # # ============================================================
    # tgt_rows = frappe.db.sql("""
    #     SELECT DISTINCT wa.name AS rid, wa.targeted_amount AS amt,
    #           wt.from_date AS f, wt.to_date AS t
    #     FROM `tabWeek Achive` wa
    #     JOIN `tabWeek Target vs Achive With Cuttings` wt ON wt.name = wa.parent
    #     WHERE wa.branch = %(b)s AND wt.from_date <= %(t)s AND wt.to_date >= %(f)s
    # """, {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # target = 0.0
    # for r in tgt_rows:
    #     target = target + float(r["amt"] or 0)

    # if tgt_rows:
    #     t_from = str(min([r["f"] for r in tgt_rows]))
    #     t_to = str(max([r["t"] for r in tgt_rows]))
    # else:
    #     t_from = win_from
    #     t_to = win_to

    # # ============================================================
    # # COLLECTIONS (Payment Entry) for the window
    # # ============================================================
    # mode_rows = frappe.db.sql("""SELECT mode_of_payment AS m, SUM(paid_amount) AS v
    #     FROM `tabPayment Entry`
    #     WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    #     GROUP BY mode_of_payment ORDER BY v DESC""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # modes = []
    # pm_detail = []
    # tot_gross = 0.0
    # tot_gst = 0.0
    # tot_exgst = 0.0
    # tot_cut = 0.0
    # tot_final = 0.0

    # for r in mode_rows:
    #     gross = float(r["v"] or 0)
    #     ex_gst = gross / 1.05
    #     gst = gross - ex_gst
    #     is_loan = r["m"] in LOAN_MODES
    #     if is_loan:
    #         cut_amt = ex_gst * 0.15
    #         final = ex_gst - cut_amt
    #     else:
    #         cut_amt = 0.0
    #         final = ex_gst

    #     modes.append({
    #         "mode": r["m"] or "Unknown",
    #         "gross": round(gross, 2),
    #         "gst": round(gst, 2),
    #         "ex_gst": round(ex_gst, 2),
    #         "is_loan": is_loan,
    #         "cut_amt": round(cut_amt, 2),
    #         "final": round(final, 2),
    #     })
    #     pm_detail.append({
    #         "m": r["m"] or "Unknown",
    #         "v": round(gross, 2),
    #         "gst": round(gst, 2),
    #         "ex_gst": round(ex_gst, 2),
    #         "is_loan": is_loan,
    #         "cut": round(cut_amt, 2),
    #         "final": round(final, 2),
    #     })
    #     tot_gross = tot_gross + gross
    #     tot_gst = tot_gst + gst
    #     tot_exgst = tot_exgst + ex_gst
    #     tot_cut = tot_cut + cut_amt
    #     tot_final = tot_final + final

    # # Today's collections stay real "today" - the tile labels them Today
    # today_rows = frappe.db.sql("""SELECT mode_of_payment AS m, SUM(paid_amount) AS v
    #     FROM `tabPayment Entry`
    #     WHERE docstatus=1 AND branch=%(b)s AND posting_date=%(t)s
    #     GROUP BY mode_of_payment ORDER BY v DESC""",
    #     {"b": branch, "t": today}, as_dict=True)

    # paid_today_gross = 0.0
    # paid_today_exgst = 0.0
    # paid_today_gst = 0.0
    # pm_today_detail = []
    # for r in today_rows:
    #     gross = float(r["v"] or 0)
    #     ex_gst = gross / 1.05
    #     gst = gross - ex_gst
    #     is_loan = r["m"] in LOAN_MODES
    #     if is_loan:
    #         cut = ex_gst * 0.15
    #         final = ex_gst - cut
    #     else:
    #         cut = 0.0
    #         final = ex_gst
    #     paid_today_gross = paid_today_gross + gross
    #     paid_today_exgst = paid_today_exgst + ex_gst
    #     paid_today_gst = paid_today_gst + gst
    #     pm_today_detail.append({
    #         "m": r["m"] or "Unknown",
    #         "v": round(gross, 2),
    #         "gst": round(gst, 2),
    #         "ex_gst": round(ex_gst, 2),
    #         "is_loan": is_loan,
    #         "cut": round(cut, 2),
    #         "final": round(final, 2),
    #     })

    # counselor_emps = get_counselor_performance(branch, win_from, win_to)

    # days = frappe.db.sql("""SELECT posting_date AS d, SUM(paid_amount) AS g
    #     FROM `tabPayment Entry`
    #     WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    #     GROUP BY posting_date ORDER BY posting_date""",
    #     {"b": branch, "f": d14, "t": win_to}, as_dict=True)

    # pm = frappe.db.sql("""SELECT posting_date AS d, mode_of_payment AS m, SUM(paid_amount) AS v
    #     FROM `tabPayment Entry`
    #     WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    #     GROUP BY posting_date, mode_of_payment""",
    #     {"b": branch, "f": d14, "t": win_to}, as_dict=True)

    # # ============================================================
    # # PENDING BALANCES - now scoped to the window's posting_date
    # # ============================================================
    # pend = frappe.db.sql("""SELECT customer AS c, COUNT(DISTINCT name) AS inv,
    #     SUM(grand_total) AS pkg,
    #     SUM(grand_total - outstanding_amount) AS paid,
    #     SUM(outstanding_amount) AS due,
    #     DATEDIFF(%(today)s, MIN(posting_date)) AS days
    #     FROM `tabSales Invoice`
    #     WHERE docstatus=1 AND branch=%(b)s AND outstanding_amount > 0
    #       AND posting_date BETWEEN %(f)s AND %(t)s
    #     GROUP BY customer ORDER BY due DESC LIMIT 25""",
    #     {"b": branch, "f": win_from, "t": win_to, "today": today}, as_dict=True)

    # pend_tot = frappe.db.sql("""SELECT IFNULL(SUM(outstanding_amount),0) AS due,
    #     COUNT(DISTINCT name) AS inv, COUNT(DISTINCT customer) AS cust
    #     FROM `tabSales Invoice`
    #     WHERE docstatus=1 AND branch=%(b)s AND outstanding_amount > 0
    #       AND posting_date BETWEEN %(f)s AND %(t)s""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)[0]

    # # ============================================================
    # # SOURCE / MEDIA MIX - with GST and without GST, from Sales Invoice
    # # ============================================================
    # media = frappe.db.sql("""SELECT IFNULL(NULLIF(tp.media,''),'Unknown') AS m,
    #         COUNT(DISTINCT tp.name) AS c,
    #         IFNULL(SUM(tp.custom_total_plan_amount),0) AS v
    #     FROM `tabTherapy Plan` tp
    #     WHERE tp.branch=%(b)s AND tp.start_date BETWEEN %(f)s AND %(t)s
    #     GROUP BY IFNULL(NULLIF(tp.media,''),'Unknown')
    #     ORDER BY v DESC""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # # Invoiced value per source with real GST split off Sales Invoice
    # media_inv = frappe.db.sql("""SELECT IFNULL(NULLIF(tp.media,''),'Unknown') AS m,
    #         IFNULL(SUM(si.grand_total),0) AS gross,
    #         IFNULL(SUM(si.net_total),0) AS ex_gst,
    #         IFNULL(SUM(si.total_taxes_and_charges),0) AS gst,
    #         COUNT(DISTINCT si.name) AS inv
    #     FROM `tabSales Invoice` si
    #     JOIN `tabTherapy Plan` tp ON tp.name = si.therapy_plan_reference_id
    #     WHERE si.docstatus=1 AND si.branch=%(b)s
    #       AND si.posting_date BETWEEN %(f)s AND %(t)s
    #     GROUP BY IFNULL(NULLIF(tp.media,''),'Unknown')""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # # Collected per source: Payment Entry -> Payment Entry Reference ->
    # # Sales Invoice -> Therapy Plan.media. This is the SAME money the
    # # Collections tile reports, split by source, so the two tiles reconcile.
    # # (Invoiced value alone never matches collections, because invoices raised
    # # in the window may be part-paid and payments in the window may settle
    # # invoices raised earlier.)
    # media_coll = frappe.db.sql("""SELECT IFNULL(NULLIF(tp.media,''),'Unknown') AS m,
    #         IFNULL(SUM(per.allocated_amount),0) AS coll
    #     FROM `tabPayment Entry Reference` per
    #     JOIN `tabPayment Entry` pe ON pe.name = per.parent
    #     JOIN `tabSales Invoice` si ON si.name = per.reference_name
    #         AND per.reference_doctype = 'Sales Invoice'
    #     JOIN `tabTherapy Plan` tp ON tp.name = si.therapy_plan_reference_id
    #     WHERE pe.docstatus = 1 AND pe.branch = %(b)s
    #       AND pe.posting_date BETWEEN %(f)s AND %(t)s
    #     GROUP BY IFNULL(NULLIF(tp.media,''),'Unknown')""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # coll_map = {}
    # for r in media_coll:
    #     coll_map[r["m"]] = float(r["coll"] or 0)

    # inv_map = {}
    # for r in media_inv:
    #     inv_map[r["m"]] = r

    # media_out = []
    # for r in media:
    #     plan_gross = float(r["v"] or 0)
    #     hit = inv_map.get(r["m"])
    #     if hit:
    #         i_gross = float(hit["gross"] or 0)
    #         i_exgst = float(hit["ex_gst"] or 0)
    #         i_gst = float(hit["gst"] or 0)
    #         i_cnt = hit["inv"]
    #     else:
    #         i_gross = 0.0
    #         i_exgst = 0.0
    #         i_gst = 0.0
    #         i_cnt = 0
    #     c_gross = coll_map.get(r["m"]) or 0.0
    #     media_out.append({
    #         "m": r["m"],
    #         "c": r["c"],
    #         "v": round(plan_gross, 2),
    #         "plan_ex_gst": round(plan_gross / 1.05, 2),
    #         "plan_gst": round(plan_gross - (plan_gross / 1.05), 2),
    #         "inv_gross": round(i_gross, 2),
    #         "inv_ex_gst": round(i_exgst, 2),
    #         "inv_gst": round(i_gst, 2),
    #         "inv_count": i_cnt,
    #         "coll_gross": round(c_gross, 2),
    #         "coll_ex_gst": round(c_gross / 1.05, 2),
    #         "coll_gst": round(c_gross - (c_gross / 1.05), 2),
    #     })

    # # Sources present on invoices but with no plan row in window
    # for r in media_inv:
    #     found = 0
    #     for x in media_out:
    #         if x["m"] == r["m"]:
    #             found = 1
    #     if not found:
    #         c2 = coll_map.get(r["m"]) or 0.0
    #         media_out.append({
    #             "m": r["m"],
    #             "c": 0,
    #             "v": 0,
    #             "plan_ex_gst": 0,
    #             "plan_gst": 0,
    #             "inv_gross": round(float(r["gross"] or 0), 2),
    #             "inv_ex_gst": round(float(r["ex_gst"] or 0), 2),
    #             "inv_gst": round(float(r["gst"] or 0), 2),
    #             "inv_count": r["inv"],
    #             "coll_gross": round(c2, 2),
    #             "coll_ex_gst": round(c2 / 1.05, 2),
    #             "coll_gst": round(c2 - (c2 / 1.05), 2),
    #         })

    # # Sources that received money in the window but have neither a plan nor an
    # # invoice dated in it (payment against an older invoice).
    # for k in coll_map:
    #     seen = 0
    #     for x in media_out:
    #         if x["m"] == k:
    #             seen = 1
    #     if not seen:
    #         cv = coll_map[k]
    #         media_out.append({
    #             "m": k, "c": 0, "v": 0, "plan_ex_gst": 0, "plan_gst": 0,
    #             "inv_gross": 0, "inv_ex_gst": 0, "inv_gst": 0, "inv_count": 0,
    #             "coll_gross": round(cv, 2),
    #             "coll_ex_gst": round(cv / 1.05, 2),
    #             "coll_gst": round(cv - (cv / 1.05), 2),
    #         })

    # # Named key function rather than a lambda - plain defs are unambiguously
    # # allowed by safe_exec. NOTE: the name must NOT start with an underscore;
    # # RestrictedPython rejects leading-underscore identifiers outright.
    # def coll_key(z):
    #     return z["coll_gross"]

    # media_out = sorted(media_out, key=coll_key, reverse=True)

    # # ============================================================
    # # DAILY TARGET TRACKER (deficit method)
    # # ============================================================
    # # The monthly target is FIXED to the 6th-to-5th cycle and does not shrink
    # # when a shorter range is picked - previously a single-day range still
    # # showed the full monthly target, so realisation always read 0%.
    # #
    # # Deficit method: each morning the target for that day is recomputed as
    # #     (monthly target - collected so far) / days still remaining
    # # so a miss today raises tomorrow's requirement automatically.

    # cyc_tgt_rows = frappe.db.sql("""
    #     SELECT DISTINCT wa.name AS rid, wa.targeted_amount AS amt
    #     FROM `tabWeek Achive` wa
    #     JOIN `tabWeek Target vs Achive With Cuttings` wt ON wt.name = wa.parent
    #     WHERE wa.branch = %(b)s AND wt.from_date <= %(t)s AND wt.to_date >= %(f)s
    # """, {"b": branch, "f": str(cyc_start), "t": str(cyc_end)}, as_dict=True)

    # cycle_target = 0.0
    # for r in cyc_tgt_rows:
    #     cycle_target = cycle_target + float(r["amt"] or 0)

    # cyc_days = frappe.db.sql("""SELECT posting_date AS d, SUM(paid_amount) AS g
    #     FROM `tabPayment Entry`
    #     WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    #     GROUP BY posting_date ORDER BY posting_date""",
    #     {"b": branch, "f": str(cyc_start), "t": str(cyc_end)}, as_dict=True)

    # cyc_day_map = {}
    # for r in cyc_days:
    #     cyc_day_map[str(r["d"])] = float(r["g"] or 0)

    # total_days = frappe.utils.date_diff(cyc_end, cyc_start) + 1
    # elapsed = frappe.utils.date_diff(today, cyc_start) + 1
    # if elapsed < 0:
    #     elapsed = 0
    # if elapsed > total_days:
    #     elapsed = total_days
    # days_left = total_days - elapsed
    # if days_left < 0:
    #     days_left = 0

    # day_rows = []
    # running = 0.0
    # idx = 0
    # while idx < total_days:
    #     dt = frappe.utils.add_days(cyc_start, idx)
    #     dts = str(dt)
    #     remaining_before = total_days - idx
    #     gap_before = cycle_target - running
    #     if gap_before < 0:
    #         gap_before = 0.0
    #     if remaining_before > 0:
    #         req = gap_before / remaining_before
    #     else:
    #         req = 0.0

    #     got = cyc_day_map.get(dts) or 0.0
    #     is_future = 1 if dts > today else 0

    #     if is_future:
    #         hit = None
    #     elif got >= req:
    #         hit = 1
    #     else:
    #         hit = 0

    #     day_rows.append({
    #         "d": dts,
    #         "req": round(req, 2),
    #         "got": round(got, 2),
    #         "diff": round(got - req, 2),
    #         "hit": hit,
    #         "future": is_future,
    #         "cum": round(running + got, 2),
    #     })
    #     running = running + got
    #     idx = idx + 1

    # cycle_achieved = running
    # cycle_gap = cycle_target - cycle_achieved
    # if cycle_gap < 0:
    #     cycle_gap = 0.0

    # if days_left > 0:
    #     req_per_day = cycle_gap / days_left
    # else:
    #     req_per_day = 0.0

    # if elapsed > 0:
    #     run_rate = cycle_achieved / elapsed
    # else:
    #     run_rate = 0.0

    # projected = run_rate * total_days

    # hit_days = 0
    # miss_days = 0
    # for r in day_rows:
    #     if r["hit"] == 1:
    #         hit_days = hit_days + 1
    #     elif r["hit"] == 0:
    #         miss_days = miss_days + 1

    # daily_tracker = {
    #     "cycle_from": str(cyc_start),
    #     "cycle_to": str(cyc_end),
    #     "target": round(cycle_target, 2),
    #     "achieved": round(cycle_achieved, 2),
    #     "gap": round(cycle_gap, 2),
    #     "pct": round((cycle_achieved / cycle_target * 100), 1) if cycle_target else 0,
    #     "total_days": total_days,
    #     "elapsed": elapsed,
    #     "days_left": days_left,
    #     "req_per_day": round(req_per_day, 2),
    #     "run_rate": round(run_rate, 2),
    #     "projected": round(projected, 2),
    #     "on_track": 1 if projected >= cycle_target else 0,
    #     "hit_days": hit_days,
    #     "miss_days": miss_days,
    #     "days": day_rows,
    # }

    # # ============================================================
    # # APPOINTMENTS - selected branch only, window scoped
    # # ============================================================
    # ap_today = frappe.db.sql("SELECT" + AP_CASE + """
    #     FROM `tabLead`
    #     WHERE custom_appointment_date_and_time IS NOT NULL
    #       AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
    #       AND DATE(custom_appointment_date_and_time)=%(t)s""",
    #     {"b": branch, "t": today}, as_dict=True)[0]

    # ap_cycle = frappe.db.sql("SELECT" + AP_CASE + """
    #     FROM `tabLead`
    #     WHERE custom_appointment_date_and_time IS NOT NULL
    #       AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
    #       AND DATE(custom_appointment_date_and_time) BETWEEN %(f)s AND %(t)s""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)[0]

    # # Selected branch only (was previously every branch)
    # ap_branch_summary = frappe.db.sql("SELECT IFNULL(NULLIF(branch,''),'Head Office') AS branch," + AP_CASE + """
    #     FROM `tabLead`
    #     WHERE custom_appointment_date_and_time IS NOT NULL
    #       AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
    #       AND DATE(custom_appointment_date_and_time) BETWEEN %(f)s AND %(t)s
    #     GROUP BY IFNULL(NULLIF(branch,''),'Head Office') ORDER BY branch""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # # Appointment rows for drill-down, same shape as the CC block
    # ap_rows = frappe.db.sql("""SELECT name AS id, lead_name AS n, lead_owner AS by_,
    #     IFNULL(NULLIF(branch,''),'Head Office') AS br,
    #     custom_appointment_date_and_time AS dt,
    #     IFNULL(NULLIF(custom_appointment_status,''),'Booked') AS st,
    #     IFNULL(custom_remarks,'') AS rm,
    #     IFNULL(source,'') AS src, IFNULL(custom_media,'') AS med
    #     FROM `tabLead`
    #     WHERE custom_appointment_date_and_time IS NOT NULL
    #       AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
    #       AND DATE(custom_appointment_date_and_time) BETWEEN %(f)s AND %(t)s
    #     ORDER BY custom_appointment_date_and_time DESC LIMIT 500""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # # ============================================================
    # # CC LEADS coming to this branch - window scoped, CC buckets
    # # ============================================================
    # leads = frappe.db.sql("""SELECT COUNT(*) t,
    #     SUM(CASE WHEN custom_appointment_status IN ('Visited Booked','Visited Not Booked') THEN 1 ELSE 0 END) w,
    #     SUM(CASE WHEN custom_appointment_status='Visited Booked' THEN 1 ELSE 0 END) bk,
    #     SUM(CASE WHEN custom_appointment_status='Visited Not Booked' THEN 1 ELSE 0 END) nbk,
    #     SUM(CASE WHEN custom_appointment_status='Not Visited' THEN 1 ELSE 0 END) nv,
    #     SUM(CASE WHEN IFNULL(custom_appointment_status,'') IN ('','Not Booked','Booked') THEN 1 ELSE 0 END) aw,
    #     SUM(CASE WHEN custom_cc_stage='FOLLOW-UP' THEN 1 ELSE 0 END) fu
    #     FROM `tabLead`
    #     WHERE custom_posting_date BETWEEN %(f)s AND %(t)s
    #       AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)[0]

    # lead_src = frappe.db.sql("""SELECT IFNULL(NULLIF(source,''),'Unknown') AS s,
    #     COUNT(*) AS c,
    #     SUM(CASE WHEN custom_appointment_status='Visited Booked' THEN 1 ELSE 0 END) AS bk
    #     FROM `tabLead`
    #     WHERE custom_posting_date BETWEEN %(f)s AND %(t)s
    #       AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
    #     GROUP BY IFNULL(NULLIF(source,''),'Unknown') ORDER BY c DESC LIMIT 25""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # # v16: walk-ins now follow the selected window instead of being pinned to
    # # today, so past dates can actually be reviewed. Includes the date so the
    # # UI can group/label rows.
    # # The updater columns only exist after console_create_lead_fields.py has
    # # been run. Select them conditionally so this script keeps working either
    # # way instead of dying on an unknown column.
    # has_upd = frappe.db.exists("Custom Field",
    #     {"dt": "Lead", "fieldname": "custom_status_updated_by_name"})

    # if has_upd:
    #     UPD_COLS = """, IFNULL(custom_status_updated_by_name,'') AS upd_by,
    #         custom_status_updated_on AS upd_on """
    # else:
    #     UPD_COLS = """, '' AS upd_by, NULL AS upd_on """

    # walkins = frappe.db.sql("""SELECT name AS id, lead_name AS n, lead_owner AS by_,
    #     DATE(custom_appointment_date_and_time) AS d,
    #     TIME_FORMAT(custom_appointment_date_and_time,'%%H:%%i') AS t,
    #     IFNULL(NULLIF(custom_appointment_status,''),'Not Booked') AS st,
    #     IFNULL(custom_remarks,'') AS rm""" + UPD_COLS + """
    #     FROM `tabLead`
    #     WHERE (branch=%(b)s OR lead_assign_to_branch=%(b)s)
    #       AND DATE(custom_appointment_date_and_time) BETWEEN %(f)s AND %(t)s
    #     ORDER BY custom_appointment_date_and_time DESC LIMIT 200""",
    #     {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # # Active employees of this branch - populates the mandatory "updated by"
    # # dropdown on the walk-in status modal.
    # emp_list = frappe.db.sql("""SELECT name AS id, employee_name AS n,
    #         IFNULL(designation,'') AS dg
    #     FROM `tabEmployee`
    #     WHERE status='Active' AND branch=%(b)s
    #     ORDER BY employee_name""",
    #     {"b": branch}, as_dict=True)

    # # ============================================================
    # # ATTENDANCE / STOCK / GRIEVANCE / WORKLIST
    # # ============================================================
    # att = frappe.db.sql("""SELECT e.employee_name AS n, e.designation AS dg,
    #     IFNULL(a.status,'Absent') AS st,
    #     TIME_FORMAT(a.custom_check_in_time,'%%H:%%i') AS pin,
    #     TIME_FORMAT(a.custom_check_out_time,'%%H:%%i') AS pout
    #     FROM `tabEmployee` e
    #     LEFT JOIN `tabAttendance` a ON a.employee=e.name AND a.attendance_date=%(t)s AND a.docstatus < 2
    #     WHERE e.status='Active' AND e.branch=%(b)s
    #     ORDER BY e.employee_name LIMIT 25""",
    #     {"b": branch, "t": today}, as_dict=True)

    # wpat = "%" + branch.replace(" ", "") + "%"
    # stock = frappe.db.sql("""SELECT SUM(CASE WHEN b.actual_qty <= 0 THEN 1 ELSE 0 END) AS zero,
    #     COUNT(*) AS items, IFNULL(SUM(b.stock_value),0) AS val
    #     FROM `tabBin` b JOIN `tabItem` i ON i.name = b.item_code
    #     WHERE REPLACE(b.warehouse,' ','') LIKE %(w)s AND i.is_stock_item = 1""",
    #     {"w": wpat}, as_dict=True)[0]

    # stock_zero_items = frappe.db.sql("""SELECT i.item_name AS n, b.item_code AS code
    #     FROM `tabBin` b JOIN `tabItem` i ON i.name = b.item_code
    #     WHERE REPLACE(b.warehouse,' ','') LIKE %(w)s AND i.is_stock_item = 1
    #       AND b.actual_qty <= 0
    #     ORDER BY i.item_name LIMIT 300""",
    #     {"w": wpat}, as_dict=True)

    # grv = frappe.db.sql("""SELECT IFNULL(SUM(status='Open'),0) AS open_,
    #     IFNULL(SUM(status='Escalated'),0) AS esc,
    #     IFNULL(SUM(priority='Red' AND status!='Closed'),0) AS red,
    #     IFNULL(SUM(status='Closed'),0) AS closed
    #     FROM `tabGrievance Ticket` WHERE branch=%(b)s""",
    #     {"b": branch}, as_dict=True)[0]

    # work = frappe.db.sql("""SELECT COUNT(*) AS open_,
    #     SUM(CASE WHEN date < %(t)s THEN 1 ELSE 0 END) AS over_,
    #     SUM(CASE WHEN priority='High' THEN 1 ELSE 0 END) AS hi,
    #     SUM(CASE WHEN date = %(t)s THEN 1 ELSE 0 END) AS due
    #     FROM `tabToDo` WHERE status='Open' AND allocated_to=%(u)s""",
    #     {"t": today, "u": frappe.session.user}, as_dict=True)[0]

    # # ============================================================
    # # RESPONSE - full payload always. "range" emitted when active
    # # so the existing JS range branch continues to work.
    # # ============================================================
    # payload = {
    #     "branch": branch,
    #     "window": [win_from, win_to],
    #     "has_range": has_range,
    #     "cycle": [win_from, win_to],
    #     "target": round(target, 2),
    #     "target_rows": len(tgt_rows),
    #     "target_window": [t_from, t_to],
    #     "achieved": round(tot_final, 2),
    #     "achieved_gross": round(tot_gross, 2),
    #     "achieved_gst": round(tot_gst, 2),
    #     "achieved_exgst": round(tot_exgst, 2),
    #     "achieved_cut": round(tot_cut, 2),
    #     "days": days,
    #     "pm": pm,
    #     "paid_today_gross": round(paid_today_gross, 2),
    #     "paid_today_exgst": round(paid_today_exgst, 2),
    #     "paid_today_gst": round(paid_today_gst, 2),
    #     "paid_mtd_gross": round(tot_gross, 2),
    #     "paid_mtd_exgst": round(tot_exgst, 2),
    #     "paid_mtd_gst": round(tot_gst, 2),
    #     "pm_today": today_rows,
    #     "pm_today_detail": pm_today_detail,
    #     "pm_window_detail": pm_detail,
    #     "emps": counselor_emps,
    #     "pend": pend,
    #     "pend_total": pend_tot,
    #     "media": media_out,
    #     "ap_today": ap_today,
    #     "ap_cycle": ap_cycle,
    #     "ap_branch_summary": ap_branch_summary,
    #     "ap_rows": ap_rows,
    #     "leads": leads,
    #     "lead_src": lead_src,
    #     "walkins": walkins,
    #     "att": att,
    #     "stock": stock,
    #     "stock_zero_items": stock_zero_items,
    #     "grv": grv,
    #     "work": work,
    #     "daily": daily_tracker,
    #     "emp_list": emp_list,
    # }

    # if has_range:
    #     payload["range"] = {
    #         "from": win_from,
    #         "to": win_to,
    #         "target": round(target, 2),
    #         "target_rows": len(tgt_rows),
    #         "achieved_gross": round(tot_gross, 2),
    #         "achieved_gst": round(tot_gst, 2),
    #         "achieved_ex_gst": round(tot_exgst, 2),
    #         "achieved_cut": round(tot_cut, 2),
    #         "achieved_final": round(tot_final, 2),
    #         "modes": modes,
    #         "emps": counselor_emps,
    #     }

    # frappe.response["message"] = payload

















    # Server Script  |  Script Type: API  |  API Method: branch_command_center
    # v16 - UNIFIED WINDOW
    #
    # WHAT CHANGED vs the live version
    # --------------------------------
    # 1. ONE code path. The old script had a "range path" that returned ONLY
    #    {"range": {...}} - so Appointments, Media, Leads, Walk-ins, Pending,
    #    Attendance, Stock, Grievance and Worklist all went BLANK the moment a
    #    custom date range was applied. Now everything is computed once against
    #    a single window (win_from -> win_to) and the full payload is always
    #    returned. The "range" key is still emitted when a range is active so
    #    the existing JS range branch keeps working.
    #
    # 2. win_from / win_to = the picked range if supplied, else the current
    #    6th-to-5th billing cycle. Every date-scoped query uses it.
    #
    # 3. PENDING BALANCES are now date-scoped. Previously the Sales Invoice
    #    outstanding query had NO date filter at all, so "Pending" showed the
    #    same all-time number no matter what dates you picked.
    #
    # 4. TARGET is the sum of Week Target rows overlapping the window, so it
    #    moves with the picked dates. Achieved stays Payment Entry collections.
    #
    # 5. MEDIA / SOURCE now returns gross + gst + ex_gst + invoiced totals per
    #    source, so the tile can show with-GST and without-GST side by side.
    #
    # 6. ap_branch_summary is now scoped to the SELECTED BRANCH only (it used
    #    to query every branch, ignoring the selector).
    #
    # 7. Appointment + Lead status buckets match the "Branch Wise CC
    #    Appointments" block's kpGetStatus() exactly:
    #       '' / 'Not Booked' / 'Booked' -> booked  (CC booked, awaiting visit)
    #       'Visited Booked'             -> visited_booked
    #       'Visited Not Booked'         -> visited_not_booked
    #       'Not Visited'                -> not_visited
    #       'Cancelled'                  -> cancelled
    #
    # safe_exec safe: no f-strings, no imports, no tuple unpacking,
    # no augmented dict assignment, no frappe.get_roles().

    branch = frappe.form_dict.get("branch")
    if not branch:
        frappe.throw("branch required")

    is_sysmgr = frappe.db.exists("Has Role",
        {"parent": frappe.session.user, "role": "System Manager"})
    if not is_sysmgr:
        allowed = [d.for_value for d in frappe.get_all("User Permission",
            filters={"user": frappe.session.user, "allow": "Branch"}, fields=["for_value"])]
        if allowed and branch not in allowed:
            frappe.throw("Not permitted for this branch")

    LOAN_MODES = ("Carepay", "Fibe Finance", "ShopSE", "Liqui Loans Charges",
                  "Loan Tap / Uno Finance Charges", "Savein Fintech Card Charges",
                  "Sai Roshini Card Charges", "Bajaj Card Charges")

    # NOTE: 'Visited' is an INTERIM state - the client turned up but the
    # booking outcome is not decided yet. It is counted separately, and also
    # rolled into visited_any alongside the two final visited outcomes so
    # footfall figures stay correct.
    AP_CASE = """
    SUM(CASE WHEN custom_appointment_status='Visited Booked' THEN 1 ELSE 0 END) AS visited_booked,
    SUM(CASE WHEN custom_appointment_status='Visited Not Booked' THEN 1 ELSE 0 END) AS visited_not_booked,
    SUM(CASE WHEN custom_appointment_status='Visited' THEN 1 ELSE 0 END) AS visited_pending,
    SUM(CASE WHEN custom_appointment_status IN ('Visited','Visited Booked','Visited Not Booked') THEN 1 ELSE 0 END) AS visited_any,
    SUM(CASE WHEN custom_appointment_status='Not Visited' THEN 1 ELSE 0 END) AS not_visited,
    SUM(CASE WHEN IFNULL(custom_appointment_status,'') IN ('','Not Booked','Booked') THEN 1 ELSE 0 END) AS booked,
    SUM(CASE WHEN custom_appointment_status='Cancelled' THEN 1 ELSE 0 END) AS cancelled,
    COUNT(*) AS total
"""


    def get_counselor_performance(branch, from_date, to_date):
        rows = _read_sql("""
        SELECT
            tp.custom_employee_name AS n,
            SUM(per.allocated_amount) AS gross,
            COUNT(DISTINCT tp.name) AS conv
        FROM `tabPayment Entry Reference` per
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        JOIN `tabSales Invoice` si ON si.name = per.reference_name
            AND per.reference_doctype = 'Sales Invoice'
        JOIN `tabTherapy Plan` tp ON tp.name = si.therapy_plan_reference_id
        WHERE pe.docstatus = 1
            AND pe.branch = %(b)s
            AND pe.posting_date BETWEEN %(f)s AND %(t)s
            AND IFNULL(tp.custom_employee_name,'') != ''
        GROUP BY tp.custom_employee_name
        ORDER BY gross DESC
    """, {"b": branch, "f": from_date, "t": to_date}, as_dict=True)

        emps = []
        for e in rows:
            gross = float(e["gross"] or 0)
            if gross == 0:
                continue
            ex_gst = gross / 1.05
            gst = gross - ex_gst
            practitioner = frappe.db.get_value(
                "Healthcare Practitioner",
                {
                    "practitioner_name": e["n"],
                    "status": "Active"
                },
                ["employee", "designation"],
                as_dict=True
            )

            designation = ""

            if practitioner:
                if practitioner.get("employee"):
                    designation = frappe.db.get_value(
                        "Employee",
                        practitioner.get("employee"),
                        "designation"
                    ) or ""

                if not designation:
                    designation = practitioner.get("designation") or ""

            # Final fallback for older records containing Employee names
            if not designation:
                designation = frappe.db.get_value(
                    "Employee",
                    {
                        "employee_name": e["n"],
                        "status": "Active"
                    },
                    "designation"
                ) or ""
            emps.append({
                "n": e["n"],
                "dg": designation,
                "gross": round(gross, 2),
                "gst": round(gst, 2),
                "net": round(ex_gst, 2),
                "conv": e["conv"],
            })
        return emps


    # ============================================================
    # WINDOW RESOLUTION - one window drives every query below
    # ============================================================
    today = frappe.utils.nowdate()
    d = frappe.utils.getdate(today)

    if d.day >= 6:
        cyc_start = frappe.utils.get_first_day(d).replace(day=6)
    else:
        cyc_start = frappe.utils.add_months(frappe.utils.get_first_day(d), -1).replace(day=6)
    cyc_end = frappe.utils.add_days(frappe.utils.add_months(cyc_start, 1), -1)

    range_from = frappe.form_dict.get("from_date")
    range_to = frappe.form_dict.get("to_date")
    has_range = 1 if (range_from and range_to) else 0

    if has_range:
        win_from = range_from
        win_to = range_to
    else:
        win_from = str(cyc_start)
        win_to = str(cyc_end)

    d14 = frappe.utils.add_days(win_to, -13)

    # ============================================================
    # TARGET - sum of weekly target rows overlapping the window
    # ============================================================
    tgt_rows = _read_sql("""
    SELECT DISTINCT wa.name AS rid, wa.targeted_amount AS amt,
           wt.from_date AS f, wt.to_date AS t
    FROM `tabWeek Achive` wa
    JOIN `tabWeek Target vs Achive With Cuttings` wt ON wt.name = wa.parent
    WHERE wa.branch = %(b)s AND wt.from_date <= %(t)s AND wt.to_date >= %(f)s
""", {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    target = 0.0
    for r in tgt_rows:
        target = target + float(r["amt"] or 0)

    if tgt_rows:
        t_from = str(min([r["f"] for r in tgt_rows]))
        t_to = str(max([r["t"] for r in tgt_rows]))
    else:
        t_from = win_from
        t_to = win_to

    # ============================================================
    # COLLECTIONS (Payment Entry) for the window
    # ============================================================
    mode_rows = _read_sql("""SELECT mode_of_payment AS m, SUM(paid_amount) AS v
    FROM `tabPayment Entry`
    WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY mode_of_payment ORDER BY v DESC""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    modes = []
    pm_detail = []
    tot_gross = 0.0
    tot_gst = 0.0
    tot_exgst = 0.0
    tot_cut = 0.0
    tot_final = 0.0

    for r in mode_rows:
        gross = float(r["v"] or 0)
        ex_gst = gross / 1.05
        gst = gross - ex_gst
        is_loan = r["m"] in LOAN_MODES
        if is_loan:
            cut_amt = ex_gst * 0.15
            final = ex_gst - cut_amt
        else:
            cut_amt = 0.0
            final = ex_gst

        modes.append({
            "mode": r["m"] or "Unknown",
            "gross": round(gross, 2),
            "gst": round(gst, 2),
            "ex_gst": round(ex_gst, 2),
            "is_loan": is_loan,
            "cut_amt": round(cut_amt, 2),
            "final": round(final, 2),
        })
        pm_detail.append({
            "m": r["m"] or "Unknown",
            "v": round(gross, 2),
            "gst": round(gst, 2),
            "ex_gst": round(ex_gst, 2),
            "is_loan": is_loan,
            "cut": round(cut_amt, 2),
            "final": round(final, 2),
        })
        tot_gross = tot_gross + gross
        tot_gst = tot_gst + gst
        tot_exgst = tot_exgst + ex_gst
        tot_cut = tot_cut + cut_amt
        tot_final = tot_final + final

    # Today's collections stay real "today" - the tile labels them Today
    today_rows = _read_sql("""SELECT mode_of_payment AS m, SUM(paid_amount) AS v
    FROM `tabPayment Entry`
    WHERE docstatus=1 AND branch=%(b)s AND posting_date=%(t)s
    GROUP BY mode_of_payment ORDER BY v DESC""",
        {"b": branch, "t": today}, as_dict=True)

    paid_today_gross = 0.0
    paid_today_exgst = 0.0
    paid_today_gst = 0.0
    pm_today_detail = []
    for r in today_rows:
        gross = float(r["v"] or 0)
        ex_gst = gross / 1.05
        gst = gross - ex_gst
        is_loan = r["m"] in LOAN_MODES
        if is_loan:
            cut = ex_gst * 0.15
            final = ex_gst - cut
        else:
            cut = 0.0
            final = ex_gst
        paid_today_gross = paid_today_gross + gross
        paid_today_exgst = paid_today_exgst + ex_gst
        paid_today_gst = paid_today_gst + gst
        pm_today_detail.append({
            "m": r["m"] or "Unknown",
            "v": round(gross, 2),
            "gst": round(gst, 2),
            "ex_gst": round(ex_gst, 2),
            "is_loan": is_loan,
            "cut": round(cut, 2),
            "final": round(final, 2),
        })

    counselor_emps = get_counselor_performance(branch, win_from, win_to)

    days = _read_sql("""SELECT posting_date AS d, SUM(paid_amount) AS g
    FROM `tabPayment Entry`
    WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY posting_date ORDER BY posting_date""",
        {"b": branch, "f": d14, "t": win_to}, as_dict=True)

    pm = _read_sql("""SELECT posting_date AS d, mode_of_payment AS m, SUM(paid_amount) AS v
    FROM `tabPayment Entry`
    WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY posting_date, mode_of_payment""",
        {"b": branch, "f": d14, "t": win_to}, as_dict=True)

    # ============================================================
    # PENDING BALANCES - now scoped to the window's posting_date
    # ============================================================
    pend = _read_sql("""SELECT customer AS c, COUNT(DISTINCT name) AS inv,
    SUM(grand_total) AS pkg,
    SUM(grand_total - outstanding_amount) AS paid,
    SUM(outstanding_amount) AS due,
    DATEDIFF(%(today)s, MIN(posting_date)) AS days
    FROM `tabSales Invoice`
    WHERE docstatus=1 AND branch=%(b)s AND outstanding_amount > 0
      AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY customer ORDER BY due DESC LIMIT 25""",
        {"b": branch, "f": win_from, "t": win_to, "today": today}, as_dict=True)

    pend_tot = _read_sql("""SELECT IFNULL(SUM(outstanding_amount),0) AS due,
    COUNT(DISTINCT name) AS inv, COUNT(DISTINCT customer) AS cust
    FROM `tabSales Invoice`
    WHERE docstatus=1 AND branch=%(b)s AND outstanding_amount > 0
      AND posting_date BETWEEN %(f)s AND %(t)s""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)[0]

    # ============================================================
    # SOURCE / MEDIA MIX - with GST and without GST, from Sales Invoice
    # ============================================================
    media = _read_sql("""SELECT IFNULL(NULLIF(tp.media,''),'Unknown') AS m,
        COUNT(DISTINCT tp.name) AS c,
        IFNULL(SUM(tp.custom_total_plan_amount),0) AS v
    FROM `tabTherapy Plan` tp
    WHERE tp.branch=%(b)s AND tp.start_date BETWEEN %(f)s AND %(t)s
    GROUP BY IFNULL(NULLIF(tp.media,''),'Unknown')
    ORDER BY v DESC""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # Invoiced value per source with real GST split off Sales Invoice
    media_inv = _read_sql("""SELECT IFNULL(NULLIF(tp.media,''),'Unknown') AS m,
        IFNULL(SUM(si.grand_total),0) AS gross,
        IFNULL(SUM(si.net_total),0) AS ex_gst,
        IFNULL(SUM(si.total_taxes_and_charges),0) AS gst,
        COUNT(DISTINCT si.name) AS inv
    FROM `tabSales Invoice` si
    JOIN `tabTherapy Plan` tp ON tp.name = si.therapy_plan_reference_id
    WHERE si.docstatus=1 AND si.branch=%(b)s
      AND si.posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY IFNULL(NULLIF(tp.media,''),'Unknown')""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # Collected per source: Payment Entry -> Payment Entry Reference ->
    # Sales Invoice -> Therapy Plan.media. This is the SAME money the
    # Collections tile reports, split by source, so the two tiles reconcile.
    # (Invoiced value alone never matches collections, because invoices raised
    # in the window may be part-paid and payments in the window may settle
    # invoices raised earlier.)
    media_coll = _read_sql("""SELECT IFNULL(NULLIF(tp.media,''),'Unknown') AS m,
        IFNULL(SUM(per.allocated_amount),0) AS coll
    FROM `tabPayment Entry Reference` per
    JOIN `tabPayment Entry` pe ON pe.name = per.parent
    JOIN `tabSales Invoice` si ON si.name = per.reference_name
        AND per.reference_doctype = 'Sales Invoice'
    JOIN `tabTherapy Plan` tp ON tp.name = si.therapy_plan_reference_id
    WHERE pe.docstatus = 1 AND pe.branch = %(b)s
      AND pe.posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY IFNULL(NULLIF(tp.media,''),'Unknown')""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    coll_map = {}
    for r in media_coll:
        coll_map[r["m"]] = float(r["coll"] or 0)

    inv_map = {}
    for r in media_inv:
        inv_map[r["m"]] = r

    media_out = []
    for r in media:
        plan_gross = float(r["v"] or 0)
        hit = inv_map.get(r["m"])
        if hit:
            i_gross = float(hit["gross"] or 0)
            i_exgst = float(hit["ex_gst"] or 0)
            i_gst = float(hit["gst"] or 0)
            i_cnt = hit["inv"]
        else:
            i_gross = 0.0
            i_exgst = 0.0
            i_gst = 0.0
            i_cnt = 0
        c_gross = coll_map.get(r["m"]) or 0.0
        media_out.append({
            "m": r["m"],
            "c": r["c"],
            "v": round(plan_gross, 2),
            "plan_ex_gst": round(plan_gross / 1.05, 2),
            "plan_gst": round(plan_gross - (plan_gross / 1.05), 2),
            "inv_gross": round(i_gross, 2),
            "inv_ex_gst": round(i_exgst, 2),
            "inv_gst": round(i_gst, 2),
            "inv_count": i_cnt,
            "coll_gross": round(c_gross, 2),
            "coll_ex_gst": round(c_gross / 1.05, 2),
            "coll_gst": round(c_gross - (c_gross / 1.05), 2),
        })

    # Sources present on invoices but with no plan row in window
    for r in media_inv:
        found = 0
        for x in media_out:
            if x["m"] == r["m"]:
                found = 1
        if not found:
            c2 = coll_map.get(r["m"]) or 0.0
            media_out.append({
                "m": r["m"],
                "c": 0,
                "v": 0,
                "plan_ex_gst": 0,
                "plan_gst": 0,
                "inv_gross": round(float(r["gross"] or 0), 2),
                "inv_ex_gst": round(float(r["ex_gst"] or 0), 2),
                "inv_gst": round(float(r["gst"] or 0), 2),
                "inv_count": r["inv"],
                "coll_gross": round(c2, 2),
                "coll_ex_gst": round(c2 / 1.05, 2),
                "coll_gst": round(c2 - (c2 / 1.05), 2),
            })

    # Sources that received money in the window but have neither a plan nor an
    # invoice dated in it (payment against an older invoice).
    for k in coll_map:
        seen = 0
        for x in media_out:
            if x["m"] == k:
                seen = 1
        if not seen:
            cv = coll_map[k]
            media_out.append({
                "m": k, "c": 0, "v": 0, "plan_ex_gst": 0, "plan_gst": 0,
                "inv_gross": 0, "inv_ex_gst": 0, "inv_gst": 0, "inv_count": 0,
                "coll_gross": round(cv, 2),
                "coll_ex_gst": round(cv / 1.05, 2),
                "coll_gst": round(cv - (cv / 1.05), 2),
            })

    # Named key function rather than a lambda - plain defs are unambiguously
    # allowed by safe_exec. NOTE: the name must NOT start with an underscore;
    # RestrictedPython rejects leading-underscore identifiers outright.
    def coll_key(z):
        return z["coll_gross"]

    media_out = sorted(media_out, key=coll_key, reverse=True)

    # ============================================================
    # DAILY TARGET TRACKER (deficit method)
    # ============================================================
    # The monthly target is FIXED to the 6th-to-5th cycle and does not shrink
    # when a shorter range is picked - previously a single-day range still
    # showed the full monthly target, so realisation always read 0%.
    #
    # Deficit method: each morning the target for that day is recomputed as
    #     (monthly target - collected so far) / days still remaining
    # so a miss today raises tomorrow's requirement automatically.

    # v17: the tracker now follows the SELECTED RANGE. It reports on whichever
    # 6th-to-5th cycle the range START falls in, so picking the "Last Month"
    # preset (6th -> 5th of the previous cycle) shows THAT cycle's target and
    # day-by-day hit/miss. With no range it reports the current cycle, as before.
    # Anchor rule: if the selected range CONTAINS today, report the current
    # (live) cycle - otherwise a long range like "This Year" (1 Apr -> today)
    # would anchor on 1 April and wrongly show the March cycle as closed.
    # Only when the whole range sits in the past do we anchor on its start,
    # which is what makes the "Last Month" preset show last month's cycle.
    if win_from <= today and today <= win_to:
        trk_anchor = frappe.utils.getdate(today)
    else:
        trk_anchor = frappe.utils.getdate(win_from)
    if trk_anchor.day >= 6:
        trk_start = frappe.utils.get_first_day(trk_anchor).replace(day=6)
    else:
        trk_start = frappe.utils.add_months(
            frappe.utils.get_first_day(trk_anchor), -1).replace(day=6)
    trk_end = frappe.utils.add_days(frappe.utils.add_months(trk_start, 1), -1)

    # A cycle entirely in the past is CLOSED - every day is settled, nothing
    # remains to collect, so the UI shows a final result rather than a forecast.
    is_closed = 1 if str(trk_end) < today else 0

    cyc_tgt_rows = _read_sql("""
    SELECT DISTINCT wa.name AS rid, wa.targeted_amount AS amt
    FROM `tabWeek Achive` wa
    JOIN `tabWeek Target vs Achive With Cuttings` wt ON wt.name = wa.parent
    WHERE wa.branch = %(b)s AND wt.from_date <= %(t)s AND wt.to_date >= %(f)s
""", {"b": branch, "f": str(trk_start), "t": str(trk_end)}, as_dict=True)

    cycle_target = 0.0
    for r in cyc_tgt_rows:
        cycle_target = cycle_target + float(r["amt"] or 0)

    # v17 FIX: this summed GROSS paid_amount, so target achievement was
    # measured on a different basis to the Collections Analysis tile, which
    # reports NET. On the 06-07 -> 25-07 cycle that overstated achievement by
    # Rs 68,065 (13.10 L gross vs 12.41 L net).
    #
    # Realisation is now measured NET, on the company standard:
    #     ex-GST  = paid_amount x 100/105
    #     loan cut = 15% of ex-GST, on loan modes only
    #     net      = ex-GST - loan cut
    # Gross / GST / cut are kept per day so the drawer can show the full build-up.
    cyc_days = _read_sql("""SELECT posting_date AS d,
        SUM(paid_amount) AS gross,
        SUM(paid_amount / 1.05) AS ex_gst,
        SUM(CASE WHEN mode_of_payment IN %(loan)s
                 THEN (paid_amount / 1.05) * 0.15 ELSE 0 END) AS cut
    FROM `tabPayment Entry`
    WHERE docstatus=1 AND branch=%(b)s AND posting_date BETWEEN %(f)s AND %(t)s
    GROUP BY posting_date ORDER BY posting_date""",
        {"b": branch, "f": str(trk_start), "t": str(trk_end),
         "loan": LOAN_MODES}, as_dict=True)

    cyc_day_map = {}
    cyc_day_detail = {}
    for r in cyc_days:
        ds = str(r["d"])
        g = float(r["gross"] or 0)
        e = float(r["ex_gst"] or 0)
        c = float(r["cut"] or 0)
        cyc_day_map[ds] = e - c
        cyc_day_detail[ds] = {
            "gross": round(g, 2),
            "gst": round(g - e, 2),
            "ex_gst": round(e, 2),
            "cut": round(c, 2),
        }

    total_days = frappe.utils.date_diff(trk_end, trk_start) + 1
    elapsed = frappe.utils.date_diff(today, trk_start) + 1
    if elapsed < 0:
        elapsed = 0
    if elapsed > total_days:
        elapsed = total_days
    days_left = total_days - elapsed
    if days_left < 0:
        days_left = 0

    day_rows = []
    running = 0.0
    idx = 0
    while idx < total_days:
        dt = frappe.utils.add_days(trk_start, idx)
        dts = str(dt)
        remaining_before = total_days - idx
        gap_before = cycle_target - running
        if gap_before < 0:
            gap_before = 0.0
        if remaining_before > 0:
            req = gap_before / remaining_before
        else:
            req = 0.0

        got = cyc_day_map.get(dts) or 0.0
        is_future = 1 if dts > today else 0

        if is_future:
            hit = None
        elif got >= req:
            hit = 1
        else:
            hit = 0

        det = cyc_day_detail.get(dts) or {"gross": 0, "gst": 0, "ex_gst": 0, "cut": 0}
        day_rows.append({
            "d": dts,
            "req": round(req, 2),
            "got": round(got, 2),
            "gross": det["gross"],
            "gst": det["gst"],
            "ex_gst": det["ex_gst"],
            "cut": det["cut"],
            "diff": round(got - req, 2),
            "hit": hit,
            "future": is_future,
            "cum": round(running + got, 2),
        })
        running = running + got
        idx = idx + 1

    cycle_achieved = running
    cycle_gap = cycle_target - cycle_achieved
    if cycle_gap < 0:
        cycle_gap = 0.0

    if days_left > 0:
        req_per_day = cycle_gap / days_left
    else:
        req_per_day = 0.0

    if elapsed > 0:
        run_rate = cycle_achieved / elapsed
    else:
        run_rate = 0.0

    projected = run_rate * total_days

    hit_days = 0
    miss_days = 0
    for r in day_rows:
        if r["hit"] == 1:
            hit_days = hit_days + 1
        elif r["hit"] == 0:
            miss_days = miss_days + 1

    trk_gross = 0.0
    trk_gst = 0.0
    trk_cut = 0.0
    for r in day_rows:
        trk_gross = trk_gross + float(r["gross"] or 0)
        trk_gst = trk_gst + float(r["gst"] or 0)
        trk_cut = trk_cut + float(r["cut"] or 0)

    daily_tracker = {
        "basis": "net",
        "gross": round(trk_gross, 2),
        "gst": round(trk_gst, 2),
        "cut": round(trk_cut, 2),
        "cycle_from": str(trk_start),
        "cycle_to": str(trk_end),
        "is_closed": is_closed,
        "target": round(cycle_target, 2),
        "achieved": round(cycle_achieved, 2),
        "gap": round(cycle_gap, 2),
        "pct": round((cycle_achieved / cycle_target * 100), 1) if cycle_target else 0,
        "total_days": total_days,
        "elapsed": elapsed,
        "days_left": days_left,
        "req_per_day": round(req_per_day, 2),
        "run_rate": round(run_rate, 2),
        "projected": round(projected, 2),
        "on_track": 1 if projected >= cycle_target else 0,
        "hit_days": hit_days,
        "miss_days": miss_days,
        "days": day_rows,
    }

    # ============================================================
    # APPOINTMENTS - selected branch only, window scoped
    # ============================================================
    ap_today = _read_sql("SELECT" + AP_CASE + """
    FROM `tabLead`
    WHERE custom_appointment_date_and_time IS NOT NULL
      AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
      AND DATE(custom_appointment_date_and_time)=%(t)s""",
        {"b": branch, "t": today}, as_dict=True)[0]

    ap_cycle = _read_sql("SELECT" + AP_CASE + """
    FROM `tabLead`
    WHERE custom_appointment_date_and_time IS NOT NULL
      AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
      AND DATE(custom_appointment_date_and_time) BETWEEN %(f)s AND %(t)s""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)[0]

    # Selected branch only (was previously every branch)
    ap_branch_summary = _read_sql("SELECT IFNULL(NULLIF(branch,''),'Head Office') AS branch," + AP_CASE + """
    FROM `tabLead`
    WHERE custom_appointment_date_and_time IS NOT NULL
      AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
      AND DATE(custom_appointment_date_and_time) BETWEEN %(f)s AND %(t)s
    GROUP BY IFNULL(NULLIF(branch,''),'Head Office') ORDER BY branch""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # Appointment rows for drill-down, same shape as the CC block
    ap_rows = _read_sql("""SELECT name AS id, lead_name AS n, lead_owner AS by_,
    IFNULL(NULLIF(branch,''),'Head Office') AS br,
    custom_appointment_date_and_time AS dt,
    IFNULL(NULLIF(custom_appointment_status,''),'Booked') AS st,
    IFNULL(custom_remarks,'') AS rm,
    IFNULL(source,'') AS src, IFNULL(custom_media,'') AS med
    FROM `tabLead`
    WHERE custom_appointment_date_and_time IS NOT NULL
      AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
      AND DATE(custom_appointment_date_and_time) BETWEEN %(f)s AND %(t)s
    ORDER BY custom_appointment_date_and_time DESC LIMIT 500""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # ============================================================
    # CC LEADS coming to this branch - window scoped, CC buckets
    # ============================================================
    leads = _read_sql("""SELECT COUNT(*) t,
    SUM(CASE WHEN custom_appointment_status IN ('Visited','Visited Booked','Visited Not Booked') THEN 1 ELSE 0 END) w,
    SUM(CASE WHEN custom_appointment_status='Visited Booked' THEN 1 ELSE 0 END) bk,
    SUM(CASE WHEN custom_appointment_status='Visited Not Booked' THEN 1 ELSE 0 END) nbk,
    SUM(CASE WHEN custom_appointment_status='Visited' THEN 1 ELSE 0 END) vp,
    SUM(CASE WHEN custom_appointment_status='Not Visited' THEN 1 ELSE 0 END) nv,
    SUM(CASE WHEN IFNULL(custom_appointment_status,'') IN ('','Not Booked','Booked') THEN 1 ELSE 0 END) aw,
    SUM(CASE WHEN custom_cc_stage='FOLLOW-UP' THEN 1 ELSE 0 END) fu
    FROM `tabLead`
    WHERE custom_posting_date BETWEEN %(f)s AND %(t)s
      AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)[0]

    lead_src = _read_sql("""SELECT IFNULL(NULLIF(source,''),'Unknown') AS s,
    COUNT(*) AS c,
    SUM(CASE WHEN custom_appointment_status='Visited Booked' THEN 1 ELSE 0 END) AS bk
    FROM `tabLead`
    WHERE custom_posting_date BETWEEN %(f)s AND %(t)s
      AND (branch=%(b)s OR lead_assign_to_branch=%(b)s)
    GROUP BY IFNULL(NULLIF(source,''),'Unknown') ORDER BY c DESC LIMIT 25""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # v16: walk-ins now follow the selected window instead of being pinned to
    # today, so past dates can actually be reviewed. Includes the date so the
    # UI can group/label rows.
    # The updater columns only exist after console_create_lead_fields.py has
    # been run. Select them conditionally so this script keeps working either
    # way instead of dying on an unknown column.
    has_upd = frappe.db.exists("Custom Field",
        {"dt": "Lead", "fieldname": "custom_status_updated_by_name"})

    if has_upd:
        UPD_COLS = """, IFNULL(custom_status_updated_by_name,'') AS upd_by,
        custom_status_updated_on AS upd_on """
    else:
        UPD_COLS = """, '' AS upd_by, NULL AS upd_on """

    walkins = _read_sql("""SELECT name AS id, lead_name AS n, lead_owner AS by_,
    DATE(custom_appointment_date_and_time) AS d,
    TIME_FORMAT(custom_appointment_date_and_time,'%%H:%%i') AS t,
    IFNULL(NULLIF(custom_appointment_status,''),'Not Booked') AS st,
    IFNULL(custom_remarks,'') AS rm""" + UPD_COLS + """
    FROM `tabLead`
    WHERE (branch=%(b)s OR lead_assign_to_branch=%(b)s)
      AND DATE(custom_appointment_date_and_time) BETWEEN %(f)s AND %(t)s
    ORDER BY custom_appointment_date_and_time DESC LIMIT 200""",
        {"b": branch, "f": win_from, "t": win_to}, as_dict=True)

    # Active employees of this branch - populates the mandatory "updated by"
    # dropdown on the walk-in status modal.
    emp_list = _read_sql("""SELECT name AS id, employee_name AS n,
        IFNULL(designation,'') AS dg
    FROM `tabEmployee`
    WHERE status='Active' AND branch=%(b)s
    ORDER BY employee_name""",
        {"b": branch}, as_dict=True)

    # ============================================================
    # ATTENDANCE / STOCK / GRIEVANCE / WORKLIST
    # ============================================================
    att = _read_sql("""SELECT e.employee_name AS n, e.designation AS dg,
    IFNULL(a.status,'Absent') AS st,
    TIME_FORMAT(a.custom_check_in_time,'%%H:%%i') AS pin,
    TIME_FORMAT(a.custom_check_out_time,'%%H:%%i') AS pout
    FROM `tabEmployee` e
    LEFT JOIN `tabAttendance` a ON a.employee=e.name AND a.attendance_date=%(t)s AND a.docstatus < 2
    WHERE e.status='Active' AND e.branch=%(b)s
    ORDER BY e.employee_name LIMIT 25""",
        {"b": branch, "t": today}, as_dict=True)

    wpat = "%" + branch.replace(" ", "") + "%"
    stock = _read_sql("""SELECT SUM(CASE WHEN b.actual_qty <= 0 THEN 1 ELSE 0 END) AS zero,
    COUNT(*) AS items, IFNULL(SUM(b.stock_value),0) AS val
    FROM `tabBin` b JOIN `tabItem` i ON i.name = b.item_code
    WHERE REPLACE(b.warehouse,' ','') LIKE %(w)s AND i.is_stock_item = 1""",
        {"w": wpat}, as_dict=True)[0]

    stock_zero_items = _read_sql("""SELECT i.item_name AS n, b.item_code AS code
    FROM `tabBin` b JOIN `tabItem` i ON i.name = b.item_code
    WHERE REPLACE(b.warehouse,' ','') LIKE %(w)s AND i.is_stock_item = 1
      AND b.actual_qty <= 0
    ORDER BY i.item_name LIMIT 300""",
        {"w": wpat}, as_dict=True)

    grv = _read_sql("""SELECT IFNULL(SUM(status='Open'),0) AS open_,
    IFNULL(SUM(status='Escalated'),0) AS esc,
    IFNULL(SUM(priority='Red' AND status!='Closed'),0) AS red,
    IFNULL(SUM(status='Closed'),0) AS closed
    FROM `tabGrievance Ticket` WHERE branch=%(b)s""",
        {"b": branch}, as_dict=True)[0]

    work = _read_sql("""SELECT COUNT(*) AS open_,
    SUM(CASE WHEN date < %(t)s THEN 1 ELSE 0 END) AS over_,
    SUM(CASE WHEN priority='High' THEN 1 ELSE 0 END) AS hi,
    SUM(CASE WHEN date = %(t)s THEN 1 ELSE 0 END) AS due
    FROM `tabToDo` WHERE status='Open' AND allocated_to=%(u)s""",
        {"t": today, "u": frappe.session.user}, as_dict=True)[0]

    # ============================================================
    # RESPONSE - full payload always. "range" emitted when active
    # so the existing JS range branch continues to work.
    # ============================================================
    payload = {
        "branch": branch,
        "window": [win_from, win_to],
        "has_range": has_range,
        "cycle": [win_from, win_to],
        "target": round(target, 2),
        "target_rows": len(tgt_rows),
        "target_window": [t_from, t_to],
        "achieved": round(tot_final, 2),
        "achieved_gross": round(tot_gross, 2),
        "achieved_gst": round(tot_gst, 2),
        "achieved_exgst": round(tot_exgst, 2),
        "achieved_cut": round(tot_cut, 2),
        "days": days,
        "pm": pm,
        "paid_today_gross": round(paid_today_gross, 2),
        "paid_today_exgst": round(paid_today_exgst, 2),
        "paid_today_gst": round(paid_today_gst, 2),
        "paid_mtd_gross": round(tot_gross, 2),
        "paid_mtd_exgst": round(tot_exgst, 2),
        "paid_mtd_gst": round(tot_gst, 2),
        "pm_today": today_rows,
        "pm_today_detail": pm_today_detail,
        "pm_window_detail": pm_detail,
        "emps": counselor_emps,
        "pend": pend,
        "pend_total": pend_tot,
        "media": media_out,
        "ap_today": ap_today,
        "ap_cycle": ap_cycle,
        "ap_branch_summary": ap_branch_summary,
        "ap_rows": ap_rows,
        "leads": leads,
        "lead_src": lead_src,
        "walkins": walkins,
        "att": att,
        "stock": stock,
        "stock_zero_items": stock_zero_items,
        "grv": grv,
        "work": work,
        "daily": daily_tracker,
        "emp_list": emp_list,
    }

    if has_range:
        payload["range"] = {
            "from": win_from,
            "to": win_to,
            "target": round(target, 2),
            "target_rows": len(tgt_rows),
            "achieved_gross": round(tot_gross, 2),
            "achieved_gst": round(tot_gst, 2),
            "achieved_ex_gst": round(tot_exgst, 2),
            "achieved_cut": round(tot_cut, 2),
            "achieved_final": round(tot_final, 2),
            "modes": modes,
            "emps": counselor_emps,
        }

    frappe.response["message"] = payload
