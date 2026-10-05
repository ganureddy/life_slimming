"""Synchronize completed CC appointments after a client invoice is submitted.

The existing branch workflow requires a PD form number and at least two PD
images before a lead can be marked Visited Booked. This hook keeps that gate
in place while allowing a submitted Sales Invoice to complete the outcome.
"""

import frappe

from life_slimming.api.pd_form_utils import pd_form_urls


def _sync_submitted_invoice(doc):
    if not doc or doc.docstatus != 1 or not doc.get("patient"):
        return

    patient = frappe.db.get_value(
        "Patient",
        doc.get("patient"),
        ["name", "custom_lead", "custom_pd_form_number"],
        as_dict=True,
    )
    if not patient or not patient.get("custom_lead"):
        return

    lead_name = patient.get("custom_lead")
    lead = frappe.db.get_value(
        "Lead",
        lead_name,
        ["name", "custom_appointment_status", "status"],
        as_dict=True,
    )
    if not lead or lead.get("custom_appointment_status") == "Visited Booked":
        return

    # Only a booked CC appointment can be completed by billing. The regular
    # branch outcome flow still handles unbooked and no-show appointments.
    if lead.get("custom_appointment_status") not in ("Booked", "Visited"):
        return

    if not (patient.get("custom_pd_form_number") or "").strip():
        return

    if len(pd_form_urls(patient.get("name"))) < 2:
        return

    values = {
        "custom_appointment_status": "Visited Booked",
        "status": "Converted",
        "custom_remarks": "",
    }

    # Preserve the existing audit trail fields where they are configured.
    meta = frappe.get_meta("Lead")
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": doc.get("owner")},
        ["name", "employee_name", "branch"],
        as_dict=True,
    )
    if employee:
        if meta.has_field("custom_status_updated_by_employee"):
            values["custom_status_updated_by_employee"] = employee.get("name")
        if meta.has_field("custom_status_updated_by_name"):
            values["custom_status_updated_by_name"] = employee.get("employee_name")
    if meta.has_field("custom_status_updated_by_user"):
        values["custom_status_updated_by_user"] = doc.get("owner")
    if meta.has_field("custom_status_updated_on"):
        values["custom_status_updated_on"] = frappe.utils.now()

    frappe.db.set_value("Lead", lead_name, values, update_modified=True)
    if frappe.get_meta("Patient").has_field("custom_final_decision"):
        frappe.db.set_value(
            "Patient", patient.get("name"), "custom_final_decision", "Booked",
            update_modified=True,
        )

    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Lead",
        "reference_name": lead_name,
        "comment_by": doc.get("owner"),
        "content": (
            "CC Walk-in Status: "
            + str(lead.get("custom_appointment_status") or "Booked")
            + " → Visited Booked | Automatically completed from submitted Sales Invoice "
            + str(doc.get("name"))
            + "."
        ),
    }).insert(ignore_permissions=True)


def sales_invoice_on_submit(doc, method=None):
    try:
        _sync_submitted_invoice(doc)
    except Exception:
        # Appointment status synchronization is secondary to invoice
        # submission; log failures for follow-up without blocking billing.
        frappe.log_error(
            title="CC appointment sync after invoice submission failed",
            message=frappe.get_traceback(),
        )
