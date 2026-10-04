"""Approvals Report Conversion

Original API: life_approval_report_conversion_action
Source modified: 2026-09-24 16:42:08.254544
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
    # v40 - C2C Therapy Type / Therapy Plan display-label validation fix
    # ============================================================================
    # Server Script Type : API
    # API Method         : life_approval_report_conversion_action
    # Allow Guest        : OFF
    # Purpose            : Secure P2P / C2C / B2B approval context + action API
    # ============================================================================
    #
    # Supported operations:
    #   operation = context
    #   operation = action
    #   operation = repair_b2b   (authorized re-apply for an already-approved B2B)
    #
    # The browser is NOT trusted for approval authority. Every action below reloads
    # the document, resolves the current pending stage, validates the logged-in user
    # and branch, validates required inputs, then saves the real DocType.
    # ============================================================================

    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw("Please login to use approval actions.")

    operation = str(frappe.form_dict.get("operation") or "context").strip().lower()
    doctype = str(frappe.form_dict.get("doctype") or "").strip()
    docname = str(frappe.form_dict.get("docname") or "").strip()

    SUPPORTED = [
        "LIFE Client Package Conversion Same Client Package To Package",
        "Client Package Conversion Client To Client",
        "Client Transfer Request Form"
    ]

    if doctype not in SUPPORTED:
        frappe.throw("Unsupported approval document type.")

    if not docname:
        frappe.throw("Request ID is required.")

    doc = frappe.get_doc(doctype, docname)

    # ---------------------------------------------------------------------------
    # Logged-in user helpers
    # ---------------------------------------------------------------------------
    role_rows = frappe.get_all(
        "Has Role",
        filters={"parent": user, "parenttype": "User"},
        fields=["role"],
        limit_page_length=500
    )
    roles = []
    for rr in role_rows:
        role = rr.get("role")
        if role and role not in roles:
            roles.append(role)

    is_system_manager = user == "Administrator" or "System Manager" in roles

    user_full_name = frappe.db.get_value("User", user, "full_name") or user

    employee_rows = frappe.get_all(
        "Employee",
        filters={"user_id": user, "status": "Active"},
        fields=["name", "employee_name", "designation", "branch", "user_id"],
        order_by="modified desc",
        limit_page_length=1
    )
    login_employee = employee_rows[0] if employee_rows else None

    branch_permission_rows = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Branch"},
        fields=["for_value"],
        limit_page_length=500
    )
    allowed_branches = []
    for bp in branch_permission_rows:
        val = str(bp.get("for_value") or "").strip()
        if val and val not in allowed_branches:
            allowed_branches.append(val)


    def clean(value):
        return str(value or "").strip()


    def lower(value):
        return clean(value).lower()


    def has_field(fieldname):
        try:
            return bool(doc.meta.has_field(fieldname))
        except Exception:
            return False


    def set_if(fieldname, value):
        if has_field(fieldname):
            doc.set(fieldname, value)


    def user_can_access_branch(branch):
        branch = clean(branch)
        if is_system_manager:
            return True
        if not branch:
            return False
        if allowed_branches:
            return branch in allowed_branches
        if login_employee and clean(login_employee.get("branch")) == branch:
            return True
        return False


    def active_manager_rows(branch, mode):
        branch = clean(branch)
        if not branch:
            return []

        rows = frappe.get_all(
            "Employee",
            filters={"status": "Active", "branch": branch},
            fields=["name", "employee_name", "designation", "branch", "user_id"],
            order_by="employee_name asc",
            limit_page_length=100
        )

        out = []
        p2p_allowed = [
            "acm", "acm(trainee)", "cm(trainee)", "assistant centre manager",
            "assistant center manager", "center manager", "centre manager", "senior manager"
        ]
        c2c_allowed = [
            "acm", "acm(trainee)", "cm(trainee)", "assistant centre manager",
            "assistant center manager", "center manager", "centre manager"
        ]
        b2b_keys = [
            "branch manager", "center manager", "centre manager",
            "assistant center manager", "assistant centre manager", "manager", "cm", "acm"
        ]

        for emp in rows:
            designation = lower(emp.get("designation"))
            ok = False
            if mode == "p2p":
                ok = designation in p2p_allowed
            elif mode == "c2c":
                ok = designation in c2c_allowed
            else:
                for key in b2b_keys:
                    if key in designation:
                        ok = True
                        break
            if ok:
                out.append(emp)

        # B2B source page falls back to branch staff when no manager keyword exists.
        if mode == "b2b" and not out:
            return rows
        return out


    def validate_manager_employee(employee_id, branch, mode):
        employee_id = clean(employee_id)
        if not employee_id:
            frappe.throw("Please select a valid Centre / Branch Manager.")

        rows = active_manager_rows(branch, mode)
        for emp in rows:
            if clean(emp.get("name")) == employee_id:
                return emp
        frappe.throw("Selected manager is not an active permitted manager for this request branch.")


    # ---------------------------------------------------------------------------
    # Fixed management user lists copied from the CURRENT source web pages.
    # ---------------------------------------------------------------------------
    P2P_AUDIT_USERS = {
        "kishore@lifescc.com": "Kishore",
        "audit@lifescc.com": "Merun Singh",
        "viveka@lifescc.com": "Viveka",
        "yaswanthkumaryy1234@gmail.com": "Yaswanth",
        "administrator": "Administrator"
    }

    P2P_COO_USERS = {
        "bhuvan@lifescc.com": "K Bhuvan Prasad",
        "yaswanthkumaryy1234@gmail.com": "Yaswanth",
        "administrator": "Administrator",
        "administrator@lifescc.com": "Administrator",
        "narendhar@lifescc.com": "Narendhar Reddy"
    }

    C2C_AUDIT_USERS = {
        "kishore@lifescc.com": "Kishore",
        "audit@lifescc.com": "Merun Singh",
        "viveka@lifescc.com": "Viveka",
        "vivekaarvind@gmail.com": "Kuriti Viveka",
        "yaswanthkumaryy1234@gmail.com": "Yaswanth",
        "administrator": "Administrator",
        "administrator@lifescc.com": "Administrator"
    }

    C2C_COO_USERS = {
        "bhuvan@lifescc.com": "K Bhuvan Prasad",
        "yaswanthkumaryy1234@gmail.com": "Yaswanth",
        "administrator": "Administrator",
        "administrator@lifescc.com": "Administrator",
        "narendhar@lifescc.com": "Narendhar"
    }

    B2B_AUDIT_USERS = {
        "viveka@lifescc.com": "Viveka",
        "audit@lifescc.com": "Merun Singh",
        "kishore@lifescc.com": "Kishore",
        "lokakavyareddy3@gmail.com": "Kavya Reddy",
        "yaswanthkumaryy1234@gmail.com": "Yaswanth",
        "narendhar@lifescc.com": "Narendhar",
        "administrator": "Administrator",
        "administrator@lifescc.com": "Administrator"
    }

    B2B_COO_USERS = {
        "bhuvan@lifescc.com": "K Bhuvan Prasad",
        "bhuvan@lifessc.com": "K Bhuvan Prasad",
        "lokakavyareddy3@gmail.com": "Kavya Reddy",
        "yaswanthkumaryy1234@gmail.com": "Yaswanth",
        "narendhar@lifescc.com": "Narendhar",
        "administrator": "Administrator",
        "administrator@lifescc.com": "Administrator"
    }

    user_key = lower(user)


    # ---------------------------------------------------------------------------
    # Current-stage resolvers
    # ---------------------------------------------------------------------------
    def p2p_pending_role():
        final_status = lower(doc.get("final_approval_status"))
        automation = lower(doc.get("automation_status"))
        stage = lower(doc.get("approval_stage") or doc.get("approval_display_status"))
        step = int(doc.get("current_tab_step") or 0)

        if final_status in ["approved", "rejected"]:
            return ""
        if automation in ["process completed", "skipped"]:
            return ""
        if "rejected" in stage or stage == "approved" or "process completed" in stage:
            return ""
        if "coo" in stage or "management" in stage or step == 4:
            return "coo"
        if "operations head" in stage or "audit team" in stage or "operations" in stage or step == 3:
            return "ops"
        return "cm"


    def c2c_pending_role():
        final_status = lower(doc.get("final_approval_status"))
        automation = lower(doc.get("automation_status"))
        stage = lower(doc.get("approval_stage") or doc.get("approval_display_status") or doc.get("conversion_status"))

        if final_status == "rejected" or automation in ["process completed", "skipped", "failed"]:
            return ""
        if final_status == "approved" and ("approved" in stage or int(doc.get("current_tab_step") or 0) >= 4):
            return ""
        if "rejected" in stage or "process completed" in stage:
            return ""
        if "coo" in stage or "management" in stage:
            return "operations_coo"
        if "audit" in stage or "operations manager" in stage or "operations head" in stage:
            return "audit_team"
        if "centre manager" in stage or "center manager" in stage:
            return "centre_manager"

        cm_decision = lower(doc.get("centre_manager_decision"))
        audit_decision = lower(doc.get("audit_team_decision"))
        if cm_decision not in ["approved", "approve"]:
            return "centre_manager"
        if audit_decision not in ["approved", "approve"]:
            return "audit_team"
        return "operations_coo"


    def b2b_pending_role():
        display = lower(doc.get("approval_display_status") or doc.get("approval_stage"))
        final_status = lower(doc.get("final_approval_status"))
        audit_status = lower(doc.get("audit_status"))
        step = int(doc.get("current_tab_step") or 0)

        if final_status in ["approved", "rejected"] and final_status != "pending":
            return ""
        if "rejected" in display or "completed" in display:
            return ""
        if "coo" in display or audit_status == "approved" or step >= 7:
            return "coo"
        if "audit" in display or clean(doc.get("cmname")) or step >= 6:
            return "audit"
        return "manager"


    # ---------------------------------------------------------------------------
    # Permission resolver
    # ---------------------------------------------------------------------------
    def resolve_context():
        if doctype == "LIFE Client Package Conversion Same Client Package To Package":
            mode = "p2p"
            role = p2p_pending_role()
            branch = clean(doc.get("branch"))
            labels = {"cm": "Centre Manager", "ops": "Audit Team", "coo": "COO / Management"}
            can_act = False
            reason = ""
            approver_name = ""

            if not role:
                reason = "This request is not waiting for an approval action."
            elif role == "cm":
                can_act = user_can_access_branch(branch)
                if not can_act:
                    reason = "Centre Manager approval is limited to the request branch."
            elif role == "ops":
                can_act = user_key in P2P_AUDIT_USERS
                approver_name = P2P_AUDIT_USERS.get(user_key) or ""
                if not can_act:
                    reason = "This request is waiting for an authorised Audit Team user."
            elif role == "coo":
                can_act = user_key in P2P_COO_USERS
                approver_name = P2P_COO_USERS.get(user_key) or ""
                if not can_act:
                    reason = "This request is waiting for an authorised COO / Management user."

            managers = active_manager_rows(branch, "p2p") if role == "cm" and can_act else []

            rows = []
            if role in ["ops", "coo"]:
                source_rows = doc.get("converted_package__service_name") or []
                for row in source_rows:
                    therapy = clean(row.get("converted_package__service_name") or row.get("therapy_type") or row.get("service_package_name"))
                    qty = int(float(row.get("converted_quantity") or row.get("no_of_sessions") or row.get("quantity") or 0))
                    completed = int(float(row.get("completed_sessions") or row.get("sessions_completed") or row.get("availed_quantity") or 0))
                    amount = float(row.get("balance_amount") or row.get("amount") or row.get("total_amount") or 0)
                    rows.append({
                        "name": clean(row.get("name")),
                        "therapy_type": therapy,
                        "qty": qty,
                        "completed": completed,
                        "amount": amount,
                        "source_row_name": clean(row.get("source_row_name")),
                        "source_plan": clean(row.get("source_plan"))
                    })

            return {
                "mode": mode,
                "pending_role": role,
                "role_label": labels.get(role) or "",
                "can_act": 1 if can_act else 0,
                "reason": reason,
                "branch": branch,
                "approver_name": approver_name or user_full_name,
                "centre_managers": managers,
                "remarks_required_for_approve": 1,
                "remarks_required_for_reject": 1,
                "require_signature": 0,
                "allow_table_edit": 1 if role in ["ops", "coo"] and can_act else 0,
                "table_rows": rows,
                "table_budget": float(doc.get("current_package__residual__balance_value_rs") or 0)
            }

        if doctype == "Client Package Conversion Client To Client":
            mode = "c2c"
            role = c2c_pending_role()
            branch = clean(doc.get("branch"))
            labels = {
                "centre_manager": "Centre Manager",
                "audit_team": "Audit / Corporate Team",
                "operations_coo": "COO / Management"
            }
            can_act = False
            reason = ""
            approver_name = ""

            if not role:
                reason = "This request is not waiting for an approval action."
            elif role == "centre_manager":
                can_act = user_can_access_branch(branch)
                if not can_act:
                    reason = "Centre Manager approval is limited to the transferor branch."
            elif role == "audit_team":
                can_act = user_key in C2C_AUDIT_USERS
                approver_name = C2C_AUDIT_USERS.get(user_key) or ""
                if not can_act:
                    reason = "This request is waiting for an authorised Audit / Corporate Team user."
            elif role == "operations_coo":
                can_act = user_key in C2C_COO_USERS
                approver_name = C2C_COO_USERS.get(user_key) or ""
                if not can_act:
                    reason = "This request is waiting for an authorised COO / Management user."

            managers = active_manager_rows(branch, "c2c") if role == "centre_manager" and can_act else []

            rows = []
            if role in ["audit_team", "operations_coo"]:
                for row in (doc.get("remaining_sessions_package_details") or []):
                    rows.append({
                        "name": clean(row.get("name")),
                        "therapy_type": clean(row.get("therapy_plans_been_transferred") or row.get("therapy_type")),
                        "qty": float(row.get("converted_quantity") or 0),
                        "amount": float(row.get("total_amount") or row.get("balance_quantity_amount") or 0),
                        "original_balance_quantity": float(row.get("original_balance_quantity") or row.get("max_quantity") or row.get("source_balance_before") or 0),
                        "max_quantity": float(row.get("max_quantity") or row.get("original_balance_quantity") or row.get("source_balance_before") or 0),
                        "start_date": clean(row.get("start_date")),
                        "validity_exp_dt": clean(row.get("validity_exp_dt")),
                        "balance_due": float(row.get("balance_due") or 0),
                        "unit_transfer_amount": float(row.get("unit_transfer_amount") or 0),
                        "unit_outstanding_amount": float(row.get("unit_outstanding_amount") or 0),
                        "source_therapy_plan": clean(row.get("source_therapy_plan")),
                        "source_therapy_row_name": clean(row.get("source_therapy_row_name")),
                        "source_invoice": clean(row.get("source_invoice")),
                        "source_sessions_before": float(row.get("source_sessions_before") or 0),
                        "source_completed_before": float(row.get("source_completed_before") or 0),
                        "source_balance_before": float(row.get("source_balance_before") or 0),
                        "source_sessions_after": float(row.get("source_sessions_after") or 0),
                        "source_balance_after": float(row.get("source_balance_after") or 0)
                    })

            return {
                "mode": mode,
                "pending_role": role,
                "role_label": labels.get(role) or "",
                "can_act": 1 if can_act else 0,
                "reason": reason,
                "branch": branch,
                "approver_name": approver_name or user_full_name,
                "centre_managers": managers,
                "remarks_required_for_approve": 0,
                "remarks_required_for_reject": 1,
                "require_signature": 0,
                "allow_table_edit": 1 if role in ["audit_team", "operations_coo"] and can_act else 0,
                "table_rows": rows,
                "table_budget": float(doc.get("balance_amount") or doc.get("total_paid_amount") or 0)
            }

        # B2B
        mode = "b2b"
        role = b2b_pending_role()
        branch = clean(doc.get("transfer_from_branch"))
        labels = {"manager": "Branch Manager", "audit": "Audit Team", "coo": "COO / Management"}
        can_act = False
        reason = ""
        approver_name = ""

        if not role:
            reason = "This request is not waiting for an approval action."
        elif role == "manager":
            can_act = user_can_access_branch(branch)
            if not can_act:
                reason = "Branch Manager approval is limited to the request branch."
        elif role == "audit":
            can_act = is_system_manager or user_key in B2B_AUDIT_USERS
            approver_name = B2B_AUDIT_USERS.get(user_key) or user_full_name
            if not can_act:
                reason = "This request is waiting for an authorised Audit Team user."
        elif role == "coo":
            can_act = is_system_manager or user_key in B2B_COO_USERS
            approver_name = B2B_COO_USERS.get(user_key) or user_full_name
            if not can_act:
                reason = "This request is waiting for an authorised COO / Management user."

        managers = active_manager_rows(branch, "b2b") if role == "manager" and can_act else []

        return {
            "mode": mode,
            "pending_role": role,
            "role_label": labels.get(role) or "",
            "can_act": 1 if can_act else 0,
            "reason": reason,
            "branch": branch,
            "approver_name": approver_name or user_full_name,
            "centre_managers": managers,
            "remarks_required_for_approve": 1,
            "remarks_required_for_reject": 1,
            "require_signature": 1 if can_act and role else 0,
            "allow_table_edit": 0,
            "table_rows": [],
            "table_budget": 0
        }


    # ---------------------------------------------------------------------------
    # Table helpers
    # ---------------------------------------------------------------------------
    def parse_table_rows():
        raw = frappe.form_dict.get("table_rows_json")
        if not raw:
            return []

        # Server Scripts run inside Frappe safe_exec. On this site
        # frappe.parse_json is not exposed on the restricted frappe namespace.
        # The safe_exec environment exposes the safe `json` namespace instead.
        if isinstance(raw, list):
            rows = raw
        else:
            try:
                rows = json.loads(raw)
            except Exception:
                frappe.throw("Final table data is invalid.")

        if not isinstance(rows, list):
            frappe.throw("Final table data must be a list.")

        return rows


    def p2p_target_category():
        value = clean(
            doc.get("target_category") or
            doc.get("shift_client_to_category") or
            doc.get("conversion_category") or
            doc.get("new_category") or
            doc.get("category")
        )
        mapping = {
            "All": "All Healthcare Service Units - LSACPL",
            "All Healthcare Service Units": "All Healthcare Service Units - LSACPL",
            "Darmat": "Darmat - LSACPL",
            "Dermat": "Darmat - LSACPL",
            "Hair": "Hair - LSACPL",
            "Laser": "Laser - LSACPL",
            "Physiotherapy": "Physiotherapy - LSACPL",
            "Skin": "Skin - LSACPL",
            "Slimming": "Slimming - LSACPL",
            "LifeRise": "LifeRise - LSACPL",
            "HT": "HT - LSACPL"
        }
        if value in mapping:
            return mapping[value]
        if value:
            return value
        if int(doc.get("skin") or 0):
            return "Skin - LSACPL"
        if int(doc.get("hair") or 0):
            return "Hair - LSACPL"
        if int(doc.get("laser") or 0):
            return "Laser - LSACPL"
        if int(doc.get("slimming") or 0):
            return "Slimming - LSACPL"
        if int(doc.get("cs") or 0):
            return "LifeRise - LSACPL"
        if int(doc.get("ht") or 0):
            return "HT - LSACPL"
        return ""


    def validate_p2p_therapy(therapy, target_category):
        therapy = clean(therapy)
        if not therapy:
            frappe.throw("Therapy Type is required in the final package table.")

        row = frappe.db.get_value(
            "Therapy Type",
            therapy,
            ["name", "therapy_type", "healthcare_service_unit", "disabled"],
            as_dict=1
        )
        if not row:
            found = frappe.get_all(
                "Therapy Type",
                filters={"therapy_type": therapy},
                fields=["name", "therapy_type", "healthcare_service_unit", "disabled"],
                limit_page_length=1
            )
            row = found[0] if found else None
        if not row:
            frappe.throw("Therapy Type does not exist: " + therapy)
        if int(row.get("disabled") or 0):
            frappe.throw("Therapy Type is disabled: " + clean(row.get("name")))

        unit = clean(row.get("healthcare_service_unit"))
        if target_category and target_category != "All Healthcare Service Units - LSACPL" and unit != target_category:
            frappe.throw("Therapy Type " + clean(row.get("name")) + " belongs to " + (unit or "blank category") + ". Only " + target_category + " is allowed.")
        return clean(row.get("name"))


    def p2p_snapshot_rows(rows):
        out = []
        for row in rows:
            therapy = clean(row.get("therapy_type"))
            qty = int(float(row.get("qty") or 0))
            completed = int(float(row.get("completed") or 0))
            amount = round(float(row.get("amount") or 0), 2)
            applied = max(qty - completed, 0)
            rate = amount / applied if applied > 0 else 0
            out.append({
                "therapy_type": therapy,
                "no_of_sessions": qty,
                "sessions_completed": completed,
                "rate": round(rate, 2),
                "amount": amount,
                "source_row_name": clean(row.get("source_row_name") or row.get("name"))
            })
        return out


    def p2p_active_rows(rows):
        out = []
        target_category = p2p_target_category()
        if not target_category:
            frappe.throw("Target category is missing. Approval cannot be completed.")

        seen = []
        for idx, row in enumerate(rows):
            therapy = validate_p2p_therapy(row.get("therapy_type"), target_category)
            qty = int(float(row.get("qty") or 0))
            completed = int(float(row.get("completed") or 0))
            amount = round(float(row.get("amount") or 0), 2)

            if qty <= 0:
                frappe.throw("Row " + str(idx + 1) + ": Sessions must be greater than 0.")
            if qty < completed:
                frappe.throw("Row " + str(idx + 1) + ": Sessions cannot be below completed sessions.")
            if amount < 0:
                frappe.throw("Row " + str(idx + 1) + ": Amount cannot be negative.")
            if therapy in seen:
                frappe.throw("Duplicate Therapy Type found: " + therapy)
            seen.append(therapy)

            applied = max(qty - completed, 0)
            rate = amount / applied if applied > 0 else 0
            out.append({
                "therapy_type": therapy,
                "qty": qty,
                "completed": completed,
                "amount": amount,
                "rate": rate,
                "source_row_name": clean(row.get("source_row_name")),
                "source_plan": clean(row.get("source_plan"))
            })
        if not out:
            frappe.throw("Final package table must contain at least one Therapy Type.")
        return out


    def apply_p2p_table(role, rows, edit_reason):
        normalized = p2p_active_rows(rows)

        # Change detection must compare against the exact CURRENT package table that
        # was presented to the approver in the modal. Comparing against older
        # Branch/Audit snapshots can falsely mark an unchanged table as edited.
        previous = []
        for x in doc.get("converted_package__service_name") or []:
            previous.append({
                "therapy_type": clean(x.get("converted_package__service_name") or x.get("therapy_type")),
                "qty": int(float(x.get("converted_quantity") or x.get("no_of_sessions") or 0)),
                "completed": int(float(x.get("completed_sessions") or x.get("sessions_completed") or 0)),
                "amount": round(float(x.get("balance_amount") or x.get("amount") or x.get("total_amount") or 0), 2)
            })

        compact = []
        for x in normalized:
            compact.append({
                "therapy_type": x.get("therapy_type"),
                "qty": x.get("qty"),
                "completed": x.get("completed"),
                "amount": round(float(x.get("amount") or 0), 2)
            })

        changed = json.dumps(previous, sort_keys=True) != json.dumps(compact, sort_keys=True)
        if changed and not clean(edit_reason):
            frappe.throw("Reason for editing the final package table is required.")

        # Preserve Branch snapshot for older requests before Audit acts.
        if role == "ops" and has_field("branch_requested_package") and not (doc.get("branch_requested_package") or []):
            doc.set("branch_requested_package", [])
            for x in previous:
                applied = max(int(x.get("qty") or 0) - int(x.get("completed") or 0), 0)
                rate = float(x.get("amount") or 0) / applied if applied > 0 else 0
                doc.append("branch_requested_package", {
                    "therapy_type": x.get("therapy_type"),
                    "no_of_sessions": x.get("qty"),
                    "sessions_completed": x.get("completed"),
                    "rate": round(rate, 2),
                    "amount": x.get("amount"),
                    "source_row_name": ""
                })

        if role == "ops" and has_field("audit_team_requested_package"):
            doc.set("audit_team_requested_package", [])
            for x in normalized:
                doc.append("audit_team_requested_package", {
                    "therapy_type": x.get("therapy_type"),
                    "no_of_sessions": x.get("qty"),
                    "sessions_completed": x.get("completed"),
                    "rate": round(float(x.get("rate") or 0), 2),
                    "amount": round(float(x.get("amount") or 0), 2),
                    "source_row_name": x.get("source_row_name")
                })
            set_if("audit_team_package_edited", 1 if changed else 0)
            set_if("audit_table_edit_remarks", clean(edit_reason) if changed else "")

        if role == "coo" and has_field("coo_management_final_package"):
            doc.set("coo_management_final_package", [])
            for x in normalized:
                doc.append("coo_management_final_package", {
                    "therapy_type": x.get("therapy_type"),
                    "no_of_sessions": x.get("qty"),
                    "sessions_completed": x.get("completed"),
                    "rate": round(float(x.get("rate") or 0), 2),
                    "amount": round(float(x.get("amount") or 0), 2),
                    "source_row_name": x.get("source_row_name")
                })
            set_if("coo_management_package_edited", 1 if changed else 0)
            set_if("coo_table_edit_remarks", clean(edit_reason) if changed else "")

        doc.set("converted_package__service_name", [])
        total = 0
        for x in normalized:
            total += float(x.get("amount") or 0)
            applied = max(int(x.get("qty") or 0) - int(x.get("completed") or 0), 0)
            rate = float(x.get("amount") or 0) / applied if applied > 0 else 0
            doc.append("converted_package__service_name", {
                "converted_package__service_name": x.get("therapy_type"),
                "service_package_name": x.get("therapy_type"),
                "therapy_type": x.get("therapy_type"),
                "service_name": x.get("therapy_type"),
                "package_name": x.get("therapy_type"),
                "converted_quantity": x.get("qty"),
                "no_of_sessions": x.get("qty"),
                "quantity": x.get("qty"),
                "completed_sessions": x.get("completed"),
                "sessions_completed": x.get("completed"),
                "availed_quantity": x.get("completed"),
                "applied_sessions": applied,
                "balance_quantity": applied,
                "rate": rate,
                "price": rate,
                "balance_amount": round(float(x.get("amount") or 0), 2),
                "amount": round(float(x.get("amount") or 0), 2),
                "total_amount": round(float(x.get("amount") or 0), 2),
                "source_row_name": x.get("source_row_name"),
                "source_plan": x.get("source_plan")
            })

        set_if("new_package_total_price_rs", round(total, 2))
        available = float(doc.get("current_package__residual__balance_value_rs") or 0)
        override_amount = max(round(total - available, 2), 0)
        set_if("approval_override_amount", override_amount)
        if changed:
            set_if("final_table_edited_during_approval", 1)
            set_if("final_table_edited_stage", "COO / Management Approval" if role == "coo" else "Audit Team Approval")
            set_if("final_table_edited_by", user)
            set_if("final_table_edited_on", frappe.utils.now_datetime())


    def normalize_c2c_rows(rows):
        out = []
        seen = []
        for idx, row in enumerate(rows):
            # C2C intentionally stores the display value as:
            #   Therapy Type (HLC-THP-xxxx)
            # while source_therapy_plan stores the Therapy Plan separately.
            # Validate only the Therapy Type portion, but preserve the combined
            # display value when writing the child table back.
            therapy_label = clean(row.get("therapy_type") or row.get("therapy_plans_been_transferred"))
            source_plan = clean(row.get("source_therapy_plan"))
            qty = float(row.get("qty") or row.get("converted_quantity") or 0)
            amount = round(float(row.get("amount") or row.get("total_amount") or row.get("balance_quantity_amount") or 0), 2)

            if not therapy_label:
                frappe.throw("Row " + str(idx + 1) + ": Therapy Type is required.")

            therapy_lookup = therapy_label
            embedded_plan = ""

            # Detect only a final Therapy Plan suffix. This does not disturb
            # Therapy Type names that legitimately contain parentheses, e.g.
            # "Inch Loss Gel Wrap (papaya)".
            suffix_pos = therapy_label.rfind(" (")
            if suffix_pos > 0 and therapy_label.endswith(")"):
                possible_plan = clean(therapy_label[suffix_pos + 2:-1])
                if possible_plan.upper().startswith("HLC-THP-"):
                    embedded_plan = possible_plan
                    therapy_lookup = clean(therapy_label[:suffix_pos])

            if embedded_plan:
                if source_plan and source_plan != embedded_plan:
                    frappe.throw(
                        "Row " + str(idx + 1) +
                        ": Therapy Plan mismatch. Display value has " + embedded_plan +
                        " but source Therapy Plan is " + source_plan + "."
                    )
                if not source_plan:
                    source_plan = embedded_plan

            therapy_row = frappe.db.get_value(
                "Therapy Type",
                therapy_lookup,
                ["name", "disabled"],
                as_dict=1
            )
            if not therapy_row:
                found_therapy = frappe.get_all(
                    "Therapy Type",
                    filters={"therapy_type": therapy_lookup},
                    fields=["name", "disabled"],
                    limit_page_length=1
                )
                therapy_row = found_therapy[0] if found_therapy else None

            if not therapy_row:
                frappe.throw(
                    "Row " + str(idx + 1) +
                    ": Therapy Type does not exist: " + therapy_lookup
                )
            if int(therapy_row.get("disabled") or 0):
                frappe.throw(
                    "Row " + str(idx + 1) +
                    ": Therapy Type is disabled: " + clean(therapy_row.get("name"))
                )

            therapy_name = clean(therapy_row.get("name"))
            therapy_display = (
                therapy_name + " (" + source_plan + ")"
                if source_plan else therapy_name
            )

            if qty <= 0 or int(qty) != qty:
                frappe.throw("Row " + str(idx + 1) + ": Sessions must be a whole number greater than 0.")
            if amount < 0:
                frappe.throw("Row " + str(idx + 1) + ": Amount cannot be negative.")

            source_key = clean(row.get("source_therapy_row_name"))
            duplicate_key = (
                "SOURCE::" + source_key
                if source_key else "OVERRIDE::" + lower(therapy_display)
            )
            if duplicate_key in seen:
                frappe.throw("Duplicate final-table row found: " + therapy_display)
            seen.append(duplicate_key)

            source_before = float(row.get("source_sessions_before") or 0)
            source_completed = float(row.get("source_completed_before") or 0)
            source_balance = float(
                row.get("source_balance_before") or
                row.get("original_balance_quantity") or
                row.get("max_quantity") or
                max(source_before - source_completed, 0)
            )
            has_source = bool(source_key)
            deduct = min(qty, max(source_balance, 0)) if has_source else 0
            source_after = max(source_before - deduct, source_completed) if has_source else 0
            balance_after = max(source_after - source_completed, 0) if has_source else 0
            unit = amount / qty if qty > 0 else 0

            out.append({
                "therapy_plans_been_transferred": therapy_display,
                "converted_quantity": int(qty),
                "original_balance_quantity": float(row.get("original_balance_quantity") or row.get("max_quantity") or source_balance or 0),
                "max_quantity": float(row.get("max_quantity") or row.get("original_balance_quantity") or source_balance or 0),
                "start_date": clean(row.get("start_date")),
                "validity_exp_dt": clean(row.get("validity_exp_dt")),
                "total_amount": amount,
                "balance_quantity_amount": amount,
                "balance_due": float(row.get("balance_due") or 0),
                "unit_transfer_amount": unit,
                "unit_outstanding_amount": float(row.get("unit_outstanding_amount") or 0),
                "source_therapy_plan": source_plan,
                "source_therapy_row_name": source_key,
                "source_invoice": clean(row.get("source_invoice")),
                "source_sessions_before": source_before if has_source else 0,
                "source_completed_before": source_completed if has_source else 0,
                "source_balance_before": source_balance if has_source else 0,
                "source_sessions_after": source_after if has_source else 0,
                "source_balance_after": balance_after if has_source else 0
            })

        if not out:
            frappe.throw("At least one Therapy Type must remain in the final transfer table.")
        return out


    def apply_c2c_table(role, rows, edit_reason):
        normalized = normalize_c2c_rows(rows)
        current = []
        for row in doc.get("remaining_sessions_package_details") or []:
            current.append({
                "therapy_plans_been_transferred": clean(row.get("therapy_plans_been_transferred")),
                "converted_quantity": int(float(row.get("converted_quantity") or 0)),
                "total_amount": round(float(row.get("total_amount") or row.get("balance_quantity_amount") or 0), 2),
                "source_therapy_row_name": clean(row.get("source_therapy_row_name"))
            })
        compact = []
        for row in normalized:
            compact.append({
                "therapy_plans_been_transferred": row.get("therapy_plans_been_transferred"),
                "converted_quantity": row.get("converted_quantity"),
                "total_amount": row.get("total_amount"),
                "source_therapy_row_name": row.get("source_therapy_row_name")
            })
        changed = json.dumps(current, sort_keys=True) != json.dumps(compact, sort_keys=True)
        if changed and not clean(edit_reason):
            frappe.throw("Reason for editing the final transfer table is required.")

        if has_field("custom_branch_requested_transfer_snapshot") and not clean(doc.get("custom_branch_requested_transfer_snapshot")):
            set_if("custom_branch_requested_transfer_snapshot", json.dumps(current, sort_keys=True))

        if role == "audit_team":
            set_if("custom_audit_approved_transfer_snapshot", json.dumps(normalized, sort_keys=True))
            set_if("custom_audit_transfer_table_edited", 1 if changed else 0)
            set_if("custom_audit_table_edit_remarks", clean(edit_reason) if changed else "")
        elif role == "operations_coo":
            set_if("custom_coo_final_transfer_snapshot", json.dumps(normalized, sort_keys=True))
            set_if("custom_coo_transfer_table_edited", 1 if changed else 0)
            set_if("custom_coo_table_edit_remarks", clean(edit_reason) if changed else "")

        if changed:
            set_if("custom_final_transfer_table_edited_stage", "Audit Team" if role == "audit_team" else "COO / Management")
            set_if("custom_final_transfer_table_edited_by", user)
            set_if("custom_final_transfer_table_edited_on", frappe.utils.now_datetime())

        doc.set("remaining_sessions_package_details", [])
        for row in normalized:
            doc.append("remaining_sessions_package_details", row)


    # ---------------------------------------------------------------------------
    # B2B final branch updater
    # ---------------------------------------------------------------------------
    def resolve_b2b_patient_name():
        # IMPORTANT:
        # Mirror the original B2B web page exactly:
        # client_full_name -> client_id__crm_no -> client.
        # Some live requests contain different values in these three fields.
        candidates = [
            clean(doc.get("client_full_name")),
            clean(doc.get("client_id__crm_no")),
            clean(doc.get("client"))
        ]

        unique_candidates = []
        for candidate in candidates:
            if candidate and candidate not in unique_candidates:
                unique_candidates.append(candidate)

        # First prefer an exact Patient document name.
        for candidate in unique_candidates:
            if frappe.db.exists("Patient", candidate):
                return candidate

        # Legacy fallback: match the Patient display name in the same priority order.
        for candidate in unique_candidates:
            found = frappe.get_all(
                "Patient",
                filters={"patient_name": candidate},
                fields=["name"],
                limit_page_length=2
            )
            if len(found) == 1:
                return clean(found[0].get("name"))

        return ""


    def apply_b2b_branch_transfer():
        target_branch = clean(doc.get("transfer_to_branch"))
        patient_name = resolve_b2b_patient_name()

        if not target_branch:
            frappe.throw("Transfer To Branch is missing. Cannot update Patient / Therapy Plan branch.")
        if not patient_name:
            frappe.throw(
                "Unable to resolve the Patient record for this B2B request. "
                "Checked Client Full Name, Client ID / CRM No and Client."
            )

        patient = frappe.get_doc("Patient", patient_name)

        # Same target fields as the original B2B page.
        if patient.meta.has_field("branch_name"):
            patient.set("branch_name", target_branch)
        if patient.meta.has_field("custom_branch"):
            patient.set("custom_branch", target_branch)

        child_field = ""
        if patient.meta.has_field("custom_brnch_list"):
            child_field = "custom_brnch_list"
        elif patient.meta.has_field("custom_branch_list"):
            child_field = "custom_branch_list"

        child_row_added = 0
        if child_field:
            exists = False
            for row in patient.get(child_field) or []:
                if clean(row.get("branch")) == target_branch:
                    exists = True
                    break

            if not exists:
                child_meta = frappe.get_meta(patient.meta.get_field(child_field).options)
                child_data = {"branch": target_branch}

                if child_meta.has_field("transfer_date"):
                    child_data["transfer_date"] = frappe.utils.today()
                if child_meta.has_field("remarks"):
                    child_data["remarks"] = (
                        "Branch updated through Client Transfer Request " + doc.name
                    )

                patient.append(child_field, child_data)
                child_row_added = 1

        # Save the Patient normally for mandatory-field validation; only permission
        # checks are bypassed because this is a controlled final B2B approval action.
        patient.flags.ignore_permissions = True
        patient.save()

        # Mirror original B2B page: update every Therapy Plan belonging to this Patient.
        plans = frappe.get_all(
            "Therapy Plan",
            filters={"patient": patient_name},
            fields=["name"],
            limit_page_length=500
        )

        updated = 0
        updated_plan_names = []
        tp_meta = frappe.get_meta("Therapy Plan")

        if tp_meta.has_field("custom_transfer_branch"):
            for plan in plans:
                pname = clean(plan.get("name"))
                if pname:
                    frappe.db.set_value(
                        "Therapy Plan",
                        pname,
                        "custom_transfer_branch",
                        target_branch,
                        update_modified=True
                    )
                    updated += 1
                    if len(updated_plan_names) < 25:
                        updated_plan_names.append(pname)

        # Read-back verification so a successful API response means the target
        # documents actually contain the intended values.
        patient_after = frappe.db.get_value(
            "Patient",
            patient_name,
            ["branch_name", "custom_branch"],
            as_dict=True
        ) or {}

        verified_patient_branch = clean(
            patient_after.get("branch_name") or patient_after.get("custom_branch")
        )

        if verified_patient_branch != target_branch:
            frappe.throw(
                "B2B final approval was saved, but Patient branch verification failed. "
                "Expected '" + target_branch + "', found '" + verified_patient_branch + "'."
            )

        mismatched_plans = []
        if tp_meta.has_field("custom_transfer_branch"):
            for plan in plans:
                pname = clean(plan.get("name"))
                if not pname:
                    continue
                actual = clean(
                    frappe.db.get_value(
                        "Therapy Plan",
                        pname,
                        "custom_transfer_branch"
                    )
                )
                if actual != target_branch:
                    mismatched_plans.append(pname)

        if mismatched_plans:
            frappe.throw(
                "Patient branch was updated, but some Therapy Plans were not updated: " +
                ", ".join(mismatched_plans[:10])
            )

        return {
            "patient": patient_name,
            "branch": target_branch,
            "patient_branch_verified": verified_patient_branch,
            "branch_history_row_added": child_row_added,
            "therapy_plans_found": len(plans),
            "therapy_plans_updated": updated,
            "therapy_plan_names": updated_plan_names
        }



    # My Approvals is a personal stage queue, not the administrator override queue.
    # Keep existing action permissions unchanged; expose a narrower queue decision.
    def personal_queue_context(ctx):
        mode = clean(ctx.get("mode"))
        if mode == "p2p":
            audit_users = P2P_AUDIT_USERS
            coo_users = P2P_COO_USERS
        elif mode == "c2c":
            audit_users = C2C_AUDIT_USERS
            coo_users = C2C_COO_USERS
        else:
            audit_users = B2B_AUDIT_USERS
            coo_users = B2B_COO_USERS
        level = ""
        if user_key in coo_users:
            level = "coo"
        elif user_key in audit_users:
            level = "audit"
        elif login_employee and user_can_access_branch(ctx.get("branch")):
            for manager in active_manager_rows(ctx.get("branch"), mode):
                if clean(manager.get("name")) == clean(login_employee.get("name")):
                    level = "manager"
                    break
        pending = clean(ctx.get("pending_role"))
        expected = "coo" if pending in ["coo", "operations_coo"] else "audit" if pending in ["ops", "audit_team", "audit"] else "manager" if pending in ["cm", "centre_manager", "manager"] else ""
        ctx["my_approval_level"] = level
        ctx["my_queue_can_act"] = 1 if level and level == expected and int(ctx.get("can_act") or 0) else 0
        return ctx

    ctx = personal_queue_context(resolve_context())

    if operation == "repair_b2b":
        if doctype != "Client Transfer Request Form":
            frappe.throw("repair_b2b is available only for Client Transfer Request Form.")

        if not (is_system_manager or user_key in B2B_COO_USERS):
            frappe.throw("Only an authorised COO / Management user can re-apply a completed B2B branch transfer.")

        if lower(doc.get("final_approval_status")) != "approved":
            frappe.throw("This B2B request is not finally approved.")

        repair_result = apply_b2b_branch_transfer()

        frappe.response["message"] = {
            "ok": 1,
            "operation": "repair_b2b",
            "doctype": doctype,
            "docname": doc.name,
            "branch_update": repair_result
        }

    elif operation == "context":
        ctx["user"] = user
        ctx["user_full_name"] = user_full_name
        frappe.response["message"] = ctx
    else:
        if operation != "action":
            frappe.throw("Invalid operation.")

        # Re-resolved immediately before write.
        if not int(ctx.get("can_act") or 0):
            frappe.throw(ctx.get("reason") or "You are not allowed to act on this request.")

        action_raw = clean(frappe.form_dict.get("action"))
        action_key = lower(action_raw)
        if action_key in ["approve", "approved"]:
            is_approve = True
        elif action_key in ["reject", "rejected"]:
            is_approve = False
        else:
            frappe.throw("Action must be Approve or Reject.")

        remarks = clean(frappe.form_dict.get("remarks"))
        signature = clean(frappe.form_dict.get("signature"))
        manager_employee_id = clean(frappe.form_dict.get("approver_employee"))
        edit_reason = clean(frappe.form_dict.get("table_edit_reason"))

        if is_approve and int(ctx.get("remarks_required_for_approve") or 0) and not remarks:
            frappe.throw("Approval remarks are required.")
        if (not is_approve) and int(ctx.get("remarks_required_for_reject") or 0) and not remarks:
            frappe.throw("Rejection remarks are required.")
        if int(ctx.get("require_signature") or 0):
            if not signature or not signature.startswith("data:image"):
                frappe.throw("Signature is required before saving this decision.")

        now_dt = frappe.utils.now_datetime()
        today = frappe.utils.today()
        branch_update_result = None
        run_p2p_final_automation = 0
        next_step = 0

        # -----------------------------------------------------------------------
        # P2P
        # -----------------------------------------------------------------------
        if doctype == "LIFE Client Package Conversion Same Client Package To Package":
            role = ctx.get("pending_role")
            role_label = ctx.get("role_label")
            approver_name = ctx.get("approver_name") or user_full_name

            if role == "cm":
                manager = validate_manager_employee(manager_employee_id, ctx.get("branch"), "p2p")
                approver_name = clean(manager.get("employee_name") or manager.get("name"))
            elif role == "ops":
                approver_name = P2P_AUDIT_USERS.get(user_key) or user_full_name
            elif role == "coo":
                approver_name = P2P_COO_USERS.get(user_key) or user_full_name

            if is_approve and role in ["ops", "coo"]:
                incoming_rows = parse_table_rows()
                if incoming_rows:
                    apply_p2p_table(role, incoming_rows, edit_reason)

            if is_approve:
                if role == "cm":
                    set_if("current_tab_step", 3)
                    set_if("approval_stage", "Audit Team Approval Pending")
                    set_if("approval_display_status", "Audit Team Approval Pending")
                    set_if("final_approval_status", "")
                    set_if("automation_status", "Pending Final Approval")
                    set_if("approved_by_name", approver_name)
                    set_if("approved_date", now_dt)
                    set_if("centre_manager_remarks", remarks)
                    set_if("approved_remarks", remarks)
                    next_step = 3
                elif role == "ops":
                    set_if("current_tab_step", 4)
                    set_if("approval_stage", "COO / Management Approval Pending")
                    set_if("approval_display_status", "COO / Management Approval Pending")
                    set_if("final_approval_status", "")
                    set_if("automation_status", "Pending Final Approval")
                    set_if("operations_final_remarks", remarks)
                    set_if("authorised_date", now_dt)
                    set_if("authorised_name", approver_name)
                    next_step = 4
                elif role == "coo":
                    set_if("current_tab_step", 5)
                    set_if("approval_stage", "Approved")
                    set_if("approval_display_status", "Approved / Pending Therapy Plan Update")
                    set_if("final_approval_status", "Approved")
                    set_if("automation_status", "Pending Final Approval")
                    set_if("coo_management_remarks", remarks)
                    set_if("coo_management_date", now_dt)
                    set_if("coo_management_name", approver_name)
                    run_p2p_final_automation = 1
                    next_step = 5
            else:
                set_if("current_tab_step", 5)
                set_if("approval_stage", "Rejected")
                set_if("final_approval_status", "Rejected")
                set_if("automation_status", "Skipped")
                set_if("approval_display_status", role_label + " Rejected")
                if role == "cm":
                    set_if("approved_by_name", approver_name)
                    set_if("approved_date", now_dt)
                    set_if("centre_manager_remarks", remarks)
                    set_if("approved_remarks", remarks)
                elif role == "ops":
                    set_if("operations_final_remarks", remarks)
                    set_if("authorised_date", now_dt)
                    set_if("authorised_name", approver_name)
                elif role == "coo":
                    set_if("coo_management_remarks", remarks)
                    set_if("coo_management_date", now_dt)
                    set_if("coo_management_name", approver_name)

        # -----------------------------------------------------------------------
        # C2C
        # -----------------------------------------------------------------------
        elif doctype == "Client Package Conversion Client To Client":
            role = ctx.get("pending_role")
            approver_name = ctx.get("approver_name") or user_full_name
            approver_id = user

            if role == "centre_manager":
                manager = validate_manager_employee(manager_employee_id, ctx.get("branch"), "c2c")
                approver_name = clean(manager.get("employee_name") or manager.get("name"))
                approver_id = clean(manager.get("name"))
            elif role == "audit_team":
                approver_name = C2C_AUDIT_USERS.get(user_key) or user_full_name
                approver_id = user
            elif role == "operations_coo":
                approver_name = C2C_COO_USERS.get(user_key) or user_full_name
                approver_id = approver_name

            if is_approve and role in ["audit_team", "operations_coo"]:
                incoming_rows = parse_table_rows()
                if incoming_rows:
                    apply_c2c_table(role, incoming_rows, edit_reason)

            if role == "centre_manager":
                set_if("centre_manager_name", approver_id)
                set_if("centre_manager_date", today)
                set_if("centre_manager_remarks", remarks)
                set_if("centre_manager_decision", "Approved" if is_approve else "Rejected")
                set_if("custom_centre_manager_action_datetime", now_dt)
                if is_approve:
                    set_if("current_tab_step", 3)
                    set_if("approval_stage", "Audit Team Approval Pending")
                    set_if("approval_display_status", "Audit Team Approval Pending")
                    set_if("final_approval_status", "")
                    set_if("automation_status", "Pending Final Approval")
                    next_step = 3
                else:
                    set_if("rejected_by_role", "Centre Manager")
                    set_if("rejected_by_name", approver_name)
                    set_if("rejection_remarks", remarks)
                    set_if("current_tab_step", 2)
                    set_if("approval_stage", "Rejected")
                    set_if("approval_display_status", "Centre Manager Rejected / Process Stopped")
                    set_if("final_approval_status", "Rejected")
                    set_if("conversion_status", "Rejected")
                    set_if("automation_status", "Skipped")
            elif role == "audit_team":
                set_if("audit_team__corporate_team_name", approver_id)
                set_if("audit_team__corporate_team_date", today)
                set_if("audit_team_remarks", remarks)
                set_if("audit_team_decision", "Approved" if is_approve else "Rejected")
                set_if("custom_audit_team_action_datetime", now_dt)
                if is_approve:
                    set_if("current_tab_step", 3)
                    set_if("approval_stage", "Operations COO Final Decision Pending")
                    set_if("approval_display_status", "Operations COO Final Decision Pending")
                    set_if("final_approval_status", "")
                    set_if("automation_status", "Pending Final Approval")
                    next_step = 4
                else:
                    set_if("rejected_by_role", "Audit Team / Corporate Team")
                    set_if("rejected_by_name", approver_name)
                    set_if("rejection_remarks", remarks)
                    set_if("current_tab_step", 3)
                    set_if("approval_stage", "Rejected")
                    set_if("approval_display_status", "Audit Team Rejected / Process Stopped")
                    set_if("final_approval_status", "Rejected")
                    set_if("conversion_status", "Rejected")
                    set_if("automation_status", "Skipped")
            elif role == "operations_coo":
                set_if("operations_coo__management_name", approver_name)
                set_if("operations_coo__management_date", today)
                set_if("office_remarks_any", remarks)
                set_if("custom_coo_management_action_datetime", now_dt)
                set_if("current_tab_step", 4)
                if is_approve:
                    set_if("approval_stage", "Approved")
                    set_if("final_approval_status", "Approved")
                    set_if("approval_display_status", "Approved / Pending Package Transfer")
                    set_if("automation_status", "Pending Final Approval")
                    set_if("conversion_status", "Approved")
                    next_step = 4
                else:
                    set_if("approval_stage", "Rejected")
                    set_if("final_approval_status", "Rejected")
                    set_if("approval_display_status", "Rejected / Skipped")
                    set_if("automation_status", "Skipped")
                    set_if("conversion_status", "Rejected")
                    set_if("rejected_by_role", "Operations COO / Management")
                    set_if("rejected_by_name", approver_name)
                    set_if("rejection_remarks", remarks)

        # -----------------------------------------------------------------------
        # B2B
        # -----------------------------------------------------------------------
        else:
            role = ctx.get("pending_role")
            approver_name = ctx.get("approver_name") or user_full_name

            if len(remarks.split()) > 100:
                frappe.throw("Approval remarks should be within 100 words.")

            if role == "manager":
                manager = validate_manager_employee(manager_employee_id, ctx.get("branch"), "b2b")
                approver_name = clean(manager.get("employee_name") or manager.get("name"))
                manager_id = clean(manager.get("name"))
                set_if("branch_manager_id", manager_id)
                set_if("cmname", approver_name)
                set_if("cmreason", remarks)
                set_if("cmsignature", signature)
                set_if("cmdate", today)
                if is_approve:
                    set_if("current_tab_step", 6)
                    set_if("approval_display_status", "Audit Team Approval Pending")
                    set_if("audit_status", "Pending")
                    set_if("final_approval_status", "Pending")
                    set_if("remarks", "Audit Team Approval Pending")
                    next_step = 6
                else:
                    set_if("current_tab_step", 5)
                    set_if("approval_display_status", "Branch Manager Rejected")
                    set_if("audit_status", "Rejected")
                    set_if("final_approval_status", "Rejected")
                    set_if("remarks", "Branch Manager Rejected")
            elif role == "audit":
                if lower(doc.get("audit_status")) not in ["pending", ""] and clean(doc.get("audit_status")):
                    frappe.throw("This request is no longer pending Audit approval.")
                if not clean(doc.get("cmname")):
                    frappe.throw("Branch Manager approval is required before Audit approval.")
                approver_name = B2B_AUDIT_USERS.get(user_key) or user_full_name
                set_if("audit_status", "Approved" if is_approve else "Rejected")
                set_if("audit_verified_by", approver_name)
                set_if("audit_verified_date", today)
                set_if("audit_remarks", remarks)
                set_if("audit_signature", signature)
                if is_approve:
                    set_if("current_tab_step", 7)
                    set_if("approval_display_status", "COO / Management Approval Pending")
                    set_if("final_approval_status", "Pending")
                    set_if("remarks", "COO / Management Approval Pending")
                    next_step = 7
                else:
                    set_if("current_tab_step", 6)
                    set_if("approval_display_status", "Audit Team Rejected")
                    set_if("final_approval_status", "Rejected")
                    set_if("remarks", "Audit Team Rejected")
            elif role == "coo":
                if lower(doc.get("audit_status")) != "approved":
                    frappe.throw("Audit Team approval is required before COO / Management approval.")
                approver_name = B2B_COO_USERS.get(user_key) or user_full_name
                set_if("current_tab_step", 7)
                set_if("approval_display_status", "Approved / Transfer Completed" if is_approve else "COO / Management Rejected")
                set_if("final_approval_status", "Approved" if is_approve else "Rejected")
                set_if("final_approval_by", approver_name)
                set_if("final_approval_date", frappe.utils.now())
                set_if("final_approval_remarks", remarks)
                set_if("final_approval_signature", signature)
                set_if("remarks", "Approved / Transfer Completed" if is_approve else "COO / Management Rejected")

        doc.flags.ignore_permissions = True
        doc.save()

        if doctype == "Client Transfer Request Form" and ctx.get("pending_role") == "coo" and is_approve:
            branch_update_result = apply_b2b_branch_transfer()

        frappe.response["message"] = {
            "ok": 1,
            "doctype": doctype,
            "docname": doc.name,
            "action": "Approved" if is_approve else "Rejected",
            "role": ctx.get("pending_role"),
            "role_label": ctx.get("role_label"),
            "approved_by": ctx.get("approver_name") or user_full_name,
            "next_step": next_step,
            "run_p2p_final_automation": run_p2p_final_automation,
            "branch_update": branch_update_result
        }
