"""Operations Service Module cryo multiple sessions executions

Original API: life_ops_submit_cryo_batch
Source modified: 2026-10-10 13:11:55.420700
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
    # LIFE_CRYO_BATCH_V1
    source_name = str(frappe.form_dict.get("source_session") or "").strip()
    if frappe.session.user == "Guest" or not source_name:
        frappe.throw("Login and source Therapy Session are required.")
    source = frappe.get_doc("Therapy Session", source_name)
    source.check_permission("read")
    source.check_permission("write")
    source.check_permission("submit")
    _read_sql("SELECT name FROM `tabTherapy Session` WHERE name=%s FOR UPDATE", (source_name,))
    source.reload()
    total = frappe.utils.cint(source.get("custom_life_batch_quantity") or 1)
    if total < 2:
        frappe.throw("Batch quantity must be at least 2.")
    therapy = frappe.get_doc("Therapy Type", source.therapy_type)
    text = str(source.therapy_type or "") + " " + str(therapy.get("therapy_type") or "") + " " + str(therapy.get("therapy_name") or "")
    batch_therapy_key = text.lower().replace(" ", "").replace("-", "").replace("_", "")
    if not any(word in batch_therapy_key for word in [
        "cryo", "filler", "botox", "zimmer", "coolsculpt",
        "thread", "therad", "thred", "mesolipo", "misolipo"
    ]):
        frappe.throw("Multiple sessions are allowed only for Cryo, Fillers, Botox, Zimmer, Cool Sculpting, Threads and Mesolipo/Meso Lipolysis.")
    if source.docstatus == 2:
        frappe.throw("The batch source session is cancelled.")
    plan_name = str(source.therapy_plan or "")
    _read_sql("SELECT name FROM `tabTherapy Plan` WHERE name=%s FOR UPDATE", (plan_name,))
    plan = frappe.get_doc("Therapy Plan", plan_name)
    plan.check_permission("read")
    booked = 0
    for row in (plan.get("therapy_plan_details") or []):
        if row.get("therapy_type") == source.therapy_type:
            booked = booked + frappe.utils.cint(row.get("no_of_sessions"))
    if booked <= 0:
        frappe.throw("No booked sessions found for this Therapy Type.")
    completed = frappe.db.count("Therapy Session", {"therapy_plan":plan_name, "therapy_type":source.therapy_type, "docstatus":1})
    names = [source.name]
    missing = []
    for index in range(2, total + 1):
        key = source.name + ":" + str(index)
        existing_name = frappe.db.get_value("Therapy Session", {"custom_life_batch_key":key}, "name")
        if existing_name:
            existing = frappe.get_doc("Therapy Session", existing_name)
            existing.check_permission("read")
            if existing.docstatus != 1:
                frappe.throw("Batch record " + existing.name + " is not submitted. Review it before retrying.")
            names.append(existing.name)
        else:
            missing.append(index)
    needed = len(missing) + (1 if source.docstatus == 0 else 0)
    if completed + needed > booked:
        frappe.throw("Therapy batch exceeds remaining sessions. Booked: " + str(booked) + "; completed: " + str(completed) + "; requested remaining: " + str(needed))
    template = source.as_dict()
    remove_fields = ["name","owner","creation","modified","modified_by","docstatus","amended_from","parent","parenttype","parentfield","idx"]
    if source.docstatus == 0:
        source.submit()
    for index in missing:
        values = {}
        for field in source.meta.fields:
            fieldname = field.fieldname
            if fieldname in remove_fields or field.fieldtype in ["Section Break","Column Break","Tab Break","HTML","Button","Heading"]:
                continue
            value = template.get(fieldname)
            if field.fieldtype in ["Table","Table MultiSelect"]:
                rows = []
                for child in (value or []):
                    clean_row = {}
                    for key in child:
                        if key not in remove_fields:
                            clean_row[key] = child.get(key)
                    rows.append(clean_row)
                values[fieldname] = rows
            else:
                values[fieldname] = value
        values["doctype"] = "Therapy Session"
        values["docstatus"] = 0
        values["custom_life_batch_quantity"] = 1
        values["custom_life_batch_source"] = source.name
        values["custom_life_batch_key"] = source.name + ":" + str(index)
        values["custom_sessions_complted"] = str(completed + (1 if template.get("docstatus") == 0 else 0) + len(names))
        values["custom_remaining_sessions"] = str(max(0, booked - frappe.utils.cint(values["custom_sessions_complted"])))
        doc = frappe.get_doc(values)
        doc.insert()
        doc.submit()
        names.append(doc.name)
    source.reload()
    frappe.response["message"] = {"session":source.as_dict(), "sessions":names, "quantity":total, "ok":True}
