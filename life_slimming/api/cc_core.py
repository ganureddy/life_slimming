"""Native V26-4 lead journey and distribution API, with owner-scoped reads."""
import json
import re
import frappe
from life_slimming.api._runtime import script_endpoint
from life_slimming.portal_access import require_module
from life_slimming.cc_business_rules import (PERMISSION_EDITORS, DEFAULT_MOVERS as POLICY_MOVERS, MOVER_ROLES, booked, has_business_result, paid_evidence, credit_for_events)


@script_endpoint(allow_guest=False)
def run(**kwargs):
    # LIFE CC CORE (V26-4) — Server Script, type API, method: life_cc_core
    # One brain for the CC Dashboard V26-4, CC Reports V26-4 and the mobile test page.
    # Does NOT replace cc_update_lead. Failed calls are saved here and NEVER touch
    # Lead.status / custom_cc_stage / custom_cc_sub_status / appointment fields.

    FAILED = ["No Response", "Not Response", "Not Reachable", "Switch OFF", "TNA",
              "Call Disconnected", "Appointment no response", "Busy", "Not Lifted"]
    STATUS_MAP = {"No Response": "Not Response", "Not Reachable": "Not Reachable", "Switch OFF": "Switch OFF", "TNA": "TNA",
                  "Call Disconnected": "Call Disconnected", "Appointment no response": "Appointment no response"}
    STATUS_FAILED = ["Not Response", "Not Reachable", "Switch OFF", "TNA", "Call Disconnected", "Appointment no response"]
    EDITORS = PERMISSION_EDITORS
    DEFAULT_MOVERS = POLICY_MOVERS
    TRACK = "LIFE CC Lead Track"
    LOG = "CC Lead Activity Log"

    fd = frappe.form_dict
    action = (fd.get("action") or "").strip()
    user = frappe.session.user
    now = frappe.utils.now_datetime()


    def jl(v):
        if not v:
            return []
        if isinstance(v, list):
            return v
        try:
            x = json.loads(v)
            return x if isinstance(x, list) else [x]
        except Exception:
            return [s.strip() for s in str(v).split(",") if s.strip()]


    def roles_of(u):
        return [r.role for r in frappe.get_all("Has Role", filters={"parent": u, "parenttype": "User"}, fields=["role"])]


    def is_tl(u):
        rs = roles_of(u)
        return bool(MOVER_ROLES.intersection(rs)) or frappe.db.get_value("User", u, "custom_portal_role") == "MD"


    def movers():
        rows = frappe.get_all("LIFE CC Assign Rule", filters={"rule_type": "Permissions", "enabled": 1}, fields=["allowed_users"], limit_page_length=1)
        if rows and rows[0].allowed_users:
            return list(set(jl(rows[0].allowed_users)) | set(EDITORS))
        return list(set(DEFAULT_MOVERS) | set(EDITORS))


    def can_move(u):
        return (u in movers()) or is_tl(u)


    def emp_of(u):
        return frappe.db.get_value("Employee", {"user_id": u, "status": "Active"}, "name")


    def dt(v):
        return frappe.utils.get_datetime(v) if v else None


    def get_track(lead):
        if frappe.db.exists(TRACK, lead):
            return frappe.get_doc(TRACK, lead)
        d = frappe.new_doc(TRACK)
        d.lead = lead
        return d


    def appt_counts(leads):
        out = {}
        for l in leads:
            out[l] = {"booked": 0, "missed": 0, "visited": 0, "last_visit": None, "last_visit_result": ""}
        if not leads:
            return out
        rows = frappe.get_all(LOG, filters={"lead": ["in", leads], "change_json": ["like", "%custom_appointment_status%"]},
                              fields=["lead", "change_json", "event_time"], order_by="event_time asc", limit_page_length=20000)
        for r in rows:
            try:
                ch = json.loads(r.change_json or "[]")
            except Exception:
                ch = []
            for c in ch:
                if c.get("field") != "custom_appointment_status":
                    continue
                nv = c.get("new") or ""
                o = out[r.lead]
                if nv == "Booked":
                    o["booked"] = o["booked"] + 1
                elif nv == "Not Visited":
                    o["missed"] = o["missed"] + 1
                elif nv in ["Visited", "Visited Booked", "Visited Not Booked"]:
                    o["visited"] = o["visited"] + 1
                    o["last_visit"] = str(r.event_time)
                    o["last_visit_result"] = nv
        return out


    def paid_map(names):
        return paid_evidence(names)

    def credit_agents(joined):
        if not joined:
            return {}
        rows = frappe.get_all(LOG, filters={"lead": ["in", list(joined)], "action": "appointment"},
            fields=["lead", "erp_user", "agent", "event_time"], order_by="event_time asc", limit_page_length=0)
        return credit_for_events(rows, joined, emp_of)

    def milestone_of(l, c):
        ap = l.get("custom_appointment_status") or ""
        st = l.get("status") or ""
        sub = l.get("custom_cc_sub_status") or ""
        appt_dt = dt(l.get("custom_appointment_date_and_time"))
        if c.get("paid") and booked(l, c):
            return "Joined Client"
        if ap == "Visited Booked" or sub == "Walked In & Booked" or st in ["Converted", "Joined"]:
            return "Booked - Payment Pending"
        if ap in ["Visited", "Visited Not Booked"] or c["visited"] > 0:
            last = c.get("last_visit_result") or ap
            return "Visited - Not Booked" if last == "Visited Not Booked" or sub == "Walked In: Not Booked" else "Visited"
        # A failed outbound call is not a visit outcome.  Keep a confirmed
        # booking in its booked state—even once its scheduled time has passed—
        # until the branch/agent explicitly records "Not Visited".  Otherwise
        # a simple No Response call incorrectly turns the UI into a no-show.
        if ap == "Booked":
            return "Appointment Booked"
        if ap == "Not Visited" or c["missed"] > 0:
            return "Appointment Missed"
        if sub in ["Very Positive", "Price Negotiation", "Call & Confirm", "Callback: Scheduled", "Out Station", "Get Back"]:
            return "Interested"
        if (l.get("custom_call_count") or 0) > 0:
            return "Contacted"
        return "New"


    def next_action_of(l, t, ms):
        st = l.get("status") or ""
        sub = l.get("custom_cc_sub_status") or ""
        stage = l.get("custom_cc_stage") or ""
        appt_dt = dt(l.get("custom_appointment_date_and_time"))
        fu = l.get("custom_next_followup_date")
        if st == "Do Not Contact" or sub == "Do Not Contact":
            return ["Do not contact", None]
        if ms == "Joined Client":
            return ["Feedback call only", str(fu) if fu else None]
        if stage in ["LOST", "INVALID"]:
            return ["Closed (" + stage + ")", None]
        if t and t.get("next_action") and t.get("next_action_due") and dt(t.get("next_action_due")) >= now:
            return [t.get("next_action"), str(t.get("next_action_due"))]
        if ms == "Appointment Booked":
            return ["Confirm appointment", str(appt_dt)]
        if t and (t.get("unreachable_streak") or 0) >= 3:
            return ["TL review - unreachable " + str(t.get("unreachable_streak")) + "x", str(fu) if fu else None]
        if ms == "Appointment Missed":
            return ["Rebook appointment", str(fu) if fu else None]
        if ms == "Visited - Not Booked":
            return ["Convert follow-up", str(fu) if fu else None]
        if ms == "Booked - Payment Pending":
            return ["Payment follow-up (branch)", str(fu) if fu else None]
        if fu:
            return ["Call back", str(fu)]
        return ["Call now", None]


    def protected_of(l, ms, evidence=None):
        appt_dt = dt(l.get("custom_appointment_date_and_time"))
        if (l.get("status") or "") == "Do Not Contact":
            return "DNC"
        if (l.get("custom_cc_stage") or "") in ["LOST", "INVALID"]:
            return l.get("custom_cc_stage")
        if ms == "Appointment Booked" or (appt_dt and appt_dt >= now and (l.get("custom_appointment_status") or "") == "Booked"):
            return "Upcoming appointment"
        if ms == "Joined Client":
            return "Joined client - feedback only"
        if ms == "Booked - Payment Pending":
            return "Booked - payment pending"
        if (evidence or {}).get("paid"):
            return "Paid client - protected"
        return ""


    def existing_lead_fields(fields):
        """Skip optional Lead fields whose database columns are not installed yet."""
        try:
            columns = frappe.db.get_table_columns("Lead")
            if isinstance(columns, (list, tuple, set)):
                return [field for field in fields if field in columns]
        except Exception:
            pass
        return fields


    LEAD_F = existing_lead_fields(["name", "lead_name", "first_name", "lead_owner", "status", "custom_cc_stage", "custom_cc_sub_status",
              "custom_appointment_status", "custom_visit_status", "custom_appointment_date_and_time",
              "custom_next_followup_date", "custom_call_count", "custom_last_call_time", "source",
              "custom_convox_disposition", "custom_convox_last_call_time", "custom_cc_appointment_agent", "creation", "modified", "lead_assign_to_branch"])


    def summaries(names):
        names = [n for n in names if n][:500]
        if not names:
            return {}
        leads = frappe.get_all("Lead", filters={"name": ["in", names]}, fields=LEAD_F, limit_page_length=500)
        tr = {}
        for t in frappe.get_all(TRACK, filters={"lead": ["in", names]}, fields=["*"], limit_page_length=500):
            tr[t.lead] = t
        cnt = appt_counts(names)
        pm = paid_map(names)
        for k in pm:
            if k in cnt:
                cnt[k]["paid"] = pm[k]["paid"]
                cnt[k]["joined_on"] = pm[k]["joined_on"]
                cnt[k]["has_bill"] = pm[k].get("has_bill", False)
        ca = credit_agents(pm)
        out = {}
        for l in leads:
            c = cnt.get(l.name) or {"booked": 0, "missed": 0, "visited": 0}
            if c["visited"] > c["booked"]:
                c["booked"] = c["visited"]
            t = tr.get(l.name) or {}
            ms = milestone_of(l, c)
            na = next_action_of(l, t, ms)
            last_res = t.get("last_call_result") if t else ""
            last_at = t.get("last_call_at") if t else None
            if not last_res and l.get("custom_convox_disposition"):
                last_res = l.get("custom_convox_disposition")
                last_at = l.get("custom_convox_last_call_time")
            if not last_at:
                last_at = l.get("custom_last_call_time")
            out[l.name] = {
                "milestone": ms, "booked": c["booked"], "missed": c["missed"], "visited": c["visited"],
                "last_visit": c.get("last_visit"),
                "last_call_result": last_res or "", "last_call_at": str(last_at) if last_at else "",
                "unreachable_streak": (t.get("unreachable_streak") if t else 0) or 0,
                "next_action": na[0], "next_action_due": na[1],
                "protected": protected_of(l, ms, pm.get(l.name)),
                # Keep an explicitly verified/credited agent from the track first,
                # then use the event-derived attribution and the appointment agent
                # fallback used by the live LIFE CC Server Script.
                "converting_agent": ((t.get("converting_agent") if t else None) or ca.get(l.name) or
                                     (l.get("custom_cc_appointment_agent") if c.get("paid") else None)),
                "credit_provisional": (pm.get(l.name) or {}).get("credit_provisional", False),
                "joined_on": c.get("joined_on"), "paid": c.get("paid") or 0,
                "owner": l.lead_owner, "sub_status": l.custom_cc_sub_status, "stage": l.custom_cc_stage,
                "appt_status": l.custom_appointment_status, "appt_at": str(l.custom_appointment_date_and_time or ""),
                "branch": l.get("lead_assign_to_branch") or "", "branch_code": BR_CODE.get(l.get("lead_assign_to_branch") or "", (l.get("lead_assign_to_branch") or "")[:3].upper()),
                "modified": str(l.modified)
            }
        return out


    def save_track(lead, vals):
        t = get_track(lead)
        for k in vals:
            t.set(k, vals[k])
        s = summaries([lead]).get(lead) or {}
        t.milestone = s.get("milestone")
        t.booked_count = s.get("booked") or 0
        t.missed_count = s.get("missed") or 0
        t.visited_count = s.get("visited") or 0
        if s.get("last_visit"):
            t.last_visit_on = s.get("last_visit")
        if t.is_new():
            t.insert(ignore_permissions=True)
        else:
            t.save(ignore_permissions=True)
        return t


    def retry_time(streak):
        if streak <= 1:
            return frappe.utils.add_to_date(now, hours=2)
        if streak == 2:
            return frappe.utils.add_to_date(now, hours=4)
        d = frappe.utils.add_days(frappe.utils.getdate(now), 1 if streak == 3 else 2)
        return frappe.utils.get_datetime(str(d) + " 11:00:00")


    def digits10(v):
        x = "".join([ch for ch in str(v or "") if ch.isdigit()])
        return x[-10:] if len(x) >= 10 else x


    def lead_numbers(d):
        out = []
        for v in [d.get("mobile_no"), d.get("phone"), d.get("whatsapp_no")] + [r.phone for r in (d.get("custom_contact_numbers_") or [])]:
            n = digits10(v)
            if len(n) == 10 and n not in out:
                out.append(n)
        return out


    BR_CODE = {"Banjara Hills": "BH", "Kukatpally": "KP", "Vizag": "VZ", "Vijayawada": "VW", "Dilsukhnagar": "DN", "Himayathnagar": "HN",
               "SR Nagar": "SN", "Chandanagar": "CN", "Gachibowli": "GB", "Madhapur": "MP", "Nellore": "NLR", "Head Office": "HO", "Ho CC": "CC", "Testing Branch": "TB"}
    NAME_CACHE = {}


    def short_name(full):
        parts = [x for x in str(full or "").replace(".", " ").split() if x]
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0].title()
        first = parts[0] if len(parts[0]) > 2 else (parts[1] if len(parts) > 1 else parts[0])
        rest = [x for x in parts if x != first]
        return first.title() + (" " + rest[0][0].upper() + "." if rest else "")


    def person(x):
        # login email / user / employee id -> short display name; never show an email
        x = str(x or "").strip()
        if not x:
            return ""
        if x in NAME_CACHE:
            return NAME_CACHE[x]
        full = ""
        if x.startswith("HR-EMP"):
            full = frappe.db.get_value("Employee", x, "employee_name") or ""
        else:
            full = frappe.db.get_value("Employee", {"user_id": x}, "employee_name") or frappe.db.get_value("User", x, "full_name") or ""
        if not full and "@" in x:
            full = x.split("@")[0]
        NAME_CACHE[x] = short_name(full) or x
        return NAME_CACHE[x]


    RANK_METHODS = {
        "conversion": "Best conversion (booked ÷ walk-ins)",
        "bookings": "Most bookings",
        "walkins": "Best quality walk-ins (show-up %)",
        "smart": "Lightest load (fewest open leads)",
        "free_leads": "Free hands — fewest leads in hand",
        "free_fu": "Free hands — fewest follow-ups due",
        "equal": "Equal turns (round robin)"
    }


    def agent_rank(agents, method, days=30):
        # performance of each agent over the last N days, by appointment date (same rules as reports)
        since = str(frappe.utils.add_days(frappe.utils.getdate(now), -days)) + " 00:00:00"
        VIS = ["Visited", "Visited Booked", "Visited Not Booked"]
        out = {}
        for a in agents:
            out[a] = {"agent": a, "name": person(a), "appts": 0, "walkins": 0, "booked": 0, "open": 0}
        if not agents:
            return []
        for r in frappe.get_all("Lead", filters={"lead_owner": ["in", agents], "custom_appointment_date_and_time": [">=", since]},
                                fields=["lead_owner", "custom_appointment_status"], limit_page_length=20000):
            o = out.get(r.lead_owner)
            if not o:
                continue
            o["appts"] = o["appts"] + 1
            if (r.custom_appointment_status or "") in VIS:
                o["walkins"] = o["walkins"] + 1
            if (r.custom_appointment_status or "") == "Visited Booked":
                o["booked"] = o["booked"] + 1
        for r in frappe.get_all("Lead", filters={"lead_owner": ["in", agents], "custom_cc_stage": ["in", ["UNTOUCHED", "FOLLOW-UP", "PIPELINE"]]},
                                fields=["lead_owner", "count(name) as n"], group_by="lead_owner", limit_page_length=200):
            if r.lead_owner in out:
                out[r.lead_owner]["open"] = r.n
        wl = workload(agents)
        tds = str(frappe.utils.getdate(now))
        fu_today = {}
        for r in frappe.get_all("Lead", filters={"lead_owner": ["in", agents], "custom_cc_stage": ["in", ["FOLLOW-UP", "PIPELINE"]],
                                                 "custom_next_followup_date": ["<=", tds + " 23:59:59"]},
                                fields=["lead_owner", "count(name) as n"], group_by="lead_owner", limit_page_length=200):
            fu_today[r.lead_owner] = r.n
        rows = list(out.values())
        for o in rows:
            w = wl.get(o["agent"]) or {}
            o["open_recent"] = w.get("open_recent", 0)
            o["overdue"] = w.get("overdue", 0)
            o["over_cap"] = w.get("over_cap", False)
            o["fu_due"] = fu_today.get(o["agent"], 0)
        for o in rows:
            o["conv"] = round(o["booked"] * 100.0 / o["walkins"], 1) if o["walkins"] else 0
            o["showup"] = round(o["walkins"] * 100.0 / o["appts"], 1) if o["appts"] else 0
            if method == "conversion":
                o["score"] = o["conv"] + o["booked"] * 0.5
            elif method == "bookings":
                o["score"] = o["booked"] * 10 + o["conv"] * 0.1
            elif method == "walkins":
                o["score"] = o["showup"] + o["walkins"] * 0.5
            elif method == "smart":
                o["score"] = -o["open"]
            elif method == "free_leads":
                o["score"] = -o["open_recent"]
            elif method == "free_fu":
                o["score"] = -o["fu_due"]
            else:
                o["score"] = 0
        rows = sorted(rows, key=lambda x: -x["score"])
        i = 1
        for o in rows:
            o["rank"] = i
            i = i + 1
        return rows


    def pick_agent(rows, given):
        # weighted turns: a better-ranked agent gets more leads, but nobody gets everything
        best = None
        bv = None
        lo = min([o.get("score", 0) for o in rows] or [0])
        for o in rows:
            w = (o.get("score", 0) - lo) + 1
            v = w / (given.get(o["agent"], 0) + 1.0)
            if bv is None or v > bv:
                best, bv = o["agent"], v
        return best


    DEFAULT_SETTINGS = {"cap_on": 1, "cap_overdue": 150, "cap_open": 1000, "open_days": 60, "overdue_days": 30, "dormant_days": 90,
                        "seniors": ["lifebcmanager@gmail.com", "lifescc001@gmail.com", "lifescc13@gmail.com"]}


    def cc_settings():
        out = dict(DEFAULT_SETTINGS)
        row = frappe.db.get_value("LIFE CC Assign Rule", {"rule_type": "Settings"}, ["last_preview"], as_dict=True)
        if row and row.last_preview:
            try:
                out.update(json.loads(row.last_preview))
            except Exception:
                pass
        return out


    def workload(agents):
        st = cc_settings()
        since = str(frappe.utils.add_days(frappe.utils.getdate(now), -int(st.get("open_days") or 60))) + " 00:00:00"
        osince = str(frappe.utils.add_days(frappe.utils.getdate(now), -int(st.get("overdue_days") or 30))) + " 00:00:00"
        out = {}
        for a in agents:
            out[a] = {"open_recent": 0, "overdue": 0}
        if not agents:
            return out
        for r in frappe.get_all("Lead", filters={"lead_owner": ["in", agents], "custom_cc_stage": ["in", ["UNTOUCHED", "FOLLOW-UP", "PIPELINE"]], "creation": [">=", since]},
                                fields=["lead_owner", "count(name) as n"], group_by="lead_owner", limit_page_length=200):
            out[r.lead_owner]["open_recent"] = r.n
        for r in frappe.get_all("Lead", filters={"lead_owner": ["in", agents], "custom_cc_stage": ["in", ["FOLLOW-UP", "PIPELINE"]], "custom_next_followup_date": ["between", [osince, now]]},
                                fields=["lead_owner", "count(name) as n"], group_by="lead_owner", limit_page_length=200):
            out[r.lead_owner]["overdue"] = r.n
        for a in out:
            o = out[a]
            o["over_cap"] = bool(st.get("cap_on")) and (o["overdue"] > int(st.get("cap_overdue") or 150) or o["open_recent"] > int(st.get("cap_open") or 1000))
        return out


    def owner_check(lead_doc):
        if lead_doc.lead_owner != user and not can_move(user):
            frappe.throw("This lead belongs to another agent.")


    # Authorize every action before using permission-bypassing aggregate queries.
    try:
        require_module("leads")
    except frappe.PermissionError:
        if action not in {"report", "cal"}:
            raise
        require_module("ccvisit")
    if action == "report":
        require_module("ccvisit", tab="journey")
    management = can_move(user)
    manager_actions = {"rank", "dist_preview", "dist_move", "dist_undo", "agents", "settings_save", "bulk_meta", "bulk_check", "bulk_create", "rules", "rule_save", "credit", "agent_stats"}
    if action in manager_actions and not management:
        frappe.throw("Lead distribution requires manager access.", frappe.PermissionError)
    if action in {"header", "timeline", "attempt", "connected", "match", "match_verify", "add_number", "save_connected"}:
        access_doc = frappe.get_doc("Lead", fd.get("lead"))
        owner_check(access_doc)
    if action == "summary" and not management:
        for lead_id in jl(fd.get("leads"))[:500]:
            owner_check(frappe.get_doc("Lead", lead_id))
    if action in {"report", "cal"} and not management:
        fd["owners"] = json.dumps([user])

    saved_result = None
    if action == "save_connected":
        # Save the worksheet and journey state in one request/transaction.
        from life_slimming.api.server_scripts.cc_update_lead import run as update_lead
        current = summaries([fd.get("lead")]).get(fd.get("lead")) or {}
        if current.get("milestone") == "Joined Client":
            values = fd.get("values") or {}
            values = json.loads(values) if isinstance(values, str) else values
            existing = frappe.get_doc("Lead", fd.get("lead"))
            immutable = {"status", "custom_cc_stage", "custom_cc_sub_status", "custom_appointment_date_and_time", "custom_appointment_status", "lead_owner"}
            if any(key in values and str(values[key] or '') != str(existing.get(key) or '') for key in immutable):
                frappe.throw("Joined clients accept feedback only; their business outcome and owner are protected.")
        saved_result = update_lead(lead=fd.get("lead"), values=fd.get("values"),
            expected_modified=fd.get("expected_modified"), attempt=fd.get("attempt"))
        if saved_result is None:
            saved_result = frappe.response.get("message") or {}
        if saved_result.get("ok") != 1:
            return saved_result
        action = "connected"

    res = {"ok": True}

    if action == "summary":
        res["leads"] = summaries(jl(fd.get("leads")))

    elif action == "timeline":
        lead = fd.get("lead")
        frappe.get_doc("Lead", lead).check_permission("read")
        start = max(0, min(4900, int(fd.get("start") or 0)))
        window = start + 101
        ev = []
        for r in frappe.get_all(LOG, filters={"lead": lead}, fields=["event_time", "action", "old_status", "new_status", "connected", "next_followup", "erp_user", "change_json"], order_by="event_time desc", limit_page_length=window):
            fr, to = r.old_status, r.new_status
            if r.action in ["tl move", "auto shuffle", "reassign", "assign"]:
                fr, to = person(fr), person(to)
            ev.append({"at": str(r.event_time), "kind": r.action, "from": fr, "to": to, "connected": r.connected,
                       "next": str(r.next_followup or ""), "by": person(r.erp_user)})
        for r in frappe.get_all("CC Followup Event", filters={"lead": lead}, fields=["due_at", "result", "closed_at", "agent"], order_by="due_at desc", limit_page_length=window):
            ev.append({"at": str(r.closed_at or r.due_at), "kind": "follow-up " + (r.result or ""), "due": str(r.due_at), "by": person(r.agent)})
        if frappe.db.exists("DocType", "LIFE Mobile Call Log"):
            for r in frappe.get_all("LIFE Mobile Call Log", filters={"lead": lead}, fields=["creation", "call_status", "talk_seconds", "agent", "disposition"], order_by="creation desc", limit_page_length=window):
                ev.append({"at": str(r.creation), "kind": "mobile call", "to": r.call_status or r.disposition, "talk": r.talk_seconds, "by": person(r.agent)})
        if frappe.db.exists("DocType", "ConVox Call Event"):
            for r in frappe.get_all("ConVox Call Event", filters={"crm_lead":lead,"event_type":"Call Status"}, fields=["received_on","call_status","call_duration","agent_id"], order_by="received_on desc", limit_page_length=window):
                caller = frappe.db.get_value("User", {"custom_convox_agent_id":r.agent_id}, "name")
                ev.append({"at":str(r.received_on),"kind":"ConVox call","to":r.call_status,"talk":r.call_duration,"by":person(caller) if caller else r.agent_id})
        ev.sort(key=lambda e: e.get("at") or "", reverse=True)
        res["events"] = ev[start:start+100]
        res["more"] = len(ev)>start+100 and start<4900
        res["capped"] = len(ev)>5000
        res["start"] = start
        res["summary"] = summaries([lead]).get(lead)

    elif action == "attempt":
        lead = fd.get("lead")
        reason = (fd.get("reason") or "").strip()
        if reason not in FAILED:
            frappe.throw("Not a failed-call reason: " + reason)
        d = frappe.get_doc("Lead", lead)
        owner_check(d)
        exp = fd.get("expected_modified")
        if exp and str(d.modified) != str(exp):
            frappe.throw("This lead was changed by someone else. Refresh and try again.")
        t = get_track(lead)
        streak = int(t.get("unreachable_streak") or 0) + 1
        nf = fd.get("next_followup")
        appt_dt = dt(d.get("custom_appointment_date_and_time"))
        if not nf:
            nf = retry_time(streak)
            if appt_dt and appt_dt > now and (d.get("custom_appointment_status") or "") == "Booked":
                nf = max(now, min(dt(nf), frappe.utils.add_to_date(appt_dt, hours=-2)))
        d.custom_call_count = int(d.get("custom_call_count") or 0) + 1
        d.custom_last_call_time = now
        d.custom_next_followup_date = nf
        note = (fd.get("note") or "").strip()
        if fd.get("remarks") is not None and str(fd.get("remarks")).strip():
            d.custom_remarks = fd.get("remarks")
        elif note:
            d.custom_remarks = ((d.get("custom_remarks") or "") + "\n[" + str(now)[:16] + " " + reason + "] " + note).strip()
        # Fresh lead with no business outcome yet: keep old reports working (stage FOLLOW-UP,
        # sub-status = failed reason, status mapped). A lead with ANY real outcome is never touched.
        cur_sub = d.get("custom_cc_sub_status") or ""
        appt_locked = (d.get("custom_appointment_status") or "") in ["Booked", "Visited", "Visited Booked", "Visited Not Booked", "Not Visited"]
        evidence = paid_map([lead]).get(lead) or {}
        if cur_sub in ["", "Lead"] + FAILED and not appt_locked and not has_business_result(d, evidence.get("paid"), evidence.get("has_bill")):
            d.custom_cc_sub_status = "No Response" if reason in ["Not Response", "Busy", "Not Lifted"] else reason
            if (d.get("custom_cc_stage") or "UNTOUCHED") == "UNTOUCHED":
                d.custom_cc_stage = "FOLLOW-UP"
            if (d.get("status") or "") in ["", "Lead", "Open"] + STATUS_FAILED:
                d.status = STATUS_MAP.get(d.custom_cc_sub_status) or d.status
        # Legacy bookings stored values such as "45 Minutes" on a Lead Select
        # whose current options may only contain "30 Minutes".  This failed
        # call path saves the Lead directly, so clear that obsolete duplicate
        # before Frappe validates the document.  The Appointment remains the
        # source of truth for the booked duration.
        duration_field = frappe.get_meta("Lead").get_field("custom_appointment_duration")
        allowed_durations = {
            value.strip() for value in str(duration_field.options or "").splitlines()
            if value.strip()
        } if duration_field else set()
        if allowed_durations and d.get("custom_appointment_duration") and d.get("custom_appointment_duration") not in allowed_durations:
            d.custom_appointment_duration = ""
        d.save(ignore_permissions=True)
        t = save_track(lead, {"last_call_result": reason, "last_call_at": now, "unreachable_streak": streak})
        res.update({"lead": lead, "streak": streak, "next_followup": str(nf), "modified": str(d.modified),
                    "summary": summaries([lead]).get(lead), "tl_review": streak >= 3})

    elif action == "connected":
        lead = fd.get("lead")
        d = frappe.get_doc("Lead", lead)
        owner_check(d)
        vals = {"last_call_result": "Connected", "last_call_at": now, "unreachable_streak": 0, "last_connected_at": now}
        if fd.get("next_action"):
            vals["next_action"] = fd.get("next_action")
            vals["next_action_due"] = fd.get("next_action_due") or d.get("custom_next_followup_date")
        save_track(lead, vals)
        res["summary"] = summaries([lead]).get(lead)

    elif action == "credit":
        # called after a sale: the agent who booked the visit that became the sale gets 100%
        lead = fd.get("lead")
        d = frappe.get_doc("Lead", lead)
        if not can_move(user):
            frappe.throw("Not allowed")
        save_track(lead, {"converting_agent": fd.get("agent") or emp_of(d.lead_owner)})
        res["summary"] = summaries([lead]).get(lead)

    elif action == "rank":
        ags = jl(fd.get("agents"))
        if not ags:
            sset = frappe.get_doc("Lead Assignment Settings", "Lead Assignment Settings")
            ags = [c.get("agent") for c in (sset.get("agent_config") or []) if c.get("agent")]
        res.update({"rows": agent_rank(ags, fd.get("method") or "conversion", int(fd.get("days") or 30)), "methods": RANK_METHODS})

    elif action == "perm":
        mv = movers()
        res["me"] = person(user)
        res["me_full"] = frappe.db.get_value("Employee", {"user_id": user}, "employee_name") or frappe.db.get_value("User", user, "full_name") or ""
        res.update({"can_move": can_move(user), "can_edit_perm": user in EDITORS, "movers": mv, "is_tl": is_tl(user),
                    "names": dict([(u, person(u)) for u in mv])})

    elif action == "dist_preview":
        if not can_move(user):
            frappe.throw("Not allowed")
        f = {}
        owners = jl(fd.get("owners"))
        if owners:
            f["lead_owner"] = ["in", owners]
        orf = None
        for key, field in [["sub_statuses", "custom_cc_sub_status"], ["stages", "custom_cc_stage"], ["sources", "source"], ["appt_statuses", "custom_appointment_status"]]:
            v = jl(fd.get(key))
            if v:
                f[field] = ["in", v]
        subs = jl(fd.get("sub_statuses"))
        if "No Response" in subs or "Not Response" in subs:
            # one spelling for agents: "No Response" (sub-status) = "Not Response" (status)
            f.pop("custom_cc_sub_status", None)
            orf = {"custom_cc_sub_status": ["in", subs + ["No Response"]], "status": ["in", ["Not Response"]]}
        if fd.get("dormant") in ["1", 1, True, "true"]:
            dd = int(cc_settings().get("dormant_days") or 90)
            f["modified"] = ["<", str(frappe.utils.add_days(frappe.utils.getdate(now), -dd)) + " 00:00:00"]
            f["custom_cc_stage"] = ["in", ["UNTOUCHED", "FOLLOW-UP", "PIPELINE"]]
        if fd.get("from_date") and fd.get("to_date"):
            f["creation"] = ["between", [fd.get("from_date"), fd.get("to_date") + " 23:59:59"]]
        if fd.get("overdue_only") in ["1", 1, True, "true"]:
            f["custom_next_followup_date"] = ["<", now]
        rows = frappe.get_all("Lead", filters=f, or_filters=orf, fields=["name"], order_by="creation desc", limit_page_length=int(fd.get("limit") or 300))
        names = [r.name for r in rows]
        sm = summaries(names)
        keep_prot = fd.get("include_protected") in ["1", 1, True, "true"]
        ms_f = jl(fd.get("milestones"))
        lc_f = jl(fd.get("last_results"))
        items = []
        for n in names:
            s = sm.get(n)
            if not s:
                continue
            if s["protected"] and not keep_prot:
                continue
            if ms_f and s["milestone"] not in ms_f:
                continue
            if lc_f and s["last_call_result"] not in lc_f:
                continue
            s["lead"] = n
            items.append(s)
        res["items"] = items
        res["count"] = len(items)

    elif action == "dist_move":
        if not can_move(user):
            frappe.throw("Not allowed to move leads")
        leads = list(dict.fromkeys(jl(fd.get("leads"))))[:500]
        to = jl(fd.get("to_agents"))
        configured = frappe.get_doc("Lead Assignment Settings", "Lead Assignment Settings")
        valid_agents = {c.get("agent") for c in configured.get("agent_config") or [] if c.get("agent")}
        if any(a not in valid_agents for a in to):
            frappe.throw("Choose configured CC agents only.")
        if not leads or not to:
            frappe.throw("Select leads and at least one agent")
        capacity = workload(to)
        settings = cc_settings()
        load = {a: frappe.db.count("Lead", {"lead_owner": a, "custom_cc_stage": ["in", ["UNTOUCHED", "FOLLOW-UP", "PIPELINE"]]}) for a in to}
        projected = dict.fromkeys(to, 0)
        simulation = dict(load)
        method = fd.get("method") or "equal"
        projection_rank = agent_rank(to, method) if method in ["conversion", "bookings", "walkins", "free_leads", "free_fu"] else []
        for index in range(len(leads)):
            target = min(to, key=lambda a:simulation[a]) if method == "smart" else pick_agent(projection_rank, projected) if projection_rank else to[index % len(to)]
            projected[target] += 1
            simulation[target] += 1
        over = [a for a in to if (capacity.get(a) or {}).get("over_cap") or settings.get("cap_on") and (capacity.get(a) or {}).get("open_recent",0)+projected[a] > int(settings.get("cap_open") or 1000)]
        if over and fd.get("accept_capacity") not in [1, "1", True]:
            return {"ok": True, "capacity_warning": over, "capacity": capacity, "projected": projected, "count": 0}
        batch = "TL-" + str(now)[:19].replace("-", "").replace(":", "").replace(" ", "")
        moved = []
        ranked = []
        given = {}
        i = 0
        for n in leads:
            d = frappe.get_doc("Lead", n)
            if summaries([n])[n].get("protected"):
                continue
            meth = fd.get("method") or "equal"
            if meth == "smart":
                a = sorted(to, key=lambda x: load[x])[0]
            elif meth in ["conversion", "bookings", "walkins", "free_leads", "free_fu"]:
                if not ranked:
                    ranked.extend(agent_rank(to, meth))
                a = pick_agent(ranked, given)
            else:
                a = to[i % len(to)]
            given[a] = given.get(a, 0) + 1
            i = i + 1
            if d.lead_owner == a:
                continue
            old = d.lead_owner
            d.lead_owner = a
            d.custom_assignment_method = "Manual"
            d.custom_assignment_rule = batch + " by " + user
            if fd.get("clear_followup") in ["1", 1, True, "true"]:
                d.custom_next_followup_date = None
            pass
            d.save(ignore_permissions=True)
            load[a] = load.get(a, 0) + 1
            frappe.get_doc({"doctype": LOG, "lead": n, "erp_user": user, "event_time": now, "action": "tl move",
                            "old_status": old or "", "new_status": a,
                            "change_json": json.dumps({"batch": batch, "from": old, "to": a, "note": fd.get("note") or ""})}).insert(ignore_permissions=True)
            save_track(n, {"shuffle_count": 0})
            moved.append({"lead": n, "from": old, "to": a})
        res.update({"batch": batch, "moved": moved, "count": len(moved)})

    elif action == "dist_undo":
        if not can_move(user):
            frappe.throw("Not allowed")
        batch = str(fd.get("batch") or "")
        if not re.fullmatch(r"TL-[0-9]{14}", batch):
            frappe.throw("Choose a valid distribution batch.")
        rows = frappe.get_all(LOG, filters={"action": "tl move", "change_json": ["like", "%" + batch + "%"]}, fields=["lead", "change_json"], limit_page_length=1000)
        back = 0
        for r in rows:
            c = json.loads(r.change_json)
            d = frappe.get_doc("Lead", r.lead)
            if c.get("batch") == batch and d.lead_owner == c.get("to") and not summaries([d.name])[d.name].get("protected"):
                d.lead_owner = c.get("from")
                d.custom_assignment_rule = "Undo " + batch + " by " + user
                pass
                d.save(ignore_permissions=True)
                back = back + 1
        res.update({"undone": back})

    elif action == "header":
        # one compact line for the client title bar
        lead = fd.get("lead")
        d = frappe.get_doc("Lead", lead)
        d.check_permission("read")
        sm = summaries([lead]).get(lead) or {}
        nums = lead_numbers(d)
        first = d.creation
        dups = 0
        for n in nums:
            for o in frappe.get_all("Lead", filters={"mobile_no": ["like", "%" + n], "name": ["!=", lead]}, fields=["name", "creation"], limit_page_length=50):
                dups = dups + 1
                if o.creation < first:
                    first = o.creation
        ms = sm.get("milestone") or ""
        since, by = None, ""
        logs = frappe.get_all(LOG, filters={"lead": lead}, fields=["event_time", "action", "erp_user", "change_json", "new_status"], order_by="event_time desc", limit_page_length=200)
        appt_ms = ["Appointment Booked", "Appointment Missed", "Visited", "Visited - Not Booked", "Booked - Payment Pending"]
        for r in logs:
            cj = r.change_json or ""
            if ms in appt_ms and "custom_appointment_status" in cj:
                since, by = r.event_time, r.erp_user
                break
            if ms not in appt_ms and ms != "Joined Client" and ("custom_cc_sub_status" in cj or r.action == "status change"):
                since, by = r.event_time, r.erp_user
                break
        if ms == "Joined Client":
            since = sm.get("joined_on")
            by = sm.get("converting_agent") or ""
        touch, touch_by = None, ""
        for r in logs:
            if r.action in ["call", "status change", "appointment", "followup schedule"]:
                touch, touch_by = r.event_time, r.erp_user
                break
        for v in [d.get("custom_last_call_time"), d.get("custom_convox_last_call_time")]:
            try:
                vv = frappe.utils.get_datetime(v) if v else None
            except Exception:
                vv = None
            if vv and (not touch or vv > frappe.utils.get_datetime(touch)):
                touch = vv
        visit = None
        pats = frappe.get_all("Patient", filters={"custom_lead": lead}, fields=["name"], limit_page_length=5)
        tr = frappe.db.get_value(TRACK, lead, ["matched_patient", "match_status"], as_dict=True)
        pnames = [p.name for p in pats] + ([tr.matched_patient] if tr and tr.match_status == "Verified" and tr.matched_patient else [])
        if pnames:
            pa = frappe.get_all("Patient Appointment", filters={"patient": ["in", pnames], "status": ["not in", ["Cancelled"]]},
                                fields=["branch", "practitioner_name", "custom_report_consultant", "appointment_date", "status"], order_by="appointment_date desc", limit_page_length=1)
            if pa:
                a = pa[0]
                cons = short_name(a.practitioner_name) or person(a.custom_report_consultant)
                visit = {"code": BR_CODE.get(a.branch or "", (a.branch or "")[:3].upper()), "branch": a.branch, "by": cons, "on": str(a.appointment_date or "")}
        res.update({"lead": lead, "received_first": str(first), "received_this": str(d.creation), "duplicates": dups,
                    "milestone": ms, "since": str(since) if since else "", "by": person(by),
                    "last_touch": str(touch) if touch else "", "last_touch_by": person(touch_by), "owner": person(d.lead_owner),
                    "visit": visit, "summary": sm})

    elif action == "agent_stats":
        # per agent: follow-ups due today / overdue, untouched, avg appointments & walk-ins per day (this business month vs last)
        ags = jl(fd.get("agents"))[:60]
        td = frappe.utils.getdate(now)
        if td.day >= 6:
            cs = frappe.utils.getdate(str(td)[:8] + "06")
        else:
            cs = frappe.utils.getdate(str(frappe.utils.add_months(td, -1))[:8] + "06")
        ls_ = frappe.utils.getdate(str(frappe.utils.add_months(cs, -1))[:8] + "06")
        le = frappe.utils.add_days(cs, -1)
        d_this = frappe.utils.date_diff(td, cs) + 1
        d_last = frappe.utils.date_diff(le, ls_) + 1
        VIS = ["Visited", "Visited Booked", "Visited Not Booked"]
        tds = str(td)

        def grp(filters):
            out = {}
            f = dict(filters)
            if ags:
                f["lead_owner"] = ["in", ags]
            for r in frappe.get_all("Lead", filters=f, fields=["lead_owner", "count(name) as n"], group_by="lead_owner", limit_page_length=500):
                out[r.lead_owner] = r.n
            return out
        open_st = ["FOLLOW-UP", "PIPELINE"]
        fu = grp({"custom_next_followup_date": ["between", [tds + " 00:00:00", tds + " 23:59:59"]], "custom_cc_stage": ["in", open_st]})
        od = grp({"custom_next_followup_date": ["<", tds + " 00:00:00"], "custom_cc_stage": ["in", open_st]})
        un = grp({"custom_cc_stage": "UNTOUCHED", "creation": [">", str(frappe.utils.add_days(td, -90))]})
        ap_t = grp({"custom_appointment_date_and_time": ["between", [str(cs) + " 00:00:00", tds + " 23:59:59"]]})
        ap_l = grp({"custom_appointment_date_and_time": ["between", [str(ls_) + " 00:00:00", str(le) + " 23:59:59"]]})
        wk_t = grp({"custom_appointment_date_and_time": ["between", [str(cs) + " 00:00:00", tds + " 23:59:59"]], "custom_appointment_status": ["in", VIS]})
        wk_l = grp({"custom_appointment_date_and_time": ["between", [str(ls_) + " 00:00:00", str(le) + " 23:59:59"]], "custom_appointment_status": ["in", VIS]})
        keys = ags[:]
        if not keys:
            for k in list(fu.keys()) + list(un.keys()) + list(ap_t.keys()):
                if k and k not in keys:
                    keys.append(k)
        st = {}
        for a in keys:
            st[a] = {"fu_today": fu.get(a, 0), "overdue": od.get(a, 0), "untouched": un.get(a, 0),
                     "appt_day": round(float(ap_t.get(a, 0)) / d_this, 1), "appt_day_lm": round(float(ap_l.get(a, 0)) / d_last, 1),
                     "walk_day": round(float(wk_t.get(a, 0)) / d_this, 1), "walk_day_lm": round(float(wk_l.get(a, 0)) / d_last, 1)}
        res.update({"stats": st, "this_from": str(cs), "last_from": str(ls_), "last_to": str(le), "days_this": d_this, "days_last": d_last})

    elif action == "match":
        # find branch patients whose number matches ANY number on this lead (main, alternate, added numbers)
        lead = fd.get("lead")
        d = frappe.get_doc("Lead", lead)
        nums = lead_numbers(d)
        cands = {}
        for n in nums:
            for p in frappe.get_all("Patient", or_filters={"mobile": ["like", "%" + n], "phone": ["like", "%" + n]},
                                    fields=["name", "patient_name", "custom_lead", "custom_branch", "mobile", "creation"], limit_page_length=20):
                cands[p.name] = p
            for r in frappe.get_all("Contact Phone", filters={"parenttype": "Patient", "phone": ["like", "%" + n]}, fields=["parent"], limit_page_length=20):
                if r.parent not in cands:
                    p = frappe.db.get_value("Patient", r.parent, ["name", "patient_name", "custom_lead", "custom_branch", "mobile", "creation"], as_dict=True)
                    if p:
                        cands[p.name] = p
        t = frappe.db.get_value(TRACK, lead, ["matched_patient", "match_status", "verified_by", "verified_on"], as_dict=True) or {}
        out = []
        for pn in cands:
            p = cands[pn]
            if p.custom_lead == lead:
                continue
            inv = frappe.get_all("Sales Invoice", filters={"patient": pn, "docstatus": 1, "is_return": 0},
                                 fields=["name", "posting_date", "branch", "grand_total", "outstanding_amount"], order_by="posting_date asc", limit_page_length=50)
            paid = sum([float(i.grand_total or 0) - float(i.outstanding_amount or 0) for i in inv])
            out.append({"patient": pn, "name": p.patient_name, "branch": p.custom_branch, "mobile_last4": str(p.mobile or "")[-4:],
                        "linked_lead": p.custom_lead, "first_bill": str(inv[0].posting_date) if inv else "", "bills": len(inv),
                        "paid": paid, "invoices": [i.name for i in inv][:5], "bill_branch": inv[0].branch if inv else "",
                        "status": (t.get("match_status") if t.get("matched_patient") == pn else "") or "Suggested"})
        res.update({"numbers": [("••••" + n[-4:]) for n in nums], "matches": out, "can_verify": can_move(user)})

    elif action == "match_verify":
        # TL / Admin confirm after checking branch records
        if not can_move(user):
            frappe.throw("Only TL / Admin can verify a joined client")
        lead = fd.get("lead")
        pn = fd.get("patient")
        decision = fd.get("decision") or "Verified"
        if decision not in ["Verified", "Rejected"]:
            frappe.throw("Bad decision")
        save_track(lead, {"matched_patient": pn, "match_status": decision, "verified_by": user, "verified_on": now,
                          "match_note": (fd.get("note") or "")[:500]})
        frappe.get_doc({"doctype": LOG, "lead": lead, "erp_user": user, "event_time": now, "action": "join " + decision.lower(),
                        "old_status": "", "new_status": pn, "change_json": json.dumps({"patient": pn, "decision": decision, "note": fd.get("note") or ""})}).insert(ignore_permissions=True)
        res["summary"] = summaries([lead]).get(lead)

    elif action == "add_number":
        lead = fd.get("lead")
        d = frappe.get_doc("Lead", lead)
        owner_check(d)
        n = digits10(fd.get("number"))
        if len(n) != 10:
            frappe.throw("Enter a 10-digit mobile number")
        if n in lead_numbers(d):
            frappe.throw("This number is already on the lead")
        d.append("custom_contact_numbers_", {"phone": n})
        d.save(ignore_permissions=True)
        res["numbers"] = [("••••" + x[-4:]) for x in lead_numbers(d)]
        res["modified"] = str(d.modified)

    elif action == "report":
        # Lead Journey report: funnel, agent table, last-call mix, joined clients, TL moves / auto shuffles
        frm = fd.get("from_date") or str(frappe.utils.add_days(frappe.utils.getdate(now), -30))
        to = fd.get("to_date") or str(frappe.utils.getdate(now))
        f = {"creation": ["between", [frm + " 00:00:00", to + " 23:59:59"]]}
        owners = jl(fd.get("owners"))
        if owners:
            f["lead_owner"] = ["in", owners]
        srcs = jl(fd.get("sources"))
        if srcs:
            f["source"] = ["in", srcs]
        report_fields = existing_lead_fields(["name", "lead_owner", "source", "custom_call_count", "custom_convox_call_count", "custom_appointment_status",
                              "custom_cc_stage", "custom_cc_sub_status", "status", "custom_next_followup_date", "custom_cc_appointment_agent"])
        rows = frappe.get_all("Lead", filters=f, fields=report_fields, limit_page_length=30000)
        names = [r.name for r in rows]
        pm = {}
        for i in range(0, len(names), 2000):
            part = paid_map(names[i:i + 2000])
            for k in part:
                pm[k] = part[k]
        ca = credit_agents(pm)
        trk = {}
        for i in range(0, len(names), 3000):
            for t in frappe.get_all(TRACK, filters={"lead": ["in", names[i:i + 3000]]}, fields=["lead", "last_call_result", "unreachable_streak"], limit_page_length=3000):
                trk[t.lead] = t
        BOOKED = ["Booked", "Visited", "Visited Booked", "Visited Not Booked", "Not Visited"]
        VISITED = ["Visited", "Visited Booked", "Visited Not Booked"]
        fun = {"leads": 0, "contacted": 0, "booked": 0, "visited": 0, "joined": 0, "paid": 0.0, "not_visited": 0, "untouched": 0}
        ag = {}
        mix = {}
        joined_list = []
        for r in rows:
            o = r.lead_owner or "Unassigned"
            a = ag.get(o) or {"agent": o, "leads": 0, "contacted": 0, "booked": 0, "visited": 0, "joined": 0, "paid": 0.0, "unreach3": 0, "overdue": 0, "untouched": 0}
            ap = r.custom_appointment_status or ""
            fun["leads"] = fun["leads"] + 1
            a["leads"] = a["leads"] + 1
            if (r.custom_call_count or 0) > 0 or (r.custom_convox_call_count or 0) > 0 or (r.custom_cc_stage or "UNTOUCHED") != "UNTOUCHED":
                fun["contacted"] = fun["contacted"] + 1
                a["contacted"] = a["contacted"] + 1
            if (r.custom_cc_stage or "UNTOUCHED") == "UNTOUCHED":
                fun["untouched"] = fun["untouched"] + 1
                a["untouched"] = a["untouched"] + 1
            if ap in BOOKED:
                fun["booked"] = fun["booked"] + 1
                a["booked"] = a["booked"] + 1
            if ap in VISITED:
                fun["visited"] = fun["visited"] + 1
                a["visited"] = a["visited"] + 1
            if ap == "Not Visited":
                fun["not_visited"] = fun["not_visited"] + 1
            if r.name in pm and pm[r.name].get("paid") and booked(r):
                fun["joined"] = fun["joined"] + 1
                fun["paid"] = fun["paid"] + pm[r.name]["paid"]
                a["joined"] = a["joined"] + 1
                a["paid"] = a["paid"] + pm[r.name]["paid"]
                joined_list.append({"lead": r.name, "owner": o, "joined_on": pm[r.name]["joined_on"], "paid": pm[r.name]["paid"],
                                    "credit": ca.get(r.name) or r.get("custom_cc_appointment_agent") or "", "credit_provisional": pm[r.name].get("credit_provisional", False)})
            t = trk.get(r.name)
            if t:
                if (t.unreachable_streak or 0) >= 3:
                    a["unreach3"] = a["unreach3"] + 1
                k = t.last_call_result or "—"
                mix[k] = mix.get(k, 0) + 1
            if r.custom_next_followup_date and frappe.utils.get_datetime(r.custom_next_followup_date) < now and (r.custom_cc_stage or "") in ["FOLLOW-UP", "PIPELINE"]:
                a["overdue"] = a["overdue"] + 1
            ag[o] = a
        emp_names = {}
        for e in frappe.get_all("Employee", filters={"name": ["in", [j["credit"] for j in joined_list if j["credit"]] or ["-"]]}, fields=["name", "employee_name", "user_id"], limit_page_length=500):
            emp_names[e.name] = e.employee_name
        for j in joined_list:
            j["credit_name"] = short_name(emp_names.get(j["credit"])) or person(j["credit"])
            j["owner"] = person(j["owner"])
        user_names = {}
        for u in frappe.get_all("User", filters={"name": ["in", list(ag.keys()) or ["-"]]}, fields=["name", "full_name"], limit_page_length=500):
            user_names[u.name] = u.full_name
        for k in ag:
            ag[k]["name"] = short_name(user_names.get(k)) or person(k)
        moves = frappe.get_all(LOG, filters={**({"lead": ["in", names or ["-"]]} if not management else {}), "action": ["in", ["tl move", "auto shuffle", "join verified", "join rejected"]],
                                             "event_time": ["between", [frm + " 00:00:00", to + " 23:59:59"]]},
                               fields=["lead", "action", "old_status", "new_status", "erp_user", "event_time", "change_json"],
                               order_by="event_time desc", limit_page_length=500)
        joined_list.sort(key=lambda x: x["joined_on"] or "", reverse=True)
        res.update({"from": frm, "to": to, "funnel": fun, "agents": sorted(list(ag.values()), key=lambda x: -x["leads"]),
                    "last_call_mix": mix, "joined": joined_list[:500], "moves": [{"lead": m.lead, "action": m.action, "event_time": str(m.event_time), "erp_user": person(m.erp_user),
                    "old_status": person(m.old_status) if m.action in ["tl move", "auto shuffle"] else m.old_status,
                    "new_status": person(m.new_status) if m.action in ["tl move", "auto shuffle"] else m.new_status} for m in moves], "capped": len(rows) >= 30000})

    elif action == "cal":
        # day-wise CC appointments for one branch (counts only): appointments · visited · booked
        if user == "Guest":
            frappe.throw("Please login")
        br = str(fd.get("branch") or "").strip()
        frm = str(fd.get("from") or "")[:10]
        to = str(fd.get("to") or "")[:10]
        flt = {"custom_appointment_date_and_time": ["between", [frm + " 00:00:00", to + " 23:59:59"]], "lead_owner": ["is", "set"]}
        if not management:
            flt["lead_owner"] = user
        rows = frappe.get_all("Lead", filters=flt, or_filters=({"branch": br, "lead_assign_to_branch": br} if br else None),
                              fields=["name", "custom_appointment_date_and_time", "custom_appointment_status"], limit_page_length=50000)
        days = {}
        for r in rows:
            k = str(r.custom_appointment_date_and_time)[:10]
            o = days.get(k) or {"a": 0, "v": 0, "b": 0}
            st = r.custom_appointment_status or ""
            o["a"] = o["a"] + 1
            if st in ["Visited", "Visited Booked", "Visited Not Booked"]:
                o["v"] = o["v"] + 1
            if st == "Visited Booked":
                o["b"] = o["b"] + 1
            days[k] = o
        res.update({"branch": br, "days": days})

    elif action == "agents":
        # configured CC agents + checked-in now + open leads in hand
        s = frappe.get_doc("Lead Assignment Settings", "Lead Assignment Settings")
        today = str(frappe.utils.getdate(now))
        out = []
        for c in s.get("agent_config") or []:
            a = c.get("agent")
            if not a:
                continue
            emp = frappe.db.get_value("Employee", {"user_id": a, "status": "Active"}, ["name", "employee_name"], as_dict=True)
            if not emp:
                continue
            att = frappe.get_all("Attendance", filters={"employee": emp.name, "attendance_date": today, "custom_check_in_time": ["is", "set"]},
                                 fields=["custom_check_in_time", "custom_check_out_time"], order_by="custom_check_in_time desc", limit_page_length=1)
            out.append({"agent": a, "name": emp.employee_name, "checked_in": bool(att) and not att[0].get("custom_check_out_time"),
                        "check_in": str(att[0].get("custom_check_in_time")) if att else "",
                        "auto": int(c.get("custom_auto_assign_enabled") or 0), "stopped": int(c.get("custom_temporarily_stopped") or 0),
                        "open": frappe.db.count("Lead", {"lead_owner": a, "custom_cc_stage": ["in", ["UNTOUCHED", "FOLLOW-UP", "PIPELINE"]]}),
                        "overdue": frappe.db.count("Lead", {"lead_owner": a, "custom_next_followup_date": ["<", now], "custom_cc_stage": ["in", ["FOLLOW-UP", "PIPELINE"]]})})
        wl = workload([o["agent"] for o in out])
        for o in out:
            o.update(wl.get(o["agent"]) or {})
        res["agents"] = out
        res["settings"] = cc_settings()

    elif action == "settings_save":
        if user not in EDITORS and not is_tl(user) and not can_move(user):
            frappe.throw("Not allowed")
        new = json.loads(fd.get("settings") or "{}")
        for key in ("cap_overdue", "cap_open", "open_days", "overdue_days", "dormant_days"):
            if key in new and (not isinstance(new[key], (int, float)) or not 1 <= new[key] <= 100000):
                frappe.throw("Workload settings must be positive numbers below 100000.")
        cur = cc_settings()
        for k in ["cap_on", "cap_overdue", "cap_open", "open_days", "overdue_days", "dormant_days", "seniors"]:
            if k in new:
                cur[k] = new[k]
        name = frappe.db.get_value("LIFE CC Assign Rule", {"rule_type": "Settings"}, "name")
        d = frappe.get_doc("LIFE CC Assign Rule", name) if name else frappe.new_doc("LIFE CC Assign Rule")
        d.rule_name = d.rule_name or "Lead distribution settings"
        d.rule_type = "Settings"
        d.enabled = 1
        d.test_mode = 0
        d.last_preview = json.dumps(cur)
        if d.is_new():
            d.insert(ignore_permissions=True)
        else:
            d.save(ignore_permissions=True)
        res["settings"] = cur

    elif action == "bulk_meta":
        if not can_move(user):
            frappe.throw("Not allowed")
        res.update({"branches": [b.name for b in frappe.get_all("Branch", fields=["name"], limit_page_length=100)],
                    "sources": [b.name for b in frappe.get_all("Lead Source", fields=["name"], limit_page_length=200)]})

    elif action == "bulk_check":
        from life_slimming.api.cc_bulk_upload import check_rows
        res.update(check_rows(json.loads(fd.get("rows") or "[]"), fd.get("mode") or "auto", jl(fd.get("to_agents")), fd.get("allow_dup") in [1,"1",True]))

    elif action == "bulk_create":
        # TL bulk upload: create leads and assign (one agent / split / by priority / leave to the automatic assignment)
        if not can_move(user):
            frappe.throw("Not allowed to upload leads")
        raw_rows = json.loads(fd.get("rows") or "[]")
        mode = fd.get("mode") or "auto"
        to = jl(fd.get("to_agents"))
        configured = frappe.get_doc("Lead Assignment Settings", "Lead Assignment Settings")
        valid_agents = {c.get("agent") for c in configured.get("agent_config") or [] if c.get("agent")}
        if any(a not in valid_agents for a in to):
            frappe.throw("Choose configured CC agents only.")
        meth = fd.get("method") or "conversion"
        allow_dup = fd.get("allow_dup") in ["1", 1, True, "true"]
        from life_slimming.api.cc_bulk_upload import check_rows
        preflight = check_rows(raw_rows, mode, to, allow_dup)
        if preflight["invalid"]:
            return {"ok": True, "validation_failed": True, **preflight}
        rows = [r for r in preflight["rows"] if r["state"] == "ready"]
        receivers = list({r.get("agent") for r in rows if mode == "file" and r.get("agent")} | set(to))
        capacity = workload(receivers)
        projected = dict.fromkeys(receivers, 0)
        ranking_for_capacity = agent_rank(to, meth) if mode == "rank" and to else []
        for index, row in enumerate(rows):
            target = row.get("agent") if mode == "file" else to[0] if mode == "agent" and to else to[index % len(to)] if mode == "split" and to else pick_agent(ranking_for_capacity, projected) if ranking_for_capacity else None
            if target:
                projected[target] = projected.get(target, 0) + 1
        settings = cc_settings()
        over = [a for a, load in capacity.items() if load.get("over_cap") or settings.get("cap_on") and load.get("open_recent",0)+projected.get(a,0)>int(settings.get("cap_open") or 1000)]
        if over and fd.get("accept_capacity") not in [1,"1",True]:
            return {"ok": True, "capacity_warning": over, "created": 0}
        ranked = agent_rank(to, meth) if mode == "rank" and to else []
        given = {}
        batch = "UP-" + str(now)[:19].replace("-", "").replace(":", "").replace(" ", "")
        out = [{"row": r["row"], "ok": 0, "msg": "Duplicate skipped: " + r["duplicate"]} for r in preflight["rows"] if r["state"] == "skip"]
        i = 0
        for r in rows:
            name = str(r.get("name") or "").strip()
            mob = digits10(r.get("mobile"))
            if not name or len(mob) != 10:
                out.append({"row": r.get("row"), "ok": 0, "msg": "Name and a 10-digit mobile are required"})
                continue
            if not r.get("source") or not r.get("branch"):
                out.append({"row": r.get("row"), "ok": 0, "msg": "Source and Branch are required"})
                continue
            dup = frappe.get_all("Lead", filters={"mobile_no": ["like", "%" + mob]}, fields=["name", "lead_owner"], limit_page_length=1)
            if dup and not allow_dup:
                out.append({"row": r.get("row"), "ok": 0, "msg": "Already a lead: " + dup[0].name + " (" + person(dup[0].lead_owner) + ")", "dup": dup[0].name})
                continue
            owner = None
            if mode == "agent" and to:
                owner = to[0]
            elif mode == "split" and to:
                owner = to[i % len(to)]
            elif mode == "rank" and ranked:
                owner = pick_agent(ranked, given)
            elif mode == "file":
                owner = r.get("agent") or None
            if owner and owner not in valid_agents:
                out.append({"row": r.get("row"), "ok": 0, "msg": "Choose a configured CC agent"})
                continue
            if owner:
                given[owner] = given.get(owner, 0) + 1
            i = i + 1
            try:
                doc = {"doctype": "Lead", "first_name": name, "mobile_no": mob, "source": r.get("source"), "branch": r.get("branch"),
                       "lead_assign_to_branch": r.get("branch"), "status": "Lead", "city": r.get("city") or "",
                       "custom_treatment_interests": r.get("interest") or "",
                       "custom_remarks": ("[" + batch + " by " + person(user) + "] " + str(r.get("notes") or "")).strip()}
                if r.get("alt") and len(digits10(r.get("alt"))) == 10:
                    doc["phone"] = digits10(r.get("alt"))
                if owner:
                    doc["lead_owner"] = owner
                ld = frappe.get_doc(doc)
                ld.insert(ignore_permissions=True)
                out.append({"row": r.get("row"), "ok": 1, "lead": ld.name, "owner": person(ld.lead_owner) if ld.lead_owner else "Auto queue"})
            except Exception as e:
                out.append({"row": r.get("row"), "ok": 0, "msg": str(e)[:160]})
        res.update({"batch": batch, "results": out, "created": len([x for x in out if x.get("ok")])})

    elif action == "rules":
        res["rules"] = frappe.get_all("LIFE CC Assign Rule", fields=["*"], order_by="rule_type asc, rule_name asc", limit_page_length=200)
        res["can_edit"] = can_move(user)
        res["can_edit_perm"] = user in EDITORS

    elif action == "rule_save":
        r = json.loads(fd.get("rule") or "{}")
        if r.get("rule_type") == "Permissions" and user not in EDITORS:
            frappe.throw("Only Bhuvan and Naren can change who can move leads")
        if not can_move(user):
            frappe.throw("Not allowed")
        name = str(r.get("rule_name") or "").strip()
        if not name or len(name) > 140:
            frappe.throw("Give the rule a name of up to 140 characters.")
        existing_type = frappe.db.get_value("LIFE CC Assign Rule", name, "rule_type")
        if existing_type == "Permissions" and user not in EDITORS:
            frappe.throw("Only Bhuvan and Naren can change a permissions rule.", frappe.PermissionError)
        if r.get("rule_type") not in ["Time-over New Lead", "Time-over Follow-up", "Absent Agent", "Hot Lead Overdue", "Visited Not Booked", "Permissions"]:
            frappe.throw("Choose a supported automatic rule type.")
        if r.get("rule_type") != "Permissions":
            for key in ["time_value", "max_shuffles", "every_minutes", "per_agent_limit"]:
                if not 1 <= int(r.get(key) or 0) <= 100000:
                    frappe.throw("Rule intervals and limits must be positive numbers.")
            if int(r.get("every_minutes") or 0) < 5:
                frappe.throw("Rules run at intervals of at least five minutes.")
        clash = []
        if r.get("rule_type") != "Permissions" and int(r.get("enabled") or 0):
            # one running rule per agent per type: ask before running a second one on the same agents
            mine = r.get("from_agents") or []
            for o in frappe.get_all("LIFE CC Assign Rule", filters={"enabled": 1, "rule_type": r.get("rule_type"), "name": ["!=", name or "-"]},
                                    fields=["name", "from_agents", "test_mode"], limit_page_length=50):
                theirs = jl(o.from_agents)
                if not mine or not theirs or [x for x in mine if x in theirs]:
                    clash.append({"rule": o.name, "agents": [person(x) for x in theirs] or ["All agents"], "test_mode": o.test_mode})
        if clash and not fd.get("force"):
            res.update({"conflict": clash, "saved": 0})
        else:
            if clash and fd.get("force") == "replace":
                for c in clash:
                    frappe.db.set_value("LIFE CC Assign Rule", c["rule"], "enabled", 0)
            d = frappe.get_doc("LIFE CC Assign Rule", name) if frappe.db.exists("LIFE CC Assign Rule", name) else frappe.new_doc("LIFE CC Assign Rule")
            for k in ["rule_name", "rule_type", "enabled", "test_mode", "time_value", "time_unit", "max_shuffles", "days", "from_time", "to_time",
                      "every_minutes", "absent_mode", "statuses", "from_agents", "sources", "to_agents", "method", "per_agent_limit", "allowed_users"]:
                if k in r:
                    v = r.get(k)
                    d.set(k, json.dumps(v) if isinstance(v, list) else v)
            if d.is_new():
                d.insert(ignore_permissions=True)
            else:
                d.save(ignore_permissions=True)
            res.update({"rule": d.name, "saved": 1, "replaced": [c["rule"] for c in clash] if fd.get("force") == "replace" else []})

    else:
        frappe.throw("Unknown action: " + action)

    return {**(saved_result or {}), **res}

