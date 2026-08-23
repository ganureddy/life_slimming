# import os
# import json
# import requests
# import frappe
# from frappe.utils import (
#     nowdate, add_days, getdate, get_url, flt, cint,
#     get_files_path, now_datetime
# )
# from frappe.utils.pdf import get_pdf


# # =========================================================================
# # CONFIGURATION
# # =========================================================================

# WATI_BASE_URL = "https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage"
# WATI_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"

# WATI_CHANNEL_NUMBER = "918143156363"
# WATI_TEMPLATE_NAME = "life_sales_and_appointments"
# WATI_BROADCAST_NAME = "life_sales_and_appointments"

# # Hard-coded recipients (91 country code prefixed)
# RECIPIENT_NUMBERS = [
#     "919014416162",
#     "919604238978",
# ]

# # Ordered branches with display codes (must match the templates)
# BRANCHES = [
#     ("Chandanagar",  "CN"),
#     ("SR Nagar",     "SN"),
#     ("Banjara Hills","BH"),
#     ("Kukatpally",   "KP"),
#     ("Gachibowli",   "GB"),
#     ("Himayathnagar","HN"),
#     ("Dilsukhnagar", "DN"),
#     ("Vijayawada",   "VW"),
#     ("Vizag",        "VZ"),
#     ("Nellore",      "NLR"),
#     ("Madhapur",     "MP"),
# ]


# # =========================================================================
# # DATA FETCHERS
# # =========================================================================

# def _money(v):
#     """Indian-style grouping with 2 decimals."""
#     try:
#         n = float(v or 0)
#     except Exception:
#         n = 0.0
#     # Indian numbering: 1,23,45,678.90
#     s = f"{n:,.2f}"
#     # convert western 1,234,567.89 -> Indian 12,34,567.89
#     if "." in s:
#         int_part, dec_part = s.split(".")
#     else:
#         int_part, dec_part = s, "00"
#     int_part = int_part.replace(",", "")
#     neg = int_part.startswith("-")
#     if neg:
#         int_part = int_part[1:]
#     if len(int_part) > 3:
#         last3 = int_part[-3:]
#         rest = int_part[:-3]
#         rest_grouped = ",".join(
#             [rest[max(0, i-2):i] for i in range(len(rest), 0, -2)][::-1]
#         )
#         int_part = f"{rest_grouped},{last3}"
#     return ("-" if neg else "") + f"{int_part}.{dec_part}"


# def get_report_date(mode="evening"):
#     """
#     Determine the report date based on run mode.

#     mode = 'evening' (8:30 PM run) -> report covers TODAY (same-day data,
#         partial day up to run time). Returns today's date.
#     mode = 'morning' (10:00 AM run) -> report covers YESTERDAY full day
#         (00:00 -> 23:59). Returns yesterday's date.
#     """
#     if mode == "morning":
#         return add_days(nowdate(), -1)
#     return nowdate()


# def get_active_target_period():
#     """
#     Return (from_date, to_date, target_doc_name, targets_dict) for the
#     Monthly Target vs Archive record whose date range covers TODAY
#     (script runs at 8:30 PM, so 'today' is the run day).

#     Fiscal month convention: 6th of month -> 5th of next month.

#     Fallback chain:
#       1. Latest submitted record where today BETWEEN from_date AND to_date.
#       2. Latest submitted record by modified desc.
#       3. Compute fiscal window from today + return empty targets.

#     Returns:
#         (from_date, to_date, doc_name or None, {branch: target_amount})
#     """
#     today = nowdate()
#     targets = {b[0]: 0.0 for b in BRANCHES}

#     parent = frappe.db.sql(
#         """
#         SELECT name, from_date, to_date
#         FROM `tabMonthly Target vs Archive`
#         WHERE docstatus = 1
#           AND from_date IS NOT NULL AND to_date IS NOT NULL
#           AND %s BETWEEN from_date AND to_date
#         ORDER BY modified DESC LIMIT 1
#         """,
#         (today,), as_dict=True
#     )
#     if not parent:
#         parent = frappe.db.sql(
#             """
#             SELECT name, from_date, to_date
#             FROM `tabMonthly Target vs Archive`
#             WHERE docstatus = 1
#             ORDER BY modified DESC LIMIT 1
#             """, as_dict=True
#         )

#     if parent:
#         doc_name = parent[0].name
#         from_date = parent[0].from_date
#         to_date = parent[0].to_date
#         rows = frappe.db.sql(
#             """
#             SELECT branch, targeted_amount
#             FROM `tabMonthly Target and Archive Data`
#             WHERE parent = %s AND parenttype = 'Monthly Target vs Archive'
#             """,
#             (doc_name,), as_dict=True
#         )
#         for r in rows:
#             if r.branch and r.branch in targets:
#                 targets[r.branch] = flt(r.targeted_amount)

#         # Safety net: if record exists but dates are NULL, compute fiscal window
#         if not from_date or not to_date:
#             from_date, to_date = compute_fiscal_window(today)
#         return from_date, to_date, doc_name, targets

#     # No record at all -> derive fiscal window so MTD still works
#     from_date, to_date = compute_fiscal_window(today)
#     return from_date, to_date, None, targets


# def compute_fiscal_window(ref_date):
#     """
#     Fiscal month: 6th of M -> 5th of M+1.
#     If ref_date.day >= 6 -> window = [ref_date.year-month-06, next_month-05]
#     If ref_date.day <  6 -> window = [prev_month-06, ref_date.year-month-05]
#     """
#     import calendar
#     d = getdate(ref_date)
#     if d.day >= 6:
#         from_d = d.replace(day=6)
#         # next month's 5th
#         if d.month == 12:
#             to_d = d.replace(year=d.year + 1, month=1, day=5)
#         else:
#             to_d = d.replace(month=d.month + 1, day=5)
#     else:
#         # previous month's 6th
#         if d.month == 1:
#             from_d = d.replace(year=d.year - 1, month=12, day=6)
#         else:
#             from_d = d.replace(month=d.month - 1, day=6)
#         to_d = d.replace(day=5)
#     return from_d, to_d


# def fetch_sales_data(report_date, period_start):
#     """
#     Per-branch sales for the report_date (today's = yesterday's closing)
#     and CYCLE sales from fiscal period_start (6th of month) through report_date.
#     Uses submitted Sales Invoices only (docstatus = 1) and excludes return invoices.
#     """
#     result = {b[0]: {"today_sales": 0.0, "today_invoices": 0, "mtd_sales": 0.0}
#               for b in BRANCHES}

#     # Today's (yesterday's) sales + invoice count
#     rows = frappe.db.sql(
#         """
#         SELECT branch,
#                COUNT(*) AS invoices,
#                SUM(grand_total) AS total
#         FROM `tabSales Invoice`
#         WHERE docstatus = 1
#           AND IFNULL(is_return, 0) = 0
#           AND posting_date = %s
#         GROUP BY branch
#         """,
#         (report_date,), as_dict=True
#     )
#     for r in rows:
#         if r.branch in result:
#             result[r.branch]["today_sales"] = flt(r.total)
#             result[r.branch]["today_invoices"] = cint(r.invoices)

