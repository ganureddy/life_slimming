// All ERP requests are intercepted. No live records are read or changed.
const WebSocket=require('../node_modules/ws');
const assert=require('node:assert/strict');
(async()=>{
const endpoint=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9230',baseUrl=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5178';
const target=await(await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json();
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));
let partial=false,fail=false;let id=0;const jobs=new Map(),errors=[],calls=[];
const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++id,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id,method,params}));});
const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const lead={name:'LEAD1',first_name:'Test Client',lead_name:'Test Client',mobile_no:'9876543210',lead_owner:'Administrator',branch:'Ho CC',creation:today+' 09:00:00',modified:'v1',custom_cc_stage:'SUCCESS',custom_cc_sub_status:'Appointment Booked',custom_appointment_status:'Booked',custom_appointment_date_and_time:today+' 10:00:00',custom_call_count:2};
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
 case 'rank':result.rows=[{agent:'Administrator',name:'CC Tester',rank:1,conv:50,showup:60,score:10}];break;
 case 'report':result={ok:true,funnel:{leads:1,joined:0},agents:[{agent:'Administrator',name:'CC Tester',leads:1,paid:0}],last_call_mix:{'No Response':1},joined:[],moves:[]};break;
 }
}

if(request.url.includes('life_cc_agent_marketing_data.run'))result=args.view==='calendar'?{days:[{day:today,branch:'Ho CC',lead_owner:'Administrator',custom_appointment_status:'Booked',count:1}]}:args.view==='appointments'?(fail?{error:'Report fixture failed'}:{rows:[lead],total:partial?10001:1,truncated:partial,restricted_to_owner:false}):{ranking_rows:[lead],rows:[{...lead,source:'Website'}],agent_report_summary:{counts:{appointments:1,visited:0,booked:0}},cc_invoice_report_summary:{rows:[{invoice:'INV1',branch:'Ho CC',lead_owner:'Administrator',lead_name:'Test Client',with_gst:100,paid:60,balance:40}],totals:{invoice_count:1,with_gst:100,paid:60,balance:40}},financial_events:[]};
if(request.url.includes('cc_report_activity.run'))result={rows:[{agent:'Administrator',name:'CC Tester',convox:2,mobile:1,answered:2,talk:180,updates:1,idle_minutes:20,updated_no_call:0,talked_no_update:1,dispositions:{Interested:2},events:[{at:today+' 10:00:00',channel:'convox',lead:'LEAD1',status:'Answered',talk:120}]}],timeline_available:true,warnings:[]};
if(request.url.includes('cc_report_activity.changes'))result={token:'v1'};
if(request.url.includes('life_cc_nofu_v1'))result={days:30,buckets:[{days:30,n:1}],statuses:[{status:'No Response',n:1}],agents:[{agent:'Administrator',n:1}],total:1,rows:[{name:'LEAD1',lead_name:'Dormant client',ph4:'3210',owner:'Administrator',sub:'No Response',last:'2026-09-01'}]};

