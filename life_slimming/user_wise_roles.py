import frappe
import traceback,sys

def get_roles(user=None, with_standard=True):
    try:
        if not user:
            user = frappe.session.user
        if user == 'Guest':
            return ['Guest']
        def get():
            return [r[0] for r in frappe.db.sql("""select role from `tabUserRole`
                where parent=%s and role not in ('All', 'Guest')""", (user,))] + ['All', 'Guest']

        roles = frappe.cache().hget("roles", user, get)

        if not with_standard:
            roles = filter(lambda x: x not in ['All', 'Guest', 'Administrator'], roles)
            
        return roles
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "get_roles")

import frappe
import requests

def send_whatsapp_on_change(doc, method):
    """
    Send WhatsApp template message via WATI when Contact is updated
    """
    try:
        client_number = "91"+doc.mobile_no

        if not client_number:
            return

        # assume client_number is already with country code, e.g. 919604238978
        wati_url = f"https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage?whatsappNumber={client_number}"

        wati_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"

        headers = {
            "Authorization": f"Bearer {wati_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "template_name": "welcome_wahtsapp",
            "broadcast_name": "welcome_wahtsapp",
            "parameters": [
                {
                    "name": "name",
                    "value": doc.name
                }
            ],
            "channel_number": "918143156363"
        }

        response = requests.post(wati_url, json=payload, headers=headers)

        frappe.logger().info({
            "status_code": response.status_code,
            "response": response.text,
            "sent_to": client_number
        })

        if response.status_code == 200:
            frappe.msgprint(f"✅ WhatsApp message sent to {client_number}")
        else:
            frappe.log_error(
                f"WATI Template Error: {response.status_code} - {response.text}",
                "WhatsApp Template Notification Failed"
            )
            frappe.msgprint(f"❌ Failed to send WhatsApp message. Check error logs.")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "WhatsApp Template Send Error")
        frappe.msgprint("❌ An unexpected error occurred while sending WhatsApp message")






import frappe
import requests

def send_whatsapp_on_therapy_session(doc, method):

    try:
        get_client = frappe.get_doc("Client", doc.client)
        client_number = "91"+get_client.mobile_no

        if not client_number:
            return

        # assume client_number is already with country code, e.g. 919604238978
        wati_url = f"https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage?whatsappNumber={client_number}"

        wati_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"

        headers = {
            "Authorization": f"Bearer {wati_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "template_name": "welcome_wahtsapp",
            "broadcast_name": "welcome_wahtsapp",
            "parameters": [
                {
                    "name": "name",
                    "value": doc.name
                }
            ],
            "channel_number": "918143156363"
        }

        response = requests.post(wati_url, json=payload, headers=headers)

        frappe.logger().info({
            "status_code": response.status_code,
            "response": response.text,
            "sent_to": client_number
        })

        if response.status_code == 200:
            frappe.msgprint(f"✅ WhatsApp message sent to {client_number}")
        else:
            frappe.log_error(
                f"WATI Template Error: {response.status_code} - {response.text}",
                "WhatsApp Template Notification Failed"
            )
            frappe.msgprint(f"❌ Failed to send WhatsApp message. Check error logs.")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "WhatsApp Template Send Error")
        frappe.msgprint("❌ An unexpected error occurred while sending WhatsApp message")





import frappe
import requests

def send_whatsapp_on_session_update(doc, method):
    try:
        # get parent Therapy Plan
        parent_doc = frappe.get_doc("Therapy Plan", doc.parent)

        if not parent_doc.patient:
            return

        client = frappe.get_doc("Patient", parent_doc.patient)
        client_number = client.mobile

        if not client_number:
            return

        # format with country code (assuming India)
        if not client_number.startswith("91"):
            client_number = "91" + client_number

        # WATI API details
        wati_url = f"https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage?whatsappNumber={client_number}"
        wati_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"

        headers = {
            "Authorization": f"Bearer {wati_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "template_name": "sesseion_exicution_completed",  
            "broadcast_name": "sesseion_exicution_completed",
            "parameters": [
                {"name": "name", "value": parent_doc.patient},
                {"name": "1", "value": str(doc.therapy_type)},
                {"name": "2", "value": f"{doc.sessions_completed}/{doc.no_of_sessions}"}

            ],
            "channel_number": "918143156363" 
        }

        response = requests.post(wati_url, json=payload, headers=headers)

        frappe.logger().info({
            "event": "Therapy Session WhatsApp Notification",
            "status_code": response.status_code,
            "response": response.text,
            "sent_to": client_number,
            "session_completed": doc.sessions_completed
        })

        if response.status_code == 200:
            frappe.msgprint(f"✅ WhatsApp notification sent to {client_number}")
        else:
            frappe.log_error(
                f"WATI Error {response.status_code}: {response.text}",
                "Therapy Session WhatsApp Failed"
            )
            frappe.msgprint(f"❌ Failed to send WhatsApp message. Check error logs.")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Therapy Session WhatsApp Exception")
        frappe.msgprint("❌ Unexpected error while sending WhatsApp message")





