"""LIFE WATI Daily Reports API

Original API: life_wati_daily_reports
Source modified: 2026-09-15 19:37:24.496147
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

    # LIFE WATI DAILY REPORT API
    # action: attendance | doctor | preview_attendance | preview_doctor

    action = str(frappe.form_dict.get("action") or "").strip().lower()
    force_send = int(frappe.form_dict.get("force") or 0)

    branch_map = {
        "MP": "Madhapur",
        "CN": "Chandanagar",
        "GB": "Gachibowli",
        "KP": "Kukatpally",
        "BH": "Banjara Hills",
        "SN": "SR Nagar",
        "DN": "Dilsukhnagar",
        "HN": "Himayathnagar",
        "VW": "Vijayawada",
        "VZ": "Vizag",
        "NLR": "Nellore",
        "HO": "Head Office"
    }
    branch_codes = ["MP","CN","GB","KP","BH","SN","DN","HN","VW","VZ","NLR","HO"]
    today = frappe.utils.nowdate()
    report_date = frappe.utils.formatdate(today, "dd-MMM-yy")

    # Reuse existing LIFE WATI configuration
    enabled = 1
    tenant_id = "1013094"
    # Add additional recipients here in future.
    report_mobiles = [
        "919822817266",
        "919032590901",
        "919604238978",
        "917416026677"
    ]

    mobile = report_mobiles[0]

    token = ""

    source_script = frappe.db.get_value(
        "Server Script",
        "WhatsApp – Lead Appointment Booked Confirmation",
        "script"
    ) or ""

    quote_character = chr(34)
    token_marker = "wati_token = " + quote_character

    if token_marker in source_script:
        token_part = source_script.split(token_marker, 1)[1]
        token = token_part.split(quote_character, 1)[0].strip()

    clean_mobile = ""
    for character in mobile:
        if character.isdigit():
            clean_mobile = clean_mobile + character
    mobile = clean_mobile
    if len(mobile) == 10:
        mobile = "91" + mobile

    if not token:
        frappe.response["message"] = {
            "status": "failed",
            "message": "Existing WATI token was not found."
        }
    else:
        report_type = "Attendance" if "attendance" in action else "Doctor IN OUT"
        report_key = today + "-" + ("ATTENDANCE" if report_type == "Attendance" else "DOCTOR")
        template_name = ""
        parameters = []
        summary = ""
        html = ""

        if report_type == "Attendance":
            employees = frappe.get_all(
                "Employee",
                filters={"status":"Active", "branch":["in", list(branch_map.values())]},
                fields=["name","employee_name","branch","designation","default_shift"],
                limit_page_length=1000
            )
            attendance_rows = frappe.get_all(
                "Attendance",
                filters={"attendance_date":today},
                fields=["employee","employee_name","status","shift","in_time","out_time","late_entry"],
                limit_page_length=1000
            )
            att_by_employee = {}
            for att in attendance_rows:
                att_by_employee[att.get("employee")] = att

            # Get submitted daily Employee Shift Assignments
            assignment_rows = frappe.get_all(
                "Shift Assignment",
                filters={
                    "start_date":["<=",today],
                    "status":"Active",
                    "docstatus":1
                },
                fields=[
                    "name","employee","employee_name","shift_type",
                    "start_date","end_date"
                ],
                order_by="start_date desc",
                limit_page_length=5000
            )

            assignment_by_employee = {}
            for assignment in assignment_rows:
                assignment_end = assignment.get("end_date")
                if not assignment_end or str(assignment_end) >= str(today):
                    employee_id = assignment.get("employee")
                    if employee_id and employee_id not in assignment_by_employee:
                        assignment_by_employee[employee_id] = assignment

            shift_names = []
            for assignment in assignment_by_employee.values():
                shift_name = assignment.get("shift_type")
                if shift_name and shift_name not in shift_names:
                    shift_names.append(shift_name)

            shift_details = {}
            if shift_names:
                shift_rows = frappe.get_all(
                    "Shift Type",
                    filters={"name":["in",shift_names]},
                    fields=[
                        "name","start_time","end_time",
                        "late_entry_grace_period"
                    ],
                    limit_page_length=500
                )
                for shift_row in shift_rows:
                    shift_details[shift_row.get("name")] = shift_row

            total_all = 0
            present_all = 0
            absent_all = 0
            ni_all = 0
            week_off_all = 0
            late_all = 0

            full_branches = []
            absent_lines = []
            no_info_lines = []
            late_lines = []
            table_rows = ""

            for code in branch_codes:
                branch = branch_map.get(code)
                branch_employees = []

                for emp in employees:
                    if emp.get("branch") == branch:
                        branch_employees.append(emp)

                total = 0
                present = 0
                absent = 0
                no_info = 0
                week_off = 0
                late_count = 0

                for emp in branch_employees:
                    employee_id = emp.get("name")
                    employee_name = str(emp.get("employee_name") or "")
                    designation = str(emp.get("designation") or "MISSING")

                    att = att_by_employee.get(employee_id)
                    assignment = assignment_by_employee.get(employee_id)
                    assigned_shift = ""
                    shift_info = None

                    if assignment:
                        assigned_shift = str(
                            assignment.get("shift_type") or ""
                        )
                        shift_info = shift_details.get(assigned_shift)

                    if assigned_shift == "Week Off":
                        week_off = week_off + 1
                        week_off_all = week_off_all + 1
                        continue

                    total = total + 1

                    if not att:
                        no_info = no_info + 1
                        no_info_lines.append(
                            code + " - " + employee_name
                            + " (" + designation + ")"
                            + (
                                " | Shift: " + assigned_shift
                                if assigned_shift
                                else " | Shift: Not Assigned"
                            )
                        )
                        continue

                    status = str(att.get("status") or "No Info")

                    if status in ["Present","Work From Home","Half Day"]:
                        present = present + 1
                    elif status in ["Absent","On Leave"]:
                        absent = absent + 1
                        absent_lines.append(
                            code + " - " + employee_name
                            + " (" + designation + ")"
                            + " | " + status
                        )
                    else:
                        no_info = no_info + 1
                        no_info_lines.append(
                            code + " - " + employee_name
                            + " (" + designation + ")"
                            + " | " + status
                        )

                    # Calculate late only from submitted Shift Assignment.
                    # Never use Attendance.shift = Flexible Shift.
                    if (
                        status in ["Present","Work From Home","Half Day"]
                        and assigned_shift
                        and assigned_shift != "Week Off"
                        and shift_info
                        and shift_info.get("start_time") is not None
                        and att.get("in_time")
                    ):
                        shift_start = shift_info.get("start_time")
                        start_seconds = 0

                        shift_parts = str(shift_start).split(":")
                        if len(shift_parts) >= 2:
                            start_seconds = (
                                int(shift_parts[0]) * 3600
                                + int(shift_parts[1]) * 60
                            )

                        grace_minutes = int(
                            shift_info.get(
                                "late_entry_grace_period"
                            ) or 0
                        )

                        in_datetime = frappe.utils.get_datetime(
                            att.get("in_time")
                        )
                        in_seconds = (
                            in_datetime.hour * 3600
                            + in_datetime.minute * 60
                            + in_datetime.second
                        )

                        late_seconds = (
                            in_seconds
                            - start_seconds
                            - (grace_minutes * 60)
                        )

                        if late_seconds > 0:
                            late_minutes = int(
                                (late_seconds + 59) / 60
                            )
                            late_count = late_count + 1
                            late_all = late_all + 1

                            in_text = frappe.utils.format_datetime(
                                att.get("in_time"),
                                "hh:mm a"
                            )

                            late_lines.append(
                                code + " - " + employee_name
                                + " (" + designation + ")"
                                + " | " + assigned_shift
                                + " | IN " + in_text
                                + " | " + str(late_minutes)
                                + " min late"
                            )

                percentage = (
                    round((present * 100.0 / total), 1)
                    if total else 0
                )

                if total and present == total:
                    full_branches.append(code)

                total_all = total_all + total
                present_all = present_all + present
                absent_all = absent_all + absent
                ni_all = ni_all + no_info

                row_class = ""
                if percentage == 100:
                    row_class = " class='full-row'"

                table_rows = (
                    table_rows
                    + "<tr" + row_class + ">"
                    + "<td class='branch-code'>" + code + "</td>"
                    + "<td>" + str(total) + "</td>"
                    + "<td class='present-value'>" + str(present) + "</td>"
                    + "<td class='absent-value'>" + str(absent) + "</td>"
                    + "<td class='ni-value'>" + str(no_info) + "</td>"
                    + "<td>" + str(late_count) + "</td>"
                    + "<td><strong>" + str(percentage) + "%</strong></td>"
                    + "</tr>"
                )

            total_percent = (
                round((present_all * 100.0 / total_all), 1)
                if total_all else 0
            )

            full_text = (
                ", ".join(full_branches)
                if full_branches else "NIL"
            )

            absent_html = (
                "<div class='detail-line absent-line'>"
                + "</div><div class='detail-line absent-line'>".join(
                    absent_lines
                )
                + "</div>"
                if absent_lines
                else "<div class='nil-box'>NIL</div>"
            )

            no_info_html = (
                "<div class='detail-line ni-line'>"
                + "</div><div class='detail-line ni-line'>".join(
                    no_info_lines
                )
                + "</div>"
                if no_info_lines
                else "<div class='nil-box'>NIL</div>"
            )

            late_html = (
                "<div class='detail-line late-line'>"
                + "</div><div class='detail-line late-line'>".join(
                    late_lines
                )
                + "</div>"
                if late_lines
                else "<div class='nil-box'>NIL</div>"
            )

            html = (
                "<div class='report-header'>"
                + "<div class='brand-mark'>LIFE</div>"
                + "<div class='header-content'>"
                + "<div class='life-title'>DAILY ATTENDANCE REPORT</div>"
                + "<div class='life-sub'>"
                + report_date + " | Report Time: 11:59 AM"
                + "</div></div></div>"
            )

            html = html + (
                "<div class='summary-grid'>"
                + "<div class='summary-card total-card'>"
                + "<span>Total Staff</span><strong>"
                + str(total_all) + "</strong></div>"
                + "<div class='summary-card present-card'>"
                + "<span>Present</span><strong>"
                + str(present_all) + "</strong></div>"
                + "<div class='summary-card absent-card'>"
                + "<span>Absent / Leave</span><strong>"
                + str(absent_all) + "</strong></div>"
                + "<div class='summary-card ni-card'>"
                + "<span>No Info</span><strong>"
                + str(ni_all) + "</strong></div>"
                + "<div class='summary-card late-card'>"
                + "<span>Late</span><strong>"
                + str(late_all) + "</strong></div>"
                + "<div class='summary-card percent-card'>"
                + "<span>Attendance</span><strong>"
                + str(total_percent) + "%</strong></div>"
                + "</div>"
            )

            html = html + (
                "<div class='table-title'>BRANCH-WISE ATTENDANCE</div>"
                + "<table class='attendance-table'>"
                + "<thead><tr>"
                + "<th>BRANCH</th><th>TOTAL</th><th>PRESENT</th>"
                + "<th>ABSENT</th><th>NO INFO</th><th>LATE</th>"
                + "<th>ATTENDANCE</th>"
                + "</tr></thead><tbody>"
                + table_rows
                + "<tr class='total-row'>"
                + "<td>TOTAL</td>"
                + "<td>" + str(total_all) + "</td>"
                + "<td>" + str(present_all) + "</td>"
                + "<td>" + str(absent_all) + "</td>"
                + "<td>" + str(ni_all) + "</td>"
                + "<td>" + str(late_all) + "</td>"
                + "<td>" + str(total_percent) + "%</td>"
                + "</tr></tbody></table>"
            )

            html = html + (
                "<div class='section absent-section'>"
                + "<div class='section-heading'>ABSENT / LEAVE — "
                + str(absent_all) + "</div>"
                + "<div class='section-body'>" + absent_html + "</div>"
                + "</div>"
            )

            html = html + (
                "<div class='section late-section'>"
                + "<div class='section-heading'>LATE ENTRY — "
                + str(late_all) + "</div>"
                + "<div class='section-note'>"
                + "Late minutes are calculated from the submitted "
                + "Employee Shift Assignment."
                + "</div>"
                + "<div class='section-body'>" + late_html + "</div>"
                + "</div>"
            )

            html = html + (
                "<div class='section ni-section'>"
                + "<div class='section-heading'>NO INFORMATION — "
                + str(ni_all) + "</div>"
                + "<div class='section-body'>" + no_info_html + "</div>"
                + "</div>"
            )

            html = html + (
                "<div class='report-footer'>"
                + "<strong>Full attendance branches:</strong> "
                + full_text
                + " &nbsp; | &nbsp; "
                + "<strong>Week Off excluded:</strong> "
                + str(week_off_all)
                + "<br>P = Present | NI = No attendance information"
                + " | No assigned shift = Late not calculated"
                + "</div>"
            )

            # LIFE ATTENDANCE COMPACT EMPLOYEE LIST V2
            yesterday = frappe.utils.add_days(today, -1)
            yesterday_text = frappe.utils.formatdate(
                yesterday,
                "dd-MMM-yy"
            )

            employee_ids = []

            for employee_row in employees:
                if employee_row.get("name"):
                    employee_ids.append(employee_row.get("name"))

            yesterday_attendance_rows = []

            if employee_ids:
                yesterday_attendance_rows = frappe.get_all(
                    "Attendance",
                    filters={
                        "employee": ["in", employee_ids],
                        "attendance_date": yesterday,
                        "docstatus": ["!=", 2]
                    },
                    fields=[
                        "employee",
                        "employee_name",
                        "status",
                        "in_time",
                        "out_time"
                    ],
                    limit_page_length=2000
                )

            yesterday_by_employee = {}

            for yesterday_row in yesterday_attendance_rows:
                yesterday_by_employee[
                    yesterday_row.get("employee")
                ] = yesterday_row

            employee_lines = []

            for code in branch_codes:
                employee_branch = branch_map.get(code)
                branch_employee_rows = []

                for employee_row in employees:
                    if employee_row.get("branch") == employee_branch:
                        branch_employee_rows.append(employee_row)

                branch_employee_rows = sorted(
                    branch_employee_rows,
                    key=lambda row: str(
                        row.get("employee_name") or ""
                    ).lower()
                )

                for employee_row in branch_employee_rows:
                    employee_id = employee_row.get("name")
                    employee_name = str(
                        employee_row.get("employee_name") or employee_id
                    )
                    designation = str(
                        employee_row.get("designation") or "MISSING"
                    )

                    today_row = att_by_employee.get(employee_id)
                    yesterday_row = yesterday_by_employee.get(employee_id)

                    today_status = "No Info"
                    today_in = "—"
                    today_out = "—"

                    if today_row:
                        today_status = str(
                            today_row.get("status") or "No Info"
                        )

                        if today_row.get("in_time"):
                            today_in = frappe.utils.format_datetime(
                                today_row.get("in_time"),
                                "hh:mm a"
                            )

                        if today_row.get("out_time"):
                            today_out = frappe.utils.format_datetime(
                                today_row.get("out_time"),
                                "hh:mm a"
                            )

                    yesterday_status = "No Info"
                    yesterday_in = "—"
                    yesterday_out = "—"

                    if yesterday_row:
                        yesterday_status = str(
                            yesterday_row.get("status") or "No Info"
                        )

                        if yesterday_row.get("in_time"):
                            yesterday_in = frappe.utils.format_datetime(
                                yesterday_row.get("in_time"),
                                "hh:mm a"
                            )

                        if yesterday_row.get("out_time"):
                            yesterday_out = frappe.utils.format_datetime(
                                yesterday_row.get("out_time"),
                                "hh:mm a"
                            )

                    line_class = "ni-line"

                    if today_status in [
                        "Present",
                        "Work From Home",
                        "Half Day"
                    ]:
                        line_class = "present-line"
                    elif today_status in ["Absent", "On Leave"]:
                        line_class = "absent-line"

                    employee_lines.append(
                        "<div class=\"detail-line "
                        + line_class
                        + "\">"
                        + "<strong>"
                        + code
                        + " - "
                        + employee_name
                        + "</strong>"
                        + " ("
                        + designation
                        + ")"
                        + " | <strong>Today:</strong> "
                        + today_status
                        + " | IN "
                        + today_in
                        + " | OUT "
                        + today_out
                        + "<br><span class=\"yesterday-line\"><strong>Yesterday:</strong> "
                        + yesterday_status
                        + " | IN "
                        + yesterday_in
                        + " | OUT "
                        + yesterday_out
                        + "</span></div>"
                    )

            employee_lines_html = (
                "".join(employee_lines)
                if employee_lines
                else "<div class=\"nil-box\">NIL</div>"
            )

            html = html + (
                "<div class=\"section employee-comparison-section\">"
                + "<div class=\"section-heading\">"
                + "EMPLOYEE-WISE ATTENDANCE"
                + "</div>"
                + "<div class=\"section-note\">"
                + "Today "
                + report_date
                + " compared with Yesterday "
                + yesterday_text
                + "</div>"
                + "<div class=\"section-body compact-employee-list\">"
                + employee_lines_html
                + "</div>"
                + "</div>"
            )

            summary = (
                "Present " + str(present_all) + "/" + str(total_all)
                + "; Absent/Leave " + str(absent_all)
                + "; NI " + str(ni_all)
                + "; Late " + str(late_all)
                + "; " + str(total_percent) + "%"
            )

            template_name = "life_daily_attendance_report_v2"
            parameters = [
                {"name":"report_date","value":report_date},
                {
                    "name":"present",
                    "value":str(present_all) + "/" + str(total_all)
                },
                {"name":"absent","value":str(absent_all)},
                {"name":"no_info","value":str(ni_all)},
                {"name":"percent","value":str(total_percent)},
                {"name":"full_branches","value":full_text}
            ]

        else:
            yesterday = frappe.utils.add_days(today, -1)
            yesterday_text = frappe.utils.formatdate(
                yesterday,
                "dd-MMM-yy"
            )

            doctors = frappe.get_all(
                "Employee",
                filters={
                    "status": "Active",
                    "branch": ["in", list(branch_map.values())],
                    "designation": [
                        "in",
                        ["Doctor", "Consultant Doctor"]
                    ]
                },
                fields=[
                    "name",
                    "employee_name",
                    "branch",
                    "designation"
                ],
                order_by="branch asc, employee_name asc",
                limit_page_length=500
            )

            employee_ids = []
            for doctor in doctors:
                if doctor.get("name"):
                    employee_ids.append(doctor.get("name"))

            attendance_rows = []

            if employee_ids:
                attendance_rows = frappe.get_all(
                    "Attendance",
                    filters={
                        "employee": ["in", employee_ids],
                        "attendance_date": [
                            "between",
                            [yesterday, today]
                        ]
                    },
                    fields=[
                        "employee",
                        "employee_name",
                        "attendance_date",
                        "status",
                        "in_time",
                        "out_time"
                    ],
                    limit_page_length=2000
                )

            today_attendance = {}
            yesterday_attendance = {}

            for attendance in attendance_rows:
                attendance_date = str(
                    attendance.get("attendance_date") or ""
                )

                if attendance_date == str(today):
                    today_attendance[
                        attendance.get("employee")
                    ] = attendance

                elif attendance_date == str(yesterday):
                    yesterday_attendance[
                        attendance.get("employee")
                    ] = attendance

            assignment_rows = []

            if employee_ids:
                assignment_rows = frappe.get_all(
                    "Shift Assignment",
                    filters={
                        "employee": ["in", employee_ids],
                        "start_date": ["<=", today],
                        "status": "Active",
                        "docstatus": 1
                    },
                    fields=[
                        "name",
                        "employee",
                        "shift_type",
                        "start_date",
                        "end_date"
                    ],
                    order_by="start_date desc",
                    limit_page_length=2000
                )

            assignment_by_employee = {}

            for assignment in assignment_rows:
                employee_id = assignment.get("employee")
                assignment_end = assignment.get("end_date")

                is_valid = (
                    not assignment_end
                    or str(assignment_end) >= str(today)
                )

                if (
                    employee_id
                    and is_valid
                    and employee_id not in assignment_by_employee
                ):
                    assignment_by_employee[
                        employee_id
                    ] = assignment

            shift_names = []

            for assignment in assignment_by_employee.values():
                shift_name = assignment.get("shift_type")

                if shift_name and shift_name not in shift_names:
                    shift_names.append(shift_name)

            shift_details = {}

            if shift_names:
                shift_rows = frappe.get_all(
                    "Shift Type",
                    filters={"name": ["in", shift_names]},
                    fields=[
                        "name",
                        "start_time",
                        "end_time",
                        "late_entry_grace_period",
                        "early_exit_grace_period"
                    ],
                    limit_page_length=200
                )

                for shift_row in shift_rows:
                    shift_details[
                        shift_row.get("name")
                    ] = shift_row

            present_statuses = [
                "Present",
                "Work From Home",
                "Half Day"
            ]

            on_duty_branches = []
            no_doctor_codes = []
            late_lines = []
            early_lines = []
            absent_lines = []
            no_info_lines = []
            week_off_lines = []
            doctor_cards = ""

            late_count = 0
            early_count = 0
            absent_count = 0
            no_info_count = 0
            week_off_count = 0

            for code in branch_codes:
                branch = branch_map.get(code)
                branch_doctors = []

                for doctor in doctors:
                    if doctor.get("branch") == branch:
                        branch_doctors.append(doctor)

                if not branch_doctors:
                    no_doctor_codes.append(code)

                    doctor_cards = doctor_cards + (
                        "<div class=\"doctor-card no-doctor-card\">"
                        + "<div class=\"doctor-card-head\">"
                        + "<span class=\"doctor-branch\">"
                        + code
                        + "</span>"
                        + "<span class=\"doctor-name\">NO DOCTOR</span>"
                        + "</div>"
                        + "<div class=\"doctor-empty\">"
                        + branch
                        + "</div>"
                        + "</div>"
                    )

                    continue

                branch_on_duty = 0

                for doctor in branch_doctors:
                    employee_id = doctor.get("name")
                    employee_name = str(
                        doctor.get("employee_name") or "MISSING"
                    )
                    designation = str(
                        doctor.get("designation") or "Doctor"
                    )

                    today_att = today_attendance.get(employee_id)
                    yesterday_att = yesterday_attendance.get(employee_id)
                    assignment = assignment_by_employee.get(employee_id)

                    assigned_shift = ""

                    if assignment:
                        assigned_shift = str(
                            assignment.get("shift_type") or ""
                        )

                    shift_info = shift_details.get(assigned_shift)

                    today_status = (
                        str(today_att.get("status") or "No Info")
                        if today_att
                        else "No Info"
                    )

                    if assigned_shift == "Week Off":
                        display_status = "Week Off"
                        week_off_count = week_off_count + 1

                        week_off_lines.append(
                            code + " / " + employee_name
                        )

                    elif today_status in present_statuses:
                        display_status = today_status
                        branch_on_duty = 1

                    elif today_status in ["Absent", "On Leave"]:
                        display_status = today_status
                        absent_count = absent_count + 1

                        absent_lines.append(
                            code
                            + " / "
                            + employee_name
                            + " / "
                            + today_status
                        )

                    else:
                        display_status = "No Info"
                        no_info_count = no_info_count + 1

                        no_info_lines.append(
                            code
                            + " / "
                            + employee_name
                        )

                    today_in = "NI"
                    today_out = "NI"
                    yesterday_in = "NI"
                    yesterday_out = "NI"
                    yesterday_status = "No Info"

                    if today_att and today_att.get("in_time"):
                        today_in = frappe.utils.format_datetime(
                            today_att.get("in_time"),
                            "hh:mm a"
                        )

                    valid_today_out = False

                    if (
                        today_att
                        and today_att.get("in_time")
                        and today_att.get("out_time")
                    ):
                        today_in_datetime = frappe.utils.get_datetime(
                            today_att.get("in_time")
                        )
                        today_out_datetime = frappe.utils.get_datetime(
                            today_att.get("out_time")
                        )

                        worked_seconds = (
                            today_out_datetime
                            - today_in_datetime
                        ).total_seconds()

                        # Ignore duplicate biometric punches.
                        # OUT must be at least 5 minutes after IN.
                        if worked_seconds >= 300:
                            valid_today_out = True
                            today_out = frappe.utils.format_datetime(
                                today_att.get("out_time"),
                                "hh:mm a"
                            )

                    if yesterday_att:
                        yesterday_status = str(
                            yesterday_att.get("status") or "No Info"
                        )

                        if yesterday_att.get("in_time"):
                            yesterday_in = (
                                frappe.utils.format_datetime(
                                    yesterday_att.get("in_time"),
                                    "hh:mm a"
                                )
                            )

                        if yesterday_att.get("out_time"):
                            yesterday_out = (
                                frappe.utils.format_datetime(
                                    yesterday_att.get("out_time"),
                                    "hh:mm a"
                                )
                            )

                    late_minutes = 0
                    early_minutes = 0

                    if (
                        assigned_shift
                        and assigned_shift != "Week Off"
                        and shift_info
                        and today_status in present_statuses
                    ):
                        if (
                            today_att
                            and today_att.get("in_time")
                            and shift_info.get("start_time") is not None
                        ):
                            start_parts = str(
                                shift_info.get("start_time")
                            ).split(":")

                            if len(start_parts) >= 2:
                                start_seconds = (
                                    int(start_parts[0]) * 3600
                                    + int(start_parts[1]) * 60
                                )

                                grace_minutes = int(
                                    shift_info.get(
                                        "late_entry_grace_period"
                                    ) or 0
                                )

                                in_datetime = frappe.utils.get_datetime(
                                    today_att.get("in_time")
                                )

                                in_seconds = (
                                    in_datetime.hour * 3600
                                    + in_datetime.minute * 60
                                    + in_datetime.second
                                )

                                late_seconds = (
                                    in_seconds
                                    - start_seconds
                                    - (grace_minutes * 60)
                                )

                                if late_seconds > 0:
                                    late_minutes = int(
                                        (late_seconds + 59) / 60
                                    )

                                    late_count = late_count + 1

                                    late_lines.append(
                                        code
                                        + " / "
                                        + employee_name
                                        + " / "
                                        + str(late_minutes)
                                        + " min"
                                    )

                        if (
                            today_att
                            and valid_today_out
                            and today_att.get("out_time")
                            and shift_info.get("end_time") is not None
                        ):
                            end_parts = str(
                                shift_info.get("end_time")
                            ).split(":")

                            if len(end_parts) >= 2:
                                end_seconds = (
                                    int(end_parts[0]) * 3600
                                    + int(end_parts[1]) * 60
                                )

                                early_grace = int(
                                    shift_info.get(
                                        "early_exit_grace_period"
                                    ) or 0
                                )

                                out_datetime = frappe.utils.get_datetime(
                                    today_att.get("out_time")
                                )

                                out_seconds = (
                                    out_datetime.hour * 3600
                                    + out_datetime.minute * 60
                                    + out_datetime.second
                                )

                                early_seconds = (
                                    end_seconds
                                    - out_seconds
                                    - (early_grace * 60)
                                )

                                if early_seconds > 0:
                                    early_minutes = int(
                                        (early_seconds + 59) / 60
                                    )

                                    early_count = early_count + 1

                                    early_lines.append(
                                        code
                                        + " / "
                                        + employee_name
                                        + " / "
                                        + str(early_minutes)
                                        + " min"
                                    )

                    if branch_on_duty:
                        if code not in on_duty_branches:
                            on_duty_branches.append(code)

                    status_class = "status-ni"

                    if display_status in present_statuses:
                        status_class = "status-present"
                    elif display_status in ["Absent", "On Leave"]:
                        status_class = "status-absent"
                    elif display_status == "Week Off":
                        status_class = "status-weekoff"

                    late_badge = ""

                    if late_minutes > 0:
                        late_badge = (
                            "<span class=\"time-alert\">"
                            + str(late_minutes)
                            + " min late</span>"
                        )

                    early_badge = ""

                    if early_minutes > 0:
                        early_badge = (
                            "<span class=\"time-alert\">"
                            + str(early_minutes)
                            + " min early</span>"
                        )

                    shift_display = (
                        assigned_shift
                        if assigned_shift
                        else "Shift Not Assigned"
                    )

                    doctor_cards = doctor_cards + (
                        "<div class=\"doctor-card\">"
                        + "<div class=\"doctor-card-head\">"
                        + "<span class=\"doctor-branch\">"
                        + code
                        + "</span>"
                        + "<div class=\"doctor-identity\">"
                        + "<div class=\"doctor-name\">"
                        + employee_name
                        + "</div>"
                        + "<div class=\"doctor-designation\">"
                        + designation
                        + " | "
                        + branch
                        + "</div>"
                        + "</div>"
                        + "<span class=\"doctor-status "
                        + status_class
                        + "\">"
                        + display_status
                        + "</span>"
                        + "</div>"
                        + "<div class=\"doctor-shift\">"
                        + "<strong>Assigned Shift:</strong> "
                        + shift_display
                        + "</div>"
                        + "<table class=\"doctor-time-table\">"
                        + "<thead><tr>"
                        + "<th>DAY</th>"
                        + "<th>IN</th>"
                        + "<th>OUT</th>"
                        + "<th>STATUS</th>"
                        + "</tr></thead>"
                        + "<tbody>"
                        + "<tr class=\"today-row\">"
                        + "<td>Today<br><small>"
                        + report_date
                        + "</small></td>"
                        + "<td>"
                        + today_in
                        + "<br>"
                        + late_badge
                        + "</td>"
                        + "<td>"
                        + today_out
                        + "<br>"
                        + early_badge
                        + "</td>"
                        + "<td>"
                        + display_status
                        + "</td>"
                        + "</tr>"
                        + "<tr>"
                        + "<td>Yesterday<br><small>"
                        + yesterday_text
                        + "</small></td>"
                        + "<td>"
                        + yesterday_in
                        + "</td>"
                        + "<td>"
                        + yesterday_out
                        + "</td>"
                        + "<td>"
                        + yesterday_status
                        + "</td>"
                        + "</tr>"
                        + "</tbody></table>"
                        + "</div>"
                    )

            # LIFE DOCTOR COMPACT EMPLOYEE LIST V2
            doctor_compact_lines = []

            for doctor_employee in doctors:
                doctor_id = doctor_employee.get("name")
                doctor_name = str(
                    doctor_employee.get("employee_name") or doctor_id
                )
                doctor_branch = str(
                    doctor_employee.get("branch") or ""
                )
                doctor_designation = str(
                    doctor_employee.get("designation") or "Doctor"
                )

                doctor_code = ""

                for branch_code in branch_codes:
                    if branch_map.get(branch_code) == doctor_branch:
                        doctor_code = branch_code
                        break

                doctor_today = today_attendance.get(doctor_id)
                doctor_yesterday = yesterday_attendance.get(doctor_id)

                doctor_today_status = "No Info"
                doctor_today_in = "—"
                doctor_today_out = "—"

                if doctor_today:
                    doctor_today_status = str(
                        doctor_today.get("status") or "No Info"
                    )

                    if doctor_today.get("in_time"):
                        doctor_today_in = frappe.utils.format_datetime(
                            doctor_today.get("in_time"),
                            "hh:mm a"
                        )

                    if doctor_today.get("out_time"):
                        today_out_datetime = frappe.utils.get_datetime(
                            doctor_today.get("out_time")
                        )

                        today_in_datetime = None

                        if doctor_today.get("in_time"):
                            today_in_datetime = frappe.utils.get_datetime(
                                doctor_today.get("in_time")
                            )

                        valid_today_out = True

                        if today_in_datetime:
                            worked_seconds = (
                                today_out_datetime
                                - today_in_datetime
                            ).total_seconds()

                            if worked_seconds < 300:
                                valid_today_out = False

                        if valid_today_out:
                            doctor_today_out = (
                                frappe.utils.format_datetime(
                                    doctor_today.get("out_time"),
                                    "hh:mm a"
                                )
                            )

                doctor_yesterday_status = "No Info"
                doctor_yesterday_in = "—"
                doctor_yesterday_out = "—"

                if doctor_yesterday:
                    doctor_yesterday_status = str(
                        doctor_yesterday.get("status") or "No Info"
                    )

                    if doctor_yesterday.get("in_time"):
                        doctor_yesterday_in = (
                            frappe.utils.format_datetime(
                                doctor_yesterday.get("in_time"),
                                "hh:mm a"
                            )
                        )

                    if doctor_yesterday.get("out_time"):
                        yesterday_out_datetime = (
                            frappe.utils.get_datetime(
                                doctor_yesterday.get("out_time")
                            )
                        )

                        yesterday_in_datetime = None

                        if doctor_yesterday.get("in_time"):
                            yesterday_in_datetime = (
                                frappe.utils.get_datetime(
                                    doctor_yesterday.get("in_time")
                                )
                            )

                        valid_yesterday_out = True

                        if yesterday_in_datetime:
                            yesterday_worked_seconds = (
                                yesterday_out_datetime
                                - yesterday_in_datetime
                            ).total_seconds()

                            if yesterday_worked_seconds < 300:
                                valid_yesterday_out = False

                        if valid_yesterday_out:
                            doctor_yesterday_out = (
                                frappe.utils.format_datetime(
                                    doctor_yesterday.get("out_time"),
                                    "hh:mm a"
                                )
                            )

                doctor_line_class = "ni-line"

                if doctor_today_status in [
                    "Present",
                    "Work From Home",
                    "Half Day"
                ]:
                    doctor_line_class = "present-line"
                elif doctor_today_status in ["Absent", "On Leave"]:
                    doctor_line_class = "absent-line"

                doctor_compact_lines.append(
                    "<div class=\"detail-line "
                    + doctor_line_class
                    + "\">"
                    + "<strong>"
                    + doctor_code
                    + " - "
                    + doctor_name
                    + "</strong>"
                    + " ("
                    + doctor_designation
                    + ")"
                    + " | <strong>Today:</strong> "
                    + doctor_today_status
                    + " | IN "
                    + doctor_today_in
                    + " | OUT "
                    + doctor_today_out
                    + " | <strong>Yesterday:</strong> "
                    + doctor_yesterday_status
                    + " | IN "
                    + doctor_yesterday_in
                    + " | OUT "
                    + doctor_yesterday_out
                    + "</span></div>"
                )

            doctor_compact_html = (
                "".join(doctor_compact_lines)
                if doctor_compact_lines
                else "<div class=\"nil-box\">NIL</div>"
            )

            on_duty = len(on_duty_branches)

            no_doctor_text = (
                ", ".join(no_doctor_codes)
                if no_doctor_codes
                else "NIL"
            )

            late_html = (
                "<div class=\"detail-line late-line\">"
                + "</div><div class=\"detail-line late-line\">".join(
                    late_lines
                )
                + "</div>"
                if late_lines
                else "<div class=\"nil-box\">NIL</div>"
            )

            early_html = (
                "<div class=\"detail-line early-line\">"
                + "</div><div class=\"detail-line early-line\">".join(
                    early_lines
                )
                + "</div>"
                if early_lines
                else "<div class=\"nil-box\">NIL</div>"
            )

            absent_html = (
                "<div class=\"detail-line absent-line\">"
                + "</div><div class=\"detail-line absent-line\">".join(
                    absent_lines
                )
                + "</div>"
                if absent_lines
                else "<div class=\"nil-box\">NIL</div>"
            )

            no_info_html = (
                "<div class=\"detail-line ni-line\">"
                + "</div><div class=\"detail-line ni-line\">".join(
                    no_info_lines
                )
                + "</div>"
                if no_info_lines
                else "<div class=\"nil-box\">NIL</div>"
            )

            html = (
                "<div class=\"report-header doctor-report-header\">"
                + "<div class=\"brand-mark\">LIFE</div>"
                + "<div class=\"header-content\">"
                + "<div class=\"life-title\">"
                + "DOCTOR IN / OUT REPORT"
                + "</div>"
                + "<div class=\"life-sub\">"
                + report_date
                + " | Today and Yesterday Comparison"
                + "</div></div></div>"
            )

            html = html + (
                "<div class=\"summary-grid doctor-summary\">"
                + "<div class=\"summary-card present-card\">"
                + "<span>On Duty</span><strong>"
                + str(on_duty)
                + "/11</strong></div>"
                + "<div class=\"summary-card late-card\">"
                + "<span>Late IN</span><strong>"
                + str(late_count)
                + "</strong></div>"
                + "<div class=\"summary-card early-card\">"
                + "<span>Early OUT</span><strong>"
                + str(early_count)
                + "</strong></div>"
                + "<div class=\"summary-card absent-card\">"
                + "<span>Absent / Leave</span><strong>"
                + str(absent_count)
                + "</strong></div>"
                + "<div class=\"summary-card ni-card\">"
                + "<span>No Info</span><strong>"
                + str(no_info_count)
                + "</strong></div>"
                + "<div class=\"summary-card total-card\">"
                + "<span>No Doctor</span><strong>"
                + str(len(no_doctor_codes))
                + "</strong></div>"
                + "</div>"
            )

            html = html + (
                "<div class=\"table-title\">"
                + "EMPLOYEE-WISE DOCTOR IN / OUT"
                + "</div>"
                + "<div class=\"section-body compact-employee-list\">"
                + doctor_compact_html
                + "</div>"
            )

            html = html + (
                "<div class=\"doctor-detail-grid\">"
                + "<div class=\"section late-section\">"
                + "<div class=\"section-heading\">LATE IN — "
                + str(late_count)
                + "</div>"
                + "<div class=\"section-body\">"
                + late_html
                + "</div></div>"
                + "<div class=\"section early-section\">"
                + "<div class=\"section-heading\">EARLY OUT — "
                + str(early_count)
                + "</div>"
                + "<div class=\"section-body\">"
                + early_html
                + "</div></div>"
                + "<div class=\"section absent-section\">"
                + "<div class=\"section-heading\">ABSENT / LEAVE — "
                + str(absent_count)
                + "</div>"
                + "<div class=\"section-body\">"
                + absent_html
                + "</div></div>"
                + "<div class=\"section ni-section\">"
                + "<div class=\"section-heading\">NO INFO — "
                + str(no_info_count)
                + "</div>"
                + "<div class=\"section-body\">"
                + no_info_html
                + "</div></div>"
                + "</div>"
            )

            html = html + (
                "<div class=\"report-footer\">"
                + "<strong>On-duty branches:</strong> "
                + (
                    ", ".join(on_duty_branches)
                    if on_duty_branches
                    else "NIL"
                )
                + "<br><strong>No Doctor:</strong> "
                + no_doctor_text
                + "<br><strong>Week Off:</strong> "
                + str(week_off_count)
                + " | Late and Early calculated from submitted "
                + "Employee Shift Assignment."
                + "</div>"
            )

            summary = (
                "On duty "
                + str(on_duty)
                + "/11"
                + "; Late "
                + str(late_count)
                + "; Early "
                + str(early_count)
                + "; Absent/Leave "
                + str(absent_count)
                + "; NI "
                + str(no_info_count)
                + "; No DR "
                + no_doctor_text
            )

            template_name = "life_daily_doctor_in_out_report_v2"

            parameters = [
                {
                    "name": "report_date",
                    "value": report_date
                },
                {
                    "name": "on_duty",
                    "value": str(on_duty) + "/11 branches"
                },
                {
                    "name": "late_in",
                    "value": str(late_count)
                },
                {
                    "name": "early_out",
                    "value": str(early_count)
                },
                {
                    "name": "absent_leave",
                    "value": str(absent_count)
                },
                {
                    "name": "no_info",
                    "value": str(no_info_count)
                },
                {
                    "name": "no_doctor",
                    "value": no_doctor_text
                }
            ]

        if frappe.db.exists("LIFE WATI Daily Report", report_key):
            report_doc = frappe.get_doc("LIFE WATI Daily Report", report_key)
        else:
            report_doc = frappe.new_doc("LIFE WATI Daily Report")
            report_doc.report_key = report_key
            report_doc.report_date = today
            report_doc.report_type = report_type

        report_doc.summary = summary
        report_doc.report_html = html
        report_doc.status = "Generated"
        report_doc.error_details = ""
        report_doc.save(ignore_permissions=True)

        pdf_content = frappe.get_print("LIFE WATI Daily Report", report_doc.name, print_format="LIFE WATI Daily Report PDF", as_pdf=True)
        generated_time = frappe.utils.format_datetime(
            frappe.utils.now(),
            "HHmmss"
        )

        file_name = (
            "LIFE_"
            + (
                "Attendance_"
                if report_type == "Attendance"
                else "Doctor_IN_OUT_"
            )
            + today
            + "_"
            + generated_time
            + ".pdf"
        )

        file_doc = frappe.get_doc({
            "doctype":"File",
            "file_name":file_name,
            "is_private":0,
            "content":pdf_content,
            "attached_to_doctype":"LIFE WATI Daily Report",
            "attached_to_name":report_doc.name
        })

        file_doc.insert(ignore_permissions=True)

        if not file_doc.file_url:
            frappe.throw("PDF File record was created without a URL.")

        pdf_url = frappe.utils.get_url(file_doc.file_url)

        report_doc.db_set(
            "pdf_file",
            file_doc.file_url,
            update_modified=False
        )

        # API is commonly opened through GET.
        # Commit here so the generated public PDF is not rolled back.
        frappe.db.commit()

        preview_only = action.startswith("preview_")
        already_sent = bool(report_doc.get("sent_on"))
        if preview_only:
            frappe.response["message"] = {"status":"preview","report":report_doc.name,"summary":summary,"pdf_url":pdf_url}
        elif already_sent and not force_send:
            frappe.response["message"] = {"status":"already_sent","report":report_doc.name,"sent_on":report_doc.sent_on,"pdf_url":pdf_url}
        elif not tenant_id or not token or len(mobile) < 11:
            report_doc.db_set("status","Failed",update_modified=False)
            report_doc.db_set("error_details","Missing WATI tenant, access token, or recipient number.",update_modified=False)
            frappe.response["message"] = {"status":"failed","message":"Missing WATI settings."}
        else:
            parameters.append({"name":"pdfLink","value":pdf_url})
            payload_base = {
                "template_name": template_name,
                "parameters": parameters
            }

            sent_numbers = []
            failed_numbers = []
            message_ids = []

            for recipient_mobile in report_mobiles:
                recipient_mobile = str(
                    recipient_mobile or ""
                ).strip()

                clean_recipient = ""

                for character in recipient_mobile:
                    if character.isdigit():
                        clean_recipient = (
                            clean_recipient + character
                        )

                if len(clean_recipient) == 10:
                    clean_recipient = (
                        "91" + clean_recipient
                    )

                if len(clean_recipient) < 11:
                    failed_numbers.append(
                        clean_recipient or recipient_mobile
                    )
                    continue

                wati_url = (
                    "https://live-mt-server.wati.io/"
                    + tenant_id
                    + "/api/v2/sendTemplateMessage"
                    + "?whatsappNumber="
                    + clean_recipient
                )

                payload = {
                    "template_name": (
                        payload_base.get("template_name")
                    ),
                    "broadcast_name": (
                        "LIFE_"
                        + report_key.replace("-", "_")
                        + "_"
                        + clean_recipient[-4:]
                    ),
                    "parameters": (
                        payload_base.get("parameters")
                    )
                }

                try:
                    response = _make_post_request(
                        wati_url,
                        headers={
                            "Authorization": (
                                "Bearer " + token
                            ),
                            "Content-Type": "application/json"
                        },
                        data=json.dumps(payload)
                    )

                    message_id = ""

                    if isinstance(response, dict):
                        message_id = str(
                            response.get("localMessageId")
                            or response.get("id")
                            or ""
                        )

                    sent_numbers.append(clean_recipient)

                    if message_id:
                        message_ids.append(message_id)

                except Exception as send_error:
                    failed_numbers.append(clean_recipient)

                    frappe.log_error(
                        message=(
                            "Report: "
                            + str(report_doc.name)
                            + "\nTemplate: "
                            + str(template_name)
                            + "\nRecipient: "
                            + str(clean_recipient)
                            + "\nError: "
                            + str(send_error)
                        ),
                        title=(
                            "LIFE WATI Recipient Send Failed"
                        )
                    )

            if sent_numbers:
                report_doc.db_set(
                    "status",
                    "Sent",
                    update_modified=False
                )

                report_doc.db_set(
                    "sent_on",
                    frappe.utils.now(),
                    update_modified=False
                )

                report_doc.db_set(
                    "wati_message_id",
                    ", ".join(message_ids),
                    update_modified=False
                )

                if failed_numbers:
                    report_doc.db_set(
                        "error_details",
                        (
                            "Failed recipients: "
                            + ", ".join(failed_numbers)
                        ),
                        update_modified=False
                    )
                else:
                    report_doc.db_set(
                        "error_details",
                        "",
                        update_modified=False
                    )

                frappe.response["message"] = {
                    "status": (
                        "partially_sent"
                        if failed_numbers
                        else "sent"
                    ),
                    "report": report_doc.name,
                    "summary": summary,
                    "pdf_url": pdf_url,
                    "sent_to": sent_numbers,
                    "failed": failed_numbers,
                    "wati_message_ids": message_ids
                }

            else:
                error_text = (
                    "WATI sending failed for all recipients: "
                    + ", ".join(failed_numbers)
                )

                report_doc.db_set(
                    "status",
                    "Failed",
                    update_modified=False
                )

                report_doc.db_set(
                    "error_details",
                    error_text,
                    update_modified=False
                )

                frappe.response["message"] = {
                    "status": "failed",
                    "report": report_doc.name,
                    "error": error_text
                }
