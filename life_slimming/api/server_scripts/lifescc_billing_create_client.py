"""lifescc.billing.create_client

Original API: lifescc.billing.create_client
Source modified: 2026-09-03 19:56:06.256219
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
    # LIFE BILLING — CREATE CLIENT
    # API Method : lifescc.billing.create_client
    # Script Type: API
    # Allow Guest: No
    #
    # Accepts Healthcare Practitioner ID from the Billing webpage.
    # Also supports an Employee ID and converts it to a practitioner.
    # ================================================================

    args = frappe.form_dict


    # ------------------------------------------------
    # INPUT VALUES
    # ------------------------------------------------

    patient_name = str(args.get("patient_name") or "").strip()
    mobile = str(args.get("mobile") or "").strip()
    sex = str(args.get("sex") or "").strip()
    dob = args.get("dob") or None
    branch = str(args.get("branch") or "").strip()
    media = str(args.get("media") or "InHouse").strip()

    visited_for = str(args.get("visited_for") or "").strip()
    consultation_value = str(
        args.get("consultation_employee") or ""
    ).strip()

    final_decision = str(
        args.get("final_decision") or ""
    ).strip()

    treatment_category = str(
        args.get("treatment_category") or ""
    ).strip()

    pd_form_number = str(
        args.get("pd_form_number") or ""
    ).strip()

    pd_form_file = str(
        args.get("pd_form_file") or ""
    ).strip()

    lead_name = str(
        args.get("lead") or ""
    ).strip()


    # ------------------------------------------------
    # MOBILE NORMALIZATION
    # ------------------------------------------------

    mobile_digits = ""

    for character in mobile:
        if character.isdigit():
            mobile_digits += character

    if len(mobile_digits) == 12 and mobile_digits[:2] == "91":
        mobile_digits = mobile_digits[2:]

    elif len(mobile_digits) == 11 and mobile_digits[:1] == "0":
        mobile_digits = mobile_digits[1:]

    mobile = mobile_digits


    # ------------------------------------------------
    # RESPONSE HELPERS
    # ------------------------------------------------

    def fail(message):
        frappe.response["message"] = {
            "error": message
        }


    def success(data):
        frappe.response["message"] = data


    # ------------------------------------------------
    # BASIC VALIDATION
    # ------------------------------------------------

    validation_error = ""

    if not patient_name:
        validation_error = "Client Name is required."

    elif len(patient_name) < 2:
        validation_error = (
            "Client Name must contain at least two characters."
        )

    elif not mobile:
        validation_error = "Mobile Number is required."

    elif not (
        mobile.isdigit()
        and len(mobile) == 10
        and mobile[0] in ("6", "7", "8", "9")
    ):
        validation_error = (
            "Enter a valid 10-digit Indian mobile number "
            "starting with 6, 7, 8 or 9."
        )

    elif not sex:
        validation_error = "Gender is required."

    elif not branch:
        validation_error = "Branch is required."

    elif not consultation_value:
        validation_error = "Consultation Employee is required."

    elif not visited_for:
        validation_error = "Visited For is required."

    elif not final_decision:
        validation_error = "Booked / Not-Booked is required."

    elif not treatment_category:
        validation_error = "Treatment Category is required."

    elif not pd_form_number:
        validation_error = "PD Form Number is required."

    elif not pd_form_file:
        validation_error = "PD Form attachment is required."

    otp_proof_key = "client_otp_verified::" + frappe.session.user + "::" + mobile
    if not validation_error and not frappe.cache().get_value(otp_proof_key):
        validation_error = "Verify this mobile number before registering."


    if validation_error:
        fail(validation_error)

    else:

        # ------------------------------------------------
        # DUPLICATE MOBILE CHECK
        # ------------------------------------------------

        existing_patient = frappe.db.get_value(
            "Patient",
            {
                "mobile": mobile
            },
            [
                "name",
                "patient_name"
            ],
            as_dict=True
        )

        if existing_patient:

            existing_name = (
                existing_patient.patient_name
                or existing_patient.name
            )

            success({
                "error": (
                    "Mobile number is already registered to "
                    + existing_name
                ),
                "name": existing_patient.name,
                "patient_name": existing_name,
                "duplicate": 1
            })

        else:

            # ------------------------------------------------
            # CONSULTATION PRACTITIONER RESOLUTION
            # ------------------------------------------------
            #
            # The Billing dropdown currently sends:
            # HLC-PRAC-YYYY-XXXXX
            #
            # Patient.custom_employee_id links to:
            # Healthcare Practitioner
            #
            # Therefore, do not validate the practitioner ID
            # directly against Employee.
            # ------------------------------------------------

            practitioner_id = ""
            linked_employee = ""

            # Billing supplied a Healthcare Practitioner ID.
            if frappe.db.exists(
                "Healthcare Practitioner",
                consultation_value
            ):
                practitioner_id = consultation_value

                linked_employee = (
                    frappe.db.get_value(
                        "Healthcare Practitioner",
                        practitioner_id,
                        "employee"
                    )
                    or ""
                )

            # Support an Employee ID if another page sends one.
            elif frappe.db.exists(
                "Employee",
                consultation_value
            ):
                linked_employee = consultation_value

                practitioner_id = (
                    frappe.db.get_value(
                        "Healthcare Practitioner",
                        {
                            "employee": consultation_value
                        },
                        "name"
                    )
                    or ""
                )

            if not practitioner_id:
                fail(
                    "Consultation Employee "
                    + consultation_value
                    + " was not found as an active "
                    + "Healthcare Practitioner."
                )

            else:

                practitioner_status = (
                    frappe.db.get_value(
                        "Healthcare Practitioner",
                        practitioner_id,
                        "status"
                    )
                    or ""
                )

                if practitioner_status != "Active":
                    fail(
                        "Selected Consultation Employee is disabled: "
                        + practitioner_id
                    )

                else:

                    # ------------------------------------------------
                    # BRANCH VALIDATION
                    # ------------------------------------------------

                    if not frappe.db.exists(
                        "Branch",
                        branch
                    ):
                        fail(
                            "Branch was not found: "
                            + branch
                        )

                    else:

                        # ------------------------------------------------
                        # GENDER VALIDATION
                        # ------------------------------------------------

                        if not frappe.db.exists(
                            "Gender",
                            sex
                        ):
                            fail(
                                "Gender was not found: "
                                + sex
                            )

                        else:

                            # ------------------------------------------------
                            # MEDIA / LEAD SOURCE RESOLUTION
                            # ------------------------------------------------

                            client_media = media

                            valid_lead = False

                            if lead_name and frappe.db.exists(
                                "Lead",
                                lead_name
                            ):
                                valid_lead = True

                                if frappe.db.exists(
                                    "Lead Source",
                                    "Call Center"
                                ):
                                    client_media = "Call Center"

                            if (
                                client_media
                                and not frappe.db.exists(
                                    "Lead Source",
                                    client_media
                                )
                            ):
                                if frappe.db.exists(
                                    "Lead Source",
                                    "InHouse"
                                ):
                                    client_media = "InHouse"

                                else:
                                    client_media = (
                                        frappe.db.get_value(
                                            "Lead Source",
                                            {},
                                            "name"
                                        )
                                        or ""
                                    )

                            # ------------------------------------------------
                            # CREATE PATIENT
                            # ------------------------------------------------

                            try:
                                patient = frappe.new_doc(
                                    "Patient"
                                )

                                patient.first_name = patient_name
                                patient.patient_name = patient_name
                                patient.mobile = mobile
                                patient.sex = sex
                                patient.status = "Active"

                                if dob:
                                    patient.dob = dob

                                # Branch fields
                                patient.custom_branch = branch
                                patient.branch_name = branch

                                # Lead source
                                if client_media:
                                    patient.custom_media = (
                                        client_media
                                    )

                                # Consultation details
                                patient.custom_client_visited_for_ = (
                                    visited_for
                                )

                                # IMPORTANT:
                                # This field links to Healthcare Practitioner.
                                patient.custom_employee_id = (
                                    practitioner_id
                                )

                                patient.custom_final_decision = (
                                    final_decision
                                )

                                patient.custom_treatment_category = (
                                    treatment_category
                                )

                                # PD Form Number
                                patient.custom_pd_form_number = (
                                    pd_form_number
                                )

                                # OTP was verified in the Billing webpage
                                # before this API was called.
                                if frappe.get_meta(
                                    "Patient"
                                ).has_field(
                                    "custom_otp_verified"
                                ):
                                    patient.custom_otp_verified = 1

                                # Link originating Lead
                                if valid_lead:
                                    patient.custom_lead = lead_name

                                # PD Form attachment child row
                                patient.append(
                                    "custom_pd_form",
                                    {
                                        "pd_form": pd_form_file
                                    }
                                )

                                patient.insert(
                                    ignore_permissions=False
                                )

                                frappe.db.commit()

                                frappe.cache().delete_value(otp_proof_key)

                                success({
                                    "name": patient.name,
                                    "patient_name": (
                                        patient.patient_name
                                    ),
                                    "mobile": patient.mobile,
                                    "branch": branch,
                                    "consultation_practitioner": (
                                        practitioner_id
                                    ),
                                    "consultation_employee": (
                                        linked_employee
                                    ),
                                    "pd_form_number": (
                                        pd_form_number
                                    ),
                                    "otp_verified": 1,
                                    "status": "success"
                                })

                            except Exception as error:
                                frappe.db.rollback()

                                fail(
                                    "Client registration failed: "
                                    + str(error)
                                )
