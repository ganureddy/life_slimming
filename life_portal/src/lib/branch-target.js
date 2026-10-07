import { dateRange, indiaStamp } from './cc.js';

export function targetCycleRange(preset = 'this', today = indiaStamp().slice(0, 10)) {
  const currentStart = dateRange('month', today)[0];
  if (preset === 'this') return [currentStart, today];
  const before = new Date(currentStart + 'T12:00:00Z');
  before.setUTCDate(before.getUTCDate() - 1);
  return dateRange('month', before.toISOString().slice(0, 10));
}

export function elapsedTargetDays(tracker) {
  return (tracker?.days || []).filter(day => !day.future);
}

export function targetKpis(tracker) {
  if (!tracker) return [];
  const n = value => Number(value || 0);
  return tracker.is_closed ? [
    ['Final realisation', `${n(tracker.pct)}%`],
    ['Achieved', n(tracker.achieved)],
    ['Target', n(tracker.target)],
    [n(tracker.gap) > 0 ? 'Shortfall' : 'Surplus', n(tracker.gap)],
    ['Days hit', n(tracker.hit_days)],
    ['Days missed', n(tracker.miss_days)],
  ] : [
    ['Cycle realisation', `${n(tracker.pct)}%`],
    ['Achieved (net)', n(tracker.achieved)],
    ['Gross receipts', n(tracker.gross)],
    ['Monthly target', n(tracker.target)],
    ['Gap to close', n(tracker.gap)],
    ['Needed per day', n(tracker.req_per_day)],
    ['Days left', n(tracker.days_left)],
  ];
}
