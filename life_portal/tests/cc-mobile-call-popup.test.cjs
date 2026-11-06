const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'life_slimming/public/js/cc_mobile_call_popup.js'), 'utf8');

function setup(auto = true) {
  const nodes = {}, requests = [], opened = [], events = {}, children = [];
  function element() {
    return { hidden: false, disabled: false, setAttribute() {}, appendChild() {},
      querySelector(selector) { return nodes[selector] ||= element(); } };
  }
  let payload = {}, failure = false, tick;
  const document = { head: element(), body: { appendChild(node) { children.push(node); } }, hidden: false,
    createElement: element, addEventListener(type, fn) { events[type] = fn; } };
  const window = { lifePortalModule: { csrf_token: 'session-token' },
    LIFE_CC_OPEN_LEAD: async id => opened.push(id), addEventListener(type, fn) { events[type] = fn; } };
  const context = vm.createContext({ window, document, AbortController, Date,
    localStorage: { getItem: () => auto ? '1' : '0', setItem() {} },
    setInterval(fn) { tick = fn; return 1; }, clearInterval() {}, setTimeout() { return 2; }, clearTimeout() {},
    fetch: async (url, options) => {
      requests.push({ url, ...options });
      return { ok: !failure, json: async () => payload };
    },
  });
  vm.runInContext(source, context);
  const flush = () => new Promise(resolve => setImmediate(resolve));
  const now = '2026-11-05 12:00:00';
  return { nodes, requests, opened, events, document, flush, children,
    async poll(call, time = now) { await flush(); payload = { message: { call, now: time } }; await tick(); await flush(); },
    async fail() { failure = true; await tick(); },
  };
}
const call = { id: 'call-1', lead: 'LEAD-OUTSIDE-QUEUE', lead_name: '<script>unsafe</script>', ph4: '1234', live: 1 };

test('polls with session CSRF, renders safe text and opens each active call once', async () => {
  const h = setup();
  await h.poll(call);
  assert.equal(h.requests[0].url, '/api/method/life_cc_mobile_v18');
  assert.equal(h.requests[0].headers['X-Frappe-CSRF-Token'], 'session-token');
  assert.equal(h.requests[0].body, '{"action":"live"}');
  assert.equal(h.requests[0].lifePortalBackground, true);
  assert.equal(h.nodes['[data-name]'].textContent, call.lead_name);
  assert.equal(h.nodes['[data-phone]'].textContent, 'LEAD-OUTSIDE-QUEUE · ••••1234');
  await h.poll(call);
  assert.deepEqual(h.opened, [call.lead]);
  h.nodes['header button'].onclick();
  await h.poll(call);
  assert.equal(h.children[0].hidden, true);
  assert.deepEqual(h.opened, [call.lead]);
  await h.poll({ ...call, id: 'call-2' });
  assert.equal(h.children[0].hidden, false);
  assert.deepEqual(h.opened, [call.lead, call.lead]);
});

test('respects automatic-open preference and manual open', async () => {
  const h = setup(false);
  await h.poll(call);
  assert.deepEqual(h.opened, []);
  await h.nodes['[data-open]'].onclick();
  await h.flush();
  assert.deepEqual(h.opened, [call.lead]);
});

test('shows recent ended calls using server time, and skips hidden tabs', async () => {
  const h = setup();
  await h.poll({ ...call, live: 0, ended_on: '2026-11-05 11:59:40.123456', disposition: 'Answered' });
  assert.equal(h.nodes['[data-status]'].textContent, 'Answered');
  assert.equal(h.children[0].hidden, false);
  assert.deepEqual(h.opened, []);
  await h.poll({ ...call, live: 0, ended_on: '2026-11-05 11:59:00' });
  assert.equal(h.children[0].hidden, true);
  await h.poll(call);
  await h.fail();
  assert.equal(h.children[0].hidden, true);
  const count = h.requests.length;
  h.document.hidden = true;
  await h.poll(call);
  assert.equal(h.requests.length, count);
});

test('actual Leads template loads popup and exact lead lookup hook', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'life_slimming/portal_pages/manifest.json')));
  const page = JSON.parse(fs.readFileSync(path.join(root, 'life_slimming/portal_pages', manifest.leads.source + '.json')));
  assert.match(page.javascript, /window\.LIFE_CC_OPEN_LEAD = async function/);
  assert.match(page.javascript, /rows\.find\(item => item\.name === id\)/);
  new vm.Script(page.javascript);
  const template = fs.readFileSync(path.join(root, 'life_slimming/www/life_portal_module.html'), 'utf8');
  assert.ok(template.indexOf('cc_mobile_call_popup.js') > template.indexOf('{{ module_javascript }}'));
});
