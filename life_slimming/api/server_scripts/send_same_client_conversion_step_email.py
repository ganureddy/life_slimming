"""LIFE Client Package Conversion Same Client Package To Package

Original API: send_same_client_conversion_step_email
Source modified: 2026-06-03 23:16:15.351540
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
    # ============================================================
    # Server Script API: send_same_client_conversion_step_email
    # Doctype: LIFE Client Package Conversion Same Client Package To Package
    #
    # Step 2 = Section 6 opened -> Branch Email
    # Step 3 = Section 7 opened -> Narendhar
    # ============================================================

    docname = frappe.form_dict.get("docname")
    next_step = frappe.form_dict.get("next_step")

    if not docname or not next_step:
        frappe.response["message"] = {
            "status": "missing_data"
        }

    else:
        doc = frappe.get_doc(
            "LIFE Client Package Conversion Same Client Package To Package",
            docname
        )

        next_step = int(next_step)

        branch_email = doc.branch_email or ""

        if next_step == 2:
            receivers = []

            if branch_email:
                receivers.append(branch_email)

            subject = "Same Client Package Conversion Pending Clinic Approval"

        elif next_step == 3:
            receivers = [
                "Narendhar@lifescc.com"
            ]

            subject = "Same Client Package Conversion Pending ERP / CRM Update"

        else:
            receivers = []
            subject = ""

        if not receivers:
            frappe.response["message"] = {
                "status": "missing_email",
                "message": "Email not found for this step"
            }

        else:
            form_link = frappe.utils.get_url_to_form(
                "LIFE Client Package Conversion Same Client Package To Package",
                doc.name
            )

            client = doc.client_name or ""
            branch = doc.branch or ""
            mobile = doc.mobile_number or ""

            message = (
                "<p>Dear Team,</p>"
                "<p>A Same Client Package Conversion form has moved to "
                "<b>Step "
                + str(next_step)
                + "</b> and requires your action.</p>"
                "<p>"
                "<b>Client:</b> "
                + str(client)
                + "<br>"
                "<b>Branch:</b> "
                + str(branch)
                + "<br>"
                "<b>Mobile:</b> "
                + str(mobile)
                + "<br>"
                "<b>Form:</b> "
                + str(doc.name)
                + "</p>"
                "<p><a href='"
                + str(form_link)
                + "'>Click here to open the conversion request</a></p>"
                "<p>Regards,<br>ERPNext</p>"
            )

            frappe.sendmail(
                recipients=receivers,
                subject=subject,
                message=message,
                reference_doctype="LIFE Client Package Conversion Same Client Package To Package",
                reference_name=doc.name,
                now=True
            )

            frappe.response["message"] = {
                "status": "sent",
                "to": ", ".join(receivers)
            }
