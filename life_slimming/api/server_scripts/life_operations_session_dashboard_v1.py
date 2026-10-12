"""LIFE Operations Session Dashboard V1

Original API: life_operations_session_dashboard_v1
Source modified: 2026-10-10 06:59:29.426893
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

    if frappe.session.user == "Guest":
        frappe.throw("Please sign in.")
    from_date = frappe.form_dict.get("from_date") or frappe.utils.today()
    to_date = frappe.form_dict.get("to_date") or frappe.utils.today()
    if frappe.utils.getdate(from_date) > frappe.utils.getdate(to_date):
        frappe.throw("From Date cannot be after To Date.")
    branch = str(frappe.form_dict.get("branch") or "").strip()
    category = str(frappe.form_dict.get("category") or "").strip()
    fields = ["name", "branch", "therapy_type", "department", "practitioner", "custom_practitioner_name", "custom_doctor", "custom_doctor_name", "start_date", "custom_actual_session_date", "patient", "patient_name", "start_time", "duration"]
    filters = [["docstatus", "=", 1]]
    if branch:
        filters.append(["branch", "=", branch])
    rows = []
    offset = 0
    while True:
        batch = frappe.get_list("Therapy Session", fields=fields, filters=filters,
            or_filters=[["custom_actual_session_date", "between", [from_date, to_date]], ["start_date", "between", [from_date, to_date]]],
            order_by="name asc", limit_start=offset, limit_page_length=500)
        for row in batch:
            date = str(row.get("custom_actual_session_date") or row.get("start_date") or "")[:10]
            if str(from_date) <= date and date <= str(to_date):
                rows.append(row)
        if len(batch) < 500:
            break
        offset += len(batch)
    types = []
    for row in rows:
        if row.get("therapy_type") and row.get("therapy_type") not in types:
            types.append(row.get("therapy_type"))
    type_map = {}
    if types:
        for row in frappe.get_all("Therapy Type", filters={"name": ["in", types]}, fields=["name", "healthcare_service_unit"], limit_page_length=0):
            type_map[row.name] = row.get("healthcare_service_unit") or ""
    therapists = {}
    doctors = {}
    categories = []
    total = 0
    no_therapist = 0
    no_doctor = 0
    for row in rows:
        cat = type_map.get(row.get("therapy_type")) or row.get("department") or "Unclassified"
        if cat not in categories:
            categories.append(cat)
        if category and cat != category:
            continue
        total += 1
        therapist = row.get("practitioner")
        doctor = row.get("custom_doctor")
        if therapist:
            key = str(therapist) + "||" + str(row.get("branch") or "") + "||" + str(cat)
            if key not in therapists:
                therapists[key] = {"staff": therapist, "name": row.get("custom_practitioner_name") or therapist, "branch": row.get("branch") or "Unassigned", "category": cat, "sessions": 0}
            therapists[key]["sessions"] = therapists[key]["sessions"] + 1
        else:
            no_therapist += 1
        if doctor:
            key = str(doctor) + "||" + str(row.get("branch") or "") + "||" + str(cat)
            if key not in doctors:
                doctors[key] = {"staff": doctor, "name": row.get("custom_doctor_name") or doctor, "branch": row.get("branch") or "Unassigned", "category": cat, "sessions": 0}
            doctors[key]["sessions"] = doctors[key]["sessions"] + 1
        else:
            no_doctor += 1
    branches = frappe.get_list("Branch", fields=["name"], order_by="name asc", limit_page_length=0)
    frappe.response["message"] = {"total": total, "therapists": list(therapists.values()), "doctors": list(doctors.values()), "categories": sorted(categories), "branches": [row.name for row in branches], "no_therapist": no_therapist, "no_doctor": no_doctor}
    detail_rows = []
    staff = str(frappe.form_dict.get("staff") or "").strip()
    role = str(frappe.form_dict.get("role") or "therapist").strip()
    if staff:
        for row in rows:
            cat = type_map.get(row.get("therapy_type")) or row.get("department") or "Unclassified"
            staff_id = row.get("custom_doctor") if role == "doctor" else row.get("practitioner")
            if staff_id == staff and (not category or cat == category):
                row["category"] = cat
                row["session_date"] = str(row.get("custom_actual_session_date") or row.get("start_date") or "")[:10]
                detail_rows.append(row)
    frappe.response["message"]["sessions"] = detail_rows
    labels = {}
    for field in frappe.get_meta("Therapy Session").fields:
        if field.fieldname and field.label:
            labels[field.fieldname] = field.label
    frappe.response["message"]["field_labels"] = labels
