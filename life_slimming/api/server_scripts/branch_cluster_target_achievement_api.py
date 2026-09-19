"""branch_cluster_target_achievement_api

Original API: branch_cluster_target_achievement_api
Source modified: 2026-09-18 18:28:30.205450
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
    # Cluster Wise Sales API - day/month targets, achievements, gaps, asking rate and Lead walk-ins
    args = frappe.form_dict or {}

    CLUSTER_MAP = {
        "Hyderabad Cluster 1 (Teena Mahur)": ["Kukatpally", "Madhapur", "Gachibowli", "Chandanagar"],
        "Hyderabad Cluster 2 (Hima Bindu)": ["Banjara Hills", "Himayathnagar", "Dilsukhnagar", "SR Nagar"],
        "AP Cluster": ["Vizag", "Vijayawada", "Nellore"]
    }

    USER_CLUSTER = {
        "teena@lifescc.com": "Hyderabad Cluster 1 (Teena Mahur)",
        "himabindu@lifescc.com": "Hyderabad Cluster 2 (Hima Bindu)",
        "navya@lifescc.com": "AP Cluster",
        "preethi.m@lifescc.com": "AP Cluster",
        "arunakumari@lifescc.com": "AP Cluster"
    }

    from_date = args.get("from_date") or frappe.utils.nowdate()
    to_date = args.get("to_date") or frappe.utils.nowdate()
    anchor = frappe.utils.getdate(to_date)

    ay = anchor.year
    am = anchor.month
    if anchor.day < 6:
        am = am - 1
        if am < 1:
            am = 12
            ay = ay - 1

    cycle_first = frappe.utils.get_first_day(frappe.utils.getdate(str(ay) + "-" + str(am) + "-01"))
    cycle_from = frappe.utils.add_days(cycle_first, 5)
    next_month = am + 1
    next_year = ay
    if next_month > 12:
        next_month = 1
        next_year = next_year + 1
    next_first = frappe.utils.get_first_day(frappe.utils.getdate(str(next_year) + "-" + str(next_month) + "-01"))
    cycle_to = frappe.utils.add_days(next_first, 4)

    cycle_days = frappe.utils.date_diff(cycle_to, cycle_from) + 1
    remaining_days = frappe.utils.date_diff(cycle_to, anchor) + 1
    if remaining_days < 1:
        remaining_days = 1

    requested = (args.get("cluster") or "").strip()
    user = frappe.session.user
    if requested and requested in CLUSTER_MAP:
        cluster_names = [requested]
    elif requested == "ALL":
        cluster_names = list(CLUSTER_MAP.keys())
    elif user in USER_CLUSTER:
        cluster_names = [USER_CLUSTER.get(user)]
    else:
        cluster_names = list(CLUSTER_MAP.keys())

    clusters_out = []
    ci = 0
    while ci < len(cluster_names):
        cluster_name = cluster_names[ci]
        branches = CLUSTER_MAP.get(cluster_name, [])
        rows = []
        totals = {"day_target": 0.0, "day_achieved": 0.0, "day_gap": 0.0, "month_target": 0.0, "month_achieved": 0.0, "month_gap": 0.0, "asking_rate": 0.0, "total_appointments": 0, "visited": 0, "visited_booked": 0, "visited_not_booked": 0}

        bi = 0
        while bi < len(branches):
            branch = branches[bi]

            target_rows = _read_sql("""
            SELECT SUM(wa.targeted_amount) AS amount
            FROM `tabWeek Achive` wa
            INNER JOIN `tabWeek Target vs Achive With Cuttings` h ON h.name = wa.parent
            WHERE wa.branch = %(branch)s
              AND h.docstatus < 2
              AND h.from_date <= %(cycle_to)s
              AND h.to_date >= %(cycle_from)s
        """, {"branch": branch, "cycle_from": cycle_from, "cycle_to": cycle_to}, as_dict=True)
            month_target = float(target_rows[0].get("amount") or 0) if target_rows else 0.0

            month_rows = _read_sql("""
            SELECT SUM(paid_amount) AS amount
            FROM `tabPayment Entry`
            WHERE docstatus = 1
              AND payment_type = 'Receive'
              AND branch = %(branch)s
              AND posting_date BETWEEN %(cycle_from)s AND %(anchor)s
        """, {"branch": branch, "cycle_from": cycle_from, "anchor": anchor}, as_dict=True)
            month_achieved = float(month_rows[0].get("amount") or 0) / 1.05 if month_rows else 0.0

            day_rows = _read_sql("""
            SELECT SUM(paid_amount) AS amount
            FROM `tabPayment Entry`
            WHERE docstatus = 1
              AND payment_type = 'Receive'
              AND branch = %(branch)s
              AND posting_date = %(anchor)s
        """, {"branch": branch, "anchor": anchor}, as_dict=True)
            day_achieved = float(day_rows[0].get("amount") or 0) / 1.05 if day_rows else 0.0

            walkin_rows = _read_sql("""
            SELECT
                COUNT(DISTINCT CASE
                    WHEN COALESCE(custom_appointment_status, '') != '' THEN name
                END) AS total_appointments,
                COUNT(DISTINCT CASE
                    WHEN custom_appointment_status = 'Visited' THEN name
                END) AS visited,
                COUNT(DISTINCT CASE
                    WHEN custom_appointment_status = 'Visited Booked' THEN name
                END) AS visited_booked,
                COUNT(DISTINCT CASE
                    WHEN custom_appointment_status = 'Visited Not Booked' THEN name
                END) AS visited_not_booked
            FROM `tabLead`
            WHERE custom_appointment_date_and_time >= %(from_start)s
              AND custom_appointment_date_and_time < %(to_end)s
              AND COALESCE(NULLIF(branch, ''), lead_assign_to_branch) = %(branch)s
        """, {
                "branch": branch,
                "from_start": str(from_date) + " 00:00:00",
                "to_end": str(frappe.utils.add_days(to_date, 1)) + " 00:00:00"
            }, as_dict=True)
            appointment_counts = walkin_rows[0] if walkin_rows else {}
            total_appointments = int(appointment_counts.get("total_appointments") or 0)
            visited = int(appointment_counts.get("visited") or 0)
            visited_booked = int(appointment_counts.get("visited_booked") or 0)
            visited_not_booked = int(appointment_counts.get("visited_not_booked") or 0)

            day_target = month_target / cycle_days if cycle_days else 0.0
            day_gap = day_target - day_achieved
            month_gap = month_target - month_achieved
            asking_rate = month_gap / remaining_days if month_gap > 0 else 0.0
            month_pct = round(month_achieved / month_target * 100.0, 1) if month_target > 0 else 0.0

            row = {
                "branch": branch,
                "day_target": day_target,
                "day_achieved": day_achieved,
                "day_gap": day_gap,
                "month_target": month_target,
                "month_achieved": month_achieved,
                "month_gap": month_gap,
                "asking_rate": asking_rate,
                "total_appointments": total_appointments,
                "visited": visited,
                "visited_booked": visited_booked,
                "visited_not_booked": visited_not_booked,
                "month_pct": month_pct,
                "target": month_target,
                "achieved": month_achieved,
                "gap": month_gap,
                "pct": month_pct
            }
            rows.append(row)

            for key in ["day_target", "day_achieved", "day_gap", "month_target", "month_achieved", "month_gap", "asking_rate"]:
                totals[key] = totals[key] + row[key]
            totals["total_appointments"] = totals["total_appointments"] + total_appointments
            totals["visited"] = totals["visited"] + visited
            totals["visited_booked"] = totals["visited_booked"] + visited_booked
            totals["visited_not_booked"] = totals["visited_not_booked"] + visited_not_booked
            bi = bi + 1

        totals["month_pct"] = round(totals["month_achieved"] / totals["month_target"] * 100.0, 1) if totals["month_target"] > 0 else 0.0
        totals["target"] = totals["month_target"]
        totals["achieved"] = totals["month_achieved"]
        totals["gap"] = totals["month_gap"]
        totals["pct"] = totals["month_pct"]
        totals["cluster"] = cluster_name
        totals["branches"] = rows
        clusters_out.append(totals)
        ci = ci + 1

    out = {
        "cycle_from": str(cycle_from),
        "cycle_to": str(cycle_to),
        "as_on_date": str(anchor),
        "selected_from": str(from_date),
        "selected_to": str(to_date),
        "clusters": clusters_out,
        "all_cluster_names": list(CLUSTER_MAP.keys()),
        "default_cluster": USER_CLUSTER.get(user)
    }
    frappe.response["message"] = out
