"""feedback

Original API: life_rise.api.get_session_details
Source modified: 2026-06-03 23:16:14.737964
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
    import frappe

    def get_session_details(session):
        return frappe.db.get_value(
            "Therapy Session",
            session,
            [
                "patient_name",
                "practitioner",
                "start_date",
                "custom_remaining_sessions"
            ],
            as_dict=True
        )

    return frappe.call(get_session_details, **dict(frappe.form_dict))
