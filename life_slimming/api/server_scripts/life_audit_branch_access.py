"""Branch Audit Report For Master Report

Original API: life_audit_branch_access
Source modified: 2026-07-27 13:28:25.996639
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
    # LIFE AUDIT — BRANCH LOGIN AND MASTER REPORT ACCESS
    # ================================================================
    # Script Type : API
    # API Method  : life_audit_branch_access
    # Enabled     : Checked
    # Allow Guest : Unchecked
    #
    # Branch resolution priority:
    # 1. Branch.custom_audit_report_email
    # 2. User Permission → Branch
    # 3. Employee.user_id → Employee.branch
    # 4. Login email prefix → Branch name
    #
    # Branch users can see only their own branch.
    # Draft audits remain hidden.
    # ================================================================

    action = (
        frappe.form_dict.get("action")
        or ""
    ).strip().lower()

    current_user = (
        frappe.session.user
        or ""
    ).strip()

    if not current_user or current_user == "Guest":
        frappe.throw(
            "Please log in before opening the Audit Command Center."
        )


    # ================================================================
    # RESOLVE LOGGED-IN USER'S BRANCH
    # ================================================================

    matched_branch = ""

    current_user_lower = (
        current_user.lower()
    )


    # ------------------------------------------------
    # PRIORITY 1: BRANCH AUDIT REPORT EMAIL
    # ------------------------------------------------

    branch_rows = frappe.db.get_all(
        "Branch",
        fields=[
            "name",
            "custom_audit_report_email"
        ],
        order_by="name asc",
        limit_page_length=0
    )

    for branch_row in branch_rows:
        branch_email = (
            branch_row.get(
                "custom_audit_report_email"
            )
            or ""
        ).strip().lower()

        if (
            branch_email
            and branch_email == current_user_lower
        ):
            matched_branch = (
                branch_row.get("name")
                or ""
            ).strip()

            break


    # ------------------------------------------------
    # PRIORITY 2: USER PERMISSION → BRANCH
    # ------------------------------------------------

    if not matched_branch:
        permission_rows = frappe.db.get_all(
            "User Permission",
            filters={
                "user": current_user,
                "allow": "Branch"
            },
            fields=[
                "for_value",
                "is_default"
            ],
            order_by="is_default desc, modified desc",
            limit_page_length=0
        )

        for permission_row in permission_rows:
            permission_branch = (
                permission_row.get(
                    "for_value"
                )
                or ""
            ).strip()

            if (
                permission_branch
                and frappe.db.exists(
                    "Branch",
                    permission_branch
                )
            ):
                matched_branch = permission_branch
                break


    # ------------------------------------------------
    # PRIORITY 3: EMPLOYEE USER → EMPLOYEE BRANCH
    # ------------------------------------------------

    if not matched_branch:
        employee_branch = (
            frappe.db.get_value(
                "Employee",
                {
                    "user_id": current_user,
                    "status": "Active"
                },
                "branch"
            )
            or ""
        ).strip()

        if (
            employee_branch
            and frappe.db.exists(
                "Branch",
                employee_branch
            )
        ):
            matched_branch = employee_branch


    # ------------------------------------------------
    # PRIORITY 4: EMAIL PREFIX → BRANCH NAME
    # ------------------------------------------------

    if not matched_branch:
        user_prefix = (
            current_user_lower.split("@")[0]
            if "@" in current_user_lower
            else current_user_lower
        )

        user_key = (
            user_prefix
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
            .replace(".", "")
            .lower()
        )

        branch_login_aliases = {
            "chandhanagar": "chandanagar",
            "chandannagar": "chandanagar"
        }

        user_key = branch_login_aliases.get(
            user_key,
            user_key
        )

        for branch_row in branch_rows:
            branch_name = (
                branch_row.get("name")
                or ""
            ).strip()

            branch_key = (
                branch_name
                .replace(" ", "")
                .replace("-", "")
                .replace("_", "")
                .replace(".", "")
                .lower()
            )

            if branch_key == user_key:
                matched_branch = branch_name
                break


    # ================================================================
    # ACTION: RESOLVE BRANCH LOGIN
    # ================================================================

    if action == "resolve":
        frappe.response["message"] = {
            "ok": True if matched_branch else False,
            "branch_user": (
                1 if matched_branch else 0
            ),
            "branch": matched_branch,
            "user": current_user
        }


    # ================================================================
    # ACTION: LOAD BRANCH MASTER REPORT
    # ================================================================

    elif action == "report":
        if not matched_branch:
            frappe.throw(
                "This login is not mapped to a Branch. "
                "Open the Branch record and enter this login email "
                "in Audit Report Email."
            )

        # Draft remains private.
        # All other workflow stages are visible to the branch.
        allowed_statuses = [
            "Submitted",
            "Verified",
            "Sent to Branch",
            "Actioned",
            "Closed"
        ]

        requested_status = (
            frappe.form_dict.get("status")
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

        requested_sort = (
            frappe.form_dict.get("sort")
            or "desc"
        ).strip().lower()

        if requested_sort not in [
            "asc",
            "desc"
        ]:
            requested_sort = "desc"

        filters = {
            "branch": matched_branch,
            "audit_status": [
                "in",
                allowed_statuses
            ]
        }

        if requested_status:
            if requested_status not in allowed_statuses:
                frappe.throw(
                    "The selected audit status is not available "
                    "to branch users."
                )

            filters["audit_status"] = (
                requested_status
            )

        if from_date and to_date:
            filters["audit_date"] = [
                "between",
                [
                    from_date,
                    to_date
                ]
            ]

        elif from_date:
            filters["audit_date"] = [
                ">=",
                from_date
            ]

        elif to_date:
            filters["audit_date"] = [
                "<=",
                to_date
            ]

        audit_rows = frappe.db.get_all(
            "Branch Audit",
            filters=filters,
            fields=[
                "name",
                "branch",
                "audit_date",
                "auditor",
                "audit_status",
                "total_score",
                "max_score",
                "percentage",
                "grade",
                "has_violation",
                "violation_summary",
                "docstatus",
                "creation",
                "management_remarks_to_auditor",
                "management_remarks_to_branch",
                "verified_on",
                "verified_by",
                "sent_to_branch_on",
                "sent_to_branch_by",
                "branch_report_email"
            ],
            order_by=(
                "audit_date "
                + requested_sort
                + ", creation desc"
            ),
            limit_page_length=500
        )

        result_audits = []

        for audit_row in audit_rows:
            audit_name = (
                audit_row.get("name")
                or ""
            )

            full_audit = frappe.get_doc(
                "Branch Audit",
                audit_name
            )

            auditor_email = (
                audit_row.get("auditor")
                or ""
            ).strip()

            auditor_full_name = ""

            if auditor_email:
                auditor_full_name = (
                    frappe.db.get_value(
                        "User",
                        auditor_email,
                        "full_name"
                    )
                    or ""
                ).strip()

            section_scores = []

            for score_row in (
                full_audit.get(
                    "section_scores"
                )
                or []
            ):
                section_scores.append(
                    {
                        "section_code": (
                            score_row.get(
                                "section_code"
                            )
                            or ""
                        ),
                        "section_name": (
                            score_row.get(
                                "section_name"
                            )
                            or ""
                        ),
                        "raw": frappe.utils.flt(
                            score_row.get("raw")
                        ),
                        "raw_max": frappe.utils.flt(
                            score_row.get(
                                "raw_max"
                            )
                        ),
                        "group_score": frappe.utils.flt(
                            score_row.get(
                                "group_score"
                            )
                        ),
                        "weight": frappe.utils.flt(
                            score_row.get(
                                "weight"
                            )
                        )
                    }
                )

            ratings = []

            for rating_row in (
                full_audit.get("ratings")
                or []
            ):
                ratings.append(
                    {
                        "section_code": (
                            rating_row.get(
                                "section_code"
                            )
                            or ""
                        ),
                        "item_idx": (
                            rating_row.get(
                                "item_idx"
                            )
                            or rating_row.get("idx")
                            or ""
                        ),
                        "question": (
                            rating_row.get(
                                "question"
                            )
                            or ""
                        ),
                        "points": frappe.utils.flt(
                            rating_row.get(
                                "points"
                            )
                        ),
                        "rating": (
                            rating_row.get(
                                "rating"
                            )
                            or ""
                        ),
                        "scored": frappe.utils.flt(
                            rating_row.get(
                                "scored"
                            )
                        ),
                        "is_critical_item": (
                            frappe.utils.cint(
                                rating_row.get(
                                    "is_critical_item"
                                )
                            )
                        ),
                        "remarks": (
                            rating_row.get(
                                "remarks"
                            )
                            or ""
                        ),
                        "evidence_attachment": (
                            rating_row.get(
                                "evidence_attachment"
                            )
                            or ""
                        ),
                        "action_owner": (
                            rating_row.get(
                                "action_owner"
                            )
                            or ""
                        ),
                        "target_date": (
                            rating_row.get(
                                "target_date"
                            )
                            or ""
                        )
                    }
                )

            result_audits.append(
                {
                    "name": audit_name,
                    "branch": (
                        audit_row.get("branch")
                        or ""
                    ),
                    "audit_date": (
                        audit_row.get(
                            "audit_date"
                        )
                        or ""
                    ),
                    "auditor": auditor_email,
                    "auditor_full_name": (
                        auditor_full_name
                        or auditor_email
                    ),
                    "audit_status": (
                        audit_row.get(
                            "audit_status"
                        )
                        or ""
                    ),
                    "total_score": frappe.utils.flt(
                        audit_row.get(
                            "total_score"
                        )
                    ),
                    "max_score": frappe.utils.flt(
                        audit_row.get(
                            "max_score"
                        )
                    ),
                    "percentage": frappe.utils.flt(
                        audit_row.get(
                            "percentage"
                        )
                    ),
                    "grade": (
                        audit_row.get("grade")
                        or ""
                    ),
                    "has_violation": (
                        frappe.utils.cint(
                            audit_row.get(
                                "has_violation"
                            )
                        )
                    ),
                    "violation_summary": (
                        audit_row.get(
                            "violation_summary"
                        )
                        or ""
                    ),
                    "docstatus": frappe.utils.cint(
                        audit_row.get(
                            "docstatus"
                        )
                    ),
                    "creation": (
                        audit_row.get(
                            "creation"
                        )
                        or ""
                    ),
                    "management_remarks_to_auditor": (
                        audit_row.get(
                            "management_remarks_to_auditor"
                        )
                        or ""
                    ),
                    "management_remarks_to_branch": (
                        audit_row.get(
                            "management_remarks_to_branch"
                        )
                        or ""
                    ),
                    "verified_on": (
                        audit_row.get(
                            "verified_on"
                        )
                        or ""
                    ),
                    "verified_by": (
                        audit_row.get(
                            "verified_by"
                        )
                        or ""
                    ),
                    "sent_to_branch_on": (
                        audit_row.get(
                            "sent_to_branch_on"
                        )
                        or ""
                    ),
                    "sent_to_branch_by": (
                        audit_row.get(
                            "sent_to_branch_by"
                        )
                        or ""
                    ),
                    "branch_report_email": (
                        audit_row.get(
                            "branch_report_email"
                        )
                        or ""
                    ),
                    "section_scores": section_scores,
                    "ratings": ratings
                }
            )

        frappe.response["message"] = {
            "ok": True,
            "branch_user": 1,
            "branch": matched_branch,
            "user": current_user,
            "audits": result_audits
        }


    # ================================================================
    # INVALID ACTION
    # ================================================================

    else:
        frappe.throw(
            "Invalid branch audit action."
        )