# import frappe
# import requests
# from frappe.utils import getdate


# def send_payment_details_to_customer(doc, method):
#     try:

#         client = doc.party_name
#         ammount = doc.paid_amount
#         posting_date = getdate(doc.posting_date).strftime("%d-%m-%Y")
#         invoice_name = None
#         if doc.references:
#             invoice_name = doc.references[0].reference_name

#         if not invoice_name:
#             frappe.msgprint("No Sales Invoice linked to this Payment Entry.")
#             return

#         invoice = frappe.get_doc("Sales Invoice", invoice_name)


#         client_number = frappe.db.get_value("Sales Invoice", invoice, "contact_mobile")
#         pdf_name = frappe.db.get_value("File", invoice_name, "attached_to_name")

#         if not client_number:
#             frappe.msgprint("Customer mobile number not found.")
#             return


#         # format with country code (assuming India)
#         if not client_number.startswith("91"):
#             client_number = "91" + client_number

#         # WATI API details
#         wati_url = f"https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage?whatsappNumber={client_number}"
#         wati_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"

#         headers = {
#             "Authorization": f"Bearer {wati_token}",
#             "Content-Type": "application/json"
#         }

#         payload = {
#             "template_name": "payment_details_confirmation",  
#             "broadcast_name": "payment_details_confirmation",
#             "parameters": [
#                 {"name": "1", "value": client},
#                 {"name": "2", "value": str(ammount)},
#                 {"name": "3", "value": str(invoice_name)},
#                 {"name": "4", "value": posting_date},
#                 {"name": "5", "value": str(doc.mode_of_payment)},
#                 {"name": "6", "value": pdf_name.file_name}
#             ],
#             "channel_number": "918143156363" 
#         }

#         response = requests.post(wati_url, json=payload, headers=headers)

#         frappe.logger().info({
#             "event": "Payment Entry WhatsApp Notification",
#             "status_code": response.status_code,
#             "response": response.text,
#             "sent_to": client_number,
#             "session_completed": doc.paid_amount
#         })

#         if response.status_code == 200:
#             frappe.msgprint(f"✅ WhatsApp notification sent to {client_number}")
#         else:
#             frappe.log_error(
#                 f"WATI Error {response.status_code}: {response.text}",
#                 "Therapy Session WhatsApp Failed"
#             )
#             frappe.msgprint(f"❌ Failed to send WhatsApp message. Check error logs.")

#     except Exception:
#         frappe.log_error(frappe.get_traceback(), "Therapy Session WhatsApp Exception")
#         frappe.msgprint("❌ Unexpected error while sending WhatsApp message")




import frappe
import requests
from frappe.utils import getdate, get_url
from frappe.utils.file_manager import save_file

# Print format used to render the payment receipt PDF. Re-rendered on every
# Payment Entry submit so paid / outstanding amounts reflect the latest payment.
PAYMENT_RECEIPT_PRINT_FORMAT = "Consultaion Patient Sales Invoice"


