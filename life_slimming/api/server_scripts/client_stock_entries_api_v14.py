"""Client Stock Entries API V14

Original API: client_stock_entries_api_v14
Source modified: 2026-09-11 13:05:45.826739
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

    patient = frappe.form_dict.get("patient")

    if frappe.session.user == "Guest":
        frappe.throw("Please login to continue")

    if not patient:
        frappe.throw("Client is required")

    if not frappe.db.exists("Patient", patient):
        frappe.throw("Client not found")

    rows = _read_sql(
        '''
    SELECT
        se.name AS stock_entry,
        se.posting_date,
        se.posting_time,
        se.purpose,
        se.stock_entry_type,
        se.docstatus,
        se.from_warehouse,
        se.to_warehouse,
        se.remarks,
        se.custom_stock_released_by,
        se.custom_stock_release_date,
        se.custom_received_by,
        se.custom_received_date,

        sed.name AS detail_name,
        sed.item_code,
        sed.item_name,
        sed.description,
        sed.qty,
        sed.transfer_qty,
        sed.uom,
        sed.stock_uom,
        sed.s_warehouse,
        sed.t_warehouse,
        sed.basic_rate,
        sed.amount,
        sed.custom_client_name,
        sed.custom_package_number,
        sed.custom_released_qty,
        sed.custom_received_qty,
        sed.custom_missing_qty,
        sed.custom_damaged_qty,
        sed.custom_return_to_source_qty

    FROM `tabStock Entry Detail` sed

    INNER JOIN `tabStock Entry` se
        ON se.name = sed.parent

    WHERE
        sed.parenttype = 'Stock Entry'
        AND sed.patient = %s
        AND se.docstatus != 2

    ORDER BY
        se.posting_date DESC,
        se.posting_time DESC,
        se.modified DESC,
        sed.idx ASC
    ''',
        (patient,),
        as_dict=True
    )

    frappe.response["message"] = rows
