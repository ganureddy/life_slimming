"""get_branch_consultants

Original API: get_branch_consultants
Source modified: 2026-06-03 23:16:14.934631
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
    branch = frappe.form_dict.get('branch', '')
    txt = frappe.form_dict.get('txt', '')

    results = _read_sql("""
    SELECT DISTINCT hp.name, hp.practitioner_name
    FROM `tabHealthcare Practitioner` hp
    WHERE hp.status = 'Active'
    AND (
        hp.branch = %(branch)s
        OR EXISTS (
            SELECT 1 FROM `tabPractitioner Branches` pb
            WHERE pb.parent = hp.name AND pb.branch = %(branch)s
        )
    )
    AND hp.practitioner_name LIKE %(txt)s
    ORDER BY hp.practitioner_name
    LIMIT 20
""", {'branch': branch, 'txt': '%' + txt + '%'}, as_dict=True)

    frappe.response['message'] = results