#     # Cycle sales (6th of month -> report_date, inclusive)
#     rows = frappe.db.sql(
#         """
#         SELECT branch, SUM(grand_total) AS total
#         FROM `tabSales Invoice`
#         WHERE docstatus = 1
#           AND IFNULL(is_return, 0) = 0
#           AND posting_date BETWEEN %s AND %s
#         GROUP BY branch
#         """,
#         (period_start, report_date), as_dict=True
#     )
#     for r in rows:
#         if r.branch in result:
#             result[r.branch]["mtd_sales"] = flt(r.total)

#     return result


# def fetch_appointment_data(report_date):
#     """
#     Per-branch appointment counters for `report_date`:
#       service_booked, executed, postponed, cancelled,
#       consultation_booked, unbooked.

#     Heuristic mapping (data has only Open/Closed/blank statuses):
#       - Service vs Consultation: appointment_type = 'Session' => Service,
#         anything else => Consultation.
#       - Executed = status = 'Closed'
#       - Postponed = status LIKE 'Postpon%'
#       - Cancelled = status LIKE 'Cancel%'
#       - Service Booked = total Service appointments for date
#       - Consultation Booked = total Consultation appointments for date
#       - Unbooked / Not Converted = appointments with no service_unit AND
#         no procedure_template AND no therapy_plan (i.e. consultation without
#         a converted service plan).
#     """
#     result = {b[0]: {
#         "service_booked": 0, "executed": 0, "postponed": 0,
#         "cancelled": 0, "consultation_booked": 0, "unbooked": 0
#     } for b in BRANCHES}

#     rows = frappe.db.sql(
#         """
#         SELECT branch,
#                appointment_type,
#                LOWER(IFNULL(status, '')) AS status,
#                IFNULL(service_unit, '')        AS service_unit,
#                IFNULL(procedure_template, '')  AS procedure_template,
#                IFNULL(therapy_plan, '')        AS therapy_plan
#         FROM `tabPatient Appointment`
#         WHERE appointment_date = %s
#           AND IFNULL(branch, '') != ''
#         """,
#         (report_date,), as_dict=True
#     )

#     for r in rows:
#         if r.branch not in result:
#             continue
#         b = result[r.branch]
#         is_service = (r.appointment_type == "Session")

#         if is_service:
#             b["service_booked"] += 1
#         else:
#             b["consultation_booked"] += 1

#         status = (r.status or "").strip().lower()
#         if status == "closed":
#             b["executed"] += 1
#         elif status.startswith("postpon"):
#             b["postponed"] += 1
#         elif status.startswith("cancel"):
#             b["cancelled"] += 1

#         # Unbooked / not converted: consultation with no plan attached
#         if not is_service and not (r.service_unit or r.procedure_template or r.therapy_plan):
#             b["unbooked"] += 1

#     return result


# # =========================================================================
# # PDF GENERATION
# # =========================================================================

# def build_pdf_html(report_date, targets, sales, appts, summary):
#     rows_sales = []
#     rows_appts = []

#     for branch_name, code in BRANCHES:
#         s = sales[branch_name]
#         t = targets.get(branch_name, 0.0)
#         achieved_pct = (s["mtd_sales"] / t * 100.0) if t > 0 else 0.0
#         pending = max(t - s["mtd_sales"], 0.0)

#         rows_sales.append(f"""
#             <tr>
#                 <td>{branch_name} <span class="code">| {code}</span></td>
#                 <td class="num">Rs. {_money(s['today_sales'])}</td>
#                 <td class="num">{s['today_invoices']}</td>
#                 <td class="num">Rs. {_money(s['mtd_sales'])}</td>
#                 <td class="num">Rs. {_money(t)}</td>
#                 <td class="num">{achieved_pct:.1f}%</td>
#                 <td class="num">Rs. {_money(pending)}</td>
#             </tr>
#         """)

#         a = appts[branch_name]
#         rows_appts.append(f"""
#             <tr>
#                 <td>{branch_name} <span class="code">| {code}</span></td>
#                 <td class="num">{a['service_booked']}</td>
#                 <td class="num">{a['executed']}</td>
#                 <td class="num">{a['postponed']}</td>
#                 <td class="num">{a['cancelled']}</td>
#                 <td class="num">{a['consultation_booked']}</td>
#                 <td class="num">{a['unbooked']}</td>
#             </tr>
#         """)

#     coverage_label = (
#         "Yesterday full day (00:00 - 23:59) - Closing Report"
#         if summary.get("mode") == "morning"
#         else f"Today live data till {now_datetime().strftime('%I:%M %p')}"
#     )
#     report_title_suffix = (
#         "Yesterday Closing Report"
#         if summary.get("mode") == "morning"
#         else "Live Same-Day Update"
#     )

#     html = f"""
#     <html>
#     <head>
#     <style>
#         @page {{ size: A4 landscape; margin: 12mm; }}
#         body {{ font-family: Helvetica, Arial, sans-serif; color: #222; font-size: 10pt; }}
#         h1 {{ color: #1f4e79; margin: 0 0 4px 0; font-size: 18pt; }}
#         h2 {{ color: #2e75b6; margin: 18px 0 8px 0; font-size: 13pt;
#               border-bottom: 2px solid #2e75b6; padding-bottom: 3px; }}
#         .meta {{ color: #555; font-size: 9pt; margin-bottom: 10px; }}
#         .summary {{ background: #f2f7fb; border-left: 4px solid #2e75b6;
#                     padding: 8px 12px; margin: 8px 0 14px 0; font-size: 10pt; }}
#         .summary b {{ color: #1f4e79; }}
#         table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
#         th, td {{ border: 1px solid #cfd8dc; padding: 5px 7px; text-align: left;
#                   font-size: 9pt; }}
#         th {{ background: #1f4e79; color: #fff; font-weight: 600; }}
#         tr:nth-child(even) td {{ background: #fafafa; }}
#         td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
#         .code {{ color: #777; font-size: 8pt; }}
#         .footer {{ margin-top: 20px; font-size: 8pt; color: #888;
#                    border-top: 1px solid #ddd; padding-top: 6px; }}
#         .totals td {{ background: #e8f1f9 !important; font-weight: 700; }}
#     </style>
#     </head>
#     <body>
#         <h1>LIFE Daily Sales &amp; Appointments Report</h1>
#         <div class="meta">
#             <b>{report_title_suffix}</b>
#             &nbsp;|&nbsp; Report Date: <b>{getdate(report_date).strftime('%d-%b-%Y')}</b>
#             &nbsp;|&nbsp; Generated: {now_datetime().strftime('%d-%b-%Y %I:%M %p')}
#             &nbsp;|&nbsp; Coverage: {coverage_label}
#             <br/>
#             Sales Cycle: <b>{getdate(summary['period_from']).strftime('%d-%b-%Y')}</b>
#             &nbsp;&rarr;&nbsp;
#             <b>{getdate(summary['period_to']).strftime('%d-%b-%Y')}</b>
#             &nbsp;(6th &rarr; 5th window)
#             {f"&nbsp;|&nbsp; Target Doc: <code>{summary['target_doc']}</code>" if summary.get('target_doc') else ""}
#         </div>

