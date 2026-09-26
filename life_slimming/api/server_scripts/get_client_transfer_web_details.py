"""Client Transfer Request Form-Web Form Data Fetch

Original API: get_client_transfer_web_details
Source modified: 2026-06-03 23:16:15.290973
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
    patient = frappe.form_dict.get("patient")
    if patient:
        frappe.get_doc("Patient", patient).check_permission("read")

    patient = frappe.form_dict.get("patient")

    if not patient:
        frappe.response["message"] = {
            "success": False,
            "message": "Patient is required"
        }

    else:
        data = {
            "client": patient,
            "client_full_name": patient,
            "client_id__crm_no": patient,
            "client_name": patient,
            "mobile_number": "",
            "date_of_brith": "",
            "gender": "",
            "email_id": "",
            "currente_address": "",
            "transfer_from_branch": "",
            "t_billed_rs": 0,
            "total_received_rs": 0,
            "balance_duers": 0,
            "nil_dues__account_fully_clear_transfer_may_proceed": 0,
            "dues_pending_transfer_blocked": 0,
            "package_service_being_transferred": []
        }

        # -----------------------------
        # PATIENT DETAILS
        # -----------------------------
        try:
            p = frappe.get_doc("Patient", patient)

            data["client"] = p.name
            data["client_full_name"] = p.name
            data["client_id__crm_no"] = p.name
            data["client_name"] = p.name

            data["mobile_number"] = (
                p.get("mobile")
                or p.get("mobile_no")
                or p.get("phone")
                or p.get("contact_mobile")
                or ""
            )

            data["date_of_brith"] = (
                p.get("dob")
                or p.get("date_of_birth")
                or ""
            )

            data["gender"] = (
                p.get("sex")
                or p.get("gender")
                or ""
            )

            data["email_id"] = (
                p.get("email")
                or p.get("email_id")
                or ""
            )

            data["currente_address"] = (
                p.get("address")
                or p.get("address_line1")
                or p.get("patient_details")
                or ""
            )

            data["transfer_from_branch"] = (
                p.get("branch")
                or p.get("custom_branch")
                or p.get("territory")
                or ""
            )

        except Exception as e:
            pass

        # -----------------------------
        # BILLING DETAILS
        # -----------------------------
        total_billed = 0
        total_received = 0
        balance_due = 0

        try:
            invoices = frappe.get_all(
                "Sales Invoice",
                filters={
                    "patient": patient,
                    "docstatus": 1
                },
                fields=[
                    "name",
                    "grand_total",
                    "rounded_total",
                    "outstanding_amount"
                ],
                limit_page_length=500
            )

            for inv in invoices:
                billed = inv.get("grand_total") or inv.get("rounded_total") or 0
                outstanding = inv.get("outstanding_amount") or 0

                total_billed = total_billed + billed
                balance_due = balance_due + outstanding

            total_received = total_billed - balance_due

        except Exception as e:
            try:
                invoices = frappe.get_all(
                    "Sales Invoice",
                    filters={
                        "customer": patient,
                        "docstatus": 1
                    },
                    fields=[
                        "name",
                        "grand_total",
                        "rounded_total",
                        "outstanding_amount"
                    ],
                    limit_page_length=500
                )

                for inv in invoices:
                    billed = inv.get("grand_total") or inv.get("rounded_total") or 0
                    outstanding = inv.get("outstanding_amount") or 0

                    total_billed = total_billed + billed
                    balance_due = balance_due + outstanding

                total_received = total_billed - balance_due

            except Exception as e:
                pass

        data["t_billed_rs"] = total_billed
        data["total_received_rs"] = total_received
        data["balance_duers"] = balance_due

        if balance_due and balance_due > 0:
            data["dues_pending_transfer_blocked"] = 1
            data["nil_dues__account_fully_clear_transfer_may_proceed"] = 0
        else:
            data["dues_pending_transfer_blocked"] = 0
            data["nil_dues__account_fully_clear_transfer_may_proceed"] = 1

        # -----------------------------
        # PACKAGE / THERAPY DETAILS
        # -----------------------------
        package_rows = []

        try:
            therapy_plans = frappe.get_all(
                "Therapy Plan",
                filters={
                    "patient": patient
                },
                fields=["name"],
                limit_page_length=200
            )

            for tp in therapy_plans:
                tp_doc = frappe.get_doc("Therapy Plan", tp.name)

                # Read all child tables inside Therapy Plan
                for table_field in tp_doc.meta.get_table_fields():
                    child_rows = tp_doc.get(table_field.fieldname) or []

                    for row in child_rows:
                        service_name = (
                            row.get("service")
                            or row.get("service_name")
                            or row.get("therapy")
                            or row.get("therapy_type")
                            or row.get("item_code")
                            or row.get("item_name")
                            or row.get("package")
                            or row.get("package_name")
                            or ""
                        )

                        sessions_booked = (
                            row.get("sessions_booked")
                            or row.get("no_of_sessions")
                            or row.get("sessions")
                            or row.get("qty")
                            or 0
                        )

                        sessions_completed = (
                            row.get("sessions_completed")
                            or row.get("completed_sessions")
                            or row.get("consumed_sessions")
                            or 0
                        )

                        sessions_remaining = sessions_booked - sessions_completed

                        if service_name:
                            package_rows.append({
                                "service__name": service_name,
                                "service_name": service_name,
                                "sessions_booked": sessions_booked,
                                "sessions_completed": sessions_completed,
                                "sessions_remaining": sessions_remaining,
                                "balance_session": sessions_remaining
                            })

        except Exception as e:
            pass

        data["package_service_being_transferred"] = package_rows

        frappe.response["message"] = {
            "success": True,
            "data": data
        }
