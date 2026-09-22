"""Legacy ConVox call route, using the permission-checked server integration."""
import secrets
import frappe
from life_slimming.api._runtime import script_endpoint
from life_slimming.api.convox import click_to_call

@script_endpoint()
def run(**kwargs):
    if frappe.form_dict.get("action", "click_to_call") != "click_to_call":
        raise frappe.ValidationError("Unsupported ConVox action.")
    frappe.response["message"] = click_to_call(
        frappe.form_dict.get("lead_id"), frappe.form_dict.get("request_id") or secrets.token_hex(16))
