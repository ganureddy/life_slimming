const { test } = require('node:test');
const assert = require('node:assert/strict');
const idle = import('../src/lib/idle.js');
async function setup(saved) {
 const { createIdleTimer, WARNING_MS, TIMEOUT_MS } = await idle;
 let time = 10000000, value = saved, warned = 0, expired = 0;
 const options = { now: () => time, read: () => value, write: v => value = v, warning: v => warned = v, expire: () => expired++ };
 const timer = createIdleTimer(options);
 return { timer, options, WARNING_MS, TIMEOUT_MS, advance: ms => time += ms, get warning() { return warned; }, get expired() { return expired; }, get saved() { return value; }, set saved(v) { value = v; } };
}
test('warns at 57 minutes, counts down, and expires once at 60', async () => {
 const t = await setup(); t.advance(t.WARNING_MS - 1); t.timer.check(); assert.equal(t.warning, 0);
 t.advance(1); t.timer.check(); assert.equal(t.warning, 180);
 t.advance(179000); t.timer.check(); assert.equal(t.warning, 1);
 t.advance(1000); t.timer.check(); t.timer.check(); assert.equal(t.expired, 1); assert.equal(t.saved.expired, true);
});
test('activity during warning resets the full idle period', async () => {
 const t = await setup(); t.advance(t.WARNING_MS); t.timer.check(); t.timer.activity(); assert.equal(t.warning, 0);
 t.advance(t.WARNING_MS - 1); t.timer.check(); assert.equal(t.expired, 0); assert.equal(t.warning, 0);
});
test('sleep past deadline expires before activity can renew session', async () => {
 const t = await setup(); t.advance(t.TIMEOUT_MS + 10000); t.timer.activity(); assert.equal(t.expired, 1);
});
test('reload preserves elapsed idle time', async () => {
 const t = await setup(); t.advance(t.WARNING_MS); const { createIdleTimer } = await idle;
 const reloaded = createIdleTimer(t.options); reloaded.check(); assert.equal(t.warning, 180);
});
test('another tab activity extends deadline and logout propagates', async () => {
 const t = await setup(); t.advance(t.WARNING_MS); t.saved = { last: t.saved.last + t.WARNING_MS }; t.timer.check(); assert.equal(t.warning, 0);
 t.saved = { ...t.saved, expired: true }; t.timer.activity(); assert.equal(t.expired, 1);
});
test('an expired session stays expired when reopened', async () => {
 const t = await setup({ last: 9999999, expired: true }); t.timer.check(); assert.equal(t.expired, 1);
});
