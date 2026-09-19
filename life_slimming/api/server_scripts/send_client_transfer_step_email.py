"""Client Transfer Request Form -Emalis

Original API: send_client_transfer_step_email
Source modified: 2026-06-03 23:16:15.362770
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
    # Server Script API: send_client_transfer_step_email
    # Doctype: Client Transfer Request Form
    # Step 2 = Section 6 opened -> Branch Email + Viveka + Accounts
    # ============================================================

    docname = frappe.form_dict.get("docname")
    next_step = frappe.form_dict.get("next_step")

    if not docname or not next_step:
        frappe.response["message"] = {
            "status": "missing_data"
        }

    else:
        doc = frappe.get_doc(
            "Client Transfer Request Form",
            docname
        )

        next_step = int(next_step)

        branch_email = doc.branch_email or ""

        if next_step == 2:
            receivers = []

            if branch_email:
                receivers.append(branch_email)

            receivers.append("Viveka@lifescc.com")
            receivers.append("accounts@lifescc.com")

            subject = "Client Transfer Request Pending Receiving Branch Review"

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
                "message": "Email not found for this step"
            }

        else:
            form_link = frappe.utils.get_url_to_form(
                "Client Transfer Request Form",
                doc.name
            )

            client = doc.client_full_name or doc.client_name or ""
            from_branch = doc.transfer_from_branch or ""
            to_branch = doc.transfer_to_branch or ""
            mobile = doc.mobile_number or ""

            message = (
                "<p>Dear Team,</p>"
                "<p>A Client Transfer Request has moved to "
                "<b>Section 6</b> and requires your action.</p>"
                "<p>"
                "<b>Client:</b> "
                + str(client)
                + "<br>"
                "<b>From Branch:</b> "
                + str(from_branch)
                + "<br>"
                "<b>To Branch:</b> "
                + str(to_branch)
                + "<br>"
                "<b>Mobile:</b> "
                + str(mobile)
                + "<br>"
                "<b>Form:</b> "
                + str(doc.name)
                + "</p>"
                "<p><a href='"
                + str(form_link)
                + "'>Click here to open the transfer request</a></p>"
                "<p>Regards,<br>ERPNext</p>"
            )

            frappe.sendmail(
                recipients=receivers,
                subject=subject,
                message=message,
                reference_doctype="Client Transfer Request Form",
                reference_name=doc.name,
                now=True
            )

            frappe.response["message"] = {
                "status": "sent",
                "to": ", ".join(receivers)
            }
