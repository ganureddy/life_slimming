"""Client Appointment status update

Original API: life_ops_update_appointment_status
Source modified: 2026-07-20 19:47:26.614626
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
    # ============================================================
    # LIFE OPS — SAFE AND REPEAT-PROTECTED APPOINTMENT RE-SCHEDULE
    #
    # API Method:
    # life_ops_update_appointment_status
    #
    # IMPORTANT:
    # Scheduler/report display call_back_status.
    # Main Patient Appointment.status is not changed here.
    # ============================================================


    appointment_name = str(
        frappe.form_dict.get("appointment_name") or ""
    ).strip()

    new_status = str(
        frappe.form_dict.get("new_status") or
        frappe.form_dict.get("status") or
        ""
    ).strip()

    new_appointment_date_text = str(
        frappe.form_dict.get("new_appointment_date") or ""
    ).strip()

    new_appointment_time_text = str(
        frappe.form_dict.get("new_appointment_time") or ""
    ).strip()


    allowed_statuses = [
        "Scheduled",
        "Re-Confirm",
        "Re-Scheduled",
        "Not Answering",
        "Closed",
        "Cancel",
    ]


    # ------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------

    if not appointment_name:
        frappe.throw("Appointment ID is required.")

    if new_status not in allowed_statuses:
        frappe.throw("Invalid appointment status.")

    if not frappe.db.exists(
        "Patient Appointment",
        appointment_name
    ):
        frappe.throw(
            "Patient Appointment was not found: " +
            appointment_name
        )


    old_appointment = frappe.get_doc(
        "Patient Appointment",
        appointment_name
    )


    if not old_appointment.has_permission("write"):
        frappe.throw(
            "You do not have permission to update this appointment."
        )


    normalized_status = (
        new_status
        .lower()
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )

    is_reschedule = normalized_status == "rescheduled"


    result = {
        "ok": True,
        "action": "",
        "old_appointment": appointment_name,
        "old_status": new_status,
        "new_appointment": "",
        "new_status": "",
        "appointment_date": "",
        "appointment_time": "",
        "new_appointment_date": "",
        "new_appointment_time": "",
    }


    # ============================================================
    # NORMAL CALLBACK STATUS UPDATE
    # ============================================================

    if not is_reschedule:

        frappe.db.set_value(
            "Patient Appointment",
            appointment_name,
            "call_back_status",
            new_status,
            update_modified=True
        )

        result["action"] = "status_updated"


    # ============================================================
    # RE-SCHEDULE WORKFLOW
    # ============================================================

    else:

        if (
            not new_appointment_date_text or
            not new_appointment_time_text
        ):
            frappe.throw(
                "Select the new appointment date and time."
            )


        new_appointment_date = frappe.utils.getdate(
            new_appointment_date_text
        )

        new_appointment_time = frappe.utils.get_time(
            new_appointment_time_text
        )


        today_date = frappe.utils.getdate(
            frappe.utils.today()
        )

        if new_appointment_date < today_date:
            frappe.throw(
                "The new appointment date cannot be in the past."
            )


        old_appointment_date = frappe.utils.getdate(
            old_appointment.get("appointment_date")
        )

        old_appointment_time = frappe.utils.get_time(
            old_appointment.get("appointment_time")
        )


        old_time_text = str(
            old_appointment_time or ""
        )[:8]

        new_time_text = str(
            new_appointment_time or ""
        )[:8]


        if (
            old_appointment_date == new_appointment_date and
            old_time_text == new_time_text
        ):
            frappe.throw(
                "Change the date or time before creating the "
                "re-scheduled appointment."
            )


        appointment_patient = str(
            old_appointment.get("patient") or ""
        ).strip()

        appointment_branch = str(
            old_appointment.get("branch") or ""
        ).strip()

        appointment_room = str(
            old_appointment.get("service_room") or ""
        ).strip()


        # --------------------------------------------------------
        # Check whether the new appointment was already created.
        #
        # This fixes the current situation:
        # the first click created tomorrow's appointment, but the
        # browser failed while displaying the success message.
        # --------------------------------------------------------

        existing_filters = [
            [
                "Patient Appointment",
                "name",
                "!=",
                appointment_name,
            ],
            [
                "Patient Appointment",
                "appointment_date",
                "=",
                new_appointment_date,
            ],
            [
                "Patient Appointment",
                "appointment_time",
                "=",
                new_appointment_time,
            ],
            [
                "Patient Appointment",
                "docstatus",
                "<",
                2,
            ],
        ]


        if appointment_patient:
            existing_filters.append(
                [
                    "Patient Appointment",
                    "patient",
                    "=",
                    appointment_patient,
                ]
            )


        if appointment_branch:
            existing_filters.append(
                [
                    "Patient Appointment",
                    "branch",
                    "=",
                    appointment_branch,
                ]
            )


        existing_appointments = frappe.get_all(
            "Patient Appointment",
            filters=existing_filters,
            fields=[
                "name",
                "call_back_status",
                "appointment_date",
                "appointment_time",
            ],
            order_by="creation desc",
            limit_page_length=10
        )


        existing_new_appointment = ""

        if existing_appointments:
            existing_new_appointment = str(
                existing_appointments[0].get("name") or ""
            ).strip()


        # --------------------------------------------------------
        # Existing tomorrow appointment found:
        # repair statuses without creating another appointment.
        # --------------------------------------------------------

        if existing_new_appointment:

            frappe.db.set_value(
                "Patient Appointment",
                appointment_name,
                "call_back_status",
                "Re-Scheduled",
                update_modified=True
            )

            frappe.db.set_value(
                "Patient Appointment",
                existing_new_appointment,
                "call_back_status",
                "Scheduled",
                update_modified=True
            )

            result["action"] = (
                "existing_rescheduled_appointment_repaired"
            )

            result["old_status"] = "Re-Scheduled"
            result["new_appointment"] = (
                existing_new_appointment
            )
            result["new_status"] = "Scheduled"

            result["appointment_date"] = str(
                new_appointment_date
            )

            result["appointment_time"] = str(
                new_appointment_time
            )

            result["new_appointment_date"] = str(
                new_appointment_date
            )

            result["new_appointment_time"] = str(
                new_appointment_time
            )


        # --------------------------------------------------------
        # No existing appointment found: create a new appointment.
        # --------------------------------------------------------

        else:

            # Check whether the room is occupied by another client.
            room_conflict = ""

            if appointment_room:

                room_rows = frappe.get_all(
                    "Patient Appointment",
                    filters=[
                        [
                            "Patient Appointment",
                            "name",
                            "!=",
                            appointment_name,
                        ],
                        [
                            "Patient Appointment",
                            "appointment_date",
                            "=",
                            new_appointment_date,
                        ],
                        [
                            "Patient Appointment",
                            "appointment_time",
                            "=",
                            new_appointment_time,
                        ],
                        [
                            "Patient Appointment",
                            "service_room",
                            "=",
                            appointment_room,
                        ],
                        [
                            "Patient Appointment",
                            "docstatus",
                            "<",
                            2,
                        ],
                    ],
                    fields=[
                        "name",
                        "status",
                        "call_back_status",
                    ],
                    limit_page_length=50
                )


                for room_row in room_rows:

                    room_main_status = str(
                        room_row.get("status") or ""
                    ).strip().lower()

                    room_callback_status = str(
                        room_row.get("call_back_status") or ""
                    ).strip().lower()

                    is_inactive = (
                        "cancel" in room_main_status or
                        room_main_status == "no show" or
                        "cancel" in room_callback_status or
                        room_callback_status in [
                            "re-scheduled",
                            "rescheduled",
                            "re scheduled",
                        ]
                    )

                    if not is_inactive:
                        room_conflict = str(
                            room_row.get("name") or ""
                        ).strip()
                        break


            if room_conflict:
                frappe.throw(
                    "The selected room is already booked on " +
                    str(new_appointment_date) +
                    " at " +
                    str(new_appointment_time) +
                    " in appointment " +
                    room_conflict +
                    ". Choose another date or time."
                )


            new_appointment_data = {
                "doctype": "Patient Appointment",
                "docstatus": 0,

                "naming_series": (
                    old_appointment.get("naming_series") or
                    "HLC-APP-.YYYY.-"
                ),

                "company": (
                    old_appointment.get("company") or
                    "Life Slimming And Cosmetic Pvt Ltd"
                ),

                "appointment_for": (
                    old_appointment.get("appointment_for") or
                    "Practitioner"
                ),

                "appointment_type": (
                    old_appointment.get("appointment_type") or
                    "Session"
                ),

                "patient": (
                    old_appointment.get("patient") or ""
                ),

                "patient_name": (
                    old_appointment.get("patient_name") or
                    old_appointment.get("patient") or
                    ""
                ),

                "patient_sex": (
                    old_appointment.get("patient_sex") or ""
                ),

                "custom_client_mobile_no": (
                    old_appointment.get(
                        "custom_client_mobile_no"
                    ) or ""
                ),

                "branch": appointment_branch,
                "service_room": appointment_room,

                "service_unit": (
                    old_appointment.get("service_unit") or ""
                ),

                "therapy_plan_1": (
                    old_appointment.get("therapy_plan_1") or ""
                ),

                "therapy_type1": (
                    old_appointment.get("therapy_type1") or ""
                ),

                "concern": (
                    old_appointment.get("concern") or
                    old_appointment.get("therapy_type1") or
                    ""
                ),

                "appointment_date": new_appointment_date,
                "appointment_time": new_appointment_time,

                "duration": (
                    old_appointment.get("duration") or 30
                ),

                # This is the status displayed in the dashboard.
                "call_back_status": "Scheduled",

                "add_video_conferencing": (
                    old_appointment.get(
                        "add_video_conferencing"
                    ) or 0
                ),

                "invoiced": 0,
                "appointment_based_on_check_in": 0,
                "reminded": 0,
            }


            if (
                old_appointment.meta.has_field(
                    "practitioner"
                ) and
                old_appointment.get("practitioner")
            ):
                new_appointment_data["practitioner"] = (
                    old_appointment.get("practitioner")
                )


            if (
                old_appointment.meta.has_field(
                    "department"
                ) and
                old_appointment.get("department")
            ):
                new_appointment_data["department"] = (
                    old_appointment.get("department")
                )


            if (
                old_appointment.meta.has_field(
                    "medical_department"
                ) and
                old_appointment.get("medical_department")
            ):
                new_appointment_data[
                    "medical_department"
                ] = old_appointment.get(
                    "medical_department"
                )


            if old_appointment.meta.has_field("notes"):

                old_notes = str(
                    old_appointment.get("notes") or ""
                ).strip()

                new_notes = (
                    "Re-scheduled from " +
                    appointment_name +
                    "."
                )

                if old_notes:
                    new_notes = (
                        new_notes +
                        "\n" +
                        old_notes
                    )

                new_appointment_data["notes"] = new_notes


            new_appointment = frappe.get_doc(
                new_appointment_data
            )

            new_appointment.insert()


            # Update only call_back_status on the old appointment.
            # Do not change the main Patient Appointment.status.
            frappe.db.set_value(
                "Patient Appointment",
                appointment_name,
                "call_back_status",
                "Re-Scheduled",
                update_modified=True
            )


            result["action"] = (
                "new_rescheduled_appointment_created"
            )

            result["old_status"] = "Re-Scheduled"
            result["new_appointment"] = (
                new_appointment.name
            )
            result["new_status"] = "Scheduled"

            result["appointment_date"] = str(
                new_appointment.appointment_date or
                new_appointment_date
            )

            result["appointment_time"] = str(
                new_appointment.appointment_time or
                new_appointment_time
            )

            result["new_appointment_date"] = (
                result["appointment_date"]
            )

            result["new_appointment_time"] = (
                result["appointment_time"]
            )


    frappe.response["message"] = result
