"""Agent 360 leads without follow-up, synced from ERP Portal on 2026-11-10.

Source: life_cc_nofu_v1, modified 2026-11-06 14:36:39.666460.
"""
import json

import frappe
from life_slimming.api._runtime import script_endpoint
from life_slimming.portal_access import require_module


@script_endpoint(allow_guest=False)
def run(**kwargs):
    require_module("ccvisit", tab="nofollowup")
    # =====================================================================
    # Server Script : life_cc_nofu_v1      Type: API   API Method: life_cc_nofu_v1   Allow Guest: NO
    # LIFE CC Reports (branch-visit-report) · Agent 360 · "No follow-up since N days" (6-Nov-2026)
    # Read-only. Leads that WERE called before (app or ConVox) but not called again for N days.
    #   agents   JSON list of lead owners (empty = all CC agents) · CC agents always get only their own leads
    #   days     not called for at least N days (default 30)
    #   statuses JSON list of CC Sub Status ("(no status)" = blank) · closed=1 includes Lost / Invalid / Success / Visited Booked
    #   owner    optional single agent drill-down · start / limit = paging
    # Returns: day-bucket counts (1d … 2y), status counts, agent counts, total, rows (numbers masked to last 4)
    # =====================================================================
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Please login")
    roles = frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")
    MGR_USERS = ["bhuvan@lifescc.com", "administrator", "kp@lifescc.com", "surya@lifescc.com"]
    is_mgr = str(user).lower() in MGR_USERS
    for r in ["System Manager", "Sales Manager", "Call Center Export", "CC Manager"]:
        if r in roles:
            is_mgr = True
    fd = frappe.form_dict


    def ival(v):
        try:
            return int(float(v or 0))
        except Exception:
            return 0


    def jl(v):
        if isinstance(v, list):
            return v
        try:
            x = json.loads(v or "[]")
            return x if isinstance(x, list) else []
        except Exception:
            return []


    def dig(v):
        s = ""
        for ch in str(v or ""):
            if ch.isdigit():
                s = s + ch
        return s


    agents = [str(a).strip().lower() for a in jl(fd.get("agents")) if str(a).strip()]
    if not is_mgr:
        agents = [str(user).lower()]
    if not agents:
        agents = [str(u).lower() for u in frappe.get_all("User", filters=[["custom_portal_role", "=", "Call Centre"], ["enabled", "=", 1]], pluck="name", limit_page_length=500)]
    if not agents:
        frappe.throw("No CC agents found")

    days = ival(fd.get("days"))
    if days < 1:
        days = 30
    start = max(0, ival(fd.get("start")))
    limit = max(1, ival(fd.get("limit")) or 200)
    if limit > 500:
        limit = 500
    now = frappe.utils.now_datetime()
    LT = "greatest(ifnull(custom_last_call_time,'2000-01-01'), ifnull(custom_convox_last_call_time,'2000-01-01'))"
    P = {"o": tuple(agents), "c": str(frappe.utils.add_to_date(now, days=-days))[:19]}
    W = ("lower(lead_owner) in %(o)s and (ifnull(custom_call_count,0)>0 or ifnull(custom_convox_call_count,0)>0 "
         "or custom_last_call_time is not null or custom_convox_last_call_time is not null)")
    if not ival(fd.get("closed")):
        W = W + " and ifnull(custom_cc_stage,'') not in ('LOST','INVALID','SUCCESS') and ifnull(custom_appointment_status,'') not in ('Visited Booked')"

    # one-click day buckets (counts for every chip in one query)
    BK = [1, 2, 3, 7, 15, 30, 60, 90, 180, 365, 730]
    parts = []
    for i in range(len(BK)):
        P["b" + str(i)] = str(frappe.utils.add_to_date(now, days=-BK[i]))[:19]
        parts.append("sum(case when " + LT + " < %(b" + str(i) + ")s then 1 else 0 end) as b" + str(i))
    br = frappe.db.sql("select " + ", ".join(parts) + " from `tabLead` where " + W, P, as_dict=True)
    buckets = []
    for i in range(len(BK)):
        buckets.append({"days": BK[i], "n": ival((br[0] if br else {}).get("b" + str(i)))})

    W1 = W + " and " + LT + " < %(c)s"
    stc = []
    for r in frappe.db.sql("select ifnull(custom_cc_sub_status,'') as s, count(*) as n from `tabLead` where " + W1 +
                           " group by ifnull(custom_cc_sub_status,'') order by n desc", P, as_dict=True):
        stc.append({"status": r.get("s") or "(no status)", "n": ival(r.get("n"))})

    sts = [("" if str(x) == "(no status)" else str(x)) for x in jl(fd.get("statuses"))][:40]
    W2 = W1
    if sts:
        P["s"] = tuple(sts)
        W2 = W2 + " and ifnull(custom_cc_sub_status,'') in %(s)s"
    agc = []
    for r in frappe.db.sql("select lower(lead_owner) as o, count(*) as n from `tabLead` where " + W2 + " group by lower(lead_owner) order by n desc", P, as_dict=True):
        agc.append({"agent": r.get("o"), "n": ival(r.get("n"))})
    own = str(fd.get("owner") or "").strip().lower()
    W3 = W2
    if own:
        P["w"] = own
        W3 = W3 + " and lower(lead_owner) = %(w)s"
    tot = frappe.db.sql("select count(*) from `tabLead` where " + W3, P)[0][0]
    rows = frappe.db.sql("select name, lead_name, first_name, gender, mobile_no, phone, source, status, custom_cc_stage, custom_cc_sub_status, "
                         "custom_appointment_status, custom_appointment_date_and_time, custom_next_followup_date, lead_assign_to_branch, creation, "
                         "lead_owner, custom_call_count, custom_convox_call_count, custom_conclusion_remark, " + LT + " as lt from `tabLead` where " + W3 +
                         " order by lt desc limit " + str(limit) + " offset " + str(start), P, as_dict=True)
    out = []
    for r in rows:
        num = dig(r.get("mobile_no") or r.get("phone"))
        lt = str(r.get("lt") or "")[:19]
        out.append({"name": r.get("name"), "lead_name": r.get("lead_name") or r.get("first_name") or "", "gender": r.get("gender") or "",
                    "ph4": num[-4:] if num else "", "source": r.get("source") or "", "status": r.get("status") or "",
                    "stage": r.get("custom_cc_stage") or "", "sub": r.get("custom_cc_sub_status") or "",
                    "appt_status": r.get("custom_appointment_status") or "", "appt": str(r.get("custom_appointment_date_and_time") or ""),
                    "next": str(r.get("custom_next_followup_date") or ""), "branch": r.get("lead_assign_to_branch") or "",
                    "created": str(r.get("creation") or "")[:19], "owner": str(r.get("lead_owner") or "").lower(),
                    "calls": ival(r.get("custom_call_count")) + ival(r.get("custom_convox_call_count")),
                    "remark": r.get("custom_conclusion_remark") or "", "last": "" if lt.startswith("2000-01-01") else lt})
    frappe.response["message"] = {"days": days, "cut": P["c"], "buckets": buckets, "statuses": stc, "agents": agc,
                                  "total": tot, "start": start, "rows": out, "now": str(now)[:19]}
