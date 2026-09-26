"""Client Package Conversion Client To Client

Original API: get_package_details
Source modified: 2026-06-03 23:16:15.279951
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

    def get_client_packages(client):

        data = frappe.get_all(
            "Client Package Conversion Client To Client",
            filters={"client_full_name": client},
            fields=["name"]
        )

        result = []

        for d in data:
            doc = frappe.get_doc("Client Package Conversion Client To Client", d.name)

            for row in doc.complete_package_details or []:
                result.append({
                    "therapy": frappe.db.get_value(
                        "Therapy Type",
                        row.complete_package_details_therapy_plans,
                        "therapy_type"
                    ),
                    "booked": row.booked_quantity,
                    "availed": row.availed_quantity,
                    "balance": row.balance_quantity
                })

        return result

    return frappe.call(get_client_packages, **dict(frappe.form_dict))
