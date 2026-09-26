"""lifescc.billing.lead_lookup

Original API: lifescc.billing.lead_lookup
Source modified: 2026-07-27 17:23:16.324855
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
    # ═══════════════════════════════════════════════════════════════════
    # SERVER SCRIPT  #8   ·   lifescc.billing.lead_lookup
    # Type: API   ·   Method: lifescc.billing.lead_lookup   ·   Guest: No
    #
    # Looks up a Lead by mobile number so the billing page can behave like
    # the Desk "Patient - Auto Fill From Lead" client script:
    #   - if the mobile matches a Lead, the client came through the call
    #     centre, so the source/media is set accordingly
    #   - name, gender, DOB, branch, enquired-for and media are pulled in
    #
    # Accepts 10-digit or 91-prefixed numbers (same normalising as the
    # Desk script's kpNormalizeMobileNumber).
    # ═══════════════════════════════════════════════════════════════════

    args = frappe.form_dict
    raw = (args.get("mobile") or "").strip()

    digits = ""
    for ch in raw:
        if ch.isdigit():
            digits += ch

    if len(digits) == 12 and digits[:2] == "91":
        mobile = digits[2:]
    else:
        mobile = digits

    if len(mobile) != 10:
        frappe.response["message"] = {"found": 0}

    else:
        # a lead may store the number with or without the 91 prefix
        lead_name = frappe.db.get_value("Lead", {"mobile_no": mobile}, "name")
        if not lead_name:
            lead_name = frappe.db.get_value("Lead", {"mobile_no": "91" + mobile}, "name")
        if not lead_name:
            lead_name = frappe.db.get_value("Lead", {"phone": mobile}, "name")

        if not lead_name:
            frappe.response["message"] = {"found": 0}
        else:
            ld = frappe.db.get_value(
                "Lead", lead_name,
                ["name", "lead_name", "first_name", "middle_name", "last_name",
                 "gender", "date_of_birth", "lead_assign_to_branch",
                 "custom_media", "enquired_for", "city", "custom_remarks",
                 "height", "weight", "medical_history"],
                as_dict=True,
            )

            full = ""
            for part in [ld.get("first_name"), ld.get("middle_name"), ld.get("last_name")]:
                if part:
                    if full:
                        full += " "
                    full += part
            if not full:
                full = ld.get("lead_name") or ""

            # Source: a client coming from a Lead is a Call Center client.
            # Fall back to the lead's own media if Call Center isn't a valid
            # Lead Source in this system.
            media = ""
            if frappe.db.exists("Lead Source", "Call Center"):
                media = "Call Center"
            elif ld.get("custom_media") and frappe.db.exists("Lead Source", ld.get("custom_media")):
                media = ld.get("custom_media")

            frappe.response["message"] = {
                "found": 1,
                "lead": ld.get("name"),
                "patient_name": full,
                "sex": ld.get("gender") or "",
                "dob": ld.get("date_of_birth") or "",
                "branch": ld.get("lead_assign_to_branch") or "",
                "media": media,
                "lead_media": ld.get("custom_media") or "",
                "visited_for": ld.get("enquired_for") or "",
                "city": ld.get("city") or "",
                "remarks": ld.get("custom_remarks") or "",
                "height": ld.get("height") or "",
                "weight": ld.get("weight") or "",
                "medical_history": ld.get("medical_history") or "",
            }
