import {money,fdate,ftime,daysBetween,addDays,d10,TODAY} from './client-info.js';

export const TEMPLATES = [
  { k: "session_1d", i: "⏰", l: "Session reminder, 1 day before", t: "Hi {first}, this is LIFE {branch}. Reminder: your {therapy} session is tomorrow, {appt_date} at {appt_time}. Reply here if you need to reschedule." },
  { k: "session_2h", i: "🕑", l: "Session reminder, 2 hours before", t: "Hi {first}, your LIFE session starts at {appt_time} today. See you at {branch}!" },
  { k: "next_appt", i: "📅", l: "Book next appointment", t: "Hi {first}, you have completed {done} of {total} sessions ({pct}%). Let's book your next visit so your results stay on track. Reply with a convenient day and time." },
  { k: "due", i: "💰", l: "Payment due reminder", t: "Hi {first}, a balance of {due} is pending on your LIFE package{due_date_text}. Please clear it at your next visit or pay online. Thank you." },
  { k: "missed", i: "🤗", l: "We missed you (irregular)", t: "Hi {first}, we missed you at LIFE {branch}! It has been {gap} days since your last session. Regular visits give the best results. Shall we book your next session?" },
  { k: "offer", i: "🎁", l: "Personal offer", t: "Hi {first}, as a valued {tier} client of LIFE, here is an exclusive offer for you: {offer}. Valid till {validity}. Reply to know more." },
  { k: "thanks", i: "🌿", l: "Thank you after session", t: "Hi {first}, thank you for visiting LIFE {branch} today. Please follow your post-care advice. Reach us anytime for help." },
  { k: "custom", i: "✏️", l: "Custom message", t: "Hi {first}, " }
];
export function msgVars(b, extra) {
  const m = b.m, p = b.patient, a = m.nextAppt;
  return Object.assign({
    first: (p.patient_name || "").split(" ")[0] || "there",
    name: p.patient_name || "",
    branch: m.home,
    therapy: a ? (a.therapy_type1 || a.therapy_type || "") : (b.sessions[0] && b.sessions[0].therapy_type) || "",
    appt_date: a ? fdate(a.appointment_date) : "{appt_date}",
    appt_time: a ? (ftime(a.appointment_time) || "") : "{appt_time}",
    done: m.doneS, total: m.totalS, pct: m.completion,
    due: money(m.due.pending),
    due_date_text: m.due.overdue ? ` (due since ${fdate(m.due.oldestOverdue)})` : m.due.next ? ` (due ${fdate(m.due.next)})` : "",
    gap: m.last ? daysBetween(m.last, m.t) : "—",
    tier: m.tier ? m.tier.key : "",
    offer: "{offer}", validity: "{validity}"
  }, extra || {});
}
export const fillTpl = (t, v) => t.replace(/\{(\w+)\}/g, (x, k) => v[k] != null && v[k] !== "" ? v[k] : x).replace(/\s{2,}/g, " ");
export function autoRules(b) {
  const m = b.m, a = m.nextAppt;
  const apptDT = a ? d10(a.appointment_date) + (a.appointment_time ? " " + ftime(a.appointment_time) : "") : null;
  return [
    { i: "⏰", l: "Every session, 1 day before", next: a ? `${fdate(addDays(a.appointment_date, -1))} ${ftime(a.appointment_time)}` : "No upcoming appointment" },
    { i: "🕑", l: "Session day, 2 hours before", next: a ? `${fdate(a.appointment_date)}, 2 hrs before ${ftime(a.appointment_time) || "slot"}` : "No upcoming appointment" },
    { i: "📅", l: "Next appointment not booked (2 days after last session)", next: !a && m.livePlans && m.last ? fdate(addDays(m.last, 2)) : a ? "Already booked" : "No active plan" },
    { i: "💰", l: "Due date crossed and unpaid (repeat every 3 days)", next: m.due.overdue ? "Due now" : m.due.next ? fdate(m.due.next) : "No dues" },
    { i: "🤗", l: "No visit for 14 days (re-engage)", next: m.last && m.livePlans ? fdate(addDays(m.last, 14)) : "—" },
    { i: "🎂", l: "Birthday wish with offer", next: b.patient.dob ? fdate(new Date().getFullYear() + String(b.patient.dob).slice(4, 10)) : "DOB not recorded" }
  ].map(r => Object.assign(r, { apptDT }));
}
