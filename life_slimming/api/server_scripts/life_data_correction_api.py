"""LIFE Data Correction API

Original API: life_data_correction_api
Source modified: 2026-09-20 20:07:11.984558
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
    # LIFE DATA CORRECTION API
    # P2P STYLE REQUEST + APPROVAL ENGINE
    # ============================================================

    action = str(
        frappe.form_dict.get("action") or "bootstrap"
    ).strip()

    current_user = str(
        frappe.session.user or ""
    ).strip()


    # ============================================================
    # DATA CORRECTION SUPER APPROVERS
    # ============================================================
    # These users can approve/reject ANY currently pending request,
    # regardless of branch or required approval role.
    #
    # They still act on the CURRENT pending stage only, so the
    # approval sequence and audit trail remain intact.
    # ============================================================

    DCR_ADMIN_USERS = [
        "Administrator",
        "lokakavyareddy3@gmail.com",
        "yaswanthkumaryy1234@gmail.com",
        "narendhar@lifescc.com"
    ]


    def is_dcr_admin():
        return current_user in DCR_ADMIN_USERS


    # ============================================================
    # HELPERS
    # ============================================================

    def clean(value):
        if value is None:
            return ""
        return str(value).strip()


    def to_int(value):
        try:
            return int(float(value or 0))
        except Exception:
            return 0


    def json_value(value, fallback):

        if value is None:
            return fallback

        # Already parsed by Frappe
        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            return value

        # Sometimes Frappe FormDict wraps list/dict data
        try:
            if hasattr(value, "as_dict"):
                return value.as_dict()
        except Exception:
            pass

        # JSON string fallback
        try:
            parsed = frappe.parse_json(value)

            if parsed is not None:
                return parsed

        except Exception:
            pass

        return fallback


    def get_user_roles():

        rows = frappe.get_all(
            "Has Role",
            filters={
                "parent": current_user,
                "parenttype": "User"
            },
            fields=["role"],
            limit_page_length=500
        )

        out = []

        for row in rows:
            role = clean(row.get("role"))

            if role and role not in out:
                out.append(role)

        return out


    def get_employee():

        if not frappe.db.exists("DocType", "Employee"):
            return {}

        meta = frappe.get_meta("Employee")

        employee_name = ""

        if meta.has_field("user_id"):
            employee_name = frappe.db.get_value(
                "Employee",
                {
                    "user_id": current_user,
                    "status": "Active"
                },
                "name"
            ) or ""

        if (
            not employee_name
            and meta.has_field("company_email")
        ):
            employee_name = frappe.db.get_value(
                "Employee",
                {
                    "company_email": current_user,
                    "status": "Active"
                },
                "name"
            ) or ""

        if (
            not employee_name
            and meta.has_field("personal_email")
        ):
            employee_name = frappe.db.get_value(
                "Employee",
                {
                    "personal_email": current_user,
                    "status": "Active"
                },
                "name"
            ) or ""

        if not employee_name:
            return {}

        fields = [
            "name",
            "employee_name",
            "designation",
            "department",
            "branch",
            "user_id",
            "company_email",
            "personal_email"
        ]

        valid_fields = []

        for fieldname in fields:
            if (
                fieldname == "name"
                or meta.has_field(fieldname)
            ):
                valid_fields.append(fieldname)

        return frappe.db.get_value(
            "Employee",
            employee_name,
            valid_fields,
            as_dict=True
        ) or {}


    def get_portal_role():

        if not frappe.db.exists(
            "User",
            current_user
        ):
            return ""

        meta = frappe.get_meta("User")

        if not meta.has_field(
            "custom_portal_role"
        ):
            return ""

        return clean(
            frappe.db.get_value(
                "User",
                current_user,
                "custom_portal_role"
            )
        )


    def resolve_access_role():

        roles = get_user_roles()

        roles_lower = []

        for role in roles:
            roles_lower.append(
                clean(role).lower()
            )

        portal_role = (
            get_portal_role()
            .lower()
        )

        employee = get_employee()

        designation = clean(
            employee.get("designation")
        ).lower()

        # --------------------------------------------
        # Explicit portal roles
        # --------------------------------------------

        if portal_role == "coo":
            return "COO"

        if portal_role == "dceo":
            return "DCEO"

        if portal_role == "audit":
            return "Audit"

        if portal_role == "accounts":
            return "Accounts"

        if portal_role == "hr":
            return "HR"

        if portal_role in [
            "operations",
            "operation",
            "ops"
        ]:
            return "Operations"

        if portal_role in [
            "branch manager",
            "centre manager",
            "center manager"
        ]:
            return "Branch Manager"

        if portal_role == "it":
            return "IT"

        # --------------------------------------------
        # Frappe roles
        # --------------------------------------------

        if "system manager" in roles_lower:
            return "IT"

        if "audit head" in roles_lower:
            return "Audit"

        if (
            "accounts manager" in roles_lower
            or "accounts user" in roles_lower
        ):
            return "Accounts"

        if (
            "hr manager" in roles_lower
            or "hr user" in roles_lower
        ):
            return "HR"

        # --------------------------------------------
        # Employee designation
        # --------------------------------------------

        if designation in [
            "coo",
            "chief operating officer"
        ]:
            return "COO"

        if (
            designation == "dceo"
            or "deputy ceo" in designation
        ):
            return "DCEO"

        if "audit" in designation:
            return "Audit"

        if (
            "operation manager" in designation
            or "operations manager" in designation
            or "operation head" in designation
        ):
            return "Operations"

        if (
            "center manager" in designation
            or "centre manager" in designation
            or "senior manager" in designation
            or "assistant center manager" in designation
            or "assistant centre manager" in designation
        ):
            return "Branch Manager"

        if "account" in designation:
            return "Accounts"

        if (
            designation.startswith("hr")
            or "human resource" in designation
        ):
            return "HR"

        if "it admin" in designation:
            return "IT"

        return "Branch User"


    def get_allowed_branches():

        employee = get_employee()

        branches = []

        primary = clean(
            employee.get("branch")
        )

        if primary:
            branches.append(primary)

        if not employee:
            return branches

        emp_name = clean(
            employee.get("name")
        )

        if not emp_name:
            return branches

        meta = frappe.get_meta("Employee")

        if meta.has_field(
            "custom_employee_branches"
        ):

            field = meta.get_field(
                "custom_employee_branches"
            )

            child_dt = ""

            if field:
                child_dt = clean(field.options)

            if (
                child_dt
                and frappe.db.exists(
                    "DocType",
                    child_dt
                )
            ):

                rows = frappe.get_all(
                    child_dt,
                    filters={
                        "parent": emp_name,
                        "parenttype": "Employee"
                    },
                    fields=["branch"],
                    limit_page_length=200
                )

                for row in rows:
                    branch = clean(
                        row.get("branch")
                    )

                    if (
                        branch
                        and branch not in branches
                    ):
                        branches.append(branch)

        return branches


    def build_context():

        employee = get_employee()

        full_name = frappe.db.get_value(
            "User",
            current_user,
            "full_name"
        ) or ""

        if not full_name:
            full_name = clean(
                employee.get("employee_name")
            )

        if not full_name:
            full_name = current_user

        access_role = resolve_access_role()

        admin_override = is_dcr_admin()

        user_roles_lower = [
            clean(r).lower()
            for r in (get_user_roles() or [])
        ]

        is_system_manager = (
            "system manager" in user_roles_lower
        )

        view_all = (
            admin_override
            or is_system_manager
            or access_role in [
                "Operations",
                "HR",
                "Accounts",
                "Audit",
                "DCEO",
                "COO",
                "IT"
            ]
        )

        return {
            "user": current_user,
            "name": full_name,
            "employee": clean(
                employee.get("name")
            ),
            "employee_name": clean(
                employee.get("employee_name")
            ),
            "designation": clean(
                employee.get("designation")
            ),
            "department": clean(
                employee.get("department")
            ),
            "branch": clean(
                employee.get("branch")
            ),
            "branches": get_allowed_branches(),
            "access_role": access_role,
            "view_all": view_all,
            "is_dcr_admin": admin_override,
            "is_system_manager": is_system_manager,
            "dcr_admin_label": (
                "Data Correction Admin"
                if admin_override else ""
            )
        }


    def validate_branch_access(
        ctx,
        branch
    ):

        if ctx.get("view_all"):
            return

        branch = clean(branch)

        allowed = (
            ctx.get("branches") or []
        )

        if (
            branch
            and branch not in allowed
        ):
            frappe.throw(
                "You do not have access to branch "
                + branch
            )


    def get_rule(rule_name):

        rule_name = clean(rule_name)

        if not rule_name:
            frappe.throw(
                "Correction Rule is required."
            )

        if not frappe.db.exists(
            "LIFE Data Correction Rule",
            rule_name
        ):
            frappe.throw(
                "Correction Rule not found: "
                + rule_name
            )

        rule = frappe.get_doc(
            "LIFE Data Correction Rule",
            rule_name
        )

        if not to_int(rule.enabled):
            frappe.throw(
                "This correction rule is disabled."
            )

        return rule


    def get_source_branch(
        rule,
        source_document
    ):

        doctype = clean(
            rule.source_doctype
        )

        if not doctype:
            return ""

        meta = frappe.get_meta(doctype)

        branch_fields = [
            clean(rule.branch_field),
            "branch",
            "custom_branch",
            "branch_name",
            "custom_transfer_branch"
        ]

        checked = []

        for fieldname in branch_fields:

            if (
                not fieldname
                or fieldname in checked
            ):
                continue

            checked.append(fieldname)

            if meta.has_field(fieldname):

                branch = frappe.db.get_value(
                    doctype,
                    source_document,
                    fieldname
                )

                if branch:
                    return clean(branch)

        return ""


    def build_approval_chain(rule):

        chain = []

        def add_stage(
            enabled,
            stage,
            role
        ):
            if to_int(enabled):
                chain.append({
                    "stage": stage,
                    "required_role": role,
                    "required_access_role": role
                })

        add_stage(
            rule.branch_manager_approval,
            "Branch Manager Approval",
            "Branch Manager"
        )

        add_stage(
            rule.operations_approval,
            "Operations Approval",
            "Operations"
        )

        add_stage(
            rule.hr_approval,
            "HR Approval",
            "HR"
        )

        add_stage(
            rule.accounts_approval,
            "Accounts Approval",
            "Accounts"
        )

        add_stage(
            rule.audit_approval,
            "Audit Approval",
            "Audit"
        )

        add_stage(
            rule.dceo_approval,
            "DCEO Approval",
            "DCEO"
        )

        add_stage(
            rule.coo_approval,
            "COO Approval",
            "COO"
        )

        return chain


    def serialize_request(doc):

        changes = []

        for row in doc.get("changes") or []:

            changes.append({
                "name": row.name,
                "idx": row.idx,
                "field_name": row.field_name,
                "field_label": row.field_label,
                "old_value": row.old_value,
                "requested_value":
                    row.requested_value,
                "approved_value":
                    row.approved_value,
                "value_type":
                    row.value_type,
                "link_doctype":
                    row.link_doctype,
                "fieldtype":
                    row.fieldtype,
                "change_remarks":
                    row.change_remarks
            })

        approvals = []

        for row in doc.get("approvals") or []:

            approvals.append({
                "name": row.name,
                "idx": row.idx,
                "stage": row.stage,
                "stage_no": row.stage_no,
                "required_role":
                    row.required_role,
                "required_access_role":
                    row.required_access_role,
                "approver_user":
                    row.approver_user,
                "approver_employee":
                    row.approver_employee,
                "approver_name":
                    row.approver_name,
                "decision":
                    row.decision,
                "remarks":
                    row.remarks,
                "acted_on":
                    row.acted_on
            })

        return {
            "name": doc.name,
            "requested_by":
                doc.requested_by,
            "requested_by_employee":
                doc.requested_by_employee,
            "requested_by_name":
                doc.requested_by_name,
            "requester_designation":
                doc.requester_designation,
            "branch": doc.branch,
            "requested_on":
                doc.requested_on,
            "category": doc.category,
            "rule": doc.rule,
            "source_doctype":
                doc.source_doctype,
            "source_document":
                doc.source_document,
            "source_display_name":
                doc.source_display_name,
            "reason": doc.reason,

            "attachment_1":
                doc.attachment_1,
            "attachment_2":
                doc.attachment_2,
            "attachment_3":
                doc.attachment_3,

            "status": doc.status,
            "workflow_stage":
                doc.workflow_stage,
            "current_approver_role":
                doc.current_approver_role,
            "current_approver_user":
                doc.current_approver_user,

            "is_on_hold":
                doc.is_on_hold,

            "final_approved_on":
                doc.final_approved_on,
            "final_approved_by":
                doc.final_approved_by,

            "posted_by":
                doc.posted_by,
            "posted_on":
                doc.posted_on,
            "posting_reference":
                doc.posting_reference,
            "posting_remarks":
                doc.posting_remarks,

            "access_role_at_creation":
                doc.access_role_at_creation,

            "source_modified_at_request":
                doc.source_modified_at_request,

            "source_modified_after_request":
                doc.source_modified_after_request,

            "creation": doc.creation,
            "modified": doc.modified,

            "changes": changes,
            "approvals": approvals
        }


    def preflight_link_check(source_meta, field_name, value):
        """
    Return None if the value is acceptable for the field type.
    Return a human-readable string if the value would fail Link validation.
    """
        if value in (None, ""):
            return None

        df = source_meta.get_field(field_name)
        if not df:
            return None

        if df.fieldtype != "Link":
            return None

        link_dt = clean(df.options)
        if not link_dt:
            return None

        # Skip validation for dynamic links
        if link_dt in ("Dynamic Link",):
            return None

        try:
            exists = frappe.db.exists(link_dt, clean(value))
        except Exception:
            # If the target doctype doesn't exist, we can't validate here.
            # Let save() handle it and surface a proper error.
            return None

        if not exists:
            return (
                "Value '" + clean(value) + "' is not a valid "
                + link_dt + " record for field '"
                + (df.label or field_name) + "'."
            )

        return None


    # ============================================================
    # BOOTSTRAP
    # ============================================================

    if action == "bootstrap":

        ctx = build_context()

        rules = frappe.get_all(
            "LIFE Data Correction Rule",
            filters={
                "enabled": 1
            },
            fields=[
                "name",
                "rule_name",
                "correction_code",
                "category",
                "source_doctype",
                "field_name",
                "field_label",
                "risk_level",
                "execution_type",
                "evidence_required",
                "minimum_attachments",
                "process_age_days"
            ],
            order_by="category asc, correction_code asc",
            limit_page_length=500
        )

        frappe.response["message"] = {
            "ok": True,
            "context": ctx,
            "rules": rules
        }


    # ============================================================
    # LIST RULES
    # ============================================================

    elif action == "list_rules":

        ctx = build_context()

        rows = frappe.get_all(
            "LIFE Data Correction Rule",
            filters={"enabled": 1},
            fields=["*"],
            order_by="category asc, correction_code asc",
            limit_page_length=500
        )

        frappe.response["message"] = {
            "ok": True,
            "context": ctx,
            "rows": rows
        }


    # ============================================================
    # SEARCH SOURCE
    # ============================================================

    elif action == "search_source":

        ctx = build_context()

        rule = get_rule(
            frappe.form_dict.get("rule")
        )

        search = clean(
            frappe.form_dict.get("search")
        )

        doctype = clean(
            rule.source_doctype
        )

        meta = frappe.get_meta(doctype)

        fields = ["name", "modified"]

        candidates = [
            rule.search_field_1,
            rule.search_field_2,
            rule.search_field_3,
            rule.branch_field,
            "patient",
            "patient_name",
            "customer",
            "customer_name",
            "employee_name",
            "branch",
            "custom_branch",
            "posting_date",
            "status",
            "party",
            "grand_total",
            "outstanding_amount",
            "therapy_type"
        ]

        for value in candidates:

            fieldname = clean(value)

            if (
                fieldname
                and meta.has_field(fieldname)
                and fieldname not in fields
            ):
                fields.append(fieldname)

        filters = {}

        if not ctx.get("view_all"):

            branch_field = clean(
                rule.branch_field
            )

            if (
                branch_field
                and meta.has_field(branch_field)
            ):
                filters[branch_field] = [
                    "in",
                    ctx.get("branches") or ["__NONE__"]
                ]

        or_filters = []

        if search:

            search_fields = [
                "name",
                clean(rule.search_field_1),
                clean(rule.search_field_2),
                clean(rule.search_field_3)
            ]

            for fieldname in search_fields:

                if (
                    fieldname
                    and (
                        fieldname == "name"
                        or meta.has_field(fieldname)
                    )
                ):
                    or_filters.append([
                        doctype,
                        fieldname,
                        "like",
                        "%" + search + "%"
                    ])

        rows = frappe.get_all(
            doctype,
            filters=filters,
            or_filters=(
                or_filters
                if or_filters
                else None
            ),
            fields=fields,
            order_by="modified desc",
            limit_page_length=50
        )

        frappe.response["message"] = {
            "ok": True,
            "rows": rows
        }


    # ============================================================
    # GET SOURCE
    # ============================================================

    elif action == "get_source":

        ctx = build_context()

        rule = get_rule(
            frappe.form_dict.get("rule")
        )

        source_document = clean(
            frappe.form_dict.get("source_document")
        )

        doctype = clean(
            rule.source_doctype
        )

        if not source_document:
            frappe.throw(
                "Source document is required."
            )

        if not frappe.db.exists(
            doctype,
            source_document
        ):
            frappe.throw(
                "Source document not found."
            )

        branch = get_source_branch(
            rule,
            source_document
        )

        validate_branch_access(
            ctx,
            branch
        )

        source = frappe.get_doc(
            doctype,
            source_document
        )

        values = []

        for fieldname in [
            clean(rule.field_name),
            clean(rule.secondary_field),
            clean(rule.third_field)
        ]:

            if (
                fieldname
                and source.meta.has_field(fieldname)
            ):

                df = source.meta.get_field(
                    fieldname
                )

                values.append({
                    "field_name":
                        fieldname,
                    "field_label":
                        df.label
                        if df else fieldname,
                    "fieldtype":
                        df.fieldtype
                        if df else "",
                    "options":
                        df.options
                        if df else "",
                    "value":
                        source.get(fieldname)
                })

        child_rows = []

        child_field = clean(
            rule.child_table_field
        )

        if (
            child_field
            and source.meta.has_field(child_field)
        ):

            for row in (
                source.get(child_field) or []
            ):

                data = {
                    "name": row.name,
                    "idx": row.idx,
                    "doctype": row.doctype
                }

                for fieldname in [
                    "item_code",
                    "item_name",
                    "qty",
                    "rate",
                    "amount",
                    "account",
                    "party_type",
                    "party",
                    "debit",
                    "credit",
                    "debit_in_account_currency",
                    "credit_in_account_currency",
                    "account_head",
                    "description",
                    "tax_amount",
                    "gst_tax_type"
                ]:

                    if row.meta.has_field(fieldname):
                        data[fieldname] = (
                            row.get(fieldname)
                        )

                child_rows.append(data)

        frappe.response["message"] = {
            "ok": True,

            "rule": {
                "name": rule.name,
                "rule_name":
                    rule.rule_name,
                "correction_code":
                    rule.correction_code,
                "category":
                    rule.category,
                "source_doctype":
                    rule.source_doctype,
                "risk_level":
                    rule.risk_level,
                "execution_type":
                    rule.execution_type
            },

            "summary": {
                "name": source.name,
                "doctype": source.doctype,
                "docstatus": source.docstatus,
                "branch": branch,
                "modified": source.modified
            },

            "values": values,
            "child_rows": child_rows
        }


    # ============================================================
    # CREATE REQUEST
    # ============================================================

    elif action == "create_request":

        ctx = build_context()

        # --------------------------------------------------------
        # Read scalar args only.
        # Complex change rows are reconstructed from flattened
        # change_0_*, change_1_* ... parameters.
        # --------------------------------------------------------

        rule_name = clean(
            frappe.form_dict.get("rule")
        )

        rule = get_rule(rule_name)

        source_document = clean(
            frappe.form_dict.get("source_document")
        )

        reason = clean(
            frappe.form_dict.get("reason")
        )

        source_display_name = clean(
            frappe.form_dict.get("source_display_name")
        )

        changes = []

        change_count = to_int(
            frappe.form_dict.get("change_count")
        )

        for i in range(change_count):

            prefix = "change_" + str(i) + "_"

            requested_value = frappe.form_dict.get(
                prefix + "requested_value"
            )

            # Preserve empty requested values intentionally.
            if requested_value is None:
                requested_value = ""

            changes.append({
                "field_name": clean(
                    frappe.form_dict.get(
                        prefix + "field_name"
                    )
                ),
                "field_label": clean(
                    frappe.form_dict.get(
                        prefix + "field_label"
                    )
                ),
                "old_value": clean(
                    frappe.form_dict.get(
                        prefix + "old_value"
                    )
                ),
                "requested_value": clean(
                    requested_value
                ),
                "value_type": clean(
                    frappe.form_dict.get(
                        prefix + "value_type"
                    )
                ),
                "fieldtype": clean(
                    frappe.form_dict.get(
                        prefix + "fieldtype"
                    )
                ),
                "link_doctype": clean(
                    frappe.form_dict.get(
                        prefix + "link_doctype"
                    )
                ),
                "change_remarks": clean(
                    frappe.form_dict.get(
                        prefix + "change_remarks"
                    )
                )
            })

        attachments = []

        attachment_count = to_int(
            frappe.form_dict.get("attachment_count")
        )

        for i in range(attachment_count):

            file_url = clean(
                frappe.form_dict.get(
                    "attachment_" + str(i)
                )
            )

            if file_url:
                attachments.append(file_url)

        if not source_document:
            frappe.throw(
                "Source document is required."
            )

        if not reason:
            frappe.throw(
                "Reason is mandatory."
            )

        if not changes:
            frappe.throw(
                "No correction rows were received from the Web Page. "
                + "Please refresh the page, select the source record, "
                + "enter at least one requested correction, and submit again."
            )

        doctype = clean(
            rule.source_doctype
        )

        if not frappe.db.exists(
            doctype,
            source_document
        ):
            frappe.throw(
                "Source document does not exist."
            )

        branch = get_source_branch(
            rule,
            source_document
        )

        validate_branch_access(
            ctx,
            branch
        )

        # --------------------------------------------
        # Evidence validation
        # --------------------------------------------

        valid_attachments = []

        for value in attachments:

            value = clean(value)

            if value:
                valid_attachments.append(value)

        minimum = to_int(
            rule.minimum_attachments
        )

        if to_int(rule.evidence_required):

            if len(valid_attachments) < max(
                minimum,
                1
            ):
                frappe.throw(
                    "Supporting evidence is required. "
                    + "Minimum attachments: "
                    + str(max(minimum, 1))
                )

        # --------------------------------------------
        # Prevent duplicate active correction
        # --------------------------------------------

        duplicate = frappe.db.exists(
            "LIFE Data Correction Request",
            {
                "source_doctype": doctype,
                "source_document":
                    source_document,
                "status": [
                    "in",
                    [
                        "Pending Approval",
                        "Approved"
                    ]
                ]
            }
        )

        if duplicate:
            frappe.throw(
                "This source record already has an "
                + "active correction request: "
                + str(duplicate)
            )

        chain = build_approval_chain(rule)

        if not chain:
            frappe.throw(
                "No approval chain is configured "
                + "for this correction rule."
            )

        employee = get_employee()

        req = frappe.new_doc(
            "LIFE Data Correction Request"
        )

        req.requested_by = current_user

        req.requested_by_employee = clean(
            employee.get("name")
        )

        req.requested_by_name = (
            ctx.get("name")
        )

        req.requester_designation = clean(
            employee.get("designation")
        )

        req.branch = branch

        req.requested_on = (
            frappe.utils.now_datetime()
        )

        req.category = rule.category
        req.rule = rule.name

        req.source_doctype = doctype
        req.source_document = (
            source_document
        )

        req.source_display_name = (
            source_display_name
            or source_document
        )

        req.reason = reason

        if len(valid_attachments) > 0:
            req.attachment_1 = valid_attachments[0]

        if len(valid_attachments) > 1:
            req.attachment_2 = valid_attachments[1]

        if len(valid_attachments) > 2:
            req.attachment_3 = valid_attachments[2]

        req.status = "Pending Approval"

        req.workflow_stage = (
            chain[0].get("stage")
        )

        req.current_approver_role = (
            chain[0].get("required_access_role")
        )

        req.current_approver_user = ""

        req.is_on_hold = (
            1
            if to_int(rule.hold_source_record)
            else 0
        )

        req.access_role_at_creation = (
            ctx.get("access_role")
        )

        req.source_modified_at_request = (
            frappe.db.get_value(
                doctype,
                source_document,
                "modified"
            )
        )

        # --------------------------------------------
        # Changes
        # --------------------------------------------

        for change in changes:

            if not isinstance(change, dict):
                continue

            field_name = clean(
                change.get("field_name")
            )

            field_label = clean(
                change.get("field_label")
            )

            old_value = change.get("old_value")

            requested_value = change.get(
                "requested_value"
            )

            if requested_value is None:
                frappe.throw(
                    "Requested value is missing for "
                    + (
                        field_label
                        or field_name
                        or "correction"
                    )
                )

            req.append(
                "changes",
                {
                    "field_name":
                        field_name,

                    "field_label":
                        field_label
                        or field_name,

                    "old_value":
                        clean(old_value),

                    "requested_value":
                        clean(requested_value),

                    # Initial approved value =
                    # requested value.
                    # Later approvers may revise it.
                    "approved_value":
                        clean(requested_value),

                    "value_type":
                        clean(
                            change.get("value_type")
                        ) or "Data",

                    "link_doctype":
                        clean(
                            change.get("link_doctype")
                        ),

                    "fieldtype":
                        clean(
                            change.get("fieldtype")
                        ),

                    "change_remarks":
                        clean(
                            change.get("change_remarks")
                        )
                }
            )

        if not req.get("changes"):
            frappe.throw(
                "No valid changes were supplied."
            )

        # --------------------------------------------
        # Approval chain child rows
        # --------------------------------------------

        stage_no = 0

        for item in chain:

            stage_no += 1

            req.append(
                "approvals",
                {
                    "stage":
                        item.get("stage"),

                    "required_role":
                        item.get("required_role"),

                    "required_access_role":
                        item.get("required_access_role"),

                    "decision":
                        "Pending",

                    "stage_no":
                        stage_no
                }
            )

        req.insert(ignore_permissions=True)

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "request": req.name,
            "status": req.status,
            "workflow_stage":
                req.workflow_stage,
            "current_approver_role":
                req.current_approver_role
        }


    # ============================================================
    # LIST REQUESTS
    # ============================================================

    elif action == "list_requests":

        ctx = build_context()

        status_filter = clean(
            frappe.form_dict.get("status")
        )

        filters = {}

        if status_filter:
            filters["status"] = status_filter

        if not ctx.get("view_all"):

            branches = (
                ctx.get("branches")
                or ["__NONE__"]
            )

            filters["branch"] = [
                "in",
                branches
            ]

        rows = frappe.get_all(
            "LIFE Data Correction Request",
            filters=filters,
            fields=[
                "name",
                "requested_by",
                "requested_by_name",
                "branch",
                "requested_on",
                "category",
                "rule",
                "source_doctype",
                "source_document",
                "source_display_name",
                "status",
                "workflow_stage",
                "current_approver_role",
                "is_on_hold",
                "final_approved_on",
                "final_approved_by",
                "posted_by",
                "posted_on",
                "posting_reference",
                "posting_remarks",
                "creation",
                "modified"
            ],
            order_by="creation desc",
            limit_page_length=500
        )

        frappe.response["message"] = {
            "ok": True,
            "rows": rows
        }


    # ============================================================
    # MY APPROVAL DASHBOARD
    # ============================================================

    elif action == "my_approvals":

        ctx = build_context()

        access_role = clean(
            ctx.get("access_role")
        )

        filters = {
            "status": "Pending Approval"
        }

        if not ctx.get("is_dcr_admin"):

            filters["current_approver_role"] = access_role

            if access_role == "Branch Manager":

                filters["branch"] = [
                    "in",
                    ctx.get("branches") or ["__NONE__"]
                ]

        rows = frappe.get_all(
            "LIFE Data Correction Request",
            filters=filters,
            fields=[
                "name",
                "requested_by_name",
                "branch",
                "requested_on",
                "category",
                "rule",
                "source_doctype",
                "source_document",
                "source_display_name",
                "reason",
                "status",
                "workflow_stage",
                "current_approver_role",
                "creation",
                "modified"
            ],
            order_by="requested_on asc",
            limit_page_length=500
        )

        frappe.response["message"] = {
            "ok": True,
            "access_role": access_role,
            "is_dcr_admin": bool(ctx.get("is_dcr_admin")),
            "count": len(rows),
            "rows": rows
        }


    # ============================================================
    # GET REQUEST DETAIL
    # ============================================================

    elif action == "get_request":

        ctx = build_context()

        request_name = clean(
            frappe.form_dict.get("request")
        )

        if not request_name:
            frappe.throw(
                "Request is required."
            )

        if not frappe.db.exists(
            "LIFE Data Correction Request",
            request_name
        ):
            frappe.throw(
                "Correction request not found."
            )

        req = frappe.get_doc(
            "LIFE Data Correction Request",
            request_name
        )

        if not ctx.get("view_all"):
            validate_branch_access(
                ctx,
                req.branch
            )

        can_act = False

        if req.status == "Pending Approval":

            if ctx.get("is_dcr_admin"):
                can_act = True

            elif clean(
                req.current_approver_role
            ) == clean(
                ctx.get("access_role")
            ):
                can_act = True

                if (
                    ctx.get("access_role")
                    == "Branch Manager"
                ):
                    if req.branch not in (
                        ctx.get("branches") or []
                    ):
                        can_act = False

        frappe.response["message"] = {
            "ok": True,
            "can_act": can_act,
            "context": ctx,
            "request": serialize_request(req)
        }


    # ============================================================
    # APPROVE / REJECT
    # ============================================================

    elif action == "decision":

        ctx = build_context()

        request_name = clean(
            frappe.form_dict.get("request")
        )

        decision = clean(
            frappe.form_dict.get("decision")
        )

        remarks = clean(
            frappe.form_dict.get("remarks")
        )

        approved_changes = json_value(
            frappe.form_dict.get("approved_changes"),
            []
        )

        if decision not in ["Approved", "Rejected"]:
            frappe.throw(
                "Decision must be Approved or Rejected."
            )

        if not remarks:
            frappe.throw(
                "Remarks are mandatory for approval and rejection."
            )

        if not frappe.db.exists(
            "LIFE Data Correction Request",
            request_name
        ):
            frappe.throw(
                "Correction request not found."
            )

        req = frappe.get_doc(
            "LIFE Data Correction Request",
            request_name
        )

        if req.status != "Pending Approval":
            frappe.throw(
                "This request is no longer pending approval."
            )

        current_role = clean(
            req.current_approver_role
        )

        user_role = clean(
            ctx.get("access_role")
        )

        admin_override = bool(
            ctx.get("is_dcr_admin")
        )

        if (
            not admin_override
            and current_role != user_role
        ):
            frappe.throw(
                "This request is pending with "
                + current_role
                + ". You are acting as "
                + user_role
                + "."
            )

        if (
            not admin_override
            and user_role == "Branch Manager"
        ):
            validate_branch_access(
                ctx,
                req.branch
            )

        # --------------------------------------------
        # Find current pending approval row
        # --------------------------------------------

        current_row = None

        for row in req.get("approvals") or []:

            if (
                clean(row.required_access_role) == current_role
                and clean(row.decision) == "Pending"
            ):
                current_row = row
                break

        # Admin fallback: if legacy request data has a mismatched
        # role label, act on the first remaining pending row in
        # stage order.
        if (
            not current_row
            and admin_override
        ):
            pending_rows = []

            for row in req.get("approvals") or []:

                if clean(row.decision) == "Pending":
                    pending_rows.append(row)

            pending_rows = sorted(
                pending_rows,
                key=lambda x: to_int(x.stage_no)
            )

            if pending_rows:
                current_row = pending_rows[0]
                current_role = clean(
                    current_row.required_access_role
                    or current_row.required_role
                    or current_row.stage
                )

        if not current_row:
            frappe.throw(
                "Current pending approval row could not be identified."
            )

        employee = get_employee()

        # --------------------------------------------
        # Optional approver revisions
        # --------------------------------------------

        if (
            decision == "Approved"
            and approved_changes
        ):

            for update in approved_changes:

                if not isinstance(update, dict):
                    continue

                row_name = clean(
                    update.get("name")
                )

                field_name = clean(
                    update.get("field_name")
                )

                approved_value = update.get(
                    "approved_value"
                )

                target_row = None

                for change_row in (
                    req.get("changes") or []
                ):

                    if (
                        row_name
                        and change_row.name == row_name
                    ):
                        target_row = change_row
                        break

                    if (
                        not row_name
                        and field_name
                        and clean(change_row.field_name)
                        == field_name
                    ):
                        target_row = change_row
                        break

                if target_row:
                    target_row.approved_value = (
                        clean(approved_value)
                    )

        # --------------------------------------------
        # Stamp approval row
        # --------------------------------------------

        current_row.decision = decision

        if admin_override:
            current_row.remarks = (
                "[Admin Override] " + remarks
            )
        else:
            current_row.remarks = remarks

        current_row.approver_user = current_user

        current_row.approver_employee = clean(
            employee.get("name")
        )

        current_row.approver_name = (
            ctx.get("name")
        )

        current_row.acted_on = (
            frappe.utils.now_datetime()
        )

        # --------------------------------------------
        # REJECT
        # --------------------------------------------

        if decision == "Rejected":

            req.status = "Rejected"

            req.workflow_stage = (
                current_role + " Rejected"
            )

            req.current_approver_role = ""
            req.current_approver_user = ""

            req.is_on_hold = 0

            # Remaining pending stages are skipped
            for row in req.get("approvals") or []:

                if (
                    row.name != current_row.name
                    and row.decision == "Pending"
                ):
                    row.decision = "Skipped"

        # --------------------------------------------
        # APPROVE
        # --------------------------------------------

        else:

            next_row = None

            rows_sorted = sorted(
                req.get("approvals") or [],
                key=lambda x: to_int(x.stage_no)
            )

            for row in rows_sorted:

                if (
                    to_int(row.stage_no)
                    > to_int(current_row.stage_no)
                    and row.decision == "Pending"
                ):
                    next_row = row
                    break

            if next_row:

                req.status = "Pending Approval"

                req.workflow_stage = next_row.stage

                req.current_approver_role = (
                    next_row.required_access_role
                )

                req.current_approver_user = ""

            else:

                req.status = "Approved"

                req.workflow_stage = "Approved - To Apply"

                req.current_approver_role = ""
                req.current_approver_user = ""

                req.final_approved_on = (
                    frappe.utils.now_datetime()
                )

                req.final_approved_by = current_user

                # Hold remains ON until the posting step
                # actually writes to the source document.
                req.is_on_hold = 1

        req.save(ignore_permissions=True)

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "request": req.name,
            "decision": decision,
            "status": req.status,
            "workflow_stage":
                req.workflow_stage,
            "current_approver_role":
                req.current_approver_role,
            "final_approved_on":
                req.final_approved_on,
            "request_data":
                serialize_request(req)
        }


    # ============================================================
    # APPLY / POST — write approved values into the source doc
    # ============================================================

    elif action == "apply_request":

        ctx = build_context()

        request_name = clean(
            frappe.form_dict.get("request")
        )

        posting_remarks = clean(
            frappe.form_dict.get("posting_remarks")
        )

        if not request_name:
            frappe.throw("Request is required.")

        if not frappe.db.exists(
            "LIFE Data Correction Request",
            request_name
        ):
            frappe.throw("Correction request not found.")

        # --------------------------------------------
        # Who may post
        # --------------------------------------------

        access_role = clean(ctx.get("access_role"))
        admin_override = bool(ctx.get("is_dcr_admin"))

        user_roles_lower = [
            clean(r).lower()
            for r in (get_user_roles() or [])
        ]

        is_system_manager = (
            "system manager" in user_roles_lower
        )

        if (
            not admin_override
            and not is_system_manager
            and access_role not in ["Accounts", "COO"]
        ):
            frappe.throw(
                "Only Accounts, COO or a System Manager can post a "
                "correction to the source document. You are acting as "
                + (access_role or "no role") + "."
            )

        # --------------------------------------------
        # Lock the request row
        # --------------------------------------------

        _read_sql(
            "select name from `tabLIFE Data Correction Request` "
            "where name=%s for update",
            request_name
        )

        req = frappe.get_doc(
            "LIFE Data Correction Request",
            request_name
        )

        if req.status != "Approved":
            frappe.throw(
                "This request is not in 'Approved' state "
                "(current status: " + clean(req.status) + ")."
            )

        if req.posted_on:
            frappe.throw(
                "This request was already posted on "
                + str(req.posted_on) + " as "
                + clean(req.posting_reference) + "."
            )

        # --------------------------------------------
        # Branch scope check
        # --------------------------------------------

        if (
            not admin_override
            and not is_system_manager
            and access_role != "COO"
            and not ctx.get("view_all")
        ):
            validate_branch_access(ctx, req.branch)

        doctype = clean(req.source_doctype)
        source_document = clean(req.source_document)

        if not doctype or not source_document:
            frappe.throw(
                "This request has no source document to post to."
            )

        if not frappe.db.exists(doctype, source_document):
            frappe.throw(
                "Source document " + source_document
                + " no longer exists. Cannot post."
            )

        # --------------------------------------------
        # Concurrency guard — has the source moved?
        # --------------------------------------------

        current_modified = frappe.db.get_value(
            doctype, source_document, "modified"
        )

        baseline_modified = (
            req.source_modified_at_request
            or req.modified
        )

        if (
            baseline_modified
            and current_modified
            and str(current_modified) != str(baseline_modified)
            and not admin_override
            and not is_system_manager
        ):
            req.source_modified_after_request = 1

            req.add_comment(
                "Comment",
                "Posting blocked: source modified at "
                + str(current_modified)
                + " vs snapshot at request "
                + str(baseline_modified)
                + ". Admin must re-confirm."
            )

            req.save(ignore_permissions=True)
            frappe.db.commit()

            frappe.throw(
                "The source document has changed since this "
                "request was raised. Re-verify and try again, "
                "or ask a DCR Admin to override."
            )

        # --------------------------------------------
        # Prepare change rows
        # --------------------------------------------

        changes = req.get("changes") or []

        if not changes:
            frappe.throw(
                "This request has no change rows to apply."
            )

        rule = None

        try:
            if req.rule and frappe.db.exists(
                "LIFE Data Correction Rule", req.rule
            ):
                rule = frappe.get_doc(
                    "LIFE Data Correction Rule", req.rule
                )
        except Exception:
            rule = None

        source = frappe.get_doc(doctype, source_document)
        source_meta = frappe.get_meta(doctype)

        applied = []
        skipped = []
        link_failures = []

        # --------------------------------------------
        # Walk every change row
        # --------------------------------------------

        for row in changes:

            field_name = clean(row.field_name)

            raw_value = (
                row.approved_value
                if clean(row.approved_value) != ""
                else row.requested_value
            )

            value = clean(raw_value)

            if not field_name:
                skipped.append("(blank field)")
                continue

            # ---- 0. Cancellation action ---------------------
            if field_name == "#cancel" and value == "Cancelled":
                try:
                    src_for_cancel = frappe.get_doc(
                        doctype, source_document
                    )

                    if int(src_for_cancel.docstatus or 0) == 1:
                        src_for_cancel.flags.ignore_permissions = True
                        src_for_cancel.cancel()
                        applied.append("#cancel · cancelled")
                    else:
                        applied.append(
                            "#cancel · docstatus not 1, skipped cancel"
                        )
                except Exception as e:
                    skipped.append("#cancel (" + str(e) + ")")
                continue

            # ---- 0b. Named ACTION --------------------------
            if field_name == "#action":
                action_name = (
                    clean(getattr(rule, "action_name", ""))
                    if rule else ""
                ) or value

                applied.append(
                    "#action · " + action_name
                    + " (recorded, not executed)"
                )
                continue

            # ---- 0c. Free-text manual ----------------------
            if field_name == "#manual":
                applied.append("#manual · recorded only")
                continue

            # ---- 1. Simple field on the source doc ----------
            if "." not in field_name:

                if not source_meta.has_field(field_name):
                    skipped.append(
                        field_name + " (no such field)"
                    )
                    continue

                df = source_meta.get_field(field_name)

                # Pre-flight link check: if the field is a Link
                # and the target record does not exist, record a
                # hard failure and skip this change row.
                link_problem = preflight_link_check(
                    source_meta, field_name, value
                )

                if link_problem:
                    link_failures.append({
                        "field_name": field_name,
                        "field_label": df.label or field_name,
                        "value": value,
                        "message": link_problem,
                    })
                    continue

                cast = value

                if df.fieldtype in ("Int",):
                    try:
                        cast = int(float(value or 0))
                    except Exception:
                        cast = 0

                elif df.fieldtype in (
                    "Float", "Currency", "Percent"
                ):
                    try:
                        cast = float(value or 0)
                    except Exception:
                        cast = 0.0

                elif df.fieldtype == "Check":
                    cast = 1 if str(value).lower() in (
                        "1", "true", "yes"
                    ) else 0

                elif df.fieldtype == "Date":
                    cast = value[:10] if value else None

                source.set(field_name, cast)
                applied.append(
                    field_name + " = " + str(cast)
                )
                continue

            # ---- 2. Child table field: table.rowname.field ----
            parts = field_name.split(".")

            if len(parts) != 3:
                skipped.append(
                    field_name + " (unrecognised path)"
                )
                continue

            table_field, row_name, child_field = parts

            if not source_meta.has_field(table_field):
                skipped.append(
                    table_field + " (no such child table)"
                )
                continue

            child_dt = source_meta.get_field(
                table_field
            ).options

            if not child_dt:
                skipped.append(
                    table_field + " (no child doctype)"
                )
                continue

            child_meta = frappe.get_meta(child_dt)

            if not child_meta.has_field(child_field):
                skipped.append(
                    field_name + " (no such child field)"
                )
                continue

            target_row = None

            for crow in source.get(table_field) or []:
                if crow.name == row_name:
                    target_row = crow
                    break

            if not target_row:
                skipped.append(
                    field_name + " (row not found)"
                )
                continue

            df = child_meta.get_field(child_field)
            cast = value

            if df.fieldtype in ("Int",):
                try:
                    cast = int(float(value or 0))
                except Exception:
                    cast = 0

            elif df.fieldtype in (
                "Float", "Currency", "Percent"
            ):
                try:
                    cast = float(value or 0)
                except Exception:
                    cast = 0.0

            target_row.set(child_field, cast)
            applied.append(
                field_name + " = " + str(cast)
            )

        # --------------------------------------------------------
        # After every change row has been processed:
        # 1. If any Link field failed pre-flight, abort the whole
        #    posting. Nothing has been written yet.
        # 2. If nothing at all was applied, abort.
        # --------------------------------------------------------

        if link_failures:
            details = []

            for f in link_failures:
                details.append(
                    (f.get("field_label")
                     or f.get("field_name"))
                    + ": " + f.get("message", "")
                )

            frappe.throw(
                "This correction cannot be posted because some values "
                "do not exist as records in the linked DocType.\n\n"
                + "\n".join(details)
                + "\n\nRaise a fresh correction with valid values, or "
                "create the missing record first."
            )

        if not applied:
            frappe.throw(
                "No field could be written. Reasons: "
                + "; ".join(skipped or ["unknown"])
            )

        # --------------------------------------------
        # Save the source doc
        # --------------------------------------------

        source.flags.ignore_permissions = True
        source.flags.ignore_validate_update_after_submit = True
        source.flags.life_dcr_post = request_name

        try:
            source.save(ignore_permissions=True)

        except Exception as e:

            frappe.db.rollback()

            # Try to give a cleaner message for the common
            # Frappe validation failures. Fall back to the raw
            # message otherwise.
            msg = str(e)

            try:
                if isinstance(e, frappe.LinkValidationError):
                    msg = (
                        "One of the corrected values points to a "
                        "record that does not exist. " + msg
                    )
                elif isinstance(e, frappe.MandatoryError):
                    msg = (
                        "The source document would be left with a "
                        "mandatory field empty after this correction. "
                        + msg
                    )
                elif isinstance(e, frappe.ValidationError):
                    msg = (
                        "The source document rejected the corrected "
                        "values. " + msg
                    )
            except Exception:
                pass

            frappe.throw(
                "Failed to write to " + doctype + " "
                + source_document + ": " + msg
            )

        # --------------------------------------------
        # Stamp the request as posted
        # --------------------------------------------

        req.posted_by = current_user
        req.posted_on = frappe.utils.now_datetime()
        req.posting_reference = request_name

        req.posting_remarks = (
            posting_remarks
            or (
                "Applied by " + access_role
                if not admin_override
                else "Applied by DCR Admin"
            )
        )

        req.status = "Posted"
        req.workflow_stage = "Posted"
        req.current_approver_role = ""
        req.current_approver_user = ""
        req.is_on_hold = 0

            # Refresh the snapshot so a subsequent correction request
        # against this same record does not trip the concurrency guard
        # on our own write.
        req.source_modified_at_request = frappe.db.get_value(
            doctype, source_document, "modified"
        )

        req.source_modified_after_request = (
            1
            if (
                baseline_modified
                and current_modified
                and str(current_modified)
                != str(baseline_modified)
            )
            else 0
        )

        req.add_comment(
            "Comment",
            "Posted to " + doctype + " " + source_document
            + ". Fields written: "
            + ", ".join(applied)
            + (
                "; skipped: " + ", ".join(skipped)
                if skipped else ""
            )
        )

        req.save(ignore_permissions=True)

        # --------------------------------------------
        # Audit trail on the source doc itself
        # --------------------------------------------

        source.add_comment(
            "Comment",
            "Data Correction " + request_name
            + " posted. Fields: " + ", ".join(applied)
            + (
                ". Remarks: " + req.posting_remarks
                if req.posting_remarks else ""
            )
        )

        source.save(ignore_permissions=True)

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": True,
            "request": req.name,
            "status": req.status,
            "posted_on": req.posted_on,
            "posted_by": req.posted_by,
            "applied": applied,
            "skipped": skipped,
            "request_data": serialize_request(req)
        }


    # ============================================================
    # UNKNOWN ACTION
    # ============================================================

    else:

        frappe.throw(
            "Unknown Data Correction action: "
            + action
        )
