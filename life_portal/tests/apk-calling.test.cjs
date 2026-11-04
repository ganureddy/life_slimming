const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../docs/apk-calling/mobile-call-handlers.js'), 'utf8');
const start = 1793790000000;
function setup(rows = []) {
  const events = [];
  const ctx = {
    window: { LifeApp: { getCallLog: () => JSON.stringify(rows) } },
    CCX: { active: { id: 'CALL1', t: start, tel: '9876543210' }, sheet: null, lastIds: [] },
    ccxIso: d => d.toISOString(), ccxStore() {}, ccxAK: () => 'active',
    ccxAfterCall: () => events.push('sheet'), ccxAdCallEnded: () => events.push('ended'),
    ccxRender() {}, ccxApiSelf: args => { events.push(args); return Promise.resolve(); },
  };
  vm.createContext(ctx);
  vm.runInContext(source, ctx);
  return { ctx, events };
}

test('invalid callbacks cannot end the active call', () => {
  const {ctx, events} = setup();
  for (const value of [null, 'invalid json', {}, {talk: 30}, {callId: 'OTHER'}]) {
    ctx.window.LIFE_CALL_DONE(value);
    assert.equal(ctx.CCX.active.ended, undefined);
  }
  assert.equal(events.length, 0);
});

test('native object and JSON string callbacks both work', () => {
  for (const stringify of [false, true]) {
    const {ctx, events} = setup();
    const row = {callId: 'CALL1', start, end: start + 80000, talk: 60, ring: 0, status: 'Answered'};
    ctx.window.LIFE_CALL_DONE(stringify ? JSON.stringify(row) : row);
    assert.equal(ctx.CCX.active.native.talk, 60);
    assert.deepEqual(events, ['sheet', 'ended']);
    assert.equal(ctx.ccxTiming(ctx.CCX.active).end, new Date(row.end).toISOString());
  }
});

test('older, incoming, unrelated and future calls are ignored', () => {
  const base = {number: '9876543210', type: 'Outgoing', talk: 99};
  const {ctx} = setup([
    {...base, start: start - 30000},
    {...base, start, type: 'Incoming'},
    {...base, start, callId: 'OTHER'},
    {...base, start: start + 30000},
    {...base, start, number: '9999999999'},
  ]);
  assert.equal(ctx.ccxTiming(ctx.CCX.active).src, 'App Timer');
});

test('matched outgoing row preserves actual end time', () => {
  const {ctx} = setup([{number: '9876543210', type: 'Outgoing', callId: 'CALL1',
    start: start + 1000, end: start + 45000, talk: 30, ring: 0, status: 'Answered'}]);
  const timing = ctx.ccxTiming(ctx.CCX.active);
  assert.equal(timing.src, 'Phone Call Log');
  assert.equal(timing.talk, 30);
  assert.equal(timing.end, new Date(start + 45000).toISOString());
});

test('late exact timing updates only a known saved call', () => {
  const {ctx, events} = setup();
  ctx.CCX.lastIds = ['SAVED'];
  ctx.window.LIFE_CALL_DONE({callId: 'SAVED', start, talk: 22, status: 'Answered'});
  assert.equal(ctx.CCX.active.ended, undefined);
  assert.equal(events.length, 1);
  assert.equal(events[0].id, 'SAVED');
  assert.equal(events[0].talk_seconds, 22);
});
