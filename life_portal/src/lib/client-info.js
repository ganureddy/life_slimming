// Client Info numerical and profile rules, maintained as application source.
export const CFG = {
  EXCLUDED_BRANCHES: ["Testing Branch", "Head Office"],
  PAGE_SIZE: 10,
  PRINT_FORMAT: "Consultaion Patient Sales Invoice",

  /* Client tier by lifetime paid amount (highest first) */
  TIERS: [
    { key: "HNI", min: 500000.01, icon: "👑", tone: "purple" },
    { key: "VVIP", min: 250000, icon: "💎", tone: "blue" },
    { key: "VIP", min: 200000, icon: "⭐", tone: "amber" }
  ],

  ACTIVE_DAYS: 30,               /* last session within → Active      */
  IRREGULAR_DAYS: 90,            /* within → Irregular, beyond → Stopped */
  DEFAULT_SESSION_GAP_DAYS: 7,   /* used when a plan has no due date  */
  BEHIND_RATIO: 0.75,            /* done < 75% of expected → Behind   */
  REGULAR_RATIO: 0.75,           /* monthly visits ≥ 75% of plan pace → Regular */

  LINKS: {
    billing: "/life_portal/billing",
    appt: "/life_portal/appt",
    service: "/life_portal/service",
    followup: "/life_portal/followup",
    documents: "/life_portal/documents",
    stock: "/life_portal/stock",
    conversions: "/life_portal/conversions"
  },

  CONVERSION_DOCTYPE: "LIFE Client Package Conversion Same Client Package To Package",
  STOCK_API: "client_stock_entries_api_v14",
  CONCERN_DOCTYPES: ["Client Complaint", "Client Concern", "Client Grievance", "LIFE Grievance", "Grievance", "Customer Complaint"],
  DIET_DOCTYPES: ["Client Diet Plan", "Diet Plan", "Diet Chart", "LIFE Diet Plan", "Client Diet Chart"],

  MEDICAL_KEYWORDS: ["diabet", "thyroid", "hypertension", "blood pressure", " bp", "cardiac", "heart", "pregnan", "lactat",
    "pcod", "pcos", "asthma", "epilep", "seizure", "keloid", "cancer", "tumour", "tumor", "kidney", "renal", "liver",
    "allerg", "hepatitis", "hiv", "steroid", "anticoag", "blood thinner", "warfarin", "surgery", "implant", "pacemaker", "psoria", "vitiligo"],

  PREF_KEY: "c360.v8."
};
export const num = v => { const n = parseFloat(v); return Number.isFinite(n) ? n : 0; };
export const r0 = v => (Math.abs(v) < 1 ? 0 : v);
export const pad = n => String(n).padStart(2, "0");
export const iso = d => d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
export const TODAY = () => iso(new Date());
export const d10 = v => String(v || "").slice(0, 10);
export const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const lc = v => String(v || "").trim().toLowerCase();
export const plural = (n, w) => n + " " + w + (n === 1 ? "" : "s");
export const STATUS = {
  active:      { e: "✅", l: "Active",      c: "ok" },
  irregular:   { e: "⚠️", l: "Irregular",   c: "warn" },
  stopped:     { e: "🚫", l: "Stopped",     c: "neg" },
  completed:   { e: "🏁", l: "Completed",   c: "info" },
  not_started: { e: "🆕", l: "Not started", c: "mute" }
};
export const PLAN_STATE = {
  ok:        { e: "▲", l: "On track",  c: "ok" },
  behind:    { e: "▼", l: "Behind",    c: "warn" },
  overdue:   { e: "⛔", l: "Overdue",   c: "neg" },
  done:      { e: "🏁", l: "Completed", c: "info" },
  cancelled: { e: "✕", l: "Cancelled", c: "mute" },
  unknown:   { e: "•", l: "No schedule", c: "mute" }
};
export const INV_STATE = { paid: ["ok", "✅ Paid"], partial: ["warn", "◐ Partial"], unpaid: ["warn", "○ Unpaid"], overdue: ["neg", "⏰ Overdue"] };
export const isExcluded = branch => CFG.EXCLUDED_BRANCHES.some(value => value.toLowerCase() === String(branch || "").trim().toLowerCase());
export function stripHtml(value) {
  return String(value || '').replace(/<[^>]*>/g, ' ').replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&').replace(/&lt;/gi, '<').replace(/&gt;/gi, '>')
    .replace(/&#39;/g, "'").replace(/&quot;/gi, '"').replace(/\s+/g, ' ').trim();
}
export function money(v, dec) {
  const n = r0(num(v));
  return "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: dec == null ? 0 : dec });
}
export function parseD(s) {
  s = d10(s);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const p = s.split("-").map(Number);
  return new Date(p[0], p[1] - 1, p[2]);
}
export function daysBetween(a, b) {
  const A = parseD(a), B = parseD(b);
  if (!A || !B) return null;
  return Math.round((B - A) / 86400000);
}
export function addDays(s, n) { const d = parseD(s); if (!d) return ""; d.setDate(d.getDate() + n); return iso(d); }
export function fdate(s) { const d = parseD(s); return d ? pad(d.getDate()) + "-" + MON[d.getMonth()] + "-" + String(d.getFullYear()).slice(-2) : "—"; }
export function ftime(t) {
  const m = String(t || "").match(/^(\d{1,2}):(\d{2})/);
  if (!m) return "";
  let h = +m[1]; const ap = h >= 12 ? "pm" : "am"; h = h % 12 || 12;
  return h + ":" + m[2] + " " + ap;
}
export function cleanMobile(v) {
  let d = String(v || "").replace(/\D/g, "");
  if (d.length === 12 && d.startsWith("91")) d = d.slice(2);
  if (d.length === 11 && d.startsWith("0")) d = d.slice(1);
  return d;
}
export function maskMobile(v) {
  const d = cleanMobile(v);
  if (!d) return "";
  if (d.length <= 6) return "••••••";
  return d.slice(0, 3) + "****" + d.slice(-3);
}
export function genderEmoji(sex) {
  const s = lc(sex);
  if (s.startsWith("f")) return { e: "👩", t: "Female" };
  if (s.startsWith("m")) return { e: "👨", t: "Male" };
  return { e: "🧑", t: sex || "Not set" };
}
export function initials(name) {
  return String(name || "?").trim().split(/\s+/).map(w => w[0]).join("").slice(0, 2).toUpperCase();
}
export function clientStatus(lastSession, plans) {
  let s = "not_started";
  if (lastSession) {
    const g = daysBetween(lastSession, TODAY());
    s = g <= CFG.ACTIVE_DAYS ? "active" : g <= CFG.IRREGULAR_DAYS ? "irregular" : "stopped";
  }
  const ps = plans || [];
  if (ps.length && ps.every(p => ["completed", "cancelled"].includes(lc(p.status))) && ps.some(p => lc(p.status) === "completed")) s = "completed";
  return s;
}
export function planHealth(p) {
  const st = lc(p.status);
  const total = num(p.total);
  const done = total > 0 ? Math.min(num(p.done), total) : num(p.done);
  const r = { total, done, balance: Math.max(0, total - done), pct: total > 0 ? Math.round(done / total * 100) : 0,
    state: "ok", overdueDays: 0, expected: 0, due: d10(p.due), estimated: false };
  if (st === "cancelled") { r.state = "cancelled"; return r; }
  if ((total > 0 && done >= total) || st === "completed") { r.state = "done"; if (!total) r.pct = 100; return r; }
  const start = d10(p.start);
  if (!start || !total) { r.state = "unknown"; return r; }
  if (!r.due) { r.due = addDays(start, total * CFG.DEFAULT_SESSION_GAP_DAYS); r.estimated = true; }
  const t = TODAY();
  const span = Math.max(1, daysBetween(start, r.due));
  const elapsed = Math.max(0, daysBetween(start, t));
  r.expected = Math.min(total, Math.round(total * Math.min(1, elapsed / span) * 10) / 10);
  if (t > r.due) { r.state = "overdue"; r.overdueDays = daysBetween(r.due, t); return r; }
  if (r.expected >= 1 && done < r.expected * CFG.BEHIND_RATIO && r.expected - done >= 1) r.state = "behind";
  return r;
}
export function dueInfo(invoices) {
  const t = TODAY();
  const r = { pending: 0, withDues: 0, overdue: 0, overdueAmt: 0, next: null, nextAmt: 0, oldestOverdue: null };
  (invoices || []).forEach(i => {
    const o = r0(num(i.outstanding_amount));
    if (o <= 0) return;
    r.pending += o; r.withDues++;
    const dd = d10(i.due_date);
    if (dd && dd < t) { r.overdue++; r.overdueAmt += o; if (!r.oldestOverdue || dd < r.oldestOverdue) r.oldestOverdue = dd; }
    else if (dd && (!r.next || dd < r.next)) { r.next = dd; r.nextAmt = o; }
  });
  return r;
}
export function tierFor(paid) {
  for (const t of CFG.TIERS) if (paid >= t.min) return t;
  return null;
}
export function therapyRows(plan) {
  const out = [], seen = new Set();
  const nameF = ["therapy_type", "therapy", "service", "service_name", "item_code", "item", "package", "package_name"];
  const totF = ["no_of_sessions", "sessions", "total_sessions", "qty", "quantity", "booked_quantity"];
  const doneF = ["sessions_completed", "completed_sessions", "total_sessions_completed", "availed_quantity", "used_sessions", "consumed_sessions", "completed_quantity"];
  Object.keys(plan || {}).forEach(k => {
    const v = plan[k];
    if (!Array.isArray(v)) return;
    v.forEach(row => {
      if (!row || typeof row !== "object") return;
      const n = nameF.map(f => row[f]).find(Boolean);
      if (!n) return;
      const pick = fs => { for (const f of fs) if (row[f] != null && row[f] !== "") return num(row[f]); return 0; };
      const total = pick(totF), done = pick(doneF);
      const key = n + "|" + total + "|" + done;
      if (seen.has(key)) return;
      seen.add(key);
      out.push({ therapy: n, total, done, balance: Math.max(0, total - done) });
    });
  });
  return out;
}
export function detectPhones(p) {
  const out = [], seen = new Set();
  const add = (v, label) => { const d = cleanMobile(v); if (d.length >= 10 && !seen.has(d)) { seen.add(d); out.push({ label, number: d }); } };
  add(p.mobile, "Primary");
  Object.keys(p || {}).forEach(k => {
    if (k === "mobile") return;
    if (!/(mobile|phone|contact|whatsapp|alternate|alt_|emergency)/i.test(k)) return;
    const v = p[k];
    if (typeof v !== "string" && typeof v !== "number") return;
    const label = k.replace(/^custom_/, "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    add(v, label);
  });
  return out;
}
export function detectClientId(p) {
  const pref_ = ["custom_client_id", "client_id", "custom_patient_id", "patient_id", "custom_uhid", "uhid", "custom_registration_number", "registration_number", "custom_mr_number", "mr_number", "uid"];
  for (const k of pref_) if (p[k]) return { id: String(p[k]), real: true };
  const k2 = Object.keys(p).find(k => /(client|patient)_?(id|code|no)$|uhid|mrn|reg(istration)?_?(no|number)/i.test(k) && p[k] && typeof p[k] === "string");
  if (k2) return { id: p[k2], real: true };
  if (p.name && lc(p.name) !== lc(p.patient_name)) return { id: p.name, real: true };
  return { id: p.name || "—", real: false };
}
export function referralInfo(p) {
  const by = [];
  const fields = [];
  Object.keys(p || {}).forEach(k => {
    if (!/(referr|refered|referred|reference_by|ref_by)/i.test(k)) return;
    fields.push(k);
    const v = p[k];
    if (v && (typeof v === "string" || typeof v === "number")) by.push({ field: k, value: String(v) });
  });
  return { by, fields };
}
export function medicalInfo(p, plans) {
  const issues = [];
  const keys = ["allergies", "medication", "medical_history", "surgical_history", "tobacco_past_use", "tobacco_current_use", "alcohol_past_use", "alcohol_current_use", "other_risk_factors", "blood_group"];
  Object.keys(p || {}).forEach(k => {
    const isMed = keys.includes(k) || /^custom_.*(medic|health|disease|condition|allerg|history|chronic|pregnan)/i.test(k);
    if (!isMed) return;
    const v = typeof p[k] === "string" ? stripHtml(p[k]) : "";
    if (!v || /^(no|none|nil|na|n\/a|-|0)$/i.test(v)) return;
    issues.push({ label: k.replace(/^custom_/, "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()), text: v, key: k });
  });
  const flagged = issues.filter(i => i.key !== "blood_group" && CFG.MEDICAL_KEYWORDS.some(w => (" " + lc(i.text)).includes(w)));
  const planMedical = plans.some(x => lc(x.custom_health_status) === "medical");
  return { issues, flagged, isMedical: planMedical || flagged.length > 0 || lc(p.custom_health_status) === "medical" };
}
export function analyze(b) {
  const t = TODAY(), p = b.patient;
  const plans = b.plans.map(x => {
    const rows = therapyRows(x);
    const total = rows.length ? rows.reduce((s, r) => s + r.total, 0) : num(x.total_sessions);
    const done = rows.length ? rows.reduce((s, r) => s + r.done, 0) : num(x.total_sessions_completed);
    return { plan: x, rows, h: planHealth({ start: x.start_date, due: x.due_date, total, done, status: x.status }) };
  });
  
  const live = plans.filter(x => !["done", "cancelled"].includes(x.h.state));
  const totalS = plans.filter(x => x.h.state !== "cancelled").reduce((s, x) => s + x.h.total, 0);
  const doneS = plans.filter(x => x.h.state !== "cancelled").reduce((s, x) => s + x.h.done, 0);

  const ses = b.sessions.slice().sort((a, c) => String(c.start_date || c.creation).localeCompare(String(a.start_date || a.creation)));
  const last = ses.length ? d10(ses[0].start_date || ses[0].creation) : null;
  const firstS = ses.length ? d10(ses[ses.length - 1].start_date || ses[ses.length - 1].creation) : null;
  const joined = plans.map(x => d10(x.plan.start_date)).filter(Boolean).sort()[0] || d10(p.creation);
  const months = Math.max(1, (daysBetween(firstS || joined, t) || 0) / 30.44);
  const avgMonthly = ses.length / months;
  const last90 = ses.filter(s => d10(s.start_date || s.creation) >= addDays(t, -90)).length;
  const recentMonthly = last90 / (90 / 30.44);
  const expectedMonthly = live.reduce((s, x) => {
    const span = Math.max(30, daysBetween(x.plan.start_date, x.h.due) || 30);
    return s + x.h.total / (span / 30.44);
  }, 0);
  const recentVisitDates = new Set(ses.filter(s => d10(s.start_date || s.creation) >= addDays(t, -30) && d10(s.start_date || s.creation) <= t).map(s => d10(s.start_date || s.creation)));
  const consistency = recentVisitDates.size >= 2 ? 'Regular' : 'Irregular';

  const due = dueInfo(b.invoices);
  const paid = r0(b.invoices.reduce((s, i) => s + num(i.base_grand_total) - num(i.outstanding_amount), 0));
  const billed = r0(b.invoices.reduce((s, i) => s + num(i.base_grand_total), 0));
  const tier = tierFor(paid);
  const nextTier = CFG.TIERS.slice().reverse().find(x => paid < x.min) || null;

  const branches = {};
  const bump = (br, d, k) => {
    if (!br || isExcluded(br)) return;
    const x = branches[br] = branches[br] || { branch: br, plans: 0, active: 0, sessions: 0, invoices: 0, first: null, last: null };
    x[k]++;
    d = d10(d);
    if (d) { if (!x.first || d < x.first) x.first = d; if (!x.last || d > x.last) x.last = d; }
  };
  plans.forEach(x => { bump(x.plan.branch, x.plan.start_date, "plans"); if (!["done", "cancelled"].includes(x.h.state) && branches[x.plan.branch]) branches[x.plan.branch].active++; });
  b.sessions.forEach(s => bump(s.branch, s.start_date || s.creation, "sessions"));
  b.invoices.forEach(i => bump(i.branch, i.posting_date, "invoices"));
  const branchList = Object.values(branches).sort((a, c) => String(c.last).localeCompare(String(a.last)));
  const home = p.branch_name || p.branch || p.custom_branch || (branchList[0] && branchList[0].branch) || "—";
  const otherBranches = branchList.filter(x => x.branch !== home && x.plans > 0);

  const firstPlan = plans.map(x => x.plan).filter(x => x.start_date).sort((a, c) => String(a.start_date).localeCompare(String(c.start_date)))[0];
  const joinedBy = firstPlan ? (firstPlan.custom_employee_name || firstPlan.consultant_name || b.users[firstPlan.owner] || firstPlan.owner || "—") : "—";

  const pr = {};
  b.sessions.forEach(s => { const n = s.custom_practitioner_name || s.practitioner; if (n) pr[n] = (pr[n] || 0) + 1; });
  const practitioners = Object.entries(pr).sort((a, c) => c[1] - a[1]);

  const nextAppt = b.appts.filter(a => d10(a.appointment_date) >= t && !["cancelled", "no show"].includes(lc(a.status)))
    .sort((a, c) => (d10(a.appointment_date) + (a.appointment_time || "")).localeCompare(d10(c.appointment_date) + (c.appointment_time || "")))[0] || null;
  const openFu = b.followups.filter(f => !["completed", "closed", "cancelled", "done"].includes(lc(f.status)));
  const overdueFu = openFu.filter(f => d10(f.next_followup_date || f.followup_date) && d10(f.next_followup_date || f.followup_date) < t);
  const nextFu = openFu.filter(f => d10(f.next_followup_date) >= t).sort((a, c) => d10(a.next_followup_date).localeCompare(d10(c.next_followup_date)))[0] || null;

  const status = clientStatus(last, b.plans);
  const med = medicalInfo(p, b.plans);
  const behind = live.filter(x => x.h.state === "behind");
  const overduePlans = live.filter(x => x.h.state === "overdue");

  const alerts = [];
  if (med.flagged.length) alerts.push({ c: "neg", e: "🩺", t: `Medical caution: ${med.flagged.map(x => x.label).join(", ")}` });
  if (due.overdue) alerts.push({ c: "neg", e: "⏰", t: `${plural(due.overdue, "invoice")} past due date — ${money(due.overdueAmt)} overdue since ${fdate(due.oldestOverdue)}` });
  if (due.withDues > 1) alerts.push({ c: "neg", e: "🧾", t: `${due.withDues} invoices carry balance — total ${money(due.pending)}` });
  overduePlans.forEach(x => alerts.push({ c: "neg", e: "⛔", t: `${x.plan.name} crossed its end date by ${x.h.overdueDays} days — ${x.h.balance} of ${x.h.total} sessions pending` }));
  behind.forEach(x => alerts.push({ c: "warn", e: "▼", t: `${x.plan.name} is behind pace — ${x.h.done} done vs ${Math.round(x.h.expected)} expected by today` }));
  if (status === "stopped") alerts.push({ c: "neg", e: "🚫", t: `No session for ${daysBetween(last, t)} days — client at risk of dropping out` });
  if (status === "irregular") alerts.push({ c: "warn", e: "⚠️", t: `Last session ${daysBetween(last, t)} days ago — call to re-engage` });
  if (overdueFu.length) alerts.push({ c: "warn", e: "📞", t: `${plural(overdueFu.length, "followup")} overdue` });
  if (consistency === "Irregular" && expectedMonthly > 0) alerts.push({ c: "warn", e: "📉", t: `Visiting ${recentMonthly.toFixed(1)}/month vs plan pace ${expectedMonthly.toFixed(1)}/month` });
  if (!alerts.length) alerts.push({ c: "ok", e: "🌿", t: "All clear — treatment on track and no overdue payments" });

  let score = 100;
  score -= overduePlans.length * 20 + behind.length * 12 + (due.overdue ? 18 : 0) + (due.withDues > 1 ? 8 : 0) + (overdueFu.length ? 6 : 0);
  score -= status === "stopped" ? 25 : status === "irregular" ? 12 : 0;
  if (consistency === "Irregular") score -= 8;
  score = Math.max(0, Math.min(100, Math.round(score)));

  return {
    planView: plans, t, joined, registered: d10(p.creation), last, firstS, visits: ses.length, avgMonthly, recentMonthly, expectedMonthly, consistency,
    totalS, doneS, completion: totalS ? Math.round(doneS / totalS * 100) : 0, livePlans: live.length,
    due, paid, billed, tier, nextTier, branchList, home, otherBranches, joinedBy, practitioners,
    nextAppt, nextFu, openFu, overdueFu, status, med, alerts, score, behind, overduePlans,
    phones: detectPhones(p), cid: detectClientId(p), ref: referralInfo(p), gender: genderEmoji(p.sex),
    invCount: b.invoices.filter(i => !Number(i.is_return)).length
  };
}
export function billingMonth(offset) {
  const n = new Date();
  let y = n.getFullYear(), m = n.getMonth();
  if (n.getDate() < 6) m -= 1;
  m -= (offset || 0);
  const from = new Date(y, m, 6), to = new Date(y, m + 1, 5);
  return [iso(from), iso(to)];
}
export function qRange(key) {
  const n = new Date();
  if (key === "all") return [null, null];
  if (key === "today") { const t = iso(n); return [t, t]; }
  if (key === "yesterday") { n.setDate(n.getDate() - 1); const t = iso(n); return [t, t]; }
  if (key === "thismonth") return billingMonth(0);
  if (key === "lastmonth") return billingMonth(1);
  return [null, null];
}
export function lookupRule(v) {
  const t = String(v || "").trim();
  const d = t.replace(/\D/g, "");
  const nonDigit = t.replace(/[\s+\-()]/g, "");
  if (d && d.length === nonDigit.length) return { ok: d.length >= 3, type: "mobile", q: d };
  return { ok: t.length >= 3, type: "name", q: t };
}
export function invClass(i) {
  const g = num(i.base_grand_total), o = r0(num(i.outstanding_amount));
  if (o <= 0) return "paid";
  if (d10(i.due_date) && d10(i.due_date) < TODAY()) return "overdue";
  return Math.abs(o - g) < 1 ? "unpaid" : "partial";
}
export function pageRange(cur, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const out = [1];
  const s = Math.max(2, cur - 2), e = Math.min(total - 1, cur + 2);
  if (s > 2) out.push("…");
  for (let i = s; i <= e; i++) out.push(i);
  if (e < total - 1) out.push("…");
  out.push(total);
  return out;
}

export function buildClientList(plans, invoices, sessions, patients, from = '', to = '', includePatients = false) {
  const byPlan = new Map(), byInvoice = new Map(), bySession = new Map(), byPatient = new Map(patients.map(row => [row.name, row]));
  for (const plan of plans) if (plan.patient && !isExcluded(plan.branch)) {
    if (!byPlan.has(plan.patient)) byPlan.set(plan.patient, []);
    byPlan.get(plan.patient).push(plan);
  }
  for (const invoice of invoices) if (!isExcluded(invoice.branch)) {
    if (!byInvoice.has(invoice.patient)) byInvoice.set(invoice.patient, []);
    byInvoice.get(invoice.patient).push(invoice);
  }
  for (const session of sessions) if (!isExcluded(session.branch) && Number(session.docstatus) !== 2) {
    const state = bySession.get(session.patient) || { count: 0, last: '' };
    state.count++; const date = d10(session.start_date || session.creation);
    if (date > state.last) state.last = date;
    bySession.set(session.patient, state);
  }
  const ids = includePatients ? [...new Set([...byPlan.keys(), ...byPatient.keys()])] : [...byPlan.keys()];
  const rows = ids.map(id => {
    const owned = byPlan.get(id) || [], patient = byPatient.get(id) || {}, ownedInvoices = [...(byInvoice.get(id) || [])].sort((a,b) => String(b.posting_date).localeCompare(String(a.posting_date)));
    const first = [...owned].sort((a,b) => String(a.start_date || '9999').localeCompare(String(b.start_date || '9999')))[0] || {};
    const visits = bySession.get(id) || { count: 0, last: '' }, due = dueInfo(ownedInvoices);
    const states = owned.map(plan => planHealth({ start:plan.start_date,due:plan.due_date,total:plan.total_sessions,done:plan.total_sessions_completed,status:plan.status }).state);
    const growth = states.includes('overdue') ? {c:'neg',l:'⛔ Overdue plan'} : states.includes('behind') ? {c:'warn',l:'▼ Behind'} : states.includes('ok') ? {c:'ok',l:'▲ On track'} : states.includes('done') ? {c:'info',l:'🏁 Done'} : {c:'mute',l:'—'};
    const paid = ownedInvoices.reduce((sum,invoice) => { const date=d10(invoice.posting_date); return sum + ((!from || date>=from) && (!to || date<=to) ? num(invoice.base_grand_total)-num(invoice.outstanding_amount) : 0); },0);
    return { id,name:first.patient_name || patient.patient_name || id,customer:patient.customer || '',mobile:cleanMobile(patient.mobile),sex:patient.sex || '',
      joined:first.start_date || patient.custom_joining_date || patient.creation,last:visits.last,visits:visits.count,paid:r0(paid),pending:r0(due.pending),withDues:due.withDues,overdue:due.overdue,
      invCount:ownedInvoices.filter(invoice => !Number(invoice.is_return)).length,medical:owned.some(plan => lc(plan.custom_health_status)==='medical')?'Medical':'Non-Medical',
      branches:[...new Set([...owned.map(plan=>plan.branch),patient.branch_name,patient.custom_branch].map(value=>String(value||'').trim()).filter(value=>value&&!isExcluded(value)))],
      status:clientStatus(visits.last,owned),growth,invoices:ownedInvoices };
  });
  return rows.sort((a,b)=>(b.overdue-a.overdue)||(b.pending-a.pending)||a.name.localeCompare(b.name));
}

export function clientListTotals(rows, collections, branch = '', mode = '') {
  const collected = collections.filter(row=>(!branch || lc(row.branch)===lc(branch))&&(!mode || row.mode_of_payment===mode))
    .reduce((sum,row)=>sum+(num(row.base_received_amount)||num(row.received_amount)||num(row.paid_amount)),0);
  const totals=rows.reduce((sum,row)=>{sum.invoices+=row.invCount;sum.paid+=row.paid;sum.pending+=row.pending;if(row.overdue)sum.overdue++;return sum;},{invoices:0,paid:0,pending:0,overdue:0});
  return {...totals,collected,balance:r0(totals.paid-collected)};
}

export function clientNetworkSummary(plansRaw, sessionsRaw, from, to) {
  const today=TODAY(),cutoff=addDays(today,-90),activeCutoff=addDays(today,-30),now=new Date();
  const year=(now.getMonth()>=3?now.getFullYear():now.getFullYear()-1)+'-04-01';
  const start=from||billingMonth(0)[0],end=to&&to<today?to:today,days=Math.max(1,daysBetween(start,end)+1),months=Math.max(1,(daysBetween(year,today)+1)/30.44);
  const plans=plansRaw.filter(row=>row.patient&&!isExcluded(row.branch)),sessions=sessionsRaw.filter(row=>!isExcluded(row.branch));
  const patients=new Set(plans.map(row=>row.patient)),last=new Map(),branches=new Map(),inService=new Map(),daily=new Map(),monthly=new Map();
  for(const row of plans){if(row.branch){if(!branches.has(row.branch))branches.set(row.branch,new Set());branches.get(row.branch).add(row.patient);if(!['completed','cancelled'].includes(lc(row.status)))inService.set(row.branch,(inService.get(row.branch)||0)+1);}}
  let dailyTotal=0,monthlyTotal=0;
  for(const row of sessions){const date=d10(row.start_date),branch=row.branch||'Unknown';if(date>=cutoff&&date>(last.get(row.patient)||''))last.set(row.patient,date);if(date>=year){monthly.set(branch,(monthly.get(branch)||0)+1);monthlyTotal++;}if(date>=start&&date<=end){daily.set(branch,(daily.get(branch)||0)+1);dailyTotal++;}}
  let active=0,irregular=0,inactive=0;
  for(const id of patients){const date=last.get(id);if(!date)inactive++;else if(date>=activeCutoff)active++;else irregular++;}
  const bars=map=>[...map].sort((a,b)=>b[1]-a[1]).map(([branch,count])=>({branch,count}));
  return{total:patients.size,active,irregular,inactive,completed:new Set(plans.filter(row=>lc(row.status)==='completed').map(row=>row.patient)).size,
    average:branches.size?Math.round(patients.size/branches.size):0,top:[...branches].sort((a,b)=>b[1].size-a[1].size)[0]?.[0]||'—',
    daily:(dailyTotal/days).toFixed(1),monthly:Math.round(monthlyTotal/months),start,end,days,inService:bars(inService),dailyBranches:bars(daily).map(row=>({...row,label:(row.count/days).toFixed(1)+'/d'})),monthlyBranches:bars(monthly).map(row=>({...row,label:Math.round(row.count/months)+'/mo'}))};
}
