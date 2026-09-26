"""mask_mobile_on_export

Original API: mask_mobile_on_export
Source modified: 2026-06-03 23:16:14.920702
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
    # ─── Masking helper ───────────────────────────────────────────────────────────
    def mask_number(value):
        """Keep first 2 and last 2 digits visible, mask everything in between."""
        if not value:
            return value
        s = str(value).strip()
        digits = re.sub(r'\D', '', s)
        if len(digits) <= 4:
            return s
        masked = digits[:2] + ('*' * (len(digits) - 4)) + digits[-2:]
        return masked

    # ─── DocType → mobile/phone field names ──────────────────────────────────────
    MOBILE_FIELDS_MAP = {
        'Address': ['phone'],
        'Appe Customer': ['mobile_number'],
        'Appointment': ['customer_phone_number'],
        'Client Session Record': ['mobile_no'],
        'Client Transfer Request Form': ['mobile_number'],
        'Communication': ['phone_no'],
        'Company': ['phone_no'],
        'Contact': ['mobile_no', 'phone'],
        'Contact Phone': ['phone'],
        'Customer': ['mobile_no'],
        'Delivery Note': ['contact_mobile'],
        'Driver': ['cell_number'],
        'Dunning': ['contact_mobile'],
        'Duplicate Lead': ['phone'],
        'Employee': ['cell_number', 'emergency_phone_number'],
        'Healthcare Practitioner': ['mobile_no', 'mobile_phone', 'office_phone', 'residence_phone'],
        'HR Employee Onboarding': ['emergency_phone', 'mobile_number'],
        'Inpatient Record': ['mobile', 'phone'],
        'Installation Note': ['contact_mobile'],
        'Job Applicant': ['phone_number'],
        'Kpcc Leads': ['alternate_phone_number', 'phone'],
        'Lab Test': ['mobile'],
        'Lead': ['mobile_no', 'phone'],
        'Loan Decalaration And Consent Form': ['guardian_mobile', 'mobile', 'mobile_no', 'mobile_number'],
        'Maintenance Schedule': ['contact_mobile'],
        'Maintenance Visit': ['contact_mobile'],
        'Marketing Lead': ['mobile_no'],
        'Medication Request': ['patient_mobile'],
        'mlead': ['phone_number'],
        'Notification Receipt Users': ['mobile_no'],
        'Opportunity': ['contact_mobile', 'phone'],
        'Patient': ['mobile', 'phone'],
        'Payment Request': ['phone_number'],
        'POS Invoice': ['contact_mobile'],
        'Prospect Lead': ['mobile_no'],
        'Purchase Invoice': ['contact_mobile'],
        'Purchase Order': ['contact_mobile', 'customer_contact_mobile'],
        'Purchase Receipt': ['contact_mobile'],
        'Quotation': ['contact_mobile'],
        'Sales Invoice': ['contact_mobile'],
        'Sales Order': ['contact_mobile', 'contact_phone'],
        'Service Request': ['patient_mobile'],
        'Subcontracting Order': ['contact_mobile'],
        'Subcontracting Receipt': ['contact_mobile'],
        'Supplier': ['mobile_no'],
        'Supplier Quotation': ['contact_mobile'],
        'Travel Request': ['cell_number'],
        'User': ['mobile_no', 'phone'],
        'Warehouse': ['mobile_no', 'phone_no'],
        'Warranty Claim': ['contact_mobile'],
    }

    # ─── Main logic ───────────────────────────────────────────────────────────────
    doctype = frappe.form_dict.get('doctype')
    rows    = frappe.form_dict.get('rows') or []

    if not doctype:
        frappe.response['message'] = {
            'error': 'doctype is required',
            'supported_doctypes': sorted(MOBILE_FIELDS_MAP.keys())
        }
    else:
        fields_to_mask = MOBILE_FIELDS_MAP.get(doctype, [])
        masked_rows = []
        for row in rows:
            row = dict(row)
            for field in fields_to_mask:
                if row.get(field):
                    row[field] = mask_number(row[field])
            masked_rows.append(row)

        frappe.response['message'] = {
            'doctype': doctype,
            'fields_masked': fields_to_mask,
            'masked_rows': masked_rows
        }
