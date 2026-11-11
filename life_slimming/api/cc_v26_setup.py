"""Install the V26 journey tables without activating redistribution rules."""
import json
from pathlib import Path
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    for suffix in ('activity', 'followup', 'track', 'rule'):
        schema = json.loads(Path(__file__).with_name('cc_v26_' + suffix + '.json').read_text())
        if not frappe.db.exists('DocType', schema['name']):
            frappe.get_doc(schema).insert(ignore_permissions=True)
    create_custom_fields({'LIFE CC Lead Track': [
        dict(fieldname='matched_patient', label='Matched Patient', fieldtype='Link', options='Patient'),
        dict(fieldname='match_status', label='Match Status', fieldtype='Select', options='\nSuggested\nVerified\nRejected'),
        dict(fieldname='verified_by', label='Verified By', fieldtype='Link', options='User'),
        dict(fieldname='verified_on', label='Verified On', fieldtype='Datetime'),
        dict(fieldname='match_note', label='Match Note', fieldtype='Small Text'),
    ]}, update=True)
