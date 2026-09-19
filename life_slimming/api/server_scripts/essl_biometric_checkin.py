"""essl_biometric_checkin

Original API: essl_biometric_checkin
Source modified: 2026-06-03 23:16:14.957526
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
    import frappe
    from frappe import _
    from datetime import datetime

    def essl_biometric_checkin():
        """
    API endpoint for eSSL eTimeTrackLite biometric device sync.
    Accepts punch data and creates Employee Checkin records.
    
    Matching logic (in order):
    1. attendance_device_id field on Employee (set biometric UserId here)
    2. employee field directly (if ERPNext Employee ID sent)
    
    POST body (JSON):
    {
        "biometric_id": "123",       # UserId from eTimeTrackLite device
        "employee": "HR-EMP-00001",  # OR direct ERPNext Employee ID
        "log_type": "IN",            # IN or OUT
        "time": "2026-04-19 09:05:00",
        "device_id": "VIJAYAWADA"    # Branch/device name
    }
    """
        try:
            data = frappe.request.get_json() or frappe.local.form_dict

            biometric_id = str(data.get("biometric_id", "")).strip()
            employee_id  = str(data.get("employee", "")).strip()
            log_type     = str(data.get("log_type", "")).strip().upper()
            time_str     = str(data.get("time", "")).strip()
            device_id    = str(data.get("device_id", "eSSL Biometric")).strip()

            # ── Validate log_type ──────────────────────────────────
            if log_type not in ("IN", "OUT"):
                frappe.local.response["http_status_code"] = 400
                return {"status": "error", "message": "log_type must be IN or OUT"}

            # ── Validate time ──────────────────────────────────────
            if not time_str:
                frappe.local.response["http_status_code"] = 400
                return {"status": "error", "message": "time is required (YYYY-MM-DD HH:MM:SS)"}
            try:
                punch_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                frappe.local.response["http_status_code"] = 400
                return {"status": "error", "message": "time must be YYYY-MM-DD HH:MM:SS format"}

            # ── Resolve Employee ───────────────────────────────────
            employee = None

            # Method 1: Match via attendance_device_id (biometric UserId stored on Employee)
            if biometric_id:
                emp = frappe.db.get_value("Employee",
                    {"attendance_device_id": biometric_id, "status": "Active"},
                    "name")
                if emp:
                    employee = emp

            # Method 2: Direct Employee ID passed
            if not employee and employee_id:
                if frappe.db.exists("Employee", employee_id):
                    employee = employee_id

            if not employee:
                frappe.local.response["http_status_code"] = 404
                return {
                    "status": "error",
                    "message": f"No active employee found for biometric_id='{biometric_id}' or employee='{employee_id}'. "
                               f"Please set the Attendance Device ID field on the Employee record in ERPNext."
                }

            # ── Duplicate check ────────────────────────────────────
            existing = frappe.db.exists("Employee Checkin", {
                "employee": employee,
                "time": punch_time,
                "log_type": log_type
            })
            if existing:
                return {
                    "status": "skipped",
                    "message": "Duplicate record already exists",
                    "name": existing,
                    "employee": employee,
                    "time": time_str
                }

            # ── Create Employee Checkin ────────────────────────────
            checkin = frappe.get_doc({
                "doctype":   "Employee Checkin",
                "employee":  employee,
                "log_type":  log_type,
                "time":      punch_time,
                "device_id": device_id
            })
            checkin.insert(ignore_permissions=False)
            frappe.db.commit()

            return {
                "status":        "success",
                "message":       "Checkin recorded successfully",
                "name":          checkin.name,
                "employee":      employee,
                "employee_name": checkin.employee_name,
                "log_type":      log_type,
                "time":          time_str,
                "device_id":     device_id
            }

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "eSSL Biometric Checkin Error")
            frappe.local.response["http_status_code"] = 500
            return {"status": "error", "message": str(e)}

    return frappe.call(essl_biometric_checkin, **dict(frappe.form_dict))
