const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const page = JSON.parse(fs.readFileSync(require('node:path').join(__dirname, '../../life_slimming/portal_pages/cc-new-dashboard-bhuvan-oct2.json'), 'utf8'));
const source = page.javascript;

function collect(lead, state) {
  const context = {wfState: state};
  vm.createContext(context);
  const mapping = source.match(/const SUBSTATUS_TO_STAGE\s*=\s*\{[\s\S]*?\n  \};/)[0];
  const fn = source.split('\n').find(line => line.startsWith('  function wfCollect('));
  vm.runInContext(`${mapping}\nconst WF={APPT_NR:'Appointment no response',BADNUM:['Invalid Number','Not in Service']};\nfunction wfIn(list, value){return list.includes(value);}\n${fn}`, context);
  context.wfCollect(lead);
}

test('legacy script parses', () => { new vm.Script(source); });
test('latest failed outcome replaces an earlier connected or failed status', () => {
  for (const previous of ['Very Positive', 'Callback: Scheduled', 'No Response', 'Appointment Booked']) {
    for (const reason of ['No Response', 'Not Reachable', 'Switch OFF', 'Call Disconnected', 'Appointment no response', 'Invalid Number']) {
      const lead = {subStatus: previous, wfSavedStatus: previous, status: 'SUCCESS', wfSavedStage: 'SUCCESS'};
      collect(lead, {result: 'Not Connected', reason});
      assert.equal(lead.subStatus, reason);
      assert.equal(lead.status, reason === 'Invalid Number' ? 'INVALID' : 'FOLLOW-UP');
    }
  }
});
test('connected outcome replaces a previous failed outcome', () => {
  const lead = {subStatus: 'No Response', wfSavedStatus: 'No Response', status: 'FOLLOW-UP'};
  collect(lead, {result: 'Connected', next: 'Very Positive'});
  assert.equal(lead.subStatus, 'Very Positive');
  assert.equal(lead.status, 'FOLLOW-UP');
});
test('reopening does not restore a historical connected outcome', () => {
  assert.ok(!source.includes('const prior=raw.workflow_hint?.prior_connected'));
  assert.ok(!source.includes('pipeline stays unchanged'));
});
