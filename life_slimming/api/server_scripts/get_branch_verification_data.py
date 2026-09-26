"""Branch Verification And Information Form

Original API: get_branch_verification_data
Source modified: 2026-06-03 23:16:15.178242
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

    def get_branch_verification_data(patient):

        # ---------------------------
        # GET PATIENT
        # ---------------------------
        client = frappe.get_doc("Patient", patient)

        # ✅ JOINING DATE (REAL FIX)
        joining_date = client.get("creation")

        # ---------------------------
        # THERAPY PLAN (LATEST)
        # ---------------------------
        plan = frappe.get_all(
            "Therapy Plan",
            filters={"patient": patient},
            fields=[
                "name",
                "start_date",
                "due_date",
                "total_sessions",
                "total_sessions_completed"
            ],
            order_by="creation desc",
            limit=1
        )

        plan = plan[0] if plan else {}

        # ---------------------------
        # PAYMENT ENTRY (GROUPED)
        # ---------------------------
        payments = frappe.get_all(
            "Payment Entry",
            filters={
                "party_type": "Customer",
                "party": patient
            },
            fields=["mode_of_payment", "paid_amount"]
        )

        payment_modes = {}
        total_paid = 0

        for p in payments:
            mode = p.mode_of_payment or "Unknown"
            amt = float(p.paid_amount or 0)

            payment_modes[mode] = payment_modes.get(mode, 0) + amt
            total_paid += amt

        # ---------------------------
        # RESPONSE
        # ---------------------------
        return {
            "client_name": client.patient_name,
            "joining_date": joining_date,

            "package_start_date": plan.get("start_date"),
            "package_end_date": plan.get("due_date"),

            "total_sessions": plan.get("total_sessions") or 0,
            "sessions_completed": plan.get("total_sessions_completed") or 0,

            "payment_modes": payment_modes,
            "total_paid": total_paid
        }

    return frappe.call(get_branch_verification_data, **dict(frappe.form_dict))
