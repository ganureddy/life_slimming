"""life_cc_mobile_v18 — native copy of the DB Server Script of the same name.

Original API: life_cc_mobile_v18 (Server Script, API, allow_guest 0)
Source modified: 2026-11-05 16:01:10.326368
Source sha256: 0e68bd2ec37bd5c502583d3bb77c11a91eff1f335bce4787931ab664def8bb00

The script body is copied verbatim into _native(), indented one level (see
../MIGRATION.md "Conversion details"); its final action chain is nested in
_dispatch() so the read actions in CACHED_ACTIONS can go through the read cache.

hooks.override_whitelisted_methods routes /api/method/life_cc_mobile_v18 here; Frappe applies that override before its
Server Script lookup, so the mobile app keeps calling the same name.

While site_config life_slimming_cache.mobile_native is 0 (the default), run()
delegates to the DB Server Script, so behaviour is unchanged until the native
copy has been compared with life_slimming.cache_tools.compare_mobile.
"""

import json

import frappe
import frappe.utils
from frappe.handler import run_server_script

from life_slimming import cache as read_cache
from life_slimming.api._runtime import script_endpoint

ACTIONS = frozenset({
    "queue", "dial", "finish", "sync", "recording", "calls", "summary", "appver", "me", "agents",
    "number", "wa_log", "timing", "live", "team", "plans", "plan_save", "plan_leads", "targets",
    "target_save", "feed",
})


# Read-only actions served through the read cache, with the request inputs each
# one reads (besides the effective agent and the viewer's manager flag).
CACHED_ACTIONS = {
    "queue": (),
    "calls": ("date",),
    "summary": ("agent", "from", "to", "team"),
    "live": ("lead", "since"),
    "team": (),
    "feed": ("agent", "since", "team"),
}


def _mobile_cache_key(action, agent, is_mgr, fd, today):
    """(namespace, scope, args) for a cacheable read action, else None."""
    if action not in CACHED_ACTIONS:
        return None
    args = {"today": today}
    args.update({name: fd.get(name) for name in CACHED_ACTIONS[action]})
    return (f"mobile_v18.{action}", f"{agent}|mgr={int(bool(is_mgr))}", args)


@script_endpoint(allow_guest=False)
def run(**kwargs):
    if not read_cache.settings().mobile_native:
        return run_server_script("life_cc_mobile_v18")
    return _native()


