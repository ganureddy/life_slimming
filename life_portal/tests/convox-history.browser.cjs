// Isolated browser fixture: no live calls, event records or recordings.
const WebSocket = require('ws');
const assert = require('node:assert/strict');
(async () => {
 const endpoint = process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9237';
 const base = process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5187';
 const target = await (await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json();
 const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise(r=>ws.on('open',r));
 let seq=0; const jobs=new Map(), errors=[], pages=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++seq,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id:seq,method,params}));});
 const fulfill=(id,message)=>send('Fetch.fulfillRequest',{requestId:id,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message})).toString('base64')});
 ws.on('message',async raw=>{
  const m=JSON.parse(raw); if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);}
  if(m.method==='Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.text);
  if(m.method!=='Fetch.requestPaused')return;
  const {requestId,request}=m.params;let message={};
  if(request.url.includes('/life_portal_module?')) return send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'text/html'}],body:Buffer.from('<html><body>Fixture CC dashboard</body></html>').toString('base64')});
  if(request.url.includes('portal.bootstrap'))message={user:'fixture',session_id:'history-fixture',full_name:'Fixture',roles:['System Manager'],portal_role:'IT',csrf_token:'fixture'};
  if(request.url.includes('convox.config'))message={enabled:false};
  if(request.url.includes('convox.lead_history')){
   const args=JSON.parse(request.postData);pages.push(args.start);
   message={lead_id:args.lead_id,lead_name:'Fixture Lead',mobile_number:'9876543210',scope:'all_agents',total_calls:26,total_events:51,start:args.start,has_more:args.start===0,fields:[{key:'agent_id',label:'Agent ID'},{key:'remarks',label:'Remarks'},{key:'recording_file_name',label:'Recording'}],events:[{name:'event-'+args.start,call_reference:'CALL-1',event_type:'Call Status',call_status:'Answered',call_datetime:'2026-09-30 09:00:00',call_duration:'00:02:15',agent_id:'AGENT1',remarks:'<img src=x onerror=alert(1)>',recording_file_name:args.start?'javascript:alert(1)':'/files/fixture-call.mp3'}]};
  }
  await fulfill(requestId,message);
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,50));}throw Error('Timed out: '+expression);};
 try{
  await send('Runtime.enable');await send('Page.enable');await send('Fetch.enable',{patterns:[{urlPattern:'*/api/method/*'},{urlPattern:'*/life_portal_module?*'}]});
  await send('Page.navigate',{url:base+'/life_portal/leads/LEAD-1/convox'});
  await wait('document.querySelector(".history-summary")?.textContent.includes("26")');
  assert.equal(await evaluate('document.querySelectorAll("audio").length'),1);
  assert.equal(await evaluate('document.querySelectorAll(".call-event img").length'),0);
  assert.equal(await evaluate('document.querySelector(".call-event dl").textContent.includes("AGENT1")'),true);
  await evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent==="Next").click()');
  await wait('document.querySelector(".history-pagination")?.textContent.includes("51–51")');
  assert.equal(await evaluate('document.querySelectorAll("audio").length'),0);
  assert.equal(await evaluate('Array.from(document.querySelectorAll("a")).some(a=>a.href.startsWith("javascript:"))'),false);
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);
  assert.deepEqual(pages,[0,50]);
  assert.equal(await evaluate(`!!document.querySelector('a[href="/life_portal/convox-history"]')`),true);
  await send('Page.navigate',{url:base+'/life_portal/leads'});
  await wait('!!document.querySelector(".portal-source-page iframe")?.contentDocument?.body?.textContent.includes("Fixture CC")');
  await evaluate(`document.querySelector("iframe").contentWindow.eval('parent.postMessage({type:"life-convox-history",lead_id:"LEAD-1"},location.origin)')`);
  await wait('!!document.querySelector("dialog[open] .history-summary")');
  assert.equal(await evaluate('document.querySelector("dialog[open]").textContent.includes("Fixture Lead")'),true);
  await evaluate('document.querySelector(".history-close").click()');
  await wait('!document.querySelector("dialog[open]")');
  assert.deepEqual(errors,[]);
  console.log('PASS: history route, counts, fields, paging, safe recording links and mobile layout');
 }finally{ws.close();await fetch(endpoint+'/json/close/'+target.id);}
})().catch(e=>{console.error(e);process.exitCode=1;});
