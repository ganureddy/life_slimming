"""LIFE Client Record Book API

Original API: life_client_record_book_api
Source modified: 2026-09-25 18:47:43.694074
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
    args = frappe.form_dict or {}
    action = (args.get("action") or "get").strip()
    patient = (args.get("patient") or "").strip()
    record_number = (args.get("record_book_number") or "").strip().upper()
    remarks = (args.get("remarks") or "").strip()
    current_user = frappe.session.user

    def clean(v):
        return (v or "").strip()

    def get_patient(name):
        rows = frappe.get_all(
            "Patient",
            filters={"name": name},
            fields=["name", "patient_name", "first_name", "custom_branch", "branch_name"],
            limit_page_length=1,
            ignore_permissions=True
        )
        return rows[0] if rows else None

    def get_branch(prow):
        for f in ["custom_branch", "branch_name"]:
            v = clean(prow.get(f))
            if v:
                return v
        return ""

    def get_records(name):
        rows = frappe.get_all(
            "Client Record Book Number",
            filters=[
                ["parenttype", "=", "Patient"],
                ["parentfield", "=", "custom_record_book_numbers"],
                ["parent", "=", name]
            ],
            fields=["record_book_number", "record_book_date", "serial_reference", "remarks", "added_by", "creation", "idx"],
            order_by="idx desc",
            limit_page_length=50,
            ignore_permissions=True
        )
        out = []
        for r in rows:
            out.append({
                "record_book_number": clean(r.get("record_book_number")).upper(),
                "record_book_date": str(r.get("record_book_date") or ""),
                "serial_reference": r.get("serial_reference") or "",
                "remarks": r.get("remarks") or "",
                "added_by": r.get("added_by") or "",
                "creation": str(r.get("creation") or "")
            })
        return out

    def get_available(branch):
        filters = [["status", "=", "Available"]]
        if branch:
            filters.append(["branch", "=", branch])
        rows = frappe.get_all(
            "Client Record Book Serial",
            filters=filters,
            fields=["name", "record_book_number", "branch", "stores_sent_date", "status"],
            order_by="record_book_number asc",
            limit_page_length=500,
            ignore_permissions=True
        )
        out = []
        for r in rows:
            out.append({
                "name": r.get("name"),
                "record_book_number": clean(r.get("record_book_number")).upper(),
                "branch": r.get("branch") or "",
                "stores_sent_date": str(r.get("stores_sent_date") or ""),
                "status": r.get("status") or ""
            })
        return out

    if not patient:
        frappe.response["message"] = {"ok": 0, "message": "Patient is required."}
        raise SystemExit

    prow = get_patient(patient)
    if not prow:
        frappe.response["message"] = {"ok": 0, "message": "Client/Patient not found."}
        raise SystemExit

    branch = get_branch(prow)
    records = get_records(patient)

    if action == "get":
        frappe.response["message"] = {
            "ok": 1,
            "patient": patient,
            "patient_name": prow.get("patient_name") or prow.get("first_name") or patient,
            "branch": branch,
            "has_record": len(records) > 0,
            "records": records,
            "available_serials": [] if records else get_available(branch)
        }
        raise SystemExit

    if action == "assign":
        if records:
            frappe.response["message"] = {
                "ok": 0,
                "error": "CLIENT_ALREADY_HAS_RECORD",
                "message": "This client already has a Record Book Number."
            }
            raise SystemExit

        if not record_number:
            frappe.response["message"] = {"ok": 0, "message": "Select a Record Book Number."}
            raise SystemExit

        used = frappe.get_all(
            "Client Record Book Number",
            filters={"record_book_number": record_number},
            fields=["parent"],
            limit_page_length=1,
            ignore_permissions=True
        )
        if used:
            frappe.response["message"] = {
                "ok": 0,
                "error": "NUMBER_ALREADY_USED",
                "message": "Record Book Number " + record_number + " is already registered to another client and cannot be reused."
            }
            raise SystemExit

        sr = frappe.get_all(
            "Client Record Book Serial",
            filters={"record_book_number": record_number},
            fields=["name", "record_book_number", "status", "branch", "assigned_client"],
            limit_page_length=1,
            ignore_permissions=True
        )
        if not sr:
            frappe.response["message"] = {"ok": 0, "message": "This serial was not issued by Stores."}
            raise SystemExit

        s = sr[0]
        if (s.get("status") or "") != "Available":
            frappe.response["message"] = {"ok": 0, "message": "This Record Book Number is already assigned or unavailable."}
            raise SystemExit

        serial_branch = clean(s.get("branch"))
        if branch and serial_branch and branch != serial_branch:
            frappe.response["message"] = {
                "ok": 0,
                "message": "This Record Book Number belongs to " + serial_branch + ", not " + branch + "."
            }
            raise SystemExit

        pdoc = frappe.get_doc("Patient", patient)
        pdoc.append("custom_record_book_numbers", {
            "record_book_number": record_number,
            "record_book_date": frappe.utils.nowdate(),
            "serial_reference": s.get("name"),
            "remarks": remarks,
            "added_by": current_user
        })
        pdoc.save(ignore_permissions=True)

        sdoc = frappe.get_doc("Client Record Book Serial", s.get("name"))
        sdoc.status = "Assigned"
        sdoc.assigned_client = patient
        sdoc.assigned_client_name = prow.get("patient_name") or prow.get("first_name") or patient
        sdoc.assigned_on = frappe.utils.now_datetime()
        sdoc.assigned_by = current_user
        sdoc.save(ignore_permissions=True)

        frappe.db.commit()

        frappe.response["message"] = {
            "ok": 1,
            "record_book_number": record_number,
            "records": get_records(patient),
            "message": "Record Book " + record_number + " assigned successfully."
        }
        raise SystemExit

    frappe.response["message"] = {"ok": 0, "message": "Unknown action."}
