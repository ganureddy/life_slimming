const { test } = require('node:test');
const assert = require('node:assert/strict');
const lib = import('../src/lib/branch-target.js');

test('target presets follow the 6th to 5th India sales cycle', async () => {
  const { targetCycleRange } = await lib;
  assert.deepEqual(targetCycleRange('this', '2026-10-05'), ['2026-09-06', '2026-10-05']);
  assert.deepEqual(targetCycleRange('last', '2026-10-05'), ['2026-08-06', '2026-09-05']);
  assert.deepEqual(targetCycleRange('this', '2026-10-06'), ['2026-10-06', '2026-10-06']);
  assert.deepEqual(targetCycleRange('last', '2026-10-06'), ['2026-09-06', '2026-10-05']);
});

test('daily tracker excludes future days and distinguishes open and closed cycles', async () => {
  const { elapsedTargetDays, targetKpis } = await lib;
  assert.deepEqual(elapsedTargetDays({ days: [{ d: '2026-10-05', future: false }, { d: '2026-10-06', future: true }] }).map(row => row.d), ['2026-10-05']);
  assert.equal(targetKpis({ is_closed: 0, pct: 50, req_per_day: 100 })[0][0], 'Cycle realisation');
  assert.equal(targetKpis({ is_closed: 1, pct: 95, gap: 5 })[0][0], 'Final realisation');
});
