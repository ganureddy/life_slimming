const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../src/api/convox.js'), 'utf8')
  .replace(/^import .*;\n/gm, '').replaceAll('export ', '');
function setup() {
  const calls = [];
  const context = { URL, crypto: { getRandomValues: require('node:crypto').webcrypto.getRandomValues.bind(require('node:crypto').webcrypto) }, session: { csrf_token: 'fixture-csrf' }, request: async (...args) => { calls.push(args); return { message: { success: true } }; } };
  vm.createContext(context);
  vm.runInContext(code + '\nthis.api = convoxApi; this.valid = validWidgetUrl; this.accepts = isDashboardMessage; this.createCallRequests = createCallRequests;', context);
  return { context, calls };
}
test('uncertain calls keep their request ID across lead changes and delayed responses', () => {
  const { context } = setup();
  let sequence = 0;
  const requests = context.createCallRequests(() => String(++sequence));
  const first = requests.forLead('LEAD-A');
  const second = requests.forLead('LEAD-B');
  requests.settle('LEAD-A', first, 'UNKNOWN');
  assert.equal(requests.forLead('LEAD-A'), first);
  requests.settle('LEAD-A', first, 'CL000');
  assert.equal(requests.forLead('LEAD-B'), second);
  const next = requests.forLead('LEAD-A');
  assert.notEqual(next, first);
  requests.settle('LEAD-A', first, 'CL000');
  assert.equal(requests.forLead('LEAD-A'), next);
});
test('only the supplied HTTPS widget endpoint is accepted', () => {
  const { context } = setup();
  assert.equal(context.valid('https://lifeslimming.deepijatel.in/ConVoxCCS/ExternalIndex'), true);
  assert.equal(context.valid('https://lifeslimming.deepijatel.in/ConVoxCCS/ExternalIndex?ExternalUserName=fixture'), true);
  for (const url of ['http://192.168.0.193/ConVoxCCS/', 'https://attacker.test/ConVoxCCS/', 'javascript:alert(1)', 'https://user:pass@lifeslimming.deepijatel.in/ConVoxCCS/', 'https://lifeslimming.deepijatel.in/ConVoxCCS/unknown']) assert.equal(context.valid(url), false);
});
test('only the actual CC iframe on the same origin can select a lead', () => {
  const { context } = setup();
  const source = {}, frame = { contentWindow: source }, origin = 'https://local.test';
  const event = { source, origin, data: { type: 'life-convox-select', lead_id: 'LEAD-TEST' } };
  assert.equal(context.accepts(event, frame, origin), true);
  assert.equal(context.accepts({ ...event, source: {} }, frame, origin), false);
  assert.equal(context.accepts({ ...event, origin: 'https://attacker.test' }, frame, origin), false);
  assert.equal(context.accepts({ ...event, data: { ...event.data, lead_id: {} } }, frame, origin), false);
  assert.equal(context.accepts(event, null, origin), false);
});
test('call requests send a lead ID and idempotency key, never credentials or a browser phone number', async () => {
  const { context, calls } = setup();
  await context.api.callLead('LEAD-TEST', 'a'.repeat(32));
  assert.equal(calls[0][0], 'life_slimming.api.convox.click_to_call');
  assert.equal(calls[0][1].csrfToken, 'fixture-csrf');
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0][1].args)), { lead_id: 'LEAD-TEST', request_id: 'a'.repeat(32) });
});
test('dashboard call messages require a lead and a correlated request ID', () => {
  const { context } = setup();
  const source = {}, frame = { contentWindow: source }, origin = 'https://local.test';
  const data = { type: 'life-convox-call', lead_id: 'LEAD-A', request_id: 'a'.repeat(32) };
  assert.equal(context.accepts({ source, origin, data }, frame, origin), true);
  for (const change of [{ lead_id: '' }, { lead_id: undefined }, { request_id: undefined }, { request_id: '<script>' }]) {
    assert.equal(context.accepts({ source, origin, data: { ...data, ...change } }, frame, origin), false);
  }
});

test('request IDs work without randomUUID and remain unique and correlated', () => {
  const { context } = setup();
  const requests = context.createCallRequests();
  const first = requests.forLead('LEAD-A');
  assert.match(first, /^[a-f0-9]{32}$/);
  assert.equal(requests.forLead('LEAD-A'), first);
  assert.notEqual(requests.forLead('LEAD-B'), first);
});
