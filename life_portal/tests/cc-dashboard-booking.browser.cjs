const WebSocket=require('../node_modules/ws'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const source=JSON.parse(fs.readFileSync('life_slimming/portal_pages/cc-new-dash.json','utf8'));
 const js=source.javascript;
 const functions=js.slice(js.indexOf('  function openModal('),js.indexOf('  function toggleDark('))+js.slice(js.indexOf('  async function openAppointmentFromLead('),js.indexOf('  function selectStatus('));
 const target=await(await fetch('http://127.0.0.1:9225/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));
 let id=0,fail=true;const jobs=new Map(),errors=[],bookings=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++id,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id,method,params}));});
 const staff=[{id:'Employee:E1',name:'Manager One',role:'Manager',designation:'ACM'},{id:'Employee:E2',name:'Doctor Two',role:'Doctor',designation:'Consultant Doctor'}];
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description);if(m.method!=='Fetch.requestPaused')return;
  const {requestId,request}=m.params;let payload,contentType='application/json';
  if(request.url.includes('/cc-booking-test')){
   contentType='text/html';payload=`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0}#modal{display:none}#modal.show{display:block}#modal-box{max-width:800px;margin:auto;padding:16px}*{box-sizing:border-box}${source.css}</style><div id="modal"><div id="modal-box"><h2 id="modal-title"></h2><div id="modal-body"></div></div></div><script>
   const LEADS=[{id:'LEAD1',branchCode:'Branch A'}];let refreshed=0;
   const escapeHtml=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const escAttr=escapeHtml;
   const frappe={call:async o=>{const r=await fetch('/api/method/'+o.method,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o.args)});const data=await r.json();if(data.error)throw Error(data.error);return data;}};
   const toast=()=>{},seedLeads=async()=>{refreshed++},renderAppointmentPage=()=>{},renderMyLeads=()=>{},renderDashboard=()=>{},updateNavBadges=()=>{};
   ${functions}
   openAppointmentFromLead('LEAD1');</script>`;
  }else{
   let result={};const args=JSON.parse(request.postData||'{}');
   if(request.url.endsWith('.bootstrap'))result={today:'2030-01-01',branches:['Branch A','Branch B'],leads:[{name:'LEAD1',lead_name:'Lead One',mobile_no:'9000000000',lead_owner_name:'Assigned Agent'}]};
   if(request.url.endsWith('.calendar'))result={schedules:(args.branch==='Branch A'?staff:[staff[1]]).map(person=>({staff:person,slots:[{start:'2030-01-01 10:00:00',end:'2030-01-01 10:45:00',available:false,reason:'Booked'},{start:'2030-01-01 11:00:00',end:'2030-01-01 11:45:00',available:true,reason:'Available'}]}))};
   if(request.url.endsWith('.book')){bookings.push(args);if(fail)payload=JSON.stringify({error:'Slot is already booked'});else result={name:'APT1'};}
   payload=payload||JSON.stringify({message:result});
  }
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:contentType+'; charset=utf-8'}],body:Buffer.from(payload).toString('base64')});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description);return r.result.value;};
 const wait=async expression=>{for(let i=0;i<80;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error('Timeout '+expression+' '+await evaluate('document.body.innerText'));};
 try{
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:5175/cc-booking-test'},{urlPattern:'http://127.0.0.1:5175/api/*'}]});
  for(const width of [1440,390]){
   fail=true;await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});await send('Page.navigate',{url:'http://127.0.0.1:5175/cc-booking-test'});
   await wait("document.querySelectorAll('#cc-slot-times button').length===2");
   assert.equal(await evaluate("document.querySelector('#cc-slot-owner').value"),'Assigned Agent');
   assert.equal(await evaluate("document.querySelector('#cc-slot-times button').disabled"),true);
   await evaluate("let role=document.querySelector('#cc-slot-role');role.value='Consultant Doctor';role.dispatchEvent(new Event('change'))");
   assert.equal(await evaluate("document.querySelector('#cc-slot-employee').value"),'Employee:E2');
   await evaluate("document.querySelector('#cc-slot-times button:not(:disabled)').click()");
   assert.match(await evaluate("document.querySelector('#cc-slot-summary').textContent"),/Doctor Two · Consultant Doctor/);
   assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
   await evaluate("document.querySelector('#cc-slot-form').requestSubmit()");await wait("document.querySelector('#cc-slot-message').textContent==='Slot is already booked'");
   fail=false;await evaluate("document.querySelector('#cc-slot-form').requestSubmit()");await wait('refreshed===1');
   assert.equal(bookings.at(-1).lead,'LEAD1');assert.equal(bookings.at(-1).resource,'Employee:E2');assert.equal(bookings.at(-1).request_id,bookings.at(-2).request_id);
   assert.equal(await evaluate("document.querySelector('#modal').classList.contains('show')"),false);
  }
  assert.deepEqual(errors,[]);console.log('Dashboard direct booking: desktop/mobile, designation filter, owner, unavailable slots, error/retry and refresh passed.');
 }finally{await send('Page.close');ws.close();}
})().catch(e=>{console.error(e);process.exit(1);});
