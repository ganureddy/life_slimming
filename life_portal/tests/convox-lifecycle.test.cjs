const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/components/ConvoxPhone.vue'), 'utf8');
function setup() {
  let resolvePoll, polls = 0, scheduled = 0;
  const context = { convoxApi: { poll: () => { polls++; return new Promise(resolve => { resolvePoll = resolve; }); } }, setTimeout: () => ++scheduled };
  vm.createContext(context);
  vm.runInContext(`let sessionGeneration = 1, pollingGeneration = null, stopped = false, timer, cursor = '';
    const settings = {value: {callbacks_ready: true}}, controller = {signal: null}, events = {value: []}, incoming = {value:null}, pollError = {value:''}, seen = new Set(), route = {name:'home'};
    ${source.slice(source.indexOf('async function pollEvents()'), source.indexOf('async function showPhone()'))}
    this.poll = pollEvents; this.switchUser = () => {sessionGeneration++}; this.eventCount = () => events.value.length;`, context);
  return { context, resolve: value => resolvePoll(value), stats: () => ({ polls, scheduled }) };
}
test('overlapping poll triggers send one request and schedule one successor', async () => {
 const s = setup(); const first = s.context.poll(); await s.context.poll();
 assert.equal(s.stats().polls, 1);
 s.resolve({cursor:'next', events:[]}); await first;
 assert.equal(s.stats().scheduled, 1);
});
test('a previous user response cannot apply events or restart polling', async () => {
 const s = setup(); const first = s.context.poll(); s.context.switchUser();
 s.resolve({cursor:'old', events:[{name:'private-event',received_on:'now'}]}); await first;
 assert.equal(s.context.eventCount(), 0); assert.equal(s.stats().scheduled, 0);
});