def send_payment_details_to_customer(doc, method):
    try:

        client = doc.party_name
        amount = doc.paid_amount
        posting_date = getdate(doc.posting_date).strftime("%d-%m-%Y")
        invoice_name = None

        # Get Sales Invoice reference
        if doc.references:
            invoice_name = doc.references[0].reference_name

        if not invoice_name:
            frappe.msgprint("No Sales Invoice linked to this Payment Entry.")
            return

        # Fetch invoice
        invoice = frappe.get_doc("Sales Invoice", invoice_name)

        # Get customer mobile
        client_number = frappe.db.get_value(
            "Sales Invoice",
            invoice_name,
            "contact_mobile"
        )

        if not client_number:
            frappe.msgprint("Customer mobile number not found.")
            return

        # Add India country code if missing
        if not client_number.startswith("91"):
            client_number = "91" + client_number

        # -------------------------------------------------
        # Generate a FRESH receipt PDF now (after this payment is submitted)
        # so the paid / outstanding amounts are up to date. The stale PDF that
        # was attached when the Sales Invoice was submitted is not used.
        # -------------------------------------------------
        pdf_url = ""
        try:
            pdf_data = frappe.get_print(
                "Sales Invoice",
                invoice_name,
                print_format=PAYMENT_RECEIPT_PRINT_FORMAT,
                as_pdf=True,
            )

            # Unique random 20-char file name
            unique_name = f"{frappe.generate_hash(length=20)}.pdf"

            # Save as a public file so WATI can fetch it without authentication
            file_doc = save_file(
                unique_name,
                pdf_data,
                "Sales Invoice",
                invoice_name,
                is_private=0,
            )

            pdf_url = get_url(file_doc.file_url)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Payment Entry Receipt PDF Generation Failed",
            )
            pdf_url = ""

        # -------------------------------------------------
        # WATI API configuration
        # -------------------------------------------------
        wati_url = f"https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage?whatsappNumber={client_number}"

        wati_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"

        headers = {
            "Authorization": f"Bearer {wati_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "template_name": "sales_confim_invoice_sent",
            "broadcast_name": "sales_confim_invoice_sent",
            "parameters": [
                {"name": "1", "value": client},
                {"name": "2", "value": str(amount)},
                {"name": "3", "value": str(invoice_name)},
                {"name": "4", "value": posting_date},
                {"name": "5", "value": str(doc.mode_of_payment)},
                {"name": "6", "value": pdf_url}
            ],
            "channel_number": "918143156363"
        }

        # Send request
        response = requests.post(wati_url, json=payload, headers=headers)

        # Logging
        frappe.logger().info({
            "event": "Payment Entry WhatsApp Notification",
            "status_code": response.status_code,
            "response": response.text,
            "sent_to": client_number,
            "invoice": invoice_name,
            "amount": amount
        })

        if response.status_code == 200:
            frappe.msgprint(f"✅ WhatsApp notification sent to {client_number}")
        else:
            frappe.log_error(
                f"WATI Error {response.status_code}: {response.text}",
                "Payment Entry WhatsApp Failed"
            )
            frappe.msgprint("❌ Failed to send WhatsApp message. Check error logs.")

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Payment Entry WhatsApp Exception"
        )
        frappe.msgprint("❌ Unexpected error while sending WhatsApp message")






import frappe
import requests

def send_whatsapp_session_completion_to_client(doc, method):
    try:
        client = frappe.get_doc("Patient", doc.patient)
        client_number = client.mobile
        remaining_sessions = int(doc.custom_remaining_sessions) - 1

        if not client_number:
            return

        # format with country code (assuming India)
        if not client_number.startswith("91"):
            client_number = "91" + client_number

        # WATI API details
        wati_url = f"https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage?whatsappNumber={client_number}"
        wati_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"

        headers = {
            "Authorization": f"Bearer {wati_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "template_name": "sesssion_update_completion",  
            "broadcast_name": "sesssion_update_completion",
            "parameters": [
                {"name": "1", "value": doc.patient},
                {"name": "2", "value": str(remaining_sessions)},
                {"name": "3", "value": "https://docs.google.com/forms/d/e/1FAIpQLSe87mWf5_A2ZIk8c-jO-S8kSzkUkE0Lp-QSvYnO5Y-gCkiwqQ/viewform"}
            ],
            "channel_number": "918143156363" 
        }

        response = requests.post(wati_url, json=payload, headers=headers)

        frappe.logger().info({
            "event": "Therapy Session WhatsApp Notification",
            "status_code": response.status_code,
            "response": response.text,
            "sent_to": client_number,
            "session_completed": doc.custom_remaining_sessions
        })

        if response.status_code == 200:
            frappe.msgprint(f"✅ WhatsApp notification sent to {client_number}")
        else:
            frappe.log_error(
                f"WATI Error {response.status_code}: {response.text}",
                "Therapy Session WhatsApp Failed"
            )
            frappe.msgprint(f"❌ Failed to send WhatsApp message. Check error logs.")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Therapy Session WhatsApp Exception")
        frappe.msgprint("❌ Unexpected error while sending WhatsApp message")

























































# import frappe
# import requests
# import random


# @frappe.whitelist()
# def send_client_whatsapp_otp(mobile):

#     try:
#         otp = random.randint(100000, 999999)

#         # store OTP in redis cache (5 minutes)
#         frappe.cache().set_value(f"client_otp_{mobile}", otp, expires_in_sec=300)

#         # format mobile
#         if not mobile.startswith("91"):
#             mobile = "91" + mobile

#         wati_url = f"https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage?whatsappNumber={mobile}"

#         wati_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"

#         headers = {
#             "Authorization": f"Bearer {wati_token}",
#             "Content-Type": "application/json"
#         }

