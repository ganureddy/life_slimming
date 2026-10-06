"""cc_walkins_range

Original API: cc_walkins_range
Source modified: 2026-09-13 12:17:18.706500
See ../CATALOG.md for migration notes and validation limits.
"""

import json
import re

import frappe
from frappe.integrations.utils import make_post_request as _make_post_request
from frappe.utils.safe_exec import read_sql as _read_sql
from frappe.utils.safe_exec import call_whitelisted_function as _call_whitelisted
from life_slimming.api._runtime import script_endpoint
from life_slimming.api.pd_form_utils import pd_form_child_urls_by_patient


@script_endpoint(allow_guest=False)
def run(**kwargs):
    # branch = frappe.form_dict.get("branch") or ""
    # dfrom = frappe.form_dict.get("from_date") or ""
    # dto = frappe.form_dict.get("to_date") or ""
    # out = []
    # if branch and dfrom and dto:
    #     filt = [
    #         ["custom_appointment_date_and_time", ">=", dfrom + " 00:00:00"],
    #         ["custom_appointment_date_and_time", "<=", dto + " 23:59:59"],
    #     ]
    #     rows = frappe.get_all("Lead",
    #         filters=filt,
    #         or_filters=[["branch", "=", branch], ["lead_assign_to_branch", "=", branch]],
    #         fields=["name", "lead_name", "mobile_no",
    #                 "custom_appointment_date_and_time",
    #                 "custom_appointment_status", "custom_visit_status",
    #                 "custom_remarks", "custom_status_updated_by_name",
    #                 "custom_status_updated_on", "lead_owner"],
    #         order_by="custom_appointment_date_and_time asc",
    #         ignore_permissions=True, limit_page_length=0)
    #     for r in rows:
    #         dt = r.get("custom_appointment_date_and_time")
    #         dstr = ""
    #         tstr = ""
    #         if dt:
    #             dstr = str(dt)[0:10]
    #             tstr = str(dt)[11:16]
    #         out.append({
    #             "id": r.get("name"),
    #             "n": r.get("lead_name") or "",
    #             "d": dstr,
    #             "t": tstr,
    #             "st": r.get("custom_appointment_status") or "Not Booked",
    #             "appt_status": r.get("custom_appointment_status") or "",
    #             "visit_status": r.get("custom_visit_status") or "",
    #             "rm": r.get("custom_remarks") or "",
    #             "by_": "",
    #             "upd_by": r.get("custom_status_updated_by_name") or "",
    #             "upd_on": str(r.get("custom_status_updated_on") or ""),
    #             "own": ""
    #         })
    # frappe.response["message"] = out





















    # Server Script: API
    # API Method: cc_walkins_range

    branch = (frappe.form_dict.get("branch") or "").strip()
    dfrom = (frappe.form_dict.get("from_date") or "").strip()
    dto = (frappe.form_dict.get("to_date") or "").strip()

    if not branch or not dfrom:
        frappe.throw("Branch and From Date are required")
    if not dto:
        dto = dfrom

    rows = frappe.get_all(
        "Lead",
        filters=[
            ["custom_appointment_date_and_time", ">=", dfrom + " 00:00:00"],
            ["custom_appointment_date_and_time", "<=", dto + " 23:59:59"]
        ],
        or_filters=[["branch", "=", branch], ["lead_assign_to_branch", "=", branch]],
        fields=[
            "name", "lead_name", "age", "mobile_no", "phone", "source",
            "lead_owner", "branch", "lead_assign_to_branch", "enquired_for",
            "custom_treatment_interests", "custom_appointment_date_and_time",
            "custom_appointment_status", "custom_visit_status", "custom_remarks",
            "custom_status_updated_by_employee", "custom_status_updated_by_name",
            "custom_status_updated_on"
        ],
        order_by="custom_appointment_date_and_time asc",
        ignore_permissions=True,
        limit_page_length=0
    )

    owner_ids = []
    lead_ids = []
    for row in rows:
        lead_ids.append(row.get("name"))
        if row.get("lead_owner") and row.get("lead_owner") not in owner_ids:
            owner_ids.append(row.get("lead_owner"))

    owner_map = {}
    if owner_ids:
        users = frappe.get_all("User", filters={"name": ["in", owner_ids]},
            fields=["name", "full_name"], ignore_permissions=True, limit_page_length=0)
        for user in users:
            full = user.get("full_name") or user.get("name") or ""
            owner_map[user.get("name")] = full.split(" ")[0] if full else ""

    patient_map = {}
    patient_names = []
    practitioner_ids = []
    if lead_ids:
        patients = frappe.get_all("Patient", filters={"custom_lead": ["in", lead_ids]},
            fields=["name", "patient_name", "custom_lead", "custom_pd_form_number",
                    "custom_employee_id", "custom_manager_name"],
            order_by="creation desc", ignore_permissions=True, limit_page_length=0)
        for patient in patients:
            lead_id = patient.get("custom_lead")
            if lead_id and lead_id not in patient_map:
                patient_map[lead_id] = patient
                patient_names.append(patient.get("name"))
                if patient.get("custom_employee_id") and patient.get("custom_employee_id") not in practitioner_ids:
                    practitioner_ids.append(patient.get("custom_employee_id"))
                if patient.get("custom_manager_name") and patient.get("custom_manager_name") not in practitioner_ids:
                    practitioner_ids.append(patient.get("custom_manager_name"))

    practitioner_map = {}
    if practitioner_ids:
        practitioner_rows = frappe.get_all("Healthcare Practitioner",
            filters={"name": ["in", practitioner_ids]},
            fields=["name", "practitioner_name"],
            ignore_permissions=True, limit_page_length=0)
        for practitioner_row in practitioner_rows:
            practitioner_map[practitioner_row.get("name")] = practitioner_row.get("practitioner_name") or practitioner_row.get("name")

    # Include attachment values stored on the PD Form child rows as well as
    # File records. Some uploads are attached to the Patient child table and
    # do not create a File row with attached_to_field=custom_pd_form.
    # Multiple File records can point to the same physical image,
    # so counting File rows directly produces an incorrect 5/5.
    file_count = {}
    file_urls_by_patient = {}

    if patient_names:
        files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Patient",
                "attached_to_name": ["in", patient_names]
            },
            fields=[
                "attached_to_name",
                "attached_to_field",
                "file_url"
            ],
            order_by="creation asc",
            ignore_permissions=True,
            limit_page_length=0
        )

        for file_row in files:
            fld = (
                file_row.get("attached_to_field") or ""
            ).lower()

            file_url = (
                file_row.get("file_url") or ""
            )

            is_pd_form = not fld or "pd_form" in fld

            if is_pd_form and file_url:
                p_name = file_row.get(
                    "attached_to_name"
                )

                if p_name not in file_urls_by_patient:
                    file_urls_by_patient[p_name] = []

                if (
                    file_url
                    not in file_urls_by_patient[p_name]
                ):
                    file_urls_by_patient[p_name].append(
                        file_url
                    )

    child_urls = pd_form_child_urls_by_patient(patient_names)
    for p_name in patient_names:
        urls = file_urls_by_patient.setdefault(p_name, [])
        for file_url in child_urls.get(p_name, []):
            if file_url not in urls:
                urls.append(file_url)
        file_count[p_name] = len(urls)

    def category_of(row):
        blob = (str(row.get("enquired_for") or "") + " " +
                str(row.get("custom_treatment_interests") or "")).lower()
        if "hair" in blob:
            return "Hair"
        if "skin" in blob or "laser" in blob:
            return "Skin"
        if "slim" in blob or "weight" in blob or "cryo" in blob or "fat" in blob:
            return "Slimming"
        return row.get("enquired_for") or ""

    out = []
    for row in rows:
        dt = row.get("custom_appointment_date_and_time")
        patient = patient_map.get(row.get("name")) or {}
        patient_name = patient.get("name") or ""
        pd_number = patient.get("custom_pd_form_number") or ""
        pd_images = file_count.get(patient_name, 0)
        consultation = (row.get("custom_status_updated_by_name") or
                        practitioner_map.get(patient.get("custom_employee_id")) or
                        practitioner_map.get(patient.get("custom_manager_name")) or "")
        appointment_status = row.get("custom_appointment_status") or ""
        if appointment_status == "Cancelled":
            appointment_status = "Not Booked"
        out.append({
            "id": row.get("name") or "",
            "n": row.get("lead_name") or "",
            "age": row.get("age") or "",
            "mobile": row.get("mobile_no") or "",
            "alt_mobile": row.get("phone") or "",
            "category": category_of(row),
            "d": str(dt)[0:10] if dt else "",
            "t": str(dt)[11:16] if dt else "",
            "date_type": "Appointment Date",
            "owner": owner_map.get(row.get("lead_owner"), row.get("lead_owner") or ""),
            "source": row.get("source") or "",
            "branch": row.get("lead_assign_to_branch") or row.get("branch") or "",
            "consultation_employee": consultation,
            "st": appointment_status,
            "visit_status": row.get("custom_visit_status") or "",
            "rm": row.get("custom_remarks") or "",
            "upd_by": row.get("custom_status_updated_by_name") or "",
            "upd_on": str(row.get("custom_status_updated_on") or ""),
            "patient": patient_name,
            "pd_number": pd_number,
            "pd_image_count": pd_images,
            "pd_available": 1 if (pd_number or pd_images) else 0
        })

    allowed_designations = [
        "Branch Manager",
        "Center Manager",
        "Centre Manager",
        "Assistant Center Manager",
        "Assistant Centre Manager",
        "ACM",
        "Area Manager",
        "Area Manager (Trainee)",
        "Area Manager Trainee",
        "Senior Manager",
        "Manager",
        "Doctor",
        "Consultant",
        "Consultant Doctor",
        "Doctor Consultant"
    ]
    employees = frappe.get_all("Employee",
        filters={"status": "Active", "branch": branch,
                 "designation": ["in", allowed_designations]},
        fields=["name", "employee_name", "designation"],
        order_by="employee_name asc", ignore_permissions=True, limit_page_length=0)

    frappe.response["message"] = {
        "rows": out,
        "employees": [{"id": e.get("name"), "n": e.get("employee_name"),
                       "dg": e.get("designation")} for e in employees]
    }
