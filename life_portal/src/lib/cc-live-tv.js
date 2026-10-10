import { visitStatus } from './cc.js';
export const kinds = {
  lead: { icon: '🔔', title: 'NEW LEAD RECEIVED', color: '#f5c542' },
  booked: { icon: '📅', title: 'APPOINTMENT BOOKED!', color: '#5dff9f' },
  walkin: { icon: '🚶', title: 'WALK-IN!', color: '#4da3ff' },
  champ: { icon: '👑', title: 'CONGRATULATIONS!', color: '#f5c542' },
};
export const visited = row => ['Visited-BKD', 'Visited-Not BKD', 'Visited · Outcome pending'].includes(visitStatus(row));
export const booked = row => !!row.custom_appointment_date_and_time && !['cancelled', 'canceled'].includes(String(row.custom_appointment_status || row.custom_visit_status || '').toLowerCase());
export function leaderboard(data) {
  const agents = new Map();
  for (const row of data.rows) {
    const id = row.lead_owner || 'unassigned';
    if (!agents.has(id)) agents.set(id, { id, name: data.agents[id] || 'Unassigned', branch: '', today: {leads:0,booked:0,walkins:0}, month: {leads:0,booked:0,walkins:0} });
    const agent = agents.get(id);
    const branch = row.branch || row.lead_assign_to_branch;
    if (branch) agent.branch = agent.branch && agent.branch !== branch ? 'Multiple branches' : branch;
    for (const [period, prefix] of [['today', data.today], ['month', data.today.slice(0,7)]]) {
      if (String(row.creation).startsWith(prefix)) agent[period].leads++;
      if (String(row.custom_appointment_date_and_time || '').startsWith(prefix)) {
        if (booked(row)) agent[period].booked++;
        if (visited(row)) agent[period].walkins++;
      }
    }
  }
  return [...agents.values()].filter(a => Object.values(a.month).some(Boolean));
}
export const rank = (agents, period) => agents.filter(a => a.id !== 'unassigned' && Object.values(a[period]).some(Boolean)).slice().sort((a,b) => b[period].walkins-a[period].walkins || b[period].booked-a[period].booked || b[period].leads-a[period].leads || a.id.localeCompare(b.id)).slice(0,3);
export function changes(previous, data) {
  if (!previous || previous.today !== data.today) return [];
  const old = new Map(previous.rows.map(row => [row.name, row]));
  const events = [];
  for (const row of data.rows) {
    const before = old.get(row.name);
    const types = [];
    if (!before && row.creation > previous.timestamp) types.push('lead');
    if (before && booked(row) && (!booked(before) || row.custom_appointment_date_and_time !== before.custom_appointment_date_and_time)) types.push('booked');
    if (before && visited(row) && !visited(before)) types.push('walkin');
    if (!before && row.creation > previous.timestamp) {
      if (booked(row)) types.push('booked');
      if (visited(row)) types.push('walkin');
    }
    for (const type of types) events.push({id: `${row.name}:${type}:${row.modified}`, type, client: row.lead_name || row.name, agent: data.agents[row.lead_owner] || 'Unassigned', branch: row.branch || row.lead_assign_to_branch || '', source: row.source || '', treatment: row.enquired_for || '', time: row.modified});
  }
  return events.sort((a,b) => a.time.localeCompare(b.time));
}
