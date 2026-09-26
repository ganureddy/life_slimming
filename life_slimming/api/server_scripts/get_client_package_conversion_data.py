"""Client Package Conversion Same Client Package to Package

Original API: get_client_package_conversion_data
Source modified: 2026-06-03 23:16:15.192124
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

    def client_package_conversion_data(patient):

        result = {}

        # ================= PATIENT =================
        if frappe.db.exists("Patient", patient):
            p = frappe.get_doc("Patient", patient)

            result["patient"] = {
                "mobile": p.mobile_no,
                "email": p.email_id,
                "dob": p.dob,
                "address": p.custom_client_address
            }

        # ================= PAYMENT ENTRY =================
        payments = frappe.get_all("Payment Entry",
            filters={"party_type": "Patient", "party": patient, "docstatus": 1},
            fields=["paid_amount", "mode_of_payment"]
        )

        total = 0
        mode_map = {}

        for d in payments:
            amt = float(d.paid_amount or 0)
            mode = d.mode_of_payment or "Unknown"

            total += amt
            mode_map[mode] = mode_map.get(mode, 0) + amt

        result["payments"] = {
            "total": total,
            "modes": "\n".join([f"{k} = ₹{v}" for k, v in mode_map.items()])
        }

        # ================= THERAPY PLAN =================
        plan = frappe.get_all("Therapy Plan",
            filters={"patient": patient},
            fields=["start_date", "due_date"],
            order_by="creation desc",
            limit=1
        )

        result["therapy"] = plan[0] if plan else {}

        return result

    return frappe.call(client_package_conversion_data, **dict(frappe.form_dict))
