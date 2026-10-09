"""LIFE Appointment Move History V1

Original API: life_appointment_move_history
Source modified: 2026-10-09 13:43:47.172183
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
    # LIFE_APPOINTMENT_MOVE_HISTORY_V1
    if frappe.session.user == "Guest":
        frappe.throw("Login required.")
    date = str(frappe.form_dict.get("date") or "").strip()
    branch = str(frappe.form_dict.get("branch") or "").strip()
    if not date or not branch:
        frappe.throw("Date and branch required.")
    ghosts = []
    start = 0
    seen = []
    while True:
        parents = frappe.get_list("Patient Appointment",
            filters=[["Patient Appointment","branch","=",branch],
                     ["LIFE Appointment Move History","from_date","=",date]],
            fields=["name"], order_by="name asc",
            limit_start=start, limit_page_length=100)
        if not parents:
            break
        for row in parents:
            if row.name in seen:
                continue
            seen.append(row.name)
            doc = frappe.get_doc("Patient Appointment",row.name)
            doc.check_permission("read")
            for history in (doc.get("custom_life_move_history") or []):
                if str(history.get("from_date") or "") != date:
                    continue
                room = history.get("from_room") or doc.get("service_room") or "No Room"
                old_time = str(history.get("from_time") or "")
                if str(doc.appointment_date)==date and str(doc.get("appointment_time"))==old_time and doc.get("service_room")==room:
                    continue
                ghosts.append({"name":doc.name,"patient":doc.get("patient_name") or doc.patient,
                    "branch":branch,"service_room":room,"appointment_date":date,
                    "appointment_time":old_time,"call_back_status":"Re-Scheduled",
                    "life_ghost":True,"life_target_date":str(doc.appointment_date),
                    "life_target_time":str(doc.get("appointment_time") or "")})
        if len(parents)<100:
            break
        start=start+100
    frappe.response["message"]={"rows":ghosts}
