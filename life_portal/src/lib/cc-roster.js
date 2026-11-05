export function movePeriod(start, view, direction) {
  const date = new Date(start + 'T12:00:00Z');
  if (view === 'month') { date.setUTCDate(1); date.setUTCMonth(date.getUTCMonth() + direction); }
  else date.setUTCDate(date.getUTCDate() + direction * 7);
  return date.toISOString().slice(0, 10);
}
export function summarize(cells = {}) {
  const summary = { planned: 0, weekOff: 0, unplanned: 0, conflicts: 0, present: 0, absent: 0, leave: 0 };
  for (const cell of Object.values(cells)) {
    if (cell.shifts.length > 1) summary.conflicts++;
    else if (!cell.shifts.length) summary.unplanned++;
    else if (cell.shifts[0].shift_type === 'Week Off') summary.weekOff++;
    else summary.planned++;
    if (['Present', 'Work From Home'].includes(cell.attendance)) summary.present++;
    if (cell.attendance === 'Absent') summary.absent++;
    if (cell.leave || cell.attendance === 'On Leave') summary.leave++;
  }
  return summary;
}
export function cellLabel(cell) {
  if (cell.shifts.length > 1) return 'Overlapping shifts';
  return cell.shifts[0]?.shift_type || 'Not planned';
}
