"""Operations & Service Module Healthcare Practitioner Names

Original API: life_ops_branch_practitioners
Source modified: 2026-09-10 17:44:19.214584
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
    # LIFE Operations — Branch Practitioner Search
    # Server Script Type: API
    # API Method: life_ops_branch_practitioners
    # Allow Guest: OFF
    #
    # Purpose:
    # Return ACTIVE Healthcare Practitioners whose selected branch is either:
    # 1) Main Healthcare Practitioner.branch
    # 2) custom_branch_list child table (Employee Branches)
    # 3) custom_branch_list_text
    # 4) custom_additional_branches
    #
    # This server-side method is required because browser-side
    # frappe.client.get_list("Employee Branches") raises:
    # frappe.PermissionError -> check_parent_permission(parent, doctype)

    branch = (frappe.form_dict.get("branch") or "").strip()

    def norm(value):
        value = (value or "").strip().lower()

        if value.endswith(" branch"):
            value = value[:-7].strip()

        value = " ".join(value.split())

        aliases = {
            "srn": "sr nagar",
            "s r nagar": "sr nagar",
            "srnagar": "sr nagar",
            "kp": "kukatpally",
            "chn": "chandanagar",
            "mp": "madhapur",
            "dsk": "dilsukhnagar",
            "hn": "himayatnagar",
            "gcb": "gachibowli",
            "vja": "vijayawada",
            "vz": "vizag",
            "nlr": "nellore",
            "bh": "banjara hills",
            "ho": "head office"
        }

        return aliases.get(value, value)

    selected = norm(branch)

    def matches(value):
        raw = (value or "").strip()

        if not raw:
            return False

        if norm(raw) == selected:
            return True

        parts = raw.replace("\n", ",").replace(";", ",").replace("|", ",").split(",")

        for part in parts:
            if norm(part) == selected:
                return True

        return False

    rows = []

    if selected:
        practitioners = frappe.get_all(
            "Healthcare Practitioner",
            filters={"status": "Active"},
            fields=[
                "name",
                "practitioner_name",
                "status",
                "branch",
                "designation",
                "department",
                "custom_branch_list_text",
                "custom_additional_branches",
                "custom_available_all_branches"
            ],
            order_by="practitioner_name asc",
            limit_page_length=2000
        )

        for p in practitioners:
            matched = False
            matched_children = []

            # 1) Exact child-table check.
            try:
                doc = frappe.get_doc("Healthcare Practitioner", p.name)

                children = doc.get("custom_branch_list") or []

                for child in children:
                    child_branch = (
                        child.get("transfer_branch")
                        or child.get("custom_transfer_branch")
                        or child.get("branch")
                        or child.get("branch_name")
                        or child.get("custom_branch")
                        or child.get("custom_branch_name")
                        or child.get("employee_branch")
                        or child.get("location")
                        or ""
                    )

                    # Extra safety: dynamically inspect any child field containing
                    # "branch" or "location".
                    if not child_branch:
                        for key in child.as_dict():
                            key_l = (key or "").lower()

                            if "branch" in key_l or "location" in key_l:
                                val = child.get(key)

                                if val:
                                    child_branch = val
                                    break

                    if matches(child_branch):
                        matched = True
                        matched_children.append({
                            "branch": child_branch
                        })

            except Exception:
                # Continue with text/main-branch fallback.
                pass

            # 2) Branch List Text fallback.
            if not matched and matches(p.get("custom_branch_list_text")):
                matched = True

            # 3) Additional Branches fallback.
            if not matched and matches(p.get("custom_additional_branches")):
                matched = True

            # 4) Main Branch fallback.
            if not matched and matches(p.get("branch")):
                matched = True

            if matched:
                rows.append({
                    "name": p.get("name"),
                    "practitioner_name": p.get("practitioner_name"),
                    "status": p.get("status"),
                    "branch": p.get("branch"),
                    "designation": p.get("designation"),
                    "department": p.get("department"),
                    "custom_branch_list_text": p.get("custom_branch_list_text"),
                    "custom_additional_branches": p.get("custom_additional_branches"),
                    "custom_available_all_branches": p.get("custom_available_all_branches"),
                    "custom_branch_list": matched_children
                })

    frappe.response["message"] = rows
