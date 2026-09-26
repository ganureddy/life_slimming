"""Lead Assignment Preview API

Original API: lead_assignment_preview
Source modified: 2026-09-16 16:43:06.608562
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

    user = frappe.session.user

    if user == "Guest":
        frappe.throw("Not permitted")

    # ---------------------------------------------------------
    # Access control
    # ---------------------------------------------------------
    user_roles = frappe.get_all(
        "Has Role",
        filters={
            "parent": user,
            "parenttype": "User"
        },
        pluck="role"
    )

    manager_roles = [
        "System Manager",
        "Sales Manager",
        "Call Center Export"
    ]

    has_manager_access = False

    for role in manager_roles:
        if role in user_roles:
            has_manager_access = True
            break

    is_configured_team_leader = False

    team_leader_rows = frappe.get_all(
        "Lead Agent Config",
        filters={
            "parent": "Lead Assignment Settings",
            "parenttype": "Lead Assignment Settings",
            "custom_team_leader": user
        },
        fields=["name"],
        limit_page_length=1
    )

    if team_leader_rows:
        is_configured_team_leader = True

    if not has_manager_access and not is_configured_team_leader:
        frappe.throw("Only an authorized Team Leader or Manager can preview lead assignment")

    # ---------------------------------------------------------
    # Request
    # ---------------------------------------------------------
    requested_source = (
        frappe.form_dict.get("source") or ""
    ).strip()

    today = frappe.utils.nowdate()
    now = frappe.utils.now_datetime()
    now_hour = now.hour

    settings = frappe.get_doc(
        "Lead Assignment Settings",
        "Lead Assignment Settings"
    )

    assignment_mode = settings.get("assignment_mode") or "Manual"

    start_time = str(
        settings.get("custom_assignment_start_time") or "10:00:00"
    )

    end_time = str(
        settings.get("custom_assignment_end_time") or "20:00:00"
    )

    start_parts = start_time.split(":")
    end_parts = end_time.split(":")

    start_hour = int(start_parts[0] or 10)
    end_hour = int(end_parts[0] or 20)

    within_assignment_hours = (
        now_hour >= start_hour and
        now_hour < end_hour
    )

    require_checkin = int(
        settings.get("custom_require_open_checkin") or 0
    )

    require_source = int(
        settings.get("custom_require_source_mapping") or 0
    )

    keep_unassigned = int(
        settings.get("custom_keep_unassigned") or 0
    )

    window_days = int(
        settings.get("custom_conversion_window_days") or 30
    )

    if window_days <= 0:
        window_days = 30

    status_text = (
        settings.get("custom_conversion_statuses") or "Converted"
    )

    conversion_statuses = []

    for status_value in status_text.split(","):
        clean_status = status_value.strip()

        if clean_status:
            conversion_statuses.append(clean_status)

    if not conversion_statuses:
        conversion_statuses = ["Converted"]

    today_start = today + " 00:00:00"
    today_end = today + " 23:59:59"

    performance_start_date = frappe.utils.add_days(
        today,
        -window_days
    )

    performance_start = performance_start_date + " 00:00:00"

    results = []
    best_agent = None
    best_score = None
    best_checkin = None

    # ---------------------------------------------------------
    # Evaluate configured agents
    # ---------------------------------------------------------
    for config in settings.get("agent_config") or []:
        agent = config.get("agent")

        if not agent:
            continue

        reasons = []

        employee = frappe.db.get_value(
            "Employee",
            {
                "user_id": agent
            },
            [
                "name",
                "employee_name",
                "designation",
                "status",
                "reports_to",
                "branch"
            ],
            as_dict=True
        )

        if not employee:
            reasons.append("Employee record not found")
        else:
            if employee.get("status") != "Active":
                reasons.append("Employee is not Active")

            if employee.get("designation") != "Business Executive":
                reasons.append("Employee is not a Business Executive")

        auto_enabled = int(
            config.get("custom_auto_assign_enabled") or 0
        )

        temporarily_stopped = int(
            config.get("custom_temporarily_stopped") or 0
        )

        if not auto_enabled:
            reasons.append("Auto assignment is disabled")

        if temporarily_stopped:
            stop_reason = (
                config.get("custom_stop_reason") or ""
            ).strip()

            if stop_reason:
                reasons.append(
                    "Temporarily stopped: " + stop_reason
                )
            else:
                reasons.append("Temporarily stopped")

        # -----------------------------------------------------
        # Source matching
        # -----------------------------------------------------
        allowed_source_text = (
            config.get("custom_lead_sources") or ""
        )

        allowed_sources = []
        allowed_sources_lower = []

        for source_value in allowed_source_text.split(","):
            clean_source = source_value.strip()

            if clean_source:
                allowed_sources.append(clean_source)
                allowed_sources_lower.append(
                    clean_source.lower()
                )

        source_matches = True

        if require_source:
            if not requested_source:
                source_matches = False
                reasons.append(
                    "Select a Lead Source for preview"
                )
            elif requested_source.lower() not in allowed_sources_lower:
                source_matches = False
                reasons.append(
                    "Lead Source is not mapped to this agent"
                )

        # -----------------------------------------------------
        # Check-in status
        # -----------------------------------------------------
        attendance = None
        checked_in = False
        checkin_time = None
        checkout_time = None

        if employee:
            attendance_rows = frappe.get_all(
                "Attendance",
                filters={
                    "employee": employee.get("name"),
                    "attendance_date": today,
                    "custom_check_in_time": ["is", "set"]
                },
                fields=[
                    "name",
                    "status",
                    "custom_check_in_time",
                    "custom_check_out_time"
                ],
                order_by="custom_check_in_time desc",
                limit_page_length=1
            )

            if attendance_rows:
                attendance = attendance_rows[0]
                checkin_time = attendance.get(
                    "custom_check_in_time"
                )
                checkout_time = attendance.get(
                    "custom_check_out_time"
                )

                if checkin_time and not checkout_time:
                    checked_in = True

        if require_checkin and not checked_in:
            reasons.append(
                "Agent is not currently checked in"
            )

        # -----------------------------------------------------
        # Daily assignment limit
        # -----------------------------------------------------
        today_count = frappe.db.count(
            "Lead",
            filters={
                "lead_owner": agent,
                "creation": [
                    "between",
                    [today_start, today_end]
                ]
            }
        )

        max_per_day = int(
            config.get("max_per_day") or 0
        )

        limit_reached = False

        if max_per_day > 0 and today_count >= max_per_day:
            limit_reached = True
            reasons.append("Daily assignment limit reached")

        # -----------------------------------------------------
        # Conversion performance
        # -----------------------------------------------------
        assigned_in_window = frappe.db.count(
            "Lead",
            filters={
                "lead_owner": agent,
                "creation": [
                    ">=",
                    performance_start
                ]
            }
        )

        converted_in_window = frappe.db.count(
            "Lead",
            filters={
                "lead_owner": agent,
                "status": [
                    "in",
                    conversion_statuses
                ],
                "creation": [
                    ">=",
                    performance_start
                ]
            }
        )

        conversion_rate = 0.0

        if assigned_in_window > 0:
            conversion_rate = (
                converted_in_window * 100.0
            ) / assigned_in_window

        conversion_factor = 1.0

        use_conversion = int(
            config.get("use_conversion") or 0
        )

        if use_conversion:
            if conversion_rate >= 30:
                conversion_factor = 3.0
            elif conversion_rate >= 20:
                conversion_factor = 2.0
            elif conversion_rate >= 10:
                conversion_factor = 1.5
            else:
                conversion_factor = 1.0

        share_weight = float(
            config.get("share_percent") or 1
        )

        if share_weight <= 0:
            share_weight = 1.0

        final_weight = (
            share_weight * conversion_factor
        )

        score = (
            today_count * 1.0
        ) / final_weight

        # -----------------------------------------------------
        # Final eligibility
        # -----------------------------------------------------
        eligible = True

        if assignment_mode != "Auto":
            eligible = False
            reasons.append(
                "Global assignment mode is not Auto"
            )

        if not within_assignment_hours:
            eligible = False
            reasons.append(
                "Outside assignment hours"
            )

        if not auto_enabled:
            eligible = False

        if temporarily_stopped:
            eligible = False

        if not source_matches:
            eligible = False

        if require_checkin and not checked_in:
            eligible = False

        if limit_reached:
            eligible = False

        if not employee:
            eligible = False

        if employee:
            if employee.get("status") != "Active":
                eligible = False

            if employee.get("designation") != "Business Executive":
                eligible = False

        result_row = {
            "agent": agent,
            "employee": (
                employee.get("name")
                if employee else None
            ),
            "employee_name": (
                employee.get("employee_name")
                if employee else agent
            ),
            "team_leader": config.get(
                "custom_team_leader"
            ),
            "auto_enabled": auto_enabled,
            "temporarily_stopped": temporarily_stopped,
            "stop_reason": config.get(
                "custom_stop_reason"
            ) or "",
            "allowed_sources": allowed_sources,
            "source_matches": source_matches,
            "checked_in": checked_in,
            "check_in_time": checkin_time,
            "check_out_time": checkout_time,
            "today_assigned": today_count,
            "max_per_day": max_per_day,
            "assigned_in_window": assigned_in_window,
            "converted_in_window": converted_in_window,
            "conversion_rate": round(
                conversion_rate,
                2
            ),
            "share_weight": share_weight,
            "conversion_factor": conversion_factor,
            "final_weight": round(
                final_weight,
                2
            ),
            "assignment_score": round(
                score,
                4
            ),
            "eligible": eligible,
            "reasons": reasons
        }

        results.append(result_row)

        if eligible:
            choose_agent = False

            if best_score is None:
                choose_agent = True
            elif score < best_score:
                choose_agent = True
            elif score == best_score:
                if best_checkin is None:
                    choose_agent = True
                elif checkin_time and checkin_time < best_checkin:
                    choose_agent = True

            if choose_agent:
                best_agent = result_row
                best_score = score
                best_checkin = checkin_time

    frappe.response["message"] = {
        "preview_only": 1,
        "today": today,
        "source": requested_source,
        "assignment_mode": assignment_mode,
        "assignment_start_time": start_time,
        "assignment_end_time": end_time,
        "within_assignment_hours": within_assignment_hours,
        "require_open_checkin": require_checkin,
        "require_source_mapping": require_source,
        "conversion_window_days": window_days,
        "conversion_statuses": conversion_statuses,
        "keep_unassigned": keep_unassigned,
        "configured_agents": len(results),
        "eligible_agents": len(
            [row for row in results if row.get("eligible")]
        ),
        "recommended_agent": (
            best_agent if best_agent else None
        ),
        "agents": results
    }
