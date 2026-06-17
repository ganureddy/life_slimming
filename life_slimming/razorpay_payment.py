"""Razorpay payment integration for Sales Invoice.

Flow:
1. "Pay Now" on a Sales Invoice opens a dialog with the contact mobile and an
   (editable) amount taken from the invoice grand total.
2. "Pay" generates a Razorpay UPI QR code that the customer scans to pay.
3. "Send Payment Link" creates a Razorpay payment link and sends it to the
   customer over WhatsApp using the WATI template ``payment_request_to_customer``.
4. When the payment is completed (detected via QR polling or the Razorpay
   webhook) a Payment Entry is created against the Sales Invoice and left in
   Draft mode.

The Razorpay API key/secret are read from the "Razorpay Settings" single
doctype. All Razorpay REST calls go to api.razorpay.com using those credentials
(the approved business website registered with Razorpay does not affect
server-to-server API calls).
"""

import json

import frappe
import razorpay
import requests
from frappe import _
from frappe.utils import flt, nowdate

# ---------------------------------------------------------------------------
# WATI configuration (kept consistent with the rest of the app)
# ---------------------------------------------------------------------------
WATI_BASE_URL = "https://live-mt-server.wati.io/1013094/api/v2/sendTemplateMessage"
WATI_TOKEN = (
	"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiOGM5YTdmNC03ZjFhLTQ2NjMtYWI3MC1iZDYwNTAxZGVhOGMi"
	"LCJ1bmlxdWVfbmFtZSI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwibmFtZWlkIjoiYWNjb3VudHNAbGlmZXNjYy5jb20iLCJlbW"
	"FpbCI6ImFjY291bnRzQGxpZmVzY2MuY29tIiwiYXV0aF90aW1lIjoiMDgvMjYvMjAyNSAxMTo1MzoyMSIsInRlbmFudF9pZCI6"
	"IjEwMTMwOTQiLCJkYl9uYW1lIjoibXQtcHJvZC1UZW5hbnRzIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMD"
	"A4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQURNSU5JU1RSQVRPUiIsImV4cCI6MjUzNDAyMzAwODAwLCJpc3MiOiJDbGFy"
	"ZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.yMIIjtD1r74yWK0vhv3r-lB5WOI2qgIARe15OQd1n4Q"
)
WATI_CHANNEL_NUMBER = "918143156363"
WATI_PAYMENT_TEMPLATE = "payment_request_to_customer"

# Mode of Payment used on the Payment Entry created from Razorpay collections
RAZORPAY_MODE_OF_PAYMENT = "Razorpay Software Pvt Ltd -Link"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_razorpay_client():
	"""Return an authenticated Razorpay client using Razorpay Settings."""
	settings = frappe.get_doc("Razorpay Settings")
	api_key = settings.api_key
	api_secret = settings.get_password(fieldname="api_secret", raise_exception=False)

	if not api_key or not api_secret:
		frappe.throw(_("Razorpay API Key/Secret is not configured in Razorpay Settings."))

	return razorpay.Client(auth=(api_key, api_secret))


def _normalise_mobile(mobile):
	"""Return mobile in WATI format with the 91 country code prefix."""
	if not mobile:
		return None
	mobile = "".join(ch for ch in str(mobile) if ch.isdigit())
	if not mobile:
		return None
	if len(mobile) == 10:
		mobile = "91" + mobile
	elif not mobile.startswith("91"):
		mobile = "91" + mobile
	return mobile


def _get_invoice(sales_invoice):
	doc = frappe.get_doc("Sales Invoice", sales_invoice)
	doc.check_permission("read")
	return doc


def _qr_data_uri(text):
	"""Return an SVG data URI for a QR code encoding ``text``."""
	import base64
	import io

	import pyqrcode

	qr = pyqrcode.create(text, error="M")
	buffer = io.BytesIO()
	qr.svg(buffer, scale=4, background="#ffffff", module_color="#000000", xmldecl=True)
	encoded = base64.b64encode(buffer.getvalue()).decode()
	return "data:image/svg+xml;base64," + encoded


