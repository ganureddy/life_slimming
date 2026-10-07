"""cc_add_lead_followup

Original API: cc_add_lead_followup
Source modified: 2026-08-13 13:28:02.051118
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
    # Server Script  |  Type: API  |  Method: cc_add_lead_followup
    # Called by the CC Dashboard Custom HTML Block after every call.
    # - Updates parent Lead fields (stage, sub-status, next followup,
    #   conclusion remark, call count, last call time)
    # - Appends a row into the followup child table (log of the call)
    # safe_exec compatible: no imports, no .format()
    # ============================================================
    # frappe.form_dict params expected:
    #   lead          (required)  Lead name e.g. CRM-LEAD-2026-18827
    #   cc_stage      UNTOUCHED / FOLLOW-UP / SUCCESS / LOST / INVALID
    #   cc_sub_status
    #   status        one of Lead.status select options
    #   next_followup datetime string or ""
    #   conclusion    text
    #   remarks       text
    # ============================================================

    params = frappe.form_dict
    lead_name = params.get("lead")

    # Match the CC lead APIs: only permitted CC/sales roles may write, and
    # non-manager agents may only write follow-ups to their own leads.
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Not permitted")
    user_roles = frappe.get_all(
        "Has Role",
        filters={"parent": user, "parenttype": "User"},
        pluck="role"
    )
    allowed_roles = ["System Manager", "Sales Manager", "Sales User", "Call Center Export"]
    if not any(role in user_roles for role in allowed_roles):
        frappe.throw("Not permitted")
    manager_roles = ["System Manager", "Sales Manager", "Call Center Export"]
    can_manage = any(role in user_roles for role in manager_roles)

    if not lead_name:
        frappe.response["message"] = {"ok": 0, "error": "lead is required"}
    else:
        if not frappe.db.exists("Lead", lead_name):
            frappe.response["message"] = {"ok": 0, "error": "Lead not found: " + lead_name}
        else:
            if not can_manage and frappe.db.get_value("Lead", lead_name, "lead_owner") != user:
                frappe.throw("Not permitted: this lead is not assigned to you")
            doc = frappe.get_doc("Lead", lead_name)

            # ---- parent field updates -------------------------------
            if params.get("cc_stage"):
                doc.custom_cc_stage = params.get("cc_stage")
            if params.get("cc_sub_status"):
                sub_val = params.get("cc_sub_status")
                sub_fix = {
                    "Not Interested": "Not interested",
                    "Existing client": "Existing Client",
                    "No response": "No Response",
                    "Invalid number": "Invalid Number",
                    "Call Back": "Callback: Scheduled",
                    "Callback": "Callback: Scheduled",
                }
                sub_val = sub_fix.get(sub_val, sub_val)
                doc.custom_cc_sub_status = sub_val
            if params.get("status"):
                doc.status = params.get("status")
            if params.get("next_followup"):
                doc.custom_next_followup_date = params.get("next_followup")
            if params.get("conclusion"):
                doc.custom_conclusion_remark = params.get("conclusion")
            if params.get("remarks"):
                doc.custom_remarks = params.get("remarks")

            doc.custom_call_count = (doc.custom_call_count or 0) + 1
            doc.custom_last_call_time = frappe.utils.now_datetime()

            # ---- append follow-up log row ---------------------------
            # TODO: verify child fieldnames first! MCP has no read access
            # to "Followup" child doctype. Run in System Console:
            #   for f in frappe.get_meta("Followup").fields:
            #       print(f.fieldname, f.fieldtype, f.label)
            # then correct the keys below to the real fieldnames.
            followup_meta = frappe.get_meta("Followup")
            child_fieldnames = []
            for f in followup_meta.fields:
                child_fieldnames.append(f.fieldname)

            row = {}
            # common guesses - only set keys that actually exist on the child
            candidate_map = {
                "date": frappe.utils.today(),
                "followup_date": frappe.utils.today(),
                "remarks": params.get("remarks") or params.get("conclusion") or "",
                "remark": params.get("remarks") or params.get("conclusion") or "",
                "status": params.get("status") or "",
                "followup_by": frappe.session.user,
                "user": frappe.session.user,
            }
            for key in candidate_map:
                if key in child_fieldnames:
                    row[key] = candidate_map[key]

            if row:
                doc.append("followup", row)

            doc.save(ignore_permissions=True)
            frappe.db.commit()

            frappe.response["message"] = {
                "ok": 1,
                "lead": doc.name,
                "call_count": doc.custom_call_count,
                "followup_row_written": 1 if row else 0,
            }
