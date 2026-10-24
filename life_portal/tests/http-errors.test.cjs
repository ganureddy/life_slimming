const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../src/api/http.js'), 'utf8').replace(/^import .*;\n/gm, '').replaceAll('export ', '');
const endpoints = JSON.parse(fs.readFileSync(path.join(__dirname, '../src/api/endpoints.json'), 'utf8'));
function setup(status, body) {
  const context = { endpoints, AbortController, setTimeout, clearTimeout, apiUrl: v => v, apiCredentials: () => 'same-origin', fetch: async () => ({ ok: false, status, json: async () => body }) };
  vm.createContext(context);
  vm.runInContext(code + '\nthis.send = request;', context);
  return context.send('fixture');
}
test('validation errors show the server message as plain text', async () => {
  await assert.rejects(setup(417, { exc_type: 'ValidationError', _server_messages: JSON.stringify([JSON.stringify({ message: 'Select a <b>branch</b> before saving.' })]) }), /Select a branch before saving/);
});
test('CSRF errors explain refreshing rather than missing permission', async () => {
  await assert.rejects(setup(403, { exc_type: 'CSRFTokenError' }), /Refresh the page/);
});
test('unexpected server errors do not display raw tracebacks', async () => {
  await assert.rejects(setup(500, { exc_type: 'DatabaseError', exception: 'private-server-detail', _server_messages: 'malformed' }), error => !error.message.includes('private-server-detail') && error.message.includes('try again'));
});

function timedClient(fetch) {
  const context = { endpoints, AbortController, DOMException, setTimeout, clearTimeout, apiUrl: v => v, apiCredentials: () => 'same-origin', fetch };
  vm.createContext(context);
  vm.runInContext(code + '\nthis.send = request;', context);
  return context.send;
}
function waitForAbort(signal) {
  return new Promise((resolve, reject) => {
    if (signal.aborted) return reject(new DOMException('Aborted', 'AbortError'));
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
  });
}
test('a stalled request becomes a visible timeout rather than an ignored navigation abort', async () => {
  let calls = 0;
  const send = timedClient((url, { signal }) => { calls++; return waitForAbort(signal); });
  await assert.rejects(send('frappe.client.get_list', { timeoutMs: 10 }), error => error.code === 'TimeoutError' && error.name !== 'AbortError');
  assert.equal(calls, 1, 'do not automatically retry transactions');
});
test('the deadline includes a stalled response body', async () => {
  const send = timedClient(async (url, { signal }) => ({ ok: true, json: () => waitForAbort(signal) }));
  await assert.rejects(send('fixture', { timeoutMs: 10 }), error => error.code === 'TimeoutError');
});
test('navigation cancellation stays an AbortError and reaches fetch', async () => {
  const controller = new AbortController();
  let fetchSignal;
  const send = timedClient((url, { signal }) => { fetchSignal = signal; return waitForAbort(signal); });
  const result = send('fixture', { signal: controller.signal, timeoutMs: 1000 });
  controller.abort();
  await assert.rejects(result, error => error.name === 'AbortError');
  assert.equal(fetchSignal.aborted, true);
});
test('successful requests remove their cancellation listener', async () => {
  const controller = new AbortController();
  let listeners = 0;
  const signal = { get aborted() { return controller.signal.aborted; },
    addEventListener: (...args) => { listeners++; controller.signal.addEventListener(...args); },
    removeEventListener: (...args) => { listeners--; controller.signal.removeEventListener(...args); } };
  const send = timedClient(async () => ({ ok: true, json: async () => ({ message: 'done' }) }));
  const result = await send('fixture', { signal });
  assert.equal(result.message, 'done');
  assert.equal(listeners, 0);
});

test('native legacy method names reach local migrated endpoints without guessing ambiguous aliases', async () => {
  const calls = [];
  const send = timedClient(async url => { calls.push(url); return { ok: true, json: async () => ({ message: [] }) }; });
  for (const method of ['life_stores_360_live_api', 'life_stock_fast_requests', 'payables_planner_api', 'frappe.client.get_list', 'create_po_from_indent360']) await send(method);
  assert.deepEqual(calls, [
    '/api/method/life_slimming.api.server_scripts.life_stores_360_live_api.run',
    '/api/method/life_slimming.api.server_scripts.life_stock_fast_requests.run',
    '/api/method/life_slimming.api.server_scripts.payables_planner_api.run',
    '/api/method/frappe.client.get_list',
    '/api/method/create_po_from_indent360',
  ]);
});

test('multipart uploads use the mapped endpoint, CSRF and browser-generated boundary', async () => {
  let call;
  const send = timedClient(async (url, options) => { call = { url, options }; return { ok: true, json: async () => ({ message: { file_url: '/private/files/photo.png' } }) }; });
  const formData = new FormData(); formData.append('file', new Blob(['photo']), 'photo.png');
  await send('life_stock_fast_requests', { formData, csrfToken: 'upload-csrf' });
  assert.equal(call.url, '/api/method/life_slimming.api.server_scripts.life_stock_fast_requests.run');
  assert.equal(call.options.method, 'POST'); assert.equal(call.options.body, formData);
  assert.equal(call.options.headers['X-Frappe-CSRF-Token'], 'upload-csrf');
  assert.equal(call.options.headers['Content-Type'], undefined);
});
