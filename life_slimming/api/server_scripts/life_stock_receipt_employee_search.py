"""BRANCH RECEIPT EMPLOYEE SEARCH

Original API: life_stock_receipt_employee_search
Source modified: 2026-10-02 12:26:29.564232
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
    # LIFE STOCK - BRANCH RECEIPT EMPLOYEE SEARCH
    # API Method:
    # life_stock_receipt_employee_search
    # ============================================================

    branch = str(
        frappe.form_dict.get("branch") or ""
    ).strip()

    query = str(
        frappe.form_dict.get("query") or ""
    ).strip()

    limit_value = frappe.form_dict.get("limit") or 20


    # ============================================================
    # LIMIT
    # ============================================================

    try:
        limit_value = int(limit_value)
    except Exception:
        limit_value = 20

    if limit_value < 1:
        limit_value = 20

    if limit_value > 50:
        limit_value = 50


    # ============================================================
    # VALIDATE REQUEST
    # ============================================================

    if not branch:
        frappe.throw(
            "Receiving branch is required."
        )


    session_user = str(
        frappe.session.user or ""
    ).strip()


    if not session_user:
        frappe.throw(
            "Unable to identify logged-in user."
        )


    if session_user == "Guest":
        frappe.throw(
            "Please login again."
        )


    # ============================================================
    # ADMINISTRATOR
    # ============================================================

    is_administrator = (
        session_user == "Administrator"
    )


    # ============================================================
    # RESOLVE BRANCHES ALLOWED FOR LOGGED-IN USER
    # ============================================================

    allowed_branches = []


    if not is_administrator:

        # --------------------------------------------------------
        # 1. USER PERMISSION -> BRANCH
        # --------------------------------------------------------

        try:

            permission_rows = frappe.get_all(
                "User Permission",
                filters={
                    "user": session_user,
                    "allow": "Branch"
                },
                fields=[
                    "for_value"
                ],
                limit_page_length=100
            )

            for permission_row in permission_rows:

                permitted_branch = str(
                    permission_row.get(
                        "for_value"
                    ) or ""
                ).strip()

                if (
                    permitted_branch
                    and
                    permitted_branch not in allowed_branches
                ):
                    allowed_branches.append(
                        permitted_branch
                    )

        except Exception:
            pass


        # --------------------------------------------------------
        # 2. EMPLOYEE BRANCH FOR LOGGED-IN USER
        # --------------------------------------------------------

        try:

            employee_rows = frappe.get_all(
                "Employee",
                filters={
                    "user_id": session_user,
                    "status": "Active"
                },
                fields=[
                    "name",
                    "branch"
                ],
                limit_page_length=10
            )

            for employee_row in employee_rows:

                employee_branch = str(
                    employee_row.get(
                        "branch"
                    ) or ""
                ).strip()

                if (
                    employee_branch
                    and
                    employee_branch not in allowed_branches
                ):
                    allowed_branches.append(
                        employee_branch
                    )

        except Exception:
            pass


        # --------------------------------------------------------
        # 3. COMPANY EMAIL FALLBACK
        # --------------------------------------------------------

        try:

            company_email_rows = frappe.get_all(
                "Employee",
                filters={
                    "company_email": session_user,
                    "status": "Active"
                },
                fields=[
                    "name",
                    "branch"
                ],
                limit_page_length=10
            )

            for employee_row in company_email_rows:

                employee_branch = str(
                    employee_row.get(
                        "branch"
                    ) or ""
                ).strip()

                if (
                    employee_branch
                    and
                    employee_branch not in allowed_branches
                ):
                    allowed_branches.append(
                        employee_branch
                    )

        except Exception:
            pass


        # --------------------------------------------------------
        # 4. PERSONAL EMAIL FALLBACK
        # --------------------------------------------------------

        try:

            personal_email_rows = frappe.get_all(
                "Employee",
                filters={
                    "personal_email": session_user,
                    "status": "Active"
                },
                fields=[
                    "name",
                    "branch"
                ],
                limit_page_length=10
            )

            for employee_row in personal_email_rows:

                employee_branch = str(
                    employee_row.get(
                        "branch"
                    ) or ""
                ).strip()

                if (
                    employee_branch
                    and
                    employee_branch not in allowed_branches
                ):
                    allowed_branches.append(
                        employee_branch
                    )

        except Exception:
            pass


        # --------------------------------------------------------
        # VALIDATE RECEIVING BRANCH
        # --------------------------------------------------------

        if branch not in allowed_branches:

            frappe.throw(
                "You are not permitted to search employees for branch: "
                + branch
            )


    # ============================================================
    # BUILD EMPLOYEE FILTERS
    # ============================================================

    filters = [
        [
            "Employee",
            "status",
            "=",
            "Active"
        ],
        [
            "Employee",
            "branch",
            "=",
            branch
        ]
    ]


    or_filters = []


    # ============================================================
    # SEARCH QUERY
    # ============================================================

    if query:

        safe_query = (
            query
            .replace("%", "")
            .replace("_", "")
            .strip()
        )

        if safe_query:

            like_value = (
                "%"
                + safe_query
                + "%"
            )

            or_filters = [
                [
                    "Employee",
                    "employee_name",
                    "like",
                    like_value
                ],
                [
                    "Employee",
                    "name",
                    "like",
                    like_value
                ],
                [
                    "Employee",
                    "designation",
                    "like",
                    like_value
                ]
            ]


    # ============================================================
    # FETCH ACTIVE EMPLOYEES
    #
    # IMPORTANT:
    # frappe.get_all is intentional here.
    #
    # The branch has already been validated against the logged-in
    # user's permitted branch(es), so this avoids Employee Read
    # permission restrictions hiding valid employees.
    # ============================================================

    employees = frappe.get_all(
        "Employee",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "employee_name",
            "status",
            "designation",
            "branch",
            "department",
            "employee_number"
        ],
        order_by="employee_name asc",
        limit_page_length=limit_value
    )


    # ============================================================
    # RESPONSE
    # ============================================================

    frappe.response["message"] = {
        "ok": True,
        "branch": branch,
        "query": query,
        "count": len(employees),
        "data": employees
    }
