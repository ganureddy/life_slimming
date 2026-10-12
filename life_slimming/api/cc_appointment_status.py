"""Role-restricted editing of the Lead appointment status in the CC dashboard."""
import frappe


def authorize():
    if frappe.session.user == 'Guest' or not (
        frappe.session.user == 'Administrator'
        or {'System Manager', 'Call Center Export'}.intersection(frappe.get_roles())
    ):
        raise frappe.PermissionError('Only System Manager and Call Center Export can edit appointment status.')


def status_options():
    field = frappe.get_meta('Lead').get_field('custom_appointment_status')
    return [value.strip() for value in (field.options or '').splitlines()
            if value.strip() and value.strip() != 'Cancelled'] if field else []


@frappe.whitelist()
def options():
    authorize()
    return status_options()


@frappe.whitelist(methods=['POST'])
def update(lead, status, expected_modified):
    authorize()
    if status not in status_options():
        raise frappe.ValidationError('Choose a valid appointment status.')
    doc = frappe.get_doc('Lead', lead)
    if not expected_modified or str(doc.modified) != str(expected_modified):
        raise frappe.ValidationError('This lead changed. Reload it before updating appointment status.')
    if doc.custom_appointment_status == 'Visited Booked' and status != 'Visited Booked':
        raise frappe.ValidationError('Visited Booked is locked and cannot be changed.')
    doc.custom_appointment_status = status
    doc.save(ignore_permissions=True)
    return {'name': doc.name, 'custom_appointment_status': doc.custom_appointment_status,
            'modified': str(doc.modified)}
