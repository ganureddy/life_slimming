export const SLIMMING = 'Slimming - LSACPL';
export const CARD_START = '2026-01-01';
export const sessionFields = ['name', 'patient', 'therapy_type', 'service_unit', 'start_date', 'before_weight', 'after_weight', 'weight_loss', 'docstatus'];
export const number = value => Number.isFinite(Number(value)) ? Number(value) : 0;
export const patientKey = value => String(value || '').trim();
export const submitted = rows => rows.filter(row => parseInt(row.docstatus || 0, 10) === 1);
export const sortedSessions = rows => [...rows].sort((a, b) => String(a.start_date || a.date || '').localeCompare(String(b.start_date || b.date || '')) || String(a.name || '').localeCompare(String(b.name || '')));
export function maskMobile(value) {
  const raw = String(value || '').replace(/\D/g, ''), mobile = raw.length > 10 ? raw.slice(-10) : raw;
  return mobile.length < 6 ? mobile : mobile.slice(0, 3) + '****' + mobile.slice(-3);
}
export const kg = value => number(value) > 0 ? number(value).toFixed(1) + ' kg' : '-';
export function difference(value) {
  const amount = number(value);
  return amount > 0 ? amount.toFixed(1) + ' kg ↓ Loss' : amount < 0 ? Math.abs(amount).toFixed(1) + ' kg ↑ Gain' : '0.0 kg No Change';
}
export const differenceClass = value => number(value) > 0 ? 'loss-good' : number(value) < 0 ? 'weight-gain' : 'loss-neutral';
export const sessionDifference = row => number(row.before_weight) && number(row.after_weight) ? number(row.before_weight) - number(row.after_weight) : 0;
export function closingWeight(rows) {
  for (const row of sortedSessions(rows).reverse()) {
    if (number(row.after_weight) > 0) return number(row.after_weight);
    if (number(row.before_weight) > 0) return number(row.before_weight);
  }
  return 0;
}
export function openingWeight(rows) {
  for (const row of sortedSessions(rows)) {
    if (number(row.before_weight) > 0) return number(row.before_weight);
    if (number(row.after_weight) > 0) return number(row.after_weight);
  }
  return 0;
}
export function monthRange(key) {
  const [year, month] = key.split('-').map(Number);
  return { start: key + '-01', end: year + '-' + String(month).padStart(2, '0') + '-' + String(new Date(Date.UTC(year, month, 0)).getUTCDate()).padStart(2, '0') };
}
export function previousMonth(key) {
  const [year, month] = key.split('-').map(Number), date = new Date(Date.UTC(year, month - 2, 1));
  return date.toISOString().slice(0, 7);
}
export function monthLabel(key) {
  return new Intl.DateTimeFormat('en', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(key + '-01T00:00:00Z'));
}
export function groupSessions(rows) {
  const groups = new Map();
  for (const row of submitted(rows)) {
    const key = patientKey(row.patient); if (!key) continue;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return groups;
}
export function monthRows({ month, current, previous, history, plans, patients }) {
  const currentGroups = groupSessions(current), previousGroups = groupSessions(previous), historyGroups = groupSessions(history), bestPlans = new Map();
  const isSlimming = plan => /slimming|weight|slim/i.test(String(plan.category || ''));
  for (const plan of plans.filter(plan => plan.branch)) {
    const key = patientKey(plan.patient), existing = bestPlans.get(key);
    if (!existing || (isSlimming(plan) && !isSlimming(existing))) bestPlans.set(key, plan);
  }
  const mobileByPatient = new Map(patients.map(row => [patientKey(row.name), row.mobile || row.phone || '']));
  return [...currentGroups].map(([patient, currentSessions]) => {
    const now = sortedSessions(currentSessions), prior = sortedSessions(previousGroups.get(patient) || []), lifetime = sortedSessions(historyGroups.get(patient) || []), plan = bestPlans.get(patient) || {};
    const previousClosing = closingWeight(prior), currentOpening = openingWeight(now), reference = previousClosing || currentOpening, currentClosing = closingWeight(now), joinedWeight = openingWeight(lifetime), presentWeight = closingWeight(lifetime);
    return {
      patient, branch: plan.branch || '-', mobile: maskMobile(mobileByPatient.get(patient)), month_label: monthLabel(month), previous_month_label: monthLabel(previousMonth(month)),
      previous_closing_weight: reference, actual_previous_closing_weight: previousClosing, current_closing_weight: currentClosing,
      reference_source: previousClosing ? monthLabel(previousMonth(month)) + ' Closing' : monthLabel(month) + ' Opening Used', used_current_opening_as_reference: !previousClosing && !!currentOpening,
      month_difference: reference && currentClosing ? reference - currentClosing : 0, completed_sessions: now.length, total_sessions: number(plan.total_sessions),
      first_session_date: lifetime[0]?.start_date || '-', joined_weight: joinedWeight, present_weight: presentWeight, total_change: joinedWeight && presentWeight ? joinedWeight - presentWeight : 0,
      current_sessions: now, previous_sessions: prior, lifetime_sessions: lifetime,
    };
  }).sort((a, b) => a.branch.localeCompare(b.branch) || a.patient.localeCompare(b.patient));
}
export function openCardRows({ attendance, plans, patients, today }) {
  const attendedPlans = new Set(submitted(attendance).map(row => String(row.therapy_plan || '')).filter(Boolean));
  const patientMap = new Map(patients.map(row => [patientKey(row.name), row])), clients = new Map();
  for (const plan of plans) {
    const started = String(plan.start_date || '').slice(0, 10), total = number(plan.total_sessions), completed = number(plan.total_sessions_completed);
    if (plan.category !== SLIMMING || number(plan.docstatus) === 2 || !['Not Started', 'In Progress'].includes(plan.status) || started > today || (total > 0 && completed >= total)) continue;
    if (started < CARD_START && !attendedPlans.has(String(plan.name || ''))) continue;
    const patient = patientKey(plan.patient), details = patientMap.get(patient) || {}, branch = plan.branch || details.branch_name || '';
    if (!patient || !branch || ['testing branch', 'head office'].includes(branch.trim().toLowerCase())) continue;
    let row = clients.get(patient);
    if (!row) {
      row = { patient, patient_name: plan.patient_name || patient, therapy_plan: plan.name, plan_status: plan.status, mobile: maskMobile(details.mobile || details.phone), branch, open_plans: [], open_branches: [] };
      clients.set(patient, row);
    }
    row.open_plans.push(plan.name); if (!row.open_branches.includes(branch)) row.open_branches.push(branch);
  }
  return [...clients.values()].sort((a, b) => a.branch.localeCompare(b.branch) || a.patient.localeCompare(b.patient));
}

export function excelTable(headers, rows) {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  return '<html><head><meta charset="UTF-8"><style>table{border-collapse:collapse;width:100%;font:12px Arial}th{background:#16a34a;color:white}td,th{border:1px solid #d1d5db;padding:8px;text-align:left}td{mso-number-format:"\\@"}</style></head><body><table><thead><tr>' + headers.map(value => '<th>' + escape(value) + '</th>').join('') + '</tr></thead><tbody>' + rows.map(row => '<tr>' + row.map(value => '<td>' + escape(value) + '</td>').join('') + '</tr>').join('') + '</tbody></table></body></html>';
}