#         <div class="summary">
#             <b>Overall Summary:</b><br/>
#             Total Sales (Day): <b>Rs. {_money(summary['total_today_sales'])}</b> &nbsp;|&nbsp;
#             Total Invoices: <b>{summary['total_invoices']}</b> &nbsp;|&nbsp;
#             Cycle Total: <b>Rs. {_money(summary['total_mtd_sales'])}</b><br/>
#             Overall Target Achievement: <b>{summary['overall_pct']:.1f}%</b> &nbsp;|&nbsp;
#             Top Branch: <b>{summary['top_branch']}</b> &nbsp;|&nbsp;
#             Lowest Branch: <b>{summary['lowest_branch']}</b><br/>
#             Total Service Appointments: <b>{summary['total_service_booked']}</b>
#             (Executed: {summary['total_executed']},
#              Postponed: {summary['total_postponed']},
#              Cancelled: {summary['total_cancelled']})
#             &nbsp;|&nbsp; Total Consultations: <b>{summary['total_consultation_booked']}</b>
#             (Unbooked: {summary['total_unbooked']})
#         </div>

#         <h2>Branch-wise Sales Performance</h2>
#         <table>
#             <thead>
#                 <tr>
#                     <th>Branch</th>
#                     <th>Today Sales</th>
#                     <th>Today Invoices</th>
#                     <th>Cycle Sales</th>
#                     <th>Target</th>
#                     <th>Achieved %</th>
#                     <th>Pending to Target</th>
#                 </tr>
#             </thead>
#             <tbody>
#                 {''.join(rows_sales)}
#                 <tr class="totals">
#                     <td>TOTAL</td>
#                     <td class="num">Rs. {_money(summary['total_today_sales'])}</td>
#                     <td class="num">{summary['total_invoices']}</td>
#                     <td class="num">Rs. {_money(summary['total_mtd_sales'])}</td>
#                     <td class="num">Rs. {_money(summary['total_target'])}</td>
#                     <td class="num">{summary['overall_pct']:.1f}%</td>
#                     <td class="num">Rs. {_money(max(summary['total_target'] - summary['total_mtd_sales'], 0))}</td>
#                 </tr>
#             </tbody>
#         </table>

#         <h2>Branch-wise Appointments &amp; Consultations</h2>
#         <table>
#             <thead>
#                 <tr>
#                     <th>Branch</th>
#                     <th>Service Booked</th>
#                     <th>Executed</th>
#                     <th>Postponed</th>
#                     <th>Cancelled</th>
#                     <th>Consultation Booked</th>
#                     <th>Unbooked / Not Converted</th>
#                 </tr>
#             </thead>
#             <tbody>
#                 {''.join(rows_appts)}
#                 <tr class="totals">
#                     <td>TOTAL</td>
#                     <td class="num">{summary['total_service_booked']}</td>
#                     <td class="num">{summary['total_executed']}</td>
#                     <td class="num">{summary['total_postponed']}</td>
#                     <td class="num">{summary['total_cancelled']}</td>
#                     <td class="num">{summary['total_consultation_booked']}</td>
#                     <td class="num">{summary['total_unbooked']}</td>
#                 </tr>
#             </tbody>
#         </table>

#         <div class="footer">
#             Auto-generated by LIFE ERP &middot; This report is system-generated and
#             requires no signature. For queries contact the Accounts team.
#         </div>
#     </body>
#     </html>
#     """
#     return html


# def save_pdf_as_public_file(pdf_bytes, report_date, mode="evening"):
#     """
#     Save PDF to /files/ (public) and return the full absolute URL.
#     Also creates a File doctype record so it appears in File Manager.
#     """
#     suffix = "Morning_Closing" if mode == "morning" else "Evening_Live"
#     filename = (
#         f"LIFE_Daily_Report_{suffix}_"
#         f"{getdate(report_date).strftime('%Y-%m-%d')}.pdf"
#     )

#     file_doc = frappe.get_doc({
#         "doctype": "File",
#         "file_name": filename,
#         "is_private": 0,
#         "content": pdf_bytes,
#         "decode": False,
#     })
#     file_doc.save(ignore_permissions=True)
#     frappe.db.commit()

#     # file_url comes back as "/files/<name>.pdf" - prefix with site URL
#     return get_url(file_doc.file_url)


# # =========================================================================
# # WHATSAPP DISPATCH
# # =========================================================================

# def send_consolidated_whatsapp(report_date, summary, pdf_url):
#     """
#     Sends ONE WhatsApp via WATI using the `life_sales_and_appointments` template
#     to EACH number in RECIPIENT_NUMBERS.

#     Template body parameters (in order):
#       {{1}} Date
#       {{2}} Total Sales (Rs.)
#       {{3}} Total Invoices
#       {{4}} Overall Target Achievement %
#       {{5}} Top Branch
#       {{6}} Lowest Branch
#       {{7}} Source (PDF URL)
#     """
#     date_str = getdate(report_date).strftime("%d-%m-%Y")

#     payload = {
#         "template_name": WATI_TEMPLATE_NAME,
#         "broadcast_name": WATI_BROADCAST_NAME,
#         "parameters": [
#             {"name": "1", "value": date_str},
#             {"name": "2", "value": _money(summary["total_today_sales"])},
#             {"name": "3", "value": str(summary["total_invoices"])},
#             {"name": "4", "value": f"{summary['overall_pct']:.1f}"},
#             {"name": "5", "value": summary["top_branch"] or "N/A"},
#             {"name": "6", "value": summary["lowest_branch"] or "N/A"},
#             {"name": "7", "value": pdf_url or ""},
#             # WATI requires the parameter name as listed in the template -
#             # if your template uses {{Source}} by name instead of {{7}},
#             # ALSO include this alias (WATI accepts both numeric and named):
#             {"name": "Source", "value": pdf_url or ""},
#         ],
#         "channel_number": WATI_CHANNEL_NUMBER,
#     }

#     headers = {
#         "Authorization": f"Bearer {WATI_TOKEN}",
#         "Content-Type": "application/json",
#     }

#     results = {}
#     all_ok = True

#     for number in RECIPIENT_NUMBERS:
#         url = f"{WATI_BASE_URL}?whatsappNumber={number}"
#         try:
#             response = requests.post(url, json=payload, headers=headers, timeout=30)
#             ok = (response.status_code == 200)
#             results[number] = {
#                 "status_code": response.status_code,
#                 "ok": ok,
#                 "response": response.text[:300],
#             }

#             frappe.logger().info({
#                 "event": "Daily Sales+Appointments WhatsApp",
#                 "status_code": response.status_code,
#                 "response": response.text[:500],
#                 "sent_to": number,
#                 "pdf_url": pdf_url,
#                 "report_date": str(report_date),
#             })

#             if not ok:
#                 all_ok = False
#                 frappe.log_error(
#                     f"WATI Error {response.status_code} for {number}: {response.text}",
#                     "Daily Report WhatsApp Failed",
#                 )
#         except Exception as e:
#             all_ok = False
#             results[number] = {"ok": False, "error": str(e)}
#             frappe.log_error(
#                 f"WATI Exception for {number}: {frappe.get_traceback()}",
#                 "Daily Report WhatsApp Exception",
#             )

#     return {"ok": all_ok, "results": results}


# # =========================================================================
# # MAIN ENTRY POINT (scheduler hook)
# # =========================================================================

# def run_daily_report(mode="evening"):
#     """
#     Main scheduler entry point.

