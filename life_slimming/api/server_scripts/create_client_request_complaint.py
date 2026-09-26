"""Submitting client Complaint api

Original API: create_client_request_complaint
Source modified: 2026-06-15 03:24:49.254047
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


    try:
        data = frappe.form_dict.get("doc")

        if not data:
            frappe.throw("No request data received.")

        if isinstance(data, str):
            doc_data = json.loads(data)
        else:
            doc_data = data

        doc_data["doctype"] = "Client Request And Complaint Form"

        doc = frappe.get_doc(doc_data)
        doc.insert(ignore_permissions=True)

        frappe.response["message"] = {
            "status": "success",
            "name": doc.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Client Request Complaint Submit Failed")

        frappe.response["message"] = {
            "status": "failed",
            "error": str(e)
        }
