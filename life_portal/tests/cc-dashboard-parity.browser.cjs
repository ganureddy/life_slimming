// Start Vite on :5175 and isolated Chrome on :9225. All business requests are mocked.
const WebSocket=require('../node_modules/ws');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const target=await(await fetch('http://127.0.0.1:9225/json/new?about:blank',{method:'PUT'})).json();
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
  if(request.url.includes('cc_get_leads.run')){
   const rows=args.query?[{...base,name:'HISTORY-1',lead_name:'History only',custom_cc_stage:'UNTOUCHED'}]:args.date_mode==='followup'?[due]:args.date_mode==='appointment'?[created[1]]:created;
   result={rows,total:rows.length,scoped_to_owner:false,contact_manager:true,truncated:partial};
   if(args.query==='Paged'){const start=Number(args.start||0);result={rows:Array.from({length:start?5:20},(_,i)=>({...base,name:'PAGE-'+(start+i+1),lead_name:'Page Lead '+(start+i+1),custom_cc_stage:'UNTOUCHED'})),more:!start};}
   if(failLoad&&!args.query)result={error:'Fixture load failed'};
  }
  if(request.url.includes('frappe.client.get_list'))result=args.filters?.designation?.[1]?.includes('Doctor')?[{name:'EMP-1',employee_name:'Test Doctor',branch:'Test Branch',designation:'Doctor',cell_number:'12345'}]:[];
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value};
 const wait=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,75))}throw Error('Timed out: '+expression+'\n'+await evaluate('document.body.innerText'))};
 const click=(selector,text)=>evaluate(`Array.from(document.querySelectorAll(${JSON.stringify(selector)})).find(el=>el.textContent.includes(${JSON.stringify(text)})).click()`);
 try{
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:5175/api/*'}]});
  for(const width of [1440,390]){
   await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
   await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/native/cc-dashboard'});
   await wait("document.querySelector('#dash-queue-list')?.textContent.includes('Created lead')");
   assert.equal(await evaluate("document.querySelectorAll('iframe').length"),0);
   assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true,'viewport overflow at '+width);
   assert.equal(await evaluate("Array.from(document.querySelectorAll('.stat-card')).find(el=>el.textContent.includes('No Response / Not Reachable')).querySelector('.sv').textContent"),'1');
   await click('.stat-card','No Response / Not Reachable');
   await wait("document.querySelector('dialog[open]')?.textContent.includes('Created lead')");
   assert.equal(await evaluate("document.querySelector('dialog[open]').textContent.includes('Older follow-up')"),false);
   await click('dialog[open] button','Close');
   await click('.stat-card','Converted ▾');
   await click('#dash-group-panel .stat-card','Created & Converted Today');
   await wait("document.querySelector('dialog[open]')?.textContent.includes('Converted lead')");
   await click('dialog[open] button','Close');
   if(width===1440){
    await evaluate("var input=document.querySelector('#global-search');input.value='History';input.dispatchEvent(new Event('input',{bubbles:true}))");
    await wait("document.querySelector('.search-results')?.textContent.includes('History only')");
    assert.ok(calls.some(call=>call.args.query==='History'&&!call.args.from_date));
    await evaluate("var input=document.querySelector('#global-search');input.value='';input.dispatchEvent(new Event('input',{bubbles:true}))");
   }
   await click('.cc-dashboard-vue .sidebar .nav-item','Doctor Directory');
   await wait("document.querySelector('#doctors-area')?.textContent.includes('Test Doctor')");
   assert.ok(await evaluate("document.querySelector('#doctors-area').textContent.includes('EMP-1')"));
   await click('.cc-dashboard-vue .sidebar .nav-item','Dashboard');
   await wait("document.querySelector('#dash-queue-list')?.textContent.includes('Created lead')");
   await click('.cc-dashboard-vue .sidebar .nav-item','Lead Follow-Up Form');
   await evaluate("var input=document.querySelector('.cc-date-toolbar input');input.value='Paged';input.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.cc-date-toolbar').requestSubmit()");
   await wait("document.querySelector('.cc-dashboard-vue main,.cc-dashboard-vue .main')?.textContent.includes('Page Lead 20')");
   await click('.cc-dashboard-vue .sidebar .nav-item','My Lead Queue');
   await wait("document.querySelectorAll('#page-my-leads article').length===20");
   await click('#page-my-leads .cc-pager button','Next');
   await wait("document.querySelector('#page-my-leads')?.textContent.includes('Page Lead 25')");
   assert.equal(await evaluate("document.querySelectorAll('#page-my-leads article').length"),5);
   await click('#page-my-leads .cc-pager button','Previous');
   await wait("document.querySelectorAll('#page-my-leads article').length===20");
   failLoad=true;await click('#cc-quick-range button','Today');
   await wait("document.querySelector('.cc-dashboard-vue [role=alert]')?.textContent.includes('Fixture load failed')");
   await click('.cc-dashboard-vue .sidebar .nav-item','Dashboard');
   assert.equal(await evaluate("Array.from(document.querySelectorAll('.stat-card')).find(el=>el.textContent.includes('Appointments ▾')).querySelector('.sv').textContent"),'0');
   assert.equal(await evaluate("document.querySelector('#dash-queue-list').textContent.includes('Great work')"),false);
   failLoad=false;await click('.cc-dashboard-vue [role=alert] button','Retry');
   await wait("document.querySelector('#dash-queue-list')?.textContent.includes('Created lead')");
   partial=true;await click('#cc-quick-range button','Today');
   await wait("document.querySelector('.cc-dashboard-vue [role=alert]')?.textContent.includes('lead limit')");
   await click('.cc-dashboard-vue .sidebar .nav-item','Reports');
   await wait("Array.from(document.querySelectorAll('.cc-card button')).some(b=>b.textContent.includes('CSV'))");
   assert.ok(await evaluate("Array.from(document.querySelectorAll('.cc-card button')).filter(b=>b.textContent.includes('CSV')).every(b=>b.disabled)"));
   partial=false;await click('#cc-quick-range button','Today');
   await wait("!document.querySelector('.cc-dashboard-vue > .cc-error') && !document.querySelector('.cc-dashboard-vue [role=alert]')");
   await click('.cc-dashboard-vue .sidebar .nav-item','Dashboard');
   fs.writeFileSync('/tmp/cc-parity-'+width+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
  }
  assert.deepEqual(errors,[]);console.log('CC parity browser checks passed: cohorts, drilldowns, permitted-history search, directory, desktop/mobile containment.');
 }finally{await send('Page.close');ws.close()}
})().catch(error=>{console.error(error);process.exit(1)});
