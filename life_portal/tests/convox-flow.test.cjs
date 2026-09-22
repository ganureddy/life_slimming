const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const app = path.join(__dirname, '../../life_slimming');
const bridge = fs.readFileSync(path.join(app, 'public/js/convox_cc_bridge.js'), 'utf8');
const page = JSON.parse(fs.readFileSync(path.join(app, 'portal_pages/cc-new-dash.json'), 'utf8'));
const dashboard = page.javascript.slice(page.javascript.indexOf('  let callRequestPending'), page.javascript.indexOf('  function openLeadSummary'));

function setup() {
  const messages = [], notices = [], listeners = {}, timeouts = new Map(), intervals = new Map();
  let seq = 0;
  const button = { disabled: false }, timer = { textContent: 'No call requested' };
  const parent = { postMessage: (data, origin) => messages.push({ data, origin }) };
  const context = {
    location: { origin: 'https://portal.test' }, parent,
    crypto: { randomUUID: () => (++seq).toString(16).padStart(32, '0') },
    document: {
      createElement: () => ({ setAttribute() {}, addEventListener() {} }),
      querySelector: () => null,
      querySelectorAll: selector => selector === '[data-convox-timer]' ? [timer] : [button],
    },
    setTimeout: fn => { const id = ++seq; timeouts.set(id, fn); return id; },
    clearTimeout: id => timeouts.delete(id),
    setInterval: fn => { const id = ++seq; intervals.set(id, fn); return id; },
    clearInterval: id => intervals.delete(id),
    addEventListener: (name, fn) => { (listeners[name] ||= []).push(fn); },
    toast: (...args) => notices.push(args), currentFollowUpLead: { id: 'LEAD-A', callCount: 3 },
    callTimerInterval: null, callSeconds: 0,
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(bridge + '\n' + dashboard, context);
  function reply(result, overrides = {}) {
    const sent = messages.findLast(message => message.data.type === 'life-convox-call').data;
    listeners.message.forEach(fn => fn({ origin: context.location.origin, source: parent,
      data: { ...sent, type: 'life-convox-call-result', ...result }, ...overrides }));
  }
  return { context, messages, notices, button, timer, timeouts, intervals, reply, emit: event => listeners.message.forEach(fn => fn(event)) };
}

test('Start Call sends the selected lead once and shows acceptance without a running timer', async () => {
  const f = setup();
  const pending = f.context.startCallTimer();
  await f.context.startCallTimer();
  assert.equal(f.messages.length, 1);
  assert.equal(f.messages[0].data.lead_id, 'LEAD-A');
  assert.equal(f.button.disabled, true);
  assert.equal(f.intervals.size, 0);
  f.reply({ success: true, status: 'CL000', refno: 'LIFE12345', message: 'Accepted' });
  await pending;
  assert.equal(f.button.disabled, false);
  assert.equal(f.intervals.size, 0);
  assert.equal(f.timer.textContent, 'Request accepted · check phone');
  assert.equal(f.context.currentFollowUpLead.callCount, 3);
  assert.equal(f.timeouts.size, 0);
});

test('a failed, timed-out, or mismatched call cannot start the timer', async () => {
  const f = setup();
  const pending = f.context.startCallTimer();
  f.reply({ success: true }, { origin: 'https://attacker.test' });
  f.reply({ success: true }, { source: {} });
  f.reply({ success: true, lead_id: 'LEAD-B' });
  assert.equal(f.timeouts.size, 1);
  assert.equal(f.intervals.size, 0);
  f.reply({ success: false, status: 'CL006', message: 'Sign in first' });
  await pending;
  assert.equal(f.notices.at(-1)[0], 'Sign in first');
  assert.equal(f.intervals.size, 0);
  const retry = f.context.startCallTimer();
  [...f.timeouts.values()][0]();
  await retry;
  assert.equal(f.intervals.size, 0);
  assert.equal(f.button.disabled, false);
  assert.match(f.notices.at(-1)[0], /unconfirmed/);
});

test('changing leads while calling cannot start a timer on the new lead', async () => {
  const f = setup();
  const pending = f.context.startCallTimer();
  f.context.currentFollowUpLead = { id: 'LEAD-B' };
  f.reply({ success: true, status: 'CL000', refno: 'LIFE12345' });
  await pending;
  assert.equal(f.intervals.size, 0);
});

test('phone controls open the vendor phone and do not claim the call ended', () => {
  const f = setup();
  f.context.stopCallTimer();
  assert.equal(f.messages[0].data.type, 'life-convox-open');
  assert.match(f.notices.at(-1)[0], /Use Hangup/);
});


test('only a trusted matching call result updates the accepted request', async () => {
  const f = setup();
  const pending = f.context.startCallTimer();
  f.reply({ success: true, refno: 'LIFE12345' });
  await pending;
  const data = { type: 'life-convox-status', call_reference: 'LIFE12345', event_type: 'Call Status', call_status: 'DISCONNECTED' };
  f.emit({ origin: 'https://attacker.test', source: f.context.parent, data });
  f.emit({ origin: f.context.location.origin, source: f.context.parent, data: { ...data, call_reference: 'OTHER' } });
  assert.equal(f.timer.textContent, 'Request accepted · check phone');
  f.emit({ origin: f.context.location.origin, source: f.context.parent, data });
  assert.equal(f.timer.textContent, 'Call result: DISCONNECTED');
  assert.equal(f.intervals.size, 0);
});
