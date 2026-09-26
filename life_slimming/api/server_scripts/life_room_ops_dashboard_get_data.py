"""Operations & Service Module

Original API: life_room_ops_dashboard_get_data
Source modified: 2026-07-10 18:54:43.737576
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
    # LIFE Appointment Report Dashboard API
    # Script Type: API
    # API Method: life_ops_dashboard_get_data

    branch = frappe.form_dict.get("branch") or "all"
    from_date = frappe.form_dict.get("from_date") or frappe.utils.today()
    to_date = frappe.form_dict.get("to_date") or frappe.utils.today()
    today = frappe.utils.today()

    history_start = frappe.utils.add_days(from_date, -180)


    def has_doctype(dt):
        try:
            return frappe.db.exists("DocType", dt)
        except Exception:
            return False


    def has_field(dt, fieldname):
        if fieldname in ["name", "docstatus", "modified", "creation", "owner"]:
            return True

        try:
            meta = frappe.get_meta(dt)
            for df in meta.fields:
                if df.fieldname == fieldname:
                    return True
        except Exception:
            return False

        return False


    def fields_ok(dt, fields):
        out = []

        for f in fields:
            if has_field(dt, f):
                out.append(f)

        if "name" not in out:
            out.insert(0, "name")

        return out


    def value(row, keys):
        for k in keys:
            try:
                v = row.get(k)
                if v is not None and v != "":
                    return v
            except Exception:
                pass

        return ""


    def get_rows(dt, filters, fields, order_by, limit_count):
        if not has_doctype(dt):
            return []

        try:
            return frappe.get_all(
                dt,
                filters=filters,
                fields=fields_ok(dt, fields),
                order_by=order_by,
                limit_page_length=limit_count
            )
        except Exception:
            return []


    def branch_filters(dt):
        filters = {}

        if branch and branch != "all":
            if has_field(dt, "branch"):
                filters["branch"] = branch
            elif has_field(dt, "branch_name"):
                filters["branch_name"] = branch
            elif has_field(dt, "custom_branch"):
                filters["custom_branch"] = branch

        return filters


    def normalize_status(s):
        s = str(s or "").strip()

        if not s:
            return "Pending"

        return s


    def get_appointment_doctype():
        if has_doctype("Appointment"):
            return "Appointment"

        if has_doctype("Patient Appointment"):
            return "Patient Appointment"

        return ""


    def date_from_row(row):
        scheduled_time = value(row, ["scheduled_time", "starts_on"])
        appointment_date = value(row, ["appointment_date", "date"])

        if appointment_date:
            return str(appointment_date)[0:10]

        if scheduled_time:
            return str(scheduled_time)[0:10]

        return ""


    def time_from_row(row):
        appointment_time = value(row, ["appointment_time", "time"])
        scheduled_time = value(row, ["scheduled_time", "starts_on"])

        if appointment_time:
            return str(appointment_time)[0:5]

        if scheduled_time:
            s = str(scheduled_time)
            if len(s) >= 16:
                return s[11:16]

        return ""


    def date_filter_field(dt):
        if has_field(dt, "scheduled_time"):
            return "scheduled_time"

        if has_field(dt, "starts_on"):
            return "starts_on"

        if has_field(dt, "appointment_date"):
            return "appointment_date"

        if has_field(dt, "date"):
            return "date"

        return ""


    # -------------------------
    # BRANCHES
    # -------------------------
    branches = []

    if has_doctype("Branch"):
        branch_rows = get_rows(
            "Branch",
            {},
            [
                "name",
                "branch",
                "branch_name",
                "branch_code",
                "custom_branch_code",
                "custom_abbreviation"
            ],
            "name asc",
            1000
        )

        for b in branch_rows:
            branches.append({
                "name": b.get("name"),
                "branch": value(b, ["branch", "branch_name", "name"]),
                "code": value(b, ["branch_code", "custom_branch_code", "custom_abbreviation"])
            })


    # -------------------------
    # APPOINTMENTS
    # -------------------------
    appointments = []
    history = []
    past_pending_count = 0
    appointment_dt = get_appointment_doctype()

    if appointment_dt:
        apt_fields = [
            "name",
            "scheduled_time",
            "starts_on",
            "appointment_date",
            "date",
            "appointment_time",
            "time",
            "duration",
            "status",
            "call_back_status",
            "appointment_status",
            "patient",
            "patient_name",
            "customer_name",
            "customer_phone_number",
            "mobile",
            "phone",
            "sex",
            "gender",
            "branch",
            "branch_name",
            "custom_branch",
            "category",
            "concern",
            "service",
            "appointment_type",
            "therapy_type",
            "custom_therapy_type",
            "custom_consultation_status",
            "room",
            "room_name",
            "service_unit",
            "custom_room",
            "custom_room_no",
            "custom_room_name",
            "custom_service_room",
            "practitioner",
            "custom_practitioner",
            "healthcare_practitioner",
            "custom_consultation_taken_by",
            "custom_employee_name",
            "owner",
            "creation",
            "modified"
        ]

        df = date_filter_field(appointment_dt)

        report_filters = branch_filters(appointment_dt)

        if df in ["scheduled_time", "starts_on"]:
            report_filters[df] = ["between", [from_date + " 00:00:00", to_date + " 23:59:59"]]
        elif df:
            report_filters[df] = ["between", [from_date, to_date]]

        rows = get_rows(
            appointment_dt,
            report_filters,
            apt_fields,
            "modified desc",
            3000
        )

        history_filters = branch_filters(appointment_dt)

        if df in ["scheduled_time", "starts_on"]:
            history_filters[df] = ["between", [history_start + " 00:00:00", to_date + " 23:59:59"]]
        elif df:
            history_filters[df] = ["between", [history_start, to_date]]

        history_rows = get_rows(
            appointment_dt,
            history_filters,
            apt_fields,
            "modified desc",
            5000
        )

        for h in history_rows:
            h_status = normalize_status(value(h, ["call_back_status", "appointment_status", "status"]))

            history.append({
                "name": h.get("name"),
                "date": date_from_row(h),
                "time": time_from_row(h),
                "patient": value(h, ["patient"]),
                "client_name": value(h, ["patient_name", "customer_name", "patient"]),
                "mobile": value(h, ["mobile", "phone", "customer_phone_number"]),
                "status": h_status
            })

        past_filters = branch_filters(appointment_dt)

        if df in ["scheduled_time", "starts_on"]:
            past_filters[df] = ["<", today + " 00:00:00"]
        elif df:
            past_filters[df] = ["<", today]

        past_rows = get_rows(
            appointment_dt,
            past_filters,
            apt_fields,
            "modified desc",
            1000
        )

        for p in past_rows:
            p_status = str(normalize_status(value(p, ["call_back_status", "appointment_status", "status"]))).lower()

            if (
                "scheduled" in p_status
                or "re-confirm" in p_status
                or "reconfirm" in p_status
                or "confirm" in p_status
                or "pending" in p_status
                or "open" in p_status
                or "unverified" in p_status
            ):
                past_pending_count = past_pending_count + 1

        for a in rows:
            apt_date = date_from_row(a)
            apt_time = time_from_row(a)
            status = normalize_status(value(a, ["call_back_status", "appointment_status", "status"]))

            appointments.append({
                "doctype": appointment_dt,
                "name": a.get("name"),
                "date": apt_date,
                "time": apt_time,
                "scheduled_time": value(a, ["scheduled_time", "starts_on"]),
                "duration": value(a, ["duration"]),
                "status": status,
                "patient": value(a, ["patient"]),
                "client_name": value(a, ["patient_name", "customer_name", "patient"]),
                "mobile": value(a, ["mobile", "phone", "customer_phone_number"]),
                "gender": value(a, ["sex", "gender"]),
                "branch": value(a, ["branch", "branch_name", "custom_branch"]),
                "concern": value(a, ["concern", "service", "category", "therapy_type", "custom_therapy_type"]),
                "therapy_type": value(a, ["therapy_type", "custom_therapy_type", "service", "concern", "category"]),
                "room": value(a, ["room", "room_name", "service_unit", "custom_room", "custom_room_no", "custom_room_name", "custom_service_room", "category"]),
                "given_by": value(a, ["custom_employee_name", "custom_consultation_taken_by", "owner", "practitioner", "custom_practitioner", "healthcare_practitioner"]),
                "given_date": str(value(a, ["creation"]))[0:10],
                "creation": str(value(a, ["creation"])),
                "modified": str(value(a, ["modified"])),
                "appointment_type": value(a, ["appointment_type"]),
                "consultation_status": value(a, ["custom_consultation_status"])
            })


    frappe.response["message"] = {
        "branch": branch,
        "from_date": from_date,
        "to_date": to_date,
        "today": today,
        "appointment_doctype": appointment_dt,
        "branches": branches,
        "appointments": appointments,
        "history": history,
        "past_pending_count": past_pending_count
    }
