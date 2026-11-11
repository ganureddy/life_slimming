"""V26 rule runner. Existing active ERP scheduler takes precedence."""
import json
import frappe


def run():
    if not frappe.db.exists("DocType", "LIFE CC Assign Rule"):
        return
    if frappe.db.exists("Server Script", {"name": "life_cc_autoshuffle", "disabled": 0}):
        return  # Do not run two redistribution jobs against the same rules.
    # LIFE CC AUTO SHUFFLE (V26-4) — Server Script, type Scheduler Event, cron */5 * * * *
    # Reads LIFE CC Assign Rule rows (Time-over New Lead / Time-over Follow-up / Absent Agent).
    # Test Mode ON = only writes what WOULD move into the rule's "Last Run Details". Nothing moves.
    # Never moves: DNC, Lost/Invalid, joined clients, upcoming booked appointments.

    TRACK = "LIFE CC Lead Track"
    LOG = "CC Lead Activity Log"
    now = frappe.utils.now_datetime()
    today = str(frappe.utils.getdate(now))
    DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekday = DAYS[frappe.utils.getdate(now).weekday()]
    MAX_PER_RULE = 50


    def jl(v):
        if not v:
            return []
        try:
            x = json.loads(v)
            return x if isinstance(x, list) else [x]
        except Exception:
            return [s.strip() for s in str(v).split(",") if s.strip()]


    def minutes_of(value, unit):
        v = int(value or 0)
        if unit == "Hours":
            return v * 60
        if unit == "Days":
            return v * 1440
        return v


    def checked_in(user):
        emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
        if not emp:
            return False
        rows = frappe.get_all("Attendance", filters={"employee": emp, "attendance_date": today, "custom_check_in_time": ["is", "set"]},
                              fields=["custom_check_out_time"], order_by="custom_check_in_time desc", limit_page_length=1)
        return bool(rows) and not rows[0].get("custom_check_out_time")


    def configured_agents():
        s = frappe.get_doc("Lead Assignment Settings", "Lead Assignment Settings")
        out = []
        for c in s.get("agent_config") or []:
            if c.get("agent") and int(c.get("custom_auto_assign_enabled") or 0) and not int(c.get("custom_temporarily_stopped") or 0):
                out.append({"agent": c.get("agent"), "sources": [x.strip().lower() for x in (c.get("custom_lead_sources") or "").split(",") if x.strip()]})
        return out


    METHOD = {"Best Conversion": "conversion", "Most Bookings": "bookings", "Best Walk-ins": "walkins", "Round Robin": "equal", "Lowest Load": "smart", "Smart": "smart",
              "Free Hands Leads": "free_leads", "Free Hands Follow-ups": "free_fu"}
    HOT_SUBS = ["Very Positive", "Price Negotiation", "Call & Confirm", "Callback: Scheduled", "Appointment Booked"]


    def settings():
        out = {"cap_on": 1, "cap_overdue": 150, "cap_open": 1000, "open_days": 60,
               "seniors": ["lifebcmanager@gmail.com", "lifescc001@gmail.com", "lifescc13@gmail.com"]}
        row = frappe.db.get_value("LIFE CC Assign Rule", {"rule_type": "Settings"}, "last_preview")
        if row:
            try:
                out.update(json.loads(row))
            except Exception:
                pass
        return out


    def caps(agents, st):
        # agents above the workload cap get no new leads
        since = str(frappe.utils.add_days(frappe.utils.getdate(now), -int(st.get("open_days") or 60))) + " 00:00:00"
        osince = str(frappe.utils.add_days(frappe.utils.getdate(now), -int(st.get("overdue_days") or 30))) + " 00:00:00"
        op, od = {}, {}
        if not agents:
            return {}
        for r in frappe.get_all("Lead", filters={"lead_owner": ["in", agents], "custom_cc_stage": ["in", ["UNTOUCHED", "FOLLOW-UP", "PIPELINE"]], "creation": [">=", since]},
                                fields=["lead_owner", "count(name) as n"], group_by="lead_owner", limit_page_length=200):
            op[r.lead_owner] = r.n
        for r in frappe.get_all("Lead", filters={"lead_owner": ["in", agents], "custom_cc_stage": ["in", ["FOLLOW-UP", "PIPELINE"]], "custom_next_followup_date": ["between", [osince, now]]},
                                fields=["lead_owner", "count(name) as n"], group_by="lead_owner", limit_page_length=200):
            od[r.lead_owner] = r.n
        out = {}
        for a in agents:
            out[a] = {"open": op.get(a, 0), "overdue": od.get(a, 0),
                      "over": bool(st.get("cap_on")) and (od.get(a, 0) > int(st.get("cap_overdue") or 150) or op.get(a, 0) > int(st.get("cap_open") or 1000))}
        return out


    def perf_scores(agents, method):
        since = str(frappe.utils.add_days(frappe.utils.getdate(now), -30)) + " 00:00:00"
        sc = {}
        for a in agents:
            sc[a] = {"appts": 0, "walk": 0, "booked": 0}
        if not agents:
            return {}
        for r in frappe.get_all("Lead", filters={"lead_owner": ["in", agents], "custom_appointment_date_and_time": [">=", since]},
                                fields=["lead_owner", "custom_appointment_status"], limit_page_length=20000):
            o = sc.get(r.lead_owner)
            if not o:
                continue
            o["appts"] = o["appts"] + 1
            if (r.custom_appointment_status or "") in ["Visited", "Visited Booked", "Visited Not Booked"]:
                o["walk"] = o["walk"] + 1
            if (r.custom_appointment_status or "") == "Visited Booked":
                o["booked"] = o["booked"] + 1
        out = {}
        for a in sc:
            o = sc[a]
            conv = o["booked"] * 100.0 / o["walk"] if o["walk"] else 0
            show = o["walk"] * 100.0 / o["appts"] if o["appts"] else 0
            if method == "conversion":
                out[a] = conv + o["booked"] * 0.5
            elif method == "bookings":
                out[a] = o["booked"] * 10 + conv * 0.1
            else:
                out[a] = show + o["walk"] * 0.5
        return out


    def protected(l):
        if (l.status or "") in ["Do Not Contact", "Converted", "Joined"]:
            return True
        if (l.custom_cc_stage or "") in ["LOST", "INVALID", "SUCCESS"]:
            return True
        if (l.custom_appointment_status or "") == "Visited Booked":
            return True
        ad = l.custom_appointment_date_and_time
        if ad and frappe.utils.get_datetime(ad) > now and (l.custom_appointment_status or "") == "Booked":
            return True
        return False


    def joined_leads(names):
        # booked AND paid = Joined Client: never shuffled, feedback only
        if not names:
            return []
        pats = frappe.get_all("Patient", filters={"custom_lead": ["in", names]}, fields=["name", "custom_lead"], limit_page_length=1000)
        p2l = {}
        for p in pats:
            p2l[p.name] = p.custom_lead
        if not p2l:
            return []
        inv = frappe.get_all("Sales Invoice", filters={"patient": ["in", list(p2l.keys())], "docstatus": 1, "is_return": 0},
                            fields=["patient", "grand_total", "outstanding_amount"], limit_page_length=5000)
        return [p2l[i.patient] for i in inv if float(i.grand_total or 0) - float(i.outstanding_amount or 0) > 0]


    F = ["name", "lead_owner", "source", "status", "custom_cc_stage", "custom_appointment_status",
         "custom_appointment_date_and_time", "custom_next_followup_date", "creation"]

    rules = frappe.get_all("LIFE CC Assign Rule", filters={"enabled": 1, "rule_type": ["in", ["Time-over New Lead", "Time-over Follow-up", "Absent Agent", "Visited Not Booked", "Hot Lead Overdue"]]},
                           fields=["*"], limit_page_length=50)

    agents_cfg = configured_agents() if rules else []
    ST = settings() if rules else {}
    CAP = caps([a["agent"] for a in agents_cfg], ST) if rules else {}
    present = {}
    for a in agents_cfg:
        present[a["agent"]] = checked_in(a["agent"])

    for r in rules:
        if r.days and weekday not in [d.strip()[:3] for d in r.days.split(",")]:
            continue
        t_now = str(now.time())[:8]
        if r.from_time and t_now < str(r.from_time)[:8].zfill(8):
            continue
        if r.to_time and t_now > str(r.to_time)[:8].zfill(8):
            continue
        every = int(r.every_minutes or 15)
        if r.last_run and frappe.utils.time_diff_in_seconds(now, r.last_run) < every * 60 - 30:
            continue

        lim = frappe.utils.add_to_date(now, minutes=-minutes_of(r.time_value, r.time_unit))
        srcs = jl(r.sources)
        froms = jl(r.from_agents)
        tos = jl(r.to_agents)
        statuses = jl(r.statuses)
        f = {"lead_owner": ["is", "set"]}
        if srcs:
            f["source"] = ["in", srcs]
        if statuses:
            f["custom_cc_sub_status"] = ["in", statuses]

        if r.rule_type == "Time-over New Lead":
            f["custom_cc_stage"] = "UNTOUCHED"
            f["creation"] = ["between", [frappe.utils.add_days(now, -30), lim]]
            if froms:
                f["lead_owner"] = ["in", froms]
        elif r.rule_type == "Time-over Follow-up":
            f["custom_cc_stage"] = ["in", ["FOLLOW-UP", "PIPELINE", "UNTOUCHED"]]
            f["custom_next_followup_date"] = ["between", [frappe.utils.add_days(now, -60), lim]]
            if froms:
                f["lead_owner"] = ["in", froms]
        elif r.rule_type == "Hot Lead Overdue":
            # hot / interested leads whose follow-up time passed by the limit
            f["custom_cc_stage"] = ["in", ["FOLLOW-UP", "PIPELINE"]]
            f["custom_next_followup_date"] = ["between", [frappe.utils.add_days(now, -30), lim]]
            if not statuses:
                f["custom_cc_sub_status"] = ["in", HOT_SUBS]
            if froms:
                f["lead_owner"] = ["in", froms]
        elif r.rule_type == "Visited Not Booked":
            # came to the branch, did not book → senior closers within the limit (default 24 h)
            f["custom_appointment_status"] = "Visited Not Booked"
            f["custom_appointment_date_and_time"] = ["between", [frappe.utils.add_days(now, -10), lim]]
            seniors = tos or ST.get("seniors") or []
            f["lead_owner"] = ["not in", seniors or ["-"]]
            if froms:
                f["lead_owner"] = ["in", [x for x in froms if x not in seniors] or ["-"]]
            if not tos:
                tos = seniors
        else:
            absent = [a for a in (froms or [x["agent"] for x in agents_cfg]) if not present.get(a)]
            if not absent:
                frappe.db.set_value("LIFE CC Assign Rule", r.name, {"last_run": now, "last_moved": 0, "last_preview": "No absent agents"}, update_modified=False)
                continue
            f["lead_owner"] = ["in", absent]
            f["custom_next_followup_date"] = ["between", [frappe.utils.add_days(now, -7), today + " 23:59:59"]]
            f["custom_cc_stage"] = ["not in", ["LOST", "INVALID", "SUCCESS"]]

        leads = frappe.get_all("Lead", filters=f, fields=F, order_by="creation asc", limit_page_length=300)
        paid_leads = joined_leads([l.name for l in leads])
        cands = [l for l in leads if not protected(l) and l.name not in paid_leads]

        pool = []
        capped = []
        for a in agents_cfg:
            if not present.get(a["agent"]):
                continue
            if tos and a["agent"] not in tos:
                continue
            if (CAP.get(a["agent"]) or {}).get("over"):
                capped.append(a["agent"])
                continue
            pool.append(a)
        if r.rule_type == "Visited Not Booked":
            # seniors may be outside the auto-assignment list: add them if checked in
            for sname in tos:
                if sname not in [x["agent"] for x in pool] and sname not in capped and checked_in(sname):
                    pool.append({"agent": sname, "sources": []})
        load = {}
        for a in pool:
            load[a["agent"]] = 0
        meth = METHOD.get(r.method or "Smart", "smart")
        scores = perf_scores([a["agent"] for a in pool], meth) if meth in ["conversion", "bookings", "walkins"] else {}
        if meth == "smart":
            for a in pool:
                load[a["agent"]] = frappe.db.count("Lead", {"lead_owner": a["agent"], "custom_cc_stage": ["in", ["UNTOUCHED", "FOLLOW-UP", "PIPELINE"]]}) / 1000.0
        per = int(r.per_agent_limit or 0)
        maxs = int(r.max_shuffles or 2)

        lines = []
        moved = 0
        to_tl = 0
        for l in cands:
            if moved >= MAX_PER_RULE:
                break
            sc = frappe.db.get_value(TRACK, l.name, "shuffle_count") or 0
            if sc >= maxs:
                to_tl = to_tl + 1
                lines.append(l.name + " | " + (l.lead_owner or "") + " -> TL queue (shuffled " + str(sc) + "x)")
                continue
            src = (l.source or "").lower()
            opts = [a["agent"] for a in pool if a["agent"] != l.lead_owner and (not a["sources"] or src in a["sources"])]
            if per:
                opts = [a for a in opts if load[a] < per]
            if not opts:
                lines.append(l.name + " | no eligible checked-in agent")
                continue
            if meth in ["conversion", "bookings", "walkins"]:
                opts = sorted(opts, key=lambda x: -((max(scores.get(x, 0), 0) + 1) / (load[x] + 1.0)))
            elif meth == "free_leads":
                opts = sorted(opts, key=lambda x: (CAP.get(x) or {}).get("open", 0) + load[x] * 5)
            elif meth == "free_fu":
                opts = sorted(opts, key=lambda x: (CAP.get(x) or {}).get("overdue", 0) + load[x] * 5)
            elif meth == "equal":
                opts = sorted(opts, key=lambda x: (load[x], x))
            else:
                opts = sorted(opts, key=lambda x: load[x])
            target = opts[0]
            load[target] = load[target] + 1
            lines.append(l.name + " | " + (l.lead_owner or "") + " -> " + target)
            if int(r.test_mode or 0) or (r.rule_type == "Absent Agent" and r.absent_mode == "Manual"):
                continue
            d = frappe.get_doc("Lead", l.name)
            old = d.lead_owner
            d.lead_owner = target
            d.custom_assignment_method = "Manual"
            d.custom_assignment_rule = "Auto shuffle: " + r.rule_name
            d.save(ignore_permissions=True)
            frappe.get_doc({"doctype": LOG, "lead": l.name, "erp_user": "Administrator", "event_time": now, "action": "auto shuffle",
                            "old_status": old or "", "new_status": target,
                            "change_json": json.dumps({"rule": r.rule_name, "from": old, "to": target})}).insert(ignore_permissions=True)
            if frappe.db.exists(TRACK, l.name):
                t = frappe.get_doc(TRACK, l.name)
            else:
                t = frappe.new_doc(TRACK)
                t.lead = l.name
            t.shuffle_count = sc + 1
            t.last_shuffled_at = now
            if t.is_new():
                t.insert(ignore_permissions=True)
            else:
                t.save(ignore_permissions=True)
            moved = moved + 1

        mode = "TEST MODE - nothing moved" if int(r.test_mode or 0) else ("MANUAL - TL to reassign" if (r.rule_type == "Absent Agent" and r.absent_mode == "Manual") else "LIVE")
        head = mode + " | " + str(len(cands)) + " leads matched, " + (str(len(capped)) + " agents skipped (over workload cap), " if capped else "") + str(moved) + " moved, " + str(to_tl) + " to TL queue | " + str(now)[:16]
        frappe.db.set_value("LIFE CC Assign Rule", r.name, {"last_run": now, "last_moved": moved,
                            "last_preview": (head + "\n" + "\n".join(lines[:150]))[:60000]}, update_modified=False)

