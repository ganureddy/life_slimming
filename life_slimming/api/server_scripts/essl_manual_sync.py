"""ESSL Manual Sync Trigger

Original API: essl_manual_sync
Source modified: 2026-06-03 23:16:15.437803
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
    # ESSL PUSH RECEIVER
    # ESSL server pushes attendance logs TO this endpoint in real-time
    # No outbound HTTP needed — ERPNext just receives and saves
    #
    # Configure in ESSL: Settings -> Server Side Settings -> Data Push
    # Push URL: https://portal.lifescc.com/api/method/essl_manual_sync
    # Method: POST

    SHIFT_START  = "09:00"
    LATE_MINUTES = 15

    def get_employee_map():
        rows = frappe.get_all("Employee",
            filters={"status": "Active"},
            fields=["name", "employee_name", "attendance_device_id"])
        emp_map = {}
        for e in rows:
            dev_id = (e.get("attendance_device_id") or "").strip()
            if dev_id:
                emp_map[dev_id] = {"erp_code": e["name"], "name": e["employee_name"]}
        return emp_map

    def save_attendance(emp_code, emp_name, day, cin, cout, hrs, late):
        ex_row = frappe.db.get_value("Attendance",
            {"employee": emp_code, "attendance_date": day, "docstatus": ["!=", 2]},
            ["name", "docstatus"], as_dict=True)
        if ex_row and ex_row.docstatus == 1:
            return "skipped"
        if ex_row:
            doc = frappe.get_doc("Attendance", ex_row.name)
        else:
            doc = frappe.new_doc("Attendance")
            doc.employee        = emp_code
            doc.attendance_date = day
            doc.company         = "Life Slimming And Cosmetic Pvt Ltd"
        doc.status        = "Present"
        doc.in_time       = str(cin)
        doc.out_time      = str(cout) if cout else None
        doc.working_hours = hrs
        doc.late_entry    = late
        doc.flags.ignore_permissions = True
        doc.save()
        frappe.db.commit()
        return "saved"

    try:
        # ESSL Push sends POST data — try all known field name formats
        form = frappe.form_dict

        # --- ESSL push payload field names (varies by version) ---
        emp_id   = (form.get("UserId")   or form.get("userid")   or
                    form.get("UserID")   or form.get("EmpId")    or
                    form.get("emp_id")   or form.get("EmployeeCode") or "").strip()

        log_time = (form.get("LogDate")  or form.get("logdate")  or
                    form.get("PunchTime") or form.get("AttTime") or
                    form.get("DateTime") or form.get("punch_time") or "").strip()

        # If no push data — this is a manual/test call, run full daily sync from DB
        if not emp_id or not log_time:
            # Return status of what would sync — shows config is working
            emp_map = get_employee_map()
            today   = str(frappe.utils.today())
            att_count = frappe.db.count("Attendance",
                {"attendance_date": today, "docstatus": ["!=", 2]})
            frappe.response["message"] = {
                "status":             "ready",
                "message":            "ESSL Push Receiver is live. Configure ESSL to push to this URL.",
                "employees_linked":   len(emp_map),
                "attendance_today":   att_count,
                "push_url":           "https://portal.lifescc.com/api/method/essl_manual_sync",
                "essl_setup_steps": [
                    "1. Login to ESSL at http://183.83.216.82",
                    "2. Go to: Device Management -> Server Settings / Data Push",
                    "3. Set Push URL: https://portal.lifescc.com/api/method/essl_manual_sync",
                    "4. Set Method: POST",
                    "5. Save and Enable Push"
                ]
            }
        else:
            # Process single push record from ESSL
            emp_map = get_employee_map()
            emp     = emp_map.get(emp_id)
            if not emp:
                frappe.response["message"] = {
                    "status": "skipped",
                    "reason": "Device ID " + emp_id + " not linked to any employee in ERPNext"
                }
            else:
                try:
                    punch_dt = frappe.utils.get_datetime(log_time[:19])
                except Exception:
                    frappe.response["message"] = {"status": "error", "reason": "Bad datetime: " + log_time}

                day    = str(punch_dt.date())
                sp     = SHIFT_START.split(":")
                lc     = int(sp[0]) * 60 + int(sp[1]) + LATE_MINUTES
                in_m   = punch_dt.hour * 60 + punch_dt.minute
                late   = 1 if in_m > lc else 0

                # Single punch: save as IN, no OUT yet (will update on next push)
                ex_row = frappe.db.get_value("Attendance",
                    {"employee": emp["erp_code"], "attendance_date": day, "docstatus": ["!=", 2]},
                    ["name", "in_time", "docstatus"], as_dict=True)

                if ex_row and ex_row.docstatus == 1:
                    frappe.response["message"] = {"status": "skipped", "reason": "Already submitted"}
                elif ex_row:
                    # Update OUT time and recalculate hours
                    doc = frappe.get_doc("Attendance", ex_row.name)
                    old_in = frappe.utils.get_datetime(str(ex_row.in_time))
                    hrs    = round((punch_dt - old_in).total_seconds() / 3600.0, 2)
                    doc.out_time      = str(punch_dt)
                    doc.working_hours = hrs if hrs > 0 else 0
                    doc.flags.ignore_permissions = True
                    doc.save()
                    frappe.db.commit()
                    frappe.response["message"] = {
                        "status": "updated",
                        "employee": emp["name"],
                        "date": day,
                        "out_time": str(punch_dt)[11:16],
                        "hours": hrs
                    }
                else:
                    # New record — first punch = IN
                    doc = frappe.new_doc("Attendance")
                    doc.employee        = emp["erp_code"]
                    doc.attendance_date = day
                    doc.company         = "Life Slimming And Cosmetic Pvt Ltd"
                    doc.status          = "Present"
                    doc.in_time         = str(punch_dt)
                    doc.late_entry      = late
                    doc.flags.ignore_permissions = True
                    doc.save()
                    frappe.db.commit()
                    frappe.response["message"] = {
                        "status": "created",
                        "employee": emp["name"],
                        "date": day,
                        "in_time": str(punch_dt)[11:16],
                        "late": late
                    }

    except Exception as e:
        frappe.log_error(str(e), "ESSL Push Receiver")
        frappe.response["message"] = {"status": "error", "error": str(e)}
