// Use the configured local Vite and isolated Chrome endpoints. All business requests are mocked.
const WebSocket=require('../node_modules/ws');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const endpoint=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9230';
 const previewBase=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5178';
 const target=await(await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));
 let failLoad=false,partial=false;let id=0;const jobs=new Map(),errors=[],calls=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++id,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id,method,params}));});
 const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const base={mobile_no:'9876543210',lead_owner:'agent@example.com',branch:'Test Branch',creation:today+' 09:00:00',custom_call_count:1};
 const created=[{...base,name:'NEW-1',lead_name:'Created lead',custom_cc_stage:'FOLLOW-UP',custom_cc_sub_status:'No Response'},{...base,name:'NEW-2',lead_name:'Converted lead',custom_cc_stage:'SUCCESS',status:'Converted',custom_appointment_status:'Visited Booked',custom_appointment_date_and_time:today+' 10:00:00'}];
 const due={...base,name:'OLD-1',lead_name:'Older follow-up',creation:'2025-01-01 09:00:00',custom_cc_stage:'FOLLOW-UP',custom_cc_sub_status:'No Response',custom_next_followup_date:today};
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id)}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description);
  if(m.method!=='Fetch.requestPaused')return;
  const {requestId,request}=m.params,args=JSON.parse(request.postData||'{}');calls.push({url:request.url,args});let result={};
  if(request.url.includes('login_context'))result={authenticated:true};
  if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'Parity Tester',roles:['System Manager'],csrf_token:'test'};
  if(request.url.includes('cc_appointments.bootstrap'))result={branches:[],leads:[],staff:[],today,timezone:'Asia/Kolkata'};
  if(request.url.includes('life_cc_core')||request.url.includes('cc_core.run'))result={ok:true,leads:{}};
  if((request.url.includes('life_cc_core')||request.url.includes('cc_core.run'))&&args.action==='header')result={ok:true,owner:'Assigned Agent',received_this:today,summary:{milestone:'Interested',booked:0,missed:0,visited:0,last_call_result:'No Response',next_action:'Call back',next_action_due:today+' 10:00:00'}};
  if(request.url.includes('cc_get_leads.run')){
   const rows=args.query?[{...base,name:'HISTORY-1',lead_name:'History only',custom_cc_stage:'UNTOUCHED'}]:args.date_mode==='followup'?[due]:args.date_mode==='appointment'?[created[1]]:created;
   result={rows,total:rows.length,scoped_to_owner:false,contact_manager:true,truncated:partial};
   if(args.detail)result={rows:[{...created[0],name:args.query,first_name:'Created lead',lead_owner_name:'Assigned Agent',source:'Website',city:'Hyderabad',custom_treatment_interests:'Slimming'}],contact_manager:true};
   if(args.query==='Paged'){const start=Number(args.start||0);result={rows:Array.from({length:start?5:20},(_,i)=>({...base,name:'PAGE-'+(start+i+1),lead_name:'Page Lead '+(start+i+1),custom_cc_stage:'UNTOUCHED'})),more:!start};}
   if(failLoad&&!args.query)result={error:'Fixture load failed'};
  }
  if(request.url.includes('frappe.client.get_list')){
   if(args.doctype==='Lead Source')result=['Website','Meta Chat','Inbound Call'].map(name=>({name}));
   else if(args.doctype==='Branch')result=[{name:'Test Branch'}];
   else if(args.doctype==='Healthcare Service Unit')result=[{name:'Slimming'}];
   else result=args.filters?.designation?.[1]?.includes('Doctor')?[{name:'EMP-1',employee_name:'Test Doctor',branch:'Test Branch',designation:'Doctor',cell_number:'12345'}]:[];
  }
  if(request.url.includes('lead_assignment_configuration.run'))result=args.action==='save_agent'?{saved:true}:{is_manager:true,settings:{assignment_mode:'Round Robin',start_time:'09:00',end_time:'18:00'},source_options:['Website','Meta Chat','Inbound Call'],agents:[
    {agent:'agent@example.com',employee_name:'Active CC Agent',employee_status:'Active',designation:'Business Executive',user_enabled:1,allowed_sources:['Website'],auto_enabled:1,max_per_day:15,share_weight:1},
    {agent:'left@example.com',employee_name:'Former Agent',employee_status:'Left',designation:'Business Executive',user_enabled:1},
    {agent:'doctor@example.com',employee_name:'Other Department',employee_status:'Active',designation:'Doctor',user_enabled:1},
    {agent:'disabled@example.com',employee_name:'Disabled Agent',employee_status:'Active',designation:'Business Executive',user_enabled:0},
  ]};
  if(request.url.includes('convox.lead_history'))result={lead_id:args.lead_id,lead_name:'Created lead',mobile_number:'9876543210',total_calls:1,total_events:1,start:0,has_more:false,fields:[{key:'call_status',label:'Call status'}],events:[{name:'CALL-1',call_reference:'REF-1',call_status:'Connected',call_datetime:today+' 10:00:00',call_duration:60}]};
  if(request.url.includes('cc_create_lead.run'))result={duplicate:{name:'NEW-1',lead_name:'Existing client',mobile_no:'9876543210'}};

  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value};
 const wait=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,75))}throw Error('Timed out: '+expression+'\n'+await evaluate('document.body.innerText + \"\\nDETAILS: \" + Array.from(document.querySelectorAll(\"code\")).map(e=>e.textContent).join(\"\\n\")'))};
 const click=async(selector,text)=>{
  if(selector.includes('.portal > .sidebar')&&text==='Dashboard')text='CC Dashboard';
  if(selector.includes('.portal > .sidebar')&&text==='Reports')text='CC Reports';
  const match=`Array.from(document.querySelectorAll(${JSON.stringify(selector)})).find(el=>el.textContent.toLowerCase().includes(${JSON.stringify(text)}.toLowerCase()))`;
  await wait(`(()=>{const element=${match};if(!element || element.disabled)return false;element.click();return true;})()`);
 };
 try{
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:previewBase+'/api/*'}]});
  for(const width of [1440,390]){
   const documentStart=calls.length;
   await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
   await send('Page.navigate',{url:previewBase+(width===1440?'/life_portal/leads':'/life_portal/native/cc-dashboard')});
   await wait("document.querySelector('#dash-queue-list')?.textContent.includes('Created lead')");
   assert.equal(await evaluate("document.querySelectorAll('iframe').length"),0);
   assert.equal(await evaluate("getComputedStyle(document.querySelector('.portal > .sidebar')).display!=='none'"),true,'CC menu must be visible on screen');
   assert.equal(await evaluate("getComputedStyle(document.querySelector('.cc-dashboard-vue .hdr')).display!=='none'"),true,'CC header must be visible on screen');
   assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true,'viewport overflow at '+width);
   assert.equal(await evaluate("Array.from(document.querySelectorAll('.stat-card')).find(el=>el.textContent.includes('NOT RESPONDING / NOT REACHABLE')).querySelector('.sv').textContent"),'1');
   await click('.stat-card','NOT RESPONDING / NOT REACHABLE');
   await wait("document.querySelector('dialog[open]')?.textContent.includes('Created lead')");
   assert.equal(await evaluate("document.querySelector('dialog[open]').textContent.includes('Older follow-up')"),false);
   await click('dialog[open] button','Close');
   await click('.stat-card','CONVERTED ▾');
   await click('#dash-group-panel .stat-card','Created & Converted Today');
   await wait("document.querySelector('dialog[open]')?.textContent.includes('Converted lead')");
   await click('dialog[open] button','Close');
   if(width===1440){
    await evaluate("var input=document.querySelector('#global-search');input.value='History';input.dispatchEvent(new Event('input',{bubbles:true}))");
    await wait("document.querySelector('.search-results')?.textContent.includes('History only')");
    assert.ok(calls.some(call=>call.args.query==='History'&&!call.args.from_date));
    await evaluate("var input=document.querySelector('#global-search');input.value='';input.dispatchEvent(new Event('input',{bubbles:true}))");
   }
   const beforeTabSwitch=calls.filter(call=>call.url.includes('cc_get_leads.run')&&!call.args.query).length;
   await click('.portal > .sidebar .nav-item','My Lead Queue');
   await wait("document.querySelector('#page-my-leads')?.textContent.includes('Created lead')");
   await wait("location.pathname.endsWith('/leads/queue') && !new URLSearchParams(location.search).has('view')");
   assert.equal(await evaluate("document.querySelector('.portal > .sidebar [aria-current=page]')?.getAttribute('aria-label')"),'My Lead Queue');
   await click('.portal > .sidebar .nav-item','Dashboard');
   await wait("document.querySelector('#dash-queue-list')?.textContent.includes('Created lead')");
   assert.equal(calls.filter(call=>call.url.includes('cc_get_leads.run')&&!call.args.query).length,beforeTabSwitch,'switching shared tabs reuses the loaded lead cohorts');
   await click('.portal > .sidebar .nav-item','Doctor Directory');
   await wait("document.querySelector('#doctors-area')?.textContent.includes('Test Doctor')");
   assert.ok(await evaluate("document.querySelector('#doctors-area').textContent.includes('EMP-1')"));
   await click('.portal > .sidebar .nav-item','Dashboard');
   await wait("document.querySelector('#dash-queue-list')?.textContent.includes('Created lead')");
   await click('.portal > .sidebar .nav-item','Lead Follow-Up Form');
   await wait("!!document.querySelector('.crm-lead-search-row input')");
   assert.equal(await evaluate("location.pathname.endsWith('/leads/follow-up')"),true);
   assert.equal(await evaluate("document.querySelector('.crm-followup-empty').textContent.includes('No lead selected')"),true);
   assert.ok(await evaluate("document.querySelector('.crm-lead-search-row button').getBoundingClientRect().height>=36"));
   fs.writeFileSync('/tmp/cc-followup-entry-'+width+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));

   await evaluate("var input=document.querySelector('.crm-lead-search-row input');input.value='Paged';input.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.crm-lead-search-row').requestSubmit()");
   await wait("document.querySelector('.cc-dashboard-vue main,.cc-dashboard-vue .main')?.textContent.includes('Page Lead 20')");
   await click('.portal > .sidebar .nav-item','My Lead Queue');
   await wait("document.querySelectorAll('#page-my-leads article').length===20");
   await click('#page-my-leads .cc-pager button','Next');
   await wait("document.querySelector('#page-my-leads')?.textContent.includes('Page Lead 25')");
   assert.equal(await evaluate("document.querySelectorAll('#page-my-leads article').length"),5);
   await click('#page-my-leads .cc-pager button','Previous');
   await wait("document.querySelectorAll('#page-my-leads article').length===20");
   failLoad=true;await click('#cc-quick-range button','Today');
   await wait("document.querySelector('.cc-dashboard-vue [role=alert]')?.textContent.includes('Fixture load failed')");
   await click('.portal > .sidebar .nav-item','Dashboard');
   assert.equal(await evaluate("Array.from(document.querySelectorAll('.stat-card')).find(el=>el.textContent.toLowerCase().includes('appointments')).querySelector('.sv').textContent"),'0');
   assert.equal(await evaluate("document.querySelector('#dash-queue-list').textContent.includes('Great work')"),false);
   failLoad=false;await click('.cc-dashboard-vue [role=alert] button','Retry');
   await wait("document.querySelector('#dash-queue-list')?.textContent.includes('Created lead')");
   partial=true;await click('#cc-quick-range button','Today');
   await wait("document.querySelector('.cc-dashboard-vue [role=alert]')?.textContent.includes('lead limit')");
   await click('.portal > .sidebar .nav-item','Reports');
   await wait("Array.from(document.querySelectorAll('.cc-card button')).some(b=>b.textContent.includes('CSV'))");
   assert.ok(await evaluate("Array.from(document.querySelectorAll('.cc-card button')).filter(b=>b.textContent.includes('CSV')).every(b=>b.disabled)"));
   partial=false;await click('.portal > .sidebar .nav-item','Dashboard');await click('#cc-quick-range button','Today');
   await wait("!document.querySelector('.cc-dashboard-vue > .cc-error') && !document.querySelector('.cc-dashboard-vue [role=alert]')");
   await click('.portal > .sidebar .nav-item','Dashboard');
   await click('#dash-queue-list .wf-q-btn','Call & Update');
   await wait("document.querySelector('#wf-shell')?.getBoundingClientRect().height>0 && document.querySelector('#wf-panel .lcx-title')?.textContent.includes('INTERESTED')");
   assert.equal(await evaluate("document.querySelector('#page-followup > .cc-journey')===null && !!document.querySelector('#wf-panel .cc-journey')"),true,'journey belongs inside the legacy disposition panel');
   assert.equal(await evaluate("getComputedStyle(document.querySelector('#followup-lead-banner')).display"),'grid','legacy client header uses the compact grid');
   assert.equal(await evaluate("document.querySelector('#call-timer').textContent"),'No call requested');
   assert.equal(await evaluate("document.querySelector('#page-followup > .cc-appointment-status')===null"),true,'follow-up has no duplicate appointment editor');
   assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true,'follow-up overflow at '+width);
   await evaluate("window.scrollTo(0,0)");
   fs.writeFileSync('/tmp/cc-followup-'+width+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
   await click('#wf-panel .oct-inline button','Connected');
   await click('#wf-panel .wf-opts button','Callback: Scheduled');
   await wait("!!document.querySelector('#ff-next-date') && !!document.querySelector('#ff-next-time')");
   assert.equal(await evaluate("document.querySelector('#ff-next-time').value"),'10:00');
   assert.equal(await evaluate("document.querySelector('#ff-next-priority').value"),'Normal');
   await evaluate("var time=document.querySelector('#ff-next-time');time.value='14:30';time.dispatchEvent(new Event('input',{bubbles:true}))");
   assert.equal(await evaluate("document.querySelector('#ff-next-time').value"),'14:30');
   await click('#wf-check-update','Check update');
   await wait("document.querySelector('.cc-worksheet-toast')?.textContent.includes('No record changed')");
   await click('#wf-panel .wf-opts button','Appointment Booked');
   await wait("document.querySelector('#wf-actions .cc-booking-next')?.textContent.includes('Create Appointment')");

   assert.equal(calls.slice(documentStart).filter(call=>call.url.includes('convox.lead_history')).length,0,'closed call details must not fetch hidden history');
   const followupUrl=await evaluate('location.href');
   await click('.cc-lead-history-actions button','ConVox');
   await wait("document.querySelector('.convox-history-dialog[open] .call-event')?.textContent.includes('Connected')");
   assert.equal(await evaluate('location.href'),followupUrl,'ConVox history stays on the lead screen');
   assert.ok(await evaluate("getComputedStyle(document.querySelector('.convox-history-dialog')).fontFamily.includes('Poppins')"));
   fs.writeFileSync('/tmp/crm-history-'+width+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
   const historyCalls=calls.filter(call=>call.url.includes('convox.lead_history')).length;
   await click('.history-close','Close');
   await click('.cc-lead-history-actions button','ConVox');
   await wait("!!document.querySelector('.convox-history-dialog[open]')");
   assert.equal(calls.filter(call=>call.url.includes('convox.lead_history')).length,historyCalls,'reopening the same lead history reuses loaded events');
   await click('.history-close','Close');
   await click('.portal > .sidebar .nav-item','Create Lead');
   await wait("document.querySelector('.crm-create-form select[name=source]')?.options.length===4");
   assert.equal(await evaluate("document.querySelectorAll('dialog[open]').length"),0,'lead creation is a full page');
   assert.equal(await evaluate("document.querySelector('.crm-create-form').textContent.includes('Other Department')"),false);
   assert.equal(await evaluate("document.querySelector('.crm-create-form').textContent.includes('Former Agent')"),false);
   assert.equal(await evaluate("document.querySelector('.crm-create-form').textContent.includes('Disabled Agent')"),false);
   assert.ok(await evaluate("getComputedStyle(document.querySelector('.crm-create-form input')).fontFamily.includes('Poppins')"));
   assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'create lead overflow '+width);
   await evaluate('window.scrollTo(0,0)');
   fs.writeFileSync('/tmp/crm-create-'+width+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
   await evaluate("for(const [name,value] of Object.entries({first_name:'New Client',mobile_no:'9876543210',source:'Website',branch:'Test Branch'})){const el=document.querySelector('.crm-create-form [name='+name+']');el.value=value;el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}));}document.querySelector('.crm-create-form').requestSubmit()");
   await wait("document.querySelector('.crm-duplicate-notice')?.textContent.includes('Existing client')");
   await click('.portal > .sidebar .nav-item','Assign Leads');
   await wait("document.querySelector('.cc-assign-sticky select')?.options.length===2");
   assert.deepEqual(await evaluate("[...document.querySelector('.cc-assign-sticky select').options].map(option=>option.value)"),['','agent@example.com']);
   await click('.portal > .sidebar .nav-item','TL Control Panel');
   await wait("document.querySelectorAll('.assignment-agent').length===1");
   await click('.assignment-sources summary','sources selected');
   await evaluate("var q=document.querySelector('.assignment-sources input[type=search]');q.value='Meta';q.dispatchEvent(new Event('input',{bubbles:true}))");
   await wait("document.querySelectorAll('.assignment-sources .crm-source-list label').length===1");
   assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'source dropdown overflow '+width);
   await evaluate("document.querySelector('.assignment-agent').scrollIntoView({block:'center'})");
   fs.writeFileSync('/tmp/crm-sources-'+width+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
   await click('.assignment-sources .crm-source-list label','Meta Chat');
   await wait("document.querySelector('.assignment-sources .crm-selected-sources')?.textContent.includes('Meta Chat')");
   await click('.assignment-sources summary','sources selected');
   await click('.assignment-agent button','Save changes');
   await wait("document.querySelector('.assignment-agent footer')?.textContent.includes('Saved')");
   assert.ok(calls.some(call=>call.args.action==='save_agent'&&call.args.lead_sources==='Website, Meta Chat'));
   assert.equal(calls.slice(documentStart).filter(call=>call.url.includes('lead_assignment_configuration.run')&&call.args.action==='get').length,1,'follow-up/create/assignment/TL share one configuration request');
   assert.equal(calls.slice(documentStart).filter(call=>call.url.includes('frappe.client.get_list')&&call.args.doctype==='Lead Source').length,1,'follow-up and create lead share one source-options request');
   assert.equal(calls.slice(documentStart).some(call=>call.args.doctype==='User'),false,'assignment must not fetch the full user list');
   assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'TL control overflow '+width);
   await evaluate('window.scrollTo(0,0)');
   fs.writeFileSync('/tmp/crm-tl-'+width+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
   assert.equal(await evaluate("document.querySelector('.portal > .sidebar [aria-label=\"Staff Attendance\"]')===null && document.querySelector('.portal > .sidebar [aria-label=\"ConVox History\"]')===null && document.querySelector('.portal > .sidebar [aria-label=\"Campaigns\"]')===null"),true,'removed CRM tabs are absent');
   await click('.portal > .sidebar .nav-item','Dashboard');
   fs.writeFileSync('/tmp/cc-parity-'+width+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
  }
  assert.equal(await evaluate("document.querySelector('.portal > .sidebar [href*=\"view=appointments\"]')===null"),true,'only Create Appointment remains');
  assert.equal(await evaluate("document.querySelector('.portal > .sidebar [aria-label=\"Agent 360\"]').getAttribute('href').includes('/ccvisit')"),true,'Agent 360 opens the branch visit report');
  await send('Page.navigate',{url:previewBase+'/life_portal/leads?view=appointments&lead=NEW-1'});
  await wait("location.pathname.endsWith('/cc-appointments') && new URLSearchParams(location.search).get('lead')==='NEW-1' && document.body.textContent.includes('CC Appointment Scheduler')");
  assert.equal(await evaluate("document.querySelector('.page-render-error')===null"),true);
  await click('.portal > .sidebar .nav-item','Dashboard');
  for(const [label,selector] of [['Call Scripts','#scripts-area'],['FAQ / Knowledge Base','#faq-area'],['Treatment Guide','#treatments-area'],['Objection Handling','#objections-area'],['Branch Directory','#branches-area']]){
   await click('.portal > .sidebar .nav-item',label);
   await wait(`document.querySelector('${selector}')?.getBoundingClientRect().height>0`);
  }
  assert.equal(await evaluate("document.querySelectorAll('.cc-dashboard-vue .sidebar').length"),0,'CC navigation lives in the main CRM sidebar');
  const beforeDirectoryLink=calls.filter(call=>call.url.includes('cc_get_leads.run')).length;
  await send('Page.navigate',{url:previewBase+'/life_portal/leads?view=doctors'});
  await wait("document.querySelector('#doctors-area')?.textContent.includes('Test Doctor') && document.querySelector('#doctors-area').getBoundingClientRect().height>0");
  assert.equal(calls.filter(call=>call.url.includes('cc_get_leads.run')).length,beforeDirectoryLink,'directory deep link does not fetch unrelated leads');
  assert.deepEqual(errors,[]);console.log('CC parity browser checks passed: cohorts, drilldowns, permitted-history search, directory, desktop/mobile containment.');
 }finally{await send('Page.close');ws.close()}
})().catch(error=>{console.error(error);process.exit(1)});
