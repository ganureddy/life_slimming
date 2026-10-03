"""cc_get_leads

Original API: cc_get_leads
Source modified: 2026-10-03 11:06:14.910658
See ../CATALOG.md for migration notes and validation limits.
"""

import json
import re

import frappe
from frappe.integrations.utils import make_post_request as _make_post_request
from frappe.utils.safe_exec import read_sql as _read_sql
from frappe.utils.safe_exec import call_whitelisted_function as _call_whitelisted
from life_slimming.api._runtime import script_endpoint
from life_slimming.api.cc_appointments import enrich_lead_appointments


@script_endpoint(allow_guest=False)
def run(**kwargs):
    # ═══════════════════════════════════════════════════════════════════
    # Server Script: cc_get_leads
    # Script Type : API   |   API Method: cc_get_leads   |   Allow Guest: NO
    # v2 (15-Jul-2026): returns creation/modified; date_mode 'created' filters on
    #   the real `creation` timestamp ('posting' still available for the old behaviour).
    # v3 (15-Jul-2026): adds date_mode "appointment" -> filters by
    #   custom_appointment_date_and_time, so the dashboard can load appointments
    #   SCHEDULED in the range regardless of when the lead was created.
    # v4 (16-Jul-2026): page limit raised 500 -> 5000. A "This Month" range easily
    #   exceeds 500 leads, and the old cap truncated SILENTLY, so dashboard totals
    #   and the conversion rate were simply wrong with no warning. The response is
    #   now an object: {"rows": [...], "total": N, "truncated": 0/1} so the UI can
    #   warn when a range is still too large.
    # v5 (16-Jul-2026): OWNER SCOPING. Non-manager roles (i.e. plain Sales User) now
    #   only receive leads where lead_owner = their own user. Managers
    #   (System Manager / Sales Manager / Call Center Export) still see everything.
    #   Enforced HERE, server-side, on purpose: filtering only in the dashboard JS
    #   would let an agent call the API directly and pull every lead.
    # Replaces every frappe.client.get_list on Lead in the CC dashboard.
    # Runs with ignore_permissions (frappe.get_all), so it keeps working
    # after agent roles are downgraded to select-only on Lead.
    # Two modes:
    #   1) date range : args from_date, to_date, date_mode ("created"/"updated")
    #   2) phone match: arg phone (used by global-search fallback + duplicate finder)
    # ═══════════════════════════════════════════════════════════════════

    ALLOWED_ROLES = ["System Manager", "Sales Manager", "Sales User", "Call Center Export", "Branch Sales Invoice"]

    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Not permitted")

    user_roles = frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")
    has_access = False
    for r in ALLOWED_ROLES:
        if r in user_roles:
            has_access = True
            break
    if not has_access:
        frappe.throw("Not permitted")

    # Managers see all leads; everyone else is scoped to leads they own.
    MANAGER_ROLES = ["System Manager", "Sales Manager", "Call Center Export"]
    is_manager = False
    for r in MANAGER_ROLES:
        if r in user_roles:
            is_manager = True
            break

    # LEAD_FIELDS = [
    #     "name", "lead_name", "first_name", "mobile_no", "phone", "age", "gender", "city", "branch",
    #     "lead_assign_to_branch", "source", "enquired_for", "category", "consultant", "status", "lead_owner",
    #     "custom_posting_date", "custom_remarks", "custom_appointment_date_and_time", "custom_appointment_status",
    #     "height", "weight", "medical_history", "custom_cc_stage", "custom_cc_sub_status", "custom_next_followup_date",
    #     "custom_call_count", "custom_conclusion_remark", "custom_bmi", "custom_target_weight", "custom_treatment_interests",
    #     "custom_current_medication", "custom_hospitalized", "custom_consulting_doctor",
    #     "email_id", "custom_status_updated_date", "custom_last_call_time", "custom_client_category",
    #     "custom_media", "custom_previous_attempts", "custom_marital_status", "custom_no_of_kids",
    #     "custom_delivery_type", "custom_breastfeeding",
    #     "creation", "modified"
    # ]
    LEAD_FIELDS = [
        "name", "lead_name", "first_name", "mobile_no", "phone", "age", "gender", "city", "branch",
        "lead_assign_to_branch", "source", "enquired_for", "category", "consultant", "status", "lead_owner",
        "custom_posting_date", "custom_remarks", "custom_appointment_date_and_time", "custom_appointment_status",
        "height", "weight", "medical_history", "custom_cc_stage", "custom_cc_sub_status", "custom_next_followup_date",
        "custom_call_count", "custom_conclusion_remark", "custom_bmi", "custom_target_weight", "custom_treatment_interests",
        "custom_current_medication", "custom_hospitalized", "custom_consulting_doctor",
        "email_id", "custom_status_updated_date", "custom_last_call_time", "custom_client_category",
        "custom_media", "custom_previous_attempts", "custom_marital_status", "custom_no_of_kids",
        "custom_delivery_type", "custom_breastfeeding", "custom_chat_script",
        "creation", "modified"
    ]
    LEAD_FIELDS += ["custom_appointment", "custom_appointment_duration"]
    phone = (frappe.form_dict.get("phone") or "").strip()

    query = (frappe.form_dict.get("query") or "").strip()
    contact_manager = user in ["bhuvan@lifescc.com", "surya@lifescc.com"]
    if not contact_manager:
        contact_manager = bool(frappe.db.exists("Employee", {"user_id": user, "status": "Active", "designation": "Business Executive Team Leader"}))
    if query:
        if len(query) < 2:
            frappe.throw("Enter at least two characters")
        scoped = [] if is_manager else [["lead_owner", "=", user]]
        pattern = "%" + query.replace("%", "").replace("_", "") + "%"
        rows = frappe.get_all("Lead", fields=LEAD_FIELDS, filters=scoped,
            or_filters=[["lead_name", "like", pattern], ["name", "like", pattern], ["mobile_no", "like", pattern], ["phone", "like", pattern], ["custom_remarks", "like", pattern]],
            order_by="modified desc", limit_start=int(frappe.form_dict.get("start") or 0), limit_page_length=21)
        frappe.response["message"] = {"rows": rows[:20], "more": len(rows) > 20, "contact_manager": contact_manager, "scoped_to_owner": 0 if is_manager else 1}
    elif phone:
        digits = ""
        for ch in phone:
            if ch.isdigit():
                digits = digits + ch
        digits = digits[-10:]
        if len(digits) < 5:
            frappe.throw("Phone search needs at least 5 digits")
        phone_filters = []
        if not is_manager:
            phone_filters.append(["lead_owner", "=", user])
        rows = frappe.get_all(
            "Lead",
            fields=LEAD_FIELDS,
            filters=phone_filters,
            or_filters=[
                ["mobile_no", "like", "%" + digits + "%"],
                ["phone", "like", "%" + digits + "%"]
            ],
            order_by="modified desc",
            limit_page_length=10
        )
        frappe.response["message"] = {"rows": rows, "total": len(rows), "truncated": 0,
                                     "scoped_to_owner": 0 if is_manager else 1}
    else:
        from_date = frappe.form_dict.get("from_date")
        to_date = frappe.form_dict.get("to_date")
        date_mode = frappe.form_dict.get("date_mode") or "created"
        if not from_date or not to_date:
            frappe.throw("from_date and to_date are required")
        if date_mode == "updated":
            filters = [["modified", "between", [from_date + " 00:00:00", to_date + " 23:59:59"]]]
        elif date_mode == "posting":
            filters = [["custom_posting_date", "between", [from_date, to_date]]]
        elif date_mode == "appointment":
            # Leads whose APPOINTMENT falls in the range (whenever the lead was created)
            filters = [["custom_appointment_date_and_time", "between", [from_date + " 00:00:00", to_date + " 23:59:59"]]]
        elif date_mode == "followup":
            # Leads whose NEXT FOLLOW-UP falls in the range (whenever the lead was created)
            filters = [["custom_next_followup_date", "between", [from_date + " 00:00:00", to_date + " 23:59:59"]]]
        else:
            # v2: "created" now uses the portal's REAL creation timestamp, not the
            # editable custom_posting_date business field.
            filters = [["creation", "between", [from_date + " 00:00:00", to_date + " 23:59:59"]]]
        if not is_manager:
            filters.append(["lead_owner", "=", user])

        PAGE_LIMIT = 5000
        total = frappe.db.count("Lead", filters=filters)
        rows = frappe.get_all(
            "Lead",
            fields=LEAD_FIELDS,
            filters=filters,
            order_by="modified desc",
            limit_page_length=PAGE_LIMIT
        )
        frappe.response["message"] = {
            "rows": rows,
            "total": total,
            "truncated": 1 if total > PAGE_LIMIT else 0,
            "scoped_to_owner": 0 if is_manager else 1
        }
    frappe.response["message"]["contact_manager"] = contact_manager

    if query and frappe.form_dict.get("detail"):
        for item in frappe.response["message"].get("rows") or []:
            if item.get("name") == query:
                versions = frappe.get_all("Version", filters={"ref_doctype": "Lead", "docname": query}, fields=["creation", "owner", "data"], order_by="creation desc", limit_page_length=0)
                events = []
                prior_connected = ""
                connected_values = ["appointment booked", "callback: scheduled", "price negotiation", "get back", "walked in: not booked", "walked in & booked", "not interested", "other clinic", "joined competition", "do not contact", "existing client", "job enquiry", "tna", "nid", "franchise lead", "not enquired"]
                for version in versions:
                    for change in json.loads(version.get("data") or "{}").get("changed") or []:
                        if change[0] == "custom_cc_sub_status":
                            events.append({"at": str(version.get("creation")), "by": version.get("owner"), "from": change[1], "to": change[2]})
                            for value in [change[2], change[1]]:
                                if str(value or "").strip().lower() in connected_values and not prior_connected:
                                    prior_connected = value
                item["workflow_hint"] = {"prior_connected": prior_connected, "legacy_events": events}

    enrich_lead_appointments(frappe.response["message"].get("rows") or [])
