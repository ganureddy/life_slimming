"""Branch Expenditure Employees Name

Original API: life_get_expenditure_branch_employees
Source modified: 2026-07-29 14:26:48.155946
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
    # Server Script Type: API
    # API Method: life_get_expenditure_branch_employees
    # Enabled: Yes
    # Allow Guest: No

    branch = (frappe.form_dict.get("branch") or "").strip()
    search_term = (frappe.form_dict.get("search_term") or "").strip().lower()
    user = frappe.session.user

    # Head Office special rule:
    # Only these active Employee designations are shown.
    head_office_designations = [
        "accountant",
        "account executive",
        "accounts executive",
        "accounts excutive",
        "senior accountant"
    ]

    is_system_manager = frappe.db.exists(
        "Has Role",
        {
            "parent": user,
            "parenttype": "User",
            "role": "System Manager"
        }
    )

    if not branch:
        frappe.response["message"] = []
    else:
        # Administrator and System Manager can select any branch.
        unrestricted = user == "Administrator" or bool(is_system_manager)

        # Branch users may request only a branch assigned to their login.
        if not unrestricted:
            allowed_branch_map = {}

            user_permissions = frappe.db.get_all(
                "User Permission",
                filters={
                    "user": user,
                    "allow": "Branch"
                },
                fields=["for_value"],
                limit_page_length=500
            )

            for permission in user_permissions:
                permission_branch = permission.get("for_value")
                if permission_branch:
                    allowed_branch_map[permission_branch] = 1

            login_employees = frappe.db.get_all(
                "Employee",
                filters={
                    "user_id": user,
                    "status": "Active"
                },
                fields=["name", "branch", "custom_branch_list"],
                limit_page_length=20
            )

            for login_employee in login_employees:
                employee_branch = login_employee.get("branch")
                if employee_branch:
                    allowed_branch_map[employee_branch] = 1

                branch_list_text = login_employee.get("custom_branch_list") or ""
                for branch_part in branch_list_text.replace("\n", ",").split(","):
                    branch_part = branch_part.strip()
                    if branch_part:
                        allowed_branch_map[branch_part] = 1

                employee_branch_rows = frappe.db.get_all(
                    "Employee Branches",
                    filters={
                        "parent": login_employee.get("name"),
                        "parenttype": "Employee",
                        "parentfield": "custom_employee_branches"
                    },
                    fields=["branch"],
                    limit_page_length=500
                )

                for branch_row in employee_branch_rows:
                    row_branch = branch_row.get("branch")
                    if row_branch:
                        allowed_branch_map[row_branch] = 1

            requested_lower = branch.lower()
            permitted = branch in allowed_branch_map

            # Treat Vizag and Visakhapatnam as equivalent legacy names.
            if not permitted and requested_lower in ("vizag", "visakhapatnam"):
                permitted = "Vizag" in allowed_branch_map or "Visakhapatnam" in allowed_branch_map

            if not permitted:
                frappe.throw("You are not permitted to load employees for branch: " + branch)

        branch_names = [branch]
        branch_lower = branch.lower()
        if branch_lower == "vizag":
            branch_names.append("Visakhapatnam")
        elif branch_lower == "visakhapatnam":
            branch_names.append("Vizag")

        employee_map = {}
        employee_fields = [
            "name",
            "employee_name",
            "designation",
            "branch",
            "custom_branch_list",
            "status"
        ]

        # 1. Main Employee.branch
        primary_employees = frappe.db.get_all(
            "Employee",
            filters=[
                ["status", "=", "Active"],
                ["branch", "in", branch_names]
            ],
            fields=employee_fields,
            limit_page_length=5000
        )

        for employee in primary_employees:
            employee_map[employee.get("name")] = employee

        # 2. Generated Small Text list custom_branch_list
        for branch_name in branch_names:
            text_employees = frappe.db.get_all(
                "Employee",
                filters=[
                    ["status", "=", "Active"],
                    ["custom_branch_list", "like", "%" + branch_name + "%"]
                ],
                fields=employee_fields,
                limit_page_length=5000
            )

            for employee in text_employees:
                employee_map[employee.get("name")] = employee

        # 3. Employee.custom_employee_branches child table
        child_rows = frappe.db.get_all(
            "Employee Branches",
            filters=[
                ["parenttype", "=", "Employee"],
                ["parentfield", "=", "custom_employee_branches"],
                ["branch", "in", branch_names]
            ],
            fields=["parent"],
            limit_page_length=10000
        )

        child_parent_names = []
        child_parent_map = {}
        for child_row in child_rows:
            parent_name = child_row.get("parent")
            if parent_name and not child_parent_map.get(parent_name):
                child_parent_map[parent_name] = 1
                child_parent_names.append(parent_name)

        if child_parent_names:
            child_employees = frappe.db.get_all(
                "Employee",
                filters=[
                    ["status", "=", "Active"],
                    ["name", "in", child_parent_names]
                ],
                fields=employee_fields,
                limit_page_length=5000
            )

            for employee in child_employees:
                employee_map[employee.get("name")] = employee

        employees = []
        for employee_name in employee_map:
            employee = employee_map[employee_name]
            display_name = employee.get("employee_name") or ""
            designation = employee.get("designation") or ""

            # For Head Office, show only accounts-designation employees.
            if branch_lower == "head office":
                normalized_designation = " ".join(
                    designation.lower().replace("-", " ").split()
                )

                if normalized_designation not in head_office_designations:
                    continue

            if search_term:
                searchable = (display_name + " " + designation + " " + employee_name).lower()
                if search_term not in searchable:
                    continue

            employees.append(employee)

        employees.sort(key=lambda employee: (employee.get("employee_name") or "").lower())
        frappe.response["message"] = employees
