"""Lead Assignment Configuration API

Original API: lead_assignment_configuration
Source modified: 2026-09-16 17:37:41.304336
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

    action = (
        frappe.form_dict.get("action") or "get"
    ).strip().lower()

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

    is_manager = False

    for role in manager_roles:
        if role in user_roles:
            is_manager = True
            break

    team_rows = frappe.get_all(
        "Lead Agent Config",
        filters={
            "parent": "Lead Assignment Settings",
            "parenttype": "Lead Assignment Settings",
            "custom_team_leader": user
        },
        fields=["name"],
        limit_page_length=1
    )

    is_team_leader = True if team_rows else False

    if not is_manager and not is_team_leader:
        frappe.throw(
            "Only an authorized Team Leader or Manager can manage lead assignment"
        )

    settings = frappe.get_doc(
        "Lead Assignment Settings",
        "Lead Assignment Settings"
    )

    today = frappe.utils.nowdate()
    today_start = today + " 00:00:00"
    today_end = today + " 23:59:59"

    # ---------------------------------------------------------
    # GET CONFIGURATION
    # ---------------------------------------------------------
    if action == "get":
        source_options = frappe.get_all(
            "Lead Source",
            pluck="name",
            order_by="name asc",
            limit_page_length=1000
        )

        agents = []

        for row in settings.get("agent_config") or []:
            if not is_manager:
                if row.get("custom_team_leader") != user:
                    continue

            employee = frappe.db.get_value(
                "Employee",
                {
                    "user_id": row.agent
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

            checked_in = False
            check_in_time = None
            check_out_time = None

            if employee:
                attendance_rows = frappe.get_all(
                    "Attendance",
                    filters={
                        "employee": employee.get("name"),
                        "attendance_date": today,
                        "custom_check_in_time": ["is", "set"]
                    },
                    fields=[
                        "custom_check_in_time",
                        "custom_check_out_time"
                    ],
                    order_by="custom_check_in_time desc",
                    limit_page_length=1
                )

                if attendance_rows:
                    attendance = attendance_rows[0]

                    check_in_time = attendance.get(
                        "custom_check_in_time"
                    )

                    check_out_time = attendance.get(
                        "custom_check_out_time"
                    )

                    if check_in_time and not check_out_time:
                        checked_in = True

            today_count = frappe.db.count(
                "Lead",
                filters={
                    "lead_owner": row.agent,
                    "creation": [
                        "between",
                        [today_start, today_end]
                    ]
                }
            )

            allowed_sources = []

            for source_value in (
                row.get("custom_lead_sources") or ""
            ).split(","):
                clean_source = source_value.strip()

                if clean_source:
                    allowed_sources.append(clean_source)

            agents.append({
                "row_name": row.name,
                "agent": row.agent,
                "employee": (
                    employee.get("name")
                    if employee else None
                ),
                "employee_name": (
                    employee.get("employee_name")
                    if employee else row.agent
                ),
                "designation": (
                    employee.get("designation")
                    if employee else None
                ),
                "employee_status": (
                    employee.get("status")
                    if employee else None
                ),
                "branch": (
                    employee.get("branch")
                    if employee else None
                ),
                "team_leader": row.get(
                    "custom_team_leader"
                ),
                "auto_enabled": int(
                    row.get(
                        "custom_auto_assign_enabled"
                    ) or 0
                ),
                "allowed_sources": allowed_sources,
                "temporarily_stopped": int(
                    row.get(
                        "custom_temporarily_stopped"
                    ) or 0
                ),
                "stop_reason": row.get(
                    "custom_stop_reason"
                ) or "",
                "share_weight": float(
                    row.get("share_percent") or 1
                ),
                "use_conversion": int(
                    row.get("use_conversion") or 0
                ),
                "max_per_day": int(
                    row.get("max_per_day") or 0
                ),
                "checked_in": checked_in,
                "check_in_time": check_in_time,
                "check_out_time": check_out_time,
                "today_assigned": today_count
            })

        frappe.response["message"] = {
            "action": "get",
            "user": user,
            "is_manager": is_manager,
            "is_team_leader": is_team_leader,
            "today": today,
            "settings": {
                "assignment_mode": settings.get(
                    "assignment_mode"
                ),
                "start_time": str(
                    settings.get(
                        "custom_assignment_start_time"
                    ) or ""
                ),
                "end_time": str(
                    settings.get(
                        "custom_assignment_end_time"
                    ) or ""
                ),
                "require_checkin": int(
                    settings.get(
                        "custom_require_open_checkin"
                    ) or 0
                ),
                "require_source_mapping": int(
                    settings.get(
                        "custom_require_source_mapping"
                    ) or 0
                ),
                "conversion_window_days": int(
                    settings.get(
                        "custom_conversion_window_days"
                    ) or 30
                ),
                "conversion_statuses": (
                    settings.get(
                        "custom_conversion_statuses"
                    ) or "Converted"
                ),
                "keep_unassigned": int(
                    settings.get(
                        "custom_keep_unassigned"
                    ) or 0
                )
            },
            "source_options": source_options,
            "agents": agents
        }

    # ---------------------------------------------------------
    # SAVE ONE AGENT
    # ---------------------------------------------------------
    elif action == "save_agent":
        agent = (
            frappe.form_dict.get("agent") or ""
        ).strip()

        if not agent:
            frappe.throw("Agent is required")

        target_row = None

        for row in settings.get("agent_config") or []:
            if row.agent == agent:
                target_row = row
                break

        if not target_row:
            frappe.throw(
                "Agent configuration was not found"
            )

        if not is_manager:
            if target_row.get(
                "custom_team_leader"
            ) != user:
                frappe.throw(
                    "You cannot edit this agent"
                )

        employee = frappe.db.get_value(
            "Employee",
            {
                "user_id": agent
            },
            [
                "name",
                "employee_name",
                "designation",
                "status"
            ],
            as_dict=True
        )

        if not employee:
            frappe.throw(
                "Active Employee mapping was not found"
            )

        if employee.get("status") != "Active":
            frappe.throw(
                "Only an Active Employee can be configured"
            )

        if employee.get("designation") != "Business Executive":
            frappe.throw(
                "Only a Business Executive can receive automatic leads"
            )

        auto_enabled = int(
            frappe.form_dict.get("auto_enabled") or 0
        )

        temporarily_stopped = int(
            frappe.form_dict.get(
                "temporarily_stopped"
            ) or 0
        )

        use_conversion = int(
            frappe.form_dict.get("use_conversion") or 0
        )

        max_per_day = int(
            frappe.form_dict.get("max_per_day") or 0
        )

        share_weight = float(
            frappe.form_dict.get("share_weight") or 1
        )

        source_text = (
            frappe.form_dict.get("lead_sources") or ""
        ).strip()

        stop_reason = (
            frappe.form_dict.get("stop_reason") or ""
        ).strip()

        requested_team_leader = (
            frappe.form_dict.get("team_leader") or ""
        ).strip()

        if max_per_day < 0:
            frappe.throw(
                "Maximum leads per day cannot be negative"
            )

        if share_weight <= 0:
            frappe.throw(
                "Share weight must be greater than zero"
            )

        clean_sources = []
        clean_sources_lower = []

        for source_value in source_text.split(","):
            clean_source = source_value.strip()

            if clean_source:
                source_lower = clean_source.lower()

                if source_lower not in clean_sources_lower:
                    if not frappe.db.exists(
                        "Lead Source",
                        clean_source
                    ):
                        frappe.throw(
                            "Invalid Lead Source: " +
                            clean_source
                        )

                    clean_sources.append(clean_source)
                    clean_sources_lower.append(
                        source_lower
                    )

        if auto_enabled and not clean_sources:
            frappe.throw(
                "Select at least one Lead Source before enabling auto assignment"
            )

        if auto_enabled and max_per_day <= 0:
            frappe.throw(
                "Set Max Leads / Day before enabling auto assignment"
            )

        if temporarily_stopped and not stop_reason:
            stop_reason = "Stopped by Team Leader"

        if not temporarily_stopped:
            stop_reason = ""

        target_row.custom_auto_assign_enabled = (
            auto_enabled
        )

        target_row.custom_lead_sources = ", ".join(
            clean_sources
        )

        target_row.custom_temporarily_stopped = (
            temporarily_stopped
        )

        target_row.custom_stop_reason = stop_reason
        target_row.share_percent = share_weight
        target_row.use_conversion = use_conversion
        target_row.max_per_day = max_per_day

        if is_manager and requested_team_leader:
            if not frappe.db.exists(
                "User",
                requested_team_leader
            ):
                frappe.throw(
                    "Invalid Team Leader User"
                )

            target_row.custom_team_leader = (
                requested_team_leader
            )

        settings.save(ignore_permissions=True)
        frappe.db.commit()

        frappe.response["message"] = {
            "action": "save_agent",
            "saved": 1,
            "agent": agent,
            "employee_name": employee.get(
                "employee_name"
            ),
            "team_leader": target_row.get(
                "custom_team_leader"
            ),
            "auto_enabled": int(
                target_row.get(
                    "custom_auto_assign_enabled"
                ) or 0
            ),
            "lead_sources": clean_sources,
            "temporarily_stopped": int(
                target_row.get(
                    "custom_temporarily_stopped"
                ) or 0
            ),
            "stop_reason": target_row.get(
                "custom_stop_reason"
            ) or "",
            "share_weight": float(
                target_row.get("share_percent") or 1
            ),
            "use_conversion": int(
                target_row.get("use_conversion") or 0
            ),
            "max_per_day": int(
                target_row.get("max_per_day") or 0
            ),
            "updated_by": user,
            "updated_on": frappe.utils.now()
        }

    else:
        frappe.throw(
            "Unsupported action: " + action
        )
