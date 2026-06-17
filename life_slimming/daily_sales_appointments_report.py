"""
Daily Sales + Appointments Consolidated Report
==============================================
- Runs daily at 8:30 PM via Frappe scheduler (configure in hooks.py).
- Pulls yesterday's closing data (00:00 -> 23:59 of "yesterday").
- Generates a single branch-wise PDF with sales + appointments insights.
- Uploads PDF as a public File in /files/.
- Sends ONE consolidated WhatsApp via WATI template `life_sales_and_appointments`
  to hard-coded number 9604238978, embedding the PDF URL in {{Source}} ({{7}}).

hooks.py registration:
----------------------
scheduler_events = {
    "cron": {
        # Every day at 8:30 PM server time
        "30 20 * * *": [
            "your_app.path.to.daily_sales_appointments_report.run_daily_report"
        ]
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
WATI_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"
WATI_CHANNEL_NUMBER = "918143156363"
WATI_TEMPLATE_NAME = "life_sales_and_appointments"
WATI_BROADCAST_NAME = "life_sales_and_appointments"

# Hard-coded recipient
RECIPIENT_NUMBER = "919604238978"  # 91 prefix + 9604238978

# Ordered branches with display codes (must match the templates)
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


def get_report_date():
    """
    Report covers 'yesterday' (full day, 00:00 -> 23:59).
    Script runs at 8:30 PM today, so 'yesterday' = today - 1.
    """
    return add_days(nowdate(), -1)


def get_month_start(report_date):
    """First day of the month for MTD calculation."""
    d = getdate(report_date)
    return d.replace(day=1)


def fetch_branch_targets():
    """
    Pull targets from Monthly Target vs Archive (submitted) child table
    'Monthly Target and Archive Data'. Returns {branch: target_amount}.
    Uses the latest submitted record whose from_date <= today <= to_date,
    falling back to the most recent submitted record.
    """
    targets = {b[0]: 0.0 for b in BRANCHES}

    today = nowdate()

    parent = frappe.db.sql(
        """
        SELECT name FROM `tabMonthly Target vs Archive`
        WHERE docstatus = 1
          AND %s BETWEEN IFNULL(from_date, '1900-01-01')
                     AND IFNULL(to_date,   '2999-12-31')
        ORDER BY modified DESC LIMIT 1
        """,
        (today,), as_dict=True
    )
    if not parent:
        parent = frappe.db.sql(
            """
            SELECT name FROM `tabMonthly Target vs Archive`
            ORDER BY modified DESC LIMIT 1
            """, as_dict=True
        )

    if parent:
        rows = frappe.db.sql(
            """
            SELECT branch, targeted_amount
            FROM `tabMonthly Target and Archive Data`
            WHERE parent = %s AND parenttype = 'Monthly Target vs Archive'
            """,
            (parent[0].name,), as_dict=True
        )
        for r in rows:
            if r.branch and r.branch in targets:
                targets[r.branch] = flt(r.targeted_amount)
    return targets


def fetch_sales_data(report_date, month_start):
    """
    Per-branch: today's sales (yesterday actually), today's invoice count, MTD sales.
    Uses submitted Sales Invoices only (docstatus = 1) and excludes return invoices.
    """
    result = {b[0]: {"today_sales": 0.0, "today_invoices": 0, "mtd_sales": 0.0}
              for b in BRANCHES}

    # Today's (yesterday's) sales + invoice count
    rows = frappe.db.sql(
        """
        SELECT branch,
               COUNT(*) AS invoices,
               SUM(grand_total) AS total
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
            result[r.branch]["today_sales"] = flt(r.total)
            result[r.branch]["today_invoices"] = cint(r.invoices)

    # MTD sales (from 1st of month till and including report_date)
    rows = frappe.db.sql(
        """
        SELECT branch, SUM(grand_total) AS total
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND IFNULL(is_return, 0) = 0
          AND posting_date BETWEEN %s AND %s
        GROUP BY branch
        """,
        (month_start, report_date), as_dict=True
    )
    for r in rows:
        if r.branch in result:
            result[r.branch]["mtd_sales"] = flt(r.total)

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
                <td>{branch_name} <span class="code">| {code}</span></td>
                <td class="num">Rs. {_money(s['today_sales'])}</td>
                <td class="num">{s['today_invoices']}</td>
                <td class="num">Rs. {_money(s['mtd_sales'])}</td>
                <td class="num">Rs. {_money(t)}</td>
                <td class="num">{achieved_pct:.1f}%</td>
                <td class="num">Rs. {_money(pending)}</td>
            </tr>
        """)

        a = appts[branch_name]
        rows_appts.append(f"""
            <tr>
                <td>{branch_name} <span class="code">| {code}</span></td>
                <td class="num">{a['service_booked']}</td>
                <td class="num">{a['executed']}</td>
                <td class="num">{a['postponed']}</td>
                <td class="num">{a['cancelled']}</td>
                <td class="num">{a['consultation_booked']}</td>
                <td class="num">{a['unbooked']}</td>
            </tr>
        """)

    html = f"""
    <html>
    <head>
    <style>
        @page {{ size: A4 landscape; margin: 12mm; }}
        body {{ font-family: Helvetica, Arial, sans-serif; color: #222; font-size: 10pt; }}
        h1 {{ color: #1f4e79; margin: 0 0 4px 0; font-size: 18pt; }}
        h2 {{ color: #2e75b6; margin: 18px 0 8px 0; font-size: 13pt;
              border-bottom: 2px solid #2e75b6; padding-bottom: 3px; }}
        .meta {{ color: #555; font-size: 9pt; margin-bottom: 10px; }}
        .summary {{ background: #f2f7fb; border-left: 4px solid #2e75b6;
                    padding: 8px 12px; margin: 8px 0 14px 0; font-size: 10pt; }}
        .summary b {{ color: #1f4e79; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
        th, td {{ border: 1px solid #cfd8dc; padding: 5px 7px; text-align: left;
                  font-size: 9pt; }}
        th {{ background: #1f4e79; color: #fff; font-weight: 600; }}
        tr:nth-child(even) td {{ background: #fafafa; }}
        td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
        .code {{ color: #777; font-size: 8pt; }}
        .footer {{ margin-top: 20px; font-size: 8pt; color: #888;
                   border-top: 1px solid #ddd; padding-top: 6px; }}
        .totals td {{ background: #e8f1f9 !important; font-weight: 700; }}
    </style>
    </head>
    <body>
        <h1>LIFE Daily Sales &amp; Appointments Report</h1>
        <div class="meta">
            Report Date: <b>{getdate(report_date).strftime('%d-%b-%Y')}</b>
            &nbsp;|&nbsp; Generated: {now_datetime().strftime('%d-%b-%Y %I:%M %p')}
            &nbsp;|&nbsp; Coverage: Closing data till yesterday 12:00 AM
        </div>

        <div class="summary">
            <b>Overall Summary:</b><br/>
            Total Sales (Day): <b>Rs. {_money(summary['total_today_sales'])}</b> &nbsp;|&nbsp;
            Total Invoices: <b>{summary['total_invoices']}</b> &nbsp;|&nbsp;
            MTD Total: <b>Rs. {_money(summary['total_mtd_sales'])}</b><br/>
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
        <table>
            <thead>
                <tr>
                    <th>Branch</th>
                    <th>Today Sales</th>
                    <th>Today Invoices</th>
                    <th>MTD Sales</th>
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
                    <td class="num">{summary['total_invoices']}</td>
                    <td class="num">Rs. {_money(summary['total_mtd_sales'])}</td>
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


def save_pdf_as_public_file(pdf_bytes, report_date):
    """
    Save PDF to /files/ (public) and return the full absolute URL.
    Also creates a File doctype record so it appears in File Manager.
    """
    filename = f"LIFE_Daily_Report_{getdate(report_date).strftime('%Y-%m-%d')}.pdf"

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "is_private": 0,
        "content": pdf_bytes,
        "decode": False,
    })
    file_doc.save(ignore_permissions=True)
    frappe.db.commit()

    # file_url comes back as "/files/<name>.pdf" - prefix with site URL
    return get_url(file_doc.file_url)


# =========================================================================
# WHATSAPP DISPATCH
# =========================================================================

def send_consolidated_whatsapp(report_date, summary, pdf_url):
    """
    Sends ONE WhatsApp via WATI using the `life_sales_and_appointments` template.

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

    url = f"{WATI_BASE_URL}?whatsappNumber={RECIPIENT_NUMBER}"
    headers = {
        "Authorization": f"Bearer {WATI_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)

    frappe.logger().info({
        "event": "Daily Sales+Appointments WhatsApp",
        "status_code": response.status_code,
        "response": response.text[:500],
        "sent_to": RECIPIENT_NUMBER,
        "pdf_url": pdf_url,
        "report_date": str(report_date),
    })

    if response.status_code != 200:
        frappe.log_error(
            f"WATI Error {response.status_code}: {response.text}",
            "Daily Report WhatsApp Failed",
        )
        return False
    return True


# =========================================================================
# MAIN ENTRY POINT (scheduler hook)
# =========================================================================

def run_daily_report():
    """
    Scheduler entry point - register in hooks.py under scheduler_events.cron.
    Cron expression for 8:30 PM daily: "30 20 * * *"
    """
    try:
        report_date = get_report_date()
        month_start = get_month_start(report_date)

        # 1. Fetch all data
        targets = fetch_branch_targets()
        sales = fetch_sales_data(report_date, month_start)
        appts = fetch_appointment_data(report_date)

        # 2. Build summary (for WhatsApp body + PDF header)
        total_today_sales = sum(sales[b[0]]["today_sales"] for b in BRANCHES)
        total_invoices = sum(sales[b[0]]["today_invoices"] for b in BRANCHES)
        total_mtd_sales = sum(sales[b[0]]["mtd_sales"] for b in BRANCHES)
        total_target = sum(targets.values())
        overall_pct = (total_mtd_sales / total_target * 100.0) if total_target > 0 else 0.0

        # Top/lowest branch by today's sales (ignore zero-sales for "top" tiebreaks)
        per_branch_today = [(b[0], sales[b[0]]["today_sales"]) for b in BRANCHES]
        per_branch_today_sorted = sorted(per_branch_today, key=lambda x: x[1], reverse=True)
        top_branch = per_branch_today_sorted[0][0] if per_branch_today_sorted else "N/A"
        lowest_branch = per_branch_today_sorted[-1][0] if per_branch_today_sorted else "N/A"

        summary = {
            "total_today_sales": total_today_sales,
            "total_invoices": total_invoices,
            "total_mtd_sales": total_mtd_sales,
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
        pdf_url = save_pdf_as_public_file(pdf_bytes, report_date)

        # 5. Send WhatsApp
        ok = send_consolidated_whatsapp(report_date, summary, pdf_url)

        frappe.logger().info(
            f"[Daily Report] date={report_date} pdf={pdf_url} sent={ok}"
        )
        return {"ok": ok, "pdf_url": pdf_url, "summary": summary}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Daily Sales+Appointments Report Failed")
        raise


# =========================================================================
# MANUAL TEST HOOK (call via bench execute)
# =========================================================================

@frappe.whitelist()
def trigger_now():
    """Manual trigger:
        bench --site <site> execute your_app.path.daily_sales_appointments_report.trigger_now
    """
    return run_daily_report()