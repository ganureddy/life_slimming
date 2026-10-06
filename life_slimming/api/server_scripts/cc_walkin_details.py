"""cc_walkin_details

Original API: cc_walkin_details
Source modified: 2026-09-13 11:53:14.048654
See ../CATALOG.md for migration notes and validation limits.
"""

import json
import re

import frappe
from frappe.integrations.utils import make_post_request as _make_post_request
from frappe.utils.safe_exec import read_sql as _read_sql
from frappe.utils.safe_exec import call_whitelisted_function as _call_whitelisted
from life_slimming.api._runtime import script_endpoint
from life_slimming.api.pd_form_utils import pd_form_urls


@script_endpoint(allow_guest=False)
def run(**kwargs):
    # Server Script: API
    # API Method: cc_walkin_details

    lead = (frappe.form_dict.get("lead") or "").strip()
    if not lead or not frappe.db.exists("Lead", lead):
        frappe.throw("Lead not found")

    patient = frappe.db.get_value("Patient", {"custom_lead": lead},
        ["name", "patient_name", "custom_pd_form_number"], as_dict=True)

    images = []
    seen_image_urls = []

    if patient:
        files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Patient",
                "attached_to_name": patient.get("name")
            },
            fields=[
                "name",
                "file_name",
                "file_url",
                "thumbnail_url",
                "attached_to_field",
                "creation"
            ],
            order_by="creation asc",
            ignore_permissions=True,
            limit_page_length=0
        )

        for file_row in files:
            fld = (
                file_row.get("attached_to_field") or ""
            ).lower()

            file_url = (
                file_row.get("file_url") or ""
            )

            is_pd_form = (
                fld == "pd_form"
                or fld == "custom_pd_form"
                or "pd_form" in fld
            )

            if (
                is_pd_form
                and file_url
                and file_url not in seen_image_urls
            ):
                seen_image_urls.append(file_url)

                images.append({
                    "name": (
                        file_row.get("file_name")
                        or "PD Form"
                    ),
                    "url": file_url,
                    "thumb": (
                        file_row.get("thumbnail_url")
                        or file_url
                    ),
                    "created": str(
                        file_row.get("creation") or ""
                    )
                })

        # PD Form child rows are the source of truth for several historical
        # uploads; those URLs may not have a matching File row.
        patient_doc = frappe.get_doc("Patient", patient.get("name"))
        for file_url in pd_form_urls(patient.get("name"), patient_doc):
            if file_url not in seen_image_urls:
                seen_image_urls.append(file_url)
                images.append({
                    "name": file_url.rsplit("/", 1)[-1] or "PD Form",
                    "url": file_url,
                    "thumb": file_url,
                    "created": "",
                })

    history = []
    comments = frappe.get_all("Comment",
        filters={"reference_doctype": "Lead", "reference_name": lead,
                 "comment_type": "Info", "content": ["like", "CC Walk-in Status:%"]},
        fields=["content", "creation", "comment_by", "owner"],
        order_by="creation desc", ignore_permissions=True, limit_page_length=100)
    for comment in comments:
        history.append({
            "details": comment.get("content") or "",
            "on": str(comment.get("creation") or ""),
            "by": comment.get("comment_by") or comment.get("owner") or ""
        })

    lead_data = frappe.db.get_value("Lead", lead,
        ["custom_remarks", "custom_appointment_status", "custom_status_updated_by_name",
         "custom_status_updated_on"], as_dict=True) or {}

    frappe.response["message"] = {
        "lead": lead,
        "remarks": lead_data.get("custom_remarks") or "",
        "status": lead_data.get("custom_appointment_status") or "",
        "updated_by": lead_data.get("custom_status_updated_by_name") or "",
        "updated_on": str(lead_data.get("custom_status_updated_on") or ""),
        "patient": patient.get("name") if patient else "",
        "pd_number": patient.get("custom_pd_form_number") if patient else "",
        "images": images,
        "history": history
    }
