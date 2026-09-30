"""Idempotent scheduler schema installation; run on migration."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    fields = [
        dict(fieldname='custom_cc_booking', label='CC Scheduled Appointment', fieldtype='Check', default='0', read_only=1),
        dict(fieldname='custom_cc_resource', label='CC Staff Resource', fieldtype='Data', read_only=1, search_index=1),
        dict(fieldname='custom_cc_staff_name', label='Consultation Staff', fieldtype='Data', read_only=1, in_list_view=1),
        dict(fieldname='custom_cc_staff_role', label='Consultation Role', fieldtype='Data', read_only=1),
        dict(fieldname='custom_cc_request', label='Booking Request ID', fieldtype='Data', read_only=1, unique=1, no_copy=1),
    ]
    if not frappe.get_meta('Appointment').has_field('branch'):
        fields.append(dict(fieldname='branch', label='Branch', fieldtype='Link', options='Branch', in_list_view=1))
    create_custom_fields({'Appointment': fields})
