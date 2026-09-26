const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../../life_slimming/public/js/portal_module_bridge.js'), 'utf8');

function setup(runtime = {}) {
  const calls = [];
  class XHR {
    open(...args) { this.args = args; }
    setRequestHeader(key, value) { this.header = [key, value]; }
  }
  const context = { URL, Headers, Request, XMLHttpRequest: XHR, location: { href: 'https://local.test/life_portal_module?module=tasks', origin: 'https://local.test' }, document: { addEventListener() {} }, frappe: { call: opts => { calls.push(opts); return opts; } } };
  context.window = context;
  context.lifePortalConfig = runtime;
  context.lifePortalModule = { user: 'fixture@example.test', csrf_token: 'fixture-csrf', methods: { legacy: 'life_slimming.api.server_scripts.fixture.run' }, routes: {} };
  context.fetch = (input, options) => { calls.push({input, options}); return Promise.resolve({ok: true}); };
  vm.runInNewContext(code, context);
  return { context, calls, XHR };
}
test('Frappe calls keep arguments and callbacks and map to POST API URL', () => {
  const { context, calls } = setup();
  const callback = () => {}, options = { method: 'legacy', type: 'GET', args: { branch: 'Fixture Branch' }, callback };
  context.frappe.call(options);
  assert.equal(calls[0].method, 'life_slimming.api.server_scripts.fixture.run');
  assert.equal(calls[0].type, 'POST');
  assert.equal(calls[0].url, '/api/method/life_slimming.api.server_scripts.fixture.run');
  assert.equal(calls[0].callback, callback);
  assert.equal(calls[0].args.branch, 'Fixture Branch');
  assert.equal(options.method, 'legacy');
});
test('fetch remaps ERP requests locally with query, POST, and CSRF', async () => {
  const { context, calls } = setup();
  await context.fetch('https://portal.lifescc.com/api/method/legacy?branch=Fixture');
  assert.equal(calls[0].input, '/api/method/life_slimming.api.server_scripts.fixture.run?branch=Fixture');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.headers.get('X-Frappe-CSRF-Token'), 'fixture-csrf');
});
test('external requests do not receive local CSRF token', async () => {
  const { context, calls } = setup();
  await context.fetch('https://example.test/data');
  assert.equal(calls[0].options.headers.has('X-Frappe-CSRF-Token'), false);
});
test('XHR upgrades migrated GET requests, preserving query and native GET APIs', () => {
  const { XHR } = setup();
  const request = new XHR();
  request.open('GET', '/api/method/legacy?branch=Fixture', true);
  assert.equal(request.args[0], 'POST');
  assert.equal(request.args[1], '/api/method/life_slimming.api.server_scripts.fixture.run?branch=Fixture');
  assert.equal(request.header[1], 'fixture-csrf');
  request.open('GET', '/api/method/frappe.client.get_list?doctype=Branch', true);
  assert.equal(request.args[0], 'GET');
});

test('one API domain setting routes Frappe, fetch and XHR requests', async () => {
  const {context, calls, XHR} = setup({apiBase: 'https://api.example.test/'});
  context.frappe.call({method:'legacy'});
  assert.equal(calls[0].url, 'https://api.example.test/api/method/life_slimming.api.server_scripts.fixture.run');
  assert.equal(calls[0].xhrFields.withCredentials, true);
  await context.fetch('/api/method/legacy?branch=Fixture');
  assert.equal(calls[1].input, 'https://api.example.test/api/method/life_slimming.api.server_scripts.fixture.run?branch=Fixture');
  assert.equal(calls[1].options.credentials, 'include');
  assert.equal(calls[1].options.headers.get('X-Frappe-CSRF-Token'), 'fixture-csrf');
  const xhr = new XHR(); xhr.open('GET','/api/method/legacy',true);
  assert.equal(xhr.args[0], 'POST');
  assert.equal(xhr.withCredentials, true);
  await context.fetch('https://outside.test/api/method/legacy');
  assert.equal(calls[2].input, 'https://outside.test/api/method/legacy');
  assert.equal(calls[2].options.headers.has('X-Frappe-CSRF-Token'), false);
  assert.equal(calls[2].options.credentials, undefined);
});
