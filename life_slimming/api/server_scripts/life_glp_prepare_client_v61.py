"""LIFE GLP Prepare Client

Original API: life_glp_prepare_client_v61
Source modified: 2026-09-01 13:12:18.243250
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
    # ================================================================
    # LIFE GLP - 6 STEP ASSESSMENT API - V5.64D PDF BILLING GATE FIX
    # ================================================================
    #
    # KEEP THE EXISTING SERVER SCRIPT RECORD:
    #
    #   Script Type : API
    #   API Method  : life_glp_prepare_client_v61
    #   Allow Guest : NO
    #   Disabled    : NO
    #
    # Replace the COMPLETE script body with this file.
    #
    # Actions:
    #   start       -> create/reuse Patient + create/resume GLP Assessment
    #   get         -> load one GLP Assessment
    #   save_step   -> save Step 2, 3, 4 or 5 to the same GLP Assessment
    #   ready       -> validate all gates and mark Ready for Billing
    #
    # This script is written for the EXACT GLP Assessment fields supplied
    # on 30-Aug-2026. It DOES NOT require any DocType structure changes.
    #
    # Important business rules retained:
    # - Direct New Assessment does NOT create a Lead.
    # - Existing Lead is linked only when source_lead is explicitly supplied.
    # - GLP Assessment.consultation_employee remains Healthcare Practitioner.
    # - Dashboard may select an Employee for Consultation Employee; this API
    #   safely maps that Employee to Healthcare Practitioner.
    # - Eligibility verdict is recorded from the clinical user. This script
    #   does NOT invent or recommend a clinical verdict or dose.
    # - Billing remains the owner of Therapy Plan + Sales Invoice.
    # ================================================================

    SERVER_VERSION = "V5.64"

    GLP_ASSESSMENT_DOCTYPE = "GLP Assessment"

    CONTRA_OPTIONS = [
        "Pregnant, lactating or planning pregnancy",
        "Type 1 diabetes",
        "Thyroid carcinoma / MEN2 in self or family",
        "History of pancreatitis",
        "Active gallbladder disease",
        "Severe gastrointestinal disease / gastroparesis",
        "Uncontrolled psychiatric illness",
        "Other uncontrolled medical condition"
    ]

    LAB_TESTS = [
        "HbA1c",
        "Fasting Blood Sugar",
        "Post Prandial Blood Sugar",
        "Thyroid Profile",
        "Liver Function Test",
        "Renal Function Test",
        "Lipid Profile",
        "Complete Blood Count"
    ]

    STATUS_RANK = {
        "Draft": 0,
        "Registration Complete": 1,
        "Screening Complete": 2,
        "Eligibility Reviewed": 3,
        "Prescription Complete": 4,
        "Consent Complete": 5,
        "Ready for Billing": 6,
        "Completed": 7
    }


    def clean(value):
        return str(value or "").strip()


    def to_float(value):
        try:
            return float(value or 0)
        except Exception:
            return 0.0


    def to_int(value):
        try:
            return int(float(value or 0))
        except Exception:
            return 0


    def yes(value):
        value = clean(value).lower()
        return value in ["1", "true", "yes", "y", "on", "checked"]


    def parse_payload():
        raw = frappe.form_dict.get("payload")

        if not raw:
            return {}

        if isinstance(raw, dict):
            return raw

        try:
            # Frappe Server Script safe_exec exposes json.loads directly.
            # frappe.parse_json is not part of the restricted Server Script namespace.
            parsed = json.loads(raw)
            return parsed or {}
        except Exception:
            frappe.throw("Invalid GLP assessment payload.")


    def now_value():
        return frappe.utils.now()


    def today_value():
        return frappe.utils.today()


    def advance_progress(doc, status, next_step):
        current_status = clean(doc.assessment_status)
        current_step = to_int(doc.current_step)

        # Never downgrade a later completed stage when the user edits an older step.
        # Blocked is preserved unless Step 3 itself is reviewed again.
        if current_status == "Blocked":
            doc.current_step = max(current_step, to_int(next_step))
            return

        if STATUS_RANK.get(status, 0) >= STATUS_RANK.get(current_status, 0):
            doc.assessment_status = status

        doc.current_step = max(current_step, to_int(next_step))


    def normalized_mobile(value):
        digits = ""

        for ch in clean(value):
            if ch.isdigit():
                digits += ch

        if len(digits) > 10:
            digits = digits[-10:]

        return digits


    def find_field(meta, fieldnames=None, labels=None):
        fieldnames = fieldnames or []
        labels = labels or []

        for fieldname in fieldnames:
            if meta.has_field(fieldname):
                return meta.get_field(fieldname)

        wanted = []

        for label in labels:
            wanted.append(
                clean(label).lower()
            )

        for df in (meta.fields or []):
            if clean(df.label).lower() in wanted:
                return df

        return None


    def field_by_keywords(meta, include_words, fieldtypes=None):
        include_words = [
            clean(x).lower()
            for x in (include_words or [])
            if clean(x)
        ]

        for df in (meta.fields or []):
            if fieldtypes and df.fieldtype not in fieldtypes:
                continue

            haystack = (
                clean(df.fieldname) +
                " " +
                clean(df.label)
            ).lower()

            ok = True

            for word in include_words:
                if word not in haystack:
                    ok = False
                    break

            if ok:
                return df

        return None


    def select_accepts(df, value):
        if (
            not df
            or df.fieldtype != "Select"
        ):
            return True

        options = []

        for line in clean(df.options).split("\n"):
            item = clean(line)

            if item:
                options.append(item)

        return (
            not options
            or clean(value) in options
        )


    def safe_set(doc, df, value):
        if not df:
            return False

        if value is None:
            return False

        if df.fieldtype == "Check":
            doc.set(
                df.fieldname,
                1 if yes(value) else 0
            )
            return True

        value = clean(value)

        if not value:
            return False

        if df.fieldtype == "Link":
            target = clean(df.options)

            if (
                not target
                or not frappe.db.exists(
                    target,
                    value
                )
            ):
                return False

        if (
            df.fieldtype == "Select"
            and not select_accepts(
                df,
                value
            )
        ):
            return False

        doc.set(
            df.fieldname,
            value
        )

        return True


    def first_name_from_full_name(full_name):
        full_name = clean(full_name)

        if not full_name:
            return ""

        parts = [
            clean(x)
            for x in full_name.split(" ")
            if clean(x)
        ]

        return parts[0] if parts else full_name


    def find_by_mobile(doctype, preferred_fields, mobile):
        """
    V5.64G PERFORMANCE:
    Resolve a Patient/mobile in one get_all query instead of repeatedly
    querying every mobile-like field one by one.

    Common stored forms supported:
      9876543210
      919876543210
      +919876543210
    """
        meta = frappe.get_meta(doctype)
        last10 = normalized_mobile(mobile)

        if not last10:
            return ""

        available = []

        for fieldname in preferred_fields:
            if meta.has_field(fieldname):
                available.append(fieldname)

        if not available:
            return ""

        candidates = [
            last10,
            "91" + last10,
            "+91" + last10
        ]

        or_filters = []

        for fieldname in available:
            for candidate in candidates:
                or_filters.append(
                    [
                        fieldname,
                        "=",
                        candidate
                    ]
                )

        fields = ["name"]

        for fieldname in available:
            if fieldname not in fields:
                fields.append(fieldname)

        rows = frappe.get_all(
            doctype,
            filters=[],
            or_filters=or_filters,
            fields=fields,
            order_by="modified desc",
            limit_page_length=20
        )

        for row in rows:
            for fieldname in available:
                if (
                    normalized_mobile(
                        row.get(fieldname)
                    )
                    == last10
                ):
                    return clean(
                        row.get("name")
                    )

        return ""


    def employee_name(employee):
        if not frappe.db.exists(
            "Employee",
            employee
        ):
            return ""

        return clean(
            frappe.db.get_value(
                "Employee",
                employee,
                "employee_name"
            )
        )


    def resolve_healthcare_practitioner(value):
        """
    Accept either:
      - Healthcare Practitioner name
      - Employee name (HR-EMP-xxxxx)

    Return Healthcare Practitioner name.
    """

        value = clean(value)

        if not value:
            return ""

        if frappe.db.exists(
            "Healthcare Practitioner",
            value
        ):
            return value

        if not frappe.db.exists(
            "Employee",
            value
        ):
            return ""

        hp_meta = frappe.get_meta(
            "Healthcare Practitioner"
        )

        for fieldname in [
            "employee",
            "employee_id",
            "custom_employee",
            "custom_employee_id"
        ]:
            if hp_meta.has_field(fieldname):
                found = frappe.db.get_value(
                    "Healthcare Practitioner",
                    {
                        fieldname: value
                    },
                    "name"
                )

                if found:
                    return found

        emp_name = employee_name(value)

        if emp_name:
            for fieldname in [
                "practitioner_name",
                "employee_name",
                "full_name"
            ]:
                if hp_meta.has_field(fieldname):
                    found = frappe.db.get_value(
                        "Healthcare Practitioner",
                        {
                            fieldname: emp_name
                        },
                        "name"
                    )

                    if found:
                        return found

        return ""


    def require_practitioner(value, label):
        practitioner = resolve_healthcare_practitioner(
            value
        )

        if not practitioner:
            frappe.throw(
                label
                + " could not be matched to an active Healthcare Practitioner."
            )

        return practitioner


    def attach_file_url(file_url, doctype, docname, fieldname=""):
        file_url = clean(file_url)

        if (
            not file_url
            or not doctype
            or not docname
        ):
            return

        file_name = frappe.db.get_value(
            "File",
            {
                "file_url": file_url
            },
            "name"
        )

        if not file_name:
            return

        values = {
            "attached_to_doctype": doctype,
            "attached_to_name": docname
        }

        if fieldname:
            values[
                "attached_to_field"
            ] = fieldname

        try:
            frappe.db.set_value(
                "File",
                file_name,
                values,
                update_modified=False
            )
        except Exception:
            pass


    def create_or_reuse_patient(payload, consultation_practitioner):
        mobile = clean(
            payload.get("mobile")
        )

        patient_name = clean(
            payload.get("full_name")
            or payload.get("patient_name")
        )

        patient = find_by_mobile(
            "Patient",
            [
                "mobile",
                "mobile_no",
                "mobile_number",
                "custom_mobile",
                "custom_mobile_no",
                "custom_mobile_number"
            ],
            mobile
        )

        if patient:
            return patient, False

        # A PD Form is required only when a brand-new Patient must be created.
        if not clean(payload.get("pd_form")):
            frappe.throw("PD Form is required for a new LIFE client. Existing Patients can continue without uploading it again.")

        meta = frappe.get_meta(
            "Patient"
        )

        doc = frappe.new_doc(
            "Patient"
        )

        if meta.has_field("first_name"):
            doc.first_name = (
                first_name_from_full_name(
                    patient_name
                )
                or patient_name
            )

        if meta.has_field("patient_name"):
            doc.patient_name = patient_name

        mobile_df = find_field(
            meta,
            [
                "mobile",
                "mobile_no",
                "mobile_number",
                "custom_mobile",
                "custom_mobile_no",
                "custom_mobile_number"
            ],
            [
                "Mobile",
                "Mobile No",
                "Mobile Number"
            ]
        )

        if mobile_df:
            doc.set(
                mobile_df.fieldname,
                mobile
            )

        gender_df = find_field(
            meta,
            [
                "sex",
                "gender"
            ],
            [
                "Sex",
                "Gender"
            ]
        )

        safe_set(
            doc,
            gender_df,
            payload.get("gender")
        )

        dob_df = find_field(
            meta,
            [
                "dob",
                "date_of_birth"
            ],
            [
                "Date of Birth",
                "DOB"
            ]
        )

        safe_set(
            doc,
            dob_df,
            payload.get("date_of_birth")
        )

        branch_df = find_field(
            meta,
            [
                "branch_name",
                "branch",
                "custom_branch_name",
                "custom_branch"
            ],
            [
                "Branch Name",
                "Branch"
            ]
        )

        safe_set(
            doc,
            branch_df,
            payload.get("branch")
        )

        media_df = find_field(
            meta,
            [
                "custom_media",
                "media",
                "custom_source",
                "source"
            ],
            [
                "Media",
                "Source",
                "Lead Source"
            ]
        )

        safe_set(
            doc,
            media_df,
            payload.get("media")
        )

        visited_df = find_field(
            meta,
            [
                "custom_client_visited_for_",
                "custom_visited_for",
                "visited_for",
                "custom_visit_for"
            ],
            [
                "Visited For",
                "Visit For"
            ]
        )

        safe_set(
            doc,
            visited_df,
            payload.get("visited_for")
        )

        booked_df = find_field(
            meta,
            [
                "custom_final_decision",
                "final_decision",
                "custom_booking_decision",
                "booking_decision"
            ],
            [
                "Final Decision",
                "Booked Or Not Booked",
                "Booking Decision"
            ]
        )

        safe_set(
            doc,
            booked_df,
            payload.get("booked_or_not_booked")
        )

        category_df = find_field(
            meta,
            [
                "custom_treatment_category",
                "treatment_category",
                "custom_category"
            ],
            [
                "Treatment Category",
                "Category"
            ]
        )

        safe_set(
            doc,
            category_df,
            payload.get("treatment_category")
        )

        consultation_df = find_field(
            meta,
            [
                "custom_employee_id",
                "custom_consultation_employee",
                "consultation_employee"
            ],
            [
                "Consultation Employee"
            ]
        )

        if consultation_df:
            if (
                consultation_df.fieldtype == "Link"
                and clean(
                    consultation_df.options
                ) == "Healthcare Practitioner"
            ):
                doc.set(
                    consultation_df.fieldname,
                    consultation_practitioner
                )

            elif (
                consultation_df.fieldtype == "Link"
                and clean(
                    consultation_df.options
                ) == "Employee"
            ):
                employee_value = clean(
                    payload.get(
                        "consultation_employee"
                    )
                )

                if frappe.db.exists(
                    "Employee",
                    employee_value
                ):
                    doc.set(
                        consultation_df.fieldname,
                        employee_value
                    )

        source_lead = clean(
            payload.get("source_lead")
        )

        if (
            source_lead
            and frappe.db.exists(
                "Lead",
                source_lead
            )
        ):
            lead_df = find_field(
                meta,
                [
                    "custom_lead",
                    "lead",
                    "custom_lead_id"
                ],
                [
                    "Lead"
                ]
            )

            if (
                lead_df
                and lead_df.fieldtype == "Link"
                and clean(
                    lead_df.options
                ) == "Lead"
            ):
                doc.set(
                    lead_df.fieldname,
                    source_lead
                )

        pd_form = clean(
            payload.get("pd_form")
        )

        pd_df = find_field(
            meta,
            [
                "custom_pd_form",
                "pd_form",
                "custom_pd_form_file",
                "pd_form_file"
            ],
            [
                "PD Form"
            ]
        )

        if (
            pd_form
            and pd_df
            and pd_df.fieldtype in [
                "Attach",
                "Attach Image",
                "Data",
                "Small Text",
                "Text"
            ]
        ):
            doc.set(
                pd_df.fieldname,
                pd_form
            )

        # LIFE hooks may populate additional link fields. Ignore link validation
        # for this initial insert, then all values written by this script remain
        # traceable and the required GLP assessment links are validated separately.
        doc.insert(
            ignore_permissions=True,
            ignore_links=True
        )

        if pd_form:
            attach_file_url(
                pd_form,
                "Patient",
                doc.name,
                pd_df.fieldname if pd_df else ""
            )

        return doc.name, True


    def find_open_assessment(patient):
        if not patient:
            return ""

        rows = frappe.get_all(
            GLP_ASSESSMENT_DOCTYPE,
            filters=[
                [
                    "patient",
                    "=",
                    patient
                ],
                [
                    "assessment_status",
                    "!=",
                    "Completed"
                ]
            ],
            fields=[
                "name",
                "assessment_status",
                "current_step",
                "modified"
            ],
            order_by="modified desc",
            limit_page_length=1
        )

        if rows:
            return clean(
                rows[0].get("name")
            )

        return ""


    def assessment_patient_value(patient_doc, field_candidates, label_candidates):
        if not patient_doc:
            return ""

        meta = frappe.get_meta("Patient")
        df = find_field(
            meta,
            field_candidates,
            label_candidates
        )

        if not df:
            return ""

        return clean(
            patient_doc.get(df.fieldname)
        )


    def assign_assessment_client_sequence_name(doc):
        # User-facing GLP Assessment naming:
        #   Client Name-001, Client Name-002, ...
        # Sequence is calculated per Patient so two different Patients with the
        # same display name do not affect one another.
        if not doc or not doc.is_new():
            return

        patient = clean(doc.patient)
        client_name = clean(
            doc.patient_name
            or doc.full_name
            or patient
            or "GLP Assessment"
        )

        # Frappe document names cannot safely contain slash characters.
        client_name = client_name.replace("/", "-").replace("\\", "-")
        client_name = client_name[:110].strip()

        next_no = (
            frappe.db.count(
                GLP_ASSESSMENT_DOCTYPE,
                filters={"patient": patient} if patient else {}
            )
            + 1
        )

        # IMPORTANT: Frappe Server Script safe_exec can reject Python string
        # string helpers. Build the 3-digit sequence manually.
        seq = str(next_no)
        while len(seq) < 3:
            seq = "0" + seq

        candidate = client_name + "-" + seq

        while frappe.db.exists(GLP_ASSESSMENT_DOCTYPE, candidate):
            next_no = next_no + 1
            seq = str(next_no)
            while len(seq) < 3:
                seq = "0" + seq
            candidate = client_name + "-" + seq

        doc.name = candidate



    def latest_registration_context(patient, exclude_name=""):
        """
    Reuse registration details from earlier GLP Assessments.

    Important:
    - Source shown in the wizard is GLP Assessment.media, not source_lead.
    - Pick the newest NON-EMPTY value for each field instead of relying on
      only the latest assessment, because a newer draft may have blank fields.
    """
        if not patient:
            return {}

        filters = {
            "patient": patient
        }

        rows = frappe.get_all(
            GLP_ASSESSMENT_DOCTYPE,
            filters=filters,
            fields=[
                "name",
                "media",
                "source_lead",
                "consultation_employee",
                "pd_form",
                "branch",
                "mobile",
                "gender",
                "date_of_birth",
                "age"
            ],
            order_by="modified desc",
            limit_page_length=50
        )

        result = {}

        wanted = [
            "media",
            "source_lead",
            "consultation_employee",
            "pd_form",
            "branch",
            "mobile",
            "gender",
            "date_of_birth",
            "age"
        ]

        for row in rows:
            if (
                exclude_name
                and clean(row.get("name")) == clean(exclude_name)
            ):
                continue

            for fieldname in wanted:
                if (
                    not clean(result.get(fieldname))
                    and clean(row.get(fieldname))
                ):
                    result[fieldname] = row.get(fieldname)

        return result


    def backfill_existing_assessment_registration(doc):
        """
    Existing/open assessment may have been created earlier with blank
    registration fields. Fill ONLY missing values from older assessments.
    Existing values are never overwritten.
    """
        if not doc or not clean(doc.get("patient")):
            return doc

        previous = latest_registration_context(
            clean(doc.get("patient")),
            clean(doc.get("name"))
        )

        updates = {}

        for fieldname in [
            "media",
            "source_lead",
            "consultation_employee",
            "pd_form",
            "branch",
            "mobile",
            "gender",
            "date_of_birth",
            "age"
        ]:
            if (
                not clean(doc.get(fieldname))
                and clean(previous.get(fieldname))
            ):
                updates[fieldname] = previous.get(fieldname)

        if updates:
            for fieldname in updates:
                doc.set(
                    fieldname,
                    updates.get(fieldname)
                )

            doc.save(
                ignore_permissions=True
            )

        return doc



    def action_start_existing_patient(payload):
        # Existing Patient -> NEW/OPEN GLP Assessment -> Step 2.
        # Never creates another Patient.
        patient = clean(payload.get("patient"))

        if not patient:
            mobile = clean(payload.get("mobile"))
            if mobile:
                patient = find_by_mobile(
                    "Patient",
                    [
                        "mobile",
                        "mobile_no",
                        "mobile_number",
                        "custom_mobile",
                        "custom_mobile_no",
                        "custom_mobile_number"
                    ],
                    mobile
                )

        if not patient or not frappe.db.exists("Patient", patient):
            return {
                "success": True,
                "server_version": SERVER_VERSION,
                "patient_created": False,
                "existing_patient": False,
                "patient_not_found": True,
                "patient": "",
                "assessment": None
            }

        # Do not create duplicate unfinished assessments. If this Patient already
        # has an assessment that is not Completed, continue that same assessment.
        open_name = find_open_assessment(patient)
        if open_name:
            open_doc = frappe.get_doc(
                GLP_ASSESSMENT_DOCTYPE,
                open_name
            )

            open_doc = backfill_existing_assessment_registration(
                open_doc
            )

            return {
                "success": True,
                "server_version": SERVER_VERSION,
                "patient_created": False,
                "existing_patient": True,
                "resumed_open_assessment": True,
                "patient": patient,
                "assessment": open_doc.as_dict()
            }

        patient_doc = frappe.get_doc("Patient", patient)

        previous_context = latest_registration_context(
            patient
        )

        patient_name = assessment_patient_value(
            patient_doc,
            ["patient_name", "full_name", "first_name"],
            ["Patient Name", "Full Name", "First Name"]
        ) or patient

        mobile = assessment_patient_value(
            patient_doc,
            [
                "mobile", "mobile_no", "mobile_number",
                "custom_mobile", "custom_mobile_no", "custom_mobile_number",
                "contact_mobile", "contact_number",
                "phone", "phone_no", "phone_number"
            ],
            ["Mobile", "Mobile No", "Mobile Number", "Phone", "Phone No"]
        )

        gender = assessment_patient_value(
            patient_doc,
            ["sex", "gender"],
            ["Sex", "Gender"]
        )

        dob = assessment_patient_value(
            patient_doc,
            ["dob", "date_of_birth"],
            ["Date of Birth", "DOB"]
        )

        branch = assessment_patient_value(
            patient_doc,
            ["branch_name", "branch", "custom_branch_name", "custom_branch"],
            ["Branch Name", "Branch"]
        )

        doc = frappe.new_doc(GLP_ASSESSMENT_DOCTYPE)
        doc.patient = patient
        doc.patient_name = patient_name
        doc.full_name = patient_name
        doc.mobile = mobile
        doc.gender = gender
        doc.date_of_birth = dob
        doc.branch = (
            branch
            or clean(
                previous_context.get("branch")
            )
        )

        doc.assessment_owner = frappe.session.user
        doc.assessment_date = today_value()

        previous_media = clean(
            previous_context.get(
                "media"
            )
        )

        if previous_media:
            doc.media = previous_media

        source_lead = clean(
            previous_context.get("source_lead")
            or payload.get("source_lead")
        )

        if source_lead and frappe.db.exists("Lead", source_lead):
            doc.source_lead = source_lead

        consultation_employee = clean(
            previous_context.get(
                "consultation_employee"
            )
        )

        if consultation_employee:
            doc.consultation_employee = consultation_employee

        previous_pd_form = clean(
            previous_context.get(
                "pd_form"
            )
        )

        if previous_pd_form:
            doc.pd_form = previous_pd_form

        doc.assessment_status = "Registration Complete"
        doc.current_step = 2
        doc.last_saved_step = 1
        doc.registration_completed_on = now_value()

        # A repeat programme is intentionally a new GLP Assessment.
        # Patient remains the same; Therapy Plan will be created later in Billing.
        assign_assessment_client_sequence_name(doc)

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "server_version": SERVER_VERSION,
            "patient_created": False,
            "existing_patient": True,
            "resumed_open_assessment": False,
            "patient": patient,
            "assessment": doc.as_dict()
        }


    def set_common_registration(doc, payload, consultation_practitioner):
        doc.patient = clean(
            payload.get("patient")
            or doc.patient
        )

        if payload.get("full_name") is not None:
            doc.patient_name = clean(
                payload.get("full_name")
            )

            doc.full_name = clean(
                payload.get("full_name")
            )

        if payload.get("mobile") is not None:
            doc.mobile = clean(
                payload.get("mobile")
            )

        if payload.get("branch") is not None:
            doc.branch = clean(
                payload.get("branch")
            )

        if consultation_practitioner:
            doc.consultation_employee = (
                consultation_practitioner
            )

        if payload.get("date_of_birth") is not None:
            doc.date_of_birth = clean(
                payload.get("date_of_birth")
            )

        if payload.get("age") is not None:
            doc.age = to_int(
                payload.get("age")
            )

        if payload.get("gender") is not None:
            doc.gender = clean(
                payload.get("gender")
            )

        if payload.get("media") is not None:
            doc.media = clean(
                payload.get("media")
            )

        if payload.get("visited_for") is not None:
            doc.visited_for = clean(
                payload.get("visited_for")
            )

        if payload.get("booked_or_not_booked") is not None:
            doc.booked_or_not_booked = clean(
                payload.get(
                    "booked_or_not_booked"
                )
            )

        if payload.get("treatment_category") is not None:
            doc.treatment_category = clean(
                payload.get(
                    "treatment_category"
                )
            )

        if payload.get("pd_form") is not None:
            doc.pd_form = clean(
                payload.get("pd_form")
            )

        source_lead = clean(
            payload.get("source_lead")
        )

        if (
            source_lead
            and frappe.db.exists(
                "Lead",
                source_lead
            )
        ):
            doc.source_lead = source_lead

        elif payload.get("source_lead") is not None:
            doc.source_lead = None

        doc.assessment_date = (
            doc.assessment_date
            or today_value()
        )

        doc.assessment_owner = (
            doc.assessment_owner
            or frappe.session.user
        )


    def child_label_field(meta, kind):
        if kind == "contra":
            return (
                find_field(
                    meta,
                    [
                        "contraindication",
                        "condition",
                        "contraindication_name"
                    ],
                    [
                        "Contraindication",
                        "Condition"
                    ]
                )
                or field_by_keywords(
                    meta,
                    [
                        "contra"
                    ],
                    [
                        "Data",
                        "Select",
                        "Small Text"
                    ]
                )
            )

        return (
            find_field(
                meta,
                [
                    "lab_test",
                    "test",
                    "lab",
                    "test_name"
                ],
                [
                    "Lab Test",
                    "Test",
                    "Lab"
                ]
            )
            or field_by_keywords(
                meta,
                [
                    "lab"
                ],
                [
                    "Data",
                    "Select",
                    "Small Text"
                ]
            )
            or field_by_keywords(
                meta,
                [
                    "test"
                ],
                [
                    "Data",
                    "Select",
                    "Small Text"
                ]
            )
        )


    def replace_contraindications(doc, rows):
        rows = rows or []

        table_df = frappe.get_meta(
            GLP_ASSESSMENT_DOCTYPE
        ).get_field(
            "contraindications"
        )

        if not table_df:
            return

        child_doctype = clean(
            table_df.options
        )

        if not child_doctype:
            return

        meta = frappe.get_meta(
            child_doctype
        )

        label_df = child_label_field(
            meta,
            "contra"
        )

        selected_df = find_field(
            meta,
            [
                "selected",
                "is_selected",
                "checked"
            ],
            [
                "Selected",
                "Checked"
            ]
        )

        remarks_df = find_field(
            meta,
            [
                "remarks",
                "remark",
                "notes"
            ],
            [
                "Remarks",
                "Remark",
                "Notes"
            ]
        )

        gate_df = find_field(
            meta,
            [
                "gate_type",
                "category"
            ],
            [
                "Gate Type",
                "Category"
            ]
        )

        if not label_df:
            frappe.throw(
                child_doctype
                + " needs a Contraindication/Condition field."
            )

        selected_values = []

        for row in rows:
            if isinstance(row, dict):
                label = clean(
                    row.get("contraindication")
                    or row.get("label")
                    or row.get("condition")
                )

                selected = yes(
                    row.get("selected", True)
                )

                remarks = clean(
                    row.get("remarks")
                )

                gate_type = clean(
                    row.get("gate_type")
                )
            else:
                label = clean(row)
                selected = True
                remarks = ""
                gate_type = ""

            if (
                label
                and selected
            ):
                selected_values.append(
                    label
                )

        doc.set(
            "contraindications",
            []
        )

        # If a Selected field exists, keep the full checklist in the child table.
        # Otherwise store selected rows only.
        source_labels = (
            CONTRA_OPTIONS
            if selected_df
            else selected_values
        )

        for label in source_labels:
            child = doc.append(
                "contraindications",
                {}
            )

            child.set(
                label_df.fieldname,
                label
            )

            is_selected = (
                label in selected_values
            )

            if selected_df:
                child.set(
                    selected_df.fieldname,
                    1 if is_selected else 0
                )

            if remarks_df:
                row_match = None

                for source_row in rows:
                    if isinstance(source_row, dict):
                        source_label = clean(
                            source_row.get("contraindication")
                            or source_row.get("label")
                            or source_row.get("condition")
                        )

                        if source_label == label:
                            row_match = source_row
                            break

                if row_match:
                    child.set(
                        remarks_df.fieldname,
                        clean(
                            row_match.get("remarks")
                        )
                    )

            # Do not invent a medical hard-stop classification.
            # Store gate_type only when the UI explicitly supplies it.
            if gate_df:
                row_match = None

                for source_row in rows:
                    if isinstance(source_row, dict):
                        source_label = clean(
                            source_row.get("contraindication")
                            or source_row.get("label")
                            or source_row.get("condition")
                        )

                        if source_label == label:
                            row_match = source_row
                            break

                if (
                    row_match
                    and clean(
                        row_match.get("gate_type")
                    )
                    and select_accepts(
                        gate_df,
                        row_match.get("gate_type")
                    )
                ):
                    child.set(
                        gate_df.fieldname,
                        clean(
                            row_match.get("gate_type")
                        )
                    )


    def replace_baseline_labs(doc, rows):
        rows = rows or []

        table_df = frappe.get_meta(
            GLP_ASSESSMENT_DOCTYPE
        ).get_field(
            "baseline_labs"
        )

        if not table_df:
            return

        child_doctype = clean(
            table_df.options
        )

        if not child_doctype:
            return

        meta = frappe.get_meta(
            child_doctype
        )

        label_df = child_label_field(
            meta,
            "lab"
        )

        if not label_df:
            frappe.throw(
                child_doctype
                + " needs a Lab Test/Test field."
            )

        status_df = find_field(
            meta,
            [
                "status",
                "lab_status"
            ],
            [
                "Status",
                "Lab Status"
            ]
        )

        date_df = find_field(
            meta,
            [
                "test_date",
                "date"
            ],
            [
                "Test Date",
                "Date"
            ]
        )

        report_df = find_field(
            meta,
            [
                "report_file",
                "report",
                "attachment"
            ],
            [
                "Report File",
                "Report",
                "Attachment"
            ]
        )

        reviewed_by_df = find_field(
            meta,
            [
                "reviewed_by"
            ],
            [
                "Reviewed By"
            ]
        )

        reviewed_on_df = find_field(
            meta,
            [
                "reviewed_on"
            ],
            [
                "Reviewed On"
            ]
        )

        remarks_df = find_field(
            meta,
            [
                "remarks",
                "notes"
            ],
            [
                "Remarks",
                "Notes"
            ]
        )

        doc.set(
            "baseline_labs",
            []
        )

        supplied = {}

        for row in rows:
            if not isinstance(row, dict):
                continue

            label = clean(
                row.get("lab_test")
                or row.get("test")
                or row.get("lab")
            )

            if label:
                supplied[
                    label.lower()
                ] = row

        ordered_labels = []

        for label in LAB_TESTS:
            ordered_labels.append(label)

        for key in supplied:
            original = clean(
                supplied[key].get("lab_test")
                or supplied[key].get("test")
                or supplied[key].get("lab")
            )

            if (
                original
                and original not in ordered_labels
            ):
                ordered_labels.append(
                    original
                )

        for label in ordered_labels:
            row = (
                supplied.get(
                    label.lower()
                )
                or {}
            )

            child = doc.append(
                "baseline_labs",
                {}
            )

            child.set(
                label_df.fieldname,
                label
            )

            status = clean(
                row.get("status")
                or "Pending"
            )

            if status_df:
                if select_accepts(
                    status_df,
                    status
                ):
                    child.set(
                        status_df.fieldname,
                        status
                    )

            test_date = clean(
                row.get("test_date")
            )

            if (
                date_df
                and test_date
            ):
                child.set(
                    date_df.fieldname,
                    test_date
                )

            report_file = clean(
                row.get("report_file")
            )

            if (
                report_df
                and report_file
            ):
                child.set(
                    report_df.fieldname,
                    report_file
                )

            reviewed_by = clean(
                row.get("reviewed_by")
            )

            if (
                reviewed_by_df
                and reviewed_by
            ):
                practitioner = resolve_healthcare_practitioner(
                    reviewed_by
                )

                if practitioner:
                    child.set(
                        reviewed_by_df.fieldname,
                        practitioner
                    )

            if (
                reviewed_on_df
                and clean(
                    row.get("reviewed_on")
                )
            ):
                child.set(
                    reviewed_on_df.fieldname,
                    clean(
                        row.get("reviewed_on")
                    )
                )

            if (
                remarks_df
                and clean(
                    row.get("remarks")
                )
            ):
                child.set(
                    remarks_df.fieldname,
                    clean(
                        row.get("remarks")
                    )
                )


    def validate_registration(payload):
        if not clean(
            payload.get("full_name")
        ):
            frappe.throw(
                "Full Name is required."
            )

        if len(
            normalized_mobile(
                payload.get("mobile")
            )
        ) != 10:
            frappe.throw(
                "Enter a valid 10-digit mobile number."
            )

        if not clean(
            payload.get("gender")
        ):
            frappe.throw(
                "Gender is required."
            )

        if not clean(
            payload.get("branch")
        ):
            frappe.throw(
                "Branch is required."
            )

        if not clean(
            payload.get("media")
        ):
            frappe.throw(
                "Media / Source is required."
            )

        if not clean(
            payload.get("consultation_employee")
        ):
            frappe.throw(
                "Consultation Employee is required."
            )

        if not clean(
            payload.get("visited_for")
        ):
            frappe.throw(
                "Visited For is required."
            )

        if not clean(
            payload.get("booked_or_not_booked")
        ):
            frappe.throw(
                "Booked / Not-Booked is required."
            )

        if not clean(
            payload.get("treatment_category")
        ):
            frappe.throw(
                "Treatment Category is required."
            )


    def action_start(payload):
        validate_registration(
            payload
        )

        consultation_practitioner = (
            require_practitioner(
                payload.get(
                    "consultation_employee"
                ),
                "Consultation Employee"
            )
        )

        # RestrictedPython Server Script compatibility:
        # Do not use tuple-unpacking here. Frappe safe_exec on this site does
        # not expose _unpack_sequence_.
        patient_result = create_or_reuse_patient(
            payload,
            consultation_practitioner
        )

        patient = patient_result[0]
        created = patient_result[1]

        assessment_name = find_open_assessment(
            patient
        )

        if assessment_name:
            doc = frappe.get_doc(
                GLP_ASSESSMENT_DOCTYPE,
                assessment_name
            )
        else:
            doc = frappe.new_doc(
                GLP_ASSESSMENT_DOCTYPE
            )

            doc.patient = patient

        payload["patient"] = patient

        set_common_registration(
            doc,
            payload,
            consultation_practitioner
        )

        advance_progress(
            doc,
            "Registration Complete",
            2
        )

        doc.last_saved_step = max(
            to_int(
                doc.last_saved_step
            ),
            1
        )

        if not doc.registration_completed_on:
            doc.registration_completed_on = (
                now_value()
            )

        if doc.is_new():
            assign_assessment_client_sequence_name(doc)
            doc.insert(
                ignore_permissions=True
            )
        else:
            doc.save(
                ignore_permissions=True
            )

        if clean(
            doc.pd_form
        ):
            attach_file_url(
                doc.pd_form,
                GLP_ASSESSMENT_DOCTYPE,
                doc.name,
                "pd_form"
            )

        frappe.db.commit()

        return {
            "success": True,
            "server_version": SERVER_VERSION,
            "patient_created": created,
            "patient": patient,
            "assessment": doc.as_dict()
        }


    def action_get(payload):
        name = clean(
            payload.get("assessment")
        )

        if (
            name
            and frappe.db.exists(
                GLP_ASSESSMENT_DOCTYPE,
                name
            )
        ):
            doc = frappe.get_doc(
                GLP_ASSESSMENT_DOCTYPE,
                name
            )

            return {
                "success": True,
                "server_version": SERVER_VERSION,
                "assessment": doc.as_dict()
            }

        mobile = clean(
            payload.get("mobile")
        )

        patient = clean(
            payload.get("patient")
        )

        if (
            not patient
            and mobile
        ):
            patient = find_by_mobile(
                "Patient",
                [
                    "mobile",
                    "mobile_no",
                    "mobile_number",
                    "custom_mobile",
                    "custom_mobile_no",
                    "custom_mobile_number"
                ],
                mobile
            )

        if patient:
            assessment_name = find_open_assessment(
                patient
            )

            if assessment_name:
                doc = frappe.get_doc(
                    GLP_ASSESSMENT_DOCTYPE,
                    assessment_name
                )

                return {
                    "success": True,
                    "server_version": SERVER_VERSION,
                    "assessment": doc.as_dict()
                }

        return {
            "success": True,
            "server_version": SERVER_VERSION,
            "assessment": None
        }


    def action_save_step(payload):
        name = clean(
            payload.get("assessment")
        )

        step = to_int(
            payload.get("step")
        )

        if (
            not name
            or not frappe.db.exists(
                GLP_ASSESSMENT_DOCTYPE,
                name
            )
        ):
            frappe.throw(
                "GLP Assessment was not found. Save Registration first."
            )

        doc = frappe.get_doc(
            GLP_ASSESSMENT_DOCTYPE,
            name
        )

        blocked = False

        if step == 2:
            height = to_float(
                payload.get("height_cm")
            )

            weight = to_float(
                payload.get("weight_kg")
            )

            if height <= 0:
                frappe.throw(
                    "Height is required."
                )

            if weight <= 0:
                frappe.throw(
                    "Weight is required."
                )

            metres = (
                height / 100.0
            )

            bmi = (
                weight /
                (
                    metres *
                    metres
                )
            )

            doc.height_cm = height
            doc.weight_kg = weight
            doc.bmi = round(
                bmi,
                1
            )
            doc.waist_cm = to_float(
                payload.get("waist_cm")
            )
            doc.body_fat_ = to_float(
                payload.get("body_fat_percentage")
            )
            doc.visceral_fat = to_float(
                payload.get("visceral_fat")
            )
            doc.muscle_mass_kg = to_float(
                payload.get("muscle_mass_kg")
            )
            doc.target_weight_kg = to_float(
                payload.get("target_weight_kg")
            )
            doc.bca_completed = (
                1
                if yes(
                    payload.get("bca_completed")
                )
                else 0
            )
            doc.bca_report = clean(
                payload.get("bca_report")
            )

            replace_contraindications(
                doc,
                payload.get(
                    "contraindications"
                )
                or []
            )

            replace_baseline_labs(
                doc,
                payload.get(
                    "baseline_labs"
                )
                or []
            )

            advance_progress(
                doc,
                "Screening Complete",
                3
            )
            doc.last_saved_step = max(
                to_int(
                    doc.last_saved_step
                ),
                2
            )
            doc.screening_completed_on = (
                now_value()
            )

        elif step == 3:
            verdict = clean(
                payload.get(
                    "eligibility_verdict"
                )
            )

            if verdict not in [
                "Green",
                "Amber",
                "Red"
            ]:
                frappe.throw(
                    "Select Eligibility Verdict: Green, Amber or Red."
                )

            assessed_by = (
                require_practitioner(
                    payload.get(
                        "assessed_by"
                    ),
                    "Assessed By"
                )
            )

            doctor_note = clean(
                payload.get(
                    "doctor_note"
                )
            )

            if (
                verdict in [
                    "Amber",
                    "Red"
                ]
                and not doctor_note
            ):
                frappe.throw(
                    "Doctor Note is required for Amber or Red eligibility."
                )

            override = yes(
                payload.get(
                    "eligibility_override"
                )
            )

            override_reason = clean(
                payload.get(
                    "override_reason"
                )
            )

            if (
                verdict == "Red"
                and override
                and not override_reason
            ):
                frappe.throw(
                    "Override Reason is required when a Red assessment is overridden."
                )

            doc.eligibility_verdict = (
                verdict
            )
            doc.eligibility_reasons = clean(
                payload.get(
                    "eligibility_reasons"
                )
            )
            doc.doctor_note = doctor_note
            doc.assessed_by = assessed_by
            doc.eligibility_reviewed_on = (
                now_value()
            )
            doc.eligibility_override = (
                1 if override else 0
            )
            doc.override_reason = (
                override_reason
            )
            doc.override_by = (
                frappe.session.user
                if override
                else None
            )

            if (
                verdict == "Red"
                and not override
            ):
                doc.assessment_status = (
                    "Blocked"
                )
                doc.current_step = 3
                blocked = True

            else:
                # Step 3 is the only step allowed to clear a prior Blocked state
                # after a practitioner records a new non-Red verdict / approved override.
                if clean(doc.assessment_status) == "Blocked":
                    doc.assessment_status = "Eligibility Reviewed"
                    doc.current_step = max(to_int(doc.current_step), 4)
                else:
                    advance_progress(
                        doc,
                        "Eligibility Reviewed",
                        4
                    )

            doc.last_saved_step = max(
                to_int(
                    doc.last_saved_step
                ),
                3
            )
            doc.eligibility_completed_on = (
                now_value()
            )

        elif step == 4:
            molecule = clean(
                payload.get("molecule")
            )

            dose = clean(
                payload.get(
                    "starting_dose_mg"
                )
            )

            if molecule not in [
                "Tirzepatide",
                "Semaglutide"
            ]:
                frappe.throw(
                    "Select Molecule."
                )

            dose_df = frappe.get_meta(
                GLP_ASSESSMENT_DOCTYPE
            ).get_field(
                "starting_dose_mg"
            )

            if not select_accepts(
                dose_df,
                dose
            ):
                frappe.throw(
                    "Select a valid Starting Dose from GLP Assessment."
                )

            prescribed_by = (
                require_practitioner(
                    payload.get(
                        "prescribed_by"
                    ),
                    "Prescribed By"
                )
            )

            reference = clean(
                payload.get(
                    "prescription_reference"
                )
            )

            prescription_file = clean(
                payload.get(
                    "prescription_file"
                )
            )

            prescription_date = clean(
                payload.get(
                    "prescription_date"
                )
            )

            if not dose:
                frappe.throw(
                    "Starting Dose is required."
                )

            if not reference:
                frappe.throw(
                    "Prescription Reference is required."
                )

            if not prescription_file:
                frappe.throw(
                    "Prescription File is required."
                )

            if not prescription_date:
                frappe.throw(
                    "Prescription Date is required."
                )

            doc.molecule = molecule
            doc.starting_dose_mg = dose
            doc.prescription_reference = (
                reference
            )
            doc.prescription_file = (
                prescription_file
            )
            doc.prescribed_by = (
                prescribed_by
            )
            doc.prescription_date = (
                prescription_date
            )
            doc.prescription_notes = clean(
                payload.get(
                    "prescription_notes"
                )
            )
            doc.prescription_locked = 1
            doc.prescription_locked_on = (
                now_value()
            )
            advance_progress(
                doc,
                "Prescription Complete",
                5
            )
            doc.last_saved_step = max(
                to_int(
                    doc.last_saved_step
                ),
                4
            )
            doc.prescription_completed_on = (
                now_value()
            )

        elif step == 5:
            required_explanations = [
                "medical_supervision_explained",
                "common_effects_explained",
                "serious_risks_explained",
                "attendance_requirement_explained",
                "outcome_disclaimer_explained",
                "package_terms_explained",
                "health_change_reporting_explained"
            ]

            for fieldname in required_explanations:
                if not yes(
                    payload.get(fieldname)
                ):
                    frappe.throw(
                        "Complete all consent explanation confirmations before continuing."
                    )

            if not yes(
                payload.get(
                    "consent_signed"
                )
            ):
                frappe.throw(
                    "Consent Signed is required."
                )

            consent_file = clean(
                payload.get(
                    "consent_file"
                )
            )

            if not consent_file:
                frappe.throw(
                    "Signed Consent File is required."
                )

            consent_taken_by = (
                require_practitioner(
                    payload.get(
                        "consent_taken_by"
                    ),
                    "Consent Taken By"
                )
            )

            consent_datetime = clean(
                payload.get(
                    "consent_date_and_time"
                )
            )

            if not consent_datetime:
                frappe.throw(
                    "Consent Date and Time is required."
                )

            doc.consent_signed = 1
            doc.consent_file = (
                consent_file
            )
            doc.photo_id_collected = (
                1
                if yes(
                    payload.get(
                        "photo_id_collected"
                    )
                )
                else 0
            )
            doc.photo_id_file = clean(
                payload.get(
                    "photo_id_file"
                )
            )

            if (
                doc.photo_id_collected
                and not doc.photo_id_file
            ):
                frappe.throw(
                    "Attach Photo ID File when Photo ID Collected is checked."
                )

            for fieldname in required_explanations:
                doc.set(
                    fieldname,
                    1
                )

            doc.consent_taken_by = (
                consent_taken_by
            )
            doc.consent_date_and_time = (
                consent_datetime
            )
            doc.consent_version = clean(
                payload.get(
                    "consent_version"
                )
            )
            doc.consent_remarks = clean(
                payload.get(
                    "consent_remarks"
                )
            )

            advance_progress(
                doc,
                "Consent Complete",
                6
            )
            doc.last_saved_step = max(
                to_int(
                    doc.last_saved_step
                ),
                5
            )
            doc.consent_completed_on = (
                now_value()
            )

        else:
            frappe.throw(
                "Unsupported GLP assessment step."
            )

        doc.save(
            ignore_permissions=True
        )

        for fieldname in [
            "bca_report",
            "prescription_file",
            "consent_file",
            "photo_id_file"
        ]:
            file_url = clean(
                doc.get(fieldname)
            )

            if file_url:
                attach_file_url(
                    file_url,
                    GLP_ASSESSMENT_DOCTYPE,
                    doc.name,
                    fieldname
                )

        for row in (
            doc.get("baseline_labs")
            or []
        ):
            row_dict = row.as_dict()

            file_url = ""

            for key in [
                "report_file",
                "report",
                "attachment"
            ]:
                if clean(
                    row_dict.get(key)
                ):
                    file_url = clean(
                        row_dict.get(key)
                    )
                    break

            if file_url:
                attach_file_url(
                    file_url,
                    GLP_ASSESSMENT_DOCTYPE,
                    doc.name
                )

        frappe.db.commit()

        return {
            "success": True,
            "server_version": SERVER_VERSION,
            "blocked": blocked,
            "assessment": doc.as_dict()
        }


    def action_ready(payload):
        name = clean(
            payload.get("assessment")
        )

        if (
            not name
            or not frappe.db.exists(
                GLP_ASSESSMENT_DOCTYPE,
                name
            )
        ):
            frappe.throw(
                "GLP Assessment was not found."
            )

        doc = frappe.get_doc(
            GLP_ASSESSMENT_DOCTYPE,
            name
        )

        if not doc.patient:
            frappe.throw(
                "Patient is missing from GLP Assessment."
            )

        if clean(
            doc.eligibility_verdict
        ) == "Red":
            if not doc.eligibility_override:
                frappe.throw(
                    "This GLP Assessment is Red and has not been explicitly overridden."
                )

            if not clean(
                doc.override_reason
            ):
                frappe.throw(
                    "Override Reason is required for a Red assessment."
                )

        if not doc.prescription_locked:
            frappe.throw(
                "Prescription step is not complete."
            )

        if not clean(
            doc.prescription_reference
        ):
            frappe.throw(
                "Prescription Reference is missing."
            )

        if not clean(
            doc.prescription_file
        ):
            frappe.throw(
                "Prescription File is missing."
            )

        if not doc.consent_signed:
            frappe.throw(
                "Signed Consent is required before Billing."
            )

        if not clean(
            doc.consent_file
        ):
            frappe.throw(
                "Signed Consent File is required before Billing."
            )

        # ============================================================
        # V5.64D - BASELINE LABS DO NOT BLOCK BILLING
        # ============================================================
        #
        # Reference/PDF workflow:
        # - Missing baseline labs can keep the eligibility position Amber/Pending.
        # - Billing / Therapy Plan creation is still allowed after the other
        #   completed gates (prescription + consent).
        # - Baseline labs remain stored in the GLP Assessment child table.
        # - A separate execution/package-activation gate can enforce labs before
        #   dose 1; Billing itself must not fail because child lab rows are Pending.
        #
        # Therefore action_ready intentionally does NOT throw when Baseline Labs
        # contain Pending/Awaited rows.
        # ============================================================

        doc.ready_for_billing = 1
        doc.billing_opened_on = (
            now_value()
        )
        doc.assessment_status = (
            "Ready for Billing"
        )
        doc.current_step = 6
        doc.last_saved_step = 6

        doc.save(
            ignore_permissions=True
        )

        frappe.db.commit()

        return {
            "success": True,
            "server_version": SERVER_VERSION,
            "patient": doc.patient,
            "patient_name": doc.patient_name,
            "branch": doc.branch,
            "source_lead": doc.source_lead,
            "assessment": doc.as_dict()
        }


    # ================================================================
    # ROUTER
    # ================================================================

    action = clean(
        frappe.form_dict.get("action")
        or "start"
    ).lower()

    payload = parse_payload()

    if action == "start":
        result = action_start(payload)

    elif action == "start_existing_patient":
        result = action_start_existing_patient(payload)

    elif action == "get":
        result = action_get(payload)

    elif action == "save_step":
        result = action_save_step(payload)

    elif action == "ready":
        result = action_ready(payload)

    else:
        frappe.throw(
            "Unsupported GLP Assessment action: "
            + action
        )

    frappe.response["message"] = result
