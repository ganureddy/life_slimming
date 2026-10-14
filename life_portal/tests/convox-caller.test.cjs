const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const bridge = fs.readFileSync(path.join(__dirname, '../../life_slimming/public/js/convox_cc_bridge.js'), 'utf8');
const phone = fs.readFileSync(path.join(__dirname, '../src/components/ConvoxPhone.vue'), 'utf8');

test('caller lookup reaches the legacy iframe and native preview through their own transports', async () => {
  const code = phone.slice(phone.indexOf('async function findCaller('), phone.indexOf('watch(() => route.name'));
  for (const name of ['leads', 'leads-native', 'unjoined']) {
    const messages = [], events = [], navigations = [];
    const context = { route: { name }, isCcDashboard: { value: name.startsWith('leads') },
      router: { push: async value => navigations.push(value) }, minimize() {},
      document: { querySelector: () => ({ contentWindow: { postMessage: (...args) => messages.push(args) } }) },
      window: { location: { origin: 'https://portal.test' }, dispatchEvent: event => events.push(event) },
      CustomEvent: function(type, options) { this.type = type; this.detail = options.detail; } };
    vm.createContext(context);
    vm.runInContext(code, context);
    await context.findCaller({ mobile_number: '+91 9876543210' });
    assert.equal(messages.length, name === 'leads' ? 1 : 0);
    assert.equal(events.length, name === 'leads-native' ? 1 : 0);
    assert.equal(navigations.length, name === 'unjoined' ? 1 : 0);
    if (messages.length) {
      assert.equal(messages[0][0].type, 'life-convox-find');
      assert.equal(messages[0][0].mobile, '+91 9876543210');
      assert.equal(messages[0][1], 'https://portal.test');
    }
  }
});

test('legacy caller search normalizes phone numbers and rejects untrusted messages', () => {
  const searches = [], listeners = {};
  const wrap = { style: {} }, input = { closest: () => wrap, focus() {} };
  const parent = {};
  const context = { parent, location: { origin: 'https://portal.test' },
    document: { createElement: () => ({ setAttribute() {}, addEventListener() {} }),
      querySelector: () => null, getElementById: () => input },
    addEventListener: (name, fn) => { listeners[name] = fn; }, globalSearch: mobile => searches.push(mobile) };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(bridge, context);
  const send = (mobile, overrides = {}) => listeners.message({ origin: context.location.origin, source: parent,
    data: { type: 'life-convox-find', mobile }, ...overrides });
  for (const mobile of ['9876543210', '+91 (98765) 43210', '09876543210']) send(mobile);
  assert.deepEqual(searches, ['9876543210', '9876543210', '9876543210']);
  assert.equal(input.value, '9876543210');
  assert.equal(wrap.style.display, 'flex');
  send('9876543210', { origin: 'https://other.test' });
  send('9876543210', { source: {} });
  send('bad number');
  assert.equal(searches.length, 3);
});
