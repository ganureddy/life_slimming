// Appointment Scheduler rules maintained directly by the Vue application.
export const appointmentSlots = Array.from({ length: 25 }, (_, index) => {
  const hour = 7 + Math.floor(index / 2);
  return `${String(hour % 12 || 12).padStart(2, '0')}:${index % 2 ? '30' : '00'} ${hour >= 12 ? 'PM' : 'AM'}`;
});
export const appointmentStatuses = ['Scheduled', 'Re-Confirm', 'Re-Scheduled', 'Not Answering', 'Closed', 'Cancel'];
export function appointmentToday(now = new Date()) {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}
export function appointmentTime(value) {
  if (!value) return '';
  if (appointmentSlots.includes(value)) return value;
  const [hour, minute = '00'] = String(value).split(':');
  const number = Number(hour);
  return `${String(number % 12 || 12).padStart(2, '0')}:${minute.padStart(2, '0')} ${number >= 12 ? 'PM' : 'AM'}`;
}
export function appointmentERPTime(slot) {
  const match = /^(\d{1,2}):(\d{2}) (AM|PM)$/.exec(slot || '');
  if (!match) return '';
  const hour = Number(match[1]) % 12 + (match[3] === 'PM' ? 12 : 0);
  return `${hour}:${match[2]}:00`;
}
export function appointmentInFuture(date, slot, now = new Date()) {
  if (!appointmentSlots.includes(slot) || !/^\d{4}-\d{2}-\d{2}$/.test(date || '')) return false;
  const today = appointmentToday(now);
  if (date !== today) return date > today;
  const [hour, minute] = appointmentERPTime(slot).split(':').map(Number);
  return hour * 60 + minute > now.getHours() * 60 + now.getMinutes();
}
export function appointmentOccupiesSlot(row) {
  const status = String(row.call_back_status || row.status || '').toLowerCase().replace(/[-_\s]/g, '');
  return !row.life_ghost && !['rescheduled', 'cancel', 'cancelled'].includes(status);
}
export function appointmentRoomLabel(room, branch) {
  const suffix = String(branch || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return String(room || '').trim().replace(new RegExp('\\s*-\\s*' + suffix + '\\s*$', 'i'), '').trim();
}
export function appointmentStatusClass(status) {
  return 'status-' + ({cancel:'cancel',cancelled:'cancel',closed:'closed','re-scheduled':'rescheduled',rescheduled:'rescheduled','re-confirm':'reconfirm','not answering':'notanswering'}[String(status || '').toLowerCase().trim()] || 'scheduled');
}
export function appointmentReportArgs(doctype, fields, filters, order, length = 500) {
  const [field, direction = 'asc'] = order.split(/\s+/);
  return { doctype, fields: JSON.stringify(fields.map(key => `\`tab${doctype}\`.\`${key}\``)), filters: JSON.stringify(filters),
    order_by: `\`tab${doctype}\`.\`${field}\` ${direction}`, start: 0, page_length: length, view: 'List', group_by: '', with_comment_count: 1 };
}
export function appointmentReportRows(response) {
  const value = response.message;
  if (!Array.isArray(value?.keys) || !Array.isArray(value?.values)) throw new Error('The appointment report returned an invalid response. Please retry.');
  return value.values.map(row => Object.fromEntries(value.keys.map((key, index) => [key, row[index]])));
}
export function appointmentIndex(rows) {
  const index = new Map();
  for (const row of rows) {
    const key = `${row.service_room}||${row.appointment_time}`;
    if (!index.has(key)) index.set(key, []);
    index.get(key).push(row);
  }
  return index;
}
export function appointmentSummary(rows, rooms) {
  const occupied = new Set(rows.filter(appointmentOccupiesSlot).map(row => `${row.service_room}||${row.appointment_time}`));
  return { total: rows.filter(row => !row.life_ghost).length,
    cancelled: rows.filter(row => !row.life_ghost && /cancel/i.test(`${row.status || ''} ${row.call_back_status || ''}`)).length,
    available: rooms.length ? Math.max(0, rooms.length * appointmentSlots.length - occupied.size) : 0 };
}
export function pendingAppointmentTherapies(doc, plan) {
  const category = doc.service_unit || doc.category || '';
  let rows = doc.therapy_plan_details || doc.therapy_plan_detail || doc.therapy_plan_table || doc.therapy_details || doc.plan_details || [];
  if (!rows.length) for (const value of Object.values(doc)) {
    if (Array.isArray(value) && value.some(row => row && (row.therapy_type || row.therapy || row.item || row.item_code || row.procedure_template || row.no_of_sessions || row.sessions || row.total_sessions))) rows = value;
  }
  if (rows.length) return rows.filter(row => row.therapy_type && Number(row.no_of_sessions || 0) > 0 && Number(row.no_of_sessions || 0) > Number(row.sessions_completed || 0)).map(row => ({
    plan: plan.name, therapy: row.therapy_type, unit: row.service_unit || category, start_date: plan.start_date,
    total: Number(row.no_of_sessions || 0), done: Number(row.sessions_completed || 0), pending: Number(row.no_of_sessions || 0) - Number(row.sessions_completed || 0),
  }));
  const therapy = doc.therapy_type || doc.therapy_type1 || doc.concern || doc.item;
  return therapy ? [{ plan: plan.name, therapy, unit: category || doc.healthcare_service_unit || '', start_date: plan.start_date, total: 1, done: 0, pending: 1 }] : [];
}
export function rescheduledAppointment(source, date, slot, user) {
  const time = appointmentERPTime(slot);
  if (source.appointment_date === date && appointmentTime(source.appointment_time) === slot) throw new Error('Choose a different date or time.');
  return { ...source, __unsaved: 1, call_back_status: 'Scheduled', appointment_date: date, appointment_time: time,
    custom_life_move_history: [...(Array.isArray(source.custom_life_move_history) ? source.custom_life_move_history : []), {
      doctype: 'LIFE Appointment Move History', from_date: source.appointment_date, from_time: source.appointment_time,
      from_room: source.service_room, to_date: date, to_time: time, moved_by: user,
    }] };
}
