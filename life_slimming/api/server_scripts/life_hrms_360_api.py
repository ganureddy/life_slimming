"""life_hrms_360_api

Original API: life_hrms_360_api
Source modified: 2026-09-13 16:00:32.402098
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

    action = frappe.form_dict.get("action") or "bootstrap"
    today = frappe.utils.today()
    month_start = today[0:8] + "01"
    current_user = frappe.session.user


    def permitted_fields(doctype, requested_fields):
        try:
            meta = frappe.get_meta(doctype)
            output = []

            for fieldname in requested_fields:
                if fieldname == "name":
                    output.append(fieldname)
                elif meta.has_field(fieldname):
                    output.append(fieldname)

            if not output:
                output = ["name"]

            return output
        except:
            return ["name"]


    def safe_rows(
        doctype,
        requested_fields,
        filters=None,
        limit=1000,
        order_by="modified desc"
    ):
        try:
            return frappe.get_all(
                doctype,
                fields=permitted_fields(
                    doctype,
                    requested_fields
                ),
                filters=filters or {},
                order_by=order_by,
                limit_page_length=limit
            )
        except:
            return []


    def current_roles():
        output = []

        try:
            rows = frappe.get_all(
                "Has Role",
                filters={
                    "parent": current_user,
                    "parenttype": "User"
                },
                fields=["role"],
                limit_page_length=200
            )

            for row in rows:
                if row.role and row.role not in output:
                    output.append(row.role)
        except:
            output = []

        if current_user == "Administrator":
            if "System Manager" not in output:
                output.append("System Manager")

        return output


    roles = current_roles()

    salary_allowed = (
        "System Manager" in roles
        or "HR Manager" in roles
        or "HR User" in roles
    )


    # HRMS_LIVE_APPOINTMENT_LETTER_BACKEND_START

    if action == "hr_letters_bootstrap":
        allowed_roles = [
            "System Manager",
            "HR Manager",
            "HR User"
        ]

        user_roles = frappe.get_roles(
            frappe.session.user
        )

        can_manage_letters = False

        for allowed_role in allowed_roles:
            if allowed_role in user_roles:
                can_manage_letters = True

        appointment_letter_rows = []
        template_rows = []
        onboarding_rows = []
        company_rows = []
        print_format_rows = []

        if can_manage_letters:
            appointment_letter_rows = frappe.get_all(
                "Appointment Letter",
                fields=[
                    "name",
                    "applicant_name",
                    "custom_employee_name",
                    "custom_employee",
                    "custom_designation",
                    "custom_ctc",
                    "custom_permanent_address",
                    "company",
                    "appointment_date",
                    "appointment_letter_template",
                    "docstatus",
                    "owner",
                    "creation",
                    "modified"
                ],
                filters={
                    "docstatus": ["<", 2]
                },
                order_by="modified desc",
                limit_page_length=1000
            )

            template_rows = frappe.get_all(
                "Appointment Letter Template",
                fields=[
                    "name",
                    "template_name",
                    "modified"
                ],
                order_by="template_name asc",
                limit_page_length=500
            )

            onboarding_rows = frappe.get_all(
                "HR Employee Onboarding",
                fields=[
                    "name",
                    "full_name",
                    "date_of_joining",
                    "designation",
                    "department_name",
                    "branch",
                    "permanent_address",
                    "current_address",
                    "docstatus",
                    "modified"
                ],
                filters={
                    "docstatus": ["<", 2],
                    "branch": ["!=", "Testing Branch"]
                },
                order_by="modified desc",
                limit_page_length=2000
            )

            company_rows = frappe.get_all(
                "Company",
                fields=[
                    "name",
                    "company_name",
                    "default_currency",
                    "disabled"
                ],
                filters={
                    "disabled": 0
                },
                order_by="company_name asc",
                limit_page_length=200
            )

            print_format_rows = frappe.get_all(
                "Print Format",
                fields=[
                    "name",
                    "doc_type",
                    "disabled",
                    "standard"
                ],
                filters={
                    "doc_type": "Appointment Letter",
                    "disabled": 0
                },
                order_by="name asc",
                limit_page_length=100
            )

        frappe.response["message"] = {
            "ok": True,
            "action": "hr_letters_bootstrap",
            "can_manage": can_manage_letters,
            "appointment_letters":
                appointment_letter_rows,
            "appointment_letter_templates":
                template_rows,
            "hr_employee_onboarding":
                onboarding_rows,
            "companies":
                company_rows,
            "print_formats":
                print_format_rows,
            "experience_letters": [],
            "relieving_letters": [],
            "warning": {
                "experience_letters":
                    "MISSING: Experience Letter "
                    "DocType is unavailable.",
                "relieving_letters":
                    "MISSING: Relieving Letter "
                    "DocType is unavailable."
            }
        }


    if action == "create_appointment_letter":
        allowed_roles = [
            "System Manager",
            "HR Manager"
        ]

        user_roles = frappe.get_roles(
            frappe.session.user
        )

        can_create_letter = False

        for allowed_role in allowed_roles:
            if allowed_role in user_roles:
                can_create_letter = True

        if not can_create_letter:
            frappe.throw(
                "Only HR Manager or System Manager can "
                "create Appointment Letters."
            )

        onboarding_name = (
            frappe.form_dict.get("onboarding")
            or frappe.form_dict.get(
                "custom_employee_name"
            )
            or ""
        ).strip()

        template_name = (
            frappe.form_dict.get("template")
            or frappe.form_dict.get(
                "appointment_letter_template"
            )
            or ""
        ).strip()

        company_name = (
            frappe.form_dict.get("company")
            or ""
        ).strip()

        appointment_date = (
            frappe.form_dict.get("appointment_date")
            or ""
        ).strip()

        supplied_ctc = (
            frappe.form_dict.get("ctc")
            or frappe.form_dict.get("custom_ctc")
            or ""
        )

        if not onboarding_name:
            frappe.throw(
                "HR Employee Onboarding is required."
            )

        if not template_name:
            frappe.throw(
                "Appointment Letter Template is required."
            )

        if not company_name:
            frappe.throw(
                "Company is required."
            )

        if not appointment_date:
            frappe.throw(
                "Appointment Date is required."
            )

        if not frappe.db.exists(
            "HR Employee Onboarding",
            onboarding_name
        ):
            frappe.throw(
                "HR Employee Onboarding does not exist: "
                + onboarding_name
            )

        if not frappe.db.exists(
            "Appointment Letter Template",
            template_name
        ):
            frappe.throw(
                "Appointment Letter Template "
                "does not exist: "
                + template_name
            )

        if not frappe.db.exists(
            "Company",
            company_name
        ):
            frappe.throw(
                "Company does not exist: "
                + company_name
            )

        company_disabled = frappe.db.get_value(
            "Company",
            company_name,
            "disabled"
        )

        if company_disabled:
            frappe.throw(
                "Disabled Company cannot be used: "
                + company_name
            )

        onboarding_doc = frappe.get_doc(
            "HR Employee Onboarding",
            onboarding_name
        )

        if onboarding_doc.docstatus == 2:
            frappe.throw(
                "Cancelled HR Employee Onboarding "
                "cannot be used."
            )

        if onboarding_doc.branch == "Testing Branch":
            frappe.throw(
                "Testing Branch records are excluded."
            )

        employee_name = (
            onboarding_doc.full_name
            or onboarding_doc.name1
            or ""
        ).strip()

        if not employee_name:
            frappe.throw(
                "MISSING: Employee name is unavailable "
                "in HR Employee Onboarding."
            )

        designation = (
            onboarding_doc.designation
            or ""
        ).strip()

        if designation:
            if not frappe.db.exists(
                "Designation",
                designation
            ):
                frappe.throw(
                    "Onboarding Designation "
                    "does not exist: "
                    + designation
                )

        existing_letter = frappe.db.get_value(
            "Appointment Letter",
            {
                "custom_employee_name":
                    onboarding_name,
                "company":
                    company_name,
                "docstatus":
                    ["<", 2]
            },
            "name"
        )

        if existing_letter:
            frappe.throw(
                "An active Appointment Letter already "
                "exists for this onboarding record: "
                + existing_letter
            )

        template_doc = frappe.get_doc(
            "Appointment Letter Template",
            template_name
        )

        if not template_doc.introduction:
            frappe.throw(
                "MISSING: Selected Appointment Letter "
                "Template has no introduction."
            )

        if not template_doc.terms:
            frappe.throw(
                "MISSING: Selected Appointment Letter "
                "Template has no terms."
            )

        letter_terms = []

        for template_term in template_doc.terms:
            term_title = (
                template_term.title
                or ""
            ).strip()

            term_description = (
                template_term.description
                or ""
            ).strip()

            if not term_title:
                frappe.throw(
                    "MISSING: Appointment Letter Template "
                    "contains a term without a title."
                )

            if not term_description:
                frappe.throw(
                    "MISSING: Appointment Letter Template "
                    "contains a term without a description."
                )

            letter_terms.append({
                "title": term_title,
                "description": term_description
            })

        numeric_ctc = 0

        if supplied_ctc not in (
            None,
            "",
            "MISSING"
        ):
            try:
                numeric_ctc = float(
                    supplied_ctc
                )
            except Exception:
                frappe.throw(
                    "CTC must be a valid positive number."
                )

            if numeric_ctc <= 0:
                frappe.throw(
                    "CTC must be greater than zero."
                )

        permanent_address = (
            onboarding_doc.permanent_address
            or onboarding_doc.current_address
            or ""
        ).strip()

        letter_doc = frappe.get_doc({
            "doctype":
                "Appointment Letter",
            "applicant_name":
                employee_name,
            "custom_employee_name":
                onboarding_name,
            "custom_employee":
                employee_name,
            "custom_designation":
                designation,
            "custom_ctc":
                numeric_ctc,
            "custom_permanent_address":
                permanent_address,
            "custom_address":
                permanent_address,
            "company":
                company_name,
            "appointment_date":
                appointment_date,
            "appointment_letter_template":
                template_name,
            "introduction":
                template_doc.introduction,
            "closing_notes":
                template_doc.closing_notes or "",
            "terms":
                letter_terms
        })

        letter_doc.insert()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "create_appointment_letter",
            "name":
                letter_doc.name,
            "doctype":
                "Appointment Letter",
            "docstatus":
                letter_doc.docstatus,
            "status":
                "Draft",
            "route": (
                "/app/appointment-letter/"
                + letter_doc.name
            ),
            "employee":
                employee_name,
            "onboarding":
                onboarding_name,
            "template":
                template_name,
            "company":
                company_name,
            "appointment_date":
                appointment_date,
            "ctc": (
                numeric_ctc
                if numeric_ctc > 0
                else "MISSING"
            ),
            "designation": (
                designation
                if designation
                else "MISSING"
            ),
            "address": (
                permanent_address
                if permanent_address
                else "MISSING"
            )
        }

    # HRMS_LIVE_APPOINTMENT_LETTER_BACKEND_END


    if action == "bootstrap":
        employees = safe_rows(
            "Employee",
            [
                "name",
                "employee_name",
                "status",
                "gender",
                "date_of_birth",
                "date_of_joining",
                "department",
                "designation",
                "branch",
                "company",
                "employment_type",
                "reports_to",
                "user_id",
                "company_email",
                "personal_email",
                "cell_number",
                "personal_mobile_no",
                "image",
                "blood_group",
                "marital_status",
                "grade",
                "holiday_list",
                "default_shift",
                "relieving_date",
                "scheduled_confirmation_date",
                "final_confirmation_date",
                "contract_end_date",
                "notice_number_of_days",
                "date_of_retirement",
                "ctc",
                "salary_currency",
                "salary_mode",
                "bank_name",
                "bank_ac_no",
                "iban",
                "current_address",
                "permanent_address",
                "person_to_be_contacted",
                "emergency_phone_number",
                "relation",
                "bio",
                "custom_employment_status",
                "custom_additional_role",
                "custom_current_responsibility",
                "custom_responsibility_from",
                "custom_responsibility_to",
                "custom_responsibility_reason",
                "custom_responsibility_assigned_by",
                "custom_responsibility_updated_on",
                "custom_doc_aadhaar",
                "custom_doc_pan",
                "custom_docs_complete",
                "custom_doc_aadhaar_file",
                "custom_doc_pan_file",
                "custom_doc_resume_file",
                "custom_doc_education_file",
                "custom_doc_offer_letter_file",
                "custom_doc_appointment_letter_file",
                "custom_doc_experience_letter_file",
                "custom_doc_relieving_letter_file",
                "custom_doc_salary_slips_file",
                "custom_doc_bank_cheque_file",
                "custom_doc_medical_fitness_file",
                "custom_doc_police_verification_file",
                "custom_doc_reference_check_file",
                "creation",
                "modified",
                "modified_by",
                "owner"
            ],
            {
                "branch": ["!=", "Testing Branch"]
            },
            1000,
            "employee_name asc"
        )

        if not salary_allowed:
            for employee in employees:
                employee["ctc"] = None
                employee["bank_name"] = None
                employee["bank_ac_no"] = None
                employee["iban"] = None
                employee["salary_mode"] = None

        # HRMS_STEP_26J_A_SETUP_START
        bootstrap_separation_names = []

        bootstrap_separation_name_rows = safe_rows(
            "Employee Separation",
            [
                "name"
            ],
            {
                "docstatus": ["!=", 2]
            },
            1000,
            "modified desc"
        )

        for separation_name_row in (
            bootstrap_separation_name_rows
        ):
            if separation_name_row.get("name"):
                bootstrap_separation_names.append(
                    separation_name_row.get("name")
                )

        if not bootstrap_separation_names:
            bootstrap_separation_names = [
                "__NO_EMPLOYEE_SEPARATION__"
            ]
        # HRMS_STEP_26J_A_SETUP_END

        # HRMS_COMMUNICATION_TASK_BOOTSTRAP_START

        hr_communications = []
        hr_todos = []
        user_notifications = []

        communication_roles = [
            "System Manager",
            "HR Manager",
            "HR User"
        ]

        communication_allowed = False

        for role_name in communication_roles:
            if role_name in roles:
                communication_allowed = True

        if communication_allowed:
            hr_communications = safe_rows(
                "Communication",
                [
                    "name",
                    "subject",
                    "communication_medium",
                    "communication_type",
                    "sent_or_received",
                    "status",
                    "delivery_status",
                    "content",
                    "sender",
                    "sender_full_name",
                    "recipients",
                    "cc",
                    "reference_doctype",
                    "reference_name",
                    "communication_date",
                    "creation",
                    "modified",
                    "owner"
                ],
                {
                    "reference_doctype": [
                        "in",
                        [
                            "Employee",
                            "Job Applicant",
                            "Interview",
                            "Job Offer",
                            "Employee Onboarding",
                            "Employee Separation",
                            "Leave Application",
                            "Attendance Request"
                        ]
                    ]
                },
                5000,
                "communication_date desc"
            )

            hr_todos = safe_rows(
                "ToDo",
                [
                    "name",
                    "status",
                    "priority",
                    "date",
                    "allocated_to",
                    "description",
                    "reference_type",
                    "reference_name",
                    "role",
                    "assigned_by",
                    "custom_completed_by",
                    "custom_completed_on",
                    "custom_completion_remarks",
                    "creation",
                    "modified",
                    "owner"
                ],
                {},
                5000,
                "modified desc"
            )
        else:
            hr_todos = safe_rows(
                "ToDo",
                [
                    "name",
                    "status",
                    "priority",
                    "date",
                    "allocated_to",
                    "description",
                    "reference_type",
                    "reference_name",
                    "assigned_by",
                    "creation",
                    "modified"
                ],
                {
                    "allocated_to": current_user
                },
                1000,
                "modified desc"
            )

        user_notifications = safe_rows(
            "Notification Log",
            [
                "name",
                "subject",
                "type",
                "email_content",
                "for_user",
                "from_user",
                "document_type",
                "document_name",
                "link",
                "read",
                "creation",
                "modified"
            ],
            {
                "for_user": current_user
            },
            2000,
            "creation desc"
        )

        # HRMS_COMMUNICATION_TASK_BOOTSTRAP_END

        frappe.response["message"] = {
            "ok": True,
            "action": "bootstrap",
            "today": today,
            "month_start": month_start,
            "user": current_user,
            "roles": roles,
            "salary_allowed": salary_allowed,

            "branches": safe_rows(
                "Branch",
                ["name"],
                {
                    "name": ["!=", "Testing Branch"]
                },
                100,
                "name asc"
            ),

            # HRMS_EMPLOYEE_MASTERS_START

            "employee_grades": safe_rows(
                "Employee Grade",
                [
                    "name"
                ],
                {},
                1000,
                "name asc"
            ),

            "employment_types": safe_rows(
                "Employment Type",
                [
                    "name"
                ],
                {},
                1000,
                "name asc"
            ),

            "shift_types": safe_rows(
                "Shift Type",
                [
                    "name"
                ],
                {},
                1000,
                "name asc"
            ),

            "holiday_lists": safe_rows(
                "Holiday List",
                [
                    "name",
                    "from_date",
                    "to_date"
                ],
                {},
                1000,
                "name asc"
            ),

            # HRMS_EMPLOYEE_MASTERS_END

            # HRMS_RECRUITMENT_WORKFLOW_BOOTSTRAP_START

            "recruitment_job_openings": safe_rows(
                "Job Opening",
                [
                    "name",
                    "job_title",
                    "designation",
                    "company",
                    "status",
                    "location",
                    "closes_on",
                    "lower_range",
                    "upper_range",
                    "currency",
                    "employment_type",
                    "description"
                ],
                {},
                1000,
                "modified desc"
            ),

            "recruitment_job_applicants": safe_rows(
                "Job Applicant",
                [
                    "name",
                    "applicant_name",
                    "email_id",
                    "phone_number",
                    "job_title",
                    "designation",
                    "status",
                    "source",
                    "source_name",
                    "resume_attachment",
                    "creation",
                    "modified"
                ],
                {},
                5000,
                "modified desc"
            ),

            "recruitment_interview_rounds": safe_rows(
                "Interview Round",
                [
                    "name",
                    "round_name",
                    "designation",
                    "custom_job_applicant_name",
                    "custom_status",
                    "custom_remarks"
                ],
                {},
                1000,
                "name asc"
            ),

            "recruitment_interviews": safe_rows(
                "Interview",
                [
                    "name",
                    "interview_round",
                    "job_applicant",
                    "job_opening",
                    "designation",
                    "status",
                    "scheduled_on",
                    "from_time",
                    "to_time",
                    "docstatus",
                    "creation",
                    "modified"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                5000,
                "scheduled_on desc"
            ),

            "recruitment_interview_feedback": safe_rows(
                "Interview Feedback",
                [
                    "name",
                    "interview",
                    "interview_round",
                    "job_applicant",
                    "interviewer",
                    "result",
                    "docstatus",
                    "creation",
                    "modified"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                5000,
                "modified desc"
            ),

            "recruitment_job_offers": safe_rows(
                "Job Offer",
                [
                    "name",
                    "job_applicant",
                    "applicant_name",
                    "status",
                    "offer_date",
                    "designation",
                    "company",
                    "docstatus",
                    "creation",
                    "modified"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                5000,
                "modified desc"
            ),

            # HRMS_RECRUITMENT_WORKFLOW_BOOTSTRAP_END

            "communication_allowed":
                communication_allowed,

            "hr_communications":
                hr_communications,

            "hr_todos":
                hr_todos,

            "user_notifications":
                user_notifications,

            "employees": employees,

            "attendance": safe_rows(
                "Attendance",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "attendance_date",
                    "status",
                    "working_hours",
                    "in_time",
                    "out_time",
                    "branch",
                    "department",
                    "docstatus"
                ],
                {
                    "attendance_date": [">=", month_start],
                    "docstatus": ["!=", 2]
                },
                10000,
                "attendance_date desc"
            ),

            "leave_applications": safe_rows(
                "Leave Application",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "leave_type",
                    "from_date",
                    "to_date",
                    "total_leave_days",
                    "status",
                    "description",
                    "posting_date",
                    "docstatus"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                3000,
                "from_date desc"
            ),

            "leave_allocations": safe_rows(
                "Leave Allocation",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "leave_type",
                    "from_date",
                    "to_date",
                    "new_leaves_allocated",
                    "total_leaves_allocated",
                    "unused_leaves",
                    "docstatus"
                ],
                {
                    "to_date": [">=", today],
                    "docstatus": ["!=", 2]
                },
                3000,
                "to_date desc"
            ),

            "job_openings": safe_rows(
                "Job Opening",
                [
                    "name",
                    "job_title",
                    "designation",
                    "department",
                    "location",
                    "status",
                    "publish",
                    "creation"
                ],
                {},
                1000,
                "creation desc"
            ),

            "job_applicants": safe_rows(
                "Job Applicant",
                [
                    "name",
                    "applicant_name",
                    "email_id",
                    "phone_number",
                    "job_title",
                    "status",
                    "source",
                    "creation"
                ],
                {},
                3000,
                "creation desc"
            ),

            "onboarding": safe_rows(
                "Employee Onboarding",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "job_applicant",
                    "date_of_joining",
                    "department",
                    "designation",
                    "status",
                    "boarding_status",
                    "project",
                    "docstatus"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                1000
            ),

            "separations": safe_rows(
                "Employee Separation",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "department",
                    "designation",
                    "status",
                    "boarding_status",
                    "project",
                    "boarding_begins_on",
                    "custom_separation_reason",
                    "custom_separation_type",
                    "custom_last_working_day",
                    "custom_eligible_for_rehire",
                    "custom_clearance_status",
                    "custom_clearance_completed_on",
                    "custom_fnf_status",
                    "custom_fnf_settlement_date",
                    "custom_fnf_settlement_amount",
                    "custom_fnf_reference",
                    "custom_fnf_remarks",
                    "custom_settled_by",
                    "custom_requested_from_hrms",
                    "docstatus",
                    "creation",
                    "modified"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                1000
            ),

            # HRMS_STEP_26G_A_START

            "separation_comments": safe_rows(
                "Comment",
                [
                    "name",
                    "reference_doctype",
                    "reference_name",
                    "comment_type",
                    "content",
                    "comment_email",
                    "comment_by",
                    "creation",
                    "modified",
                    "owner"
                ],
                {
                    # HRMS_STEP_26J_A_FILTER_START
                    "reference_doctype":
                        "Employee Separation",
                    "reference_name": [
                        "in",
                        bootstrap_separation_names
                    ]
                    # HRMS_STEP_26J_A_FILTER_END
                },
                5000,
                "creation desc"
            ),

            "separation_versions": safe_rows(
                "Version",
                [
                    "name",
                    "ref_doctype",
                    "docname",
                    "data",
                    "creation",
                    "modified",
                    "owner"
                ],
                {
                    "ref_doctype":
                        "Employee Separation",
                    "docname": [
                        "in",
                        bootstrap_separation_names
                    ]
                },
                5000,
                "creation desc"
            ),

            # HRMS_STEP_26G_A_END

            # HRMS_STEP_27A_START

            # HRMS_STEP_28_START

            "salary_structure_assignments": (
                safe_rows(
                    "Salary Structure Assignment",
                    [
                        "name",
                        "employee",
                        "employee_name",
                        "department",
                        "designation",
                        "grade",
                        "salary_structure",
                        "from_date",
                        "company",
                        "currency",
                        "base",
                        "variable",
                        "docstatus",
                        "creation",
                        "modified"
                    ],
                    {
                        "docstatus": ["!=", 2]
                    },
                    5000,
                    "from_date desc"
                )
                if salary_allowed
                else []
            ),

            "additional_salaries": (
                safe_rows(
                    "Additional Salary",
                    [
                        "name",
                        "employee",
                        "employee_name",
                        "department",
                        "company",
                        "salary_component",
                        "type",
                        "currency",
                        "amount",
                        "payroll_date",
                        "from_date",
                        "to_date",
                        "is_recurring",
                        "disabled",
                        "docstatus",
                        "creation",
                        "modified"
                    ],
                    {
                        "docstatus": ["!=", 2]
                    },
                    5000,
                    "payroll_date desc"
                )
                if salary_allowed
                else []
            ),

            "employee_advances": (
                safe_rows(
                    "Employee Advance",
                    [
                        "name",
                        "employee",
                        "posting_date",
                        "company",
                        "department",
                        "currency",
                        "advance_amount",
                        "paid_amount",
                        "pending_amount",
                        "claimed_amount",
                        "return_amount",
                        "mode_of_payment",
                        "repay_unclaimed_amount_from_salary",
                        "status",
                        "docstatus",
                        "creation",
                        "modified"
                    ],
                    {
                        "docstatus": ["!=", 2]
                    },
                    5000,
                    "posting_date desc"
                )
                if salary_allowed
                else []
            ),

            "expense_claims": (
                safe_rows(
                    "Expense Claim",
                    [
                        "name",
                        "employee",
                        "employee_name",
                        "department",
                        "company",
                        "expense_approver",
                        "approval_status",
                        "total_sanctioned_amount",
                        "total_advance_amount",
                        "grand_total",
                        "total_claimed_amount",
                        "total_amount_reimbursed",
                        "posting_date",
                        "is_paid",
                        "mode_of_payment",
                        "clearance_date",
                        "status",
                        "docstatus",
                        "creation",
                        "modified"
                    ],
                    {
                        "docstatus": ["!=", 2]
                    },
                    5000,
                    "posting_date desc"
                )
                if salary_allowed
                else []
            ),

            "employee_benefit_applications": (
                safe_rows(
                    "Employee Benefit Application",
                    [
                        "name",
                        "employee",
                        "employee_name",
                        "department",
                        "date",
                        "payroll_period",
                        "company",
                        "currency",
                        "max_benefits",
                        "remaining_benefit",
                        "total_amount",
                        "pro_rata_dispensed_amount",
                        "docstatus",
                        "creation",
                        "modified"
                    ],
                    {
                        "docstatus": ["!=", 2]
                    },
                    5000,
                    "date desc"
                )
                if salary_allowed
                else []
            ),

            # HRMS_STEP_28_END

            "appraisals": safe_rows(
                "Appraisal",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "employee_image",
                    "department",
                    "designation",
                    "company",
                    "appraisal_cycle",
                    "appraisal_template",
                    "start_date",
                    "end_date",
                    "rate_goals_manually",
                    "goal_score_percentage",
                    "total_score",
                    "avg_feedback_score",
                    "self_score",
                    "final_score",
                    "remarks",
                    "reflections",
                    "amended_from",
                    "docstatus",
                    "creation",
                    "modified",
                    "modified_by",
                    "owner"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                5000,
                "end_date desc"
            ),

            "appraisal_cycles": safe_rows(
                "Appraisal Cycle",
                [
                    "name",
                    "cycle_name",
                    "company",
                    "status",
                    "start_date",
                    "end_date",
                    "branch",
                    "department",
                    "designation",
                    "kra_evaluation_method",
                    "calculate_final_score_based_on_formula",
                    "creation",
                    "modified",
                    "modified_by",
                    "owner"
                ],
                {},
                1000,
                "start_date desc"
            ),

            # HRMS_STEP_27A_END

            "training": safe_rows(
                "Training Event",
                [
                    "name",
                    "event_name",
                    "type",
                    "start_time",
                    "end_time",
                    "trainer_name",
                    "event_status",
                    "docstatus"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                3000
            ),

            "assets": safe_rows(
                "Asset",
                [
                    "name",
                    "asset_name",
                    "item_code",
                    "custodian",
                    "location",
                    "status",
                    "purchase_date",
                    "available_for_use"
                ],
                {},
                5000
            ),

            "transfers": safe_rows(
                "Employee Transfer",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "transfer_date",
                    "new_company",
                    "docstatus",
                    "creation",
                    "modified",
                    "modified_by"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                3000,
                "transfer_date desc"
            ),

            "promotions": safe_rows(
                "Employee Promotion",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "promotion_date",
                    "revised_ctc",
                    "docstatus",
                    "creation",
                    "modified",
                    "modified_by"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                3000,
                "promotion_date desc"
            ),


            # HRMS_BOOTSTRAP_DATA_START

            "attendance_requests": safe_rows(
                "Attendance Request",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "department",
                    "company",
                    "from_date",
                    "to_date",
                    "half_day",
                    "half_day_date",
                    "include_holidays",
                    "shift",
                    "reason",
                    "explanation",
                    "docstatus",
                    "creation",
                    "modified",
                    "modified_by"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                5000,
                "from_date desc"
            ),

            "job_offers": safe_rows(
                "Job Offer",
                [
                    "name",
                    "job_applicant",
                    "applicant_name",
                    "designation",
                    "company",
                    "offer_date",
                    "status",
                    "docstatus",
                    "creation",
                    "modified",
                    "modified_by"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                3000,
                "creation desc"
            ),

            "asset_movements": safe_rows(
                "Asset Movement",
                [
                    "name",
                    "company",
                    "purpose",
                    "transaction_date",
                    "reference_doctype",
                    "reference_name",
                    "docstatus",
                    "creation",
                    "modified",
                    "modified_by"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                5000,
                "transaction_date desc"
            ),

            # HRMS_BOOTSTRAP_DATA_END


            # HRMS_RECORD_BOOTSTRAP_START

            "employee_hr_records": safe_rows(
                "Employee HR Record",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "branch",
                    "department",
                    "record_type",
                    "record_date",
                    "severity",
                    "status",
                    "subject",
                    "details",
                    "action_taken",
                    "effective_from",
                    "effective_to",
                    "confidential",
                    "attachment",
                    "issued_by",
                    "issued_on",
                    "source",
                    "creation",
                    "modified",
                    "modified_by"
                ],
                (
                    {}
                    if (
                        "System Manager" in roles
                        or "HR Manager" in roles
                    )
                    else {
                        "confidential": 0
                    }
                ),
                5000,
                "record_date desc"
            ),

            "employee_announcements": safe_rows(
                "Employee Announcement",
                [
                    "name",
                    "message",
                    "active",
                    "priority",
                    "valid_till",
                    "interval_hours",
                    "custom_subject",
                    "custom_audience",
                    "custom_branch",
                    "custom_department",
                    "custom_valid_from",
                    "custom_created_by",
                    "custom_created_on",
                    "custom_attachment",
                    "creation",
                    "modified",
                    "modified_by"
                ],
                {
                    "active": 1
                },
                1000,
                "custom_created_on desc"
            ),

            # HRMS_RECORD_BOOTSTRAP_END


            # HRMS_GRIEVANCE_BOOTSTRAP_START

            "employee_grievances": safe_rows(
                "Employee Grievance",
                [
                    "name",
                    "subject",
                    "raised_by",
                    "employee_name",
                    "designation",
                    "date",
                    "status",
                    "reports_to",
                    "grievance_against_party",
                    "grievance_against",
                    "grievance_type",
                    "associated_document_type",
                    "associated_document",
                    "description",
                    "cause_of_grievance",
                    "resolved_by",
                    "resolution_date",
                    "employee_responsible",
                    "resolution_detail",
                    "docstatus",
                    "creation",
                    "modified",
                    "modified_by"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                3000,
                "date desc"
            ),

            "grievance_types": safe_rows(
                "Grievance Type",
                [
                    "name",
                    "description"
                ],
                {},
                500,
                "name asc"
            ),

            # HRMS_GRIEVANCE_BOOTSTRAP_END


            # HRMS_CHECKIN_SALARY_BOOTSTRAP_START

            "checkins": safe_rows(
                "Employee Checkin",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "time",
                    "log_type",
                    "device_id",
                    "shift",
                    "skip_auto_attendance",
                    "attendance",
                    "creation",
                    "modified"
                ],
                {},
                10000,
                "time desc"
            ),

            "salary_slips": (
                safe_rows(
                    "Salary Slip",
                    [
                        "name",
                        "employee",
                        "employee_name",
                        "start_date",
                        "end_date",
                        "posting_date",
                        "status",
                        "gross_pay",
                        "total_deduction",
                        "net_pay",
                        "currency",
                        "payment_days",
                        "total_working_days",
                        "leave_without_pay",
                        "absent_days",
                        "docstatus",
                        "creation",
                        "modified"
                    ],
                    {
                        "docstatus": ["!=", 2]
                    },
                    5000,
                    "start_date desc"
                )
                if salary_allowed
                else []
            ),

            # HRMS_CHECKIN_SALARY_BOOTSTRAP_END


            # HRMS_CHILD_DATA_BOOTSTRAP_START

            "training_participants": safe_rows(
                "Training Event Employee",
                [
                    "name",
                    "parent",
                    "parenttype",
                    "parentfield",
                    "idx",
                    "employee",
                    "employee_name",
                    "department",
                    "email"
                ],
                {
                    "parenttype": "Training Event"
                },
                           10000,
                "parent asc, idx asc"
            ),

            "asset_movement_items": safe_rows(
                "Asset Movement Item",
                [
                    "name",
                    "parent",
                    "parenttype",
                    "parentfield",
                    "idx",
                    "asset",
                    "source_location",
                    "target_location",
                    "from_employee",
                    "to_employee"
                ],
                {
                    "parenttype": "Asset Movement"
                },
                10000,
                "parent asc, idx asc"
            ),

            # HRMS_CHILD_DATA_BOOTSTRAP_END

            "shifts": safe_rows(
                "Shift Assignment",
                [
                    "name",
                    "employee",
                    "employee_name",
                    "shift_type",
                    "start_date",
                    "end_date",
                    "status",
                    "docstatus"
                ],
                {
                    "docstatus": ["!=", 2]
                },
                5000,
                "start_date desc"
            )
        }



    # HRMS_CREATE_EMPLOYEE_START

    elif action == "create_employee":
        create_roles = [
            "System Manager",
            "HR Manager",
            "HR User"
        ]

        can_create_employee = False

        for role_name in create_roles:
            if role_name in roles:
                can_create_employee = True

        if not can_create_employee:
            frappe.throw(
                "You do not have permission "
                "to create an Employee."
            )

        first_name = (
            frappe.form_dict.get("first_name")
            or ""
        ).strip()

        middle_name = (
            frappe.form_dict.get("middle_name")
            or ""
        ).strip()

        last_name = (
            frappe.form_dict.get("last_name")
            or ""
        ).strip()

        gender = (
            frappe.form_dict.get("gender")
            or ""
        ).strip()

        date_of_birth = (
            frappe.form_dict.get("date_of_birth")
            or ""
        ).strip()

        date_of_joining = (
            frappe.form_dict.get("date_of_joining")
            or ""
        ).strip()

        company = (
            frappe.form_dict.get("company")
            or ""
        ).strip()

        branch = (
            frappe.form_dict.get("branch")
            or ""
        ).strip()

        department = (
            frappe.form_dict.get("department")
            or ""
        ).strip()

        designation = (
            frappe.form_dict.get("designation")
            or ""
        ).strip()

        employment_type = (
            frappe.form_dict.get("employment_type")
            or ""
        ).strip()

        reports_to = (
            frappe.form_dict.get("reports_to")
            or ""
        ).strip()

        personal_mobile_no = (
            frappe.form_dict.get(
                "personal_mobile_no"
            )
            or ""
        ).strip()

        cell_number = (
            frappe.form_dict.get("cell_number")
            or personal_mobile_no
        ).strip()

        personal_email = (
            frappe.form_dict.get("personal_email")
            or ""
        ).strip()

        blood_group = (
            frappe.form_dict.get("blood_group")
            or ""
        ).strip()

        marital_status = (
            frappe.form_dict.get("marital_status")
            or ""
        ).strip()

        grade = (
            frappe.form_dict.get("grade")
            or ""
        ).strip()

        default_shift = (
            frappe.form_dict.get("default_shift")
            or ""
        ).strip()

        person_to_be_contacted = (
            frappe.form_dict.get(
                "person_to_be_contacted"
            )
            or ""
        ).strip()

        relation = (
            frappe.form_dict.get("relation")
            or ""
        ).strip()

        emergency_phone_number = (
            frappe.form_dict.get(
                "emergency_phone_number"
            )
            or ""
        ).strip()

        current_address = (
            frappe.form_dict.get("current_address")
            or ""
        ).strip()

        permanent_address = (
            frappe.form_dict.get(
                "permanent_address"
            )
            or ""
        ).strip()

        custom_aadhaar_number = (
            frappe.form_dict.get(
                "custom_aadhaar_number"
            )
            or ""
        ).strip()

        # HRMS_EMPLOYEE_EXTENDED_FIELDS_START

        attendance_device_id = (
            frappe.form_dict.get(
                "attendance_device_id"
            )
            or ""
        ).strip()

        holiday_list = (
            frappe.form_dict.get(
                "holiday_list"
            )
            or ""
        ).strip()

        shift_request_approver = (
            frappe.form_dict.get(
                "shift_request_approver"
            )
            or ""
        ).strip()

        company_email = (
            frappe.form_dict.get(
                "company_email"
            )
            or ""
        ).strip()

        pan_number = (
            frappe.form_dict.get(
                "pan_number"
            )
            or ""
        ).strip().upper()

        provident_fund_account = (
            frappe.form_dict.get(
                "provident_fund_account"
            )
            or ""
        ).strip()

        bank_name = (
            frappe.form_dict.get(
                "bank_name"
            )
            or ""
        ).strip()

        bank_ac_no = (
            frappe.form_dict.get(
                "bank_ac_no"
            )
            or ""
        ).strip()

        ifsc_code = (
            frappe.form_dict.get(
                "ifsc_code"
            )
            or ""
        ).strip().upper()

        salary_currency = (
            frappe.form_dict.get(
                "salary_currency"
            )
            or ""
        ).strip()

        salary_mode = (
            frappe.form_dict.get(
                "salary_mode"
            )
            or ""
        ).strip()

        ctc_text = (
            frappe.form_dict.get("ctc")
            or ""
        ).strip()

        ctc = None

        if ctc_text:
            ctc = frappe.utils.flt(
                ctc_text
            )

            if ctc < 0:
                frappe.throw(
                    "Annual CTC cannot be negative."
                )

        # HRMS_EMPLOYEE_EXTENDED_FIELDS_END

        mandatory_missing = []

        if not first_name:
            mandatory_missing.append("First Name")

        if not gender:
            mandatory_missing.append("Gender")

        if not date_of_birth:
            mandatory_missing.append(
                "Date of Birth"
            )

        if not date_of_joining:
            mandatory_missing.append(
                "Date of Joining"
            )

        if not company:
            mandatory_missing.append("Company")

        if not branch:
            mandatory_missing.append("Branch")

        if not department:
            mandatory_missing.append("Department")

        if not designation:
            mandatory_missing.append("Designation")

        if mandatory_missing:
            frappe.throw(
                "Missing mandatory fields: "
                + ", ".join(mandatory_missing)
            )

        # Validate live Link values
        link_checks = [
            ["Gender", gender, "Gender"],
            ["Company", company, "Company"],
            ["Branch", branch, "Branch"],
            [
                "Department",
                department,
                "Department"
            ],
            [
                "Designation",
                designation,
                "Designation"
            ]
        ]

        if employment_type:
            link_checks.append([
                "Employment Type",
                employment_type,
                "Employment Type"
            ])

        if reports_to:
            link_checks.append([
                "Employee",
                reports_to,
                "Reporting Manager"
            ])

        if grade:
            link_checks.append([
                "Employee Grade",
                grade,
                "Grade"
            ])

        if default_shift:
            link_checks.append([
                "Shift Type",
                default_shift,
                "Default Shift"
            ])

        if holiday_list:
            link_checks.append([
                "Holiday List",
                holiday_list,
                "Holiday List"
            ])

        if shift_request_approver:
            link_checks.append([
                "User",
                shift_request_approver,
                "Shift Request Approver"
            ])

        if salary_currency:
            link_checks.append([
                "Currency",
                salary_currency,
                "Salary Currency"
            ])

        for check in link_checks:
            link_doctype = check[0]
            link_value = check[1]
            link_label = check[2]

            if not frappe.db.exists(
                link_doctype,
                link_value
            ):
                frappe.throw(
                    link_label
                    + " does not exist: "
                    + link_value
                )

        if branch.lower() == "testing branch":
            frappe.throw(
                "Testing Branch cannot be selected."
            )

        if (
            personal_mobile_no
            and (
                not personal_mobile_no.isdigit()
                or len(personal_mobile_no) != 10
            )
        ):
            frappe.throw(
                "Personal Mobile must contain "
                "exactly 10 digits."
            )

        if (
            emergency_phone_number
            and (
                not emergency_phone_number.isdigit()
                or len(emergency_phone_number) != 10
            )
        ):
            frappe.throw(
                "Emergency Phone must contain "
                "exactly 10 digits."
            )

        if attendance_device_id:
            existing_device_employee = (
                frappe.db.exists(
                    "Employee",
                    {
                        "attendance_device_id":
                            attendance_device_id
                    }
                )
            )

            if existing_device_employee:
                frappe.throw(
                    "Attendance Device ID already "
                    "belongs to Employee: "
                    + existing_device_employee
                )

        employee_data = {
            "doctype": "Employee",
            "naming_series": "HR-EMP-",
            "first_name": first_name,
            "gender": gender,
            "date_of_birth": date_of_birth,
            "date_of_joining": date_of_joining,
            "status": "Active",
            "company": company,
            "branch": branch,
            "department": department,
            "designation": designation
        }

        optional_data = {
            "middle_name": middle_name,
            "last_name": last_name,
            "employment_type": employment_type,
            "reports_to": reports_to,
            "personal_mobile_no":
                personal_mobile_no,
            "cell_number": cell_number,
            "personal_email": personal_email,
            "blood_group": blood_group,
            "marital_status": marital_status,
            "grade": grade,
            "default_shift": default_shift,
            "person_to_be_contacted":
                person_to_be_contacted,
            "relation": relation,
            "emergency_phone_number":
                emergency_phone_number,
            "current_address": current_address,
            "permanent_address":
                permanent_address,
            "custom_aadhaar_number":
                custom_aadhaar_number,
            "attendance_device_id":
                attendance_device_id,
            "holiday_list":
                holiday_list,
            "shift_request_approver":
                shift_request_approver,
            "company_email":
                company_email,
            "pan_number":
                pan_number,
            "provident_fund_account":
                provident_fund_account,
            "bank_name":
                bank_name,
            "bank_ac_no":
                bank_ac_no,
            "ifsc_code":
                ifsc_code,
            "salary_currency":
                salary_currency,
            "salary_mode":
                salary_mode,
            "ctc":
                ctc
        }

        employee_meta = frappe.get_meta("Employee")

        for fieldname in optional_data:
            field_value = optional_data.get(
                fieldname
            )

            if (
                field_value
                and employee_meta.has_field(
                    fieldname
                )
            ):
                employee_data[fieldname] = (
                    field_value
                )

        employee_doc = frappe.get_doc(
            employee_data
        )

        # Employee is not submittable.
        # insert() saves it permanently in the backend.
        employee_doc.insert()

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action": "create_employee",
            "employee": employee_doc.name,
            "employee_name":
                employee_doc.employee_name,
            "branch": employee_doc.branch,
            "department":
                employee_doc.department,
            "designation":
                employee_doc.designation,
            "status": employee_doc.status,
            "message":
                "Employee saved successfully in ERPNext"
        }

    # HRMS_CREATE_EMPLOYEE_END



    # HRMS_ACTION_API_START

    elif action == "update_employee_status":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
            or "HR User" in roles
        )

        if not allowed:
            frappe.throw(
                "Not permitted to update Employee status."
            )

        employee = (
            frappe.form_dict.get("employee") or ""
        ).strip()

        new_status = (
            frappe.form_dict.get("status") or ""
        ).strip()

        reason = (
            frappe.form_dict.get("reason") or ""
        ).strip()

        effective_date = (
            frappe.form_dict.get("effective_date")
            or today
        ).strip()

        if not employee:
            frappe.throw("Employee is mandatory.")

        if not new_status:
            frappe.throw("Status is mandatory.")

        if not reason:
            frappe.throw("Reason is mandatory.")

        if new_status not in [
            "Active",
            "Inactive",
            "Suspended",
            "Left"
        ]:
            frappe.throw(
                "Invalid Employee status: "
                + new_status
            )

        if not frappe.db.exists("Employee", employee):
            frappe.throw(
                "Employee does not exist: " + employee
            )

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        old_status = employee_doc.status
        employee_doc.status = new_status

        if (
            new_status == "Left"
            and employee_doc.meta.has_field(
                "relieving_date"
            )
        ):
            employee_doc.relieving_date = (
                effective_date
            )

        if employee_doc.meta.has_field(
            "custom_hrms_last_action"
        ):
            employee_doc.custom_hrms_last_action = (
                "Status: "
                + str(old_status)
                + " to "
                + str(new_status)
            )

        if employee_doc.meta.has_field(
            "custom_hrms_last_action_on"
        ):
            employee_doc.custom_hrms_last_action_on = (
                frappe.utils.now()
            )

        if employee_doc.meta.has_field(
            "custom_hrms_last_action_by"
        ):
            employee_doc.custom_hrms_last_action_by = (
                current_user
            )

        if employee_doc.meta.has_field(
            "custom_hrms_action_reason"
        ):
            employee_doc.custom_hrms_action_reason = (
                reason
            )

        employee_doc.save()

        employee_doc.add_comment(
            "Comment",
            (
                "HRMS 360 status change: "
                + str(old_status)
                + " to "
                + str(new_status)
                + ". Effective: "
                + str(effective_date)
                + ". Reason: "
                + str(reason)
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action": "update_employee_status",
            "employee": employee_doc.name,
            "old_status": old_status,
            "new_status": employee_doc.status,
            "message": "Employee status updated"
        }


    elif action == "create_employee_transfer":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can submit transfers."
            )

        employee = (
            frappe.form_dict.get("employee") or ""
        ).strip()

        transfer_date = (
            frappe.form_dict.get("transfer_date")
            or today
        ).strip()

        new_branch = (
            frappe.form_dict.get("new_branch") or ""
        ).strip()

        new_department = (
            frappe.form_dict.get("new_department")
            or ""
        ).strip()

        new_designation = (
            frappe.form_dict.get("new_designation")
            or ""
        ).strip()

        reason = (
            frappe.form_dict.get("reason") or ""
        ).strip()

        if not employee:
            frappe.throw("Employee is mandatory.")

        if not transfer_date:
            frappe.throw(
                "Transfer Date is mandatory."
            )

        if not reason:
            frappe.throw(
                "Transfer Reason is mandatory."
            )

        if not (
            new_branch
            or new_department
            or new_designation
        ):
            frappe.throw(
                "Select a new Branch, Department "
                "or Designation."
            )

        if not frappe.db.exists("Employee", employee):
            frappe.throw(
                "Employee does not exist: " + employee
            )

        if new_branch:
            if new_branch.lower() == "testing branch":
                frappe.throw(
                    "Testing Branch cannot be selected."
                )

            if not frappe.db.exists(
                "Branch",
                new_branch
            ):
                frappe.throw(
                    "Branch does not exist: "
                    + new_branch
                )

        if (
            new_department
            and not frappe.db.exists(
                "Department",
                new_department
            )
        ):
            frappe.throw(
                "Department does not exist: "
                + new_department
            )

        if (
            new_designation
            and not frappe.db.exists(
                "Designation",
                new_designation
            )
        ):
            frappe.throw(
                "Designation does not exist: "
                + new_designation
            )

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        transfer_doc = frappe.get_doc({
            "doctype": "Employee Transfer",
            "employee": employee,
            "transfer_date": transfer_date,
            "company": employee_doc.company
        })

        if transfer_doc.meta.has_field(
            "custom_transfer_reason"
        ):
            transfer_doc.custom_transfer_reason = reason

        if transfer_doc.meta.has_field(
            "custom_requested_from_hrms"
        ):
            transfer_doc.custom_requested_from_hrms = 1

        if new_branch:
            transfer_doc.append(
                "transfer_details",
                {
                    "property": "Branch",
                    "fieldname": "branch",
                    "current":
                        employee_doc.branch or "",
                    "new": new_branch
                }
            )

        if new_department:
            transfer_doc.append(
                "transfer_details",
                {
                    "property": "Department",
                    "fieldname": "department",
                    "current":
                        employee_doc.department or "",
                    "new": new_department
                }
            )

        if new_designation:
            transfer_doc.append(
                "transfer_details",
                {
                    "property": "Designation",
                    "fieldname": "designation",
                    "current":
                        employee_doc.designation or "",
                    "new": new_designation
                }
            )

        transfer_doc.insert()
        transfer_doc.submit()

        employee_doc.add_comment(
            "Comment",
            (
                "HRMS 360 Transfer "
                + transfer_doc.name
                + ". Reason: "
                + reason
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action": "create_employee_transfer",
            "employee": employee,
            "transfer": transfer_doc.name,
            "docstatus": transfer_doc.docstatus,
            "message": "Employee Transfer submitted"
        }


    elif action == "create_employee_promotion":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can submit promotions."
            )

        employee = (
            frappe.form_dict.get("employee") or ""
        ).strip()

        promotion_date = (
            frappe.form_dict.get("promotion_date")
            or today
        ).strip()

        new_designation = (
            frappe.form_dict.get("new_designation")
            or ""
        ).strip()

        revised_ctc = (
            frappe.form_dict.get("revised_ctc")
            or ""
        ).strip()

        reason = (
            frappe.form_dict.get("reason") or ""
        ).strip()

        if not employee:
            frappe.throw("Employee is mandatory.")

        if not promotion_date:
            frappe.throw(
                "Promotion Date is mandatory."
            )

        if not new_designation:
            frappe.throw(
                "New Designation is mandatory."
            )

        if not reason:
            frappe.throw(
                "Promotion Reason is mandatory."
            )

        if not frappe.db.exists("Employee", employee):
            frappe.throw(
                "Employee does not exist: " + employee
            )

        if not frappe.db.exists(
            "Designation",
            new_designation
        ):
            frappe.throw(
                "Designation does not exist: "
                + new_designation
            )

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        promotion_doc = frappe.get_doc({
            "doctype": "Employee Promotion",
            "employee": employee,
            "promotion_date": promotion_date,
            "company": employee_doc.company
        })

        if promotion_doc.meta.has_field(
            "current_ctc"
        ):
            promotion_doc.current_ctc = (
                employee_doc.ctc or 0
            )

        if (
            revised_ctc
            and promotion_doc.meta.has_field(
                "revised_ctc"
            )
        ):
            promotion_doc.revised_ctc = float(
                revised_ctc
            )

        if promotion_doc.meta.has_field(
            "custom_promotion_reason"
        ):
            promotion_doc.custom_promotion_reason = (
                reason
            )

        if promotion_doc.meta.has_field(
            "custom_requested_from_hrms"
        ):
            promotion_doc.custom_requested_from_hrms = 1

        if promotion_doc.meta.has_field(
            "promotion_details"
        ):
            promotion_doc.append(
                "promotion_details",
                {
                    "property": "Designation",
                    "fieldname": "designation",
                    "current":
                        employee_doc.designation or "",
                    "new": new_designation
                }
            )

        promotion_doc.insert()
        promotion_doc.submit()

        employee_doc.add_comment(
            "Comment",
            (
                "HRMS 360 Promotion "
                + promotion_doc.name
                + ". Reason: "
                + reason
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action": "create_employee_promotion",
            "employee": employee,
            "promotion": promotion_doc.name,
            "docstatus": promotion_doc.docstatus,
            "message": "Employee Promotion submitted"
        }



    elif action == "create_employee_separation":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can create separations."
            )

        employee = (
            frappe.form_dict.get("employee")
            or ""
        ).strip()

        begins_on = (
            frappe.form_dict.get(
                "boarding_begins_on"
            )
            or today
        ).strip()

        reason = (
            frappe.form_dict.get("reason")
            or ""
        ).strip()

        separation_type = (
            frappe.form_dict.get(
                "separation_type"
            )
            or "Resignation"
        ).strip()

        last_working_day = (
            frappe.form_dict.get(
                "last_working_day"
            )
            or ""
        ).strip()

        eligible_for_rehire = (
            frappe.form_dict.get(
                "eligible_for_rehire"
            )
            or "To Be Decided"
        ).strip()

        separation_template = (
            frappe.form_dict.get(
                "employee_separation_template"
            )
            or ""
        ).strip()

        if not employee:
            frappe.throw(
                "Employee is mandatory."
            )

        if not reason:
            frappe.throw(
                "Separation Reason is mandatory."
            )

        if not frappe.db.exists(
            "Employee",
            employee
        ):
            frappe.throw(
                "Employee does not exist: "
                + employee
            )

        valid_separation_types = [
            "Resignation",
            "Termination",
            "Contract End",
            "Absconding",
            "Retirement",
            "Other"
        ]

        if (
            separation_type
            not in valid_separation_types
        ):
            frappe.throw(
                "Invalid Separation Type: "
                + separation_type
            )

        if eligible_for_rehire not in [
            "Yes",
            "No",
            "To Be Decided"
        ]:
            frappe.throw(
                "Invalid Eligible for Rehire value."
            )

        if (
            separation_template
            and not frappe.db.exists(
                "Employee Separation Template",
                separation_template
            )
        ):
            frappe.throw(
                "Separation Template does not exist: "
                + separation_template
            )

        # Prevent duplicate open separation records
        existing_separation = frappe.get_all(
            "Employee Separation",
            filters={
                "employee": employee,
                "docstatus": ["!=", 2],
                "boarding_status": [
                    "in",
                    ["Pending", "In Process"]
                ]
            },
            fields=["name"],
            order_by="creation desc",
            limit_page_length=1
        )

        if existing_separation:
            frappe.throw(
                "An open Employee Separation already "
                "exists: "
                + existing_separation[0].name
            )

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        separation_data = {
            "doctype": "Employee Separation",
            "employee": employee,
            "company": employee_doc.company,
            "boarding_begins_on": begins_on
        }

        if separation_template:
            separation_data[
                "employee_separation_template"
            ] = separation_template

        separation_doc = frappe.get_doc(
            separation_data
        )

        if separation_doc.meta.has_field(
            "custom_separation_reason"
        ):
            separation_doc.custom_separation_reason = (
                reason
            )

        if separation_doc.meta.has_field(
            "custom_separation_type"
        ):
            separation_doc.custom_separation_type = (
                separation_type
            )

        if (
            last_working_day
            and separation_doc.meta.has_field(
                "custom_last_working_day"
            )
        ):
            separation_doc.custom_last_working_day = (
                last_working_day
            )

        if separation_doc.meta.has_field(
            "custom_eligible_for_rehire"
        ):
            separation_doc.custom_eligible_for_rehire = (
                eligible_for_rehire
            )

        if separation_doc.meta.has_field(
            "custom_clearance_status"
        ):
            separation_doc.custom_clearance_status = (
                "Pending"
            )

        if separation_doc.meta.has_field(
            "custom_fnf_status"
        ):
            separation_doc.custom_fnf_status = (
                "Pending"
            )

        if separation_doc.meta.has_field(
            "custom_requested_from_hrms"
        ):
            separation_doc.custom_requested_from_hrms = 1

        # Keep separation as Draft for HR verification
        separation_doc.insert()

        # Notice is stored in the custom employment status.
        # Standard Employee status remains Active until F&F.
        if employee_doc.meta.has_field(
            "custom_employment_status"
        ):
            employee_doc.custom_employment_status = (
                "Notice"
            )
            employee_doc.save()

        employee_doc.add_comment(
            "Comment",
            (
                "HRMS 360 Separation "
                + separation_doc.name
                + " created as Draft. Type: "
                + separation_type
                + ". Last working day: "
                + str(last_working_day or "Not set")
                + ". Reason: "
                + reason
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "create_employee_separation",
            "employee": employee,
            "separation": separation_doc.name,
            "docstatus":
                separation_doc.docstatus,
            "message":
                "Employee Separation saved as Draft"
        }


    elif action == "update_employee_separation":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can update separations."
            )

        separation = (
            frappe.form_dict.get("separation")
            or ""
        ).strip()

        employee = (
            frappe.form_dict.get("employee")
            or ""
        ).strip()

        clearance_status = (
            frappe.form_dict.get(
                "clearance_status"
            )
            or ""
        ).strip()

        boarding_status = (
            frappe.form_dict.get(
                "boarding_status"
            )
            or ""
        ).strip()

        remarks = (
            frappe.form_dict.get("remarks")
            or ""
        ).strip()

        if not separation and not employee:
            frappe.throw(
                "Separation ID or Employee ID "
                "is mandatory."
            )

        if not separation:
            rows = frappe.get_all(
                "Employee Separation",
                filters={
                    "employee": employee,
                    "docstatus": ["!=", 2]
                },
                fields=["name"],
                order_by="creation desc",
                limit_page_length=1
            )

            if not rows:
                frappe.throw(
                    "No Employee Separation found "
                    "for " + employee
                )

            separation = rows[0].name

        if not frappe.db.exists(
            "Employee Separation",
            separation
        ):
            frappe.throw(
                "Employee Separation does not exist: "
                + separation
            )

        separation_doc = frappe.get_doc(
            "Employee Separation",
            separation
        )

        if separation_doc.docstatus == 2:
            frappe.throw(
                "Cancelled Separation cannot "
                "be updated."
            )

        # HRMS_STEP_26F_API_START
        current_fnf_status = (
            separation_doc.get(
                "custom_fnf_status"
            )
            or ""
        )

        current_clearance_status = (
            separation_doc.get(
                "custom_clearance_status"
            )
            or ""
        )

        if current_fnf_status == "Settled":
            frappe.throw(
                "Completed F&F Settlement cannot "
                "be modified from HRMS 360."
            )

        effective_clearance_status = (
            clearance_status
            or current_clearance_status
        )

        if (
            boarding_status == "Completed"
            and effective_clearance_status
            != "Completed"
        ):
            frappe.throw(
                "Clearance must be Completed before "
                "Separation Status can be Completed."
            )
        # HRMS_STEP_26F_API_END

        if clearance_status:
            if clearance_status not in [
                "Pending",
                "In Progress",
                "Completed",
                "Blocked"
            ]:
                frappe.throw(
                    "Invalid Clearance Status."
                )

            if separation_doc.meta.has_field(
                "custom_clearance_status"
            ):
                separation_doc.custom_clearance_status = (
                    clearance_status
                )

            if (
                clearance_status == "Completed"
                and separation_doc.meta.has_field(
                    "custom_clearance_completed_on"
                )
            ):
                separation_doc.custom_clearance_completed_on = (
                    today
                )

        if boarding_status:
            if boarding_status not in [
                "Pending",
                "In Process",
                "Completed"
            ]:
                frappe.throw(
                    "Invalid Separation Status."
                )

            separation_doc.boarding_status = (
                boarding_status
            )

        if remarks:
            if separation_doc.meta.has_field(
                "custom_fnf_remarks"
            ):
                old_remarks = (
                    separation_doc.custom_fnf_remarks
                    or ""
                )

                if old_remarks:
                    separation_doc.custom_fnf_remarks = (
                        old_remarks
                        + "\n"
                        + remarks
                    )
                else:
                    separation_doc.custom_fnf_remarks = (
                        remarks
                    )

        separation_doc.save()

        separation_doc.add_comment(
            "Comment",
            (
                "HRMS 360 Separation updated. "
                + "Clearance: "
                + str(
                    clearance_status
                    or separation_doc.get(
                        "custom_clearance_status"
                    )
                    or "Not changed"
                )
                + ". Status: "
                + str(
                    boarding_status
                    or separation_doc.boarding_status
                    or "Not changed"
                )
                + ". Remarks: "
                + str(remarks or "None")
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "update_employee_separation",
            "separation":
                separation_doc.name,
            "employee":
                separation_doc.employee,
            "clearance_status":
                separation_doc.get(
                    "custom_clearance_status"
                ),
            "boarding_status":
                separation_doc.boarding_status,
            "message":
                "Employee Separation updated"
        }


    elif action == "settle_employee_fnf":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can settle F&F."
            )

        separation = (
            frappe.form_dict.get("separation")
            or ""
        ).strip()

        employee = (
            frappe.form_dict.get("employee")
            or ""
        ).strip()

        settlement_date = (
            frappe.form_dict.get(
                "settlement_date"
            )
            or today
        ).strip()

        settlement_amount = (
            frappe.form_dict.get(
                "settlement_amount"
            )
            or "0"
        ).strip()

        reference = (
            frappe.form_dict.get("reference")
            or ""
        ).strip()

        remarks = (
            frappe.form_dict.get("remarks")
            or ""
        ).strip()

        if not separation and not employee:
            frappe.throw(
                "Separation ID or Employee ID "
                "is mandatory."
            )

        if not remarks:
            frappe.throw(
                "F&F settlement remarks "
                "are mandatory."
            )

        try:
            settlement_amount_value = float(
                settlement_amount
            )
        except:
            frappe.throw(
                "Settlement Amount must be numeric."
            )

        if settlement_amount_value < 0:
            frappe.throw(
                "Settlement Amount cannot be negative."
            )

        if not separation:
            rows = frappe.get_all(
                "Employee Separation",
                filters={
                    "employee": employee,
                    "docstatus": ["!=", 2]
                },
                fields=["name"],
                order_by="creation desc",
                limit_page_length=1
            )

            if not rows:
                frappe.throw(
                    "No Employee Separation found "
                    "for " + employee
                )

            separation = rows[0].name

        if not frappe.db.exists(
            "Employee Separation",
            separation
        ):
            frappe.throw(
                "Employee Separation does not exist: "
                + separation
            )

        separation_doc = frappe.get_doc(
            "Employee Separation",
            separation
        )

        if separation_doc.docstatus == 2:
            frappe.throw(
                "Cancelled Separation cannot "
                "be settled."
            )

        # HRMS_STEP_26F_FNF_START
        current_clearance_status = (
            separation_doc.get(
                "custom_clearance_status"
            )
            or ""
        )

        if current_clearance_status != "Completed":
            frappe.throw(
                "Clearance must be Completed before "
                "F&F can be settled."
            )

        current_fnf_status = (
            separation_doc.get(
                "custom_fnf_status"
            )
            or ""
        )

        if current_fnf_status == "Settled":
            frappe.throw(
                "F&F is already settled for "
                + separation_doc.employee
            )

        last_working_day = (
            separation_doc.get(
                "custom_last_working_day"
            )
            or ""
        )

        if (
            last_working_day
            and settlement_date
            < str(last_working_day)
        ):
            frappe.throw(
                "Settlement Date cannot be before "
                "the Last Working Day."
            )

        if (
            settlement_amount_value > 0
            and not reference
        ):
            frappe.throw(
                "Settlement Reference is mandatory "
                "when Settlement Amount is greater "
                "than zero."
            )
        # HRMS_STEP_26F_FNF_END

        if separation_doc.meta.has_field(
            "custom_fnf_status"
        ):
            if (
                separation_doc.custom_fnf_status
                == "Settled"
            ):
                frappe.throw(
                    "F&F is already settled for "
                    + separation_doc.employee
                )

            separation_doc.custom_fnf_status = (
                "Settled"
            )

        if separation_doc.meta.has_field(
            "custom_fnf_settlement_date"
        ):
            separation_doc.custom_fnf_settlement_date = (
                settlement_date
            )

        if separation_doc.meta.has_field(
            "custom_fnf_settlement_amount"
        ):
            separation_doc.custom_fnf_settlement_amount = (
                settlement_amount_value
            )

        if separation_doc.meta.has_field(
            "custom_fnf_reference"
        ):
            separation_doc.custom_fnf_reference = (
                reference
            )

        if separation_doc.meta.has_field(
            "custom_fnf_remarks"
        ):
            separation_doc.custom_fnf_remarks = (
                remarks
            )

        if separation_doc.meta.has_field(
            "custom_settled_by"
        ):
            separation_doc.custom_settled_by = (
                current_user
            )

        if separation_doc.meta.has_field(
            "custom_clearance_status"
        ):
            separation_doc.custom_clearance_status = (
                "Completed"
            )

        if separation_doc.meta.has_field(
            "custom_clearance_completed_on"
        ):
            separation_doc.custom_clearance_completed_on = (
                settlement_date
            )

        separation_doc.boarding_status = (
            "Completed"
        )

        separation_doc.save()

        employee_doc = frappe.get_doc(
            "Employee",
            separation_doc.employee
        )

        employee_doc.status = "Left"

        if employee_doc.meta.has_field(
            "custom_employment_status"
        ):
            employee_doc.custom_employment_status = (
                "Resigned"
            )

        if employee_doc.meta.has_field(
            "relieving_date"
        ):
            last_working_day = (
                separation_doc.get(
                    "custom_last_working_day"
                )
                or settlement_date
            )

            employee_doc.relieving_date = (
                last_working_day
            )

        if employee_doc.meta.has_field(
            "custom_hrms_last_action"
        ):
            employee_doc.custom_hrms_last_action = (
                "F&F Settled"
            )

        if employee_doc.meta.has_field(
            "custom_hrms_last_action_on"
        ):
            employee_doc.custom_hrms_last_action_on = (
                frappe.utils.now()
            )

        if employee_doc.meta.has_field(
            "custom_hrms_last_action_by"
        ):
            employee_doc.custom_hrms_last_action_by = (
                current_user
            )

        employee_doc.save()

        employee_doc.add_comment(
            "Comment",
            (
                "HRMS 360 F&F settled. "
                + "Separation: "
                + separation_doc.name
                + ". Date: "
                + settlement_date
                + ". Amount: "
                + str(settlement_amount_value)
                + ". Reference: "
                + str(reference or "None")
                + ". Remarks: "
                + remarks
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action": "settle_employee_fnf",
            "separation":
                separation_doc.name,
            "employee":
                employee_doc.name,
            "employee_status":
                employee_doc.status,
            "fnf_status": "Settled",
            "message":
                "F&F settled and Employee marked Left"
        }



    # HRMS_EMPLOYEE_MASTER_API_START

    elif action == "update_employee_master":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can update Employee master fields."
            )

        employee = (
            frappe.form_dict.get("employee")
            or ""
        ).strip()

        fieldname = (
            frappe.form_dict.get("fieldname")
            or ""
        ).strip()

        new_value = (
            frappe.form_dict.get("value")
            or ""
        ).strip()

        effective_date = (
            frappe.form_dict.get(
                "effective_date"
            )
            or today
        ).strip()

        reason = (
            frappe.form_dict.get("reason")
            or ""
        ).strip()

        remarks = (
            frappe.form_dict.get("remarks")
            or ""
        ).strip()

        if not employee:
            frappe.throw(
                "Employee is mandatory."
            )

        if not fieldname:
            frappe.throw(
                "Field Name is mandatory."
            )

        if not new_value:
            frappe.throw(
                "New Value is mandatory."
            )

        if not reason:
            frappe.throw(
                "Reason is mandatory."
            )

        if not frappe.db.exists(
            "Employee",
            employee
        ):
            frappe.throw(
                "Employee does not exist: "
                + employee
            )

        allowed_fields = {
            "department": {
                "label": "Department",
                "doctype": "Department"
            },
            "designation": {
                "label": "Designation",
                "doctype": "Designation"
            },
            "reports_to": {
                "label": "Reporting Manager",
                "doctype": "Employee"
            },
            "employment_type": {
                "label": "Employment Type",
                "doctype": "Employment Type"
            },
            "grade": {
                "label": "Employee Grade",
                "doctype": "Employee Grade"
            },
            "default_shift": {
                "label": "Default Shift",
                "doctype": "Shift Type"
            },
            "custom_employment_status": {
                "label": "Employment Status",
                "doctype": ""
            }
        }

        if fieldname not in allowed_fields:
            frappe.throw(
                "This field cannot be updated "
                "through HRMS 360: "
                + fieldname
            )

        field_config = allowed_fields[
            fieldname
        ]

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        if not employee_doc.meta.has_field(
            fieldname
        ):
            frappe.throw(
                "Employee field is missing: "
                + fieldname
            )

        if fieldname == "reports_to":
            if new_value == employee:
                frappe.throw(
                    "Employee cannot report "
                    "to themselves."
                )

            if not frappe.db.exists(
                "Employee",
                new_value
            ):
                frappe.throw(
                    "Reporting Manager does "
                    "not exist: "
                    + new_value
                )

            manager_status = frappe.db.get_value(
                "Employee",
                new_value,
                "status"
            )

            if manager_status != "Active":
                frappe.throw(
                    "Reporting Manager must "
                    "be an active employee."
                )

        elif field_config["doctype"]:
            if not frappe.db.exists(
                field_config["doctype"],
                new_value
            ):
                frappe.throw(
                    field_config["label"]
                    + " does not exist: "
                    + new_value
                )

        if (
            fieldname
            == "custom_employment_status"
        ):
            valid_employment_statuses = [
                "Probation",
                "Confirmed",
                "Notice",
                "Resigned"
            ]

            if (
                new_value
                not in valid_employment_statuses
            ):
                frappe.throw(
                    "Invalid Employment Status: "
                    + new_value
                )

        old_value = (
            employee_doc.get(fieldname)
            or ""
        )

        if str(old_value) == str(new_value):
            frappe.throw(
                field_config["label"]
                + " is already "
                + new_value
            )

        employee_doc.set(
            fieldname,
            new_value
        )

        if employee_doc.meta.has_field(
            "custom_hrms_last_action"
        ):
            employee_doc.custom_hrms_last_action = (
                field_config["label"]
                + ": "
                + str(old_value or "Not set")
                + " to "
                + str(new_value)
            )

        if employee_doc.meta.has_field(
            "custom_hrms_last_action_on"
        ):
            employee_doc.custom_hrms_last_action_on = (
                frappe.utils.now()
            )

        if employee_doc.meta.has_field(
            "custom_hrms_last_action_by"
        ):
            employee_doc.custom_hrms_last_action_by = (
                current_user
            )

        if employee_doc.meta.has_field(
            "custom_hrms_action_reason"
        ):
            employee_doc.custom_hrms_action_reason = (
                reason
            )

        employee_doc.save()

        history_text = (
            "HRMS 360 "
            + field_config["label"]
            + " changed from "
            + str(old_value or "Not set")
            + " to "
            + str(new_value)
            + ". Effective: "
            + str(effective_date)
            + ". Reason: "
            + reason
        )

        if remarks:
            history_text = (
                history_text
                + ". Remarks: "
                + remarks
            )

        employee_doc.add_comment(
            "Comment",
            history_text
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "update_employee_master",
            "employee":
                employee_doc.name,
            "fieldname": fieldname,
            "field_label":
                field_config["label"],
            "old_value": old_value,
            "new_value":
                employee_doc.get(fieldname),
            "effective_date":
                effective_date,
            "message":
                field_config["label"]
                + " updated successfully"
        }

    # HRMS_EMPLOYEE_MASTER_API_END


    # HRMS_SALARY_REVISION_API_START

    elif action == "create_salary_revision":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can create Salary Revisions."
            )

        employee = (
            frappe.form_dict.get("employee")
            or ""
        ).strip()

        revision_date = (
            frappe.form_dict.get(
                "revision_date"
            )
            or today
        ).strip()

        revised_ctc_text = (
            frappe.form_dict.get(
                "revised_ctc"
            )
            or ""
        ).strip()

        reason = (
            frappe.form_dict.get("reason")
            or ""
        ).strip()

        remarks = (
            frappe.form_dict.get("remarks")
            or ""
        ).strip()

        if not employee:
            frappe.throw(
                "Employee is mandatory."
            )

        if not revised_ctc_text:
            frappe.throw(
                "Revised CTC is mandatory."
            )

        if not reason:
            frappe.throw(
                "Salary Revision Reason "
                "is mandatory."
            )

        if not frappe.db.exists(
            "Employee",
            employee
        ):
            frappe.throw(
                "Employee does not exist: "
                + employee
            )

        try:
            revised_ctc = float(
                revised_ctc_text
            )
        except:
            frappe.throw(
                "Revised CTC must be numeric."
            )

        if revised_ctc <= 0:
            frappe.throw(
                "Revised CTC must be "
                "greater than zero."
            )

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        old_ctc = float(
            employee_doc.ctc or 0
        )

        if old_ctc == revised_ctc:
            frappe.throw(
                "Revised CTC is the same "
                "as the current CTC."
            )

        promotion_doc = frappe.get_doc({
            "doctype": "Employee Promotion",
            "employee": employee,
            "promotion_date": revision_date,
            "company": employee_doc.company
        })

        if promotion_doc.meta.has_field(
            "current_ctc"
        ):
            promotion_doc.current_ctc = old_ctc

        if promotion_doc.meta.has_field(
            "revised_ctc"
        ):
            promotion_doc.revised_ctc = (
                revised_ctc
            )

        if promotion_doc.meta.has_field(
            "custom_promotion_reason"
        ):
            promotion_doc.custom_promotion_reason = (
                reason
            )

        if promotion_doc.meta.has_field(
            "custom_requested_from_hrms"
        ):
            promotion_doc.custom_requested_from_hrms = 1

        if promotion_doc.meta.has_field(
            "promotion_details"
        ):
            promotion_doc.append(
                "promotion_details",
                {
                    "property": "CTC",
                    "fieldname": "ctc",
                    "current": old_ctc,
                    "new": revised_ctc
                }
            )

        promotion_doc.insert()
        promotion_doc.submit()

        employee_doc.add_comment(
            "Comment",
            (
                "HRMS 360 Salary Revision "
                + promotion_doc.name
                + ". Previous CTC: "
                + str(old_ctc)
                + ". Revised CTC: "
                + str(revised_ctc)
                + ". Effective: "
                + str(revision_date)
                + ". Reason: "
                + reason
                + (
                    ". Remarks: " + remarks
                    if remarks
                    else ""
                )
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "create_salary_revision",
            "employee": employee,
            "salary_revision":
                promotion_doc.name,
            "docstatus":
                promotion_doc.docstatus,
            "old_ctc": old_ctc,
            "revised_ctc": revised_ctc,
            "revision_date":
                revision_date,
            "message":
                "Salary Revision submitted"
        }

    # HRMS_SALARY_REVISION_API_END


    # HRMS_ASSET_MOVEMENT_API_START

    elif action == "assign_employee_asset":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
            or "Asset Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "You do not have permission "
                "to issue employee assets."
            )

        employee = (
            frappe.form_dict.get("employee")
            or ""
        ).strip()

        asset = (
            frappe.form_dict.get("asset")
            or ""
        ).strip()

        transaction_date = (
            frappe.form_dict.get(
                "transaction_date"
            )
            or frappe.utils.now()
        ).strip()

        reason = (
            frappe.form_dict.get("reason")
            or ""
        ).strip()

        if not employee:
            frappe.throw(
                "Employee is mandatory."
            )

        if not asset:
            frappe.throw(
                "Asset is mandatory."
            )

        if not reason:
            frappe.throw(
                "Asset Issue Reason is mandatory."
            )

        if not frappe.db.exists(
            "Employee",
            employee
        ):
            frappe.throw(
                "Employee does not exist: "
                + employee
            )

        if not frappe.db.exists(
            "Asset",
            asset
        ):
            frappe.throw(
                "Asset does not exist: "
                + asset
            )

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        asset_doc = frappe.get_doc(
            "Asset",
            asset
        )

        if asset_doc.docstatus != 1:
            frappe.throw(
                "Asset must be submitted "
                "before it can be issued."
            )

        current_custodian = (
            asset_doc.custodian
            if asset_doc.meta.has_field(
                "custodian"
            )
            else ""
        )

        if current_custodian:
            frappe.throw(
                "Asset is already assigned to: "
                + str(current_custodian)
            )

        movement = frappe.get_doc({
            "doctype": "Asset Movement",
            "company":
                asset_doc.company
                or employee_doc.company,
            "purpose": "Issue",
            "transaction_date":
                transaction_date
        })

        movement.append(
            "assets",
            {
                "asset": asset,
                "source_location":
                    asset_doc.location or "",
                "to_employee": employee
            }
        )

        movement.insert()
        movement.submit()

        asset_doc.add_comment(
            "Comment",
            (
                "Issued from HRMS 360 to "
                + employee
                + ". Asset Movement: "
                + movement.name
                + ". Reason: "
                + reason
            )
        )

        employee_doc.add_comment(
            "Comment",
            (
                "Asset "
                + asset
                + " issued through HRMS 360. "
                + "Asset Movement: "
                + movement.name
                + ". Reason: "
                + reason
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "assign_employee_asset",
            "employee": employee,
            "asset": asset,
            "asset_movement":
                movement.name,
            "docstatus":
                movement.docstatus,
            "message":
                "Asset issued successfully"
        }


    elif action == "return_employee_asset":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
            or "Asset Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "You do not have permission "
                "to receive employee assets."
            )

        employee = (
            frappe.form_dict.get("employee")
            or ""
        ).strip()

        asset = (
            frappe.form_dict.get("asset")
            or ""
        ).strip()

        target_location = (
            frappe.form_dict.get(
                "target_location"
            )
            or ""
        ).strip()

        transaction_date = (
            frappe.form_dict.get(
                "transaction_date"
            )
            or frappe.utils.now()
        ).strip()

        reason = (
            frappe.form_dict.get("reason")
            or ""
        ).strip()

        condition = (
            frappe.form_dict.get("condition")
            or ""
        ).strip()

        if not employee:
            frappe.throw(
                "Employee is mandatory."
            )

        if not asset:
            frappe.throw(
                "Asset is mandatory."
            )

        if not reason:
            frappe.throw(
                "Asset Return Reason is mandatory."
            )

        if not frappe.db.exists(
            "Employee",
            employee
        ):
            frappe.throw(
                "Employee does not exist: "
                + employee
            )

        if not frappe.db.exists(
            "Asset",
            asset
        ):
            frappe.throw(
                "Asset does not exist: "
                + asset
            )

        asset_doc = frappe.get_doc(
            "Asset",
            asset
        )

        if asset_doc.docstatus != 1:
            frappe.throw(
                "Asset must be submitted."
            )

        current_custodian = (
            asset_doc.custodian
            if asset_doc.meta.has_field(
                "custodian"
            )
            else ""
        )

        if (
            current_custodian
            and current_custodian != employee
        ):
            frappe.throw(
                "Asset is assigned to another "
                "employee: "
                + str(current_custodian)
            )

        if not target_location:
            target_location = (
                asset_doc.location or ""
            )

        if not target_location:
            frappe.throw(
                "Target Location is mandatory "
                "for an Asset Return."
            )

        if not frappe.db.exists(
            "Location",
            target_location
        ):
            frappe.throw(
                "Asset Location does not exist: "
                + target_location
            )

        movement = frappe.get_doc({
            "doctype": "Asset Movement",
            "company": asset_doc.company,
            "purpose": "Receipt",
            "transaction_date":
                transaction_date
        })

        movement.append(
            "assets",
            {
                "asset": asset,
                "from_employee": employee,
                "target_location":
                    target_location
            }
        )

        movement.insert()
        movement.submit()

        asset_doc.add_comment(
            "Comment",
            (
                "Returned through HRMS 360 by "
                + employee
                + ". Asset Movement: "
                + movement.name
                + ". Condition: "
                + str(condition or "Not specified")
                + ". Reason: "
                + reason
            )
        )

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        employee_doc.add_comment(
            "Comment",
            (
                "Asset "
                + asset
                + " returned through HRMS 360. "
                + "Asset Movement: "
                + movement.name
                + ". Condition: "
                + str(condition or "Not specified")
                + ". Reason: "
                + reason
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "return_employee_asset",
            "employee": employee,
            "asset": asset,
            "asset_movement":
                movement.name,
            "docstatus":
                movement.docstatus,
            "target_location":
                target_location,
            "message":
                "Asset returned successfully"
        }

    # HRMS_ASSET_MOVEMENT_API_END


    # HRMS_LEAVE_API_START

    elif action == "manage_leave_application":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
            or "HR User" in roles
        )

        if not allowed:
            frappe.throw(
                "You do not have permission "
                "to manage Leave Applications."
            )

        operation = (
            frappe.form_dict.get("operation")
            or "create"
        ).strip().lower()

        valid_operations = [
            "create",
            "submit",
            "approve",
            "reject",
            "cancel"
        ]

        if operation not in valid_operations:
            frappe.throw(
                "Invalid Leave operation: "
                + operation
            )

        # --------------------------------------------------------
        # Create a new Leave Application
        # --------------------------------------------------------

        if operation == "create":
            employee = (
                frappe.form_dict.get("employee")
                or ""
            ).strip()

            leave_type = (
                frappe.form_dict.get("leave_type")
                or ""
            ).strip()

            from_date = (
                frappe.form_dict.get("from_date")
                or ""
            ).strip()

            to_date = (
                frappe.form_dict.get("to_date")
                or ""
            ).strip()

            description = (
                frappe.form_dict.get("description")
                or ""
            ).strip()

            half_day_text = (
                frappe.form_dict.get("half_day")
                or "0"
            ).strip().lower()

            half_day = (
                half_day_text
                in ["1", "true", "yes"]
            )

            half_day_date = (
                frappe.form_dict.get(
                    "half_day_date"
                )
                or ""
            ).strip()

            submit_text = (
                frappe.form_dict.get("submit")
                or "0"
            ).strip().lower()

            submit_application = (
                submit_text
                in ["1", "true", "yes"]
            )

            if not employee:
                frappe.throw(
                    "Employee is mandatory."
                )

            if not leave_type:
                frappe.throw(
                    "Leave Type is mandatory."
                )

            if not from_date:
                frappe.throw(
                    "From Date is mandatory."
                )

            if not to_date:
                frappe.throw(
                    "To Date is mandatory."
                )

            if not description:
                frappe.throw(
                    "Leave reason is mandatory."
                )

            if not frappe.db.exists(
                "Employee",
                employee
            ):
                frappe.throw(
                    "Employee does not exist: "
                    + employee
                )

            if not frappe.db.exists(
                "Leave Type",
                leave_type
            ):
                frappe.throw(
                    "Leave Type does not exist: "
                    + leave_type
                )

            if from_date > to_date:
                frappe.throw(
                    "From Date cannot be after "
                    "To Date."
                )

            if half_day:
                if not half_day_date:
                    half_day_date = from_date

                if (
                    half_day_date < from_date
                    or half_day_date > to_date
                ):
                    frappe.throw(
                        "Half Day Date must be "
                        "within the leave period."
                    )

            employee_doc = frappe.get_doc(
                "Employee",
                employee
            )

            if employee_doc.status != "Active":
                frappe.throw(
                    "Leave can be created only "
                    "for an active employee."
                )

            duplicate = frappe.get_all(
                "Leave Application",
                filters={
                    "employee": employee,
                    "docstatus": ["!=", 2],
                    "status": [
                        "not in",
                        ["Rejected", "Cancelled"]
                    ],
                    "from_date": ["<=", to_date],
                    "to_date": [">=", from_date]
                },
                fields=["name"],
                limit_page_length=1
            )

            if duplicate:
                frappe.throw(
                    "An overlapping Leave Application "
                    "already exists: "
                    + duplicate[0].name
                )

            leave_data = {
                "doctype": "Leave Application",
                "employee": employee,
                "leave_type": leave_type,
                "from_date": from_date,
                "to_date": to_date,
                "description": description,
                "posting_date": today,
                "half_day": 1 if half_day else 0
            }

            if half_day:
                leave_data["half_day_date"] = (
                    half_day_date
                )

            leave_doc = frappe.get_doc(
                leave_data
            )

            leave_doc.insert()

            if submit_application:
                leave_doc.submit()

            leave_doc.add_comment(
                "Comment",
                (
                    "Created from HRMS 360 by "
                    + current_user
                    + ". Reason: "
                    + description
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_leave_application",
                "operation": "create",
                "leave_application":
                    leave_doc.name,
                "employee": employee,
                "status": leave_doc.status,
                "docstatus":
                    leave_doc.docstatus,
                "message": (
                    "Leave Application submitted"
                    if leave_doc.docstatus == 1
                    else
                    "Leave Application saved as Draft"
                )
            }

        # --------------------------------------------------------
        # Process an existing Leave Application
        # --------------------------------------------------------

        else:
            leave_application = (
                frappe.form_dict.get(
                    "leave_application"
                )
                or ""
            ).strip()

            remarks = (
                frappe.form_dict.get("remarks")
                or ""
            ).strip()

            if not leave_application:
                frappe.throw(
                    "Leave Application ID "
                    "is mandatory."
                )

            if not frappe.db.exists(
                "Leave Application",
                leave_application
            ):
                frappe.throw(
                    "Leave Application does not exist: "
                    + leave_application
                )

            leave_doc = frappe.get_doc(
                "Leave Application",
                leave_application
            )

            previous_status = (
                leave_doc.status or ""
            )

            previous_docstatus = (
                leave_doc.docstatus
            )

            if operation == "submit":
                if leave_doc.docstatus != 0:
                    frappe.throw(
                        "Only a Draft Leave Application "
                        "can be submitted."
                    )

                leave_doc.submit()

            elif operation == "approve":
                if leave_doc.docstatus == 2:
                    frappe.throw(
                        "Cancelled Leave Application "
                        "cannot be approved."
                    )

                if leave_doc.docstatus == 0:
                    leave_doc.status = "Approved"
                    leave_doc.submit()
                else:
                    if leave_doc.status != "Approved":
                        leave_doc.db_set(
                            "status",
                            "Approved",
                            update_modified=True
                        )

                    leave_doc.reload()

            elif operation == "reject":
                if leave_doc.docstatus == 2:
                    frappe.throw(
                        "Leave Application is "
                        "already cancelled."
                    )

                if leave_doc.docstatus == 1:
                    frappe.throw(
                        "Submitted Leave cannot be "
                        "directly rejected. Cancel it first."
                    )

                leave_doc.status = "Rejected"
                leave_doc.save()

            elif operation == "cancel":
                if leave_doc.docstatus != 1:
                    frappe.throw(
                        "Only a submitted Leave "
                        "Application can be cancelled."
                    )

                leave_doc.cancel()

            leave_doc.reload()

            leave_doc.add_comment(
                "Comment",
                (
                    "HRMS 360 Leave action: "
                    + operation.title()
                    + ". Previous status: "
                    + str(previous_status)
                    + ". New status: "
                    + str(leave_doc.status)
                    + ". Action by: "
                    + current_user
                    + ". Remarks: "
                    + str(remarks or "None")
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_leave_application",
                "operation": operation,
                "leave_application":
                    leave_doc.name,
                "employee":
                    leave_doc.employee,
                "previous_status":
                    previous_status,
                "previous_docstatus":
                    previous_docstatus,
                "status":
                    leave_doc.status,
                "docstatus":
                    leave_doc.docstatus,
                "message":
                    "Leave Application "
                    + operation.title()
                    + " successful"
            }

    # HRMS_LEAVE_API_END


    # HRMS_TIME_REQUEST_API_START

    elif action == "manage_time_request":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
            or "HR User" in roles
        )

        if not allowed:
            frappe.throw(
                "You do not have permission "
                "to manage attendance or shifts."
            )

        operation = (
            frappe.form_dict.get("operation")
            or ""
        ).strip().lower()

        valid_operations = [
            "create_attendance_request",
            "cancel_attendance_request",
            "create_shift_assignment",
            "cancel_shift_assignment"
        ]

        if operation not in valid_operations:
            frappe.throw(
                "Invalid time operation: "
                + operation
            )

        # ========================================================
        # CREATE ATTENDANCE REQUEST
        # ========================================================

        if operation == "create_attendance_request":
            employee = (
                frappe.form_dict.get("employee")
                or ""
            ).strip()

            from_date = (
                frappe.form_dict.get("from_date")
                or ""
            ).strip()

            to_date = (
                frappe.form_dict.get("to_date")
                or from_date
            ).strip()

            request_reason = (
                frappe.form_dict.get(
                    "request_reason"
                )
                or ""
            ).strip()

            explanation = (
                frappe.form_dict.get(
                    "explanation"
                )
                or ""
            ).strip()

            shift = (
                frappe.form_dict.get("shift")
                or ""
            ).strip()

            half_day_text = (
                frappe.form_dict.get("half_day")
                or "0"
            ).strip().lower()

            half_day = (
                half_day_text
                in ["1", "true", "yes"]
            )

            half_day_date = (
                frappe.form_dict.get(
                    "half_day_date"
                )
                or ""
            ).strip()

            include_holidays_text = (
                frappe.form_dict.get(
                    "include_holidays"
                )
                or "0"
            ).strip().lower()

            include_holidays = (
                include_holidays_text
                in ["1", "true", "yes"]
            )

            submit_text = (
                frappe.form_dict.get("submit")
                or "1"
            ).strip().lower()

            submit_request = (
                submit_text
                in ["1", "true", "yes"]
            )

            if not employee:
                frappe.throw(
                    "Employee is mandatory."
                )

            if not from_date:
                frappe.throw(
                    "From Date is mandatory."
                )

            if not to_date:
                frappe.throw(
                    "To Date is mandatory."
                )

            if not request_reason:
                frappe.throw(
                    "Attendance Request Reason "
                    "is mandatory."
                )

            if not explanation:
                frappe.throw(
                    "Explanation is mandatory."
                )

            if request_reason not in [
                "Work From Home",
                "On Duty"
            ]:
                frappe.throw(
                    "Reason must be Work From Home "
                    "or On Duty."
                )

            if from_date > to_date:
                frappe.throw(
                    "From Date cannot be after "
                    "To Date."
                )

            if not frappe.db.exists(
                "Employee",
                employee
            ):
                frappe.throw(
                    "Employee does not exist: "
                    + employee
                )

            employee_doc = frappe.get_doc(
                "Employee",
                employee
            )

            if employee_doc.status != "Active":
                frappe.throw(
                    "Attendance Request can be "
                    "created only for an active employee."
                )

            if shift:
                if not frappe.db.exists(
                    "Shift Type",
                    shift
                ):
                    frappe.throw(
                        "Shift Type does not exist: "
                        + shift
                    )

            if half_day:
                if not half_day_date:
                    half_day_date = from_date

                if (
                    half_day_date < from_date
                    or half_day_date > to_date
                ):
                    frappe.throw(
                        "Half Day Date must be within "
                        "the request period."
                    )

            duplicate = frappe.get_all(
                "Attendance Request",
                filters={
                    "employee": employee,
                    "docstatus": ["!=", 2],
                    "from_date": ["<=", to_date],
                    "to_date": [">=", from_date]
                },
                fields=["name"],
                limit_page_length=1
            )

            if duplicate:
                frappe.throw(
                    "An overlapping Attendance Request "
                    "already exists: "
                    + duplicate[0].name
                )

            request_data = {
                "doctype": "Attendance Request",
                "employee": employee,
                "company": employee_doc.company,
                "from_date": from_date,
                "to_date": to_date,
                "reason": request_reason,
                "explanation": explanation,
                "half_day":
                    1 if half_day else 0,
                "include_holidays":
                    1 if include_holidays else 0
            }

            if half_day:
                request_data["half_day_date"] = (
                    half_day_date
                )

            if shift:
                request_data["shift"] = shift

            request_doc = frappe.get_doc(
                request_data
            )

            request_doc.insert()

            if submit_request:
                request_doc.submit()

            request_doc.add_comment(
                "Comment",
                (
                    "Created from HRMS 360 by "
                    + current_user
                    + ". Reason: "
                    + request_reason
                    + ". Explanation: "
                    + explanation
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_time_request",
                "operation":
                    "create_attendance_request",
                "attendance_request":
                    request_doc.name,
                "employee": employee,
                "docstatus":
                    request_doc.docstatus,
                "message": (
                    "Attendance Request submitted"
                    if request_doc.docstatus == 1
                    else
                    "Attendance Request saved as Draft"
                )
            }

        # ========================================================
        # CANCEL ATTENDANCE REQUEST
        # ========================================================

        elif operation == "cancel_attendance_request":
            attendance_request = (
                frappe.form_dict.get(
                    "attendance_request"
                )
                or ""
            ).strip()

            remarks = (
                frappe.form_dict.get("remarks")
                or ""
            ).strip()

            if not attendance_request:
                frappe.throw(
                    "Attendance Request ID "
                    "is mandatory."
                )

            if not remarks:
                frappe.throw(
                    "Cancellation remarks "
                    "are mandatory."
                )

            if not frappe.db.exists(
                "Attendance Request",
                attendance_request
            ):
                frappe.throw(
                    "Attendance Request does not exist: "
                    + attendance_request
                )

            request_doc = frappe.get_doc(
                "Attendance Request",
                attendance_request
            )

            if request_doc.docstatus != 1:
                frappe.throw(
                    "Only a submitted Attendance "
                    "Request can be cancelled."
                )

            request_doc.add_comment(
                "Comment",
                (
                    "Cancelled from HRMS 360 by "
                    + current_user
                    + ". Remarks: "
                    + remarks
                )
            )

            request_doc.cancel()

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_time_request",
                "operation":
                    "cancel_attendance_request",
                "attendance_request":
                    request_doc.name,
                "docstatus":
                    request_doc.docstatus,
                "message":
                    "Attendance Request cancelled"
            }

        # ========================================================
        # CREATE SHIFT ASSIGNMENT
        # ========================================================

        elif operation == "create_shift_assignment":
            employee = (
                frappe.form_dict.get("employee")
                or ""
            ).strip()

            shift_type = (
                frappe.form_dict.get(
                    "shift_type"
                )
                or ""
            ).strip()

            start_date = (
                frappe.form_dict.get(
                    "start_date"
                )
                or today
            ).strip()

            end_date = (
                frappe.form_dict.get("end_date")
                or ""
            ).strip()

            shift_location = (
                frappe.form_dict.get(
                    "shift_location"
                )
                or ""
            ).strip()

            reason = (
                frappe.form_dict.get("reason")
                or ""
            ).strip()

            if not employee:
                frappe.throw(
                    "Employee is mandatory."
                )

            if not shift_type:
                frappe.throw(
                    "Shift Type is mandatory."
                )

            if not reason:
                frappe.throw(
                    "Shift Assignment Reason "
                    "is mandatory."
                )

            if not frappe.db.exists(
                "Employee",
                employee
            ):
                frappe.throw(
                    "Employee does not exist: "
                    + employee
                )

            if not frappe.db.exists(
                "Shift Type",
                shift_type
            ):
                frappe.throw(
                    "Shift Type does not exist: "
                    + shift_type
                )

            if (
                shift_location
                and not frappe.db.exists(
                    "Shift Location",
                    shift_location
                )
            ):
                frappe.throw(
                    "Shift Location does not exist: "
                    + shift_location
                )

            if (
                end_date
                and start_date > end_date
            ):
                frappe.throw(
                    "Start Date cannot be after "
                    "End Date."
                )

            employee_doc = frappe.get_doc(
                "Employee",
                employee
            )

            if employee_doc.status != "Active":
                frappe.throw(
                    "Shift can be assigned only "
                    "to an active employee."
                )

            assignment_data = {
                "doctype": "Shift Assignment",
                "employee": employee,
                "company": employee_doc.company,
                "shift_type": shift_type,
                "start_date": start_date,
                "status": "Active"
            }

            if end_date:
                assignment_data["end_date"] = (
                    end_date
                )

            if shift_location:
                assignment_data[
                    "shift_location"
                ] = shift_location

            assignment_doc = frappe.get_doc(
                assignment_data
            )

            assignment_doc.insert()
            assignment_doc.submit()

            employee_doc.add_comment(
                "Comment",
                (
                    "Shift "
                    + shift_type
                    + " assigned through HRMS 360. "
                    + "Shift Assignment: "
                    + assignment_doc.name
                    + ". Effective: "
                    + start_date
                    + ". Reason: "
                    + reason
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_time_request",
                "operation":
                    "create_shift_assignment",
                "shift_assignment":
                    assignment_doc.name,
                "employee": employee,
                "shift_type":
                    shift_type,
                "docstatus":
                    assignment_doc.docstatus,
                "message":
                    "Shift Assignment submitted"
            }

        # ========================================================
        # CANCEL SHIFT ASSIGNMENT
        # ========================================================

        elif operation == "cancel_shift_assignment":
            shift_assignment = (
                frappe.form_dict.get(
                    "shift_assignment"
                )
                or ""
            ).strip()

            remarks = (
                frappe.form_dict.get("remarks")
                or ""
            ).strip()

            if not shift_assignment:
                frappe.throw(
                    "Shift Assignment ID "
                    "is mandatory."
                )

            if not remarks:
                frappe.throw(
                    "Cancellation remarks "
                    "are mandatory."
                )

            if not frappe.db.exists(
                "Shift Assignment",
                shift_assignment
            ):
                frappe.throw(
                    "Shift Assignment does not exist: "
                    + shift_assignment
                )

            assignment_doc = frappe.get_doc(
                "Shift Assignment",
                shift_assignment
            )

            if assignment_doc.docstatus != 1:
                frappe.throw(
                    "Only a submitted Shift "
                    "Assignment can be cancelled."
                )

            assignment_doc.add_comment(
                "Comment",
                (
                    "Cancelled from HRMS 360 by "
                    + current_user
                    + ". Remarks: "
                    + remarks
                )
            )

            assignment_doc.cancel()

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_time_request",
                "operation":
                    "cancel_shift_assignment",
                "shift_assignment":
                    assignment_doc.name,
                "docstatus":
                    assignment_doc.docstatus,
                "message":
                    "Shift Assignment cancelled"
            }

    # HRMS_TIME_REQUEST_API_END


    # HRMS_TRAINING_API_START

    elif action == "manage_training_event":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
            or "HR User" in roles
        )

        if not allowed:
            frappe.throw(
                "You do not have permission "
                "to manage Training Events."
            )

        operation = (
            frappe.form_dict.get("operation")
            or "create"
        ).strip().lower()

        if operation not in [
            "create",
            "complete",
            "cancel"
        ]:
            frappe.throw(
                "Invalid Training operation: "
                + operation
            )

        # ========================================================
        # CREATE TRAINING EVENT
        # ========================================================

        if operation == "create":
            event_name = (
                frappe.form_dict.get(
                    "event_name"
                )
                or ""
            ).strip()

            training_program = (
                frappe.form_dict.get(
                    "training_program"
                )
                or ""
            ).strip()

            training_type = (
                frappe.form_dict.get(
                    "training_type"
                )
                or "Workshop"
            ).strip()

            training_level = (
                frappe.form_dict.get(
                    "training_level"
                )
                or ""
            ).strip()

            company = (
                frappe.form_dict.get("company")
                or ""
            ).strip()

            trainer_name = (
                frappe.form_dict.get(
                    "trainer_name"
                )
                or ""
            ).strip()

            trainer_email = (
                frappe.form_dict.get(
                    "trainer_email"
                )
                or ""
            ).strip()

            location = (
                frappe.form_dict.get("location")
                or ""
            ).strip()

            start_time = (
                frappe.form_dict.get(
                    "start_time"
                )
                or ""
            ).strip()

            end_time = (
                frappe.form_dict.get(
                    "end_time"
                )
                or ""
            ).strip()

            introduction = (
                frappe.form_dict.get(
                    "introduction"
                )
                or ""
            ).strip()

            employee_values = (
                frappe.form_dict.get("employees")
                or ""
            ).strip()

            submit_text = (
                frappe.form_dict.get("submit")
                or "1"
            ).strip().lower()

            submit_event = (
                submit_text
                in ["1", "true", "yes"]
            )

            if not event_name:
                frappe.throw(
                    "Event Name is mandatory."
                )

            if not location:
                frappe.throw(
                    "Training Location is mandatory."
                )

            if not start_time:
                frappe.throw(
                    "Start Time is mandatory."
                )

            if not end_time:
                frappe.throw(
                    "End Time is mandatory."
                )

            if not introduction:
                frappe.throw(
                    "Training Introduction "
                    "is mandatory."
                )

            if start_time >= end_time:
                frappe.throw(
                    "End Time must be after "
                    "Start Time."
                )

            valid_training_types = [
                "Seminar",
                "Theory",
                "Workshop",
                "Conference",
                "Exam",
                "Internet",
                "Self-Study"
            ]

            if (
                training_type
                not in valid_training_types
            ):
                frappe.throw(
                    "Invalid Training Type: "
                    + training_type
                )

            if training_level:
                if training_level not in [
                    "Beginner",
                    "Intermediate",
                    "Advance"
                ]:
                    frappe.throw(
                        "Invalid Training Level: "
                        + training_level
                    )

            if training_program:
                if not frappe.db.exists(
                    "Training Program",
                    training_program
                ):
                    frappe.throw(
                        "Training Program does not exist: "
                        + training_program
                    )

            employee_ids = []

            if employee_values:
                normalized_employees = (
                    employee_values
                    .replace("\n", ",")
                    .replace(";", ",")
                )

                for employee_value in (
                    normalized_employees.split(",")
                ):
                    employee_id = (
                        employee_value.strip()
                    )

                    if (
                        employee_id
                        and employee_id
                        not in employee_ids
                    ):
                        employee_ids.append(
                            employee_id
                        )

            if not employee_ids:
                frappe.throw(
                    "Select at least one employee."
                )

            employee_docs = []

            for employee_id in employee_ids:
                if not frappe.db.exists(
                    "Employee",
                    employee_id
                ):
                    frappe.throw(
                        "Employee does not exist: "
                        + employee_id
                    )

                employee_doc = frappe.get_doc(
                    "Employee",
                    employee_id
                )

                if employee_doc.status != "Active":
                    frappe.throw(
                        "Training can be assigned only "
                        "to active employees: "
                        + employee_id
                    )

                employee_docs.append(
                    employee_doc
                )

                if not company:
                    company = (
                        employee_doc.company
                        or ""
                    )

            if not company:
                frappe.throw(
                    "Company is mandatory."
                )

            if not frappe.db.exists(
                "Company",
                company
            ):
                frappe.throw(
                    "Company does not exist: "
                    + company
                )

            training_doc = frappe.get_doc({
                "doctype": "Training Event",
                "event_name": event_name,
                "training_program":
                    training_program or None,
                "event_status": "Scheduled",
                "type": training_type,
                "level":
                    training_level or None,
                "company": company,
                "trainer_name":
                    trainer_name,
                "trainer_email":
                    trainer_email,
                "location": location,
                "start_time": start_time,
                "end_time": end_time,
                "introduction":
                    introduction
            })

            for employee_doc in employee_docs:
                training_doc.append(
                    "employees",
                    {
                        "employee":
                            employee_doc.name,
                        "employee_name":
                            employee_doc.employee_name,
                        "department":
                            employee_doc.department,
                        "email":
                            (
                                employee_doc.company_email
                                or employee_doc.personal_email
                                or ""
                            )
                    }
                )

            training_doc.insert()

            if submit_event:
                training_doc.submit()

            for employee_doc in employee_docs:
                employee_doc.add_comment(
                    "Comment",
                    (
                        "Assigned to Training Event "
                        + training_doc.name
                        + " through HRMS 360. Event: "
                        + event_name
                        + ". Start: "
                        + start_time
                    )
                )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_training_event",
                "operation": "create",
                "training_event":
                    training_doc.name,
                "event_status":
                    training_doc.event_status,
                "docstatus":
                    training_doc.docstatus,
                "employees":
                    employee_ids,
                "message":
                    "Training Event created"
            }

        # ========================================================
        # COMPLETE OR CANCEL TRAINING EVENT
        # ========================================================

        else:
            training_event = (
                frappe.form_dict.get(
                    "training_event"
                )
                or ""
            ).strip()

            remarks = (
                frappe.form_dict.get("remarks")
                or ""
            ).strip()

            if not training_event:
                frappe.throw(
                    "Training Event ID "
                    "is mandatory."
                )

            if not remarks:
                frappe.throw(
                    "Remarks are mandatory."
                )

            if not frappe.db.exists(
                "Training Event",
                training_event
            ):
                frappe.throw(
                    "Training Event does not exist: "
                    + training_event
                )

            training_doc = frappe.get_doc(
                "Training Event",
                training_event
            )

            if training_doc.docstatus == 2:
                frappe.throw(
                    "Training Event is already cancelled."
                )

            old_status = (
                training_doc.event_status
                or ""
            )

            if operation == "complete":
                if training_doc.docstatus != 1:
                    frappe.throw(
                        "Only a submitted Training Event "
                        "can be completed."
                    )

                training_doc.db_set(
                    "event_status",
                    "Completed",
                    update_modified=True
                )

            elif operation == "cancel":
                if training_doc.docstatus == 1:
                    training_doc.db_set(
                        "event_status",
                        "Cancelled",
                        update_modified=True
                    )

                    training_doc.reload()
                    training_doc.cancel()

                else:
                    training_doc.event_status = (
                        "Cancelled"
                    )
                    training_doc.save()

            training_doc.reload()

            training_doc.add_comment(
                "Comment",
                (
                    "HRMS 360 Training action: "
                    + operation.title()
                    + ". Previous status: "
                    + old_status
                    + ". Remarks: "
                    + remarks
                    + ". Updated by: "
                    + current_user
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_training_event",
                "operation":
                    operation,
                "training_event":
                    training_doc.name,
                "event_status":
                    training_doc.event_status,
                "docstatus":
                    training_doc.docstatus,
                "message":
                    "Training Event "
                    + operation.title()
                    + " successful"
            }

    # HRMS_TRAINING_API_END


    # HRMS_RECRUITMENT_API_START

    elif action == "manage_recruitment":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
            or "HR User" in roles
        )

        if not allowed:
            frappe.throw(
                "You do not have permission "
                "to manage Recruitment."
            )

        operation = (
            frappe.form_dict.get("operation")
            or ""
        ).strip().lower()

        valid_operations = [
            "create_job_opening",
            "create_applicant",
            "update_applicant_status",
            "create_onboarding",
            "complete_onboarding",
            "cancel_onboarding"
        ]

        if operation not in valid_operations:
            frappe.throw(
                "Invalid Recruitment operation: "
                + operation
            )

        # ========================================================
        # CREATE JOB APPLICANT
        # ========================================================

        # HRMS_LIVE_JOB_OPENING_API_START
        if operation == "create_job_opening":
            designation = (
                frappe.form_dict.get(
                    "designation"
                )
                or ""
            ).strip()

            department = (
                frappe.form_dict.get(
                    "department"
                )
                or ""
            ).strip()

            company = (
                frappe.form_dict.get(
                    "company"
                )
                or ""
            ).strip()

            location = (
                frappe.form_dict.get(
                    "location"
                )
                or ""
            ).strip()

            employment_type = (
                frappe.form_dict.get(
                    "employment_type"
                )
                or ""
            ).strip()

            closes_on = (
                frappe.form_dict.get(
                    "closes_on"
                )
                or ""
            ).strip()

            vacancies = frappe.utils.cint(
                frappe.form_dict.get(
                    "vacancies"
                )
                or 0
            )

            priority = (
                frappe.form_dict.get(
                    "priority"
                )
                or "MISSING"
            ).strip()

            grade = (
                frappe.form_dict.get(
                    "grade"
                )
                or "MISSING"
            ).strip()

            experience_min = (
                frappe.form_dict.get(
                    "experience_min"
                )
                or "MISSING"
            ).strip()

            experience_max = (
                frappe.form_dict.get(
                    "experience_max"
                )
                or "MISSING"
            ).strip()

            education = (
                frappe.form_dict.get(
                    "education"
                )
                or "MISSING"
            ).strip()

            skills = (
                frappe.form_dict.get(
                    "skills"
                )
                or "MISSING"
            ).strip()

            responsibilities = (
                frappe.form_dict.get(
                    "responsibilities"
                )
                or "MISSING"
            ).strip()

            selection_rounds = (
                frappe.form_dict.get(
                    "selection_rounds"
                )
                or "MISSING"
            ).strip()

            hiring_manager = (
                frappe.form_dict.get(
                    "hiring_manager"
                )
                or "MISSING"
            ).strip()

            contact_phone = (
                frappe.form_dict.get(
                    "contact_phone"
                )
                or "MISSING"
            ).strip()

            contact_email = (
                frappe.form_dict.get(
                    "contact_email"
                )
                or "MISSING"
            ).strip()

            lower_range = frappe.utils.flt(
                frappe.form_dict.get(
                    "lower_range"
                )
                or 0
            )

            upper_range = frappe.utils.flt(
                frappe.form_dict.get(
                    "upper_range"
                )
                or 0
            )

            if not designation:
                frappe.throw(
                    "Designation is mandatory."
                )

            if not company:
                frappe.throw(
                    "MISSING: Live Company value "
                    "is required."
                )

            if not location:
                frappe.throw(
                    "Branch is mandatory."
                )

            if (
                location.lower()
                == "testing branch"
            ):
                frappe.throw(
                    "Testing Branch cannot be used."
                )

            if not closes_on:
                frappe.throw(
                    "Apply-before date is mandatory."
                )

            if vacancies <= 0:
                frappe.throw(
                    "Vacancies must be greater "
                    "than zero."
                )

            if (
                upper_range
                and lower_range > upper_range
            ):
                frappe.throw(
                    "Minimum salary cannot exceed "
                    "maximum salary."
                )

            if not frappe.db.exists(
                "Designation",
                designation
            ):
                frappe.throw(
                    "Designation does not exist: "
                    + designation
                )

            if not frappe.db.exists(
                "Company",
                company
            ):
                frappe.throw(
                    "Company does not exist: "
                    + company
                )

            if not frappe.db.exists(
                "Branch",
                location
            ):
                frappe.throw(
                    "Branch does not exist: "
                    + location
                )

            if (
                department
                and not frappe.db.exists(
                    "Department",
                    department
                )
            ):
                frappe.throw(
                    "Department does not exist: "
                    + department
                )

            if (
                employment_type
                and not frappe.db.exists(
                    "Employment Type",
                    employment_type
                )
            ):
                frappe.throw(
                    "Employment Type does not exist: "
                    + employment_type
                )

            job_title = (
                designation
                + " - "
                + location
                + " - "
                + closes_on
            )

            duplicate = frappe.get_all(
                "Job Opening",
                filters={
                    "job_title": job_title,
                    "company": company,
                    "status": "Open"
                },
                fields=[
                    "name",
                    "route"
                ],
                limit_page_length=1
            )

            if duplicate:
                frappe.throw(
                    "An open Job Opening already exists: "
                    + duplicate[0].name
                )

            description = (
                "Vacancies: "
                + str(vacancies)
                + "\nPriority: "
                + priority
                + "\nEmployee Grade: "
                + grade
                + "\nExperience: "
                + experience_min
                + " to "
                + experience_max
                + " years"
                + "\nEducation: "
                + education
                + "\nSkills: "
                + skills
                + "\nResponsibilities: "
                + responsibilities
                + "\nSelection Rounds: "
                + selection_rounds
                + "\nHiring Manager: "
                + hiring_manager
                + "\nContact Phone: "
                + contact_phone
                + "\nContact Email: "
                + contact_email
                + "\nCreated from LIFE HRMS 360 by: "
                + current_user
            )

            job_data = {
                "doctype": "Job Opening",
                "job_title": job_title,
                "designation": designation,
                "company": company,
                "location": location,
                "status": "Open",
                "closes_on": closes_on,
                "publish": 1,
                "publish_applications_received": 1,
                "description": description,
                "salary_per": "Month",
                "publish_salary_range":
                    1 if (
                        lower_range
                        or upper_range
                    ) else 0,
                "lower_range": lower_range,
                "upper_range": upper_range
            }

            if department:
                job_data["department"] = (
                    department
                )

            if employment_type:
                job_data[
                    "employment_type"
                ] = employment_type

            if frappe.db.exists(
                "Currency",
                "INR"
            ):
                job_data["currency"] = "INR"

            job_doc = frappe.get_doc(
                job_data
            )

            job_doc.insert()

            job_doc.add_comment(
                "Comment",
                (
                    "Created live from LIFE HRMS 360 by "
                    + current_user
                )
            )

            frappe.db.commit()

            public_route = (
                job_doc.route
                or ""
            ).strip()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_recruitment",
                "operation":
                    "create_job_opening",
                "job_opening":
                    job_doc.name,
                "job_title":
                    job_doc.job_title,
                "status":
                    job_doc.status,
                "route":
                    public_route,
                "apply_link":
                    (
                        "/"
                        + public_route.lstrip("/")
                    )
                    if public_route
                    else "MISSING",
                "message":
                    "Job Opening created in ERPNext"
            }

        # HRMS_LIVE_JOB_OPENING_API_END

        elif operation == "create_applicant":
            applicant_name = (
                frappe.form_dict.get(
                    "applicant_name"
                )
                or ""
            ).strip()

            email_id = (
                frappe.form_dict.get("email_id")
                or ""
            ).strip().lower()

            phone_number = (
                frappe.form_dict.get(
                    "phone_number"
                )
                or ""
            ).strip()

            job_opening = (
                frappe.form_dict.get(
                    "job_opening"
                )
                or ""
            ).strip()

            designation = (
                frappe.form_dict.get(
                    "designation"
                )
                or ""
            ).strip()

            source = (
                frappe.form_dict.get("source")
                or ""
            ).strip()

            source_employee = (
                frappe.form_dict.get(
                    "source_employee"
                )
                or ""
            ).strip()

            cover_letter = (
                frappe.form_dict.get(
                    "cover_letter"
                )
                or ""
            ).strip()

            resume_attachment = (
                frappe.form_dict.get(
                    "resume_attachment"
                )
                or ""
            ).strip()

            if not applicant_name:
                frappe.throw(
                    "Applicant Name is mandatory."
                )

            if not email_id:
                frappe.throw(
                    "Email Address is mandatory."
                )

            if not phone_number:
                frappe.throw(
                    "Phone Number is mandatory."
                )

            duplicate_filters = [
                ["email_id", "=", email_id]
            ]

            duplicate = frappe.get_all(
                "Job Applicant",
                filters=duplicate_filters,
                fields=["name", "applicant_name"],
                limit_page_length=1
            )

            if duplicate:
                frappe.throw(
                    "A Job Applicant already exists "
                    "with this email: "
                    + duplicate[0].name
                )

            if job_opening:
                if not frappe.db.exists(
                    "Job Opening",
                    job_opening
                ):
                    frappe.throw(
                        "Job Opening does not exist: "
                        + job_opening
                    )

            if designation:
                if not frappe.db.exists(
                    "Designation",
                    designation
                ):
                    frappe.throw(
                        "Designation does not exist: "
                        + designation
                    )

            if source:
                if not frappe.db.exists(
                    "Job Applicant Source",
                    source
                ):
                    frappe.throw(
                        "Applicant Source does not exist: "
                        + source
                    )

            if source_employee:
                if not frappe.db.exists(
                    "Employee",
                    source_employee
                ):
                    frappe.throw(
                        "Source Employee does not exist: "
                        + source_employee
                    )

            applicant_data = {
                "doctype": "Job Applicant",
                "applicant_name": applicant_name,
                "email_id": email_id,
                "phone_number": phone_number,
                "status": "Open"
            }

            if job_opening:
                applicant_data["job_title"] = (
                    job_opening
                )

            if designation:
                applicant_data["designation"] = (
                    designation
                )

            if source:
                applicant_data["source"] = source

            if source_employee:
                applicant_data["source_name"] = (
                    source_employee
                )

            if cover_letter:
                applicant_data["cover_letter"] = (
                    cover_letter
                )

            if resume_attachment:
                applicant_data[
                    "resume_attachment"
                ] = resume_attachment

            applicant_doc = frappe.get_doc(
                applicant_data
            )

            applicant_doc.insert()

            applicant_doc.add_comment(
                "Comment",
                (
                    "Created from HRMS 360 by "
                    + current_user
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_recruitment",
                "operation":
                    "create_applicant",
                "job_applicant":
                    applicant_doc.name,
                "status":
                    applicant_doc.status,
                "message":
                    "Job Applicant created"
            }

        # ========================================================
        # UPDATE JOB APPLICANT STATUS
        # ========================================================

        elif operation == "update_applicant_status":
            job_applicant = (
                frappe.form_dict.get(
                    "job_applicant"
                )
                or ""
            ).strip()

            new_status = (
                frappe.form_dict.get("status")
                or ""
            ).strip()

            remarks = (
                frappe.form_dict.get("remarks")
                or ""
            ).strip()

            if not job_applicant:
                frappe.throw(
                    "Job Applicant ID is mandatory."
                )

            if new_status not in [
                "Open",
                "Replied",
                "Rejected",
                "Hold",
                "Accepted"
            ]:
                frappe.throw(
                    "Invalid Applicant Status: "
                    + new_status
                )

            if not remarks:
                frappe.throw(
                    "Status remarks are mandatory."
                )

            if not frappe.db.exists(
                "Job Applicant",
                job_applicant
            ):
                frappe.throw(
                    "Job Applicant does not exist: "
                    + job_applicant
                )

            applicant_doc = frappe.get_doc(
                "Job Applicant",
                job_applicant
            )

            old_status = (
                applicant_doc.status or ""
            )

            applicant_doc.status = new_status
            applicant_doc.save()

            applicant_doc.add_comment(
                "Comment",
                (
                    "HRMS 360 Applicant Status: "
                    + old_status
                    + " to "
                    + new_status
                    + ". Remarks: "
                    + remarks
                    + ". Updated by: "
                    + current_user
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_recruitment",
                "operation":
                    "update_applicant_status",
                "job_applicant":
                    applicant_doc.name,
                "old_status":
                    old_status,
                "status":
                    applicant_doc.status,
                "message":
                    "Applicant Status updated"
            }

        # ========================================================
        # CREATE EMPLOYEE ONBOARDING
        # ========================================================

        elif operation == "create_onboarding":
            job_applicant = (
                frappe.form_dict.get(
                    "job_applicant"
                )
                or ""
            ).strip()

            job_offer = (
                frappe.form_dict.get(
                    "job_offer"
                )
                or ""
            ).strip()

            company = (
                frappe.form_dict.get("company")
                or ""
            ).strip()

            department = (
                frappe.form_dict.get(
                    "department"
                )
                or ""
            ).strip()

            designation = (
                frappe.form_dict.get(
                    "designation"
                )
                or ""
            ).strip()

            employee_grade = (
                frappe.form_dict.get(
                    "employee_grade"
                )
                or ""
            ).strip()

            holiday_list = (
                frappe.form_dict.get(
                    "holiday_list"
                )
                or ""
            ).strip()

            date_of_joining = (
                frappe.form_dict.get(
                    "date_of_joining"
                )
                or ""
            ).strip()

            boarding_begins_on = (
                frappe.form_dict.get(
                    "boarding_begins_on"
                )
                or today
            ).strip()

            onboarding_template = (
                frappe.form_dict.get(
                    "employee_onboarding_template"
                )
                or ""
            ).strip()

            notify_text = (
                frappe.form_dict.get(
                    "notify_users_by_email"
                )
                or "0"
            ).strip().lower()

            notify_users = (
                notify_text
                in ["1", "true", "yes"]
            )

            if not job_applicant:
                frappe.throw(
                    "Job Applicant is mandatory."
                )

            if not job_offer:
                frappe.throw(
                    "Job Offer is mandatory."
                )

            if not date_of_joining:
                frappe.throw(
                    "Date of Joining is mandatory."
                )

            if not frappe.db.exists(
                "Job Applicant",
                job_applicant
            ):
                frappe.throw(
                    "Job Applicant does not exist: "
                    + job_applicant
                )

            if not frappe.db.exists(
                "Job Offer",
                job_offer
            ):
                frappe.throw(
                    "Job Offer does not exist: "
                    + job_offer
                )

            applicant_doc = frappe.get_doc(
                "Job Applicant",
                job_applicant
            )

            job_offer_doc = frappe.get_doc(
                "Job Offer",
                job_offer
            )

            if (
                job_offer_doc.meta.has_field(
                    "job_applicant"
                )
                and job_offer_doc.job_applicant
                and job_offer_doc.job_applicant
                    != job_applicant
            ):
                frappe.throw(
                    "Job Offer belongs to a different "
                    "Job Applicant."
                )

            if job_offer_doc.docstatus != 1:
                frappe.throw(
                    "Job Offer must be submitted "
                    "before onboarding."
                )

            if applicant_doc.status != "Accepted":
                frappe.throw(
                    "Job Applicant must have "
                    "Accepted status."
                )

            if not company:
                if job_offer_doc.meta.has_field(
                    "company"
                ):
                    company = (
                        job_offer_doc.company or ""
                    )

            if not company:
                frappe.throw(
                    "Company is mandatory."
                )

            if not frappe.db.exists(
                "Company",
                company
            ):
                frappe.throw(
                    "Company does not exist: "
                    + company
                )

            link_checks = [
                [
                    "Department",
                    department,
                    "Department"
                ],
                [
                    "Designation",
                    designation,
                    "Designation"
                ],
                [
                    "Employee Grade",
                    employee_grade,
                    "Employee Grade"
                ],
                [
                    "Holiday List",
                    holiday_list,
                    "Holiday List"
                ],
                [
                    "Employee Onboarding Template",
                    onboarding_template,
                    "Onboarding Template"
                ]
            ]

            for link_check in link_checks:
                if (
                    link_check[1]
                    and not frappe.db.exists(
                        link_check[0],
                        link_check[1]
                    )
                ):
                    frappe.throw(
                        link_check[2]
                        + " does not exist: "
                        + link_check[1]
                    )

            duplicate = frappe.get_all(
                "Employee Onboarding",
                filters={
                    "job_applicant":
                        job_applicant,
                    "docstatus": ["!=", 2]
                },
                fields=["name"],
                limit_page_length=1
            )

            if duplicate:
                frappe.throw(
                    "Employee Onboarding already exists: "
                    + duplicate[0].name
                )

            onboarding_data = {
                "doctype":
                    "Employee Onboarding",
                "job_applicant":
                    job_applicant,
                "job_offer":
                    job_offer,
                "company":
                    company,
                "employee_name":
                    applicant_doc.applicant_name,
                "date_of_joining":
                    date_of_joining,
                "boarding_begins_on":
                    boarding_begins_on,
                "notify_users_by_email":
                    1 if notify_users else 0
            }

            if department:
                onboarding_data["department"] = (
                    department
                )

            if designation:
                onboarding_data["designation"] = (
                    designation
                )

            if employee_grade:
                onboarding_data["employee_grade"] = (
                    employee_grade
                )

            if holiday_list:
                onboarding_data["holiday_list"] = (
                    holiday_list
                )

            if onboarding_template:
                onboarding_data[
                    "employee_onboarding_template"
                ] = onboarding_template

            onboarding_doc = frappe.get_doc(
                onboarding_data
            )

            onboarding_doc.insert()
            onboarding_doc.submit()

            onboarding_doc.add_comment(
                "Comment",
                (
                    "Employee Onboarding created "
                    "from HRMS 360 by "
                    + current_user
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_recruitment",
                "operation":
                    "create_onboarding",
                "employee_onboarding":
                    onboarding_doc.name,
                "job_applicant":
                    job_applicant,
                "job_offer":
                    job_offer,
                "boarding_status":
                    onboarding_doc.boarding_status,
                "docstatus":
                    onboarding_doc.docstatus,
                "message":
                    "Employee Onboarding submitted"
            }

        # ========================================================
        # COMPLETE OR CANCEL ONBOARDING
        # ========================================================

        else:
            employee_onboarding = (
                frappe.form_dict.get(
                    "employee_onboarding"
                )
                or ""
            ).strip()

            remarks = (
                frappe.form_dict.get("remarks")
                or ""
            ).strip()

            if not employee_onboarding:
                frappe.throw(
                    "Employee Onboarding ID "
                    "is mandatory."
                )

            if not remarks:
                frappe.throw(
                    "Remarks are mandatory."
                )

            if not frappe.db.exists(
                "Employee Onboarding",
                employee_onboarding
            ):
                frappe.throw(
                    "Employee Onboarding does not exist: "
                    + employee_onboarding
                )

            onboarding_doc = frappe.get_doc(
                "Employee Onboarding",
                employee_onboarding
            )

            if onboarding_doc.docstatus == 2:
                frappe.throw(
                    "Employee Onboarding is "
                    "already cancelled."
                )

            if operation == "complete_onboarding":
                if onboarding_doc.docstatus != 1:
                    frappe.throw(
                        "Only submitted Onboarding "
                        "can be completed."
                    )

                onboarding_doc.db_set(
                    "boarding_status",
                    "Completed",
                    update_modified=True
                )

            elif operation == "cancel_onboarding":
                if onboarding_doc.docstatus != 1:
                    frappe.throw(
                        "Only submitted Onboarding "
                        "can be cancelled."
                    )

                onboarding_doc.add_comment(
                    "Comment",
                    (
                        "Cancelled through HRMS 360. "
                        + "Remarks: "
                        + remarks
                        + ". Cancelled by: "
                        + current_user
                    )
                )

                onboarding_doc.cancel()

            onboarding_doc.reload()

            onboarding_doc.add_comment(
                "Comment",
                (
                    "HRMS 360 Onboarding action: "
                    + operation
                    + ". Remarks: "
                    + remarks
                    + ". Updated by: "
                    + current_user
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_recruitment",
                "operation":
                    operation,
                "employee_onboarding":
                    onboarding_doc.name,
                "boarding_status":
                    onboarding_doc.boarding_status,
                "docstatus":
                    onboarding_doc.docstatus,
                "message":
                    "Employee Onboarding updated"
            }

    # HRMS_RECRUITMENT_API_END


    # HRMS_EMPLOYEE_ASSIGNMENT_API_START

    elif action == "manage_employee_assignment":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can manage employee assignments."
            )

        operation = (
            frappe.form_dict.get("operation")
            or ""
        ).strip().lower()

        valid_operations = [
            "assign_role",
            "assign_responsibility",
            "clear_role",
            "clear_responsibility"
        ]

        if operation not in valid_operations:
            frappe.throw(
                "Invalid Employee Assignment "
                "operation: "
                + operation
            )

        employee = (
            frappe.form_dict.get("employee")
            or ""
        ).strip()

        role_name = (
            frappe.form_dict.get("role")
            or ""
        ).strip()

        responsibility = (
            frappe.form_dict.get(
                "responsibility"
            )
            or ""
        ).strip()

        effective_from = (
            frappe.form_dict.get(
                "effective_from"
            )
            or today
        ).strip()

        effective_to = (
            frappe.form_dict.get(
                "effective_to"
            )
            or ""
        ).strip()

        reason = (
            frappe.form_dict.get("reason")
            or ""
        ).strip()

        remarks = (
            frappe.form_dict.get("remarks")
            or ""
        ).strip()

        if not employee:
            frappe.throw(
                "Employee is mandatory."
            )

        if not reason:
            frappe.throw(
                "Assignment Reason is mandatory."
            )

        if not frappe.db.exists(
            "Employee",
            employee
        ):
            frappe.throw(
                "Employee does not exist: "
                + employee
            )

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        if employee_doc.status != "Active":
            frappe.throw(
                "Role or Responsibility can be "
                "assigned only to an active employee."
            )

        old_role = (
            employee_doc.get(
                "custom_additional_role"
            )
            or ""
        )

        old_responsibility = (
            employee_doc.get(
                "custom_current_responsibility"
            )
            or ""
        )

        if operation == "assign_role":
            if not role_name:
                frappe.throw(
                    "Additional Role is mandatory."
                )

            employee_doc.custom_additional_role = (
                role_name
            )

            action_description = (
                "Additional Role changed from "
                + str(old_role or "None")
                + " to "
                + role_name
            )

        elif operation == "assign_responsibility":
            if not responsibility:
                frappe.throw(
                    "Responsibility is mandatory."
                )

            if (
                effective_to
                and effective_from > effective_to
            ):
                frappe.throw(
                    "Responsibility From Date cannot "
                    "be after To Date."
                )

            employee_doc.custom_current_responsibility = (
                responsibility
            )

            employee_doc.custom_responsibility_from = (
                effective_from
            )

            employee_doc.custom_responsibility_to = (
                effective_to or None
            )

            action_description = (
                "Responsibility changed from "
                + str(
                    old_responsibility
                    or "None"
                )
                + " to "
                + responsibility
            )

        elif operation == "clear_role":
            if not old_role:
                frappe.throw(
                    "Employee has no Additional Role "
                    "to clear."
                )

            employee_doc.custom_additional_role = (
                None
            )

            action_description = (
                "Additional Role cleared: "
                + old_role
            )

        elif operation == "clear_responsibility":
            if not old_responsibility:
                frappe.throw(
                    "Employee has no Responsibility "
                    "to clear."
                )

            employee_doc.custom_current_responsibility = (
                None
            )

            employee_doc.custom_responsibility_from = (
                None
            )

            employee_doc.custom_responsibility_to = (
                None
            )

            action_description = (
                "Responsibility cleared: "
                + old_responsibility
            )

        employee_doc.custom_responsibility_reason = (
            reason
        )

        employee_doc.custom_responsibility_assigned_by = (
            current_user
        )

        employee_doc.custom_responsibility_updated_on = (
            frappe.utils.now()
        )

        employee_doc.save()

        employee_doc.add_comment(
            "Comment",
            (
                "HRMS 360: "
                + action_description
                + ". Effective from: "
                + str(effective_from)
                + (
                    ". Effective to: "
                    + str(effective_to)
                    if effective_to
                    else ""
                )
                + ". Reason: "
                + reason
                + (
                    ". Remarks: "
                    + remarks
                    if remarks
                    else ""
                )
                + ". Updated by: "
                + current_user
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "manage_employee_assignment",
            "operation":
                operation,
            "employee":
                employee_doc.name,
            "additional_role":
                employee_doc.get(
                    "custom_additional_role"
                ),
            "responsibility":
                employee_doc.get(
                    "custom_current_responsibility"
                ),
            "effective_from":
                employee_doc.get(
                    "custom_responsibility_from"
                ),
            "effective_to":
                employee_doc.get(
                    "custom_responsibility_to"
                ),
            "message":
                "Employee assignment updated"
        }

    # HRMS_EMPLOYEE_ASSIGNMENT_API_END


    # HRMS_EMPLOYEE_DOCUMENT_API_START

    elif action == "manage_employee_document":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
            or "HR User" in roles
        )

        if not allowed:
            frappe.throw(
                "You do not have permission "
                "to manage Employee documents."
            )

        operation = (
            frappe.form_dict.get("operation")
            or "link"
        ).strip().lower()

        employee = (
            frappe.form_dict.get("employee")
            or ""
        ).strip()

        document_type = (
            frappe.form_dict.get(
                "document_type"
            )
            or ""
        ).strip().lower()

        file_url = (
            frappe.form_dict.get("file_url")
            or ""
        ).strip()

        remarks = (
            frappe.form_dict.get("remarks")
            or ""
        ).strip()

        if operation not in [
            "link",
            "remove"
        ]:
            frappe.throw(
                "Invalid Document operation: "
                + operation
            )

        if not employee:
            frappe.throw(
                "Employee is mandatory."
            )

        if not document_type:
            frappe.throw(
                "Document Type is mandatory."
            )

        if not frappe.db.exists(
            "Employee",
            employee
        ):
            frappe.throw(
                "Employee does not exist: "
                + employee
            )

        document_fields = {
            "photo": "image",
            "aadhaar":
                "custom_doc_aadhaar_file",
            "pan":
                "custom_doc_pan_file",
            "resume":
                "custom_doc_resume_file",
            "education":
                "custom_doc_education_file",
            "offer":
                "custom_doc_offer_letter_file",
            "appointment":
                "custom_doc_appointment_letter_file",
            "experience":
                "custom_doc_experience_letter_file",
            "relieving":
                "custom_doc_relieving_letter_file",
            "salaryslip":
                "custom_doc_salary_slips_file",
            "bank":
                "custom_doc_bank_cheque_file",
            "medical":
                "custom_doc_medical_fitness_file",
            "police":
                "custom_doc_police_verification_file",
            "ref":
                "custom_doc_reference_check_file"
        }

        document_labels = {
            "photo": "Profile Photo",
            "aadhaar": "Aadhaar Card",
            "pan": "PAN Card",
            "resume": "Resume / CV",
            "education":
                "Education Certificates",
            "offer": "Offer Letter",
            "appointment":
                "Appointment Letter",
            "experience":
                "Experience Letter",
            "relieving":
                "Relieving Letter",
            "salaryslip":
                "Last 3 Payslips",
            "bank":
                "Bank / Cancelled Cheque",
            "medical":
                "Medical Fitness",
            "police":
                "Police Verification",
            "ref":
                "Reference Check"
        }

        if document_type not in document_fields:
            frappe.throw(
                "Invalid Employee Document Type: "
                + document_type
            )

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        target_field = document_fields[
            document_type
        ]

        document_label = document_labels[
            document_type
        ]

        if not employee_doc.meta.has_field(
            target_field
        ):
            frappe.throw(
                "Employee document field is missing: "
                + target_field
            )

        old_file_url = (
            employee_doc.get(target_field)
            or ""
        )

        if operation == "link":
            if not file_url:
                frappe.throw(
                    "Uploaded File URL is mandatory."
                )

            file_name = frappe.db.get_value(
                "File",
                {
                    "file_url": file_url
                },
                "name"
            )

            if not file_name:
                frappe.throw(
                    "Uploaded File record was not found: "
                    + file_url
                )

            file_doc = frappe.get_doc(
                "File",
                file_name
            )

            file_doc.attached_to_doctype = (
                "Employee"
            )

            file_doc.attached_to_name = employee

            file_doc.attached_to_field = (
                target_field
            )

            file_doc.save(
                ignore_permissions=True
            )

            employee_doc.set(
                target_field,
                file_url
            )

            action_text = (
                document_label
                + " linked"
            )

        else:
            if not old_file_url:
                frappe.throw(
                    document_label
                    + " is already missing."
                )

            employee_doc.set(
                target_field,
                None
            )

            action_text = (
                document_label
                + " removed from Employee"
            )

        # Keep existing checklist fields synchronized
        if employee_doc.meta.has_field(
            "custom_doc_aadhaar"
        ):
            employee_doc.custom_doc_aadhaar = (
                1
                if employee_doc.get(
                    "custom_doc_aadhaar_file"
                )
                else 0
            )

        if employee_doc.meta.has_field(
            "custom_doc_pan"
        ):
            employee_doc.custom_doc_pan = (
                1
                if employee_doc.get(
                    "custom_doc_pan_file"
                )
                else 0
            )

        required_document_fields = [
            "image",
            "custom_doc_aadhaar_file",
            "custom_doc_pan_file",
            "custom_doc_resume_file",
            "custom_doc_education_file",
            "custom_doc_offer_letter_file",
            "custom_doc_appointment_letter_file",
            "custom_doc_experience_letter_file",
            "custom_doc_relieving_letter_file",
            "custom_doc_salary_slips_file",
            "custom_doc_bank_cheque_file",
            "custom_doc_medical_fitness_file",
            "custom_doc_police_verification_file",
            "custom_doc_reference_check_file"
        ]

        missing_documents = []

        for required_field in required_document_fields:
            if not employee_doc.get(
                required_field
            ):
                missing_documents.append(
                    required_field
                )

        documents_complete = (
            len(missing_documents) == 0
        )

        if employee_doc.meta.has_field(
            "custom_docs_complete"
        ):
            employee_doc.custom_docs_complete = (
                1 if documents_complete else 0
            )

        employee_doc.save()

        employee_doc.add_comment(
            "Comment",
            (
                "HRMS 360 Employee Document: "
                + action_text
                + ". Previous file: "
                + str(old_file_url or "None")
                + ". Current file: "
                + str(
                    employee_doc.get(
                        target_field
                    )
                    or "None"
                )
                + ". Remarks: "
                + str(remarks or "None")
                + ". Updated by: "
                + current_user
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "manage_employee_document",
            "operation":
                operation,
            "employee":
                employee_doc.name,
            "document_type":
                document_type,
            "document_label":
                document_label,
            "fieldname":
                target_field,
            "file_url":
                employee_doc.get(
                    target_field
                ),
            "documents_complete":
                documents_complete,
            "missing_count":
                len(missing_documents),
            "missing_fields":
                missing_documents,
            "message":
                action_text
        }

    # HRMS_EMPLOYEE_DOCUMENT_API_END


    # HRMS_EMPLOYEE_RECORD_API_START

    elif action == "manage_employee_hr_record":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can manage Employee HR Records."
            )

        operation = (
            frappe.form_dict.get("operation")
            or "create"
        ).strip().lower()

        if operation not in [
            "create",
            "update",
            "resolve",
            "close"
        ]:
            frappe.throw(
                "Invalid HR Record operation: "
                + operation
            )

        valid_record_types = [
            "Warning",
            "Disciplinary Action",
            "Achievement",
            "Appreciation",
            "Counselling",
            "Incident",
            "Confidential HR Note"
        ]

        valid_severities = [
            "Information",
            "Low",
            "Medium",
            "High",
            "Critical"
        ]

        valid_statuses = [
            "Open",
            "Under Review",
            "Resolved",
            "Closed"
        ]

        # ========================================================
        # CREATE EMPLOYEE HR RECORD
        # ========================================================

        if operation == "create":
            employee = (
                frappe.form_dict.get("employee")
                or ""
            ).strip()

            record_type = (
                frappe.form_dict.get(
                    "record_type"
                )
                or ""
            ).strip()

            record_date = (
                frappe.form_dict.get(
                    "record_date"
                )
                or today
            ).strip()

            severity = (
                frappe.form_dict.get("severity")
                or "Information"
            ).strip()

            subject = (
                frappe.form_dict.get("subject")
                or ""
            ).strip()

            details = (
                frappe.form_dict.get("details")
                or ""
            ).strip()

            action_taken = (
                frappe.form_dict.get(
                    "action_taken"
                )
                or ""
            ).strip()

            effective_from = (
                frappe.form_dict.get(
                    "effective_from"
                )
                or ""
            ).strip()

            effective_to = (
                frappe.form_dict.get(
                    "effective_to"
                )
                or ""
            ).strip()

            attachment = (
                frappe.form_dict.get(
                    "attachment"
                )
                or ""
            ).strip()

            confidential_text = (
                frappe.form_dict.get(
                    "confidential"
                )
                or "1"
            ).strip().lower()

            confidential = (
                confidential_text
                in ["1", "true", "yes"]
            )

            if not employee:
                frappe.throw(
                    "Employee is mandatory."
                )

            if not record_type:
                frappe.throw(
                    "Record Type is mandatory."
                )

            if record_type not in valid_record_types:
                frappe.throw(
                    "Invalid Record Type: "
                    + record_type
                )

            if severity not in valid_severities:
                frappe.throw(
                    "Invalid Severity: "
                    + severity
                )

            if not subject:
                frappe.throw(
                    "Subject is mandatory."
                )

            if not details:
                frappe.throw(
                    "Details are mandatory."
                )

            if not frappe.db.exists(
                "Employee",
                employee
            ):
                frappe.throw(
                    "Employee does not exist: "
                    + employee
                )

            if (
                effective_from
                and effective_to
                and effective_from > effective_to
            ):
                frappe.throw(
                    "Effective From cannot be "
                    "after Effective To."
                )

            employee_doc = frappe.get_doc(
                "Employee",
                employee
            )

            record_doc = frappe.get_doc({
                "doctype":
                    "Employee HR Record",
                "employee":
                    employee,
                "record_type":
                    record_type,
                "record_date":
                    record_date,
                "severity":
                    severity,
                "status":
                    "Open",
                "subject":
                    subject,
                "details":
                    details,
                "action_taken":
                    action_taken,
                "effective_from":
                    effective_from or None,
                "effective_to":
                    effective_to or None,
                "confidential":
                    1 if confidential else 0,
                "attachment":
                    attachment or None,
                "issued_by":
                    current_user,
                "issued_on":
                    frappe.utils.now(),
                "source":
                    "HRMS 360"
            })

            record_doc.insert()

            employee_doc.add_comment(
                "Comment",
                (
                    "HRMS 360 "
                    + record_type
                    + " created: "
                    + record_doc.name
                    + ". Subject: "
                    + subject
                    + ". Severity: "
                    + severity
                    + ". Created by: "
                    + current_user
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_employee_hr_record",
                "operation":
                    "create",
                "hr_record":
                    record_doc.name,
                "employee":
                    employee,
                "record_type":
                    record_type,
                "status":
                    record_doc.status,
                "message":
                    record_type + " created"
            }

        # ========================================================
        # UPDATE, RESOLVE OR CLOSE
        # ========================================================

        else:
            hr_record = (
                frappe.form_dict.get(
                    "hr_record"
                )
                or ""
            ).strip()

            remarks = (
                frappe.form_dict.get("remarks")
                or ""
            ).strip()

            if not hr_record:
                frappe.throw(
                    "Employee HR Record ID "
                    "is mandatory."
                )

            if not remarks:
                frappe.throw(
                    "Remarks are mandatory."
                )

            if not frappe.db.exists(
                "Employee HR Record",
                hr_record
            ):
                frappe.throw(
                    "Employee HR Record does not exist: "
                    + hr_record
                )

            record_doc = frappe.get_doc(
                "Employee HR Record",
                hr_record
            )

            previous_status = (
                record_doc.status or ""
            )

            if operation == "update":
                new_status = (
                    frappe.form_dict.get("status")
                    or ""
                ).strip()

                action_taken = (
                    frappe.form_dict.get(
                        "action_taken"
                    )
                    or ""
                ).strip()

                severity = (
                    frappe.form_dict.get(
                        "severity"
                    )
                    or ""
                ).strip()

                if new_status:
                    if new_status not in valid_statuses:
                        frappe.throw(
                            "Invalid HR Record Status: "
                            + new_status
                        )

                    record_doc.status = new_status

                if severity:
                    if severity not in valid_severities:
                        frappe.throw(
                            "Invalid Severity: "
                            + severity
                        )

                    record_doc.severity = severity

                if action_taken:
                    record_doc.action_taken = (
                        action_taken
                    )

            elif operation == "resolve":
                if record_doc.status == "Closed":
                    frappe.throw(
                        "Closed HR Record cannot "
                        "be resolved again."
                    )

                record_doc.status = "Resolved"
                record_doc.action_taken = remarks

            elif operation == "close":
                if record_doc.status == "Closed":
                    frappe.throw(
                        "HR Record is already closed."
                    )

                record_doc.status = "Closed"

                if record_doc.action_taken:
                    record_doc.action_taken = (
                        record_doc.action_taken
                        + "\n"
                        + remarks
                    )
                else:
                    record_doc.action_taken = remarks

            record_doc.save()

            record_doc.add_comment(
                "Comment",
                (
                    "HRMS 360 action: "
                    + operation.title()
                    + ". Previous status: "
                    + previous_status
                    + ". Current status: "
                    + str(record_doc.status)
                    + ". Remarks: "
                    + remarks
                    + ". Updated by: "
                    + current_user
                )
            )

            employee_doc = frappe.get_doc(
                "Employee",
                record_doc.employee
            )

            employee_doc.add_comment(
                "Comment",
                (
                    "HR Record "
                    + record_doc.name
                    + " updated. Type: "
                    + record_doc.record_type
                    + ". Status: "
                    + str(record_doc.status)
                    + ". Updated by: "
                    + current_user
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_employee_hr_record",
                "operation":
                    operation,
                "hr_record":
                    record_doc.name,
                "employee":
                    record_doc.employee,
                "record_type":
                    record_doc.record_type,
                "previous_status":
                    previous_status,
                "status":
                    record_doc.status,
                "message":
                    "Employee HR Record updated"
            }

    # HRMS_EMPLOYEE_RECORD_API_END


    # HRMS_ANNOUNCEMENT_API_START

    elif action == "manage_employee_announcement":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can manage announcements."
            )

        operation = (
            frappe.form_dict.get("operation")
            or "create"
        ).strip().lower()

        if operation not in [
            "create",
            "update",
            "deactivate"
        ]:
            frappe.throw(
                "Invalid Announcement operation: "
                + operation
            )

        if operation == "create":
            subject = (
                frappe.form_dict.get("subject")
                or ""
            ).strip()

            announcement_message = (
                frappe.form_dict.get(
                    "announcement_message"
                )
                or ""
            ).strip()

            audience = (
                frappe.form_dict.get("audience")
                or "All Employees"
            ).strip()

            branch = (
                frappe.form_dict.get("branch")
                or ""
            ).strip()

            department = (
                frappe.form_dict.get("department")
                or ""
            ).strip()

            priority = (
                frappe.form_dict.get("priority")
                or "Medium"
            ).strip()

            valid_from = (
                frappe.form_dict.get("valid_from")
                or today
            ).strip()

            valid_till = (
                frappe.form_dict.get("valid_till")
                or ""
            ).strip()

            attachment = (
                frappe.form_dict.get("attachment")
                or ""
            ).strip()

            if not subject:
                frappe.throw(
                    "Announcement Subject is mandatory."
                )

            if not announcement_message:
                frappe.throw(
                    "Announcement Message is mandatory."
                )

            if audience not in [
                "All Employees",
                "Branch",
                "Department"
            ]:
                frappe.throw(
                    "Invalid Announcement Audience."
                )

            if priority not in [
                "Low",
                "Medium",
                "High"
            ]:
                frappe.throw(
                    "Invalid Announcement Priority."
                )

            if audience == "Branch":
                if not branch:
                    frappe.throw(
                        "Branch is mandatory."
                    )

                if branch.lower() == "testing branch":
                    frappe.throw(
                        "Testing Branch is excluded."
                    )

                if not frappe.db.exists(
                    "Branch",
                    branch
                ):
                    frappe.throw(
                        "Branch does not exist: "
                        + branch
                    )

            if audience == "Department":
                if not department:
                    frappe.throw(
                        "Department is mandatory."
                    )

                if not frappe.db.exists(
                    "Department",
                    department
                ):
                    frappe.throw(
                        "Department does not exist: "
                        + department
                    )

            if (
                valid_till
                and valid_from > valid_till
            ):
                frappe.throw(
                    "Valid From cannot be after "
                    "Valid Till."
                )

            announcement_doc = frappe.get_doc({
                "doctype": "Employee Announcement",
                "message": announcement_message,
                "active": 1,
                "priority": priority,
                "valid_till": valid_till or None,
                "custom_subject": subject,
                "custom_audience": audience,
                "custom_branch": (
                    branch
                    if audience == "Branch"
                    else None
                ),
                "custom_department": (
                    department
                    if audience == "Department"
                    else None
                ),
                "custom_valid_from": valid_from,
                "custom_created_by": current_user,
                "custom_created_on":
                    frappe.utils.now(),
                "custom_attachment":
                    attachment or None
            })

            announcement_doc.insert()

            announcement_doc.add_comment(
                "Comment",
                (
                    "Created from HRMS 360 by "
                    + current_user
                    + ". Audience: "
                    + audience
                    + ". Priority: "
                    + priority
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_employee_announcement",
                "operation": "create",
                "announcement":
                    announcement_doc.name,
                "subject": subject,
                "audience": audience,
                "active":
                    announcement_doc.active,
                "message":
                    "Employee Announcement created"
            }

        else:
            announcement = (
                frappe.form_dict.get(
                    "announcement"
                )
                or ""
            ).strip()

            remarks = (
                frappe.form_dict.get("remarks")
                or ""
            ).strip()

            if not announcement:
                frappe.throw(
                    "Announcement ID is mandatory."
                )

            if not remarks:
                frappe.throw(
                    "Remarks are mandatory."
                )

            if not frappe.db.exists(
                "Employee Announcement",
                announcement
            ):
                frappe.throw(
                    "Announcement does not exist: "
                    + announcement
                )

            announcement_doc = frappe.get_doc(
                "Employee Announcement",
                announcement
            )

            if operation == "deactivate":
                announcement_doc.active = 0

            if operation == "update":
                subject = (
                    frappe.form_dict.get("subject")
                    or ""
                ).strip()

                announcement_message = (
                    frappe.form_dict.get(
                        "announcement_message"
                    )
                    or ""
                ).strip()

                priority = (
                    frappe.form_dict.get("priority")
                    or ""
                ).strip()

                valid_till = (
                    frappe.form_dict.get(
                        "valid_till"
                    )
                    or ""
                ).strip()

                active_value = (
                    frappe.form_dict.get("active")
                    or ""
                ).strip().lower()

                if subject:
                    announcement_doc.custom_subject = (
                        subject
                    )

                if announcement_message:
                    announcement_doc.message = (
                        announcement_message
                    )

                if priority:
                    if priority not in [
                        "Low",
                        "Medium",
                        "High"
                    ]:
                        frappe.throw(
                            "Invalid Announcement Priority."
                        )

                    announcement_doc.priority = priority

                if valid_till:
                    valid_from_value = (
                        announcement_doc.custom_valid_from
                        or today
                    )

                    if (
                        str(valid_from_value)
                        > valid_till
                    ):
                        frappe.throw(
                            "Valid Till cannot be before "
                            "Valid From."
                        )

                    announcement_doc.valid_till = (
                        valid_till
                    )

                if active_value:
                    if active_value in [
                        "1",
                        "true",
                        "yes"
                    ]:
                        announcement_doc.active = 1

                    elif active_value in [
                        "0",
                        "false",
                        "no"
                    ]:
                        announcement_doc.active = 0

                    else:
                        frappe.throw(
                            "Invalid Active value."
                        )

            announcement_doc.save()

            announcement_doc.add_comment(
                "Comment",
                (
                    "HRMS 360 Announcement action: "
                    + operation.title()
                    + ". Remarks: "
                    + remarks
                    + ". Updated by: "
                    + current_user
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_employee_announcement",
                "operation": operation,
                "announcement":
                    announcement_doc.name,
                "subject":
                    announcement_doc.custom_subject,
                "active":
                    announcement_doc.active,
                "priority":
                    announcement_doc.priority,
                "message":
                    "Employee Announcement updated"
            }

    # HRMS_ANNOUNCEMENT_API_END


    # HRMS_GRIEVANCE_API_START

    elif action == "manage_employee_grievance":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
            or "HR User" in roles
        )

        if not allowed:
            frappe.throw(
                "You do not have permission "
                "to manage Employee Grievances."
            )

        operation = (
            frappe.form_dict.get("operation")
            or "create"
        ).strip().lower()

        if operation not in [
            "create",
            "investigate",
            "resolve",
            "mark_invalid",
            "cancel"
        ]:
            frappe.throw(
                "Invalid Grievance operation: "
                + operation
            )

        if operation == "create":
            raised_by = (
                frappe.form_dict.get("raised_by")
                or ""
            ).strip()

            subject = (
                frappe.form_dict.get("subject")
                or ""
            ).strip()

            grievance_date = (
                frappe.form_dict.get(
                    "grievance_date"
                )
                or today
            ).strip()

            grievance_type = (
                frappe.form_dict.get(
                    "grievance_type"
                )
                or ""
            ).strip()

            against_party = (
                frappe.form_dict.get(
                    "against_party"
                )
                or "Employee"
            ).strip()

            against = (
                frappe.form_dict.get("against")
                or ""
            ).strip()

            description = (
                frappe.form_dict.get("description")
                or ""
            ).strip()

            cause = (
                frappe.form_dict.get("cause")
                or ""
            ).strip()

            submit_text = (
                frappe.form_dict.get("submit")
                or "1"
            ).strip().lower()

            submit_grievance = (
                submit_text
                in ["1", "true", "yes"]
            )

            if not raised_by:
                frappe.throw(
                    "Raised By Employee is mandatory."
                )

            if not subject:
                frappe.throw(
                    "Grievance Subject is mandatory."
                )

            if not grievance_type:
                frappe.throw(
                    "Grievance Type is mandatory."
                )

            if not against:
                frappe.throw(
                    "Grievance Against is mandatory."
                )

            if not description:
                frappe.throw(
                    "Grievance Description is mandatory."
                )

            if not frappe.db.exists(
                "Employee",
                raised_by
            ):
                frappe.throw(
                    "Raised By Employee does not exist: "
                    + raised_by
                )

            if not frappe.db.exists(
                "Grievance Type",
                grievance_type
            ):
                frappe.throw(
                    "Grievance Type does not exist: "
                    + grievance_type
                )

            if not frappe.db.exists(
                "DocType",
                against_party
            ):
                frappe.throw(
                    "Against Party DocType does not exist: "
                    + against_party
                )

            if not frappe.db.exists(
                against_party,
                against
            ):
                frappe.throw(
                    "Grievance Against record "
                    "does not exist: "
                    + against
                )

            if (
                against_party == "Employee"
                and raised_by == against
            ):
                frappe.throw(
                    "Employee cannot raise a grievance "
                    "against themselves."
                )

            grievance_doc = frappe.get_doc({
                "doctype": "Employee Grievance",
                "subject": subject,
                "raised_by": raised_by,
                "date": grievance_date,
                "status": "Open",
                "grievance_against_party":
                    against_party,
                "grievance_against":
                    against,
                "grievance_type":
                    grievance_type,
                "description":
                    description,
                "cause_of_grievance":
                    cause
            })

            grievance_doc.insert()

            if submit_grievance:
                grievance_doc.submit()

            grievance_doc.add_comment(
                "Comment",
                (
                    "Created through HRMS 360 by "
                    + current_user
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_employee_grievance",
                "operation":
                    "create",
                "grievance":
                    grievance_doc.name,
                "raised_by":
                    raised_by,
                "status":
                    grievance_doc.status,
                "docstatus":
                    grievance_doc.docstatus,
                "message":
                    "Employee Grievance created"
            }

        else:
            grievance = (
                frappe.form_dict.get("grievance")
                or ""
            ).strip()

            resolution_detail = (
                frappe.form_dict.get(
                    "resolution_detail"
                )
                or ""
            ).strip()

            employee_responsible = (
                frappe.form_dict.get(
                    "employee_responsible"
                )
                or ""
            ).strip()

            if not grievance:
                frappe.throw(
                    "Employee Grievance ID "
                    "is mandatory."
                )

            if operation != "cancel":
                if not resolution_detail:
                    frappe.throw(
                        "Action or Resolution details "
                        "are mandatory."
                    )

            if not frappe.db.exists(
                "Employee Grievance",
                grievance
            ):
                frappe.throw(
                    "Employee Grievance does not exist: "
                    + grievance
                )

            grievance_doc = frappe.get_doc(
                "Employee Grievance",
                grievance
            )

            if grievance_doc.docstatus == 2:
                frappe.throw(
                    "Employee Grievance is "
                    "already cancelled."
                )

            previous_status = (
                grievance_doc.status or ""
            )

            if employee_responsible:
                if not frappe.db.exists(
                    "Employee",
                    employee_responsible
                ):
                    frappe.throw(
                        "Responsible Employee "
                        "does not exist: "
                        + employee_responsible
                    )

                grievance_doc.employee_responsible = (
                    employee_responsible
                )

            if operation == "investigate":
                grievance_doc.status = (
                    "Investigated"
                )

                grievance_doc.resolution_detail = (
                    resolution_detail
                )

                grievance_doc.save()

            elif operation == "resolve":
                grievance_doc.status = "Resolved"
                grievance_doc.resolved_by = (
                    current_user
                )
                grievance_doc.resolution_date = (
                    today
                )
                grievance_doc.resolution_detail = (
                    resolution_detail
                )
                grievance_doc.save()

            elif operation == "mark_invalid":
                grievance_doc.status = "Invalid"
                grievance_doc.resolved_by = (
                    current_user
                )
                grievance_doc.resolution_date = (
                    today
                )
                grievance_doc.resolution_detail = (
                    resolution_detail
                )
                grievance_doc.save()

            elif operation == "cancel":
                if grievance_doc.docstatus != 1:
                    frappe.throw(
                        "Only a submitted Grievance "
                        "can be cancelled."
                    )

                grievance_doc.cancel()

            grievance_doc.reload()

            grievance_doc.add_comment(
                "Comment",
                (
                    "HRMS 360 Grievance action: "
                    + operation
                    + ". Previous status: "
                    + previous_status
                    + ". Current status: "
                    + str(grievance_doc.status)
                    + ". Details: "
                    + str(
                        resolution_detail
                        or "None"
                    )
                    + ". Updated by: "
                    + current_user
                )
            )

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action":
                    "manage_employee_grievance",
                "operation":
                    operation,
                "grievance":
                    grievance_doc.name,
                "previous_status":
                    previous_status,
                "status":
                    grievance_doc.status,
                "docstatus":
                    grievance_doc.docstatus,
                "message":
                    "Employee Grievance updated"
            }

    # HRMS_GRIEVANCE_API_END

    # HRMS_ACTION_API_END


    elif action == "employee_history":
        employee_name = (
            frappe.form_dict.get("employee") or ""
        ).strip()

        if not employee_name:
            frappe.throw("Employee ID is required")

        if not frappe.db.exists(
            "Employee",
            employee_name
        ):
            frappe.throw(
                "Employee not found: " + employee_name
            )

        employee_rows = safe_rows(
            "Employee",
            [
                "name",
                "employee_name",
                "status",
                "gender",
                "date_of_birth",
                "date_of_joining",
                "department",
                "designation",
                "branch",
                "company",
                "employment_type",
                "reports_to",
                "user_id",
                "company_email",
                "personal_email",
                "cell_number",
                "personal_mobile_no",
                "image",
                "blood_group",
                "marital_status",
                "grade",
                "holiday_list",
                "default_shift",
                "relieving_date",
                "scheduled_confirmation_date",
                "final_confirmation_date",
                "contract_end_date",
                "notice_number_of_days",
                "date_of_retirement",
                "ctc",
                "salary_currency",
                "salary_mode",
                "bank_name",
                "bank_ac_no",
                "iban",
                "current_address",
                "permanent_address",
                "person_to_be_contacted",
                "emergency_phone_number",
                "relation",
                "bio",
                "custom_employment_status",
                "custom_additional_role",
                "custom_current_responsibility",
                "custom_responsibility_from",
                "custom_responsibility_to",
                "custom_responsibility_reason",
                "custom_responsibility_assigned_by",
                "custom_responsibility_updated_on",
                "custom_doc_aadhaar",
                "custom_doc_pan",
                "custom_docs_complete",
                "custom_doc_aadhaar_file",
                "custom_doc_pan_file",
                "custom_doc_resume_file",
                "custom_doc_education_file",
                "custom_doc_offer_letter_file",
                "custom_doc_appointment_letter_file",
                "custom_doc_experience_letter_file",
                "custom_doc_relieving_letter_file",
                "custom_doc_salary_slips_file",
                "custom_doc_bank_cheque_file",
                "custom_doc_medical_fitness_file",
                "custom_doc_police_verification_file",
                "custom_doc_reference_check_file",
                "creation",
                "modified",
                "modified_by",
                "owner"
            ],
            {
                "name": employee_name
            },
            1
        )

        employee = None

        if employee_rows:
            employee = employee_rows[0]

        if employee and not salary_allowed:
            employee["ctc"] = None
            employee["bank_name"] = None
            employee["bank_ac_no"] = None
            employee["iban"] = None
            employee["salary_mode"] = None

        attendance = safe_rows(
            "Attendance",
            [
                "name",
                "attendance_date",
                "status",
                "working_hours",
                "in_time",
                "out_time",
                "leave_type",
                "late_entry",
                "early_exit",
                "shift",
                "docstatus"
            ],
            {
                "employee": employee_name,
                "docstatus": ["!=", 2]
            },
            1000,
            "attendance_date desc"
        )

        checkins = safe_rows(
            "Employee Checkin",
            [
                "name",
                "time",
                "log_type",
                "device_id",
                "shift",
                "skip_auto_attendance",
                "creation",
                "modified"
            ],
            {
                "employee": employee_name
            },
            2000,
            "time desc"
        )

        leave_applications = safe_rows(
            "Leave Application",
            [
                "name",
                "leave_type",
                "from_date",
                "to_date",
                "total_leave_days",
                "half_day",
                "half_day_date",
                "status",
                "description",
                "posting_date",
                "leave_approver",
                "docstatus",
                "creation",
                "modified",
                "modified_by"
            ],
            {
                "employee": employee_name,
                "docstatus": ["!=", 2]
            },
            1000,
            "from_date desc"
        )

        leave_allocations = safe_rows(
            "Leave Allocation",
            [
                "name",
                "leave_type",
                "from_date",
                "to_date",
                "new_leaves_allocated",
                "total_leaves_allocated",
                "unused_leaves",
                "carry_forward",
                "docstatus",
                "creation",
                "modified"
            ],
            {
                "employee": employee_name,
                "docstatus": ["!=", 2]
            },
            1000,
            "to_date desc"
        )

        salary_slips = []

        if salary_allowed:
            salary_slips = safe_rows(
                "Salary Slip",
                [
                    "name",
                    "start_date",
                    "end_date",
                    "posting_date",
                    "gross_pay",
                    "total_deduction",
                    "net_pay",
                    "rounded_total",
                    "status",
                    "docstatus",
                    "creation",
                    "modified"
                ],
                {
                    "employee": employee_name,
                    "docstatus": ["!=", 2]
                },
                1000,
                "end_date desc"
            )

        transfers = safe_rows(
            "Employee Transfer",
            [
                "name",
                "transfer_date",
                "new_company",
                "docstatus",
                "creation",
                "modified",
                "modified_by",
                "owner"
            ],
            {
                "employee": employee_name,
                "docstatus": ["!=", 2]
            },
            500,
            "transfer_date desc"
        )

        promotions = safe_rows(
            "Employee Promotion",
            [
                "name",
                "promotion_date",
                "revised_ctc",
                "docstatus",
                "creation",
                "modified",
                "modified_by",
                "owner"
            ],
            {
                "employee": employee_name,
                "docstatus": ["!=", 2]
            },
            500,
            "promotion_date desc"
        )

        shifts = safe_rows(
            "Shift Assignment",
            [
                "name",
                "shift_type",
                "start_date",
                "end_date",
                "status",
                "docstatus",
                "creation",
                "modified"
            ],
            {
                "employee": employee_name,
                "docstatus": ["!=", 2]
            },
            1000,
            "start_date desc"
        )

        assets = safe_rows(
            "Asset",
            [
                "name",
                "asset_name",
                "item_code",
                "location",
                "status",
                "purchase_date",
                "available_for_use",
                "creation",
                "modified"
            ],
            {
                "custodian": employee_name
            },
            1000
        )

        appraisals = safe_rows(
            "Appraisal",
            [
                "name",
                "start_date",
                "end_date",
                "status",
                "total_score",
                "final_score",
                "department",
                "designation",
                "docstatus",
                "creation",
                "modified",
                "modified_by"
            ],
            {
                "employee": employee_name,
                "docstatus": ["!=", 2]
            },
            1000
        )

        onboarding = safe_rows(
            "Employee Onboarding",
            [
                "name",
                "job_applicant",
                "date_of_joining",
                "department",
                "designation",
                "status",
                "boarding_status",
                "project",
                "docstatus",
                "creation",
                "modified"
            ],
            {
                "employee": employee_name,
                "docstatus": ["!=", 2]
            },
            500
        )

        separations = safe_rows(
            "Employee Separation",
            [
                "name",
                "department",
                "designation",
                "status",
                "boarding_status",
                "project",
                "docstatus",
                "creation",
                "modified",
                "modified_by"
            ],
            {
                "employee": employee_name,
                "docstatus": ["!=", 2]
            },
            500
        )

        files = safe_rows(
            "File",
            [
                "name",
                "file_name",
                "file_url",
                "is_private",
                "file_size",
                "folder",
                "creation",
                "modified",
                "owner"
            ],
            {
                "attached_to_doctype": "Employee",
                "attached_to_name": employee_name,
                "is_folder": 0
            },
            1000,
            "creation desc"
        )

        comments = safe_rows(
            "Comment",
            [
                "name",
                "comment_type",
                "content",
                "comment_email",
                "comment_by",
                "creation",
                "modified",
                "owner"
            ],
            {
                "reference_doctype": "Employee",
                "reference_name": employee_name
            },
            1000,
            "creation desc"
        )

        versions = safe_rows(
            "Version",
            [
                "name",
                "data",
                "creation",
                "modified",
                "owner"
            ],
            {
                "ref_doctype": "Employee",
                "docname": employee_name
            },
            1000,
            "creation desc"
        )

        timeline = []

        if employee:
            timeline.append({
                "date": employee.get("date_of_joining")
                    or employee.get("creation"),
                "type": "Joining",
                "title": "Employee joined",
                "detail": (
                    employee.get("designation", "")
                    + " · "
                    + employee.get("branch", "")
                ),
                "reference": employee_name,
                "by": employee.get("owner")
            })

            if employee.get("modified"):
                timeline.append({
                    "date": employee.get("modified"),
                    "type": "Employee",
                    "title": "Employee record updated",
                    "detail": employee.get("status", ""),
                    "reference": employee_name,
                    "by": employee.get("modified_by")
                })

        for row in transfers:
            timeline.append({
                "date": row.get("transfer_date")
                    or row.get("creation"),
                "type": "Transfer",
                "title": "Employee transfer",
                "detail": row.get("new_company", ""),
                "reference": row.get("name"),
                "by": row.get("modified_by")
                    or row.get("owner")
            })

        for row in promotions:
            detail = "Promotion recorded"

            if salary_allowed and row.get("revised_ctc"):
                detail = (
                    "Revised CTC: "
                    + str(row.get("revised_ctc"))
                )

            timeline.append({
                "date": row.get("promotion_date")
                    or row.get("creation"),
                "type": "Promotion",
                "title": "Employee promotion",
                "detail": detail,
                "reference": row.get("name"),
                "by": row.get("modified_by")
                    or row.get("owner")
            })

        for row in leave_applications:
            timeline.append({
                "date": row.get("from_date")
                    or row.get("creation"),
                "type": "Leave",
                "title": row.get("leave_type")
                    or "Leave application",
                "detail": (
                    str(row.get("total_leave_days") or 0)
                    + " day(s) · "
                    + str(row.get("status") or "")
                ),
                "reference": row.get("name"),
                "by": row.get("modified_by")
            })

        for row in appraisals:
            timeline.append({
                "date": row.get("end_date")
                    or row.get("modified"),
                "type": "Appraisal",
                "title": "Employee appraisal",
                "detail": (
                    "Score: "
                    + str(
                        row.get("final_score")
                        or row.get("total_score")
                        or 0
                    )
                ),
                "reference": row.get("name"),
                "by": row.get("modified_by")
            })

        for row in shifts:
            timeline.append({
                "date": row.get("start_date")
                    or row.get("creation"),
                "type": "Shift",
                "title": "Shift assigned",
                "detail": row.get("shift_type") or "",
                "reference": row.get("name"),
                "by": None
            })

        for row in assets:
            timeline.append({
                "date": row.get("purchase_date")
                    or row.get("creation"),
                "type": "Asset",
                "title": "Asset assigned",
                "detail": (
                    row.get("asset_name")
                    or row.get("item_code")
                    or row.get("name")
                ),
                "reference": row.get("name"),
                "by": None
            })

        for row in files:
            timeline.append({
                "date": row.get("creation"),
                "type": "Document",
                "title": "Document attached",
                "detail": row.get("file_name") or "",
                "reference": row.get("name"),
                "by": row.get("owner")
            })

        for row in comments:
            timeline.append({
                "date": row.get("creation"),
                "type": row.get("comment_type")
                    or "Comment",
                "title": "Employee comment",
                "detail": row.get("content") or "",
                "reference": row.get("name"),
                "by": (
                    row.get("comment_by")
                    or row.get("comment_email")
                    or row.get("owner")
                )
            })

        for row in versions:
            timeline.append({
                "date": row.get("creation"),
                "type": "Version",
                "title": "Employee record changed",
                "detail": row.get("data") or "",
                "reference": row.get("name"),
                "by": row.get("owner")
            })

        for row in onboarding:
            timeline.append({
                "date": row.get("date_of_joining")
                    or row.get("creation"),
                "type": "Onboarding",
                "title": "Employee onboarding",
                "detail": (
                    row.get("boarding_status")
                    or row.get("status")
                    or ""
                ),
                "reference": row.get("name"),
                "by": None
            })

        for row in separations:
            timeline.append({
                "date": row.get("creation"),
                "type": "Separation",
                "title": "Employee separation",
                "detail": (
                    row.get("boarding_status")
                    or row.get("status")
                    or ""
                ),
                "reference": row.get("name"),
                "by": row.get("modified_by")
            })

        frappe.response["message"] = {
            "ok": True,
            "action": "employee_history",
            "today": today,
            "user": current_user,
            "roles": roles,
            "salary_allowed": salary_allowed,
            "employee": employee,
            "attendance": attendance,
            "checkins": checkins,
            "leave_applications": leave_applications,
            "leave_allocations": leave_allocations,
            "salary_slips": salary_slips,
            "transfers": transfers,
            "promotions": promotions,
            "shifts": shifts,
            "assets": assets,
            "appraisals": appraisals,
            "onboarding": onboarding,
            "separations": separations,
            "files": files,
            "comments": comments,
            "versions": versions,
            "timeline": timeline
        }



    # HRMS_STEP_27D_A_START

    elif action == "create_appraisal_cycle":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can create Appraisal Cycles."
            )

        cycle_name = (
            frappe.form_dict.get("cycle_name")
            or ""
        ).strip()

        company = (
            frappe.form_dict.get("company")
            or ""
        ).strip()

        start_date = (
            frappe.form_dict.get("start_date")
            or ""
        ).strip()

        end_date = (
            frappe.form_dict.get("end_date")
            or ""
        ).strip()

        branch = (
            frappe.form_dict.get("branch")
            or ""
        ).strip()

        department = (
            frappe.form_dict.get("department")
            or ""
        ).strip()

        designation = (
            frappe.form_dict.get("designation")
            or ""
        ).strip()

        evaluation_method = (
            frappe.form_dict.get(
                "kra_evaluation_method"
            )
            or "Manual Rating"
        ).strip()

        if not cycle_name:
            frappe.throw(
                "Cycle Name is mandatory."
            )

        if not company:
            frappe.throw(
                "Company is mandatory."
            )

        if not start_date:
            frappe.throw(
                "Start Date is mandatory."
            )

        if not end_date:
            frappe.throw(
                "End Date is mandatory."
            )

        if end_date < start_date:
            frappe.throw(
                "Appraisal Cycle End Date cannot "
                "be before Start Date."
            )

        if branch == "Testing Branch":
            frappe.throw(
                "Testing Branch is not allowed."
            )

        if not frappe.db.exists(
            "Company",
            company
        ):
            frappe.throw(
                "Company does not exist: "
                + company
            )

        existing_cycle = frappe.get_all(
            "Appraisal Cycle",
            filters={
                "cycle_name": cycle_name
            },
            fields=["name"],
            limit_page_length=1
        )

        if existing_cycle:
            frappe.throw(
                "Appraisal Cycle already exists: "
                + existing_cycle[0].name
            )

        valid_evaluation_methods = [
            "Automated Based on Goal Progress",
            "Manual Rating"
        ]

        if (
            evaluation_method
            not in valid_evaluation_methods
        ):
            frappe.throw(
                "Invalid KRA Evaluation Method."
            )

        cycle_data = {
            "doctype": "Appraisal Cycle",
            "cycle_name": cycle_name,
            "company": company,
            "start_date": start_date,
            "end_date": end_date,
            "kra_evaluation_method":
                evaluation_method
        }

        if branch:
            if not frappe.db.exists(
                "Branch",
                branch
            ):
                frappe.throw(
                    "Branch does not exist: "
                    + branch
                )

            cycle_data["branch"] = branch

        if department:
            if not frappe.db.exists(
                "Department",
                department
            ):
                frappe.throw(
                    "Department does not exist: "
                    + department
                )

            cycle_data["department"] = department

        if designation:
            if not frappe.db.exists(
                "Designation",
                designation
            ):
                frappe.throw(
                    "Designation does not exist: "
                    + designation
                )

            cycle_data["designation"] = designation

        cycle_doc = frappe.get_doc(
            cycle_data
        )

        cycle_doc.insert()

        cycle_doc.add_comment(
            "Comment",
            (
                "Appraisal Cycle created from "
                "LIFE HRMS 360."
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "create_appraisal_cycle",
            "appraisal_cycle":
                cycle_doc.name,
            "cycle_name":
                cycle_doc.cycle_name,
            "message":
                "Appraisal Cycle created"
        }


    elif action == "create_employee_appraisal":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR Manager or System Manager "
                "can create Appraisals."
            )

        employee = (
            frappe.form_dict.get("employee")
            or ""
        ).strip()

        appraisal_cycle = (
            frappe.form_dict.get(
                "appraisal_cycle"
            )
            or ""
        ).strip()

        appraisal_template = (
            frappe.form_dict.get(
                "appraisal_template"
            )
            or ""
        ).strip()

        remarks = (
            frappe.form_dict.get("remarks")
            or ""
        ).strip()

        reflections = (
            frappe.form_dict.get("reflections")
            or ""
        ).strip()

        if not employee:
            frappe.throw(
                "Employee is mandatory."
            )

        if not appraisal_cycle:
            frappe.throw(
                "Appraisal Cycle is mandatory."
            )

        if not frappe.db.exists(
            "Employee",
            employee
        ):
            frappe.throw(
                "Employee does not exist: "
                + employee
            )

        if not frappe.db.exists(
            "Appraisal Cycle",
            appraisal_cycle
        ):
            frappe.throw(
                "Appraisal Cycle does not exist: "
                + appraisal_cycle
            )

        if (
            appraisal_template
            and not frappe.db.exists(
                "Appraisal Template",
                appraisal_template
            )
        ):
            frappe.throw(
                "Appraisal Template does not exist: "
                + appraisal_template
            )

        existing_appraisal = frappe.get_all(
            "Appraisal",
            filters={
                "employee": employee,
                "appraisal_cycle":
                    appraisal_cycle,
                "docstatus": ["!=", 2]
            },
            fields=["name"],
            order_by="creation desc",
            limit_page_length=1
        )

        if existing_appraisal:
            frappe.throw(
                "An Appraisal already exists for "
                + employee
                + " in this cycle: "
                + existing_appraisal[0].name
            )

        employee_doc = frappe.get_doc(
            "Employee",
            employee
        )

        cycle_doc = frappe.get_doc(
            "Appraisal Cycle",
            appraisal_cycle
        )

        if (
            cycle_doc.company
            and employee_doc.company
            and cycle_doc.company
            != employee_doc.company
        ):
            frappe.throw(
                "Employee Company does not match "
                "the Appraisal Cycle Company."
            )

        appraisal_data = {
            "doctype": "Appraisal",
            "employee": employee,
            "company": employee_doc.company,
            "appraisal_cycle":
                appraisal_cycle
        }

        if appraisal_template:
            appraisal_data[
                "appraisal_template"
            ] = appraisal_template

        if remarks:
            appraisal_data["remarks"] = remarks

        if reflections:
            appraisal_data[
                "reflections"
            ] = reflections

        appraisal_doc = frappe.get_doc(
            appraisal_data
        )

        appraisal_doc.insert()

        appraisal_doc.add_comment(
            "Comment",
            (
                "Draft Appraisal created from "
                "LIFE HRMS 360 for cycle "
                + appraisal_cycle
                + "."
            )
        )

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action":
                "create_employee_appraisal",
            "employee":
                employee,
            "appraisal":
                appraisal_doc.name,
            "appraisal_cycle":
                appraisal_cycle,
            "docstatus":
                appraisal_doc.docstatus,
            "message":
                "Draft Appraisal created"
        }

    # HRMS_STEP_27E_A_START

    elif action == "submit_employee_appraisal":
        allowed = (
            "System Manager" in roles
            or "HR Manager" in roles
            or "HR User" in roles
        )

        if not allowed:
            frappe.throw(
                "Only HR User, HR Manager or System Manager "
                "can submit Appraisals."
            )

        appraisal_name = (
            frappe.form_dict.get("appraisal")
            or ""
        ).strip()

        if not appraisal_name:
            frappe.throw(
                "Appraisal ID is mandatory."
            )

        if not frappe.db.exists(
            "Appraisal",
            appraisal_name
        ):
            frappe.throw(
                "Appraisal does not exist: "
                + appraisal_name
            )

        appraisal_doc = frappe.get_doc(
            "Appraisal",
            appraisal_name
        )

        if appraisal_doc.docstatus == 1:
            frappe.throw(
                "Appraisal is already submitted: "
                + appraisal_name
            )

        if appraisal_doc.docstatus == 2:
            frappe.throw(
                "Cancelled Appraisal cannot be submitted: "
                + appraisal_name
            )

        if appraisal_doc.docstatus != 0:
            frappe.throw(
                "Only a Draft Appraisal can be submitted."
            )

        if not appraisal_doc.employee:
            frappe.throw(
                "Employee is MISSING in this Appraisal."
            )

        if not appraisal_doc.appraisal_cycle:
            frappe.throw(
                "Appraisal Cycle is MISSING in this Appraisal."
            )

        if not appraisal_doc.company:
            frappe.throw(
                "Company is MISSING in this Appraisal."
            )

        if not frappe.db.exists(
            "Employee",
            appraisal_doc.employee
        ):
            frappe.throw(
                "Linked Employee does not exist: "
                + appraisal_doc.employee
            )

        employee_branch = frappe.db.get_value(
            "Employee",
            appraisal_doc.employee,
            "branch"
        ) or ""

        if employee_branch == "Testing Branch":
            frappe.throw(
                "Testing Branch Appraisals are not allowed."
            )

        if not frappe.db.exists(
            "Appraisal Cycle",
            appraisal_doc.appraisal_cycle
        ):
            frappe.throw(
                "Linked Appraisal Cycle does not exist: "
                + appraisal_doc.appraisal_cycle
            )

        cycle_company = frappe.db.get_value(
            "Appraisal Cycle",
            appraisal_doc.appraisal_cycle,
            "company"
        ) or ""

        if (
            cycle_company
            and appraisal_doc.company
            and cycle_company != appraisal_doc.company
        ):
            frappe.throw(
                "Appraisal Company does not match the "
                "Appraisal Cycle Company."
            )

        score_fields = [
            "goal_score_percentage",
            "total_score",
            "avg_feedback_score",
            "self_score",
            "final_score"
        ]

        positive_score_found = False

        for score_field in score_fields:
            score_value = appraisal_doc.get(
                score_field
            )

            if (
                score_value is not None
                and score_value != ""
                and float(score_value) > 0
            ):
                positive_score_found = True

        if not positive_score_found:
            frappe.throw(
                "Appraisal scores are MISSING. Enter and calculate "
                "the applicable Goal, Feedback or Self Appraisal "
                "scores before submission."
            )

        appraisal_doc.add_comment(
            "Comment",
            (
                "Appraisal submission initiated from "
                "LIFE HRMS 360."
            )
        )

        appraisal_doc.submit()

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "action": "submit_employee_appraisal",
            "appraisal": appraisal_doc.name,
            "employee": appraisal_doc.employee,
            "appraisal_cycle":
                appraisal_doc.appraisal_cycle,
            "docstatus": appraisal_doc.docstatus,
            "goal_score": appraisal_doc.get(
                "goal_score_percentage"
            ),
            "feedback_score": appraisal_doc.get(
                "avg_feedback_score"
            ),
            "self_score": appraisal_doc.get(
                "self_score"
            ),
            "final_score": appraisal_doc.get(
                "final_score"
            ),
            "message": "Appraisal submitted"
        }

    # HRMS_STEP_27E_A_END

    # HRMS_STEP_27D_A_END

    # HRMS_RECRUITMENT_WORKFLOW_ACTION_START

    elif action == "manage_recruitment_workflow":
        recruitment_roles = [
            "System Manager",
            "HR Manager",
            "HR User"
        ]

        recruitment_allowed = False

        for role_name in recruitment_roles:
            if role_name in roles:
                recruitment_allowed = True

        if not recruitment_allowed:
            frappe.throw(
                "You do not have permission to "
                "manage Recruitment records."
            )

        operation = (
            frappe.form_dict.get("operation")
            or ""
        ).strip()

        if operation == "create_job_applicant":
            applicant_name = (
                frappe.form_dict.get(
                    "applicant_name"
                )
                or ""
            ).strip()

            email_id = (
                frappe.form_dict.get(
                    "email_id"
                )
                or ""
            ).strip().lower()

            phone_number = (
                frappe.form_dict.get(
                    "phone_number"
                )
                or ""
            ).strip()

            job_opening = (
                frappe.form_dict.get(
                    "job_opening"
                )
                or ""
            ).strip()

            source = (
                frappe.form_dict.get("source")
                or ""
            ).strip()

            source_name = (
                frappe.form_dict.get(
                    "source_name"
                )
                or ""
            ).strip()

            if not applicant_name:
                frappe.throw(
                    "Applicant Name is mandatory."
                )

            if not email_id:
                frappe.throw(
                    "Email Address is mandatory."
                )

            if not phone_number:
                frappe.throw(
                    "Phone Number is mandatory."
                )

            if (
                not phone_number.isdigit()
                or len(phone_number) != 10
            ):
                frappe.throw(
                    "Phone Number must contain "
                    "exactly 10 digits."
                )

            if frappe.db.exists(
                "Job Applicant",
                email_id
            ):
                frappe.throw(
                    "Job Applicant already exists: "
                    + email_id
                )

            designation = ""

            if job_opening:
                if not frappe.db.exists(
                    "Job Opening",
                    job_opening
                ):
                    frappe.throw(
                        "Job Opening does not exist: "
                        + job_opening
                    )

                opening_status = (
                    frappe.db.get_value(
                        "Job Opening",
                        job_opening,
                        "status"
                    )
                    or ""
                )

                if opening_status != "Open":
                    frappe.throw(
                        "Job Opening is not Open: "
                        + job_opening
                    )

                designation = (
                    frappe.db.get_value(
                        "Job Opening",
                        job_opening,
                        "designation"
                    )
                    or ""
                )

            applicant_data = {
                "doctype": "Job Applicant",
                "applicant_name": applicant_name,
                "email_id": email_id,
                "phone_number": phone_number,
                "status": "Open"
            }

            if job_opening:
                applicant_data["job_title"] = (
                    job_opening
                )

            if designation:
                applicant_data["designation"] = (
                    designation
                )

            if (
                source
                and frappe.db.exists(
                    "Job Applicant Source",
                    source
                )
            ):
                applicant_data["source"] = source

            if (
                source_name
                and frappe.db.exists(
                    "Employee",
                    source_name
                )
            ):
                applicant_data["source_name"] = (
                    source_name
                )

            applicant_doc = frappe.get_doc(
                applicant_data
            )

            applicant_doc.insert()

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "operation":
                    "create_job_applicant",
                "job_applicant":
                    applicant_doc.name,
                "applicant_name":
                    applicant_doc.applicant_name,
                "job_opening":
                    applicant_doc.job_title,
                "designation":
                    applicant_doc.designation,
                "status":
                    applicant_doc.status,
                "message":
                    "Job Applicant saved in ERPNext"
            }

        elif operation == "schedule_interview":
            job_applicant = (
                frappe.form_dict.get(
                    "job_applicant"
                )
                or ""
            ).strip()

            interview_round = (
                frappe.form_dict.get(
                    "interview_round"
                )
                or ""
            ).strip()

            scheduled_on = (
                frappe.form_dict.get(
                    "scheduled_on"
                )
                or ""
            ).strip()

            from_time = (
                frappe.form_dict.get(
                    "from_time"
                )
                or ""
            ).strip()

            to_time = (
                frappe.form_dict.get(
                    "to_time"
                )
                or ""
            ).strip()

            if not job_applicant:
                frappe.throw(
                    "Job Applicant is mandatory."
                )

            if not interview_round:
                frappe.throw(
                    "Interview Round is mandatory."
                )

            if not scheduled_on:
                frappe.throw(
                    "Scheduled On is mandatory."
                )

            if not from_time:
                frappe.throw(
                    "From Time is mandatory."
                )

            if not to_time:
                frappe.throw(
                    "To Time is mandatory."
                )

            if not frappe.db.exists(
                "Job Applicant",
                job_applicant
            ):
                frappe.throw(
                    "Job Applicant does not exist: "
                    + job_applicant
                )

            if not frappe.db.exists(
                "Interview Round",
                interview_round
            ):
                frappe.throw(
                    "Interview Round does not exist: "
                    + interview_round
                )

            if scheduled_on < today:
                frappe.throw(
                    "Interview date cannot be "
                    "in the past."
                )

            if to_time <= from_time:
                frappe.throw(
                    "Interview To Time must be "
                    "after From Time."
                )

            applicant = frappe.get_doc(
                "Job Applicant",
                job_applicant
            )

            round_designation = (
                frappe.db.get_value(
                    "Interview Round",
                    interview_round,
                    "designation"
                )
                or ""
            )

            if (
                round_designation
                and applicant.designation
                and round_designation
                    != applicant.designation
            ):
                frappe.throw(
                    "Interview Round belongs to "
                    + round_designation
                    + ", but the applicant "
                    "designation is "
                    + applicant.designation
                    + "."
                )

            duplicate_interview = (
                frappe.db.exists(
                    "Interview",
                    {
                        "job_applicant":
                            job_applicant,
                        "interview_round":
                            interview_round,
                        "scheduled_on":
                            scheduled_on,
                        "docstatus":
                            ["!=", 2]
                    }
                )
            )

            if duplicate_interview:
                frappe.throw(
                    "An Interview already exists: "
                    + duplicate_interview
                )

            interview_data = {
                "doctype": "Interview",
                "interview_round":
                    interview_round,
                "job_applicant":
                    job_applicant,
                "status": "Pending",
                "scheduled_on":
                    scheduled_on,
                "from_time": from_time,
                "to_time": to_time
            }

            if applicant.job_title:
                interview_data[
                    "job_opening"
                ] = applicant.job_title

            if applicant.designation:
                interview_data[
                    "designation"
                ] = applicant.designation

            interview_doc = frappe.get_doc(
                interview_data
            )

            interview_doc.insert()

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "operation":
                    "schedule_interview",
                "interview":
                    interview_doc.name,
                "job_applicant":
                    interview_doc.job_applicant,
                "interview_round":
                    interview_doc.interview_round,
                "scheduled_on":
                    interview_doc.scheduled_on,
                "from_time":
                    interview_doc.from_time,
                "to_time":
                    interview_doc.to_time,
                "status":
                    interview_doc.status,
                "message":
                    "Interview saved in ERPNext"
            }

        elif operation == "create_job_offer":
            job_applicant = (
                frappe.form_dict.get(
                    "job_applicant"
                )
                or ""
            ).strip()

            offer_date = (
                frappe.form_dict.get(
                    "offer_date"
                )
                or today
            ).strip()

            company = (
                frappe.form_dict.get("company")
                or ""
            ).strip()

            if not job_applicant:
                frappe.throw(
                    "Job Applicant is mandatory."
                )

            if not company:
                frappe.throw(
                    "Company is mandatory."
                )

            if not frappe.db.exists(
                "Job Applicant",
                job_applicant
            ):
                frappe.throw(
                    "Job Applicant does not exist: "
                    + job_applicant
                )

            if not frappe.db.exists(
                "Company",
                company
            ):
                frappe.throw(
                    "Company does not exist: "
                    + company
                )

            applicant = frappe.get_doc(
                "Job Applicant",
                job_applicant
            )

            if not applicant.applicant_name:
                frappe.throw(
                    "Applicant Name is MISSING."
                )

            if not applicant.designation:
                frappe.throw(
                    "Applicant Designation is MISSING."
                )

            if not frappe.db.exists(
                "Designation",
                applicant.designation
            ):
                frappe.throw(
                    "Applicant Designation does not "
                    "exist: "
                    + applicant.designation
                )

            existing_offer = frappe.db.exists(
                "Job Offer",
                {
                    "job_applicant":
                        job_applicant,
                    "docstatus":
                        ["!=", 2]
                }
            )

            if existing_offer:
                frappe.throw(
                    "Job Offer already exists: "
                    + existing_offer
                )

            offer_doc = frappe.get_doc({
                "doctype": "Job Offer",
                "job_applicant":
                    job_applicant,
                "applicant_name":
                    applicant.applicant_name,
                "status":
                    "Awaiting Response",
                "offer_date":
                    offer_date,
                "designation":
                    applicant.designation,
                "company":
                    company
            })

            offer_doc.insert()

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "operation":
                    "create_job_offer",
                "job_offer":
                    offer_doc.name,
                "job_applicant":
                    offer_doc.job_applicant,
                "applicant_name":
                    offer_doc.applicant_name,
                "designation":
                    offer_doc.designation,
                "company":
                    offer_doc.company,
                "status":
                    offer_doc.status,
                "docstatus":
                    offer_doc.docstatus,
                "message":
                    "Draft Job Offer saved in ERPNext"
            }

        elif operation == "create_interview_feedback":
            frappe.throw(
                "MISSING: Interview Feedback creation "
                "requires the live Skill Assessment "
                "child-field schema. Feedback records "
                "are available read-only until that "
                "schema is configured."
            )

        else:
            frappe.throw(
                "Unsupported Recruitment operation: "
                + operation
            )

    # HRMS_RECRUITMENT_WORKFLOW_ACTION_END

    # HRMS_COMMUNICATION_TASK_ACTION_START

    elif action == "manage_hr_task":
        task_roles = [
            "System Manager",
            "HR Manager",
            "HR User"
        ]

        task_manager = False

        for role_name in task_roles:
            if role_name in roles:
                task_manager = True

        operation = (
            frappe.form_dict.get("operation")
            or ""
        ).strip()

        if operation == "create":
            if not task_manager:
                frappe.throw(
                    "You do not have permission "
                    "to create HR tasks."
                )

            description = (
                frappe.form_dict.get(
                    "description"
                )
                or ""
            ).strip()

            allocated_to = (
                frappe.form_dict.get(
                    "allocated_to"
                )
                or ""
            ).strip()

            due_date = (
                frappe.form_dict.get(
                    "due_date"
                )
                or ""
            ).strip()

            priority = (
                frappe.form_dict.get(
                    "priority"
                )
                or "Medium"
            ).strip()

            reference_type = (
                frappe.form_dict.get(
                    "reference_type"
                )
                or ""
            ).strip()

            reference_name = (
                frappe.form_dict.get(
                    "reference_name"
                )
                or ""
            ).strip()

            if not description:
                frappe.throw(
                    "Task Description is mandatory."
                )

            if not allocated_to:
                frappe.throw(
                    "Allocated To is mandatory."
                )

            if priority not in [
                "High",
                "Medium",
                "Low"
            ]:
                frappe.throw(
                    "Invalid task priority: "
                    + priority
                )

            if not frappe.db.exists(
                "User",
                allocated_to
            ):
                frappe.throw(
                    "Allocated User does not exist: "
                    + allocated_to
                )

            user_enabled = frappe.db.get_value(
                "User",
                allocated_to,
                "enabled"
            )

            if not user_enabled:
                frappe.throw(
                    "Allocated User is disabled: "
                    + allocated_to
                )

            if due_date and due_date < today:
                frappe.throw(
                    "Task Due Date cannot be "
                    "in the past."
                )

            if (
                reference_type
                and not frappe.db.exists(
                    "DocType",
                    reference_type
                )
            ):
                frappe.throw(
                    "Reference DocType does not exist: "
                    + reference_type
                )

            if (
                reference_type
                and not reference_name
            ):
                frappe.throw(
                    "Reference Name is mandatory "
                    "when Reference DocType is selected."
                )

            if (
                reference_name
                and not reference_type
            ):
                frappe.throw(
                    "Reference DocType is mandatory "
                    "when Reference Name is entered."
                )

            if (
                reference_type
                and reference_name
                and not frappe.db.exists(
                    reference_type,
                    reference_name
                )
            ):
                frappe.throw(
                    "Referenced document does not exist: "
                    + reference_type
                    + " "
                    + reference_name
                )

            task_data = {
                "doctype": "ToDo",
                "status": "Open",
                "priority": priority,
                "allocated_to": allocated_to,
                "description": description
            }

            if due_date:
                task_data["date"] = due_date

            if reference_type:
                task_data[
                    "reference_type"
                ] = reference_type

            if reference_name:
                task_data[
                    "reference_name"
                ] = reference_name

            task_doc = frappe.get_doc(
                task_data
            )

            task_doc.insert()

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action": "manage_hr_task",
                "operation": "create",
                "task": task_doc.name,
                "status": task_doc.status,
                "priority": task_doc.priority,
                "allocated_to":
                    task_doc.allocated_to,
                "due_date": task_doc.date,
                "reference_type":
                    task_doc.reference_type,
                "reference_name":
                    task_doc.reference_name,
                "message":
                    "HR task saved in ERPNext"
            }

        elif operation == "complete":
            task_name = (
                frappe.form_dict.get("task")
                or ""
            ).strip()

            completion_remarks = (
                frappe.form_dict.get(
                    "completion_remarks"
                )
                or ""
            ).strip()

            if not task_name:
                frappe.throw(
                    "Task is mandatory."
                )

            if not frappe.db.exists(
                "ToDo",
                task_name
            ):
                frappe.throw(
                    "Task does not exist: "
                    + task_name
                )

            task_doc = frappe.get_doc(
                "ToDo",
                task_name
            )

            can_complete = task_manager

            if (
                task_doc.allocated_to
                == current_user
            ):
                can_complete = True

            if not can_complete:
                frappe.throw(
                    "You do not have permission "
                    "to complete this task."
                )

            if task_doc.status == "Closed":
                frappe.throw(
                    "Task is already completed: "
                    + task_name
                )

            if task_doc.status == "Cancelled":
                frappe.throw(
                    "Cancelled task cannot be completed."
                )

            task_doc.status = "Closed"

            task_meta = frappe.get_meta(
                "ToDo"
            )

            if task_meta.has_field(
                "custom_completed_by"
            ):
                task_doc.custom_completed_by = (
                    current_user
                )

            if task_meta.has_field(
                "custom_completed_on"
            ):
                task_doc.custom_completed_on = (
                    frappe.utils.now()
                )

            if (
                completion_remarks
                and task_meta.has_field(
                    "custom_completion_remarks"
                )
            ):
                task_doc.custom_completion_remarks = (
                    completion_remarks
                )

            task_doc.save()

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action": "manage_hr_task",
                "operation": "complete",
                "task": task_doc.name,
                "status": task_doc.status,
                "completed_by": current_user,
                "message":
                    "HR task completed in ERPNext"
            }

        elif operation == "cancel":
            if not task_manager:
                frappe.throw(
                    "You do not have permission "
                    "to cancel HR tasks."
                )

            task_name = (
                frappe.form_dict.get("task")
                or ""
            ).strip()

            if not task_name:
                frappe.throw(
                    "Task is mandatory."
                )

            if not frappe.db.exists(
                "ToDo",
                task_name
            ):
                frappe.throw(
                    "Task does not exist: "
                    + task_name
                )

            task_doc = frappe.get_doc(
                "ToDo",
                task_name
            )

            if task_doc.status == "Closed":
                frappe.throw(
                    "Completed task cannot be cancelled."
                )

            if task_doc.status == "Cancelled":
                frappe.throw(
                    "Task is already cancelled."
                )

            task_doc.status = "Cancelled"
            task_doc.save()

            frappe.db.commit()

            frappe.response["message"] = {
                "ok": True,
                "action": "manage_hr_task",
                "operation": "cancel",
                "task": task_doc.name,
                "status": task_doc.status,
                "message":
                    "HR task cancelled in ERPNext"
            }

        else:
            frappe.throw(
                "Unsupported HR task operation: "
                + operation
            )

    # HRMS_COMMUNICATION_TASK_ACTION_END

    else:
        frappe.throw("Unsupported HRMS action")

    # HRMS_STEP_29_COMPLETE
