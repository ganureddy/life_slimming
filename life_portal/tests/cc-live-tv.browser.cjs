// Isolated fixtures only: Vite :5175, headless Chrome :9225.
const WebSocket = require('../node_modules/ws');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
 const target = await (await fetch('http://127.0.0.1:9225/json/new?about:blank',{method:'PUT'})).json();
 const ws = new WebSocket(target.webSocketDebuggerUrl);
 await new Promise(resolve=>ws.on('open',resolve));
 let seq=0, calls=0, denied=false, called=false;
 const jobs=new Map(), errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++seq,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id:seq,method,params}));});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let i=0;i<150;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error('Timed out: '+expression);};
 const agents=Object.fromEntries(Array.from({length:13},(_,i)=>['agent'+i,'Agent '+i+' Long Name']));
 const rows=Array.from({length:13},(_,i)=>({name:'L'+i,lead_name:'Client '+i,lead_owner:'agent'+i,creation:'2026-10-11 09:00:00',modified:'2026-10-11 09:00:00',branch:'Banjara Hills',custom_appointment_date_and_time:'2026-10-11 12:00:00',custom_appointment_status:'Visited Booked',custom_call_count:1,custom_last_call_time:'2026-10-11 09:01:00'}));
 rows.push({name:'waiting',lead_name:'Waiting Client',lead_owner:'agent0',creation:'2026-10-11 09:40:00',modified:'2026-10-11 09:40:00',custom_call_count:0,custom_last_call_time:null});
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
  if(m.method!=='Fetch.requestPaused')return;
  const {requestId,request}=m.params;let result={};let status=200;
  if(request.url.includes('login_context'))result={authenticated:true};
  if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'TV Tester',roles:['System Manager'],csrf_token:'fixture'};
  if(request.url.includes('cc_live_tv.snapshot')){
   calls++;
   if(called){rows[13].custom_call_count=1;rows[13].custom_last_call_time='2026-10-11 10:00:00';}
   result={rows,agents,agent_images:{agent0:'/files/missing-tv-image.png'},today:'2026-10-11',timestamp:'2026-10-11 10:00:00',timezone:'Asia/Kolkata',week_start:'2026-10-05',week_end:'2026-10-12'};
   if(denied){status=403;result=null;}
  }
  await send('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')});
 });
 try {
  await send('Page.enable');await send('Runtime.enable');
  await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:5175/api/*'}]});
  await send('Emulation.setDeviceMetricsOverride',{width:1920,height:1080,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/native/cc-live-tv'});
  await wait("document.querySelector('.waiting')?.textContent.includes('Waiting Client')");
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.chip b')).map(el=>el.textContent)"),['14','13','13','13']);
  assert.equal(await evaluate("document.querySelector('.weekly-band').textContent.includes('8.75')"),true);
  await evaluate("window.tvOffset=45000; window.OriginalDate=Date; window.Date=class extends OriginalDate { constructor(...args){super(...(args.length?args:[OriginalDate.now()+window.tvOffset]));} static now(){return OriginalDate.now()+window.tvOffset;} };");
  await wait("document.querySelectorAll('.rw').length===8");
  await evaluate('window.tvOffset=53000');
  await wait("document.querySelector('.rw .rk')?.textContent==='9'");
  await new Promise(r=>setTimeout(r,700));
  const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync('/tmp/cc-tv-v2.png',Buffer.from(shot.data,'base64'));
  called=true;
  await wait("!document.querySelector('.waiting')");
  for(const [width,height] of [[1366,768],[3840,2160]]){
   await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
   await new Promise(r=>setTimeout(r,150));
   assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
  }
  denied=true;
  await wait("document.querySelector('.chip b')?.textContent==='—'");
  assert.equal(await evaluate("document.querySelectorAll('.rw').length"),0);
  assert.equal(await evaluate("document.querySelector('.weekly-band').textContent.includes('Agent 0')"),false);
  assert.ok(calls>=3);assert.deepEqual(errors,[]);
  console.log('CC TV browser checks passed: counts, waiting removal, idle roster pagination, scaling, permission clearing. Screenshot: /tmp/cc-tv-v2.png');
 } finally { await send('Page.close').catch(()=>{}); ws.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