def _native():
    # ── verbatim body of Server Script "life_cc_mobile_v18" ──────────────────
    # LIFE_CC_SALES_OWNER_FIX_V1_20261105
    # =====================================================================
    # Server Script : life_cc_mobile_v18       Type: API   Allow Guest: NO   (V18 test — live app still uses life_cc_mobile_call)
    # LIFE mobile app — CC Agent mode (V17, 3-Nov-2026)
    #   action=queue    my call queue (untouched / follow-ups due / today's appts), numbers masked
    #   action=dial     returns the number for ONE of my leads + opens a LIFE Mobile Call Log row
    #   action=finish   closes the call row (status, ring/talk secs, disposition, remarks)
    #   action=sync     bulk upsert from the phone call log (native APK bridge) by call_key
    #   action=recording attach the uploaded phone recording (private file) to a call
    #   action=calls    my calls for a date (mobile + ConVox)
    #   action=summary  my light report for a period (leads, calls, talk, appts, walk-ins, booked)
    # Lead status itself is saved by the existing cc_update_lead API (same FSM as CC Dashboard).
    # Owner-scoped: an agent only sees / dials own leads. Managers may pass agent=<user>.
    # =====================================================================

    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Please login")

    MANAGER_ROLES = ["System Manager", "Sales Manager", "Call Center Export"]
    roles = frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")
    MANAGER_USERS = ["bhuvan@lifescc.com", "administrator", "kp@lifescc.com", "surya@lifescc.com"]
    is_mgr = str(user).lower() in MANAGER_USERS
    for r in MANAGER_ROLES:
        if r in roles:
            is_mgr = True

    fd = frappe.form_dict
    action = fd.get("action") or "queue"
    agent = user
    if is_mgr and fd.get("agent"):
        agent = fd.get("agent")

    today = frappe.utils.today()


    def dig(v):
        s = ""
        for ch in str(v or ""):
            if ch.isdigit():
                s = s + ch
        return s


    def last4(v):
        d = dig(v)
        return d[-4:] if d else ""


    def ival(v):
        try:
            return int(float(v or 0))
        except Exception:
            return 0


    def dt_or_none(v):
        v = str(v or "").strip().replace("T", " ")
        if not v:
            return None
        if len(v) == 16:
            v = v + ":00"
        return v[:19]


    def agent_full(u):
        return frappe.db.get_value("User", u, "full_name") or u


    def norm(s):
        o = ""
        for ch in str(s or "").lower():
            if ch >= "a" and ch <= "z":
                o = o + ch
        return o


    def convox_ids(u, frm, to):
        # ConVox agent IDs that belong to this ERP user (name-token match, same rule as the web report)
        full = str(agent_full(u) or "").lower()
        fn = norm(full)
        toks = []
        cur = ""
        for ch in full + " ":
            if ch >= "a" and ch <= "z":
                cur = cur + ch
            else:
                if len(cur) >= 3:
                    toks.append(cur)
                cur = ""
        ids = frappe.get_all("ConVox Call Event", filters=[["received_on", "between", [frm + " 00:00:00", to + " 23:59:59"]]],
                             fields=["agent_id"], distinct=True, limit_page_length=500)
        out = []
        for row in ids:
            a = row.get("agent_id") or ""
            c = norm(a)
            if len(c) < 3 or str(a).strip().upper() in ["CUSTOMER", "DIALER", "SYSTEM"]:
                continue
            hit = c in fn
            if not hit:
                for t in toks:
                    if t == c or (len(t) >= 5 and len(c) >= 5 and t[:5] == c[:5]):
                        hit = True
            if hit:
                out.append(a)
        return out


    LEAD_F = ["name", "lead_name", "first_name", "source", "status", "custom_cc_stage", "custom_cc_sub_status",
              "custom_next_followup_date", "custom_call_count", "custom_last_call_time", "custom_appointment_date_and_time",
              "custom_appointment_status", "creation", "modified", "lead_assign_to_branch", "mobile_no", "phone",
              "custom_treatment_interests", "custom_conclusion_remark", "enquired_for", "custom_convox_last_call_time", "custom_convox_call_count"]


    def slim(r):
        return {
            "name": r.get("name"), "lead_name": r.get("lead_name") or r.get("first_name") or "",
            "source": r.get("source") or "", "status": r.get("status") or "", "stage": r.get("custom_cc_stage") or "",
            "sub": r.get("custom_cc_sub_status") or "", "next": str(r.get("custom_next_followup_date") or ""),
            "calls": r.get("custom_call_count") or 0, "last_call": str(r.get("custom_last_call_time") or ""),
            "appt": str(r.get("custom_appointment_date_and_time") or ""), "appt_status": r.get("custom_appointment_status") or "",
            "created": str(r.get("creation") or ""), "modified": str(r.get("modified") or ""),
            "branch": r.get("lead_assign_to_branch") or "", "ph4": last4(r.get("mobile_no") or r.get("phone")),
            "interest": r.get("custom_treatment_interests") or r.get("enquired_for") or "",
            "concl": r.get("custom_conclusion_remark") or "", "convox": str(r.get("custom_convox_last_call_time") or ""),
            "cvx_calls": r.get("custom_convox_call_count") or 0
        }


    def untouched_count(owners):
        return frappe.db.count("Lead", filters=[["lead_owner", "in", owners], ["status", "in", ["Lead", "Open", ""]],
                                                ["custom_cc_stage", "not in", ["FOLLOW-UP", "SUCCESS", "LOST", "INVALID", "PIPELINE"]]])


    def in_hand_count(owners):
        return frappe.db.count("Lead", filters=[["lead_owner", "in", owners], ["custom_cc_stage", "not in", ["LOST", "INVALID"]]])


    def mobile_calls_by_lead(ag):
        out = {}
        for x in frappe.get_all("LIFE Mobile Call Log", filters=[["agent", "=", ag], ["lead", "is", "set"]], fields=["lead", "count(name) as n"],
                                group_by="lead", limit_page_length=20000):
            out[x.get("lead")] = x.get("n") or 0
        return out



    # ===================== V18 (4-Nov-2026): agent view, TL, auto dial, targets, feed, live sync =====================

    def cc_users():
        rows = frappe.get_all("User", filters=[["custom_portal_role", "=", "Call Centre"], ["enabled", "=", 1]],
                              fields=["name", "full_name"], order_by="full_name asc", limit_page_length=500)
        return rows


    def name_tokens(full):
        full = str(full or "").lower()
        toks = []
        cur = ""
        for ch in full + " ":
            if ch >= "a" and ch <= "z":
                cur = cur + ch
            else:
                if len(cur) >= 3:
                    toks.append(cur)
                cur = ""
        return toks


    def convox_map(users, frm, to):
        # {convox_agent_id: erp_user} for the given users, same name-token rule as the web report
        ids = frappe.get_all("ConVox Call Event", filters=[["received_on", "between", [frm + " 00:00:00", to + " 23:59:59"]]],
                             fields=["agent_id"], distinct=True, limit_page_length=500)
        out = {}
        for row in ids:
            a = row.get("agent_id") or ""
            c = norm(a)
            if len(c) < 3 or str(a).strip().upper() in ["CUSTOMER", "DIALER", "SYSTEM"]:
                continue
            for u in users:
                fn = norm(u.get("full_name"))
                hit = c in fn
                if not hit:
                    for t in name_tokens(u.get("full_name")):
                        if t == c or (len(t) >= 5 and len(c) >= 5 and t[:5] == c[:5]):
                            hit = True
                if hit:
                    out[a] = u.get("name")
                    break
        return out


    def require_mgr():
        if not is_mgr:
            frappe.throw("Only TL / Admin can change this")


    def require_editor():
        # plans + targets: CC TL (role Call Center Export) and Surya only
        if not ("Call Center Export" in roles or str(user).lower() in ["surya@lifescc.com", "administrator"]):
            frappe.throw("Only the CC TL and Surya can change plans and targets")


    def fixed_appts(owners, frm, to):
        # leads set to "Appointment Booked" by these agents in the period (fast: Lead table only)
        own = {}
        rows = frappe.get_all("Lead", filters=[["lead_owner", "in", owners], ["custom_cc_sub_status", "=", "Appointment Booked"],
                                               ["modified", "between", [frm + " 00:00:00", to + " 23:59:59"]]],
                              fields=["lead_owner"], limit_page_length=50000)
        for x in rows:
            o = x.get("lead_owner") or ""
            own[o] = (own.get(o) or 0) + 1
        return own


    def appt_counts(owners, frm, to):
        rows = frappe.get_all("Lead", filters=[["lead_owner", "in", owners], ["custom_appointment_date_and_time", "between", [frm + " 00:00:00", to + " 23:59:59"]]],
                              fields=["custom_appointment_status"], limit_page_length=50000)
        sch = 0
        walk = 0
        bk = 0
        for r in rows:
            s = str(r.get("custom_appointment_status") or "").strip().lower()
            if s in ["booked", "visited", "visited booked", "visited not booked", "not visited", "cancelled"]:
                sch = sch + 1
            if s in ["visited", "visited booked", "visited not booked"]:
                walk = walk + 1
            if s == "visited booked":
                bk = bk + 1
        return {"sch": sch, "walk": walk, "bk": bk}


    def call_counts(users, frm, to):
        owners = [u.get("name") for u in users]
        mob = frappe.get_all("LIFE Mobile Call Log", filters=[["agent", "in", owners], ["started_on", "between", [frm + " 00:00:00", to + " 23:59:59"]]],
                             fields=["call_status", "connected", "talk_seconds"], limit_page_length=50000)
        c = 0
        a = 0
        t = 0
        for r in mob:
            c = c + 1
            if r.get("call_status") == "Answered" or r.get("connected") == "Connected":
                a = a + 1
                t = t + ival(r.get("talk_seconds"))
        ids = list(convox_map(users, frm, to).keys())
        if ids:
            cv = frappe.get_all("ConVox Call Event", filters=[["agent_id", "in", ids], ["received_on", "between", [frm + " 00:00:00", to + " 23:59:59"]]],
                                fields=["call_status", "call_duration"], limit_page_length=100000)
            for r in cv:
                c = c + 1
                if str(r.get("call_status") or "").upper() == "ANSWERED":
                    a = a + 1
                    t = t + ival(r.get("call_duration"))
        return {"calls": c, "ans": a, "talk": t}


    def lead_patients(lead_names):
        pats = []
        for i in range(0, len(lead_names), 500):
            pats.extend(frappe.get_all("Patient", filters=[["custom_lead", "in", lead_names[i:i + 500]]], pluck="name", limit_page_length=5000))
        return pats


    def revenue(owners, frm, to):
        # CC revenue = submitted Sales Invoices (net, without GST) dated in the period for patients created from these agents' leads
        total = 0.0
        names = frappe.get_all("Lead", filters=[["lead_owner", "in", owners]],
                               pluck="name", limit_page_length=50000)
        if not names:
            return 0
        pats = lead_patients(names)
        for i in range(0, len(pats), 500):
            for x in frappe.get_all("Sales Invoice", filters=[["patient", "in", pats[i:i + 500]], ["docstatus", "=", 1], ["is_return", "=", 0],
                                                              ["posting_date", "between", [frm, to]]], fields=["net_total"], limit_page_length=50000):
                total = total + float(x.get("net_total") or 0)
        return round(total)


    def _dispatch():
        # The verbatim action chain. `r` is also the top-level loop variable
        # above, so keep rebinding the same variable as the original script.
        nonlocal r
        if action == "queue":
            frm7 = frappe.utils.add_days(today, -7)
            frm30 = frappe.utils.add_days(today, -30)
            tom = frappe.utils.add_days(today, 1)
            new_rows = frappe.get_all("Lead", fields=LEAD_F, filters=[["lead_owner", "=", agent], ["creation", ">=", frm7 + " 00:00:00"]],
                                      order_by="creation desc", limit_page_length=400)
            untouched = []
            for r in new_rows:
                st = str(r.get("status") or "").strip().lower()
                sg = str(r.get("custom_cc_stage") or "").strip().lower()
                if (st in ["", "lead", "open"]) and (sg in ["", "untouched"]):
                    untouched.append(slim(r))
            fu_rows = frappe.get_all("Lead", fields=LEAD_F, filters=[["lead_owner", "=", agent],
                                     ["custom_next_followup_date", "between", [frm30 + " 00:00:00", today + " 23:59:59"]],
                                     ["custom_cc_stage", "not in", ["LOST", "INVALID", "SUCCESS"]]],
                                     order_by="custom_next_followup_date asc", limit_page_length=400)
            ap_rows = frappe.get_all("Lead", fields=LEAD_F, filters=[["lead_owner", "=", agent],
                                     ["custom_appointment_date_and_time", "between", [today + " 00:00:00", tom + " 23:59:59"]]],
                                     order_by="custom_appointment_date_and_time asc", limit_page_length=300)
            mc = mobile_calls_by_lead(agent)
            fus = [slim(r) for r in fu_rows]
            aps = [slim(r) for r in ap_rows]
            for lst in [untouched, fus, aps]:
                for x in lst:
                    x["mob_calls"] = mc.get(x.get("name")) or 0
                    x["tc"] = (x.get("cvx_calls") or 0) + x["mob_calls"]
                    if not x["tc"]:
                        x["tc"] = x.get("calls") or 0
            frappe.response["message"] = {
                "agent": agent, "agent_name": agent_full(agent), "today": today, "now": str(frappe.utils.now_datetime())[:19],
                "untouched": untouched, "followups": fus, "appts": aps,
                "untouched_all": untouched_count([agent]), "in_hand": in_hand_count([agent]),
                "manager": 1 if is_mgr else 0
            }

        elif action == "dial":
            lead = fd.get("lead")
            if not lead:
                frappe.throw("lead is required")
            L = frappe.db.get_value("Lead", lead, ["name", "lead_name", "first_name", "mobile_no", "phone", "lead_owner"], as_dict=True)
            if not L:
                frappe.throw("Lead not found")
            if (L.get("lead_owner") != user) and not is_mgr:
                frappe.throw("This lead is not assigned to you")
            which = fd.get("which") or "mobile"
            num = dig(L.get("phone") if which == "alt" else (L.get("mobile_no") or L.get("phone")))
            if len(num) < 10:
                frappe.throw("No valid mobile number on this lead")
            num = num[-10:]
            key = str(fd.get("call_key") or "")[:120]
            if key and frappe.db.exists("LIFE Mobile Call Log", {"call_key": key}):
                name = frappe.db.get_value("LIFE Mobile Call Log", {"call_key": key}, "name")
            else:
                d = frappe.get_doc({
                    "doctype": "LIFE Mobile Call Log", "agent": user, "agent_name": agent_full(user),
                    "lead": L.get("name"), "lead_name": L.get("lead_name") or L.get("first_name") or "",
                    "mobile_number": num, "direction": "Outgoing", "call_status": "Dialing",
                    "started_on": frappe.utils.now_datetime(), "data_source": "App Timer",
                    "call_key": key or None, "device_id": str(fd.get("device") or "")[:140],
                    "app_version": str(fd.get("app_version") or "")[:60],
                    "auto_plan": str(fd.get("plan") or "")[:140]
                })
                d.insert(ignore_permissions=True)
                name = d.name
            frappe.db.commit()
            frappe.response["message"] = {"ok": 1, "id": name, "number": num, "tel": "+91" + num}

        elif action == "finish":
            cid = fd.get("id")
            if not cid or not frappe.db.exists("LIFE Mobile Call Log", cid):
                frappe.throw("Call not found")
            d = frappe.get_doc("LIFE Mobile Call Log", cid)
            if d.agent != user and not is_mgr:
                frappe.throw("Not your call")
            st = fd.get("call_status") or ""
            if st in ["Answered", "Not Answered", "Busy", "Rejected", "Unknown"]:
                d.call_status = st
            if fd.get("started_on"):
                d.started_on = dt_or_none(fd.get("started_on"))
            d.ended_on = dt_or_none(fd.get("ended_on")) or frappe.utils.now_datetime()
            d.ring_seconds = ival(fd.get("ring_seconds"))
            d.talk_seconds = ival(fd.get("talk_seconds"))
            src = fd.get("data_source") or ""
            if src in ["Phone Call Log", "App Timer", "Manual"]:
                d.data_source = src
            if fd.get("connected") in ["Connected", "Not Connected"]:
                d.connected = fd.get("connected")
            if fd.get("disposition"):
                d.disposition = str(fd.get("disposition"))[:140]
            if fd.get("cc_stage"):
                d.cc_stage = str(fd.get("cc_stage"))[:40]
            if fd.get("next_followup"):
                d.next_followup = dt_or_none(fd.get("next_followup"))
            if fd.get("remarks"):
                d.remarks = str(fd.get("remarks"))[:1000]
            if fd.get("lead_updated"):
                d.lead_updated = 1
            d.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.response["message"] = {"ok": 1, "id": d.name}

        elif action == "sync":
            # rows from the phone's call log (native APK bridge): [{key, number, type, start, ring, talk, status}]
            raw = fd.get("rows") or "[]"
            rows = raw if isinstance(raw, list) else json.loads(raw)
            made = 0
            upd = 0
            for r in rows[:300]:
                key = str(r.get("key") or "")[:120]
                num = dig(r.get("number"))[-10:]
                if not key or len(num) < 10:
                    continue
                lead = ""
                found = frappe.get_all("Lead", filters=[["lead_owner", "=", user]], or_filters=[["mobile_no", "like", "%" + num], ["phone", "like", "%" + num]],
                                       fields=["name", "lead_name"], limit_page_length=1)
                if found:
                    lead = found[0].get("name")
                vals = {"call_status": r.get("status") if r.get("status") in ["Answered", "Not Answered", "Busy", "Rejected", "Unknown"] else "Unknown",
                        "started_on": dt_or_none(r.get("start")), "ring_seconds": ival(r.get("ring")), "talk_seconds": ival(r.get("talk")),
                        "data_source": "Phone Call Log", "direction": r.get("type") if r.get("type") in ["Outgoing", "Incoming", "Missed"] else "Outgoing"}
                ex = frappe.db.get_value("LIFE Mobile Call Log", {"call_key": key}, "name")
                if not ex and r.get("app_id") and frappe.db.exists("LIFE Mobile Call Log", r.get("app_id")):
                    ex = r.get("app_id")
                if ex:
                    d = frappe.get_doc("LIFE Mobile Call Log", ex)
                    if d.agent != user:
                        continue
                    for k in vals:
                        d.set(k, vals[k])
                    d.save(ignore_permissions=True)
                    upd = upd + 1
                else:
                    if not lead:
                        continue  # only work calls to own leads are stored, personal calls are ignored
                    vals.update({"doctype": "LIFE Mobile Call Log", "agent": user, "agent_name": agent_full(user), "lead": lead,
                                 "lead_name": found[0].get("lead_name") or "", "mobile_number": num, "call_key": key})
                    frappe.get_doc(vals).insert(ignore_permissions=True)
                    made = made + 1
            frappe.db.commit()
            frappe.response["message"] = {"ok": 1, "created": made, "updated": upd}

        elif action == "recording":
            # APK uploads the phone's call recording (upload_file, private, attached to this call) then calls this
            cid = fd.get("id")
            url = str(fd.get("file_url") or "")
            if not cid or not frappe.db.exists("LIFE Mobile Call Log", cid):
                frappe.throw("Call not found")
            d = frappe.get_doc("LIFE Mobile Call Log", cid)
            if d.agent != user and not is_mgr:
                frappe.throw("Not your call")
            if not url.startswith("/private/files/"):
                frappe.throw("Recording must be a private file")
            d.recording = url
            d.recording_available = 1
            d.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.response["message"] = {"ok": 1, "id": d.name}

        elif action == "calls":
            day = fd.get("date") or today
            m = frappe.get_all("LIFE Mobile Call Log", filters=[["agent", "=", agent], ["started_on", "between", [day + " 00:00:00", day + " 23:59:59"]]],
                               fields=["name", "lead", "lead_name", "mobile_number", "call_status", "started_on", "talk_seconds", "ring_seconds",
                                       "disposition", "connected", "data_source", "recording_available", "remarks"],
                               order_by="started_on desc", limit_page_length=500)
            for r in m:
                r["ph4"] = last4(r.pop("mobile_number"))
                r["src"] = "mobile"
                r["started_on"] = str(r.get("started_on") or "")
            ids = convox_ids(agent, day, day)
            c = []
            if ids:
                c = frappe.get_all("ConVox Call Event", filters=[["agent_id", "in", ids], ["received_on", "between", [day + " 00:00:00", day + " 23:59:59"]]],
                                   fields=["name", "crm_lead", "mobile_number", "call_status", "received_on", "call_duration", "ring_duration", "disposition", "recording_available"],
                                   order_by="received_on desc", limit_page_length=1000)
                names = []
                nums = []
                for r in c:
                    if r.get("crm_lead"):
                        names.append(r.get("crm_lead"))
                    else:
                        n10 = dig(r.get("mobile_number"))[-10:]
                        if len(n10) == 10:
                            nums.extend([n10, "91" + n10, "+91" + n10, "+91-" + n10, "0" + n10])
                lmap = {}
                if names:
                    for x in frappe.get_all("Lead", filters=[["name", "in", list(set(names))]], fields=["name", "lead_name"], limit_page_length=2000):
                        lmap[x.get("name")] = x.get("lead_name") or ""
                nmap = {}
                if nums:
                    for x in frappe.get_all("Lead", filters=[["mobile_no", "in", list(set(nums))]], fields=["name", "lead_name", "mobile_no"], limit_page_length=2000):
                        nmap[dig(x.get("mobile_no"))[-10:]] = [x.get("name"), x.get("lead_name") or ""]
                for r in c:
                    n10 = dig(r.get("mobile_number"))[-10:]
                    if r.get("crm_lead"):
                        r["lead_name"] = lmap.get(r.get("crm_lead")) or ""
                    elif nmap.get(n10):
                        r["crm_lead"] = nmap.get(n10)[0]
                        r["lead_name"] = nmap.get(n10)[1]
                    r["ph4"] = last4(r.pop("mobile_number"))
                    r["src"] = "convox"
                    r["received_on"] = str(r.get("received_on") or "")
            frappe.response["message"] = {"date": day, "mobile": m, "convox": c, "convox_ids": ids}

        elif action == "summary":
            frm = fd.get("from") or today
            to = fd.get("to") or today
            a0 = frm + " 00:00:00"
            a1 = to + " 23:59:59"
            team = 1 if (is_mgr and fd.get("team") and not fd.get("agent")) else 0
            U = cc_users() if team else [{"name": agent, "full_name": agent_full(agent)}]
            owners = [u.get("name") for u in U]
            leads = frappe.get_all("Lead", filters=[["lead_owner", "in", owners], ["creation", "between", [a0, a1]]],
                                   fields=["status", "custom_cc_stage"], limit_page_length=50000)
            unt = 0
            junk = 0
            for r in leads:
                st = str(r.get("status") or "").strip().lower()
                sg = str(r.get("custom_cc_stage") or "").strip().lower()
                if (st in ["", "lead", "open"]) and (sg in ["", "untouched"]):
                    unt = unt + 1
                if sg == "invalid":
                    junk = junk + 1
            A = appt_counts(owners, frm, to)
            fixed = sum(fixed_appts(owners, frm, to).values())
            mob = frappe.get_all("LIFE Mobile Call Log", filters=[["agent", "in", owners], ["started_on", "between", [a0, a1]]],
                                 fields=["call_status", "talk_seconds", "started_on", "connected", "data_source"], limit_page_length=50000)
            M = {"calls": len(mob), "ans": 0, "talk": 0, "long": 0, "exact": 0}
            hours = {}
            first = ""
            last = ""
            for r in mob:
                t = ival(r.get("talk_seconds"))
                if r.get("call_status") == "Answered" or r.get("connected") == "Connected":
                    M["ans"] = M["ans"] + 1
                M["talk"] = M["talk"] + t
                if t >= 60:
                    M["long"] = M["long"] + 1
                if r.get("data_source") == "Phone Call Log":
                    M["exact"] = M["exact"] + 1
                s = str(r.get("started_on") or "")
                if s:
                    h = s[11:13]
                    hours[h] = (hours.get(h) or 0) + 1
                    if not first or s < first:
                        first = s
                    if s > last:
                        last = s
            ids = list(convox_map(U, frm, to).keys())
            C = {"calls": 0, "ans": 0, "talk": 0, "long": 0, "ids": ids}
            if ids:
                cv = frappe.get_all("ConVox Call Event", filters=[["agent_id", "in", ids], ["received_on", "between", [a0, a1]]],
                                    fields=["call_status", "call_duration", "received_on"], limit_page_length=100000)
                for r in cv:
                    C["calls"] = C["calls"] + 1
                    t = ival(r.get("call_duration"))
                    if str(r.get("call_status") or "").upper() == "ANSWERED":
                        C["ans"] = C["ans"] + 1
                        C["talk"] = C["talk"] + t
                        if t >= 60:
                            C["long"] = C["long"] + 1
                    s = str(r.get("received_on") or "")
                    if s:
                        h = s[11:13]
                        hours[h] = (hours.get(h) or 0) + 1
                        if not first or s < first:
                            first = s
                        if s > last:
                            last = s
            # sales summary: invoices dated in the period for patients created from these agents' leads
            SL = {"invoices": 0, "net": 0, "billed": 0, "outstanding": 0, "clients": 0}
            bl = frappe.get_all("Lead", filters=[["lead_owner", "in", owners]],
                                pluck="name", limit_page_length=50000)
            if bl:
                pats = lead_patients(bl)
                seen = {}
                for i in range(0, len(pats), 500):
                    for x in frappe.get_all("Sales Invoice", filters=[["patient", "in", pats[i:i + 500]], ["docstatus", "=", 1], ["is_return", "=", 0],
                                                                      ["posting_date", "between", [frm, to]]],
                                            fields=["patient", "net_total", "grand_total", "outstanding_amount"], limit_page_length=50000):
                        SL["invoices"] = SL["invoices"] + 1
                        SL["net"] = SL["net"] + float(x.get("net_total") or 0)
                        SL["billed"] = SL["billed"] + float(x.get("grand_total") or 0)
                        SL["outstanding"] = SL["outstanding"] + float(x.get("outstanding_amount") or 0)
                        seen[x.get("patient")] = 1
                SL["clients"] = len(seen)
            SL["collected"] = SL["billed"] - SL["outstanding"]
            frappe.response["message"] = {
                "agent": "" if team else agent, "agent_name": "All CC agents" if team else agent_full(agent), "team": team, "agents": len(owners), "from": frm, "to": to,
                "leads": {"received": len(leads), "untouched": unt, "worked": len(leads) - unt, "junk": junk,
                          "untouched_all": untouched_count(owners), "in_hand": in_hand_count(owners)},
                "appts": {"fixed": fixed, "scheduled": A["sch"], "walkins": A["walk"], "booked": A["bk"]},
                "sales": SL, "mobile": M, "convox": C, "hours": hours, "first": first, "last": last
            }

        elif action == "appver":
            # tiny update check for the mobile app (instead of downloading the whole page every 5 minutes)
            route = str(fd.get("route") or "").strip("/")
            m = frappe.db.get_value("Web Page", {"route": route}, "modified") if route else None
            frappe.response["message"] = {"modified": str(m or "")}

        elif action == "me":
            u = frappe.db.get_value("User", user, ["full_name", "user_image", "last_login", "last_active"], as_dict=True) or {}
            frappe.response["message"] = {"user": user, "full_name": u.get("full_name") or user, "image": u.get("user_image") or "",
                                          "last_login": str(u.get("last_login") or ""), "now": str(frappe.utils.now_datetime())[:19]}

        elif action == "agents":
            require_mgr()
            us = cc_users()
            uc = {}
            for x in frappe.get_all("Lead", filters=[["lead_owner", "in", [u.get("name") for u in us]], ["status", "in", ["Lead", "Open", ""]],
                                                     ["custom_cc_stage", "not in", ["FOLLOW-UP", "SUCCESS", "LOST", "INVALID", "PIPELINE"]]],
                                    fields=["lead_owner", "count(name) as n"], group_by="lead_owner", limit_page_length=1000):
                uc[x.get("lead_owner")] = x.get("n") or 0
            frappe.response["message"] = {"agents": [{"user": u.get("name"), "name": u.get("full_name") or u.get("name"), "untouched": uc.get(u.get("name")) or 0} for u in us]}

        elif action == "number":
            lead = fd.get("lead")
            L = frappe.db.get_value("Lead", lead, ["name", "mobile_no", "phone", "lead_owner"], as_dict=True)
            if not L:
                frappe.throw("Lead not found")
            if L.get("lead_owner") != user and not is_mgr:
                frappe.throw("This lead is not assigned to you")
            num = dig(L.get("mobile_no") or L.get("phone"))[-10:]
            if len(num) < 10:
                frappe.throw("No valid mobile number on this lead")
            frappe.response["message"] = {"number": num}

        elif action == "wa_log":
            lead = fd.get("lead")
            if lead and frappe.db.exists("Lead", lead):
                frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "Lead", "reference_name": lead,
                                "content": "WhatsApp opened from LIFE app (" + str(fd.get("template") or "chat")[:20] + ") by " + agent_full(user)}).insert(ignore_permissions=True)
                frappe.db.commit()
            frappe.response["message"] = {"ok": 1}

        elif action == "timing":
            cid = fd.get("id")
            if not cid or not frappe.db.exists("LIFE Mobile Call Log", cid):
                frappe.throw("Call not found")
            d = frappe.get_doc("LIFE Mobile Call Log", cid)
            if d.agent != user:
                frappe.throw("Not your call")
            if fd.get("call_status") in ["Answered", "Not Answered", "Busy", "Rejected", "Unknown"]:
                d.call_status = fd.get("call_status")
            d.talk_seconds = ival(fd.get("talk_seconds"))
            d.ring_seconds = ival(fd.get("ring_seconds"))
            if fd.get("started_on"):
                d.started_on = dt_or_none(fd.get("started_on"))
            d.data_source = "Phone Call Log"
            d.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.response["message"] = {"ok": 1}

        elif action == "live":
            lead = fd.get("lead")
            if lead:
                # phone asks: did the agent already save this lead on the computer during the call?
                L = frappe.db.get_value("Lead", lead, ["modified", "modified_by", "custom_cc_sub_status", "custom_cc_stage", "lead_owner"], as_dict=True) or {}
                since = dt_or_none(fd.get("since")) or ""
                upd = 1 if (L and str(L.get("modified") or "")[:19] > since and L.get("modified_by") == user) else 0
                frappe.response["message"] = {"updated_elsewhere": upd, "sub": L.get("custom_cc_sub_status") or "", "stage": L.get("custom_cc_stage") or "",
                                              "modified": str(L.get("modified") or "")}
            else:
                # computer asks: is this agent on a call from the LIFE app right now?
                frm = str(frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-20))[:19]
                rows = frappe.get_all("LIFE Mobile Call Log", filters=[["agent", "=", agent], ["started_on", ">=", frm]],
                                      fields=["name", "lead", "lead_name", "mobile_number", "call_status", "started_on", "ended_on", "disposition", "auto_plan"],
                                      order_by="started_on desc", limit_page_length=1)
                call = None
                if rows:
                    r = rows[0]
                    call = {"id": r.get("name"), "lead": r.get("lead"), "lead_name": r.get("lead_name"), "ph4": last4(r.get("mobile_number")),
                            "status": r.get("call_status"), "started_on": str(r.get("started_on") or ""), "ended_on": str(r.get("ended_on") or ""),
                            "disposition": r.get("disposition") or "", "auto": 1 if r.get("auto_plan") else 0, "live": 1 if r.get("call_status") == "Dialing" else 0}
                frappe.response["message"] = {"call": call, "now": str(frappe.utils.now_datetime())[:19]}

        elif action == "team":
            require_mgr()
            users = cc_users()
            owners = [u.get("name") for u in users]
            a0 = today + " 00:00:00"
            a1 = today + " 23:59:59"
            R = {}
            for u in users:
                R[u.get("name")] = {"user": u.get("name"), "name": u.get("full_name") or u.get("name"), "calls": 0, "ans": 0, "talk": 0, "fixed": 0,
                                    "last": "", "live": 0, "live_lead": "", "ad": 0}
            for r in frappe.get_all("LIFE Mobile Call Log", filters=[["agent", "in", owners], ["started_on", "between", [a0, a1]]],
                                    fields=["agent", "call_status", "connected", "talk_seconds", "started_on", "lead_name", "auto_plan"], order_by="started_on asc", limit_page_length=50000):
                x = R.get(r.get("agent"))
                if not x:
                    continue
                x["calls"] = x["calls"] + 1
                if r.get("call_status") == "Answered" or r.get("connected") == "Connected":
                    x["ans"] = x["ans"] + 1
                    x["talk"] = x["talk"] + ival(r.get("talk_seconds"))
                s = str(r.get("started_on") or "")[:19]
                if s > x["last"]:
                    x["last"] = s
                if r.get("call_status") == "Dialing" and s >= str(frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-20))[:19]:
                    x["live"] = 1
                    x["live_lead"] = r.get("lead_name") or ""
                if r.get("auto_plan") and s >= str(frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-15))[:19]:
                    x["ad"] = 1
            m = convox_map(users, today, today)
            if m:
                for r in frappe.get_all("ConVox Call Event", filters=[["agent_id", "in", list(m.keys())], ["received_on", "between", [a0, a1]]],
                                        fields=["agent_id", "call_status", "call_duration", "received_on"], limit_page_length=100000):
                    x = R.get(m.get(r.get("agent_id")))
                    if not x:
                        continue
                    x["calls"] = x["calls"] + 1
                    if str(r.get("call_status") or "").upper() == "ANSWERED":
                        x["ans"] = x["ans"] + 1
                        x["talk"] = x["talk"] + ival(r.get("call_duration"))
                    s = str(r.get("received_on") or "")[:19]
                    if s > x["last"]:
                        x["last"] = s
            fx = fixed_appts(owners, today, today)
            nowd = frappe.utils.now_datetime()
            out = []
            for k in R:
                x = R[k]
                x["fixed"] = fx.get(k) or 0
                x["idle_min"] = 0
                if x["last"]:
                    try:
                        x["idle_min"] = int((nowd - frappe.utils.get_datetime(x["last"])).total_seconds() / 60)
                    except Exception:
                        x["idle_min"] = 0
                out.append(x)
            out.sort(key=lambda z: (-z["live"], -z["calls"]))
            frappe.response["message"] = {"rows": out, "date": today}

        elif action == "plans":
            rows = frappe.get_all("LIFE CC Auto Dial Plan", fields=["name", "plan_name", "statuses", "order_by", "from_date", "to_date", "gap_seconds", "next_rule",
                                                                    "agents", "active", "daily_cap", "skip_called_today"], order_by="modified desc", limit_page_length=200)
            for r in rows:
                r["from_date"] = str(r.get("from_date") or "")
                r["to_date"] = str(r.get("to_date") or "")
            mine = []
            for r in rows:
                ag = [x.strip() for x in str(r.get("agents") or "ALL").split(",") if x.strip()]
                if r.get("active") and ("ALL" in ag or agent in ag):
                    mine.append(r)
            frappe.response["message"] = {"plans": rows if is_mgr else [], "mine": mine}

        elif action == "plan_save":
            require_editor()
            d = json.loads(fd.get("doc") or "{}")
            keys = ["plan_name", "statuses", "order_by", "from_date", "to_date", "gap_seconds", "next_rule", "agents", "active", "daily_cap", "skip_called_today"]
            if d.get("name") and frappe.db.exists("LIFE CC Auto Dial Plan", d.get("name")):
                doc = frappe.get_doc("LIFE CC Auto Dial Plan", d.get("name"))
            else:
                doc = frappe.get_doc({"doctype": "LIFE CC Auto Dial Plan", "active": 1})
            for k in keys:
                if k in d:
                    v = d.get(k)
                    if k in ["from_date", "to_date"] and not v:
                        v = None
                    doc.set(k, v)
            if not doc.plan_name:
                frappe.throw("Plan name is required")
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.response["message"] = {"ok": 1, "name": doc.name}

        elif action == "plan_leads":
            P = frappe.get_doc("LIFE CC Auto Dial Plan", fd.get("plan"))
            ag = [x.strip() for x in str(P.agents or "ALL").split(",") if x.strip()]
            if not P.active or not ("ALL" in ag or agent in ag):
                frappe.throw("This plan is not assigned to you")
            sts = [x.strip() for x in str(P.statuses or "").split(",") if x.strip()]
            base = [["lead_owner", "=", agent]]
            if P.from_date:
                base.append(["creation", ">=", str(P.from_date) + " 00:00:00"])
            if P.to_date:
                base.append(["creation", "<=", str(P.to_date) + " 23:59:59"])
            order = "creation asc" if P.order_by == "Oldest first" else "creation desc"
            found = {}
            subs = [s for s in sts if s not in ["New (Untouched)", "Follow-up due"]]
            if subs:
                for r in frappe.get_all("Lead", fields=LEAD_F, filters=base + [["custom_cc_sub_status", "in", subs]], order_by=order, limit_page_length=600):
                    found[r.get("name")] = r
            if "New (Untouched)" in sts:
                for r in frappe.get_all("Lead", fields=LEAD_F, filters=base + [["status", "in", ["Lead", "Open", ""]]], order_by=order, limit_page_length=600):
                    sg = str(r.get("custom_cc_stage") or "").strip().lower()
                    if sg in ["", "untouched"]:
                        found[r.get("name")] = r
            if "Follow-up due" in sts:
                for r in frappe.get_all("Lead", fields=LEAD_F, filters=base + [["custom_next_followup_date", "<=", str(frappe.utils.now_datetime())[:19]],
                                                                               ["custom_cc_stage", "not in", ["LOST", "INVALID", "SUCCESS"]]], order_by=order, limit_page_length=600):
                    found[r.get("name")] = r
            rows = list(found.values())
            rows.sort(key=lambda z: str(z.get("creation") or ""), reverse=(P.order_by != "Oldest first"))
            out = []
            skip = 1 if P.skip_called_today is None else P.skip_called_today
            for r in rows:
                if skip:
                    if str(r.get("custom_last_call_time") or "")[:10] == today or str(r.get("custom_convox_last_call_time") or "")[:10] == today:
                        continue
                if not (r.get("mobile_no") or r.get("phone")):
                    continue
                out.append(slim(r))
                if len(out) >= 300:
                    break
            tc = frappe.db.count("LIFE Mobile Call Log", filters=[["agent", "=", agent], ["started_on", ">=", today + " 00:00:00"]])
            frappe.response["message"] = {"leads": out, "cap": P.daily_cap or 0, "today_calls": tc}

        elif action == "targets":
            users = cc_users()
            rows = frappe.get_all("LIFE CC Target", filters=[["active", "=", 1]], fields=["name", "target_name", "metric", "scope", "agent", "day_target", "month_target",
                                                                                         "sale_target", "incentive", "from_date", "to_date", "active"],
                                  order_by="modified desc", limit_page_length=50)
            if is_mgr:
                allrows = frappe.get_all("LIFE CC Target", fields=["name", "target_name", "metric", "scope", "agent", "day_target", "month_target",
                                                                  "sale_target", "incentive", "from_date", "to_date", "active"], order_by="modified desc", limit_page_length=100)
            else:
                allrows = rows
            cache = {}
            names = {}
            for u in users:
                names[u.get("name")] = u.get("full_name") or u.get("name")

            def metric_value(metric, us, frm, to):
                k = metric + "|" + ",".join(sorted([u.get("name") for u in us])) + "|" + frm + "|" + to
                if k in cache:
                    return cache[k]
                owners = [u.get("name") for u in us]
                v = 0
                if metric == "Appointments Fixed":
                    v = sum(fixed_appts(owners, frm, to).values())
                elif metric in ["Appointments Scheduled", "Walk-ins", "Booked"]:
                    a = appt_counts(owners, frm, to)
                    v = a["sch"] if metric == "Appointments Scheduled" else (a["walk"] if metric == "Walk-ins" else a["bk"])
                elif metric in ["Calls", "Answered Calls", "Talk Minutes"]:
                    c = call_counts(us, frm, to)
                    v = c["calls"] if metric == "Calls" else (c["ans"] if metric == "Answered Calls" else round(c["talk"] / 60.0))
                elif metric == "Sale Amount":
                    v = revenue(owners, frm, to)
                cache[k] = v
                return v

            out = []
            for t in allrows:
                frm = str(t.get("from_date") or "") or today[:8] + "06"
                to = str(t.get("to_date") or "") or today
                mto = min(to, today)
                if t.get("scope") == "Agent":
                    us = [u for u in users if u.get("name") == t.get("agent")]
                    if not is_mgr and t.get("agent") != agent:
                        continue
                else:
                    us = users
                x = dict(t)
                x["from"] = frm
                x["to"] = to
                x["from_date"] = frm
                x["to_date"] = to
                x["agent_name"] = names.get(t.get("agent")) or ""
                x["day_value"] = metric_value(t.get("metric"), us, today, today) if t.get("day_target") else 0
                x["month_value"] = metric_value(t.get("metric"), us, frm, mto) if t.get("month_target") else 0
                x["sale_value"] = revenue([u.get("name") for u in us], frm, mto) if t.get("sale_target") else 0
                x["day_pct"] = round(x["day_value"] * 100.0 / t.get("day_target"), 1) if t.get("day_target") else None
                x["month_pct"] = round(x["month_value"] * 100.0 / t.get("month_target"), 1) if t.get("month_target") else None
                x["sale_pct"] = round(x["sale_value"] * 100.0 / t.get("sale_target"), 1) if t.get("sale_target") else None
                if not t.get("active"):
                    x["day_pct"] = x["day_pct"] if is_mgr else None
                out.append(x)
            if not is_mgr:
                out = [x for x in out if x.get("active")]
            frappe.response["message"] = {"targets": out}

        elif action == "target_save":
            require_editor()
            d = json.loads(fd.get("doc") or "{}")
            keys = ["target_name", "metric", "scope", "agent", "day_target", "month_target", "sale_target", "incentive", "from_date", "to_date", "active"]
            if d.get("name") and frappe.db.exists("LIFE CC Target", d.get("name")):
                doc = frappe.get_doc("LIFE CC Target", d.get("name"))
            else:
                doc = frappe.get_doc({"doctype": "LIFE CC Target", "active": 1})
            for k in keys:
                if k in d:
                    v = d.get(k)
                    if k in ["from_date", "to_date", "agent"] and not v:
                        v = None
                    doc.set(k, v)
            if not doc.target_name:
                frappe.throw("Target name is required")
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.response["message"] = {"ok": 1, "name": doc.name}

        elif action == "feed":
            since = dt_or_none(fd.get("since")) or str(frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-30))[:19]
            nowv = str(frappe.utils.now_datetime())[:19]
            team = 1 if (is_mgr and fd.get("team") and not fd.get("agent")) else 0
            owners = [u.get("name") for u in cc_users()] if team else [agent]
            names = {}
            if team:
                for u in cc_users():
                    names[u.get("name")] = (u.get("full_name") or "").split(" ")[0]
            MAP = {"booked": ["📅", "New appointment"], "visited": ["🚶", "Visited"], "visited booked": ["🎉", "Booked"],
                   "visited not booked": ["🙁", "Visited · not booked"], "not visited": ["⌛", "No-show"], "cancelled": ["✖️", "Appointment cancelled"]}
            items = []
            # fast: leads of these owners changed since last check that carry an appointment status (one item per lead + status)
            rows = frappe.get_all("Lead", filters=[["lead_owner", "in", owners], ["modified", ">", since],
                                                   ["custom_appointment_status", "in", ["Booked", "Visited", "Visited Booked", "Visited Not Booked", "Not Visited", "Cancelled"]]],
                                  fields=["name", "lead_name", "lead_owner", "lead_assign_to_branch", "custom_appointment_status", "custom_appointment_date_and_time", "modified"],
                                  order_by="modified asc", limit_page_length=300)
            for L in rows:
                ev = MAP.get(str(L.get("custom_appointment_status") or "").strip().lower())
                if not ev:
                    continue
                who = (" · " + names.get(L.get("lead_owner"))) if team and names.get(L.get("lead_owner")) else ""
                ap = str(L.get("custom_appointment_date_and_time") or "")[:16]
                items.append({"id": L.get("name") + ":" + str(L.get("custom_appointment_status")), "icon": ev[0], "title": ev[1] + " · " + (L.get("lead_name") or ""),
                              "body": (L.get("lead_assign_to_branch") or "") + (" · " + ap if ap else "") + who, "at": str(L.get("modified"))[:19]})
            # client paid: Payment Entries (received) from patients created from these agents' leads
            pays = frappe.get_all("Payment Entry", filters=[["docstatus", "=", 1], ["payment_type", "=", "Receive"], ["creation", ">", since]],
                                  fields=["name", "party", "party_name", "paid_amount", "creation", "branch"], order_by="creation asc", limit_page_length=300)
            parties = list(set([p.get("party") for p in pays if p.get("party")]))
            pl = {}
            for i in range(0, len(parties), 300):
                for x in frappe.get_all("Patient", filters=[["customer", "in", parties[i:i + 300]], ["custom_lead", "is", "set"]], fields=["customer", "custom_lead"], limit_page_length=600):
                    pl[x.get("customer")] = x.get("custom_lead")
            po = {}
            ln = list(set(pl.values()))
            for i in range(0, len(ln), 300):
                for x in frappe.get_all("Lead", filters=[["name", "in", ln[i:i + 300]]], fields=["name", "lead_owner"], limit_page_length=600):
                    po[x.get("name")] = x.get("lead_owner")
            for p in pays:
                o = po.get(pl.get(p.get("party")))
                if not o or o not in owners or not float(p.get("paid_amount") or 0):
                    continue
                who = (" · " + names.get(o)) if team and names.get(o) else ""
                items.append({"id": "pay:" + p.get("name"), "icon": "₹", "title": "Client paid · " + (p.get("party_name") or ""),
                              "body": "₹" + str(int(float(p.get("paid_amount") or 0))) + ((" · " + p.get("branch")) if p.get("branch") else "") + who, "at": str(p.get("creation"))[:19]})
            items.sort(key=lambda z: z.get("at"), reverse=True)
            frappe.response["message"] = {"items": items[:60], "now": nowv}

        else:
            frappe.throw("Unknown action")

    key = _mobile_cache_key(action, agent, is_mgr, fd, today)
    if key is None:
        _dispatch()
        return

    def compute():
        _dispatch()
        return frappe.response.get("message")

    frappe.response["message"] = read_cache.cached_read(*key, compute)
