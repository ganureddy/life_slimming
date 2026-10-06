"""cc_update_lead

Original API: cc_update_lead
Source modified: 2026-09-06 14:53:19.081176
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
    # # ═══════════════════════════════════════════════════════════════════
    # # Server Script: cc_update_lead
    # # Script Type : API   |   API Method: cc_update_lead   |   Allow Guest: NO
    # # Replaces every frappe.client.set_value("Lead", ...) call in the dashboard
    # # (follow-up save, booking sync, manual assignment, auto round-robin).
    # # Field whitelist = only the fields the dashboard actually writes, so this
    # # API can't be abused to set arbitrary Lead fields.
    # # lead_owner changes are role-gated SERVER-SIDE (client checks are cosmetic).
    # # v4 (16-Jul-2026): OWNER SCOPING — a non-manager can only update leads they own.
    # #   Without this, an agent scoped to their own leads in cc_get_leads could still
    # #   POST an update for any lead ID they happened to know.
    # # ═══════════════════════════════════════════════════════════════════

    # ALLOWED_ROLES = ["System Manager", "Sales Manager", "Sales User", "Call Center Export", "Branch Sales Invoice"]
    # OWNER_EDIT_ROLES = ["System Manager", "Sales Manager", "Call Center Export"]

    # # Every field syncLeadToPortal / syncBookingToPortal / bulk assignment writes:
    # # ALLOWED_FIELDS = [
    # #     "first_name", "phone", "age", "gender", "city", "consultant", "weight", "height",
    # #     "custom_bmi", "custom_target_weight", "medical_history", "custom_current_medication",
    # #     "custom_previous_attempts", "custom_hospitalized", "custom_marital_status",
    # #     "custom_no_of_kids", "custom_breastfeeding", "email_id", "category",
    # #     "lead_assign_to_branch", "source", "enquired_for", "lead_owner",
    # #     "custom_cc_stage", "custom_cc_sub_status", "status", "custom_conclusion_remark",
    # #     "custom_remarks", "custom_next_followup_date", "branch",
    # #     "custom_appointment_date_and_time", "custom_appointment_duration",
    # #     "custom_consulting_doctor", "custom_appointment_status",
    # #     # v5 — backing field for the treatment-interest checkboxes (script 9)
    # #     "custom_treatment_interests",
    # #     # v6 — pipeline date/time
    # #     "custom_pipeline_date_and_time"
    # # ]
    # ALLOWED_FIELDS = [
    #     "first_name", "phone", "age", "gender", "city", "consultant", "weight", "height",
    #     "custom_bmi", "custom_target_weight", "medical_history", "custom_current_medication",
    #     "custom_previous_attempts", "custom_hospitalized", "custom_marital_status",
    #     "custom_no_of_kids", "custom_breastfeeding", "email_id", "category",
    #     "lead_assign_to_branch", "source", "enquired_for", "lead_owner",
    #     "custom_cc_stage", "custom_cc_sub_status", "status", "custom_conclusion_remark",
    #     "custom_remarks", "custom_next_followup_date", "branch",
    #     "custom_appointment_date_and_time", "custom_appointment_duration",
    #     "custom_consulting_doctor", "custom_appointment_status",
    #     "custom_treatment_interests",
    #     "custom_pipeline_date_and_time",
    #     "custom_chat_script"
    # ]
    # user = frappe.session.user
    # if user == "Guest":
    #     frappe.throw("Not permitted")

    # user_roles = frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")
    # has_access = False
    # for r in ALLOWED_ROLES:
    #     if r in user_roles:
    #         has_access = True
    #         break
    # if not has_access:
    #     frappe.throw("Not permitted")

    # can_edit_owner = False
    # for r in OWNER_EDIT_ROLES:
    #     if r in user_roles:
    #         can_edit_owner = True
    #         break

    # # Managers may edit any lead; everyone else only their own.
    # is_manager = can_edit_owner

    # lead = frappe.form_dict.get("lead")
    # if not lead:
    #     frappe.throw("lead is required")

    # if not is_manager:
    #     current_owner = frappe.db.get_value("Lead", lead, "lead_owner")
    #     if current_owner != user:
    #         frappe.throw("Not permitted: this lead is not assigned to you")

    # # NOTE: frappe.parse_json is NOT available inside safe_exec (Server Scripts).
    # # Frappe already decodes a JSON-string form value into a dict for us, but be
    # # defensive: accept either a dict or a JSON string via the whitelisted json module.
    # values = frappe.form_dict.get("values")
    # if isinstance(values, str):
    #     try:
    #         values = json.loads(values or "{}")
    #     except Exception:
    #         frappe.throw("values could not be parsed as JSON")
    # if not isinstance(values, dict):
    #     frappe.throw("values must be a JSON object")

    # # v5 — Link fields reject values that aren't existing records, and ONE bad link
    # # aborts the WHOLE save ("Could not find Consultant: X" — and the agent's other
    # # 30 fields silently vanish with it). Resolve links case-insensitively; if a
    # # value genuinely doesn't exist, drop THAT FIELD and save the rest.
    # LINK_FIELDS = {
    #     "consultant": "Concern",
    #     "category": "Healthcare Service Unit",
    #     "custom_consulting_doctor": "Healthcare Practitioner",
    #     "branch": "Branch",
    #     "lead_assign_to_branch": "Branch",
    #     "lead_owner": "User",
    # }

    # def resolve_link(doctype, value):
    #     v = str(value or "").strip()
    #     if not v:
    #         return ""
    #     exact = frappe.db.exists(doctype, v)
    #     if exact:
    #         return v
    #     # case/space-insensitive fallback: 'Slimming' should find 'slimming'
    #     rows = frappe.get_all(doctype, pluck="name", limit_page_length=0)
    #     for n in rows:
    #         if str(n).strip().lower() == v.lower():
    #             return n
    #     return None

    # clean = {}
    # skipped = []
    # for k in values:
    #     if k not in ALLOWED_FIELDS:
    #         skipped.append(k)
    #         continue
    #     if k == "lead_owner" and not can_edit_owner:
    #         skipped.append(k)
    #         continue
    #     if k in LINK_FIELDS and values[k]:
    #         resolved = resolve_link(LINK_FIELDS[k], values[k])
    #         if resolved is None:
    #             skipped.append("%s (no %s named '%s')" % (k, LINK_FIELDS[k], values[k]))
    #             continue
    #         clean[k] = resolved
    #         continue
    #     clean[k] = values[k]

    # if not clean:
    #     frappe.response["message"] = {"ok": 0, "name": lead, "changed": 0, "skipped": skipped}
    # else:
    #     doc = frappe.get_doc("Lead", lead)
    #     doc.update(clean)
    #     doc.save(ignore_permissions=True)
    #     frappe.response["message"] = {"ok": 1, "name": doc.name, "changed": len(clean), "skipped": skipped}





















































    # ============================================================
    # Server Script: cc_update_lead
    # Script Type: API
    # API Method: cc_update_lead
    # Allow Guest: No
    #
    # Only "Visited Booked" is permanently locked.
    # Visited Not Booked and Not Visited can be corrected/rebooked.
    # ============================================================

    ALLOWED_ROLES = [
        "System Manager",
        "Sales Manager",
        "Sales User",
        "Call Center Export",
        "Branch Sales Invoice"
    ]

    OWNER_EDIT_ROLES = [
        "System Manager",
        "Sales Manager",
        "Call Center Export"
    ]

    ALLOWED_FIELDS = [
        "first_name",
        "phone",
        "age",
        "gender",
        "city",
        "consultant",
        "weight",
        "height",
        "custom_bmi",
        "custom_target_weight",
        "medical_history",
        "custom_current_medication",
        "custom_previous_attempts",
        "custom_hospitalized",
        "custom_marital_status",
        "custom_no_of_kids",
        "custom_breastfeeding",
        "email_id",
        "category",
        "lead_assign_to_branch",
        "source",
        "enquired_for",
        "custom_media",
        "custom_posting_date",
        "custom_delivery_type",
        "custom_specific_interests",
        "lead_owner",
        "custom_cc_stage",
        "custom_cc_sub_status",
        "status",
        "custom_conclusion_remark",
        "custom_remarks",
        "custom_next_followup_date",
        "branch",
        "custom_appointment_date_and_time",
        "custom_appointment_duration",
        "custom_consulting_doctor",
        "custom_appointment_status",
        "custom_treatment_interests",
        "custom_pipeline_date_and_time",
        "custom_chat_script"
    ]


    # ------------------------------------------------------------
    # LOGIN AND ROLE VALIDATION
    # ------------------------------------------------------------

    user = frappe.session.user

    if user == "Guest":
        frappe.throw("Not permitted")


    user_roles = frappe.get_all(
        "Has Role",
        filters={
            "parent": user,
            "parenttype": "User"
        },
        pluck="role"
    )


    has_access = False

    for role in ALLOWED_ROLES:
        if role in user_roles:
            has_access = True
            break


    if not has_access:
        frappe.throw("Not permitted")


    can_edit_owner = False

    for role in OWNER_EDIT_ROLES:
        if role in user_roles:
            can_edit_owner = True
            break


    # ------------------------------------------------------------
    # GET LEAD
    # ------------------------------------------------------------

    lead = frappe.form_dict.get("lead")

    if not lead:
        frappe.throw("lead is required")


    if not frappe.db.exists("Lead", lead):
        frappe.throw("Lead not found")


    # Non-manager users can update only their assigned leads.
    if not can_edit_owner:
        current_owner = frappe.db.get_value(
            "Lead",
            lead,
            "lead_owner"
        )

        if current_owner != user:
            frappe.throw(
                "Not permitted: this lead is not assigned to you"
            )


    # ------------------------------------------------------------
    # GET VALUES
    # ------------------------------------------------------------

    values = frappe.form_dict.get("values")


    if isinstance(values, str):
        try:
            values = json.loads(values or "{}")
        except Exception:
            frappe.throw("values could not be parsed as JSON")


    if not isinstance(values, dict):
        frappe.throw("values must be a JSON object")


    # ------------------------------------------------------------
    # LINK FIELD VALIDATION
    # ------------------------------------------------------------

    LINK_FIELDS = {
        "consultant": "Concern",
        "category": "Healthcare Service Unit",
        "custom_consulting_doctor": "Healthcare Practitioner",
        "branch": "Branch",
        "lead_assign_to_branch": "Branch",
        "lead_owner": "User"
    }


    def resolve_link(doctype, value):
        link_value = str(value or "").strip()

        if not link_value:
            return ""

        if frappe.db.exists(doctype, link_value):
            return link_value

        records = frappe.get_all(
            doctype,
            pluck="name",
            limit_page_length=0
        )

        for record_name in records:
            if str(record_name).strip().lower() == link_value.lower():
                return record_name

        return None


    # ------------------------------------------------------------
    # APPOINTMENT STATUS PROTECTION
    # ------------------------------------------------------------

    current_appointment_status = frappe.db.get_value(
        "Lead",
        lead,
        "custom_appointment_status"
    ) or ""

    current_appointment_status = str(
        current_appointment_status
    ).strip()


    requested_appointment_status = values.get(
        "custom_appointment_status"
    )


    if requested_appointment_status is not None:
        requested_appointment_status = str(
            requested_appointment_status or ""
        ).strip()

        # Cancelled must never be used.
        if requested_appointment_status == "Cancelled":
            frappe.throw(
                "Cancelled is not allowed. "
                "Use Not Booked or Not Visited."
            )

        # Only Visited Booked is permanently locked.
        if (
            current_appointment_status == "Visited Booked"
            and requested_appointment_status != "Visited Booked"
        ):
            frappe.throw(
                "Visited Booked is locked and cannot be changed"
            )

        # Walk-in statuses must be updated only through cc_walkin_update.
        if requested_appointment_status in [
            "Visited",
            "Visited Booked",
            "Visited Not Booked",
            "Not Visited"
        ]:
            frappe.throw(
                "Use cc_walkin_update for walk-in status changes"
            )


    # ------------------------------------------------------------
    # PREPARE CLEAN VALUES
    # ------------------------------------------------------------

    clean = {}
    skipped = []


    for fieldname in values:
        fieldvalue = values.get(fieldname)

        if fieldname not in ALLOWED_FIELDS:
            skipped.append(fieldname)
            continue

        # Only authorized manager roles may change Lead Owner.
        if fieldname == "lead_owner" and not can_edit_owner:
            skipped.append(fieldname)
            continue

        # Resolve Link fields safely.
        if fieldname in LINK_FIELDS and fieldvalue:
            resolved_value = resolve_link(
                LINK_FIELDS[fieldname],
                fieldvalue
            )

            if resolved_value is None:
                skipped.append(
                    "%s (no %s named '%s')" % (
                        fieldname,
                        LINK_FIELDS[fieldname],
                        fieldvalue
                    )
                )
                continue

            clean[fieldname] = resolved_value
            continue

        clean[fieldname] = fieldvalue


    # ------------------------------------------------------------
    # SAVE LEAD
    # ------------------------------------------------------------

    if not clean:
        frappe.response["message"] = {
            "ok": 0,
            "name": lead,
            "changed": 0,
            "skipped": skipped
        }

    else:
        lead_doc = frappe.get_doc("Lead", lead)

        lead_doc.update(clean)

        lead_doc.save(ignore_permissions=True)

        frappe.response["message"] = {
            "ok": 1,
            "name": lead_doc.name,
            "changed": len(clean),
            "skipped": skipped
        }
