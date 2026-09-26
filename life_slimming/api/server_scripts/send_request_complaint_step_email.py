"""Client Request And Complaint Form-Auto Fetch And Emails

Original API: send_request_complaint_step_email
Source modified: 2026-06-03 23:16:15.374289
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
    # Server Script API: send_request_complaint_step_email
    # Doctype: Client Request And Complaint Form
    # Step 2 opened -> Branch Email + Viveka
    # ============================================================

    docname = frappe.form_dict.get("docname")
    next_step = frappe.form_dict.get("next_step")

    if not docname or not next_step:
        frappe.response["message"] = {
            "status": "missing_data"
        }

    else:
        doc = frappe.get_doc(
            "Client Request And Complaint Form",
            docname
        )

        next_step = int(next_step)

        branch_email = doc.branch_email or ""

        if next_step == 2:
            receivers = []

            if branch_email:
                receivers.append(branch_email)

            receivers.append("Viveka@lifescc.com")

            subject = "Client Request / Complaint Pending Branch Verification"

        else:
            receivers = []
            subject = ""

        if next_step != 2:
            frappe.response["message"] = {
                "status": "no_email_for_this_step"
            }

        elif not receivers:
            frappe.response["message"] = {
                "status": "missing_email",
                "message": "Email not found"
            }

        else:
            form_link = frappe.utils.get_url_to_form(
                "Client Request And Complaint Form",
                doc.name
            )

            client = doc.client_name or doc.name1 or ""
            branch = doc.branch or ""
            phone = doc.phone_number or ""

            message = (
                "<p>Dear Team,</p>"
                "<p>A Client Request / Complaint Form has moved to "
                "<b>Step 2 - Branch Verification</b> and requires your action.</p>"
                "<p>"
                "<b>Client:</b> "
                + str(client)
                + "<br>"
                "<b>Branch:</b> "
                + str(branch)
                + "<br>"
                "<b>Phone:</b> "
                + str(phone)
                + "<br>"
                "<b>Form:</b> "
                + str(doc.name)
                + "</p>"
                "<p><a href='"
                + str(form_link)
                + "'>Click here to open the request / complaint form</a></p>"
                "<p>Regards,<br>ERPNext</p>"
            )

            frappe.sendmail(
                recipients=receivers,
                subject=subject,
                message=message,
                reference_doctype="Client Request And Complaint Form",
                reference_name=doc.name,
                now=True
            )

            frappe.response["message"] = {
                "status": "sent",
                "to": ", ".join(receivers)
            }
