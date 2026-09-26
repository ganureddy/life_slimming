"""Therapy Session Consent & After Photo

Original API: life_setup_therapy_session_media_fields
Source modified: 2026-08-25 16:47:13.919456
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
    # LIFE - Therapy Session media fields setup
    # Server Script Type: API
    # API Method: life_setup_therapy_session_media_fields

    created = []
    existing = []

    # ---------------------------------------------------------
    # 1. CLIENT CONSENT FORM - Therapy Session
    # ---------------------------------------------------------

    consent_fieldname = "custom_client_consent_form"

    if not frappe.db.exists(
        "Custom Field",
        {
            "dt": "Therapy Session",
            "fieldname": consent_fieldname
        }
    ):
        consent_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Therapy Session",
            "label": "Client Consent Form",
            "fieldname": consent_fieldname,
            "fieldtype": "Attach",
            "insert_after": "custom_client_consent_image_preview",
            "read_only": 0,
            "hidden": 0
        })

        consent_field.insert(ignore_permissions=True)
        created.append("Therapy Session → Client Consent Form")
    else:
        existing.append("Therapy Session → Client Consent Form")


    # ---------------------------------------------------------
    # 2. FIND CHILD TABLE USED BY "Client Photos in session"
    # ---------------------------------------------------------

    therapy_meta = frappe.get_meta("Therapy Session")

    photos_field = therapy_meta.get_field(
        "custom_client_photos_in_session"
    )

    child_doctype = None

    if photos_field:
        child_doctype = photos_field.options


    # ---------------------------------------------------------
    # 3. CREATE AFTER IMAGE FIELD IN CHILD TABLE
    # ---------------------------------------------------------

    if child_doctype:

        after_fieldname = "custom_after_image"

        if not frappe.db.exists(
            "Custom Field",
            {
                "dt": child_doctype,
                "fieldname": after_fieldname
            }
        ):
            child_meta = frappe.get_meta(child_doctype)

            insert_after = ""

            # Prefer placing After Image after existing attach_image
            if child_meta.get_field("attach_image"):
                insert_after = "attach_image"

            after_field = frappe.get_doc({
                "doctype": "Custom Field",
                "dt": child_doctype,
                "label": "After Image",
                "fieldname": after_fieldname,
                "fieldtype": "Attach Image",
                "insert_after": insert_after,
                "in_list_view": 1,
                "read_only": 0,
                "hidden": 0
            })

            after_field.insert(ignore_permissions=True)

            created.append(
                child_doctype + " → After Image"
            )

        else:
            existing.append(
                child_doctype + " → After Image"
            )

    else:
        frappe.throw(
            "Could not detect the child DocType for "
            "Therapy Session field custom_client_photos_in_session."
        )


    # ---------------------------------------------------------
    # CLEAR META CACHE
    # ---------------------------------------------------------

    frappe.clear_cache(doctype="Therapy Session")

    if child_doctype:
        frappe.clear_cache(doctype=child_doctype)


    # ---------------------------------------------------------
    # RESPONSE
    # ---------------------------------------------------------

    frappe.response["message"] = {
        "success": True,
        "created": created,
        "already_existing": existing,
        "photo_child_doctype": child_doctype,
        "consent_field": "custom_client_consent_form",
        "after_image_field": "custom_after_image"
    }