#     mode = 'evening' -> same-day data, run at 8:30 PM
#     mode = 'morning' -> yesterday closing data, run at 10:00 AM
#     """
#     try:
#         report_date = get_report_date(mode)

#         # 1. Resolve fiscal period + targets from Monthly Target vs Archive
#         period_from, period_to, target_doc, targets = get_active_target_period()

#         # Clamp the period_to to report_date so MTD never includes future dates
#         # within the same cycle. Sales window = [period_from, min(report_date, period_to)]
#         cycle_end = report_date if getdate(report_date) <= getdate(period_to) else period_to

#         # 2. Fetch sales + appointment data
#         sales = fetch_sales_data(report_date, period_from)
#         appts = fetch_appointment_data(report_date)

#         # 2. Build summary (for WhatsApp body + PDF header)
#         total_today_sales = sum(sales[b[0]]["today_sales"] for b in BRANCHES)
#         total_invoices = sum(sales[b[0]]["today_invoices"] for b in BRANCHES)
#         total_mtd_sales = sum(sales[b[0]]["mtd_sales"] for b in BRANCHES)
#         total_target = sum(targets.values())
#         overall_pct = (total_mtd_sales / total_target * 100.0) if total_target > 0 else 0.0

#         # Top/lowest branch by today's sales (ignore zero-sales for "top" tiebreaks)
#         per_branch_today = [(b[0], sales[b[0]]["today_sales"]) for b in BRANCHES]
#         per_branch_today_sorted = sorted(per_branch_today, key=lambda x: x[1], reverse=True)
#         top_branch = per_branch_today_sorted[0][0] if per_branch_today_sorted else "N/A"
#         lowest_branch = per_branch_today_sorted[-1][0] if per_branch_today_sorted else "N/A"

#         summary = {
#             "mode": mode,
#             "period_from": period_from,
#             "period_to": period_to,
#             "target_doc": target_doc,
#             "total_today_sales": total_today_sales,
#             "total_invoices": total_invoices,
#             "total_mtd_sales": total_mtd_sales,
#             "total_target": total_target,
#             "overall_pct": overall_pct,
#             "top_branch": top_branch,
#             "lowest_branch": lowest_branch,
#             "total_service_booked": sum(appts[b[0]]["service_booked"] for b in BRANCHES),
#             "total_executed": sum(appts[b[0]]["executed"] for b in BRANCHES),
#             "total_postponed": sum(appts[b[0]]["postponed"] for b in BRANCHES),
#             "total_cancelled": sum(appts[b[0]]["cancelled"] for b in BRANCHES),
#             "total_consultation_booked": sum(appts[b[0]]["consultation_booked"] for b in BRANCHES),
#             "total_unbooked": sum(appts[b[0]]["unbooked"] for b in BRANCHES),
#         }

#         # 3. Build PDF
#         html = build_pdf_html(report_date, targets, sales, appts, summary)
#         pdf_bytes = get_pdf(html)

#         # 4. Save PDF as public File and get URL
#         pdf_url = save_pdf_as_public_file(pdf_bytes, report_date, mode=mode)

#         # 5. Send WhatsApp (to all recipients)
#         send_result = send_consolidated_whatsapp(report_date, summary, pdf_url)

#         frappe.logger().info(
#             f"[Daily Report] date={report_date} pdf={pdf_url} "
#             f"sent_ok={send_result['ok']} results={send_result['results']}"
#         )
#         return {
#             "ok": send_result["ok"],
#             "pdf_url": pdf_url,
#             "summary": summary,
#             "whatsapp": send_result["results"],
#         }

#     except Exception:
#         frappe.log_error(frappe.get_traceback(), "Daily Sales+Appointments Report Failed")
#         raise


# # =========================================================================
# # SCHEDULER WRAPPERS (register these in hooks.py)
# # =========================================================================

# def run_morning_report():
#     """
#     10:00 AM run - Yesterday Closing Report (full day 00:00 - 23:59).
#     Register in hooks.py:
#         "0 10 * * *": ["life_slimming.daily_sales_appointments_report.run_morning_report"]
#     """
#     return run_daily_report(mode="morning")


# def run_evening_report():
#     """
#     8:30 PM run - Same-day live update (partial day up to run time).
#     Register in hooks.py:
#         "30 20 * * *": ["life_slimming.daily_sales_appointments_report.run_evening_report"]
#     """
#     return run_daily_report(mode="evening")


# # =========================================================================
# # MANUAL TEST HOOKS (call via bench execute)
# # =========================================================================

# @frappe.whitelist()
# def trigger_now(mode="evening"):
#     """Manual trigger:
#         bench --site <site> execute life_slimming.daily_sales_appointments_report.trigger_now
#         bench --site <site> execute life_slimming.daily_sales_appointments_report.trigger_now \\
#               --kwargs '{"mode": "morning"}'
#     """
#     return run_daily_report(mode=mode)


# @frappe.whitelist()
# def trigger_morning():
#     """Manual morning trigger."""
#     return run_morning_report()


# @frappe.whitelist()
# def trigger_evening():
#     """Manual evening trigger."""
#     return run_evening_report()



# RECIPIENT_NUMBERS = [
#     "919014416162",
#     "919604238978",
#     "917416026677",
#     "919553722285",
#     "919705170170",
#     "919502025252",
#     "918099931463"

# ]

"""
Daily Sales + Appointments Consolidated Report
==============================================
Two scheduled runs:
  - 10:00 AM (morning): Yesterday Closing Report - full day 00:00 -> 23:59 of YESTERDAY.
  - 8:30  PM (evening): Same-day Live Update    - TODAY's data so far (partial day).

Both runs:
  - Generate a single branch-wise PDF with sales + appointments insights.
  - Upload PDF as a public File in /files/.
  - Send ONE consolidated WhatsApp via WATI template
    `life_sales_and_client_appointment_details` (Utility category)
    to all RECIPIENT_NUMBERS, embedding the PDF URL in {{Source}} ({{7}}).

hooks.py registration:
----------------------
scheduler_events = {
    "cron": {
        # Morning closing report (yesterday's full data)
        "0 10 * * *": [
            "life_slimming.daily_sales_appointments_report.run_morning_report"
        ],
        # Evening live update (today's data so far)
        "30 20 * * *": [
            "life_slimming.daily_sales_appointments_report.run_evening_report"
        ],
    }
}
"""

import os
import json
import requests
import frappe
from frappe.utils import (
    nowdate, add_days, getdate, get_url, flt, cint,
    get_files_path, now_datetime
)
from frappe.utils.pdf import get_pdf


# =========================================================================
# CONFIGURATION
# =========================================================================

WATI_BASE_URL = "https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage"
WATI_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0."
    "yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"
)
WATI_CHANNEL_NUMBER = "918143156363"
WATI_TEMPLATE_NAME = "life_sales_and_client_appointment_details"
WATI_BROADCAST_NAME = "life_sales_and_client_appointment_details"

# GST rate to strip from gross collections to show "Without GST" columns.
# 5% GST -> divisor = 1.05 -> without_gst = amount / 1.05
GST_RATE = 0.05
GST_DIVISOR = 1.0 + GST_RATE

# Set False to test the pipeline (PDF + logs) WITHOUT sending WhatsApp.
# Useful during Meta quality-rating cooldowns or template re-approval.
WHATSAPP_ENABLED = True

