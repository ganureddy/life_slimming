"""Native replacement for the live ``life_stock_request_controls`` Server Script."""

import frappe

from life_slimming.api._runtime import script_endpoint


SETTINGS_DOCTYPE = "LIFE Stock Request Settings"


def _value(fieldname, default):
    meta = frappe.get_meta(SETTINGS_DOCTYPE)
    if not meta.has_field(fieldname):
        return default
    return frappe.db.get_single_value(SETTINGS_DOCTYPE, fieldname) or default


@script_endpoint(allow_guest=False)
def run(**kwargs):
    """Return the four settings values consumed by the live stock dashboard."""
    return {
        "rules": _value("item_request_rules", "{}"),
        "windows": _value("branch_request_windows", "{}"),
        "exception": _value("enable_monthly_indent_exception", 0),
        "imr": _value("item_master_rules", "{}"),
    }
