"""cc_walkin_update

Original API: cc_walkin_update
Source modified: 2026-09-13 12:17:18.756149
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
    # # # lead = frappe.form_dict.get("lead")
    # # # status = frappe.form_dict.get("status")
    # # # valid = ["Not Booked","Booked","Cancelled","Not Visited","Visited Not Booked","Visited Booked"]
    # # # if not lead or status not in valid:
    # # #     frappe.throw("Invalid lead or status")
    # # # if not frappe.db.exists("Lead", lead):
    # # #     frappe.throw("Lead not found")
    # # # frappe.db.set_value("Lead", lead, "custom_appointment_status", status)





    # # # Server Script  |  Script Type: API  |  API Method: cc_walkin_update
    # # # v3 - mandatory EMPLOYEE attribution on every status update.
    # # #
    # # # CHANGES vs v2
    # # #  1. Requires an "employee" param on every call and records who updated
    # # #     the appointment (Employee link + name + timestamp + login user).
    # # #     Without this there was no way to tell which branch staff member
    # # #     marked an outcome.
    # # #  2. The employee is validated to be ACTIVE and to actually belong to the
    # # #     same branch as the Lead - so one branch cannot log an update against
    # # #     another branch's staff.
    # # #  3. Reason still mandatory for the negative outcomes.
    # # #
    # # # REQUIRES: run console_create_lead_fields.py once first, to create
    # # #   custom_status_updated_by_employee / _by_name / _on / _by_user on Lead.
    # # #
    # # # safe_exec safe: no f-strings, no imports, no tuple unpacking.

    # # lead = frappe.form_dict.get("lead")
    # # status = frappe.form_dict.get("status")
    # # remarks = frappe.form_dict.get("remarks") or ""
    # # remarks = remarks.strip()
    # # employee = frappe.form_dict.get("employee") or ""
    # # employee = employee.strip()

    # # valid = ["Not Booked", "Booked", "Cancelled", "Not Visited",
    # #          "Visited Not Booked", "Visited Booked"]

    # # if not lead or status not in valid:
    # #     frappe.throw("Invalid lead or status")

    # # if not frappe.db.exists("Lead", lead):
    # #     frappe.throw("Lead not found")

    # # # ---- Employee is mandatory -------------------------------------------
    # # if not employee:
    # #     frappe.throw("Please select the employee updating this appointment")

    # # emp = frappe.db.get_value("Employee", employee,
    # #     ["name", "employee_name", "status", "branch"], as_dict=True)

    # # if not emp:
    # #     frappe.throw("Employee not found")

    # # if emp.get("status") != "Active":
    # #     frappe.throw("Employee " + str(emp.get("employee_name")) + " is not Active")

    # # # ---- Employee must belong to the Lead's branch -----------------------
    # # lead_branch = frappe.db.get_value("Lead", lead, "branch")
    # # lead_assign = frappe.db.get_value("Lead", lead, "lead_assign_to_branch")
    # # emp_branch = emp.get("branch")

    # # allowed_branches = []
    # # if lead_branch:
    # #     allowed_branches.append(lead_branch)
    # # if lead_assign:
    # #     allowed_branches.append(lead_assign)

    # # if allowed_branches and emp_branch not in allowed_branches:
    # #     frappe.throw("Employee " + str(emp.get("employee_name"))
    # #         + " belongs to " + str(emp_branch)
    # #         + " and cannot update an appointment for "
    # #         + str(allowed_branches[0]))

    # # # ---- Reason mandatory for negative outcomes --------------------------
    # # needs_reason = ["Visited Not Booked", "Not Visited", "Cancelled"]
    # # if status in needs_reason and not remarks:
    # #     frappe.throw("A reason is required for " + status)

    # # # ---- Write ------------------------------------------------------------
    # # frappe.db.set_value("Lead", lead, "custom_appointment_status", status)
    # # frappe.db.set_value("Lead", lead, "custom_status_updated_by_employee", emp.get("name"))
    # # frappe.db.set_value("Lead", lead, "custom_status_updated_by_name", emp.get("employee_name"))
    # # frappe.db.set_value("Lead", lead, "custom_status_updated_on", frappe.utils.now())
    # # frappe.db.set_value("Lead", lead, "custom_status_updated_by_user", frappe.session.user)

    # # if status == "Visited Booked":
    # #     frappe.db.set_value("Lead", lead, "status", "Converted")
    # #     frappe.db.set_value("Lead", lead, "custom_remarks", "")
    # # elif status in needs_reason:
    # #     frappe.db.set_value("Lead", lead, "custom_remarks", remarks)

    # # frappe.response["message"] = {
    # #     "ok": 1,
    # #     "lead": lead,
    # #     "status": status,
    # #     "remarks": remarks,
    # #     "employee": emp.get("name"),
    # #     "employee_name": emp.get("employee_name"),
    # #     "updated_on": frappe.utils.now(),
    # # }
















    # # Server Script  |  Script Type: API  |  API Method: cc_walkin_update
    # # v4 - adds the interim "Visited" status.
    # #
    # # CHANGES vs v3
    # #  1. "Visited" is now an accepted status - the client turned up but the
    # #     booking outcome is not yet decided. No reason is required for it.
    # #  2. Status can be CHANGED after the fact (e.g. Visited -> Visited Booked
    # #     once the consultation finishes). Every change is re-stamped with the
    # #     employee who made it, so the audit trail follows the latest edit.
    # #  3. Returns the previous status so the UI can show what changed.
    # #
    # # CHANGES in v3
    # #  1. Requires an "employee" param on every call and records who updated
    # #     the appointment (Employee link + name + timestamp + login user).
    # #     Without this there was no way to tell which branch staff member
    # #     marked an outcome.
    # #  2. The employee is validated to be ACTIVE and to actually belong to the
    # #     same branch as the Lead - so one branch cannot log an update against
    # #     another branch's staff.
    # #  3. Reason still mandatory for the negative outcomes.
    # #
    # # REQUIRES: run console_create_lead_fields.py once first, to create
    # #   custom_status_updated_by_employee / _by_name / _on / _by_user on Lead.
    # #
    # # safe_exec safe: no f-strings, no imports, no tuple unpacking.

    # #version 2 by narendhar

    # # lead = frappe.form_dict.get("lead")
    # # status = frappe.form_dict.get("status")
    # # remarks = frappe.form_dict.get("remarks") or ""
    # # remarks = remarks.strip()
    # # employee = frappe.form_dict.get("employee") or ""
    # # employee = employee.strip()

    # # valid = ["Not Booked", "Booked", "Visited", "Cancelled", "Not Visited",
    # #          "Visited Not Booked", "Visited Booked"]

    # # if not lead or status not in valid:
    # #     frappe.throw("Invalid lead or status")

    # # if not frappe.db.exists("Lead", lead):
    # #     frappe.throw("Lead not found")

    # # # ---- Employee is mandatory -------------------------------------------
    # # if not employee:
    # #     frappe.throw("Please select the employee updating this appointment")

    # # emp = frappe.db.get_value("Employee", employee,
    # #     ["name", "employee_name", "status", "branch"], as_dict=True)

    # # if not emp:
    # #     frappe.throw("Employee not found")

    # # if emp.get("status") != "Active":
    # #     frappe.throw("Employee " + str(emp.get("employee_name")) + " is not Active")

    # # # ---- Employee must belong to the Lead's branch -----------------------
    # # lead_branch = frappe.db.get_value("Lead", lead, "branch")
    # # lead_assign = frappe.db.get_value("Lead", lead, "lead_assign_to_branch")
    # # emp_branch = emp.get("branch")

    # # allowed_branches = []
    # # if lead_branch:
    # #     allowed_branches.append(lead_branch)
    # # if lead_assign:
    # #     allowed_branches.append(lead_assign)

    # # if allowed_branches and emp_branch not in allowed_branches:
    # #     frappe.throw("Employee " + str(emp.get("employee_name"))
    # #         + " belongs to " + str(emp_branch)
    # #         + " and cannot update an appointment for "
    # #         + str(allowed_branches[0]))

    # # # ---- Reason mandatory for negative outcomes --------------------------
    # # needs_reason = ["Visited Not Booked", "Not Visited", "Cancelled"]
    # # if status in needs_reason and not remarks:
    # #     frappe.throw("A reason is required for " + status)

    # # # ---- Write ------------------------------------------------------------
    # # # Previous status is captured so the caller can show what changed, and so
    # # # a correction (e.g. Visited -> Visited Booked) is fully traceable.
    # # prev_status = frappe.db.get_value("Lead", lead, "custom_appointment_status") or ""

    # # frappe.db.set_value("Lead", lead, "custom_appointment_status", status)
    # # frappe.db.set_value("Lead", lead, "custom_status_updated_by_employee", emp.get("name"))
    # # frappe.db.set_value("Lead", lead, "custom_status_updated_by_name", emp.get("employee_name"))
    # # frappe.db.set_value("Lead", lead, "custom_status_updated_on", frappe.utils.now())
    # # frappe.db.set_value("Lead", lead, "custom_status_updated_by_user", frappe.session.user)

    # # if status == "Visited Booked":
    # #     frappe.db.set_value("Lead", lead, "status", "Converted")
    # #     frappe.db.set_value("Lead", lead, "custom_remarks", "")
    # # elif status in needs_reason:
    # #     frappe.db.set_value("Lead", lead, "custom_remarks", remarks)
    # # elif status in ["Visited", "Booked", "Not Booked"]:
    # #     # Correcting back to a neutral/interim state must not leave a stale
    # #     # "did not book" reason attached to the Lead.
    # #     if prev_status in needs_reason:
    # #         frappe.db.set_value("Lead", lead, "custom_remarks", "")

    # # frappe.response["message"] = {
    # #     "ok": 1,
    # #     "lead": lead,
    # #     "status": status,
    # #     "previous_status": prev_status,
    # #     "remarks": remarks,
    # #     "employee": emp.get("name"),
    # #     "employee_name": emp.get("employee_name"),
    # #     "updated_on": frappe.utils.now(),
    # # }

    # # ============================================================
    # # CC WALK-IN STATUS UPDATE
    # #
    # # RULE:
    # # If current status is "Visited", it can be changed to
    # # "Cancelled" only within 1 hour from the time Visited was set.
    # #
    # # Existing timestamp field used:
    # #   custom_status_updated_on
    # #
    # # IMPORTANT:
    # # Re-selecting "Visited" does NOT restart the 1-hour timer.
    # # ============================================================

    # # ============================================================
    # # CC WALK-IN UPDATE
    # #
    # # RULE:
    # # Once an appointment enters a VISITED state:
    # #
    # #   Visited
    # #   Visited Not Booked
    # #   Visited Booked
    # #
    # # it can be changed to Cancelled ONLY within 1 hour.
    # #
    # # Moving between visited statuses does NOT restart the timer.
    # #
    # # Existing field used as timer:
    # #   custom_status_updated_on
    # # ============================================================


    # # ------------------------------------------------------------
    # # REQUEST DATA
    # # ------------------------------------------------------------

    # lead = frappe.form_dict.get("lead")
    # status = frappe.form_dict.get("status")

    # remarks = frappe.form_dict.get("remarks") or ""
    # remarks = remarks.strip()

    # employee = frappe.form_dict.get("employee") or ""
    # employee = employee.strip()


    # # ------------------------------------------------------------
    # # VALID STATUSES
    # # ------------------------------------------------------------

    # valid = [
    #     "Not Booked",
    #     "Booked",
    #     "Visited",
    #     "Cancelled",
    #     "Not Visited",
    #     "Visited Not Booked",
    #     "Visited Booked"
    # ]


    # VISITED_STATUSES = [
    #     "Visited",
    #     "Visited Not Booked",
    #     "Visited Booked"
    # ]


    # NEGATIVE_STATUSES = [
    #     "Visited Not Booked",
    #     "Not Visited",
    #     "Cancelled"
    # ]


    # # ------------------------------------------------------------
    # # BASIC VALIDATION
    # # ------------------------------------------------------------

    # if not lead:
    #     frappe.throw("Lead is required")

    # if status not in valid:
    #     frappe.throw("Invalid appointment status")

    # if not frappe.db.exists("Lead", lead):
    #     frappe.throw("Lead not found")


    # # ============================================================
    # # EMPLOYEE VALIDATION
    # # ============================================================

    # if not employee:
    #     frappe.throw(
    #         "Please select the employee updating this appointment"
    #     )


    # emp = frappe.db.get_value(
    #     "Employee",
    #     employee,
    #     [
    #         "name",
    #         "employee_name",
    #         "status",
    #         "branch"
    #     ],
    #     as_dict=True
    # )


    # if not emp:
    #     frappe.throw("Employee not found")


    # if emp.get("status") != "Active":
    #     frappe.throw(
    #         "Employee "
    #         + str(emp.get("employee_name") or employee)
    #         + " is not Active"
    #     )


    # # ============================================================
    # # LOAD CURRENT LEAD DATA BEFORE CHANGING ANYTHING
    # # ============================================================

    # lead_data = frappe.db.get_value(
    #     "Lead",
    #     lead,
    #     [
    #         "branch",
    #         "lead_assign_to_branch",
    #         "custom_appointment_status",
    #         "custom_status_updated_on",
    #         "custom_remarks"
    #     ],
    #     as_dict=True
    # )


    # if not lead_data:
    #     frappe.throw("Lead not found")


    # lead_branch = lead_data.get("branch")
    # lead_assign = lead_data.get("lead_assign_to_branch")

    # prev_status = (
    #     lead_data.get("custom_appointment_status") or ""
    # )

    # previous_updated_on = (
    #     lead_data.get("custom_status_updated_on")
    # )


    # # ============================================================
    # # EMPLOYEE MUST BELONG TO LEAD BRANCH
    # # ============================================================

    # emp_branch = emp.get("branch")

    # allowed_branches = []

    # if lead_branch:
    #     allowed_branches.append(lead_branch)

    # if lead_assign and lead_assign not in allowed_branches:
    #     allowed_branches.append(lead_assign)


    # if allowed_branches and emp_branch not in allowed_branches:

    #     frappe.throw(
    #         "Employee "
    #         + str(emp.get("employee_name"))
    #         + " belongs to "
    #         + str(emp_branch)
    #         + " and cannot update an appointment for "
    #         + str(allowed_branches[0])
    #     )


    # # ============================================================
    # # REASON REQUIRED FOR NEGATIVE OUTCOMES
    # # ============================================================

    # if status in NEGATIVE_STATUSES and not remarks:

    #     frappe.throw(
    #         "A reason is required for " + status
    #     )


    # # ============================================================
    # # CURRENT TIME
    # # ============================================================

    # now_dt = frappe.utils.now_datetime()
    # now_value = frappe.utils.now()


    # # ============================================================
    # # VISITED -> CANCELLED RULE
    # #
    # # IMPORTANT:
    # # This now applies to:
    # #
    # #   Visited              -> Cancelled
    # #   Visited Not Booked   -> Cancelled
    # #   Visited Booked       -> Cancelled
    # #
    # # ============================================================

    # if prev_status in VISITED_STATUSES and status == "Cancelled":

    #     if not previous_updated_on:

    #         frappe.throw(
    #             "Cancellation is not allowed. "
    #             "The time when this appointment was marked Visited "
    #             "is unavailable."
    #         )


    #     visited_time = frappe.utils.get_datetime(
    #         previous_updated_on
    #     )


    #     elapsed_seconds = (
    #         now_dt - visited_time
    #     ).total_seconds()


    #     # Bad/future timestamp
    #     if elapsed_seconds < 0:

    #         frappe.throw(
    #             "Invalid Visited status timestamp. "
    #             "Please contact the administrator."
    #         )


    #     # 60 minutes or more = BLOCK
    #     if elapsed_seconds >= 3600:

    #         elapsed_minutes = int(
    #             elapsed_seconds / 60
    #         )

    #         elapsed_hours = int(
    #             elapsed_seconds / 3600
    #         )


    #         if elapsed_hours >= 24:

    #             elapsed_days = int(
    #                 elapsed_seconds / 86400
    #             )

    #             frappe.throw(
    #                 "Cancellation time expired. "
    #                 "This client was marked as Visited "
    #                 + str(elapsed_days)
    #                 + " day(s) ago. "
    #                 "A visited appointment can be cancelled "
    #                 "only within 1 hour."
    #             )

    #         else:

    #             frappe.throw(
    #                 "Cancellation time expired. "
    #                 "This client was marked as Visited "
    #                 + str(elapsed_minutes)
    #                 + " minutes ago. "
    #                 "A visited appointment can be cancelled "
    #                 "only within 1 hour."
    #             )


    # # ============================================================
    # # TIMER PRESERVATION
    # # ============================================================

    # old_is_visited = (
    #     prev_status in VISITED_STATUSES
    # )

    # new_is_visited = (
    #     status in VISITED_STATUSES
    # )


    # # If already in a visited state and changing to another
    # # visited state, DO NOT restart the timer.
    # #
    # # Examples:
    # #
    # # Visited
    # #    -> Visited Not Booked
    # #
    # # Visited
    # #    -> Visited Booked
    # #
    # # Visited Not Booked
    # #    -> Visited
    # #
    # # The original Visited time remains unchanged.
    # #
    # preserve_visited_timer = (
    #     old_is_visited
    #     and new_is_visited
    # )


    # # Same status also must not restart Visited timer
    # same_status = (
    #     prev_status == status
    # )


    # # ============================================================
    # # WRITE APPOINTMENT STATUS
    # # ============================================================

    # if prev_status != status:

    #     frappe.db.set_value(
    #         "Lead",
    #         lead,
    #         "custom_appointment_status",
    #         status
    #     )


    # # ============================================================
    # # WRITE AUDIT EMPLOYEE
    # # ============================================================

    # frappe.db.set_value(
    #     "Lead",
    #     lead,
    #     "custom_status_updated_by_employee",
    #     emp.get("name")
    # )


    # frappe.db.set_value(
    #     "Lead",
    #     lead,
    #     "custom_status_updated_by_name",
    #     emp.get("employee_name")
    # )


    # frappe.db.set_value(
    #     "Lead",
    #     lead,
    #     "custom_status_updated_by_user",
    #     frappe.session.user
    # )


    # # ============================================================
    # # TIMESTAMP LOGIC
    # # ============================================================

    # effective_updated_on = previous_updated_on


    # # ------------------------------------------------------------
    # # CASE 1:
    # # Entering Visited for first time from non-visited status.
    # #
    # # Booked -> Visited
    # # Not Booked -> Visited
    # #
    # # Start the one-hour timer.
    # # ------------------------------------------------------------

    # if not old_is_visited and new_is_visited:

    #     frappe.db.set_value(
    #         "Lead",
    #         lead,
    #         "custom_status_updated_on",
    #         now_value
    #     )

    #     effective_updated_on = now_value


    # # ------------------------------------------------------------
    # # CASE 2:
    # # Already Visited and changing between Visited statuses.
    # #
    # # KEEP OLD TIME.
    # # ------------------------------------------------------------

    # elif old_is_visited and new_is_visited:

    #     effective_updated_on = previous_updated_on


    # # ------------------------------------------------------------
    # # CASE 3:
    # # Leaving visited family to another status.
    # #
    # # Example:
    # # Visited -> Cancelled
    # # Visited -> Not Visited
    # #
    # # Normal audit timestamp can become now.
    # # ------------------------------------------------------------

    # elif prev_status != status:

    #     frappe.db.set_value(
    #         "Lead",
    #         lead,
    #         "custom_status_updated_on",
    #         now_value
    #     )

    #     effective_updated_on = now_value


    # # ------------------------------------------------------------
    # # CASE 4:
    # # Same non-visited status updated again.
    # # Keep normal audit behavior.
    # # ------------------------------------------------------------

    # elif not new_is_visited:

    #     frappe.db.set_value(
    #         "Lead",
    #         lead,
    #         "custom_status_updated_on",
    #         now_value
    #     )

    #     effective_updated_on = now_value


    # # ============================================================
    # # STATUS-SPECIFIC BUSINESS LOGIC
    # # ============================================================

    # if status == "Visited Booked":

    #     frappe.db.set_value(
    #         "Lead",
    #         lead,
    #         "status",
    #         "Converted"
    #     )

    #     frappe.db.set_value(
    #         "Lead",
    #         lead,
    #         "custom_remarks",
    #         ""
    #     )


    # elif status in NEGATIVE_STATUSES:

    #     frappe.db.set_value(
    #         "Lead",
    #         lead,
    #         "custom_remarks",
    #         remarks
    #     )


    # elif status in [
    #     "Visited",
    #     "Booked",
    #     "Not Booked"
    # ]:

    #     # Clear stale negative remarks when corrected back
    #     # to normal/interim state.

    #     if prev_status in NEGATIVE_STATUSES:

    #         frappe.db.set_value(
    #             "Lead",
    #             lead,
    #             "custom_remarks",
    #             ""
    #         )


    # # ============================================================
    # # CALCULATE CURRENT CANCEL PERMISSION
    # # ============================================================

    # cancel_allowed = 0
    # cancel_remaining_seconds = 0
    # cancel_remaining_minutes = 0


    # if status in VISITED_STATUSES:

    #     timer_value = effective_updated_on

    #     if timer_value:

    #         timer_dt = frappe.utils.get_datetime(
    #             timer_value
    #         )

    #         elapsed = (
    #             now_dt - timer_dt
    #         ).total_seconds()


    #         if elapsed >= 0 and elapsed < 3600:

    #             cancel_allowed = 1

    #             cancel_remaining_seconds = int(
    #                 3600 - elapsed
    #             )

    #             cancel_remaining_minutes = int(
    #                 (cancel_remaining_seconds + 59) / 60
    #             )


    # # ============================================================
    # # RESPONSE
    # # ============================================================

    # frappe.response["message"] = {

    #     "ok": 1,

    #     "lead": lead,

    #     "status": status,

    #     "previous_status": prev_status,

    #     "remarks": remarks,

    #     "employee": emp.get("name"),

    #     "employee_name": emp.get("employee_name"),

    #     "updated_by_user": frappe.session.user,

    #     "updated_on": str(
    #         effective_updated_on or ""
    #     ),

    #     "cancel_allowed": cancel_allowed,

    #     "cancel_remaining_seconds": cancel_remaining_seconds,

    #     "cancel_remaining_minutes": cancel_remaining_minutes
    # }












    # ============================================================
    # Server Script: cc_walkin_update
    # Script Type: API
    # API Method: cc_walkin_update
    # Allow Guest: No
    #
    # Workflow:
    # 1. Booked/Not Booked -> Visited or Not Visited
    # 2. Visited -> Visited Booked or Visited Not Booked
    # 3. Only Visited Booked is permanently locked
    # 4. Visited Not Booked and Not Visited can be corrected
    # 5. Final visited decisions require Patient, PD number
    #    and 2-5 PD Form images
    # ============================================================


    # ------------------------------------------------------------
    # REQUEST VALUES
    # ------------------------------------------------------------

    lead = (frappe.form_dict.get("lead") or "").strip()
    status = (frappe.form_dict.get("status") or "").strip()
    remarks = (frappe.form_dict.get("remarks") or "").strip()
    employee = (frappe.form_dict.get("employee") or "").strip()


    valid_statuses = [
        "Visited",
        "Not Visited",
        "Visited Not Booked",
        "Visited Booked"
    ]

    negative_statuses = [
        "Not Visited",
        "Visited Not Booked"
    ]

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

    # ------------------------------------------------------------
    # BASIC VALIDATION
    # ------------------------------------------------------------

    if not lead:
        frappe.throw("Lead is required")


    if not frappe.db.exists("Lead", lead):
        frappe.throw("Lead not found")


    if status not in valid_statuses:
        frappe.throw("Invalid appointment status")


    if not employee:
        frappe.throw("Please select the Consultation Employee")


    if status in negative_statuses and not remarks:
        frappe.throw("A reason is required for " + status)


    # ------------------------------------------------------------
    # CONSULTATION EMPLOYEE VALIDATION
    # ------------------------------------------------------------

    emp = frappe.db.get_value(
        "Employee",
        employee,
        [
            "name",
            "employee_name",
            "status",
            "branch",
            "designation"
        ],
        as_dict=True
    )


    if not emp:
        frappe.throw("Consultation Employee not found")


    if emp.get("status") != "Active":
        frappe.throw("Please select an active Consultation Employee")


    if emp.get("designation") not in allowed_designations:
        frappe.throw(
            "Only Branch Manager, Center Manager, Assistant Center Manager, "
            "Area Manager, Area Manager Trainee or Doctor/Consultant "
            "can update this status"
        )


    # ------------------------------------------------------------
    # LEAD AND BRANCH VALIDATION
    # ------------------------------------------------------------

    old = frappe.db.get_value(
        "Lead",
        lead,
        [
            "branch",
            "lead_assign_to_branch",
            "custom_appointment_status",
            "custom_status_updated_on",
            "custom_remarks",
            "status"
        ],
        as_dict=True
    )


    if not old:
        frappe.throw("Lead details could not be loaded")


    lead_branch = (
        old.get("lead_assign_to_branch")
        or old.get("branch")
        or ""
    )


    if (
        lead_branch
        and emp.get("branch")
        and emp.get("branch") != lead_branch
    ):
        frappe.throw(
            "The Consultation Employee must belong to "
            + lead_branch
        )


    previous_status = (
        old.get("custom_appointment_status") or ""
    ).strip()


    now_value = frappe.utils.now()


    # ------------------------------------------------------------
    # STATUS WORKFLOW VALIDATION
    # ------------------------------------------------------------

    # Only Visited Booked is permanently locked.
    if previous_status == "Visited Booked":
        frappe.throw(
            "Visited Booked is locked and cannot be changed"
        )


    # After Visited, only the final booking decision is allowed.
    if previous_status == "Visited":
        if status not in [
            "Visited Booked",
            "Visited Not Booked"
        ]:
            frappe.throw(
                "After Visited, select only Visited Booked "
                "or Visited Not Booked"
            )


    # Initial or correctable statuses must first return to Visited.
    elif previous_status in [
        "",
        "Booked",
        "Not Booked",
        "Not Visited",
        "Visited Not Booked"
    ]:
        if status not in [
            "Visited",
            "Not Visited"
        ]:
            frappe.throw(
                "First update the client as Visited"
            )


    else:
        frappe.throw(
            "Invalid previous appointment status: "
            + previous_status
        )


    # ------------------------------------------------------------
    # PATIENT AND PD FORM VALIDATION
    # ------------------------------------------------------------

    patient = None
    patient_name = ""


    if status in [
        "Visited Booked",
        "Visited Not Booked"
    ]:
        patient = frappe.db.get_value(
            "Patient",
            {"custom_lead": lead},
            [
                "name",
                "custom_pd_form_number"
            ],
            as_dict=True
        )

        if not patient:
            frappe.throw(
                "Create the Client/Patient before selecting "
                + status
            )

        patient_name = patient.get("name") or ""

        pd_form_number = (
            patient.get("custom_pd_form_number") or ""
        ).strip()

        if not pd_form_number:
            frappe.throw(
                "PD Form Number is mandatory in the Client/Patient"
            )

        pd_files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Patient",
                "attached_to_name": patient_name
            },
            fields=[
                "file_url",
                "attached_to_field"
            ],
            order_by="creation asc",
            ignore_permissions=True,
            limit_page_length=0
        )

        pd_image_urls = []

        for pd_file in pd_files:
            attached_field = (
                pd_file.get("attached_to_field") or ""
            ).lower()

            file_url = pd_file.get("file_url") or ""

            if (
                not attached_field
                or attached_field == "pd_form"
                or attached_field == "custom_pd_form"
                or "pd_form" in attached_field
            ):
                if (
                    file_url
                    and file_url not in pd_image_urls
                ):
                    pd_image_urls.append(file_url)

        pd_count = len(pd_image_urls)

        if pd_count < 2:
            frappe.throw(
                "At least 2 PD Form images are mandatory"
            )

        if pd_count > 5:
            frappe.throw(
                "Maximum 5 PD Form images are allowed"
            )


    # ------------------------------------------------------------
    # UPDATE LEAD
    # ------------------------------------------------------------

    lead_values = {
        "custom_appointment_status": status,
        "custom_status_updated_by_employee": emp.get("name"),
        "custom_status_updated_by_name": emp.get("employee_name"),
        "custom_status_updated_by_user": frappe.session.user,
        "custom_status_updated_on": now_value,
        "custom_remarks": (
            remarks
            if status in negative_statuses
            else ""
        )
    }


    # Visited Booked means the Lead is converted.
    if status == "Visited Booked":
        lead_values["status"] = "Converted"


    # Visited Not Booked must never become Cancelled.
    elif status == "Visited Not Booked":
        lead_values["status"] = "Appointment no response"


    # Not Visited must not use Cancelled.
    elif status == "Not Visited":
        lead_values["status"] = "Appointment no response"


    # When correcting a negative result back to Visited,
    # remove the old negative Lead status.
    elif status == "Visited":
        if old.get("status") in [
            "Appointment no response",
            "Cancelled"
        ]:
            lead_values["status"] = "Appointment Booked"


    frappe.db.set_value(
        "Lead",
        lead,
        lead_values
    )


    # ------------------------------------------------------------
    # FIND LINKED PATIENT
    # ------------------------------------------------------------

    if not patient_name:
        patient_name = frappe.db.get_value(
            "Patient",
            {"custom_lead": lead},
            "name"
        ) or ""


    # ------------------------------------------------------------
    # SYNC CONSULTATION EMPLOYEE AND DECISION TO PATIENT
    # ------------------------------------------------------------

    if patient_name:
        practitioner_rows = frappe.get_all(
            "Healthcare Practitioner",
            filters={
                "employee": emp.get("name")
            },
            fields=[
                "name",
                "branch"
            ],
            order_by="modified desc",
            ignore_permissions=True,
            limit_page_length=20
        )

        practitioner_name = ""

        # Prefer a practitioner from the same branch.
        for practitioner_row in practitioner_rows:
            if (
                practitioner_row.get("branch")
                == emp.get("branch")
            ):
                practitioner_name = (
                    practitioner_row.get("name") or ""
                )
                break

        # Fallback to the first linked practitioner.
        if not practitioner_name and practitioner_rows:
            practitioner_name = (
                practitioner_rows[0].get("name") or ""
            )


        patient_values = {}


        if practitioner_name:
            patient_values["custom_employee_id"] = (
                practitioner_name
            )


        if status == "Visited Booked":
            patient_values["custom_final_decision"] = "Booked"


        elif status == "Visited Not Booked":
            patient_values["custom_final_decision"] = (
                "Not-Booked"
            )


        # Clear an old final decision when reopening/correcting.
        elif status in [
            "Visited",
            "Not Visited"
        ]:
            patient_values["custom_final_decision"] = ""


        if patient_values:
            frappe.db.set_value(
                "Patient",
                patient_name,
                patient_values
            )


    # ------------------------------------------------------------
    # COPY PD IMAGES INTO PATIENT CHILD TABLE
    # ------------------------------------------------------------

    if (
        patient_name
        and status in [
            "Visited Booked",
            "Visited Not Booked"
        ]
    ):
        patient_doc = frappe.get_doc(
            "Patient",
            patient_name
        )

        pd_meta = frappe.get_meta("PD Form")

        pd_attach_field = ""

        for pd_df in pd_meta.fields:
            if (
                pd_df.fieldtype in [
                    "Attach",
                    "Attach Image"
                ]
                and not pd_df.hidden
            ):
                pd_attach_field = pd_df.fieldname
                break


        if not pd_attach_field:
            frappe.throw(
                "PD Form child table has no "
                "Attach or Attach Image field"
            )


        existing_urls = []

        for pd_row in (
            patient_doc.get("custom_pd_form") or []
        ):
            existing_url = pd_row.get(pd_attach_field)

            if existing_url:
                existing_urls.append(existing_url)


        patient_files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Patient",
                "attached_to_name": patient_name
            },
            fields=[
                "file_url",
                "attached_to_field"
            ],
            order_by="creation asc",
            ignore_permissions=True,
            limit_page_length=0
        )


        for patient_file in patient_files:
            attached_field = (
                patient_file.get("attached_to_field") or ""
            ).lower()

            file_url = (
                patient_file.get("file_url") or ""
            )

            is_pd_form_file = (
                not attached_field
                or attached_field == "pd_form"
                or attached_field == "custom_pd_form"
                or "pd_form" in attached_field
            )

            if (
                is_pd_form_file
                and file_url
                and file_url not in existing_urls
            ):
                patient_doc.append(
                    "custom_pd_form",
                    {
                        pd_attach_field: file_url
                    }
                )

                existing_urls.append(file_url)


        if len(existing_urls) < 2:
            frappe.throw(
                "At least 2 PD Form images are mandatory"
            )


        if len(existing_urls) > 5:
            frappe.throw(
                "Maximum 5 PD Form images are allowed"
            )


        patient_doc.save(ignore_permissions=True)


    # ------------------------------------------------------------
    # STATUS HISTORY COMMENT
    # ------------------------------------------------------------

    safe_status = frappe.utils.escape_html(
        status
    )

    safe_previous = frappe.utils.escape_html(
        previous_status or "Not updated"
    )

    safe_employee = frappe.utils.escape_html(
        emp.get("employee_name") or ""
    )

    safe_remarks = frappe.utils.escape_html(
        remarks or "No remarks"
    )


    comment_content = (
        "CC Walk-in Status: "
        + safe_previous
        + " → "
        + safe_status
        + " | Consultation Employee: "
        + safe_employee
        + " | Remarks: "
        + safe_remarks
    )


    comment = frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Lead",
        "reference_name": lead,
        "comment_by": emp.get("employee_name"),
        "content": comment_content
    })


    comment.insert(ignore_permissions=True)


    # ------------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------------

    frappe.response["message"] = {
        "ok": 1,
        "lead": lead,
        "status": status,
        "previous_status": previous_status,
        "remarks": remarks,
        "employee": emp.get("name"),
        "employee_name": emp.get("employee_name"),
        "updated_on": now_value,
        "patient": patient_name
    }
