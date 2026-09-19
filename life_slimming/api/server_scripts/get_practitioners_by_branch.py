"""get_practitioners_by_branch

Original API: get_practitioners_by_branch
Source modified: 2026-06-03 23:16:15.166304
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
    branch = frappe.form_dict.branch

    practitioners = []

    records = frappe.get_all(
        "Healthcare Practitioner",
        fields=["name"]
    )

    for p in records:

        doc = frappe.get_doc("Healthcare Practitioner", p.name)

        if doc.branch == branch:
            practitioners.append(doc.name)
            continue

        for row in doc.custom_branch_list:

            if row.branch == branch:
                practitioners.append(doc.name)
                break

    frappe.response["message"] = practitioners