# Hard-coded recipients (91 country code prefixed)
RECIPIENT_NUMBERS = [
    "919014416162",
    "919604238978",
    "917416026677",
    "919553722285",
    "919705170170",
    "919502025252",
    "918099931463",
    "919666158152"
]
BRANCHES = [
    ("Chandanagar",  "CN"),
    ("SR Nagar",     "SN"),
    ("Banjara Hills","BH"),
    ("Kukatpally",   "KP"),
    ("Gachibowli",   "GB"),
    ("Himayathnagar","HN"),
    ("Dilsukhnagar", "DN"),
    ("Vijayawada",   "VW"),
    ("Vizag",        "VZ"),
    ("Nellore",      "NLR"),
    ("Madhapur",     "MP"),
]

# Quick lookup: branch full name -> short code (e.g. "Chandanagar" -> "CN")
BRANCH_CODE = {name: code for name, code in BRANCHES}


# =========================================================================
# DATA FETCHERS
# =========================================================================

def _money(v):
    """Indian-style grouping with 2 decimals."""
    try:
        n = float(v or 0)
    except Exception:
        n = 0.0
    # Indian numbering: 1,23,45,678.90
    s = f"{n:,.2f}"
    # convert western 1,234,567.89 -> Indian 12,34,567.89
    if "." in s:
        int_part, dec_part = s.split(".")
    else:
        int_part, dec_part = s, "00"
    int_part = int_part.replace(",", "")
    neg = int_part.startswith("-")
    if neg:
        int_part = int_part[1:]
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        rest_grouped = ",".join(
            [rest[max(0, i-2):i] for i in range(len(rest), 0, -2)][::-1]
        )
        int_part = f"{rest_grouped},{last3}"
    return ("-" if neg else "") + f"{int_part}.{dec_part}"


def get_report_date(mode="evening"):
    """
    Determine the report date based on run mode.

    mode = 'evening' (8:30 PM run) -> report covers TODAY (same-day data,
        partial day up to run time). Returns today's date.
    mode = 'morning' (10:00 AM run) -> report covers YESTERDAY full day
        (00:00 -> 23:59). Returns yesterday's date.
    """
    if mode == "morning":
        return add_days(nowdate(), -1)
    return nowdate()


def get_active_target_period():
    """
    Return (from_date, to_date, target_doc_name, targets_dict) for the
    Monthly Target vs Archive record whose date range covers TODAY
    (script runs at 8:30 PM, so 'today' is the run day).

    Fiscal month convention: 6th of month -> 5th of next month.

    Fallback chain:
      1. Latest submitted record where today BETWEEN from_date AND to_date.
      2. Latest submitted record by modified desc.
      3. Compute fiscal window from today + return empty targets.

    Returns:
        (from_date, to_date, doc_name or None, {branch: target_amount})
    """
    today = nowdate()
    targets = {b[0]: 0.0 for b in BRANCHES}

    parent = frappe.db.sql(
        """
        SELECT name, from_date, to_date
        FROM `tabMonthly Target vs Archive`
        WHERE docstatus = 1
          AND from_date IS NOT NULL AND to_date IS NOT NULL
          AND %s BETWEEN from_date AND to_date
        ORDER BY modified DESC LIMIT 1
        """,
        (today,), as_dict=True
    )
    if not parent:
        parent = frappe.db.sql(
            """
            SELECT name, from_date, to_date
            FROM `tabMonthly Target vs Archive`
            WHERE docstatus = 1
            ORDER BY modified DESC LIMIT 1
            """, as_dict=True
        )

    if parent:
        doc_name = parent[0].name
        from_date = parent[0].from_date
        to_date = parent[0].to_date
        rows = frappe.db.sql(
            """
            SELECT branch, targeted_amount
            FROM `tabMonthly Target and Archive Data`
            WHERE parent = %s AND parenttype = 'Monthly Target vs Archive'
            """,
            (doc_name,), as_dict=True
        )
        for r in rows:
            if r.branch and r.branch in targets:
                targets[r.branch] = flt(r.targeted_amount)

        # Safety net: if record exists but dates are NULL, compute fiscal window
        if not from_date or not to_date:
            from_date, to_date = compute_fiscal_window(today)
        return from_date, to_date, doc_name, targets

    # No record at all -> derive fiscal window so MTD still works
    from_date, to_date = compute_fiscal_window(today)
    return from_date, to_date, None, targets


def compute_fiscal_window(ref_date):
    """
    Fiscal month: 6th of M -> 5th of M+1.
    If ref_date.day >= 6 -> window = [ref_date.year-month-06, next_month-05]
    If ref_date.day <  6 -> window = [prev_month-06, ref_date.year-month-05]
    """
    import calendar
    d = getdate(ref_date)
    if d.day >= 6:
        from_d = d.replace(day=6)
        # next month's 5th
        if d.month == 12:
            to_d = d.replace(year=d.year + 1, month=1, day=5)
        else:
            to_d = d.replace(month=d.month + 1, day=5)
    else:
        # previous month's 6th
        if d.month == 1:
            from_d = d.replace(year=d.year - 1, month=12, day=6)
        else:
            from_d = d.replace(month=d.month - 1, day=6)
        to_d = d.replace(day=5)
    return from_d, to_d


def fetch_sales_data(report_date, period_start):
    """
    Per-branch sales for the report_date and CYCLE (period_start -> report_date).

    SALES AMOUNTS come from `Payment Entry.paid_amount`:
      - docstatus = 1 (submitted)
      - payment_type = 'Receive' (incoming receipts only - excludes Pay/Internal Transfer)
      - filtered by branch + posting_date
    This reflects actual money collected, not invoiced.

    INVOICE COUNT (today_invoices) still comes from Sales Invoice
    (submitted, non-return) because "invoices issued today" is a Sales Invoice concept.

    Without-GST = amount / 1.05 (GST 5%).
    """
    result = {b[0]: {
        "today_sales": 0.0,
        "today_sales_excl_gst": 0.0,
        "today_invoices": 0,
        "mtd_sales": 0.0,
        "mtd_sales_excl_gst": 0.0,
    } for b in BRANCHES}

    # ---- TODAY: collections via Payment Entry ----
    rows = frappe.db.sql(
        """
        SELECT branch, SUM(paid_amount) AS total
        FROM `tabPayment Entry`
        WHERE docstatus = 1
          AND payment_type = 'Receive'
          AND posting_date = %s
        GROUP BY branch
        """,
        (report_date,), as_dict=True
    )
    for r in rows:
        if r.branch in result:
            gross = flt(r.total)
            result[r.branch]["today_sales"] = gross
            result[r.branch]["today_sales_excl_gst"] = gross / GST_DIVISOR

    # ---- TODAY: invoice count via Sales Invoice ----
    rows = frappe.db.sql(
        """
        SELECT branch, COUNT(*) AS invoices
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND IFNULL(is_return, 0) = 0
          AND posting_date = %s
        GROUP BY branch
        """,
        (report_date,), as_dict=True
    )
    for r in rows:
        if r.branch in result:
            result[r.branch]["today_invoices"] = cint(r.invoices)

    # ---- CYCLE: collections via Payment Entry ----
    rows = frappe.db.sql(
        """
        SELECT branch, SUM(paid_amount) AS total
        FROM `tabPayment Entry`
        WHERE docstatus = 1
          AND payment_type = 'Receive'
          AND posting_date BETWEEN %s AND %s
        GROUP BY branch
        """,
        (period_start, report_date), as_dict=True
    )
    for r in rows:
        if r.branch in result:
            gross = flt(r.total)
            result[r.branch]["mtd_sales"] = gross
            result[r.branch]["mtd_sales_excl_gst"] = gross / GST_DIVISOR

    return result


