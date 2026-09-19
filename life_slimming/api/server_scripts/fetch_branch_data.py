"""fetch_branch_data

Original API: fetch_branch_data
Source modified: 2026-06-03 23:16:14.875797
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
    # ============================================================
    #  MTD Performance Email — ERPNext Server Script
    # ============================================================

    # ── 1. PARAMETERS ────────────────────────────────────────────
    from_date  = frappe.form_dict.get('from_date')
    to_date    = frappe.form_dict.get('to_date')
    lm_from    = frappe.form_dict.get('last_month_from')
    lm_to      = frappe.form_dict.get('last_month_to')
    doc_name   = frappe.form_dict.get('doc_name')

    if not all([from_date, to_date, doc_name]):
        frappe.throw("Missing required parameters: from_date, to_date, doc_name")

    EXCLUDED_BRANCHES = ("Head Office", "All Branch", "Vijaywada And Dilsukhnagarr")

    SHORT_NAMES = {
        "Himayathnagar" : "HMY",
        "Banjara Hills"  : "BNJ",
        "Dilsukhnagar"   : "DSN",
        "Vijayawada"     : "VJA",
        "Secunderabad"   : "SEC",
        "Kukatpally"     : "KPT",
        "Guntur"         : "GNT",
        "Gachibowli"     : "GCH",
        "SR Nagar"       : "SRN",
        "Vizag"          : "VZG",
        "Chandanagar"    : "CHN",
        "Madhapur"       : "MDH",
        "Nellore"        : "NLR",
    }

    # ── 2. DATA ACQUISITION ──────────────────────────────────────
    def get_stats(start, end):
        if not start or not end:
            return {}
        rows = _read_sql("""
        SELECT
            pe.branch,
            SUM(pe.paid_amount)             AS actual_paid,
            SUM(pe.paid_amount / 1.05)      AS amt_without_gst,
            SUM(CASE
                    WHEN pe.mode_of_payment IN (
                        'Sai Roshini Card Charges',
                        'Liqui Loans Charges',
                        'ShopSE',
                        'Loan Tap / Uno Finance Charges',
                        'Savein Fintech Card Charges',
                        'Bajaj Card Charges',
                        'Fibe Finance',
                        'Carepay'
                    ) THEN (pe.paid_amount / 1.05) * 0.10
                    ELSE 0
                END)                        AS mode_cut_amt
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus = 1
          AND pe.posting_date BETWEEN %(start)s AND %(end)s
          AND pe.branch NOT IN %(excluded)s
        GROUP BY pe.branch
    """, {"start": start, "end": end, "excluded": EXCLUDED_BRANCHES}, as_dict=True)
        return {r.branch: r for r in rows}

    today_date     = frappe.utils.today()
    today_dt       = frappe.utils.getdate(today_date)
    weekday_num    = today_dt.weekday()
    week_start_str = str(frappe.utils.add_days(today_date, -weekday_num))

    current_stats    = get_stats(from_date, to_date)
    last_month_stats = get_stats(lm_from, lm_to)
    today_stats      = get_stats(today_date, today_date)
    week_stats       = get_stats(week_start_str, today_date)

    # ── 3. BUSINESS LOGIC ────────────────────────────────────────
    doc       = frappe.get_doc("Week Target vs Achive With Cuttings", doc_name)
    rem_days  = max(frappe.utils.date_diff(to_date, today_date), 1)
    rem_weeks = max(rem_days / 7.0, 1)

    def get_short(name):
        return SHORT_NAMES.get(name, name[:5] + ".")

    branch_rows = []
    g_t = g_wo = g_l_wo = g_n = g_l_n = g_df = 0.0
    g_day_ask = g_week_ask = g_today_n = g_week_n = 0.0

    for d in doc.get("week_target_vs_archive_details"):
        br  = d.branch
        s   = current_stats.get(br, {})
        ls  = last_month_stats.get(br, {})
        ts  = today_stats.get(br, {})
        ws  = week_stats.get(br, {})

        t         = frappe.utils.flt(d.targeted_amount)
        wo        = frappe.utils.flt(s.get("amt_without_gst", 0))
        l_wo      = frappe.utils.flt(ls.get("amt_without_gst", 0))
        cut       = frappe.utils.flt(s.get("mode_cut_amt", 0))
        l_cut     = frappe.utils.flt(ls.get("mode_cut_amt", 0))
        n         = wo - cut
        l_n       = l_wo - l_cut
        p         = (n / t * 100)   if t else 0.0
        lp        = (l_n / t * 100) if t else 0.0
        df        = max(t - n, 0)
        day_ask   = (df / rem_days)  if df else 0.0
        week_ask  = (df / rem_weeks) if df else 0.0

        t_wo      = frappe.utils.flt(ts.get("amt_without_gst", 0))
        t_cut     = frappe.utils.flt(ts.get("mode_cut_amt", 0))
        today_n   = t_wo - t_cut

        w_wo      = frappe.utils.flt(ws.get("amt_without_gst", 0))
        w_cut     = frappe.utils.flt(ws.get("mode_cut_amt", 0))
        week_n    = w_wo - w_cut

        g_t        = g_t        + t
        g_wo       = g_wo       + wo
        g_l_wo     = g_l_wo     + l_wo
        g_n        = g_n        + n
        g_l_n      = g_l_n      + l_n
        g_df       = g_df       + df
        g_day_ask  = g_day_ask  + day_ask
        g_week_ask = g_week_ask + week_ask
        g_today_n  = g_today_n  + today_n
        g_week_n   = g_week_n   + week_n

        branch_rows.append({
            "br": br, "t": t, "wo": wo, "l_wo": l_wo,
            "n": n, "l_n": l_n, "df": df,
            "day_ask": day_ask, "week_ask": week_ask,
            "today_n": today_n, "week_n": week_n,
            "p": p, "lp": lp
        })

    branch_rows.sort(key=lambda x: x["p"], reverse=True)
    g_p = (g_n / g_t * 100) if g_t else 0

    # ── 4. HTML HELPERS ──────────────────────────────────────────
    def fmt(v):
        v = int(v)
        s = str(v)
        if len(s) <= 3:
            return s
        last3 = s[-3:]
        rest  = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.append(rest)
        parts.reverse()
        return ",".join(parts) + "," + last3

    def pct_color(p):
        if p >= 100: return "#10b981"
        if p >= 80:  return "#f97316"
        return "#ef4444"

    def trend_arrow(curr, prev):
        if curr > prev: return '<span style="color:#10b981;">&#9650;</span>'
        if curr < prev: return '<span style="color:#ef4444;">&#9660;</span>'
        return '<span style="color:#94a3b8;">&#8212;</span>'

    def badge(p, lp):
        col = pct_color(p)
        arr = trend_arrow(p, lp)
        bg  = col + "22"
        pv  = str(int(p))
        return (
            '<span style="display:inline-flex;align-items:center;gap:4px;'
            'padding:2px 10px;border-radius:100px;font-size:11px;font-weight:700;'
            'background:' + bg + ';color:' + col + ';">' + pv + '% ' + arr + '</span>'
        )

    def achieved_badge(achieved, target):
        p   = (achieved / target * 100) if target else 0
        col = pct_color(p)
        bg  = col + "22"
        return (
            '<span style="display:inline-flex;align-items:center;gap:3px;'
            'padding:2px 8px;border-radius:100px;font-size:10px;font-weight:700;'
            'background:' + bg + ';color:' + col + ';">'
            '&#8377;' + str(fmt(achieved)) + '</span>'
        )

    # ── 5. CSS ───────────────────────────────────────────────────
    CSS = (
        '<style>'
        '* { box-sizing:border-box; margin:0; padding:0; }'
        'body { background:#f1f5f9; font-family:Arial,sans-serif; }'
        '.wrap { max-width:1100px; margin:0 auto; background:#fff; border-radius:16px;'
        '        overflow:hidden; box-shadow:0 8px 30px rgba(0,0,0,.12); }'
        '.hero { background:linear-gradient(135deg,#1e3a8a,#1d4ed8,#2563eb);'
        '        padding:28px 24px; text-align:center; color:#fff; }'
        '.hero h2 { font-size:22px; font-weight:800; letter-spacing:-.5px; }'
        '.hero p  { font-size:12px; opacity:.75; margin-top:6px; }'
        '.body { padding:20px; }'
        '.sec-title { font-size:10px; text-transform:uppercase; letter-spacing:.1em;'
        '             color:#94a3b8; margin-bottom:10px; margin-top:8px; padding-bottom:6px;'
        '             border-bottom:1px solid #f1f5f9; }'
        'table { width:100%; border-collapse:collapse; font-size:12px; margin-bottom:20px; }'
        'thead th { background:#f8fafc; color:#64748b; font-weight:600; font-size:10px;'
        '           text-transform:uppercase; letter-spacing:.06em; padding:9px 12px;'
        '           text-align:right; white-space:nowrap; }'
        'thead th:first-child { text-align:left; }'
        'tbody tr { border-bottom:1px solid #f8fafc; }'
        'tbody tr:last-child { border-bottom:none; }'
        'td { padding:10px 12px; text-align:right; color:#475569; }'
        'td:first-child { text-align:left; }'
        '.br-name { font-weight:700; color:#0f172a; font-size:13px; }'
        '.br-sub  { font-size:9px; color:#94a3b8; margin-top:2px; }'
        '.br-badge { margin-top:4px; }'
        '.net-v   { font-weight:700; color:#0f172a; font-size:13px; }'
        '.ask-v   { font-weight:800; color:#f59e0b; font-size:13px; }'
        '.wk-v    { font-weight:800; color:#8b5cf6; font-size:13px; }'
        '.def-v   { color:#ef4444; font-size:11px; }'
        '.tot td  { background:#0f172a; color:#fff; font-weight:700; font-size:13px;'
        '           padding:13px 12px; }'
        '</style>'
    )

    # ── 6. BRANCH TABLE ──────────────────────────────────────────
    branch_rows_html = ""
    excel_rows       = ""

    for r in branch_rows:
        br_name  = r["br"]
        sh_name  = get_short(br_name)
        br_badge = badge(r["p"], r["lp"])

        branch_rows_html = (
            branch_rows_html
            + '<tr>'
            + '<td>'
            + '<div class="br-name">' + br_name + '</div>'
            + '<div class="br-sub">' + sh_name + '</div>'
            + '<div class="br-badge">' + br_badge + '</div>'
            + '</td>'
            + '<td>' + str(fmt(r["t"])) + '</td>'
            + '<td><span class="net-v">' + str(fmt(r["n"]))    + '</span></td>'
            + '<td style="color:#6366f1;">' + str(fmt(r["wo"]))   + '</td>'
            + '<td style="color:#94a3b8;">' + str(fmt(r["l_wo"])) + '</td>'
            + '<td style="color:#94a3b8;">' + str(fmt(r["l_n"]))  + '</td>'
            + '<td><span class="def-v">'    + str(fmt(r["df"]))   + '</span></td>'
            + '<td><span class="ask-v">'  + str(fmt(r["day_ask"]))  + '</span></td>'
            + '<td>' + achieved_badge(r["today_n"], r["day_ask"]) + '</td>'
            + '<td><span class="wk-v">'   + str(fmt(r["week_ask"])) + '</span></td>'
            + '<td>' + achieved_badge(r["week_n"],  r["week_ask"]) + '</td>'
            + '</tr>'
        )

        excel_rows = (
            excel_rows
            + '<tr>'
            + '<td>' + br_name + '</td>'
            + '<td>' + str(int(r["t"]))        + '</td>'
            + '<td>' + str(int(r["n"]))        + '</td>'
            + '<td>' + str(int(r["wo"]))       + '</td>'
            + '<td>' + str(int(r["l_wo"]))     + '</td>'
            + '<td>' + str(int(r["l_n"]))      + '</td>'
            + '<td>' + str(int(r["df"]))       + '</td>'
            + '<td>' + str(int(r["p"])) + '%'  + '</td>'
            + '<td>' + str(int(r["day_ask"]))  + '</td>'
            + '<td>' + str(int(r["today_n"]))  + '</td>'
            + '<td>' + str(int(r["week_ask"])) + '</td>'
            + '<td>' + str(int(r["week_n"]))   + '</td>'
            + '</tr>'
        )

    branch_table = (
        '<div class="sec-title">Branch Breakdown &mdash; sorted by % achieved</div>'
        '<table>'
        '<thead><tr>'
        '<th>Branch</th>'
        '<th>Target</th>'
        '<th>Net MTD</th>'
        '<th style="color:#6366f1;">WO Amt</th>'
        '<th>LM WO</th>'
        '<th>LM Net</th>'
        '<th>Deficit</th>'
        '<th style="background:#fef3c7;color:#92400e;">Day T</th>'
        '<th style="background:#fef3c7;color:#92400e;">Today &#10003;</th>'
        '<th style="background:#ede9fe;color:#5b21b6;">Wk T</th>'
        '<th style="background:#ede9fe;color:#5b21b6;">Wk &#10003;</th>'
        '</tr></thead>'
        '<tbody>' + branch_rows_html + '</tbody>'
        '<tfoot>'
        '<tr class="tot">'
        '<td>TOTAL</td>'
        '<td>' + str(fmt(g_t))      + '</td>'
        '<td>' + str(fmt(g_n))    + '</td>'
        '<td>' + str(fmt(g_wo))   + '</td>'
        '<td>' + str(fmt(g_l_wo)) + '</td>'
        '<td>' + str(fmt(g_l_n))  + '</td>'
        '<td>' + str(fmt(g_df))   + '</td>'
        '<td style="color:#fbbf24;font-weight:800;">' + str(fmt(g_day_ask))  + '</td>'
        '<td style="color:#fbbf24;font-weight:800;">' + str(fmt(g_today_n))  + '</td>'
        '<td style="color:#c4b5fd;font-weight:800;">' + str(fmt(g_week_ask)) + '</td>'
        '<td style="color:#c4b5fd;font-weight:800;">' + str(fmt(g_week_n))   + '</td>'
        '</tr>'
        '</tfoot>'
        '</table>'
    )

    # ── 7. ASSEMBLE EMAIL ────────────────────────────────────────
    email_content = (
        CSS
        + '<div style="background:#f1f5f9;padding:20px;">'
        + '<div class="wrap">'
        + '<div class="hero">'
        + '<h2>' + str(doc_name) + '</h2>'
        + '<p>MTD: ' + str(from_date) + ' &#8594; ' + str(to_date)
        + ' &nbsp;|&nbsp; Week from: ' + str(week_start_str)
        + ' &nbsp;|&nbsp; Today: ' + str(today_date) + '</p>'
        + '</div>'
        + '<div class="body">'
        + branch_table
        + '</div>'
        + '</div>'
        + '</div>'
    )

    excel_content = (
        "<html><body>"
        "<table border='1'>"
        "<tr style='background:#1e3a8a;color:#fff;'>"
        "<th>Branch</th><th>Target</th><th>Net MTD</th>"
        "<th>WO Amt</th><th>LM WO</th><th>LM Net</th>"
        "<th>Deficit</th><th>MTD%</th>"
        "<th>Day Target</th><th>Today Achieved</th>"
        "<th>Week Target</th><th>Week Achieved</th>"
        "</tr>"
        + excel_rows
        + "</table></body></html>"
    )

    # ── 8. SEND ─────────────────────────────────────────────────
    frappe.sendmail(
        recipients  = ["narendhar@lifescc.com", "surya@lifescc.com", "lokakavyareddy3@gmail.com","jaani@lifescc.com","bhuvan@lifescc.com","corporatemanager@lifescc.com"],
        subject     = "MTD Performance: " + str(doc_name) + " (" + str(from_date) + " to " + str(to_date) + ")",
        message     = email_content,
        attachments = [{"fname": str(doc_name) + ".xls", "fcontent": excel_content}],
        now         = True,
    )

    frappe.response["message"] = {
        "status"      : "Email Sent Successfully",
        "branches"    : len(branch_rows),
        "period"      : str(from_date) + " to " + str(to_date),
        "today"       : str(today_date),
        "week_start"  : str(week_start_str),
    }
