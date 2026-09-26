"""md_audit_api

Original API: md_audit_api
Source modified: 2026-08-04 13:09:42.273302
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
    #  SERVER SCRIPT (API)  —  md_audit_api
    #  Script Type : API   ·   API Method : md_audit_api
    #  URL (summary): /api/method/md_audit_api
    #  URL (detail) : /api/method/md_audit_api?audit=AUDIT-2026-00001
    #
    #  Branch audit overview for the MD.
    #   summary: latest submitted audit per branch — score %, grade,
    #            violations, and the LOWEST-scoring sections (what to improve).
    #   detail : one audit's full section breakdown.
    #
    #  "What to improve" = sections with the lowest raw/raw_max %.
    #
    #  safe_exec-safe: dict params only, no None, no reserved aliases,
    #  no try/except, no % literals, no slicing of function results.
    # =====================================================================

    args = frappe.form_dict or {}
    audit = args.get("audit")

    # ---------- MODE: one audit — full section breakdown ----------
    if audit:
        an = str(audit).strip()
        head = _read_sql("""
        SELECT name, branch, audit_date, total_score, max_score,
               percentage, grade, has_violation, violation_summary,
               audit_status, auditor
        FROM `tabBranch Audit`
        WHERE name = %(n)s
        LIMIT 1
    """, {"n": an}, as_dict=True)
        secs = _read_sql("""
        SELECT section_code, section_name, raw, raw_max, group_score, weight
        FROM `tabBranch Audit Section Score`
        WHERE parent = %(n)s
        ORDER BY (raw / GREATEST(raw_max, 1)) ASC
    """, {"n": an}, as_dict=True)
        sections = []
        for r in secs:
            rw = float(r.get("raw") or 0)
            rmx = float(r.get("raw_max") or 0)
            p = 0.0
            if rmx > 0:
                p = round(rw / rmx * 100.0, 1)
            d = {}
            d["code"] = r.get("section_code")
            d["name"] = r.get("section_name")
            d["raw"] = rw
            d["raw_max"] = rmx
            d["pct"] = p
            d["weight"] = float(r.get("weight") or 0)
            sections.append(d)
        hd = {}
        if len(head) > 0:
            h = head[0]
            hd["name"] = h.get("name")
            hd["branch"] = h.get("branch")
            hd["audit_date"] = str(h.get("audit_date") or "")
            hd["percentage"] = float(h.get("percentage") or 0)
            hd["grade"] = h.get("grade") or ""
            hd["total_score"] = float(h.get("total_score") or 0)
            hd["max_score"] = float(h.get("max_score") or 0)
            hd["has_violation"] = int(h.get("has_violation") or 0)
            hd["violation_summary"] = h.get("violation_summary") or ""
            hd["status"] = h.get("audit_status") or ""
            hd["erp"] = "/app/branch-audit/" + str(h.get("name"))
        out = {}
        out["audit"] = hd
        out["sections"] = sections
        frappe.response["message"] = out

    # ---------- MODE: summary — latest audit per branch ----------
    else:
        # latest submitted audit per branch (docstatus = 1)
        latest = _read_sql("""
        SELECT ba.name, ba.branch, ba.audit_date, ba.percentage,
               ba.grade, ba.total_score, ba.max_score,
               ba.has_violation, ba.violation_summary, ba.audit_status
        FROM `tabBranch Audit` ba
        INNER JOIN (
            SELECT branch, MAX(audit_date) AS mx
            FROM `tabBranch Audit`
            WHERE docstatus = 1
            GROUP BY branch
        ) last ON last.branch = ba.branch AND last.mx = ba.audit_date
        WHERE ba.docstatus = 1
        ORDER BY ba.percentage ASC
    """, {}, as_dict=True)

        branches = []
        seen = {}
        tot_pct = 0.0
        n_aud = 0
        n_viol = 0
        for r in latest:
            br = r.get("branch")
            if br in seen:
                continue
            seen[br] = 1
            aname = r.get("name")
            # lowest 3 sections for this audit = improvement areas
            low = _read_sql("""
            SELECT section_name, raw, raw_max
            FROM `tabBranch Audit Section Score`
            WHERE parent = %(n)s
            ORDER BY (raw / GREATEST(raw_max, 1)) ASC
            LIMIT 3
        """, {"n": aname}, as_dict=True)
            improve = []
            for s in low:
                rw = float(s.get("raw") or 0)
                rmx = float(s.get("raw_max") or 0)
                sp = 0.0
                if rmx > 0:
                    sp = round(rw / rmx * 100.0, 1)
                imp = {}
                imp["name"] = s.get("section_name")
                imp["pct"] = sp
                improve.append(imp)
            pct = float(r.get("percentage") or 0)
            hv = int(r.get("has_violation") or 0)
            d = {}
            d["audit"] = aname
            d["branch"] = br
            d["audit_date"] = str(r.get("audit_date") or "")
            d["pct"] = pct
            d["grade"] = r.get("grade") or ""
            d["total_score"] = float(r.get("total_score") or 0)
            d["max_score"] = float(r.get("max_score") or 0)
            d["has_violation"] = hv
            d["violation_summary"] = r.get("violation_summary") or ""
            d["status"] = r.get("audit_status") or ""
            d["improve"] = improve
            d["erp"] = "/app/branch-audit/" + str(aname)
            branches.append(d)
            tot_pct = tot_pct + pct
            n_aud = n_aud + 1
            if hv == 1:
                n_viol = n_viol + 1

        totals = {}
        totals["audited_branches"] = n_aud
        if n_aud > 0:
            totals["avg_pct"] = round(tot_pct / n_aud, 1)
        else:
            totals["avg_pct"] = 0.0
        totals["with_violation"] = n_viol

        out = {}
        out["branches"] = branches
        out["totals"] = totals
        frappe.response["message"] = out
