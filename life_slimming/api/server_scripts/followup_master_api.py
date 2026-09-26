"""followup_master_api

Original API: followup_master_api
Source modified: 2026-07-31 19:50:19.546332
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
    # =====================================================================
    #  Server Script  ->  Script Type: API
    #  Name:            followup_master_api
    #  API Method:      followup_master_api
    #  Allow Guest:     No
    # ---------------------------------------------------------------------
    #  Call from the web page as:
    #     /api/method/followup_master_api?action=bootstrap
    #     /api/method/followup_master_api  (POST, action=save_followup / save_diet)
    #  Safe-exec friendly: no imports, no f-strings, no .format(), no unpack.
    # =====================================================================

    action = frappe.form_dict.get("action") or "bootstrap"
    out = {}

    # ---------------------------------------------------------------------
    # helper: normalise a followup extra dict to JSON text
    # ---------------------------------------------------------------------
    def to_json(v):
        try:
            return frappe.as_json(v)
        except Exception:
            return "{}"


    # =====================================================================
    # BOOTSTRAP  — everything the desk needs in one shot
    # =====================================================================
    if action == "bootstrap":

        # ---- branches ----
        branches = frappe.get_all("Branch", fields=["name"], order_by="name asc")
        branch_list = []
        for b in branches:
            branch_list.append({"n": b.get("name"), "c": ""})
        out["branches"] = branch_list

        # ---- employees (active only, the roles that matter for followups) ----
        emps = frappe.get_all(
            "Employee",
            filters={"status": "Active"},
            fields=["name", "employee_name", "designation", "branch"],
            order_by="employee_name asc",
            limit_page_length=600,
        )
        emp_list = []
        for e in emps:
            emp_list.append({
                "c": e.get("name"),
                "n": e.get("employee_name"),
                "r": e.get("designation") or "",
                "b": e.get("branch") or "",
            })
        out["employees"] = emp_list

        # ---- clients (recent patients; branch filter optional) ----
        br = frappe.form_dict.get("branch")
        pat_filters = {}
        if br and br != "All branches":
            pat_filters["branch_name"] = br

        pats = frappe.get_all(
            "Patient",
            filters=pat_filters,
            fields=[
                "name", "patient_name", "mobile", "phone", "email", "sex",
                "branch_name", "status", "custom_final_decision",
                "custom_client_visited_for_", "custom_treatment_category",
                "custom_weightin_kg", "custom_bmi", "custom_health_flag",
                "custom_remarks", "custom_client_photo", "creation",
            ],
            order_by="modified desc",
            limit_page_length=400,
        )

        # decide app-status from custom_final_decision
        # Real portal values (all 18k+ patients) are only: "Booked", "Not-Booked", "" / null
        def app_status(fd):
            if fd == "Not-Booked":
                return "Unjoined"
            # "Booked", "", and null all treated as Active
            return "Active"

        clients = []
        pat_names = []
        for p in pats:
            pat_names.append(p.get("name"))
            st = app_status(p.get("custom_final_decision"))
            clients.append({
                "id": p.get("name"),
                "n": p.get("patient_name") or p.get("name"),
                "mob": p.get("mobile") or "",
                "mob2": p.get("phone") or "",
                "email": p.get("email") or "",
                "sex": p.get("sex") or "",
                "br": p.get("branch_name") or "",
                "sv": p.get("custom_client_visited_for_") or p.get("custom_treatment_category") or "",
                "st": st,
                "fd": p.get("custom_final_decision") or "",
                "flag": p.get("custom_health_flag") or "",
                "ws": p.get("custom_weightin_kg") or 0,
                "bmi": p.get("custom_bmi") or 0,
                "prefNote": p.get("custom_remarks") or "",
                "photo": p.get("custom_client_photo") or "",
                "pend": 0, "val": 0, "paid": 0,
                "tot": 0, "done": 0, "bal": 0,
                "lastV": None, "mv": 0, "reg": "\u2014",
            })

        # ---- dues from Sales Invoice for these patients ----
        if pat_names:
            invs = frappe.get_all(
                "Sales Invoice",
                filters={"patient": ["in", pat_names], "docstatus": 1},
                fields=["patient", "grand_total", "outstanding_amount",
                        "posting_date", "status"],
                limit_page_length=0,
            )
            agg = {}
            for iv in invs:
                pid = iv.get("patient")
                row = agg.get(pid)
                if row is None:
                    row = {"val": 0, "pend": 0}
                    agg[pid] = row
                row["val"] = row["val"] + (iv.get("grand_total") or 0)
                row["pend"] = row["pend"] + (iv.get("outstanding_amount") or 0)
            for c in clients:
                r = agg.get(c["id"])
                if r is not None:
                    c["val"] = r["val"]
                    c["pend"] = r["pend"]
                    c["paid"] = r["val"] - r["pend"]

        # ---- Leads as the Unjoined pipeline ----
        # Real Lead.status vocabulary: Lead, Call Back, Appointment Booked,
        # Converted, TNA, Not Response, Call Disconnected, Not Enquired, Not interested
        # Include everything still worth chasing; exclude Converted (already a
        # patient) and Not interested (dead).
        lead_filters = {"status": ["not in", ["Converted", "Not interested"]]}
        if br and br != "All branches":
            lead_filters["branch"] = br
        leads = frappe.get_all(
            "Lead",
            filters=lead_filters,
            fields=[
                "name", "lead_name", "mobile_no", "phone", "email_id", "gender",
                "branch", "status", "enquired_for", "custom_remarks",
                "custom_next_followup_date", "custom_cc_stage",
                "custom_appointment_status", "custom_bmi", "custom_target_weight",
                "priority",
            ],
            order_by="modified desc",
            limit_page_length=400,
        )
        for l in leads:
            pr = "High" if l.get("priority") in ("High", "Urgent") else "Normal"
            clients.append({
                "id": l.get("name"),
                "n": l.get("lead_name") or l.get("name"),
                "mob": l.get("mobile_no") or l.get("phone") or "",
                "mob2": l.get("phone") or "",
                "email": l.get("email_id") or "",
                "sex": l.get("gender") or "",
                "br": l.get("branch") or "",
                "sv": l.get("enquired_for") or "",
                "st": "Unjoined",
                "fd": l.get("status") or "",
                "flag": "",
                "ws": 0,
                "bmi": l.get("custom_bmi") or 0,
                "prefNote": l.get("custom_remarks") or "",
                "photo": "",
                "pend": 0, "val": 0, "paid": 0,
                "tot": 0, "done": 0, "bal": 0,
                "lastV": None, "mv": 0, "reg": "\u2014",
                "is_lead": 1,
                "lead_status": l.get("status") or "",
                "cc_stage": l.get("custom_cc_stage") or "",
                "next_fu": str(l.get("custom_next_followup_date") or ""),
            })

        out["clients"] = clients

        # ---- existing followups (recent) ----
        fus = frappe.get_all(
            "LIFE Followup",
            fields=["name", "patient", "party_type", "party_id", "lead",
                    "patient_name", "followup_type",
                    "followup_date", "followup_time", "channels", "outcome",
                    "remarks", "logged_by", "employee", "branch",
                    "next_date", "priority", "extra_json"],
            order_by="followup_date desc, creation desc",
            limit_page_length=500,
        )
        fu_list = []
        for f in fus:
            chans = []
            raw = f.get("channels") or ""
            if raw:
                parts = raw.split(",")
                for p2 in parts:
                    v = p2.strip()
                    if v:
                        chans.append(v)
            ex = {}
            ej = f.get("extra_json")
            if ej:
                try:
                    ex = frappe.parse_json(ej)
                except Exception:
                    ex = {}
            cid_val = f.get("party_id") or f.get("patient") or f.get("lead")
            fu_list.append({
                "id": f.get("name"),
                "cid": cid_val,
                "party_type": f.get("party_type") or "Patient",
                "type": f.get("followup_type"),
                "d": str(f.get("followup_date") or ""),
                "t": f.get("followup_time") or "",
                "ch": chans,
                "out": f.get("outcome") or "",
                "rem": f.get("remarks") or "",
                "by": f.get("logged_by") or "",
                "emp": f.get("employee") or "",
                "br": f.get("branch") or "",
                "next": str(f.get("next_date") or ""),
                "pri": f.get("priority") or "Normal",
                "extra": ex,
            })
        out["followups"] = fu_list

        # ---- diet charts (recent) ----
        dcs = frappe.get_all(
            "LIFE Diet Chart",
            fields=["name", "patient", "chart_date", "template_name",
                    "duration", "prepared_by", "avoid_list", "message",
                    "total_kcal", "total_protein"],
            order_by="chart_date desc",
            limit_page_length=300,
        )
        dc_list = []
        for d in dcs:
            dc_list.append({
                "id": d.get("name"),
                "cid": d.get("patient"),
                "d": str(d.get("chart_date") or ""),
                "tpl": d.get("template_name") or "",
                "dur": d.get("duration") or "",
                "by": d.get("prepared_by") or "",
                "avoid": d.get("avoid_list") or "",
                "msg": d.get("message") or "",
                "kcal": d.get("total_kcal") or 0,
                "prot": d.get("total_protein") or 0,
            })
        out["diet_charts"] = dc_list

        out["user"] = {
            "name": frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
            "email": frappe.session.user,
        }
        out["ok"] = True


    # =====================================================================
    # SAVE FOLLOWUP
    # =====================================================================
    elif action == "save_followup":
        d = frappe.form_dict
        doc = frappe.new_doc("LIFE Followup")
        cid = d.get("cid")
        ptype = d.get("party_type") or "Patient"
        doc.party_type = ptype
        doc.party_id = cid
        if ptype == "Lead":
            doc.lead = cid
        else:
            doc.patient = cid
        doc.patient_name = d.get("client_name") or ""
        doc.followup_type = d.get("type")
        doc.followup_date = d.get("d")
        doc.followup_time = d.get("t") or ""
        doc.channels = d.get("ch") or ""
        doc.outcome = d.get("out") or ""
        doc.remarks = d.get("rem") or ""
        doc.logged_by = d.get("by") or frappe.session.user
        doc.employee = d.get("emp") or ""
        doc.branch = d.get("br") or None
        doc.next_date = d.get("next") or None
        doc.priority = d.get("pri") or "Normal"
        ex = d.get("extra")
        if ex:
            doc.extra_json = ex
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        out["ok"] = True
        out["id"] = doc.name


    # =====================================================================
    # SAVE DIET CHART
    # =====================================================================
    elif action == "save_diet":
        d = frappe.form_dict
        doc = frappe.new_doc("LIFE Diet Chart")
        doc.patient = d.get("cid")
        doc.patient_name = d.get("client_name") or ""
        doc.chart_date = d.get("d")
        doc.template_name = d.get("tpl") or ""
        doc.duration = d.get("dur") or ""
        doc.prepared_by = d.get("by") or ""
        doc.avoid_list = d.get("avoid") or ""
        doc.message = d.get("msg") or ""
        doc.total_kcal = d.get("kcal") or 0
        doc.total_protein = d.get("prot") or 0
        doc.branch = d.get("br") or None
        rows_raw = d.get("rows")
        if rows_raw:
            try:
                rows = frappe.parse_json(rows_raw)
            except Exception:
                rows = []
            for r in rows:
                doc.append("rows", {
                    "meal": r.get("meal") or "",
                    "item": r.get("item") or "",
                    "item_te": r.get("item_te") or r.get("te") or "",
                    "qty": r.get("qty") or 0,
                    "unit": r.get("unit") or "",
                    "kcal": r.get("kcal") or 0,
                    "protein": r.get("protein") or r.get("p") or 0,
                    "note": r.get("note") or "",
                })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        out["ok"] = True
        out["id"] = doc.name

    else:
        out["ok"] = False
        out["error"] = "unknown action"

    frappe.response["message"] = out
