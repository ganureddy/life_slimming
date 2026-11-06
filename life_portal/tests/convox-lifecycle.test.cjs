const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/components/ConvoxPhone.vue'), 'utf8');
function setup(settingsValue = {callbacks_ready:true}) {
  let resolvePoll, rejectPoll, polls = 0, scheduled = 0;
  const delays = [];
  const context = { convoxApi: { poll: () => { polls++; return new Promise((resolve, reject) => { resolvePoll = resolve; rejectPoll = reject; }); } }, setTimeout: (_, delay) => { delays.push(delay); return ++scheduled; } };
  vm.createContext(context);
  vm.runInContext(`let sessionGeneration = 1, pollingGeneration = null, stopped = false, timer, cursor = '';
    const settings = {value: ${JSON.stringify(settingsValue)}}, controller = {signal: null}, events = {value: []}, incoming = {value:null}, pollError = {value:''}, seen = new Set(), route = {name:'home'};
    let pollFailures = 0;
    ${source.slice(source.indexOf('async function pollEvents()'), source.indexOf('async function showPhone()'))}
    this.poll = pollEvents; this.switchUser = () => {sessionGeneration++}; this.eventCount = () => events.value.length;`, context);
  return { context, resolve: value => resolvePoll(value), reject: error => rejectPoll(error), delays, stats: () => ({ polls, scheduled }) };
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

test('logout clears the phone and rejects an in-flight session response', async () => {
  let resolveSession;
  const context = {
    convoxApi: { widgetSession: () => new Promise(resolve => { resolveSession = resolve; }) },
    clearTimeout() {},
    validWidgetUrl: () => true,
  };
  vm.createContext(context);
  vm.runInContext(`
    const ref = value => ({value});
    const loggedOut=ref(false), starting=ref(false), url=ref(''), phoneConfirmed=ref(true),
      error=ref(''), notice=ref(''), pollError=ref(''), settings=ref({enabled:true}),
      events=ref([{name:'private'}]), incoming=ref({}), selectedLead=ref('LEAD-1'), open=ref(true),
      preferManual=ref(false), manualLogin=ref(false), frameVersion=ref(0);
    const session={user:'agent'}, controller={signal:null}, seen=new Set(['old']);
    let sessionGeneration=1, stopped=false, cursor='old', timer, pollFailures=0;
    ${source.slice(source.indexOf('async function connect('), source.indexOf('async function callSelected('))}
    ${source.slice(source.indexOf('function portalLogout()'), source.indexOf('function warnBeforeLeaving('))}
    this.connect=connect; this.logout=portalLogout;
    this.state=()=>({loggedOut:loggedOut.value,url:url.value,events:events.value.length,starting:starting.value});
  `, context);
  const pending = context.connect();
  context.logout();
  resolveSession({url:'https://phone.example',mode:'sso'});
  await pending;
  assert.equal(context.state().loggedOut, true);
  assert.equal(context.state().url, '');
  assert.equal(context.state().events, 0);
  assert.equal(context.state().starting, false);
  await context.connect();
});

test('saved history polls even when callback ingestion is not configured', async () => {
 const s = setup({history_ready:true,callbacks_ready:false});
 const pending=s.context.poll();
 assert.equal(s.stats().polls,1);
 s.resolve({cursor:'next',events:[]}); await pending;
 assert.equal(s.stats().scheduled,1);
});

test('outage retries back off to one minute and recover to live update frequency', async () => {
 const s = setup();
 for (let i = 0; i < 4; i++) {
   const pending = s.context.poll();
   s.reject(new Error('Temporary outage'));
   await pending;
 }
 assert.deepEqual(s.delays, [15000, 30000, 60000, 60000]);
 const pending = s.context.poll();
 s.resolve({cursor:'recovered',events:[]});
 await pending;
 assert.equal(s.delays.at(-1), 5000);
});

test('authorization failures stop retries', async () => {
 for (const status of [401, 403]) {
   const s = setup();
   const pending = s.context.poll();
   s.reject(Object.assign(new Error('Access denied'), {status}));
   await pending;
   assert.equal(s.stats().scheduled, 0);
 }
});
