"""LIFE Client 360 Branch Safe Patient Lookup

Original API: life_client360_branch_patient_lookup
Source modified: 2026-09-25 15:55:38.891427
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
    # LIFE CLIENT-360 — Branch-safe Patient Lookup API v2
    # API Method: life_client360_branch_patient_lookup
    # Allow Guest: NO
    #
    # This version is intentionally simple and GET-friendly.
    # It does not depend on frappe.client.get_list permissions for Patient search.

    args = frappe.form_dict or {}
    action = (args.get("action") or "search").strip()
    current_user = frappe.session.user

    excluded = ["testing branch", "head office", "ho", "ho cc"]

    # -----------------------------
    # Resolve allowed branch(es)
    # -----------------------------
    is_admin = False

    role_rows = frappe.get_all(
        "Has Role",
        filters={
            "parent": current_user,
            "parenttype": "User"
        },
        fields=["role"],
        limit_page_length=200,
        ignore_permissions=True
    )

    for rr in role_rows:
        if (rr.get("role") or "") == "System Manager":
            is_admin = True

    if current_user == "Administrator":
        is_admin = True

    allowed_branches = []

    emp_rows = frappe.get_all(
        "Employee",
        filters={
            "user_id": current_user,
            "status": "Active"
        },
        fields=["branch"],
        limit_page_length=20,
        ignore_permissions=True
    )

    for er in emp_rows:
        bv = (er.get("branch") or "").strip()
        if bv and bv not in allowed_branches and bv.lower() not in excluded:
            allowed_branches.append(bv)

    perm_rows = frappe.get_all(
        "User Permission",
        filters={
            "user": current_user,
            "allow": "Branch"
        },
        fields=["for_value"],
        limit_page_length=100,
        ignore_permissions=True
    )

    for pr in perm_rows:
        bv = (pr.get("for_value") or "").strip()
        if bv and bv not in allowed_branches and bv.lower() not in excluded:
            allowed_branches.append(bv)

    allowed_keys = []
    for bv in allowed_branches:
        bk = bv.lower().strip()
        if bk and bk not in allowed_keys:
            allowed_keys.append(bk)

    result = {
        "ok": 1,
        "user": current_user,
        "is_admin": is_admin,
        "branches": allowed_branches
    }

    # -----------------------------
    # SEARCH
    # -----------------------------
    if action == "search":
        q = (args.get("q") or "").strip()

        rows = []
        seen = []

        digits = ""
        alpha = False

        for ch in q:
            if ch >= "0" and ch <= "9":
                digits = digits + ch
            elif (
                (ch >= "A" and ch <= "Z")
                or
                (ch >= "a" and ch <= "z")
            ):
                alpha = True

        patient_fields = [
            "name",
            "patient_name",
            "first_name",
            "mobile",
            "sex",
            "customer",
            "branch_name",
            "custom_branch",
            "custom_joining_date",
            "creation",
            "modified"
        ]

        if digits and len(digits) >= 3 and not alpha:
            # Exact mobile first
            exact_rows = frappe.get_all(
                "Patient",
                filters={"mobile": digits},
                fields=patient_fields,
                limit_page_length=50,
                order_by="modified desc",
                ignore_permissions=True
            )

            for r in exact_rows:
                nm = r.get("name")
                if nm and nm not in seen:
                    seen.append(nm)
                    rows.append(r)

            # LIKE fallback
            if not rows:
                like_rows = frappe.get_all(
                    "Patient",
                    filters=[
                        ["mobile", "like", "%" + digits + "%"]
                    ],
                    fields=patient_fields,
                    limit_page_length=100,
                    order_by="modified desc",
                    ignore_permissions=True
                )

                for r in like_rows:
                    nm = r.get("name")
                    if nm and nm not in seen:
                        seen.append(nm)
                        rows.append(r)

            # formatted number fallback
            if (not rows) and len(digits) >= 5:
                probes = [digits[:5], digits[-5:]]

                for probe in probes:
                    like_rows = frappe.get_all(
                        "Patient",
                        filters=[
                            ["mobile", "like", "%" + probe + "%"]
                        ],
                        fields=patient_fields,
                        limit_page_length=100,
                        order_by="modified desc",
                        ignore_permissions=True
                    )

                    for r in like_rows:
                        nm = r.get("name")
                        if nm and nm not in seen:
                            seen.append(nm)
                            rows.append(r)
        else:
            if len(q) >= 3:
                name_rows = frappe.get_all(
                    "Patient",
                    filters=[
                        ["patient_name", "like", "%" + q + "%"]
                    ],
                    fields=patient_fields,
                    limit_page_length=100,
                    order_by="modified desc",
                    ignore_permissions=True
                )

                for r in name_rows:
                    nm = r.get("name")
                    if nm and nm not in seen:
                        seen.append(nm)
                        rows.append(r)

        names = []
        for r in rows:
            nm = r.get("name")
            if nm:
                names.append(nm)

        child_map = {}

        if names:
            child_rows = frappe.get_all(
                "Multiple Branches",
                filters=[
                    ["parenttype", "=", "Patient"],
                    ["parent", "in", names]
                ],
                fields=["parent", "branch"],
                limit_page_length=2000,
                ignore_permissions=True
            )

            for cr in child_rows:
                parent = cr.get("parent")
                branch = (cr.get("branch") or "").strip()

                if parent and branch:
                    if parent not in child_map:
                        child_map[parent] = []

                    if branch not in child_map[parent]:
                        child_map[parent].append(branch)

        output = []

        for r in rows:
            patient_name = r.get("name")
            branches = []

            for bv in [
                r.get("branch_name"),
                r.get("custom_branch")
            ]:
                bv = (bv or "").strip()
                if bv and bv.lower() not in excluded and bv not in branches:
                    branches.append(bv)

            for bv in child_map.get(patient_name, []):
                bv = (bv or "").strip()
                if bv and bv.lower() not in excluded and bv not in branches:
                    branches.append(bv)

            allowed = is_admin

            if not allowed:
                for bv in branches:
                    if bv.lower().strip() in allowed_keys:
                        allowed = True

            if allowed:
                output.append({
                    "name": patient_name,
                    "patient_name": r.get("patient_name") or r.get("first_name") or patient_name,
                    "mobile": r.get("mobile") or "",
                    "sex": r.get("sex") or "",
                    "customer": r.get("customer") or "",
                    "branch_name": r.get("branch_name") or r.get("custom_branch") or "",
                    "custom_branch": r.get("custom_branch") or r.get("branch_name") or "",
                    "branches": branches,
                    "custom_joining_date": str(r.get("custom_joining_date") or ""),
                    "creation": str(r.get("creation") or "")
                })

                if len(output) >= 30:
                    break

        result["rows"] = output
        result["candidate_count"] = len(rows)

    # -----------------------------
    # ONE PATIENT FULL ROW
    # -----------------------------
    elif action == "row":
        patient = (args.get("patient") or "").strip()

        pats = frappe.get_all(
            "Patient",
            filters={"name": patient},
            fields=[
                "name",
                "patient_name",
                "first_name",
                "mobile",
                "sex",
                "customer",
                "branch_name",
                "custom_branch",
                "custom_joining_date",
                "creation"
            ],
            limit_page_length=1,
            ignore_permissions=True
        )

        if not pats:
            result = {
                "ok": 0,
                "error": "PATIENT_NOT_FOUND",
                "user": current_user,
                "branches": allowed_branches
            }
        else:
            p = pats[0]

            child_rows = frappe.get_all(
                "Multiple Branches",
                filters=[
                    ["parenttype", "=", "Patient"],
                    ["parent", "=", patient]
                ],
                fields=["branch"],
                limit_page_length=100,
                ignore_permissions=True
            )

            branches = []

            for bv in [
                p.get("branch_name"),
                p.get("custom_branch")
            ]:
                bv = (bv or "").strip()
                if bv and bv.lower() not in excluded and bv not in branches:
                    branches.append(bv)

            for cr in child_rows:
                bv = (cr.get("branch") or "").strip()
                if bv and bv.lower() not in excluded and bv not in branches:
                    branches.append(bv)

            allowed = is_admin

            if not allowed:
                for bv in branches:
                    if bv.lower().strip() in allowed_keys:
                        allowed = True

            if not allowed:
                result = {
                    "ok": 0,
                    "error": "PATIENT_NOT_IN_USER_BRANCH",
                    "user": current_user,
                    "branches": allowed_branches
                }
            else:
                plans = frappe.get_all(
                    "Therapy Plan",
                    filters={"patient": patient},
                    fields=[
                        "name",
                        "patient",
                        "patient_name",
                        "start_date",
                        "due_date",
                        "branch",
                        "custom_health_status",
                        "status",
                        "total_sessions",
                        "total_sessions_completed"
                    ],
                    limit_page_length=1000,
                    order_by="start_date asc",
                    ignore_permissions=True
                )

                invoices = frappe.get_all(
                    "Sales Invoice",
                    filters={
                        "patient": patient,
                        "docstatus": 1
                    },
                    fields=[
                        "name",
                        "patient",
                        "posting_date",
                        "due_date",
                        "base_grand_total",
                        "outstanding_amount",
                        "status",
                        "is_return",
                        "branch"
                    ],
                    limit_page_length=3000,
                    order_by="posting_date desc",
                    ignore_permissions=True
                )

                sessions = frappe.get_all(
                    "Therapy Session",
                    filters=[
                        ["patient", "=", patient],
                        ["docstatus", "!=", 2]
                    ],
                    fields=[
                        "name",
                        "patient",
                        "start_date",
                        "creation",
                        "branch"
                    ],
                    limit_page_length=5000,
                    order_by="start_date desc",
                    ignore_permissions=True
                )

                result["patient"] = {
                    "name": p.get("name"),
                    "patient_name": p.get("patient_name") or p.get("first_name") or p.get("name"),
                    "mobile": p.get("mobile") or "",
                    "sex": p.get("sex") or "",
                    "customer": p.get("customer") or "",
                    "branch_name": p.get("branch_name") or p.get("custom_branch") or "",
                    "custom_branch": p.get("custom_branch") or p.get("branch_name") or "",
                    "branches": branches,
                    "custom_joining_date": str(p.get("custom_joining_date") or ""),
                    "creation": str(p.get("creation") or "")
                }
                result["plans"] = plans
                result["invoices"] = invoices
                result["sessions"] = sessions

    else:
        result = {
            "ok": 0,
            "error": "UNKNOWN_ACTION",
            "user": current_user,
            "branches": allowed_branches
        }

    frappe.response["message"] = result
