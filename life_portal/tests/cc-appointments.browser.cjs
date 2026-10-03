// Run with Vite on 5175 and an isolated Chrome debugging session on 9225.
const WebSocket = require('../node_modules/ws');
const assert = require('node:assert/strict');
(async () => {
 const target=await (await fetch('http://127.0.0.1:9225/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));
 let id=0,failBooking=true;const jobs=new Map(),errors=[],bookings=[],changes=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++id,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id,method,params}));});
 const staff={id:'Employee:E1',name:'Consultation Manager',role:'Manager'};
 const lead={name:'LEAD-TEST',lead_name:'Test Lead',mobile_no:'9000000000',lead_owner:'agent@example.test',lead_owner_name:'Assigned Agent'};
 const stamp=minutes=>`2030-01-01 ${String(10+Math.floor(minutes/60)).padStart(2,'0')}:${String(minutes%60).padStart(2,'0')}:00`;
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description);
  if(m.method!=='Fetch.requestPaused')return;
  const {requestId,request}=m.params;let result={};let body;
  if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'Booking Manager',roles:['System Manager'],csrf_token:'test'};
  if(request.url.includes('cc_appointments.bootstrap'))result={appointment:JSON.parse(request.postData||'{}').selected_lead==='LEAD-EXISTING'?{name:'APT-1',modified:'2029-01-01 09:00:00',branch:'Banjara Hills',start:stamp(0),duration:45,staff:staff.name}:null,branches:['Banjara Hills'],staff:[staff],leads:[lead],today:'2030-01-01',timezone:'Asia/Kolkata'};
  if(request.url.includes('cc_appointments.calendar'))result={schedules:[{staff,slots:Array.from({length:38},(_,i)=>({start:stamp(i*15),end:stamp(i*15+45),available:i>=4,reason:i<4?'Booked':'Available'})),events:[{editable:true,name:'APT-1',start:stamp(0),end:stamp(60),client:'Existing Lead',agent:lead.lead_owner,agent_name:lead.lead_owner_name,branch:'Banjara Hills',lead:'LEAD-EXISTING'}]}]};
  if(request.url.includes('cc_appointments.book')){bookings.push(JSON.parse(request.postData));if(failBooking)body={exc_type:'ValidationError',_server_messages:JSON.stringify([JSON.stringify({message:'Slot already booked. Refresh and try again.'})])};else result={name:'APT-NEW'};}
  if(request.url.includes('cc_appointments.reschedule')){changes.push(JSON.parse(request.postData));result={name:'APT-1'};}
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify(body||{message:result})).toString('base64')});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let i=0;i<80;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100));}throw new Error('Timed out: '+expression+'\n'+await evaluate('document.body.innerText')+'\n'+JSON.stringify(errors));};
 try{
  await send('Storage.clearDataForOrigin',{origin:'http://127.0.0.1:5175',storageTypes:'local_storage'});
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:5175/api/*'}]});
  for(const width of [1440,390]){
   await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
   await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/cc-appointments?lead=LEAD-TEST'});
   await wait("document.querySelectorAll('.calendar-grid tbody tr').length===40");
   assert.equal(await evaluate("document.querySelectorAll('.calendar-grid .event-card').length"),4);
   if(width===1440){const shot=await send('Page.captureScreenshot',{format:'png'});require('node:fs').writeFileSync('/tmp/cc-appointments-desktop.png',Buffer.from(shot.data,'base64'));}
   assert.equal(await evaluate("document.querySelector('.summary strong').textContent"),'1');
   assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
   await evaluate("document.querySelector('.add-slot').click()");await wait("document.querySelector('dialog').open");
   assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('dialog input[readonly]')).map(e=>e.value)"),['Assigned Agent','Consultation Manager · Manager']);
   assert.equal(await evaluate("document.querySelector('dialog select').value"),'LEAD-TEST');
   failBooking=true;await evaluate("document.querySelector('dialog form').requestSubmit()");await wait("document.querySelector('dialog .error')?.textContent.includes('Slot already booked')");
   assert.equal(await evaluate("document.querySelector('dialog').open"),true);
   failBooking=false;await evaluate("document.querySelector('dialog form').requestSubmit()");await wait("!document.querySelector('dialog').open && document.querySelector('.success')");
   assert.equal(bookings.at(-1).resource,staff.id);assert.equal(bookings.at(-1).lead,lead.name);
   assert.equal(bookings.at(-1).request_id,bookings.at(-2).request_id);
   await wait("document.querySelector('.agenda button') && !document.querySelector('.agenda button').disabled");
   await evaluate("document.querySelector('.agenda button').click()");
   await wait("document.body.textContent.includes('Changing APT-1') && document.querySelector('.add-slot')");
   await evaluate("document.querySelector('.add-slot').click()");await wait("document.querySelector('dialog').open");
   assert.equal(await evaluate("document.querySelector('dialog select').disabled"),true);
   await evaluate("document.querySelector('dialog form').requestSubmit()");
   await wait("!document.querySelector('dialog').open && document.querySelector('.success')?.textContent.includes('updated successfully')");
   assert.equal(changes.at(-1).appointment,'APT-1');
   assert.equal(changes.at(-1).modified,'2029-01-01 09:00:00');
   assert.equal(changes.at(-1).resource,staff.id);
  }
  assert.deepEqual(errors,[]);console.log('CC calendar: desktop/mobile grid, selected lead/owner, conflict handling, retry and booking passed.');
 }finally{await send('Page.close');ws.close();}
})().catch(e=>{console.error(e);process.exit(1);});