def fetch_appointment_data(report_date):
    """
    Per-branch appointment counters for `report_date`:
      service_booked, executed, postponed, cancelled,
      consultation_booked, unbooked.

    Heuristic mapping (data has only Open/Closed/blank statuses):
      - Service vs Consultation: appointment_type = 'Session' => Service,
        anything else => Consultation.
      - Executed = status = 'Closed'
      - Postponed = status LIKE 'Postpon%'
      - Cancelled = status LIKE 'Cancel%'
      - Service Booked = total Service appointments for date
      - Consultation Booked = total Consultation appointments for date
      - Unbooked / Not Converted = appointments with no service_unit AND
        no procedure_template AND no therapy_plan (i.e. consultation without
        a converted service plan).
    """
    result = {b[0]: {
        "service_booked": 0, "executed": 0, "postponed": 0,
        "cancelled": 0, "consultation_booked": 0, "unbooked": 0
    } for b in BRANCHES}

    rows = frappe.db.sql(
        """
        SELECT branch,
               appointment_type,
               LOWER(IFNULL(status, '')) AS status,
               IFNULL(service_unit, '')        AS service_unit,
               IFNULL(procedure_template, '')  AS procedure_template,
               IFNULL(therapy_plan, '')        AS therapy_plan
        FROM `tabPatient Appointment`
        WHERE appointment_date = %s
          AND IFNULL(branch, '') != ''
        """,
        (report_date,), as_dict=True
    )

    for r in rows:
        if r.branch not in result:
            continue
        b = result[r.branch]
        is_service = (r.appointment_type == "Session")

        if is_service:
            b["service_booked"] += 1
        else:
            b["consultation_booked"] += 1

        status = (r.status or "").strip().lower()
        if status == "closed":
            b["executed"] += 1
        elif status.startswith("postpon"):
            b["postponed"] += 1
        elif status.startswith("cancel"):
            b["cancelled"] += 1

        # Unbooked / not converted: consultation with no plan attached
        if not is_service and not (r.service_unit or r.procedure_template or r.therapy_plan):
            b["unbooked"] += 1

    return result


# =========================================================================
# PDF GENERATION
# =========================================================================

def build_pdf_html(report_date, targets, sales, appts, summary):
    rows_sales = []
    rows_appts = []

    for branch_name, code in BRANCHES:
        s = sales[branch_name]
        t = targets.get(branch_name, 0.0)
        achieved_pct = (s["mtd_sales"] / t * 100.0) if t > 0 else 0.0
        pending = max(t - s["mtd_sales"], 0.0)

        rows_sales.append(f"""
            <tr>
                <td>{code}</td>
                <td class="num">Rs. {_money(s['today_sales'])}</td>
                <td class="num">Rs. {_money(s['today_sales_excl_gst'])}</td>
                <td class="num">{s['today_invoices']}</td>
                <td class="num">Rs. {_money(s['mtd_sales'])}</td>
                <td class="num">Rs. {_money(s['mtd_sales_excl_gst'])}</td>
                <td class="num">Rs. {_money(t)}</td>
                <td class="num">{achieved_pct:.1f}%</td>
                <td class="num">Rs. {_money(pending)}</td>
            </tr>
        """)

        a = appts[branch_name]
        rows_appts.append(f"""
            <tr>
                <td>{code}</td>
                <td class="num">{a['service_booked']}</td>
                <td class="num">{a['executed']}</td>
                <td class="num">{a['postponed']}</td>
                <td class="num">{a['cancelled']}</td>
                <td class="num">{a['consultation_booked']}</td>
                <td class="num">{a['unbooked']}</td>
            </tr>
        """)

    coverage_label = (
        "Yesterday full day (00:00 - 23:59) - Closing Report"
        if summary.get("mode") == "morning"
        else f"Today live data till {now_datetime().strftime('%I:%M %p')}"
    )
    report_title_suffix = (
        "Yesterday Closing Report"
        if summary.get("mode") == "morning"
        else "Live Same-Day Update"
    )

    html = f"""
    <html>
    <head>
    <style>
        @page {{ size: A4 landscape; margin: 10mm; }}
        body {{ font-family: Helvetica, Arial, sans-serif; color: #222; font-size: 10pt; }}
        h1 {{ color: #1f4e79; margin: 0 0 4px 0; font-size: 18pt; }}
        h2 {{ color: #2e75b6; margin: 14px 0 6px 0; font-size: 12pt;
              border-bottom: 2px solid #2e75b6; padding-bottom: 3px; }}
        .meta {{ color: #555; font-size: 9pt; margin-bottom: 8px; }}
        .summary {{ background: #f2f7fb; border-left: 4px solid #2e75b6;
                    padding: 7px 10px; margin: 6px 0 10px 0; font-size: 9.5pt; }}
        .summary b {{ color: #1f4e79; }}

        /* default tables (appointments) */
        table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
        th, td {{ border: 1px solid #cfd8dc; padding: 4px 6px; text-align: left;
                  font-size: 9pt; }}
        th {{ background: #1f4e79; color: #fff; font-weight: 600; }}
        tr:nth-child(even) td {{ background: #fafafa; }}
        td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
        .code {{ color: #777; font-size: 7.5pt; }}
        .footer {{ margin-top: 16px; font-size: 8pt; color: #888;
                   border-top: 1px solid #ddd; padding-top: 6px; }}
        .totals td {{ background: #e8f1f9 !important; font-weight: 700; }}

        /* sales table - 9 columns, must fit one line each */
        table.sales {{ table-layout: fixed; }}
        table.sales th, table.sales td {{
            font-size: 7.8pt;
            padding: 3px 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        table.sales th {{ font-size: 7.5pt; line-height: 1.15; }}
    </style>
    </head>
    <body>
        <h1>LIFE Daily Sales &amp; Appointments Report</h1>
        <div class="meta">
            <b>{report_title_suffix}</b>
            &nbsp;|&nbsp; Report Date: <b>{getdate(report_date).strftime('%d-%b-%Y')}</b>
            &nbsp;|&nbsp; Generated: {now_datetime().strftime('%d-%b-%Y %I:%M %p')}
            &nbsp;|&nbsp; Coverage: {coverage_label}
            <br/>
            Sales Cycle: <b>{getdate(summary['period_from']).strftime('%d-%b-%Y')}</b>
            &nbsp;&rarr;&nbsp;
            <b>{getdate(summary['period_to']).strftime('%d-%b-%Y')}</b>
            &nbsp;(6th &rarr; 5th window)
            {f"&nbsp;|&nbsp; Target Doc: <code>{summary['target_doc']}</code>" if summary.get('target_doc') else ""}
        </div>

        <div class="summary">
            <b>Overall Summary:</b><br/>
            Total Sales (Day): <b>Rs. {_money(summary['total_today_sales'])}</b>
            &nbsp;(excl. GST: <b>Rs. {_money(summary['total_today_sales_excl_gst'])}</b>)
            &nbsp;|&nbsp; Total Invoices: <b>{summary['total_invoices']}</b><br/>
            Cycle Total: <b>Rs. {_money(summary['total_mtd_sales'])}</b>
            &nbsp;(excl. GST: <b>Rs. {_money(summary['total_mtd_sales_excl_gst'])}</b>)<br/>
            Overall Target Achievement: <b>{summary['overall_pct']:.1f}%</b> &nbsp;|&nbsp;
            Top Branch: <b>{summary['top_branch']}</b> &nbsp;|&nbsp;
            Lowest Branch: <b>{summary['lowest_branch']}</b><br/>
            Total Service Appointments: <b>{summary['total_service_booked']}</b>
            (Executed: {summary['total_executed']},
             Postponed: {summary['total_postponed']},
             Cancelled: {summary['total_cancelled']})
            &nbsp;|&nbsp; Total Consultations: <b>{summary['total_consultation_booked']}</b>
            (Unbooked: {summary['total_unbooked']})
        </div>

        <h2>Branch-wise Sales Performance</h2>
        <table class="sales">
            <colgroup>
                <col style="width: 6%;" />   <!-- Branch (code only) -->
                <col style="width: 11.5%;" /><!-- Today Sales -->
                <col style="width: 12.5%;" /><!-- Today Sales excl GST -->
                <col style="width: 7.5%;" /> <!-- Today Invoices -->
                <col style="width: 12%;" />  <!-- Cycle Sales -->
                <col style="width: 13%;" />  <!-- Cycle Sales excl GST -->
                <col style="width: 12%;" />  <!-- Target -->
                <col style="width: 8.5%;" /> <!-- Achieved % -->
                <col style="width: 17%;" />  <!-- Pending to Target -->
            </colgroup>
            <thead>
                <tr>
                    <th>Branch</th>
                    <th>Today Sales</th>
                    <th>Today Sales (excl. GST)</th>
                    <th>Today Invoices</th>
                    <th>Cycle Sales</th>
                    <th>Cycle Sales (excl. GST)</th>
                    <th>Target</th>
                    <th>Achieved %</th>
                    <th>Pending to Target</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_sales)}
                <tr class="totals">
                    <td>TOTAL</td>
                    <td class="num">Rs. {_money(summary['total_today_sales'])}</td>
                    <td class="num">Rs. {_money(summary['total_today_sales_excl_gst'])}</td>
                    <td class="num">{summary['total_invoices']}</td>
                    <td class="num">Rs. {_money(summary['total_mtd_sales'])}</td>
                    <td class="num">Rs. {_money(summary['total_mtd_sales_excl_gst'])}</td>
                    <td class="num">Rs. {_money(summary['total_target'])}</td>
                    <td class="num">{summary['overall_pct']:.1f}%</td>
                    <td class="num">Rs. {_money(max(summary['total_target'] - summary['total_mtd_sales'], 0))}</td>
                </tr>
            </tbody>
        </table>

        <h2>Branch-wise Appointments &amp; Consultations</h2>
        <table>
            <thead>
                <tr>
                    <th>Branch</th>
                    <th>Service Booked</th>
                    <th>Executed</th>
                    <th>Postponed</th>
                    <th>Cancelled</th>
                    <th>Consultation Booked</th>
                    <th>Unbooked / Not Converted</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_appts)}
                <tr class="totals">
                    <td>TOTAL</td>
                    <td class="num">{summary['total_service_booked']}</td>
                    <td class="num">{summary['total_executed']}</td>
                    <td class="num">{summary['total_postponed']}</td>
                    <td class="num">{summary['total_cancelled']}</td>
                    <td class="num">{summary['total_consultation_booked']}</td>
                    <td class="num">{summary['total_unbooked']}</td>
                </tr>
            </tbody>
        </table>

        <div class="footer">
            Auto-generated by LIFE ERP &middot; This report is system-generated and
            requires no signature. For queries contact the Accounts team.
        </div>
    </body>
    </html>
    """
    return html


