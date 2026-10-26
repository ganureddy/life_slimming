import { visitStatus } from './cc.js';
export const kinds = {
  lead: { icon: '🔔', title: 'NEW LEAD RECEIVED', color: '#f5c542' },
  booked: { icon: '📅', title: 'APPOINTMENT BOOKED!', color: '#5dff9f' },
  walkin: { icon: '🚶', title: 'VISITED!', color: '#4da3ff' },
  champ: { icon: '👑', title: 'CONGRATULATIONS!', color: '#f5c542' },
};
// Appointment Status is the only source for appointment outcomes.
const appointmentOutcome = row => visitStatus({custom_appointment_status:row.custom_appointment_status});
export const visited = row => ['Visited-BKD', 'Visited-Not BKD', 'Visited · Outcome pending'].includes(appointmentOutcome(row));
export const booked = row => !!row.custom_appointment_date_and_time && !['cancelled', 'canceled'].includes(String(row.custom_appointment_status || '').toLowerCase());
export function leaderboard(data) {
  const agents = new Map();
  for (const row of data.rows) {
    const id = row.lead_owner || 'unassigned';
    if (!agents.has(id)) agents.set(id, { id, enabled: Object.hasOwn(data.agents, id), name: data.agents[id] || 'Unassigned', branch: '', today: {leads:0,booked:0,walkins:0,visitedBooked:0}, month: {leads:0,booked:0,walkins:0,visitedBooked:0}, week: {walkins:0} });
    const agent = agents.get(id);
    const branch = row.branch || row.lead_assign_to_branch;
    if (branch) agent.branch = agent.branch && agent.branch !== branch ? 'Multiple branches' : branch;
    const appointmentDay = String(row.custom_appointment_date_and_time || '').slice(0,10);
    if (data.week_start && appointmentDay >= data.week_start && appointmentDay < data.week_end && visited(row)) agent.week.walkins++;
    for (const period of ['today', 'month']) {
      const inPeriod = value => {
        const day = String(value || '').slice(0,10);
        return period === 'today' ? day === data.today : day >= data.month_start && day < data.month_end;
      };
      if (inPeriod(row.creation)) agent[period].leads++;
      if (inPeriod(row.custom_appointment_date_and_time)) {
        if (booked(row)) agent[period].booked++;
        if (visited(row)) agent[period].walkins++;
        if (appointmentOutcome(row) === 'Visited-BKD') agent[period].visitedBooked++;
      }
    }
  }
  return [...agents.values()];
}
export const sortedAgents = (agents, period) => agents.filter(a => a.id !== 'unassigned' && a.enabled !== false).slice().sort((a,b) => b[period].walkins-a[period].walkins || (b[period].visitedBooked || 0)-(a[period].visitedBooked || 0) || (b[period].booked || 0)-(a[period].booked || 0) || (b[period].leads || 0)-(a[period].leads || 0) || a.id.localeCompare(b.id));
export const rank = (agents, period) => sortedAgents(agents, period).filter(a => Object.values(a[period]).some(Boolean)).slice(0,3);
export const WEEKLY_TARGET = 35 / 4;
export function highlights(agents) {
  const lines = [];
  for (const agent of sortedAgents(agents, 'today')) {
    const t = agent.today;
    if (t.walkins >= 5) lines.push(`🔥 ${agent.name} · ${t.walkins} visits today`);
    if (t.booked >= 5) lines.push(`📅 ${agent.name} · ${t.booked} appointments booked today`);
    if (agent.month.walkins >= 50) lines.push(`🏆 ${agent.name} · ${agent.month.walkins} visits this month`);
    if (t.walkins >= 2 && t.visitedBooked / t.walkins >= .5) lines.push(`🎯 ${agent.name} · ${Math.round(t.visitedBooked / t.walkins * 100)}% visited booked ratio`);
  }
  return lines.length ? lines : ['⭐ Highlights appear here when agents hit targets'];
}
// Persisted activity, not opening a form, is evidence that a lead was touched.
export function hasRecordedActivity(row) {
  if (row.custom_cc_first_touched_at || row.custom_last_call_time || row.custom_convox_last_call_time) return true;
  if (Number(row.custom_call_count) > 0 || Number(row.custom_convox_call_count) > 0) return true;
  if (row.custom_next_followup_date) return true;
  const normalize = value => String(value || '').trim().toLowerCase();
  const untouched = new Set(['', 'lead', 'new', 'open', 'untouched', 'uncontacted', 'not contacted']);
  if (!untouched.has(normalize(row.custom_cc_sub_status))) return true;
  if (!untouched.has(normalize(row.custom_cc_stage))) return true;
  if (!untouched.has(normalize(row.status))) return true;
  const appointment = normalize(row.custom_appointment_status);
  return !!appointment && !['pending', 'not set'].includes(appointment);
}
// Frappe timestamps are site-local: compare like-for-like without browser timezone conversion.
export function waitingLeads(data, elapsedMs = 0) {
  if (!data) return [];
  const stamp = value => Date.parse(String(value || '').replace(' ', 'T').slice(0,19) + 'Z');
  const now = stamp(data.timestamp) + Math.max(0, elapsedMs);
  return data.rows.filter(row => String(row.creation).startsWith(data.today)
    && row.custom_call_count != null && Number(row.custom_call_count) === 0
    && Object.hasOwn(row, 'custom_last_call_time') && !row.custom_last_call_time
    && !hasRecordedActivity(row))
    .map(row => ({...row, minutes: Math.floor((now-stamp(row.creation))/60000)}))
    .filter(row => row.minutes >= 10).sort((a,b) => b.minutes-a.minutes);
}
export function changes(previous, data) {
  if (!previous || previous.today !== data.today) return [];
  const old = new Map(previous.rows.map(row => [row.name, row]));
  const events = [];
  for (const row of data.rows) {
    if (row.lead_owner && !Object.hasOwn(data.agents, row.lead_owner)) continue;
    const before = old.get(row.name);
    const types = [];
    if (!before && row.creation > previous.timestamp) types.push('lead');
    if (before && booked(row) && (!booked(before) || row.custom_appointment_date_and_time !== before.custom_appointment_date_and_time)) types.push('booked');
    if (before && visited(row) && !visited(before)) types.push('walkin');
    if (!before && row.creation > previous.timestamp) {
      if (booked(row)) types.push('booked');
      if (visited(row)) types.push('walkin');
    }
    for (const type of types) events.push({id: `${row.name}:${type}:${row.modified}`, type, client: row.lead_name || row.name, agentId: row.lead_owner, agent: data.agents[row.lead_owner] || 'Unassigned', branch: row.branch || row.lead_assign_to_branch || '', source: row.source || '', treatment: row.enquired_for || '', appointmentStatus: row.custom_appointment_status || '', time: row.modified});
  }
  return events.sort((a,b) => a.time.localeCompare(b.time));
}
