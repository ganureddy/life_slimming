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

test('legacy appointment editor uses backend choices, optimistic version checks and existing edit roles', async () => {
  const start = source.indexOf('  function openApptDetail(idx)');
  const end = source.indexOf('  function bookAppointment()', start);
  const fn = source.slice(start, end);
  async function editor(roles) {
    const calls = [], nodes = {}, lead = {leadId:'LEAD-1',clientName:'Client',status:'Booked',modified:'v1'};
    const element = () => ({isConnected:true,disabled:true,value:'',textContent:'',appendChild(){},addEventListener(_,handler){this.click=handler;}});
    const context = {APPOINTMENTS:[lead],LEADS:[{id:'LEAD-1',apptStatus:'Booked'}],currentRoles:()=>roles,
      frappe:{session:{user:'user@example.test'},call:async request=>{calls.push(request);return {message:request.method.endsWith('.options')?['Booked','Visited','Visited Booked']:{name:'LEAD-1',custom_appointment_status:request.args.status,modified:'v2'}};}},
      document:{getElementById:id=>nodes[id]||null,createElement:element},escapeHtml:String,escAttr:String,maskSpan:String,fmtDate:String,apptStatusPill:String,toast(){},closeModal(){},renderAppointmentList(){},
      openModal(_,html){if(html.includes('cc-apt-status-save'))for(const id of ['cc-apt-status-save','cc-apt-status','cc-apt-status-error'])nodes[id]=element();}};
    vm.createContext(context);vm.runInContext(fn+'\nopenApptDetail(0);',context);
    await new Promise(resolve=>setImmediate(resolve));return {calls,nodes,lead};
  }
  const agent=await editor(['Sales User']);assert.equal(agent.calls.length,0);assert.equal(agent.nodes['cc-apt-status-save'],undefined);
  const manager=await editor(['System Manager']);assert.equal(manager.calls[0].method,'life_slimming.api.cc_appointment_status.options');
  manager.nodes['cc-apt-status'].value='Visited';manager.nodes['cc-apt-status'].onchange();manager.nodes['cc-apt-status-save'].click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(manager.calls[1].method,'life_slimming.api.cc_appointment_status.update');
  assert.equal(manager.calls[1].args.expected_modified,'v1');assert.equal(manager.lead.status,'Visited');assert.equal(manager.lead.modified,'v2');
  assert(!source.includes('cc_set_visit_status'));assert(!source.includes('custom_visit_status'));assert(!source.includes('<th>Visit Status</th>'));
});