def save_pdf_as_public_file(pdf_bytes, report_date, mode="evening"):
    """
    Save PDF to /files/ (public) and return the full absolute URL.
    Also creates a File doctype record so it appears in File Manager.

    IMPORTANT: WhatsApp (Meta) silently drops template messages containing
    non-HTTPS links. We force https:// here so WATI -> WhatsApp delivery works.
    """
    suffix = "Morning_Closing" if mode == "morning" else "Evening_Live"
    filename = (
        f"LIFE_Daily_Report_{suffix}_"
        f"{getdate(report_date).strftime('%Y-%m-%d')}.pdf"
    )

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "is_private": 0,
        "content": pdf_bytes,
        "decode": False,
    })
    file_doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Build absolute URL and force HTTPS
    url = get_url(file_doc.file_url)
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url


# =========================================================================
# WHATSAPP DISPATCH
# =========================================================================

def send_consolidated_whatsapp(report_date, summary, pdf_url):
    """
    Sends ONE WhatsApp via WATI using the
    `life_sales_and_client_appointment_details` Utility template
    to EACH number in RECIPIENT_NUMBERS.

    Template body parameters (in order):
      {{1}} Date
      {{2}} Total Sales (Rs.)
      {{3}} Total Invoices
      {{4}} Overall Target Achievement %
      {{5}} Top Branch
      {{6}} Lowest Branch
      {{7}} Source (PDF URL)
    """
    date_str = getdate(report_date).strftime("%d-%m-%Y")

    payload = {
        "template_name": WATI_TEMPLATE_NAME,
        "broadcast_name": WATI_BROADCAST_NAME,
        "parameters": [
            {"name": "1", "value": date_str},
            {"name": "2", "value": _money(summary["total_today_sales"])},
            {"name": "3", "value": str(summary["total_invoices"])},
            {"name": "4", "value": f"{summary['overall_pct']:.1f}"},
            {"name": "5", "value": summary["top_branch"] or "N/A"},
            {"name": "6", "value": summary["lowest_branch"] or "N/A"},
            {"name": "7", "value": pdf_url or ""},
            # WATI requires the parameter name as listed in the template -
            # if your template uses {{Source}} by name instead of {{7}},
            # ALSO include this alias (WATI accepts both numeric and named):
            {"name": "Source", "value": pdf_url or ""},
        ],
        "channel_number": WATI_CHANNEL_NUMBER,
    }

    headers = {
        "Authorization": f"Bearer {WATI_TOKEN}",
        "Content-Type": "application/json",
    }

    results = {}
    all_ok = True

    if not WHATSAPP_ENABLED:
        frappe.logger().info("[Daily Report] WHATSAPP_ENABLED is False - skipping send")
        return {"ok": True, "results": {"skipped": "WHATSAPP_ENABLED=False"}}

    for number in RECIPIENT_NUMBERS:
        url = f"{WATI_BASE_URL}?whatsappNumber={number}"
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            http_ok = (response.status_code == 200)

            # WATI returns HTTP 200 even when Meta later rejects the message.
            # Inspect the JSON body for Meta-level errors / restrictions.
            meta_ok = True
            meta_error = None
            try:
                body = response.json()
                # WATI shape: { "result": true/false, "error": "...",
                #               "receivers": [{ "errors": [...] }] }
                if body.get("result") is False:
                    meta_ok = False
                    meta_error = body.get("error") or "WATI result=false"
                receivers = body.get("receivers") or []
                for r in receivers:
                    if r.get("errors"):
                        meta_ok = False
                        meta_error = str(r.get("errors"))
                        break
            except Exception:
                # Body wasn't JSON - rely on HTTP status only
                pass

            ok = http_ok and meta_ok
            results[number] = {
                "status_code": response.status_code,
                "ok": ok,
                "meta_error": meta_error,
                "response": response.text[:500],
            }

            frappe.logger().info({
                "event": "Daily Sales+Appointments WhatsApp",
                "status_code": response.status_code,
                "meta_ok": meta_ok,
                "meta_error": meta_error,
                "response": response.text[:500],
                "sent_to": number,
                "pdf_url": pdf_url,
                "report_date": str(report_date),
            })

            if not ok:
                all_ok = False
                err_title = "Daily Report WhatsApp Failed"
                err_msg = (
                    f"Number: {number}\n"
                    f"HTTP: {response.status_code}\n"
                    f"Meta Error: {meta_error}\n"
                    f"Response: {response.text[:800]}"
                )
                frappe.log_error(err_msg, err_title)

        except Exception as e:
            all_ok = False
            results[number] = {"ok": False, "error": str(e)}
            frappe.log_error(
                f"WATI Exception for {number}: {frappe.get_traceback()}",
                "Daily Report WhatsApp Exception",
            )

    return {"ok": all_ok, "results": results}


