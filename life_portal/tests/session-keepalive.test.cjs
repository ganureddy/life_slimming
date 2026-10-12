const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync(require('node:path').join(__dirname, '../../life_slimming/public/js/session_keepalive.js'), 'utf8');

async function run(response) {
  const timers = new Map(); let id = 0, calls = 0;
  const window = { addEventListener() {} }; window.parent = window;
  vm.runInNewContext(code, {
    window, document: { addEventListener() {} }, AbortController,
    setTimeout(fn, ms) { timers.set(++id, { fn, ms }); return id; },
    clearTimeout(id) { timers.delete(id); },
    fetch: async () => { calls++; if (response instanceof Error) throw response; return response; },
  });
  await new Promise(resolve => setImmediate(resolve));
  return { timers: [...timers.values()], calls };
}
test('exempt session schedules renewal before its timeout', async () => {
  const result = await run({ ok: true, status: 200, json: async () => ({ message: { idle_logout_exempt: true, heartbeat_seconds: 30 } }) });
  assert.equal(result.timers.length, 1); assert.equal(result.timers[0].ms, 30000);
});
test('ordinary users and expired sessions stop renewal', async () => {
  for (const response of [
    { ok: true, status: 200, json: async () => ({ message: { idle_logout_exempt: false } }) },
    { ok: false, status: 401 }, { ok: false, status: 403 },
  ]) assert.equal((await run(response)).timers.length, 0);
});
test('temporary network failures retry without authenticating again', async () => {
  const result = await run(new Error('offline'));
  assert.equal(result.calls, 1); assert.equal(result.timers[0].ms, 60000);
});
test('SPA login resumes policy checks after the guest response', async () => {
  const events = {}, timers = new Map(); let id = 0, calls = 0;
  const window = { addEventListener(name, fn) { events[name] = fn; } }; window.parent = window;
  vm.runInNewContext(code, {
    window, document: { addEventListener() {} }, AbortController,
    setTimeout(fn, ms) { timers.set(++id, { fn, ms }); return id; },
    clearTimeout(id) { timers.delete(id); },
    fetch: async () => ++calls === 1 ? { status: 403 } : {
      ok: true, status: 200, json: async () => ({ message: { idle_logout_exempt: true, heartbeat_seconds: 60 } }),
    },
  });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(timers.size, 0);
  events['life-portal:session-loaded']();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls, 2); assert.equal([...timers.values()][0].ms, 60000);
});
