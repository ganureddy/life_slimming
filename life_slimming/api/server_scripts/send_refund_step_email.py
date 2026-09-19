"""Client Refund Request Form

Original API: send_refund_step_email
Source modified: 2026-06-03 23:16:15.322660
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
    # Server Script API: send_refund_step_email
    # Doctype: Client Refund Request Form
    # Step 2 -> Branch Email + Viveka
    # Step 3 -> Audit Manager
    # Step 4 -> COO / MD
    # Step 5 -> Accounts
    # ============================================================

    docname = frappe.form_dict.get("docname")
    next_step = frappe.form_dict.get("next_step")

    if not docname or not next_step:
        frappe.response["message"] = {
            "status": "missing_data"
        }

    else:
        doc = frappe.get_doc("Client Refund Request Form", docname)
        next_step = int(next_step)

        branch_email = doc.branch_email or ""

        # Step 2 recipients
        step_2_recipients = []

        if branch_email:
            step_2_recipients.append(branch_email)

        step_2_recipients.append("viveka@lifescc.com")

        step_email_map = {
            2: {
                "to": step_2_recipients,
                "subject": "Refund Request Pending Branch Manager Review"
            },
            3: {
                "to": ["audit@lifescc.com"],
                "subject": "Refund Request Pending Audit Manager Verification"
            },
            4: {
                "to": ["bhuvan@lifescc.com"],
                "subject": "Refund Request Pending COO / MD Approval"
            },
            5: {
                "to": ["account@lifescc.com"],
                "subject": "Refund Request Pending Accounts Payment Processing"
            }
        }

        if next_step not in step_email_map:
            frappe.response["message"] = {
                "status": "no_email_for_this_step"
            }

        else:
            email_data = step_email_map[next_step]
            receivers = email_data.get("to") or []

            if not receivers:
                frappe.response["message"] = {
                    "status": "missing_email",
                    "message": "Email not found for this step"
                }

            else:
                form_link = frappe.utils.get_url_to_form(
                    "Client Refund Request Form",
                    doc.name
                )

                client = doc.client_full_name or doc.client_name or ""
                branch = doc.branch or doc.branch_visited or ""
                mobile = doc.mobile_number or ""

                message = (
                    "<p>Dear Team,</p>"
                    "<p>A refund request has moved to <b>Step "
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
                    + "'>Click here to open the refund request</a></p>"
                    "<p>Regards,<br>ERPNext</p>"
                )

                frappe.sendmail(
                    recipients=receivers,
                    subject=email_data["subject"],
                    message=message,
                    reference_doctype="Client Refund Request Form",
                    reference_name=doc.name,
                    now=True
                )

                frappe.response["message"] = {
                    "status": "sent",
                    "to": ", ".join(receivers)
                }
