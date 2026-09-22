"""ConVox authenticated callback; preserves the migrated API route."""
import frappe
from life_slimming.api._runtime import script_endpoint
from life_slimming.api.convox import receive_callback

@script_endpoint(allow_guest=True)
def run(**kwargs):
    frappe.response.update(receive_callback('Call Popup', dict(frappe.form_dict)))
