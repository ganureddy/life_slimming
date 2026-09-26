"""Client  Package Conversion Cloent To Client-Emails

Original API: send_client_conversion_step_email
Source modified: 2026-06-15 15:51:55.464563
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
    # Server Script API: send_client_conversion_step_email
    # Doctype: Client Package Conversion Client To Client
    #
    # Purpose:
    # Sends email notification with web page link when a request
    # moves from one approval step to the next.
    #
    # Flow:
    # Step 2 = After Branch / Step 1 submission
    #          Mail goes to Audit / Corporate Team
    #
    # Step 3 = After Audit / Corporate approval
    #          Mail goes to Operations COO / Management
    #
    # Step 4 = After Final approval
    #          Mail goes to ERP / CRM update person
    #
    # TEMPORARY MAIL CONTROL:
    # SEND_EMAILS = True  -> Emails will be sent
    # SEND_EMAILS = False -> Emails will NOT be sent
    # ============================================================

    SEND_EMAILS = False

    WEB_PAGE_ROUTE = "/package-conversion-client-to-client"

    DOCTYPE = "Client Package Conversion Client To Client"

    docname = frappe.form_dict.get("docname")
    next_step = frappe.form_dict.get("next_step")

    if not docname or not next_step:
        frappe.response["message"] = {
            "status": "missing_data",
            "message": "Document name or next step is missing."
        }

    else:
        try:
            next_step = int(next_step)

            doc = frappe.get_doc(DOCTYPE, docname)

            # ------------------------------------------------------------
            # Email recipients based on next approval step
            # ------------------------------------------------------------
            step_email_map = {
                2: {
                    "to": [
                        "kishore@lifescc.com",
                        "vivekaarvind@gmail.com",
                        "audit@lifescc.com"
                    ],
                    "subject": "Client Package Conversion Pending Audit / Corporate Review",
                    "step_title": "Audit / Corporate Review"
                },

                3: {
                    "to": [
                        "bhuvan@lifessc.com"
                    ],
                    "subject": "Client Package Conversion Pending Operations COO / Management Approval",
                    "step_title": "Operations COO / Management Approval"
                },

                4: {
                    "to": [
                        "Narendhar@lifescc.com"
                    ],
                    "subject": "Client Package Conversion Approved - ERP / CRM Update Required",
                    "step_title": "ERP / CRM Update"
                }
            }

            if next_step not in step_email_map:
                frappe.response["message"] = {
                    "status": "no_email_for_this_step",
                    "message": "No email configured for this step."
                }

            else:
                email_data = step_email_map[next_step]
                receivers = email_data.get("to") or []

                final_receivers = []

                for email in receivers:
                    if email:
                        final_receivers.append(email)

                if not final_receivers:
                    frappe.response["message"] = {
                        "status": "missing_email",
                        "message": "No recipient email found for this step."
                    }

                else:
                    # ------------------------------------------------------------
                    # Custom web page link
                    # Example:
                    # https://portal.lifescc.com/package-conversion-client-to-client?request=DOCNAME
                    # ------------------------------------------------------------
                    form_link = frappe.utils.get_url(
                        WEB_PAGE_ROUTE + "?request=" + doc.name
                    )

                    transferor = doc.client_full_name or ""
                    transferee = doc.client_name or ""
                    branch = doc.branch or ""
                    mobile = doc.mobile_number or ""
                    conversion_status = doc.conversion_status or ""
                    step_title = email_data.get("step_title") or "Next Approval Step"

                    message = (
                        "<p>Dear Team,</p>"

                        "<p>A <b>Client Package Conversion</b> request has moved to the next approval stage.</p>"

                        "<p>"
                        "<b>Pending Step:</b> "
                        + str(step_title)
                        + "<br>"

                        "<b>Current Step No:</b> Step "
                        + str(next_step)
                        + "<br>"

                        "<b>Current Status:</b> "
                        + str(conversion_status)
                        + "</p>"

                        "<p>"
                        "<b>Request ID:</b> "
                        + str(doc.name)
                        + "<br>"

                        "<b>Branch:</b> "
                        + str(branch)
                        + "<br>"

                        "<b>Transferor Client:</b> "
                        + str(transferor)
                        + "<br>"

                        "<b>Receiving Client:</b> "
                        + str(transferee)
                        + "<br>"

                        "<b>Mobile:</b> "
                        + str(mobile)
                        + "</p>"

                        "<p>"
                        "<a href='"
                        + str(form_link)
                        + "' "
                        + "style='display:inline-block;padding:10px 16px;background:#198754;color:#ffffff;"
                        + "text-decoration:none;border-radius:6px;font-weight:bold;'>"
                        + "Open Conversion Request"
                        + "</a>"
                        + "</p>"

                        "<p>If the button does not work, copy and open this link:</p>"
                        "<p>"
                        + str(form_link)
                        + "</p>"

                        "<p>Regards,<br>ERPNext</p>"
                    )

                    if not SEND_EMAILS:
                        frappe.response["message"] = {
                            "status": "email_temporarily_disabled",
                            "to": ", ".join(final_receivers),
                            "link": form_link,
                            "message": "Email sending is temporarily disabled. No email was sent."
                        }

                    else:
                        frappe.sendmail(
                            recipients=final_receivers,
                            subject=email_data["subject"],
                            message=message,
                            reference_doctype=DOCTYPE,
                            reference_name=doc.name,
                            now=True
                        )

                        frappe.response["message"] = {
                            "status": "sent",
                            "to": ", ".join(final_receivers),
                            "link": form_link,
                            "message": "Email sent successfully."
                        }

        except Exception as e:
            frappe.response["message"] = {
                "status": "failed",
                "message": str(e)
            }
