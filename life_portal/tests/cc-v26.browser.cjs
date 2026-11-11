// All ERP requests are intercepted. No live records are read or changed.
const WebSocket=require('../node_modules/ws');
const assert=require('node:assert/strict');
(async()=>{
const endpoint=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9230',baseUrl=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5178';
const target=await(await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json();
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));
let id=0;const jobs=new Map(),errors=[],calls=[];
const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++id,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id,method,params}));});
const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const lead={name:'LEAD1',first_name:'Test Client',lead_name:'Test Client',mobile_no:'9876543210',lead_owner:'Administrator',branch:'Ho CC',creation:today+' 09:00:00',modified:'v1',custom_cc_stage:'SUCCESS',custom_cc_sub_status:'Appointment Booked',custom_appointment_status:'Booked',custom_call_count:2};
const summary={milestone:'Appointment Missed',last_call_result:'No Response',next_action:'Rebook appointment',next_action_due:today+' 09:00:00',unreachable_streak:3,booked:1,missed:1,visited:0,owner:'Administrator'};
ws.on('message',async raw=>{const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);return;}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description);if(m.method!=='Fetch.requestPaused')return;
const {requestId,request}=m.params,args=JSON.parse(request.postData||'{}');calls.push({url:request.url,args});let result={};
if(request.url.includes('login_context'))result={authenticated:true};
if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'CC Tester',roles:['System Manager'],csrf_token:'test'};
if(request.url.includes('cc_get_leads.run'))result={rows:[lead],total:1,scoped_to_owner:false};
if(request.url.includes('frappe.client.get_list'))result=[];
if(request.url.includes('cc_attendance.snapshot'))result={employees:[{name:'EMP1',employee_name:'CC Tester',user_id:'Administrator'}],rows:[{name:'ATT1',employee:'EMP1',attendance_date:today,status:'Present',custom_check_in_time:'09:00:00'}]};
if(request.url.includes('cc_core.run')){
 result={ok:true};
 switch(args.action){
 case 'summary':result.leads={LEAD1:summary};break;
 case 'header':result={ok:true,summary,owner:'CC Tester',last_touch:today};break;
 case 'timeline':result.events=[{at:today,kind:'mobile call',to:'No Response',by:'CC Tester'}];break;
 case 'perm':result={ok:true,can_move:true,can_edit_perm:true,movers:['Administrator']};break;
 case 'agents':result={ok:true,agents:[{agent:'Administrator',name:'CC Tester',checked_in:true,open:10,overdue:2}],settings:{cap_on:1,cap_overdue:150,cap_open:1000,open_days:60}};break;
 case 'rules':result.rules=[{name:'New leads',rule_name:'New leads',rule_type:'Time-over New Lead',test_mode:1,enabled:1}];break;
 case 'bulk_meta':result={ok:true,sources:['Website'],branches:['Ho CC']};break;
 case 'dist_preview':result={ok:true,items:[{...summary,lead:'LEAD1'}],count:1};break;
 case 'dist_move':result={ok:true,batch:'TL-20261111120000',count:1};break;
 case 'dist_undo':result={ok:true,undone:1};break;
 case 'rule_save':result={ok:true,saved:1};break;
 case 'bulk_check':{const rows=JSON.parse(args.rows);result={ok:true,rows:rows.map((r,i)=>({...r,state:i?'invalid':'ready',errors:i?['Unknown branch.']:[],duplicate:''})),ready:1,invalid:Math.max(0,rows.length-1),skipped:0};break;}
 case 'bulk_create':result={ok:true,created:1,results:[{row:2,ok:1,lead:'LEAD-NEW',owner:'CC Tester'}]};break;
 case 'rank':result.rows=[{agent:'Administrator',name:'CC Tester',rank:1,conv:50,showup:60,score:10}];break;
 case 'report':result={ok:true,funnel:{leads:1,joined:0},agents:[{agent:'Administrator',name:'CC Tester',leads:1,paid:0}],last_call_mix:{'No Response':1},joined:[],moves:[]};break;
 }
}
await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')});
});
const evaluate=async expression=>(await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result?.value;
const wait=async exp=>{for(let i=0;i<120;i++){if(await evaluate(exp))return;await new Promise(r=>setTimeout(r,75));}throw Error('Timed out: '+exp+'\n'+await evaluate('document.body.innerText'));};
const click=async(selector,text)=>{await wait(`(()=>{const el=[...document.querySelectorAll(${JSON.stringify(selector)})].find(e=>e.textContent.includes(${JSON.stringify(text)}));if(!el||el.disabled)return false;el.click();return true;})()`);};
try{
await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:baseUrl+'/api/*'}]});
for(const width of [1440,390]){
 await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:baseUrl+'/life_portal/native/cc-dashboard'});
 await wait("document.querySelector('.cc-recovery-tiles')?.textContent.includes('No-show recovery')");
 await wait("document.querySelector('.cc-recovery-tiles strong')?.textContent==='1'");
 assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'dashboard overflow '+width);
 assert.equal(await evaluate("document.querySelector('#cc-reports-link')"),null);
 if(width===1440){
  if(await evaluate("document.querySelector('.cc-menu-pin').getAttribute('aria-pressed')==='true'"))await click('.cc-menu-pin','Unpin menu');
  await new Promise(r=>setTimeout(r,10500));await wait("!!document.querySelector('.cc-menu-tab')");
  await click('.cc-menu-tab','MENU');await click('.cc-menu-pin','Pin menu');
  await new Promise(r=>setTimeout(r,10500));
  assert.equal(await evaluate("document.querySelector('.sidebar').classList.contains('collapsed')"),false,'pinned menu must stay open');
 }
 await click('.sidebar .nav-item','Lead Distribution');
 await wait("document.querySelector('.cc-distribution')?.textContent.includes('Current owners')");
 await click('.cc-distribution button','Preview leads');
 await wait("document.querySelector('.cc-distribution')?.textContent.includes('1 eligible leads')");
 await click('.cc-distribution button','Choose receiving agents');
 await evaluate("const s=[...document.querySelectorAll('.distribution-fields label')].find(e=>e.textContent.startsWith('Receiving agents')).querySelector('select');s.options[0].selected=true;s.dispatchEvent(new Event('change',{bubbles:true}));");
 await click('.cc-distribution button','Move 1 selected');
 await wait("document.querySelector('.cc-distribution')?.textContent.includes('1 leads moved.')");
 await click('.cc-distribution button','Undo last batch');
 await wait("document.querySelector('.cc-distribution')?.textContent.includes('1 leads moved back.')");
 await click('.distribution-tabs button','Auto Rules');
 await wait("document.querySelector('.cc-distribution')?.textContent.includes('New leads')");
 assert.equal(await evaluate("[...document.querySelectorAll('label')].find(e=>e.textContent.trim()==='Test mode').querySelector('input').checked"),true);
 await evaluate("const input=[...document.querySelectorAll('.distribution-fields label')].find(el=>el.textContent.startsWith('Rule name')).querySelector('input');input.value='Review rule';input.dispatchEvent(new Event('input',{bubbles:true}));");
 const beforeRules=calls.filter(c=>c.args.action==='rule_save').length;
 await click('.cc-distribution button','Review rule');await wait("document.querySelector('.rule-applied')?.textContent.includes('What is applied')");
 assert.equal(calls.filter(c=>c.args.action==='rule_save').length,beforeRules,'review must not save');
 await click('.rule-applied button','Accept & Apply');await wait("document.querySelector('.cc-distribution')?.textContent.includes('Rule saved')");
 await click('.distribution-tabs button','Bulk Upload');
 const pastedCsv=['name,mobile,source,branch','A,9876543210,Website,Ho CC','B,9876543211,Website,Unknown'].join('\n');
 await evaluate(`const input=document.querySelector('textarea[placeholder="Include the header row"]');input.value=${JSON.stringify(pastedCsv)};input.dispatchEvent(new Event('input',{bubbles:true}));`);
 await click('.cc-distribution button','Read pasted rows');await click('.cc-distribution button','Check every row');
 await wait("document.querySelector('.cc-distribution')?.textContent.includes('Unknown branch.')");
 assert.equal(await evaluate("[...document.querySelectorAll('.cc-distribution button')].find(b=>b.textContent.startsWith('Create ')).disabled"),true);
 await click('.distribution-tabs button','Agents & Priority');await click('.cc-distribution button','Calculate ranking');
 await wait("document.querySelector('.cc-distribution')?.textContent.includes('Conversion %')");
 assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'distribution overflow '+width);
 await click('.sidebar .nav-item','Agent 360');
 await wait("document.body.textContent.includes('Agent 360 · Lead Journey')&&document.body.textContent.includes('CC Tester')");
 assert.equal(await evaluate("document.querySelectorAll('iframe').length"),0,'report must load only on request');
 await click('.sidebar .nav-item','Staff Attendance');
 await wait("document.querySelector('table')?.textContent.includes('Present')");
 await click('.sidebar .nav-item','My Lead Queue');await wait("document.querySelector('#my-leads-list')?.textContent.includes('Unreachable 3×')");
 await click('#my-leads-list button','Call & Update');
 await wait("document.querySelector('.cc-journey')?.textContent.includes('Rebook appointment')");
 await click('.cc-journey button','Timeline');await wait("document.querySelector('.cc-journey')?.textContent.includes('mobile call')");
 assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'follow-up overflow '+width);
}
assert.deepEqual(errors,[]);console.log('V26 browser checks passed: desktop/mobile recovery, distribution preview/move/undo, rules, ranking, lazy Agent 360, attendance and journey timeline.');
}finally{await send('Page.close');ws.close();}
})().catch(e=>{console.error(e);process.exit(1);});
