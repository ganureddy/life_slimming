"""Legacy ConVox frontend route; never returns unscoped call history."""
import frappe
from life_slimming.api._runtime import script_endpoint
from life_slimming.api.convox import config, poll, history

@script_endpoint()
def run(**kwargs):
    action = frappe.form_dict.get("action", "config")
    if action == "config":
        frappe.response.update({"status": "success", **config()})
    elif action == "poll":
        frappe.response.update({"status": "success", **poll(frappe.form_dict.get("after"))})
    elif action == "history":
        frappe.response.update({"status": "success", **history(frappe.form_dict.get("lead_id"), frappe.form_dict.get("mobile_number"), frappe.form_dict.get("call_reference"))})
    else:
        raise frappe.ValidationError("Use the agent-scoped call updates in the ConVox phone.")
