"""Install the settings fields required by the live Stock Dashboard."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


FIELDS = [
    {"fieldname": "stock_dashboard_controls_section", "label": "Stock Dashboard Controls", "fieldtype": "Section Break"},
    {"fieldname": "item_request_rules", "label": "Item Request Rules", "fieldtype": "Long Text", "default": "{}", "description": "JSON rules controlling branch item request access."},
    {"fieldname": "branch_request_windows", "label": "Branch Request Windows", "fieldtype": "Long Text", "default": "{}", "description": "JSON branch request-window rules."},
    {"fieldname": "item_master_rules", "label": "Item Master Rules", "fieldtype": "Long Text", "default": "{}", "description": "JSON item request-use metadata."},
    {"fieldname": "enable_monthly_indent_exception", "label": "Enable Monthly Indent Exception", "fieldtype": "Check", "default": "0"},
    {"fieldname": "control_log", "label": "Control Log", "fieldtype": "Long Text", "default": "[]", "read_only": 1},
]


def execute():
    if not frappe.db.exists("DocType", "LIFE Stock Request Settings"):
        return
    meta = frappe.get_meta("LIFE Stock Request Settings", cached=False)
    missing = [field for field in FIELDS if not meta.has_field(field["fieldname"])]
    if missing:
        create_custom_fields({"LIFE Stock Request Settings": missing}, update=True)
    frappe.clear_cache(doctype="LIFE Stock Request Settings")


def status():
    required = [field["fieldname"] for field in FIELDS]
    meta = frappe.get_meta("LIFE Stock Request Settings", cached=False)
    return {fieldname: bool(meta.has_field(fieldname)) for fieldname in required}
