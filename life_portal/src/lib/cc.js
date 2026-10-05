// Shared native CC presentation rules; no legacy DOM or script execution.
export function indiaStamp(date = new Date()) {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).format(date);
}
export function dateRange(period, today = indiaStamp().slice(0, 10)) {
  const shift = (value, days) => { const d = new Date(value + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0, 10); };
  if (period === 'tomorrow') return [shift(today, 1), shift(today, 1)];
  if (period === 'week') return [shift(today, 1), shift(today, 7)];
  if (period === 'ten') return [today, shift(today, 9)];
  if (period === 'month' || period === 'nextmonth') {
    const d = new Date(today + 'T12:00:00Z');
    d.setUTCMonth(d.getUTCMonth() - (d.getUTCDate() < 6 ? 1 : 0) + (period === 'nextmonth' ? 1 : 0), 6);
    const from = d.toISOString().slice(0, 10); d.setUTCMonth(d.getUTCMonth() + 1, 5);
    return [from, d.toISOString().slice(0, 10)];
  }
  return [today, today];
}
const normalize = value => String(value || '').trim().toLowerCase().replace(/&/g, ' and ').replace(/[–—_\-/]+/g, ' ').replace(/\s+/g, ' ');
export function visitStatus(row) {
  const values = [row.custom_appointment_status, row.custom_visit_status, row.status].filter(Boolean);
  for (const value of values) {
    const n = normalize(value);
    if (['visited booked', 'visited and booked', 'booked visited', 'booked and visited'].includes(n)) return 'Visited-BKD';
    if (['visited not booked', 'visited and not booked', 'visited unbooked', 'not booked visited'].includes(n)) return 'Visited-Not BKD';
  }
  const raw = values[0] || row.custom_cc_stage || 'Not set', n = normalize(raw);
  if (['not visited', 'no show', 'no visit', 'did not visit'].includes(n)) return 'Not Visited';
  if (['booked', 'appointment booked', 'scheduled', 'appointment scheduled', 'confirmed', 're confirm', 'reconfirmed', 'awaiting visit', 'open', 'pending'].includes(n)) return 'Appt Fixed';
  if (n === 'visited') return 'Visited · Outcome pending';
  return raw;
}
export const branchOf = row => row.branch || row.lead_assign_to_branch || 'Branch not assigned';
export function visitMetrics(rows, now = indiaStamp()) {
  const result = { appointments: rows.length, visits: 0, booked: 0, pending: 0, overdue: 0 };
  for (const row of rows) {
    const status = visitStatus(row), stamp = String(row.custom_appointment_date_and_time || '').replace('T', ' ').slice(0, 19);
    const overdue = status === 'Appt Fixed' && stamp && stamp < now;
    if (['Visited-BKD', 'Visited-Not BKD', 'Visited · Outcome pending'].includes(status)) result.visits++;
    if (status === 'Visited-BKD') result.booked++;
    if (overdue) result.overdue++;
    if (status === 'Visited · Outcome pending' || overdue || /branch\s*pending/i.test(status)) result.pending++;
  }
  return result;
}
export function maskPhone(value) {
  const digits = String(value || '').replace(/\D/g, '');
  return digits.length > 4 ? digits.slice(0, 2) + '*'.repeat(digits.length - 4) + digits.slice(-2) : digits;
}
export function csvText(columns, rows) {
  const cell = value => {
    let text = String(value ?? '');
    // Spreadsheet formula injection protection also applies after leading whitespace.
    if (/^\s*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  };
  return '\uFEFF' + [columns.map(c => c.label), ...rows.map(row => columns.map(c => c.value ? c.value(row) : row[c.key]))].map(row => row.map(cell).join(',')).join('\r\n');
}
export function downloadCsv(filename, columns, rows) {
  const url = URL.createObjectURL(new Blob([csvText(columns, rows)], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