#         payload = {
#             "template_name": "client_otp_verification",
#             "broadcast_name": "client_otp_verification",
#             "parameters": [
#                 {
#                     "name": "1",
#                     "value": str(otp)
#                 }
#             ],
#             "channel_number": "918143156363"
#         }

#         response = requests.post(wati_url, json=payload, headers=headers)

#         frappe.logger().info({
#             "event": "Client OTP Sent",
#             "mobile": mobile,
#             "otp": otp,
#             "response": response.text
#         })

#         return True

#     except Exception:
#         frappe.log_error(frappe.get_traceback(), "Send Client OTP Error")
#         return False


# @frappe.whitelist()
# def verify_client_otp(mobile, otp):

#     stored_otp = frappe.cache().get_value(f"client_otp_{mobile}")

#     if stored_otp and str(stored_otp) == str(otp):
#         frappe.cache().delete_value(f"client_otp_{mobile}")
#         return "verified"

#     return "invalid"


# @frappe.whitelist()
# def send_otp_from_doctype(doctype, docname):

#     mobile = None

#     # -----------------------
#     # Payment Entry
#     # -----------------------
#     if doctype == "Payment Entry":

#         party = frappe.db.get_value("Payment Entry", docname, "party")

#         if frappe.db.exists("Patient", party):
#             mobile = frappe.db.get_value("Patient", party, "mobile")

#     # -----------------------
#     # Therapy Session
#     # -----------------------
#     elif doctype == "Therapy Session":

#         patient = frappe.db.get_value("Therapy Session", docname, "patient")

#         if patient:
#             mobile = frappe.db.get_value("Patient", patient, "mobile")

#     if not mobile:
#         frappe.throw("Patient mobile not found")

#     # 🔥 reuse your existing OTP sender
#     return send_client_whatsapp_otp(mobile)



# @frappe.whitelist()
# def verify_otp_from_doctype(doctype, docname, otp):

#     mobile = None

#     if doctype == "Payment Entry":

#         party = frappe.db.get_value("Payment Entry", docname, "party")

#         if frappe.db.exists("Patient", party):
#             mobile = frappe.db.get_value("Patient", party, "mobile")

#     elif doctype == "Therapy Session":

#         patient = frappe.db.get_value("Therapy Session", docname, "patient")

#         if patient:
#             mobile = frappe.db.get_value("Patient", patient, "mobile")

#     if not mobile:
#         return "invalid"

#     # 🔥 reuse existing verifier
#     return verify_client_otp(mobile, otp)








# import frappe
# import requests
# import random


# # -----------------------------
# # Helper: Get patient mobile
# # -----------------------------
# def get_patient_mobile(doctype, docname):

#     if doctype == "Patient":
#         patient = docname

#     elif doctype == "Payment Entry":
#         party = frappe.db.get_value("Payment Entry", docname, "party")

#         # check patient exists
#         if frappe.db.exists("Patient", party):
#             patient = party
#         else:
#             return None

#     elif doctype == "Therapy Session":
#         patient = frappe.db.get_value("Therapy Session", docname, "patient")

#     else:
#         return None

#     return frappe.db.get_value("Patient", patient, "mobile")


# # -----------------------------
# # SEND OTP
# # -----------------------------
# @frappe.whitelist()
# def send_whatsapp_otp_for_doc(doctype, docname):

#     mobile = get_patient_mobile(doctype, docname)

#     if not mobile:
#         frappe.throw("Patient mobile number not found")

#     otp = random.randint(100000, 999999)

#     otp_key = f"client_otp::{doctype}::{docname}"

#     frappe.cache().set_value(
#         otp_key,
#         otp,
#         expires_in_sec=300
#     )

#     if not mobile.startswith("91"):
#         mobile = "91" + mobile

#     wati_url = f"https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage?whatsappNumber={mobile}"

#     wati_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"

#     headers = {
#         "Authorization": f"Bearer {wati_token}",
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "template_name": "client_otp_verification",
#         "broadcast_name": "client_otp_verification",
#         "parameters": [
#             {"name": "1", "value": str(otp)}
#         ],
#         "channel_number": "918143156363"
#     }

#     response = requests.post(wati_url, json=payload, headers=headers)

#     frappe.logger().info(response.text)

#     if response.status_code == 200:
#         return True
#     else:
#         frappe.throw(f"WATI Error: {response.text}")


# # -----------------------------
# # VERIFY OTP
# # -----------------------------
# @frappe.whitelist()
# def verify_whatsapp_otp_for_doc(doctype, docname, otp):

#     otp_key = f"client_otp::{doctype}::{docname}"