if(request.url.includes('cc_report_history.history'))result={rows:args.kind==='updates'?[{id:'V1',at:today+' 10:00:00',agent_name:'CC Tester',lead:'LEAD1',changes:[{field:'custom_cc_sub_status',before:'Lead',after:'Interested'}]}]:[{id:'CALL-'+(Number(args.start||0)+1),at:today+' 10:00:00',agent:'Administrator',agent_name:'CC Tester',lead:'LEAD1',phone:'••••3210',direction:'Outbound',status:'Answered',duration:120,disposition:'Interested'}],has_more:!args.start,start:Number(args.start||0),limit:30};
if(request.url.includes('cc_report_history.recording'))result={url:''};
await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')});
});
const evaluate=async expression=>(await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result?.value;
const wait=async exp=>{for(let i=0;i<120;i++){if(await evaluate(exp))return;await new Promise(r=>setTimeout(r,75));}throw Error('Timed out: '+exp+'\n'+await evaluate('document.body.innerText'));};
const click=async(selector,text)=>{await wait(`(()=>{const el=[...document.querySelectorAll(${JSON.stringify(selector)})].find(e=>e.textContent.includes(${JSON.stringify(text)}));if(!el||el.disabled)return false;el.click();return true;})()`);};
try{
await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:baseUrl+'/api/*'}]});
for(const width of [1440,390]){
 await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:baseUrl+'/life_portal/native/cc-visit-report'});
 await wait("document.querySelector('.cc-report-summary')?.textContent.includes('Ho CC')");
 await wait("document.querySelector('.cc-month-strip')?.textContent.includes('Appointments')");
 assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'report overflow '+width);
 assert.equal(await evaluate("document.querySelectorAll('.cc-report-tabs button').length"),6);
 assert.equal(calls.filter(c=>c.url.includes('life_cc_agent_marketing_data')&&!c.args.view).length,0,'financial data must stay lazy');
 await click('.cc-report-summary tbody button','1');
 await wait("document.querySelector('dialog[open]')?.textContent.includes('Test Client')");
 assert.equal(await evaluate("document.querySelector('dialog[open]').textContent.includes('9876543210')"),false);
 await click('dialog[open] button','Close');
 await click('.cc-report-summary button','CC Agent-wise');
 await wait("document.querySelector('.cc-report-summary')?.textContent.includes('Administrator')");
 await click('.cc-report-header-actions button','Today’s appointments');
 await wait("document.querySelector('dialog[open]')?.textContent.includes('Test Client')");
 await click('dialog[open] button','Close appointments');
 await click('.cc-report-header-actions button','Share preview');
 await wait("document.querySelector('dialog[open] textarea')?.value.includes('LIFE CC REPORT')");
 await click('dialog[open] button','Close');
 await click('.cc-report-tabs button','Agent 360');
 await wait("document.body.textContent.includes('ConVox calls')&&document.body.textContent.includes('CC Tester')");
 assert.equal(calls.filter(c=>c.url.includes('cc_report_history.')).length,0,'history and recordings must not load with summary');
 await click('.cc-history-card','convox');
 await wait("document.querySelector('.cc-history-dialog[open]')?.textContent.includes('••••3210')");
 assert.equal(await evaluate("document.querySelector('.cc-history-dialog').textContent.includes('9876543210')"),false);
 await click('.cc-history-dialog footer button','Next');
 await wait("document.querySelector('.cc-history-dialog footer')?.textContent.includes('31')");
 await click('.cc-history-dialog nav button','CC History');
 await wait("document.querySelector('.cc-history-dialog tbody')?.textContent.includes('Interested')");
 await click('.cc-history-dialog tbody button','Play');
 await wait("document.querySelector('.cc-history-dialog')?.textContent.includes('Recording unavailable')");
 await click('.cc-history-dialog nav button','Lead Updates');
 await wait("document.querySelector('.cc-history-dialog')?.textContent.includes('custom_cc_sub_status')");
 await click('.cc-history-dialog header button','Close history');
 await click('.cc-card button','Timeline / outcomes');
 await wait("document.body.textContent.includes('Interested: 2')");
 await click('.cc-report-tabs button','Lead Journey');
 await wait("document.querySelector('.card-hdr')?.textContent.includes('Lead Journey')");
 await click('.cc-report-tabs button','Agent Report');
 await wait("document.body.textContent.includes('Agent performance')");
 assert.equal(calls.filter(c=>c.url.includes('life_cc_agent_marketing_data')&&!c.args.view).length,0,'agent performance must use appointment data without loading invoices');
 await click('[aria-label="Agent reports"] button','No follow-up');
 await wait("document.body.textContent.includes('Dormant client')");
 assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'no follow-up overflow '+width);
 await click('.cc-report-tabs button','Consultant');
 await wait("document.body.textContent.includes('Branch collections')&&document.body.textContent.includes('INV1')");
 assert.equal(calls.filter(c=>c.url.includes('life_cc_agent_marketing_data')&&!c.args.view).length,1);
 await click('.cc-report-tabs button','Digital Marketing');
 await wait("document.body.textContent.includes('Campaign / agency sources:')||document.body.textContent.includes('Lead & digital marketing')");
 await click('.cc-report-tabs button','Consultant');
 await wait("document.body.textContent.includes('Branch collections')");
 assert.equal(calls.filter(c=>c.url.includes('life_cc_agent_marketing_data')&&!c.args.view).length,1,'financial report must be reused across tabs');
 assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'consultant overflow '+width);
 calls.length=0;
}
await click('.cc-report-tabs button','CC Branch Visits');
partial=true;await click('.cc-filters button','Apply / refresh');
await wait("document.body.textContent.includes('Counts are partial')");
assert.equal(await evaluate("[...document.querySelectorAll('button')].find(b=>b.textContent==='Export filtered CSV').disabled"),true);
assert.equal(await evaluate("[...document.querySelectorAll('.cc-report-header-actions button')].find(b=>b.textContent==='Share preview').disabled"),true);
partial=false;fail=true;await click('.cc-filters button','Apply / refresh');
await wait("document.body.textContent.includes('Report fixture failed')");
fail=false;await click('.cc-error button','Retry');await wait("document.querySelector('.cc-report-summary tbody button')?.textContent==='1'");
assert.deepEqual(errors,[]);console.log('Visit report V26 browser checks passed: desktop/mobile month strip, six tabs, lazy financials, grouped drilldowns, masked details, share preview, activity timeline, Lead Journey, no-follow-up and collections.');
}finally{await send('Page.close');ws.close();}
})().catch(e=>{console.error(e);process.exit(1);});
