"""CC-LEAD-New By Bhuvan

Original API: cc_phone_lookup
Source modified: 2026-10-03 18:34:26.640319
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
    # ============================================================
    # Server Script : cc_phone_lookup
    # Script Type   : API
    # API Method    : cc_phone_lookup
    # Allow Guest   : No
    # Purpose       : Follow-up form → (1) when an agent types a phone number,
    #                 tell them if it already belongs to an existing client
    #                 (Patient) and which branch. Read-only. Returns no phone
    #                 numbers, only client name + branch.
    #                 (2) BOOKED seal: returns how many submitted Sales Invoices
    #                 the matched client has and the latest invoice date/branch.
    # ============================================================

    ALLOWED_ROLES = ["System Manager", "Sales Manager", "Sales User",
                     "Call Center Export", "Branch Sales Invoice"]

    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Not permitted")

    roles = frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")
    ok = False
    for r in ALLOWED_ROLES:
        if r in roles:
            ok = True
            break
    if not ok:
        frappe.throw("Not permitted")

    raw = str(frappe.form_dict.get("phone") or "")
    digits = ""
    for ch in raw:
        if ch.isdigit():
            digits = digits + ch
    if len(digits) > 10:
        digits = digits[-10:]

    matches = []
    if len(digits) == 10:
        like = "%" + digits
        names = []

        for field in ["mobile", "phone"]:
            for n in frappe.get_all("Patient", filters={field: ["like", like]},
                                    pluck="name", limit_page_length=20):
                if n not in names:
                    names.append(n)

        # extra numbers saved in the Patient "Contact Numbers" table
        for n in frappe.get_all("Contact Phone",
                                filters={"parenttype": "Patient", "phone": ["like", like]},
                                pluck="parent", limit_page_length=20):
            if n not in names:
                names.append(n)

        for n in names[:10]:
            p = frappe.db.get_value("Patient", n,
                                    ["name", "patient_name", "custom_branch", "branch_name", "status", "customer"],
                                    as_dict=True)
            if p:
                inv_count = 0
                last_date = ""
                last_branch = ""
                if p.customer:
                    invs = frappe.get_all("Sales Invoice",
                                          filters={"customer": p.customer, "docstatus": 1, "is_return": 0},
                                          fields=["name", "posting_date", "branch"],
                                          order_by="posting_date desc", limit_page_length=50)
                    inv_count = len(invs)
                    if invs:
                        last_date = str(invs[0].posting_date or "")
                        last_branch = invs[0].branch or ""
                matches.append({
                    "patient": p.name,
                    "client": p.patient_name or p.name,
                    "branch": p.custom_branch or p.branch_name or "",
                    "status": p.status or "",
                    "invoices": inv_count,
                    "last_invoice_date": last_date,
                    "last_invoice_branch": last_branch
                })

    frappe.response["message"] = {"matches": matches}