# =========================================================================
# MAIN ENTRY POINT (scheduler hook)
# =========================================================================

def run_daily_report(mode="evening"):
    """
    Main scheduler entry point.

    mode = 'evening' -> same-day data, run at 8:30 PM
    mode = 'morning' -> yesterday closing data, run at 10:00 AM
    """
    try:
        report_date = get_report_date(mode)

        # 1. Resolve fiscal period + targets from Monthly Target vs Archive
        period_from, period_to, target_doc, targets = get_active_target_period()

        # Clamp the period_to to report_date so MTD never includes future dates
        # within the same cycle. Sales window = [period_from, min(report_date, period_to)]
        cycle_end = report_date if getdate(report_date) <= getdate(period_to) else period_to

        # 2. Fetch sales + appointment data
        sales = fetch_sales_data(report_date, period_from)
        appts = fetch_appointment_data(report_date)

        # 2. Build summary (for WhatsApp body + PDF header)
        total_today_sales = sum(sales[b[0]]["today_sales"] for b in BRANCHES)
        total_today_sales_excl_gst = sum(sales[b[0]]["today_sales_excl_gst"] for b in BRANCHES)
        total_invoices = sum(sales[b[0]]["today_invoices"] for b in BRANCHES)
        total_mtd_sales = sum(sales[b[0]]["mtd_sales"] for b in BRANCHES)
        total_mtd_sales_excl_gst = sum(sales[b[0]]["mtd_sales_excl_gst"] for b in BRANCHES)
        total_target = sum(targets.values())
        overall_pct = (total_mtd_sales / total_target * 100.0) if total_target > 0 else 0.0

        # Top/lowest branch by today's sales (returned as SHORT CODES for WhatsApp + PDF)
        per_branch_today = [(b[0], sales[b[0]]["today_sales"]) for b in BRANCHES]
        per_branch_today_sorted = sorted(per_branch_today, key=lambda x: x[1], reverse=True)
        top_branch_name = per_branch_today_sorted[0][0] if per_branch_today_sorted else None
        lowest_branch_name = per_branch_today_sorted[-1][0] if per_branch_today_sorted else None
        top_branch = BRANCH_CODE.get(top_branch_name, "N/A") if top_branch_name else "N/A"
        lowest_branch = BRANCH_CODE.get(lowest_branch_name, "N/A") if lowest_branch_name else "N/A"

        summary = {
            "mode": mode,
            "period_from": period_from,
            "period_to": period_to,
            "target_doc": target_doc,
            "total_today_sales": total_today_sales,
            "total_today_sales_excl_gst": total_today_sales_excl_gst,
            "total_invoices": total_invoices,
            "total_mtd_sales": total_mtd_sales,
            "total_mtd_sales_excl_gst": total_mtd_sales_excl_gst,
            "total_target": total_target,
            "overall_pct": overall_pct,
            "top_branch": top_branch,
            "lowest_branch": lowest_branch,
            "total_service_booked": sum(appts[b[0]]["service_booked"] for b in BRANCHES),
            "total_executed": sum(appts[b[0]]["executed"] for b in BRANCHES),
            "total_postponed": sum(appts[b[0]]["postponed"] for b in BRANCHES),
            "total_cancelled": sum(appts[b[0]]["cancelled"] for b in BRANCHES),
            "total_consultation_booked": sum(appts[b[0]]["consultation_booked"] for b in BRANCHES),
            "total_unbooked": sum(appts[b[0]]["unbooked"] for b in BRANCHES),
        }

        # 3. Build PDF
        html = build_pdf_html(report_date, targets, sales, appts, summary)
        pdf_bytes = get_pdf(html)

        # 4. Save PDF as public File and get URL
        pdf_url = save_pdf_as_public_file(pdf_bytes, report_date, mode=mode)

        # 5. Send WhatsApp (to all recipients)
        send_result = send_consolidated_whatsapp(report_date, summary, pdf_url)

        frappe.logger().info(
            f"[Daily Report] date={report_date} pdf={pdf_url} "
            f"sent_ok={send_result['ok']} results={send_result['results']}"
        )
        return {
            "ok": send_result["ok"],
            "pdf_url": pdf_url,
            "summary": summary,
            "whatsapp": send_result["results"],
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Daily Sales+Appointments Report Failed")
        raise


# =========================================================================
# SCHEDULER WRAPPERS (register these in hooks.py)
# =========================================================================

def run_morning_report():
    """
    10:00 AM run - Yesterday Closing Report (full day 00:00 - 23:59).
    Register in hooks.py:
        "0 10 * * *": ["life_slimming.daily_sales_appointments_report.run_morning_report"]
    """
    return run_daily_report(mode="morning")


def run_evening_report():
    """
    8:30 PM run - Same-day live update (partial day up to run time).
    Register in hooks.py:
        "30 20 * * *": ["life_slimming.daily_sales_appointments_report.run_evening_report"]
    """
    return run_daily_report(mode="evening")


# =========================================================================
# MANUAL TEST HOOKS (call via bench execute)
# =========================================================================

@frappe.whitelist()
def trigger_now(mode="evening"):
    """Manual trigger:
        bench --site <site> execute life_slimming.daily_sales_appointments_report.trigger_now
        bench --site <site> execute life_slimming.daily_sales_appointments_report.trigger_now \\
              --kwargs '{"mode": "morning"}'
    """
    return run_daily_report(mode=mode)


@frappe.whitelist()
def trigger_morning():
    """Manual morning trigger."""
    return run_morning_report()


@frappe.whitelist()
def trigger_evening():
    """Manual evening trigger."""
    return run_evening_report()