"""get_therapy_plans_for_patient

Original API: get_therapy_plans_for_patient
Source modified: 2026-06-03 23:16:15.129041
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
    patient = frappe.form_dict.get('patient')

    if not patient:
        frappe.throw('Patient is required')

    plans = frappe.get_all(
        'Therapy Plan',
        filters=[['patient', '=', patient], ['status', '!=', 'Completed']],
        fields=['name', 'status'],
        limit=500,
        ignore_permissions=True
    )

    plan_names = [p['name'] for p in plans]

    if not plan_names:
        frappe.response['message'] = {'plans': [], 'details': []}
    else:
        details = frappe.get_all(
            'Therapy Plan Detail',
            filters=[['parent', 'in', plan_names]],
            fields=['parent', 'therapy_type', 'no_of_sessions', 'sessions_completed'],
            limit=1000,
            ignore_permissions=True
        )
        frappe.response['message'] = {'plans': plans, 'details': details}
