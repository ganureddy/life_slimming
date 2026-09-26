"""lifescc_hrms_dashboard

Original API: lifescc_hrms_dashboard
Source modified: 2026-07-19 08:26:19.736997
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
    # LIFE HRMS - Dashboard API
    # CREATE AS: Server Script
    #   Script Type : API
    #   API Method  : lifescc_hrms_dashboard
    #   Allow Guest : NO
    # ------------------------------------------------------------
    # Returns one payload: KPIs + branch rollup + employee list.
    # Respects User Permissions (uses get_list, not db.get_all).
    # safe_exec: no imports, no f-strings, no db.commit()
    # ============================================================

    args = frappe.form_dict
    mode = args.get("mode") or "dashboard"

    cur_user = frappe.session.user
    role_rows = frappe.db.get_all(
        "Has Role",
        filters={"parent": cur_user, "parenttype": "User"},
        fields=["role"],
        limit_page_length=0,
    )
    roles = [r.get("role") for r in role_rows]
    is_hr = False
    if cur_user == "Administrator":
        is_hr = True
    else:
        for rl in ["System Manager", "HR Manager", "HR User"]:
            if rl in roles:
                is_hr = True

    # ---------- shared fetch (permission-aware) ----------
    EMP_FIELDS = [
        "name", "employee_name", "status", "branch", "department", "designation",
        "date_of_joining", "final_confirmation_date", "relieving_date",
        "resignation_letter_date", "custom_employment_status",
        "custom_notice_start_date", "custom_expected_relieving",
        "custom_docs_complete", "cell_number", "company_email", "image",
        "gender", "date_of_birth", "blood_group", "marital_status",
        "personal_email", "current_address", "permanent_address",
        "emergency_phone_number", "person_to_be_contacted",
        "employment_type", "grade", "reports_to", "company",
        "custom_doc_aadhaar", "custom_doc_pan", "custom_doc_bank",
        "custom_doc_education", "custom_doc_offer",
    ]

    def fetch_employees():
        return frappe.get_list(
            "Employee",
            fields=EMP_FIELDS,
            filters={"status": ["in", ["Active", "Inactive"]]},
            limit_page_length=0,
            ignore_permissions=False,
        )

    if mode == "dashboard":
        emps = fetch_employees()

        kpi = {
            "total": len(emps),
            "active": 0, "inactive": 0,
            "probation": 0, "confirmed": 0, "notice": 0, "resigned": 0,
            "docs_pending": 0, "no_branch": 0,
        }
        branches = {}

        for e in emps:
            if e.get("status") == "Active":
                kpi["active"] = kpi["active"] + 1
            else:
                kpi["inactive"] = kpi["inactive"] + 1

            es = e.get("custom_employment_status")
            if es == "Probation":
                kpi["probation"] = kpi["probation"] + 1
            elif es == "Confirmed":
                kpi["confirmed"] = kpi["confirmed"] + 1
            elif es == "Notice":
                kpi["notice"] = kpi["notice"] + 1
            elif es == "Resigned":
                kpi["resigned"] = kpi["resigned"] + 1

            if not e.get("custom_docs_complete"):
                kpi["docs_pending"] = kpi["docs_pending"] + 1

            b = e.get("branch")
            if not b:
                kpi["no_branch"] = kpi["no_branch"] + 1
                b = "(No Branch)"
            if b not in branches:
                branches[b] = {"branch": b, "total": 0, "active": 0,
                               "probation": 0, "notice": 0, "docs_pending": 0}
            branches[b]["total"] = branches[b]["total"] + 1
            if e.get("status") == "Active":
                branches[b]["active"] = branches[b]["active"] + 1
            if es == "Probation":
                branches[b]["probation"] = branches[b]["probation"] + 1
            if es == "Notice":
                branches[b]["notice"] = branches[b]["notice"] + 1
            if not e.get("custom_docs_complete"):
                branches[b]["docs_pending"] = branches[b]["docs_pending"] + 1

        # transfers (real data - 33 records live)
        transfers = frappe.get_list(
            "Employee Transfer",
            fields=["name", "employee", "employee_name", "transfer_date",
                    "new_company"],
            filters={"docstatus": 1},
            order_by="transfer_date desc",
            limit_page_length=50,
            ignore_permissions=False,
        )
        kpi["transfers"] = len(transfers)

        promos = frappe.get_list(
            "Employee Promotion",
            fields=["name", "employee", "employee_name", "promotion_date"],
            filters={"docstatus": 1},
            order_by="promotion_date desc",
            limit_page_length=50,
            ignore_permissions=False,
        )
        kpi["promotions"] = len(promos)

        blist = sorted(branches.values(), key=lambda x: -x["total"])

        frappe.response["message"] = {
            "ok": True,
            "is_hr": is_hr,
            "kpi": kpi,
            "branches": blist,
            "transfers": transfers,
            "promotions": promos,
            "generated": frappe.utils.now(),
        }

    elif mode == "list":
        emps = fetch_employees()
        q = (args.get("q") or "").lower().strip()
        fb = args.get("branch") or ""
        fs = args.get("emp_status") or ""

        out = []
        for e in emps:
            if fb and e.get("branch") != fb:
                continue
            if fs and e.get("custom_employment_status") != fs:
                continue
            if q:
                hay = " ".join([
                    str(e.get("employee_name") or ""),
                    str(e.get("name") or ""),
                    str(e.get("designation") or ""),
                    str(e.get("department") or ""),
                ]).lower()
                if q not in hay:
                    continue
            out.append(e)

        frappe.response["message"] = {"ok": True, "count": len(out), "rows": out[:500]}

    elif mode == "profile":
        emp_id = args.get("employee")
        if not emp_id:
            frappe.response["message"] = {"ok": False, "error": "employee required"}
        else:
            doc = frappe.get_doc("Employee", emp_id)
            doc.check_permission("read")

            transfers = frappe.get_list(
                "Employee Transfer",
                fields=["name", "transfer_date", "new_company"],
                filters={"employee": emp_id, "docstatus": 1},
                order_by="transfer_date desc",
                limit_page_length=0,
            )
            promos = frappe.get_list(
                "Employee Promotion",
                fields=["name", "promotion_date", "current_ctc", "revised_ctc"],
                filters={"employee": emp_id, "docstatus": 1},
                order_by="promotion_date desc",
                limit_page_length=0,
            )

            prof = {}
            for f in EMP_FIELDS:
                prof[f] = doc.get(f)
            prof["gender"] = doc.get("gender")
            prof["date_of_birth"] = doc.get("date_of_birth")
            prof["blood_group"] = doc.get("blood_group")
            prof["reports_to"] = doc.get("reports_to")
            prof["employment_type"] = doc.get("employment_type")
            prof["docs"] = {
                "aadhaar": doc.get("custom_doc_aadhaar"),
                "pan": doc.get("custom_doc_pan"),
                "bank": doc.get("custom_doc_bank"),
                "education": doc.get("custom_doc_education"),
                "offer": doc.get("custom_doc_offer"),
            }

            frappe.response["message"] = {
                "ok": True,
                "profile": prof,
                "transfers": transfers,
                "promotions": promos,
            }

    elif mode == "attendance":
        emp_id = args.get("employee")
        month = args.get("month")
        if not emp_id:
            frappe.response["message"] = {"ok": False, "error": "employee required"}
        else:
            filt = {"employee": emp_id, "docstatus": ["<", 2]}
            if month:
                filt["attendance_date"] = ["like", month + "%"]
            rows = frappe.get_list(
                "Attendance",
                fields=["attendance_date", "status", "custom_check_in_time",
                        "custom_check_out_time", "working_hours", "late_entry",
                        "early_exit"],
                filters=filt,
                order_by="attendance_date asc",
                limit_page_length=0,
                ignore_permissions=False,
            )
            frappe.response["message"] = {"ok": True, "count": len(rows), "rows": rows}

    elif mode == "audit":
        emp_id = args.get("employee")
        if not emp_id:
            frappe.response["message"] = {"ok": False, "error": "employee required"}
        else:
            rows = frappe.get_list(
                "Version",
                fields=["name", "ref_doctype", "docname", "owner", "creation"],
                filters={"ref_doctype": "Employee", "docname": emp_id},
                order_by="creation desc",
                limit_page_length=100,
                ignore_permissions=False,
            )
            frappe.response["message"] = {"ok": True, "count": len(rows), "rows": rows}

    elif mode == "refdata":
        branches = frappe.get_list(
            "Branch", fields=["name"], limit_page_length=0,
            ignore_permissions=False,
        )
        depts = frappe.get_list(
            "Department", fields=["name", "department_name"],
            limit_page_length=0, ignore_permissions=False,
        )
        frappe.response["message"] = {
            "ok": True,
            "branches": [b.get("name") for b in branches],
            "departments": [d.get("department_name") or d.get("name") for d in depts],
        }

    elif mode == "emp_full":
        emps = fetch_employees()
        palette = ["#059669", "#2563EB", "#D97706", "#7C3AED",
                   "#0891B2", "#BE185D", "#0F2D5E", "#DC2626"]
        out = []
        idx = 0
        for e in emps:
            st = e.get("custom_employment_status") or ""
            ui_status = "Active"
            if st == "Notice":
                ui_status = "Notice Period"
            elif st == "Resigned":
                ui_status = "Resigned"
            elif st == "Probation":
                ui_status = "Probation"
            elif e.get("status") == "Inactive":
                ui_status = "Resigned"

            docs = {
                "aadhaar": "uploaded" if e.get("custom_doc_aadhaar") else "pending",
                "pan": "uploaded" if e.get("custom_doc_pan") else "pending",
                "bank": "uploaded" if e.get("custom_doc_bank") else "pending",
                "education": "uploaded" if e.get("custom_doc_education") else "pending",
                "offer": "uploaded" if e.get("custom_doc_offer") else "pending",
            }

            rec = {
                "id": e.get("name"),
                "color": palette[idx % len(palette)],
                "name": e.get("employee_name") or e.get("name"),
                "designation": e.get("designation") or "-",
                "department": e.get("department") or "-",
                "branch": e.get("branch") or "",
                "branchName": e.get("branch") or "(No Branch)",
                "gender": e.get("gender") or "",
                "dob": e.get("date_of_birth") or "",
                "bloodGroup": e.get("blood_group") or "",
                "maritalStatus": e.get("marital_status") or "",
                "nationality": "Indian",
                "address": e.get("current_address") or "",
                "permanentAddress": e.get("permanent_address") or "",
                "mobile": e.get("cell_number") or "",
                "email": e.get("personal_email") or "",
                "emergencyName": e.get("person_to_be_contacted") or "",
                "emergencyRel": "",
                "emergencyPhone": e.get("emergency_phone_number") or "",
                "empNumber": e.get("name"),
                "joiningDate": e.get("date_of_joining") or "",
                "confirmationDate": e.get("final_confirmation_date") or "",
                "employmentType": e.get("employment_type") or "Full-Time",
                "category": "",
                "reportingManager": e.get("reports_to") or "",
                "hrManager": "",
                "companyEmail": e.get("company_email") or "",
                "officialMobile": e.get("cell_number") or "",
                "status": ui_status,
                "grade": e.get("grade") or "",
                "salaryGrade": e.get("grade") or "",
                "shift": "",
                "ctc": 0, "gross": 0, "basic": 0, "hra": 0, "ta": 0,
                "da": 0, "otherAllow": 0,
                "currentKPI": 0, "overallRating": 0,
                "leaveBalance": {"cl": 0, "sl": 0, "pl": 0, "ml": 0},
                "documents": docs,
                "assets": [],
                "erp": {},
                "promotions": [],
                "transfers": [],
                "salaryHistory": [],
                "performance": [],
                "warnings": [],
                "achievements": [],
                "appreciations": [],
                "training": [],
                "hrNotes": [],
                "expectedRelieving": e.get("custom_expected_relieving") or "",
                "noticeStart": e.get("custom_notice_start_date") or "",
                "attendance2024": [],
                "timeline": [],
                "isConfirmed": 1 if st == "Confirmed" else 0,
                "isProbation": 1 if st == "Probation" else 0,
            }
            out.append(rec)
            idx = idx + 1

        frappe.response["message"] = {"ok": True, "count": len(out), "employees": out}

    else:
        frappe.response["message"] = {"ok": False, "error": "unknown mode"}