# ---------------------------------------------------------------------------
# 1. QR code ("Pay")
# ---------------------------------------------------------------------------
@frappe.whitelist()
def create_qr(sales_invoice, amount):
	"""Create a fixed-amount single-use Razorpay UPI QR code for the invoice."""
	invoice = _get_invoice(sales_invoice)
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Amount must be greater than zero."))

	client = get_razorpay_client()

	try:
		qr = client.qrcode.create(
			{
				"type": "upi_qr",
				"name": invoice.customer_name or invoice.customer,
				"usage": "single_use",
				"fixed_amount": True,
				"payment_amount": int(round(amount * 100)),  # paise
				"description": _("Payment for {0}").format(sales_invoice),
				"notes": {
					"sales_invoice": sales_invoice,
					"reference_doctype": "Sales Invoice",
				},
			}
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Razorpay QR Create Failed")
		frappe.throw(_("Could not create Razorpay QR code. Please check the error logs."))

	return {
		"qr_id": qr.get("id"),
		"image_url": qr.get("image_url"),
		"amount": amount,
	}


@frappe.whitelist()
def check_qr_payment(sales_invoice, qr_id):
	"""Poll a QR code for captured payments and create a Payment Entry if paid."""
	client = get_razorpay_client()

	try:
		payments = client.qrcode.fetch_all_payments(qr_id)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Razorpay QR Poll Failed")
		return {"status": "pending"}

	for payment in payments.get("items", []):
		if payment.get("status") == "captured":
			payment_entry = _create_payment_entry(
				sales_invoice,
				flt(payment.get("amount", 0)) / 100.0,
				payment.get("id"),
			)
			return {"status": "paid", "payment_entry": payment_entry}

	return {"status": "pending"}


# ---------------------------------------------------------------------------
# 1b. Razorpay Checkout ("Pay") -- works without the QR Codes product
# ---------------------------------------------------------------------------
@frappe.whitelist()
def create_order(sales_invoice, amount):
	"""Create a Razorpay order for the Checkout popup."""
	invoice = _get_invoice(sales_invoice)
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Amount must be greater than zero."))

	settings = frappe.get_doc("Razorpay Settings")
	client = get_razorpay_client()

	try:
		order = client.order.create(
			{
				"amount": int(round(amount * 100)),  # paise
				"currency": invoice.currency or "INR",
				"receipt": sales_invoice,
				"payment_capture": 1,
				"notes": {
					"sales_invoice": sales_invoice,
					"reference_doctype": "Sales Invoice",
				},
			}
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Razorpay Order Create Failed")
		frappe.throw(_("Could not create Razorpay order. Please check the error logs."))

	return {
		"order_id": order.get("id"),
		"amount": order.get("amount"),
		"currency": order.get("currency"),
		"key_id": settings.api_key,
		"customer_name": invoice.customer_name or invoice.customer,
		"contact_mobile": invoice.contact_mobile or "",
		"contact_email": invoice.contact_email or "",
	}


@frappe.whitelist()
def verify_and_record_payment(
	sales_invoice, razorpay_payment_id, razorpay_order_id, razorpay_signature
):
	"""Verify the Checkout signature and create a Draft Payment Entry."""
	client = get_razorpay_client()

	try:
		client.utility.verify_payment_signature(
			{
				"razorpay_order_id": razorpay_order_id,
				"razorpay_payment_id": razorpay_payment_id,
				"razorpay_signature": razorpay_signature,
			}
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Razorpay Signature Verification Failed")
		frappe.throw(_("Payment signature verification failed."))

	# Fetch the authoritative amount from Razorpay rather than trusting the client
	try:
		payment = client.payment.fetch(razorpay_payment_id)
		amount = flt(payment.get("amount", 0)) / 100.0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Razorpay Payment Fetch Failed")
		amount = flt(frappe.db.get_value("Sales Invoice", sales_invoice, "outstanding_amount"))

	payment_entry = _create_payment_entry(sales_invoice, amount, razorpay_payment_id)
	return {"status": "paid", "payment_entry": payment_entry}


# ---------------------------------------------------------------------------
# 2. Payment link (hosted page) -- used by both "Pay" and "Send Payment Link"
# ---------------------------------------------------------------------------
def _create_razorpay_payment_link(invoice, amount, mobile=None):
	"""Create a Razorpay-hosted payment link for a Sales Invoice.

	The payment happens on Razorpay's own hosted page (tied to the approved
	Razorpay account), so the requesting site domain is never involved.
	"""
	customer_name = invoice.customer_name or invoice.customer
	client = get_razorpay_client()

	customer = {"name": customer_name}
	if mobile:
		customer["contact"] = "+" + mobile

	try:
		link = client.payment_link.create(
			{
				"amount": int(round(amount * 100)),  # paise
				"currency": invoice.currency or "INR",
				"accept_partial": False,
				"description": _("Payment for {0}").format(invoice.name),
				"reference_id": f"{invoice.name}-{frappe.generate_hash(length=6)}",
				"customer": customer,
				"notify": {"sms": False, "email": False},
				"reminder_enable": False,
				"notes": {
					"sales_invoice": invoice.name,
					"reference_doctype": "Sales Invoice",
				},
			}
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Razorpay Payment Link Failed")
		frappe.throw(_("Could not create Razorpay payment link. Please check the error logs."))

	return link


@frappe.whitelist()
def create_payment_link(sales_invoice, amount):
	"""Create a hosted payment link and return its URL (opened in a new tab)."""
	invoice = _get_invoice(sales_invoice)
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Amount must be greater than zero."))

	mobile = _normalise_mobile(invoice.contact_mobile)
	link = _create_razorpay_payment_link(invoice, amount, mobile)
	short_url = link.get("short_url")

	return {
		"short_url": short_url,
		"payment_link_id": link.get("id"),
		"qr_image": _qr_data_uri(short_url) if short_url else None,
	}


@frappe.whitelist()
def send_payment_link(sales_invoice, amount, contact_mobile=None):
	"""Create a Razorpay payment link and send it to the customer via WATI."""
	invoice = _get_invoice(sales_invoice)
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Amount must be greater than zero."))

	mobile = _normalise_mobile(contact_mobile or invoice.contact_mobile)
	if not mobile:
		frappe.throw(_("A valid contact mobile number is required to send the payment link."))

	link = _create_razorpay_payment_link(invoice, amount, mobile)
	short_url = link.get("short_url")
	_send_wati_payment_link(mobile, invoice.customer_name or invoice.customer, amount, short_url)

	return {"short_url": short_url, "payment_link_id": link.get("id")}


@frappe.whitelist()
def check_payment_link_payment(sales_invoice, payment_link_id):
	"""Poll a payment link; create a Draft Payment Entry once it is paid."""
	client = get_razorpay_client()

	try:
		link = client.payment_link.fetch(payment_link_id)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Razorpay Payment Link Poll Failed")
		return {"status": "pending"}

	link_status = link.get("status")
	if link_status in ("cancelled", "expired"):
		return {"status": "failed", "reason": link_status}

	if link_status != "paid":
		return {"status": "pending"}

	# Pick the captured payment id from the link, if available
	razorpay_payment_id = None
	for payment in link.get("payments") or []:
		if payment.get("status") == "captured":
			razorpay_payment_id = payment.get("payment_id") or payment.get("id")
			break

	amount = flt(link.get("amount_paid", 0)) / 100.0 or flt(link.get("amount", 0)) / 100.0
	payment_entry = _create_payment_entry(
		sales_invoice, amount, razorpay_payment_id or payment_link_id
	)
	return {"status": "paid", "payment_entry": payment_entry}


def _send_wati_payment_link(mobile, customer_name, amount, link):
	"""Send the payment link over WhatsApp using the WATI template."""
	wati_url = f"{WATI_BASE_URL}?whatsappNumber={mobile}"
	headers = {
		"Authorization": f"Bearer {WATI_TOKEN}",
		"Content-Type": "application/json",
	}
	payload = {
		"template_name": WATI_PAYMENT_TEMPLATE,
		"broadcast_name": WATI_PAYMENT_TEMPLATE,
		"parameters": [
			{"name": "1", "value": str(customer_name)},
			{"name": "2", "value": "{:.2f}".format(flt(amount))},
			{"name": "3", "value": str(link)},
		],
		"channel_number": WATI_CHANNEL_NUMBER,
	}

	try:
		response = requests.post(wati_url, json=payload, headers=headers, timeout=30)
		frappe.logger().info(
			{
				"wati_status_code": response.status_code,
				"wati_response": response.text,
				"sent_to": mobile,
			}
		)
		if response.status_code != 200:
			frappe.log_error(
				f"WATI Payment Link Error: {response.status_code} - {response.text}",
				"WhatsApp Payment Link Failed",
			)
			frappe.throw(_("Payment link created but WhatsApp message could not be sent. Check error logs."))
	except frappe.exceptions.ValidationError:
		raise
	except Exception:
		frappe.log_error(frappe.get_traceback(), "WhatsApp Payment Link Send Error")
		frappe.throw(_("Payment link created but an error occurred while sending the WhatsApp message."))


# ---------------------------------------------------------------------------
# 3. Webhook -> create Payment Entry (Draft)
# ---------------------------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def razorpay_webhook():
	"""Handle Razorpay webhooks for qr_code.credited and payment_link.paid."""
	body = frappe.request.get_data(as_text=True)
	signature = frappe.get_request_header("X-Razorpay-Signature")
	webhook_secret = frappe.conf.get("razorpay_webhook_secret")

	if webhook_secret:
		try:
			get_razorpay_client().utility.verify_webhook_signature(body, signature, webhook_secret)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Razorpay Webhook Signature Failed")
			frappe.local.response["http_status_code"] = 400
			return {"status": "invalid signature"}

	try:
		data = json.loads(body or "{}")
	except ValueError:
		frappe.local.response["http_status_code"] = 400
		return {"status": "invalid payload"}

	event = data.get("event")
	payload = data.get("payload", {})

	sales_invoice = None
	amount = 0
	razorpay_payment_id = None

	if event == "qr_code.credited":
		payment_entity = payload.get("payment", {}).get("entity", {})
		qr_entity = payload.get("qr_code", {}).get("entity", {})
		sales_invoice = (qr_entity.get("notes") or payment_entity.get("notes") or {}).get("sales_invoice")
		amount = flt(payment_entity.get("amount", 0)) / 100.0
		razorpay_payment_id = payment_entity.get("id")

	elif event == "payment_link.paid":
		payment_entity = payload.get("payment", {}).get("entity", {})
		link_entity = payload.get("payment_link", {}).get("entity", {})
		sales_invoice = (link_entity.get("notes") or {}).get("sales_invoice")
		amount = flt(payment_entity.get("amount", 0)) / 100.0
		razorpay_payment_id = payment_entity.get("id")

	else:
		return {"status": "ignored"}

	if not sales_invoice or not amount:
		frappe.log_error(json.dumps(data, indent=2), "Razorpay Webhook Missing Reference")
		return {"status": "missing reference"}

	try:
		_create_payment_entry(sales_invoice, amount, razorpay_payment_id)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "Razorpay Webhook Payment Entry Failed")
		frappe.local.response["http_status_code"] = 500
		return {"status": "error"}

	return {"status": "ok"}


# ---------------------------------------------------------------------------
# Payment Entry creation
# ---------------------------------------------------------------------------
def _create_payment_entry(sales_invoice, amount, razorpay_payment_id):
	"""Create a Draft Payment Entry against the Sales Invoice.

	Idempotent: if a Payment Entry already references the same Razorpay payment
	id, the existing one is returned instead of creating a duplicate.
	"""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	if razorpay_payment_id:
		existing = frappe.db.get_value(
			"Payment Entry",
			{"reference_no": razorpay_payment_id, "docstatus": ["<", 2]},
			"name",
		)
		if existing:
			return existing

	# Run as Administrator: the webhook runs as Guest, and get_payment_entry
	# internally enforces read permission on the bank/cash Account.
	original_user = frappe.session.user
	try:
		frappe.set_user("Administrator")

		amount = flt(amount)
		payment_entry = get_payment_entry(
			"Sales Invoice",
			sales_invoice,
			party_amount=amount,
			ignore_permissions=True,
		)
		payment_entry.mode_of_payment = _ensure_mode_of_payment(RAZORPAY_MODE_OF_PAYMENT)
		payment_entry.reference_no = razorpay_payment_id or f"RZP-{frappe.generate_hash(length=8)}"
		payment_entry.reference_date = nowdate()

		payment_entry.flags.ignore_permissions = True
		payment_entry.insert(ignore_permissions=True)
		payment_entry.submit()

		return payment_entry.name
	finally:
		frappe.set_user(original_user)


def _ensure_mode_of_payment(mode_name):
	"""Return the Mode of Payment, creating it (type Bank) if it doesn't exist."""
	if not frappe.db.exists("Mode of Payment", mode_name):
		frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": mode_name,
				"type": "Bank",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
	return mode_name
