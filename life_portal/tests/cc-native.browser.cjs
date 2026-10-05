// Local Vite :5175 + isolated Chrome :9225; every business API is mocked.
const WebSocket = require('../node_modules/ws');
const assert = require('node:assert/strict');
(async()=>{
 const target=await(await fetch('http://127.0.0.1:9225/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));
 let id=0,fail=false,truncated=false;const jobs=new Map(),errors=[],calls=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++id,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id,method,params}));});
 const rows=Array.from({length:85},(_,i)=>({name:'LEAD-'+String(i+1).padStart(3,'0'),lead_name:'Client '+(i+1),mobile_no:'9876543210',branch:i<45?'Branch A':'Branch B',lead_owner:'lifescc13@gmail.com',custom_appointment_date_and_time:'2026-10-05 10:00:00',custom_appointment_status:i%2?'Visited & Booked':'Scheduled'}));
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
  if(m.method!=='Fetch.requestPaused')return;
  const {requestId,request}=m.params;const args=JSON.parse(request.postData||'{}');calls.push({url:request.url,args});let result={},body;
  if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'Native Tester',roles:['System Manager'],csrf_token:'test'};
  if(request.url.includes('cc_get_leads.run')){
   if(args.detail)result={rows:[{...rows[0],workflow_hint:{legacy_events:[{at:'2026-10-05',by:'Agent',from:'New',to:'Scheduled'}]}}]};
   else result={rows:rows.slice(args.start||0,(args.start||0)+40),total:85,has_more:(args.start||0)+40<85,scoped_to_owner:1};
  }
  if(request.url.includes('life_cc_agent_marketing_data.run')){
   if(fail)body={exc_type:'ValidationError',_server_messages:JSON.stringify([JSON.stringify({message:'Report temporarily unavailable'})])};
   else if(args.view==='appointments')result={rows,total:truncated?10001:85,truncated,restricted_to_owner:true};
   else result={financial_events:[{event_key:'E1',sales_invoice:'INV-TEST',lead_name:'Client 1',event_date:'2026-10-05',paid_amount:1200,branch:'Branch A'}]};
  }
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify(body||{message:result})).toString('base64')});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,75));}throw Error('Timed out: '+expression+'\n'+await evaluate('document.body.innerText'));};
 const click=text=>evaluate(`Array.from(document.querySelectorAll('.cc-native button')).find(b=>b.textContent.trim()===${JSON.stringify(text)}).click()`);
 try{
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:5175/api/*'}]});
  for(const width of [1440,390]){
   calls.length=0;
   await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
   await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/native/cc-dashboard'});
   await wait("document.querySelectorAll('.cc-table tbody tr').length===40");
   assert.equal(calls.filter(c=>c.url.includes('cc_get_leads')).length,1);
   assert.equal(calls.find(c=>c.url.includes('cc_get_leads')).args.page_size,40);
   assert.equal(await evaluate("document.querySelectorAll('iframe').length"),0);
   assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
   await click('Next');await wait("document.querySelector('.cc-table tbody tr')?.textContent.includes('LEAD-041')");
   assert.equal(calls.filter(c=>c.url.includes('cc_get_leads')).at(-1).args.start,40);
   await click('Previous');await wait("document.querySelector('.cc-table tbody tr')?.textContent.includes('LEAD-001')");
   await click('Details');await wait("document.querySelector('dialog').open && document.querySelector('dialog li')");
   assert.equal(calls.filter(c=>c.args.detail).length,1);await click('Close');
   assert.ok(await evaluate("document.querySelector('.cc-table a').href.includes('cc-appointments?lead=LEAD-001')"));
   calls.length=0;
   await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/native/cc-visit-report'});
   await wait("document.querySelectorAll('.cc-table tbody tr').length===40 && document.querySelectorAll('.cc-cards button').length===3");
   assert.equal(calls.filter(c=>c.url.includes('life_cc_agent_marketing_data')).length,1);
   assert.equal(calls.find(c=>c.url.includes('life_cc_agent_marketing_data')).args.view,'appointments');
   assert.equal(await evaluate("document.querySelectorAll('iframe').length"),0);
   assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
   await click('Next');await wait("document.querySelector('.cc-table tbody tr')?.textContent.includes('LEAD-041')");
   await evaluate("document.querySelectorAll('.cc-cards button')[2].click()");await wait("document.querySelector('.cc-pager').textContent.includes('Page 1 / 1')");
   assert.equal(await evaluate("document.querySelectorAll('.cc-table tbody tr').length"),40);
   assert.ok(await evaluate("Array.from(document.querySelectorAll('.cc-table tbody tr')).every(r=>r.textContent.includes('Branch B'))"));
   await evaluate("window.__csv='';URL.createObjectURL=blob=>{blob.text().then(t=>window.__csv=t);return 'blob:test'};URL.revokeObjectURL=()=>{};HTMLAnchorElement.prototype.click=function(){}");
   await click('Export filtered CSV');await wait("window.__csv.includes('LEAD-085')");
   assert.equal(await evaluate("window.__csv.includes('9876543210')"),false);
   assert.equal(await evaluate("window.__csv.split('\\r\\n').length"),41);
   await click('Load financial events');await wait("document.body.textContent.includes('INV-TEST')");
   assert.equal(calls.filter(c=>c.url.includes('life_cc_agent_marketing_data')&&!c.args.view).length,1);
   fail=true;await click('Apply / refresh');await wait("document.querySelector('.cc-error')?.textContent.includes('Report temporarily unavailable')");
   assert.equal(await evaluate("Array.from(document.querySelectorAll('.cc-native button')).find(b=>b.textContent==='Export filtered CSV').disabled"),true);
   fail=false;truncated=true;await click('Retry');await wait("document.body.textContent.includes('Counts are partial')");
   assert.equal(await evaluate("Array.from(document.querySelectorAll('.cc-native button')).find(b=>b.textContent==='Export filtered CSV').disabled"),true);
   truncated=false;
  }
  assert.deepEqual(errors,[]);
  console.log('Native CC browser checks passed: desktop/mobile, no iframe, initial request budget, pagination, lazy details/financials, branch filters, masked CSV, errors/retry, incomplete-export blocking.');
 }finally{await send('Page.close');ws.close();}
})().catch(e=>{console.error(e);process.exit(1);});
