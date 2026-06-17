import frappe
import base64
from frappe.utils.pdf import get_pdf


def decrypt_invoice(encoded):
    try:
        return base64.urlsafe_b64decode(encoded.encode()).decode()
    except Exception:
        return None


@frappe.whitelist(allow_guest=True)
def download_invoice(enc=None):

    if not enc:
        frappe.throw("Invalid Request")

    invoice_name = decrypt_invoice(enc)

    if not invoice_name:
        frappe.throw("Invalid or tampered link")

    if not frappe.db.exists("Sales Invoice", invoice_name):
        frappe.throw("Invoice not found")

    # generate pdf
    html = frappe.get_print(
        "Sales Invoice",
        invoice_name,
        print_format="Standard"
    )

    pdf = get_pdf(html)

    frappe.local.response.filename = f"{invoice_name}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "binary"