#     stored_otp = frappe.cache().get_value(otp_key)

#     if stored_otp and str(stored_otp) == str(otp):

#         frappe.cache().delete_value(otp_key)

#         # ✅ mark document verified
#         frappe.db.set_value(
#             doctype,
#             docname,
#             "custom_otp_verified",
#             1
#         )

#         return "verified"

#     return "invalid"



import frappe
import requests
import random


# =========================================================
# CONFIGURATION
# =========================================================

WATI_URL = "https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage"
WATI_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMiLCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbWFpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"
CHANNEL_NUMBER = "918143156363"
OTP_EXPIRY = 300  # 5 minutes


# =========================================================
# COMMON HELPERS
# =========================================================

def format_mobile(mobile):
    if not mobile:
        return None

    mobile = str(mobile).strip()

    if not mobile.startswith("91"):
        mobile = "91" + mobile

    return mobile


def send_wati_message(mobile, otp):

    mobile = format_mobile(mobile)

    url = f"{WATI_URL}?whatsappNumber={mobile}"

    headers = {
        "Authorization": f"Bearer {WATI_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "template_name": "client_otp_verification",
        "broadcast_name": "client_otp_verification",
        "parameters": [
            {"name": "1", "value": str(otp)}
        ],
        "channel_number": CHANNEL_NUMBER
    }

    response = requests.post(url, json=payload, headers=headers)

    frappe.logger().info({
        "event": "OTP_SENT",
        "mobile": mobile,
        "response": response.text
    })

    if response.status_code != 200:
        frappe.throw(f"WATI Error: {response.text}")

    return True


# =========================================================
# MOBILE FETCHER (SAFE FOR PAYMENT ENTRY)
# =========================================================

def get_patient_mobile(doctype, docname):

    patient = None

    if doctype == "Patient":
        patient = docname

    elif doctype == "Payment Entry":

        party = frappe.db.get_value(
            "Payment Entry",
            docname,
            "party"
        )

        if frappe.db.exists("Patient", party):
            patient = party

    elif doctype == "Therapy Session":

        patient = frappe.db.get_value(
            "Therapy Session",
            docname,
            "patient"
        )

    if not patient:
        return None

    return frappe.db.get_value("Patient", patient, "mobile")


# =========================================================
# CORE OTP ENGINE
# =========================================================

def generate_and_send_otp(cache_key, mobile):

    otp = random.randint(100000, 999999)

    frappe.cache().set_value(
        cache_key,
        otp,
        expires_in_sec=OTP_EXPIRY
    )

    send_wati_message(mobile, otp)

    return True


def verify_otp(cache_key, otp):

    stored_otp = frappe.cache().get_value(cache_key)

    if stored_otp and str(stored_otp) == str(otp):
        frappe.cache().delete_value(cache_key)
        return True

    return False


# =========================================================
# OLD API (PATIENT JS — DO NOT CHANGE)
# =========================================================

@frappe.whitelist()
def send_client_whatsapp_otp(mobile):
    """
    Used by Patient.js (UNCHANGED)
    """

    if not mobile:
        frappe.throw("Mobile number required")

    cache_key = f"client_otp_{mobile}"

    generate_and_send_otp(cache_key, mobile)

    return True


@frappe.whitelist()
def verify_client_otp(mobile, otp):
    """
    Used by Patient.js (UNCHANGED)
    """

    cache_key = f"client_otp_{mobile}"

    if verify_otp(cache_key, otp):
        return "verified"

    return "invalid"


# =========================================================
# NEW API (PAYMENT ENTRY JS)
# =========================================================

@frappe.whitelist()
def send_whatsapp_otp_for_doc(doctype, docname):
    """
    Used by Payment Entry JS
    """

    mobile = get_patient_mobile(doctype, docname)

    if not mobile:
        frappe.throw("Patient mobile number not found")

    cache_key = f"client_otp::{doctype}::{docname}"

    generate_and_send_otp(cache_key, mobile)

    return True


@frappe.whitelist()
def verify_whatsapp_otp_for_doc(doctype, docname, otp):
    """
    Verify OTP + mark document verified
    """

    cache_key = f"client_otp::{doctype}::{docname}"

    if verify_otp(cache_key, otp):

        meta = frappe.get_meta(doctype)

        # Only set if field exists (safe)
        if meta.has_field("custom_otp_verified"):
            frappe.db.set_value(
                doctype,
                docname,
                "custom_otp_verified",
                1
            )

        frappe.logger().info({
            "event": "OTP_VERIFIED",
            "doctype": doctype,
            "docname": docname
        })

        return "verified"

    return "invalid"