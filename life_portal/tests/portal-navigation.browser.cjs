// Isolated browser fixtures: no live ERP data or business writes.
const WebSocket = require('ws');
const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
 const endpoint = process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9226';
 const base = process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5176';
 const loading = fs.readFileSync('life_slimming/public/js/portal_module_loading.js','utf8');
 const bridge = fs.readFileSync('life_slimming/public/js/portal_module_bridge.js','utf8');
 const target = await (await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json();
 const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise(r => ws.on('open',r));
 const sessionId = 'fixture-' + Date.now();
 let sequence=0,role='IT';const jobs=new Map(),errors=[],pending=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++sequence,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id:sequence,method,params}));});
 const fulfill=(requestId,payload,type='application/json')=>send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:type}],body:Buffer.from(payload).toString('base64')});
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description);
  if(m.method!=='Fetch.requestPaused')return;
  const {requestId,request}=m.params;
  if(request.url.includes('/api/fixture/')){pending.push(requestId);return;}
  if(request.url.includes('/life_portal_module?')){
   const module=new URL(request.url).searchParams.get('module');
   const config={module,methods:{},routes:{'/branch-visit-report-NEW-Bhuvan':'ccvisit'}};
   return fulfill(requestId,`<!doctype html><html><body><h1>Fixture ${module}</h1><a id="report" href="/branch-visit-report-NEW-Bhuvan?branch=Fixture#table">Visit report</a><script>window.frappe={call:()=>{}};window.lifePortalModule=${JSON.stringify(config)};</script><script>${loading}</script><script>${bridge}</script><script>fetch('/api/fixture/slow');</script></body></html>`,'text/html');
  }
  let message={};
  if(request.url.includes('portal.bootstrap'))message={user:'workspace-fixture',session_id:sessionId,full_name:'Workspace Fixture',roles:role==='IT'?['System Manager']:[],portal_role:role,csrf_token:'fixture'};
  if(request.url.includes('convox.config'))message={enabled:false};
  await fulfill(requestId,JSON.stringify({message}));
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let n=0;n<100;n++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,50));}throw Error('Timed out: '+expression);};
 try {
  await send('Runtime.enable');await send('Page.enable');
  await send('Fetch.enable',{patterns:[{urlPattern:'*/api/method/*'},{urlPattern:'*/api/fixture/*'},{urlPattern:'*/life_portal_module?*'}]});
  await send('Page.navigate',{url:base+'/life_portal/leads'});
  await wait('!!document.querySelector(".route-loader")');
  await new Promise(resolve=>setTimeout(resolve,15500));
  assert.equal(await evaluate('document.querySelector(".route-loader button")?.textContent'),'Retry loading');
  await evaluate('window.navigationMarker="preserved";document.querySelector("iframe").contentDocument.querySelector("#report").click()');
  await wait('location.pathname === "/life_portal/ccvisit"');
  assert.equal(await evaluate('window.navigationMarker'),'preserved');
  assert.equal(await evaluate('location.search+location.hash'),'?branch=Fixture#table');
  await wait('document.querySelector("iframe")?.contentDocument?.querySelector("h1")?.textContent === "Fixture ccvisit"');
  assert.equal(await evaluate('document.querySelectorAll(".portal > header").length'),1);
  await evaluate('document.querySelector("iframe").src="/life_portal/tasks"');
  await wait('location.pathname === "/life_portal/tasks"');
  await wait('document.querySelector("iframe")?.contentDocument?.querySelector("h1")?.textContent === "Fixture tasks"');
  assert.equal(await evaluate('document.querySelectorAll(".portal > header").length'),1);
  assert.equal(await evaluate('document.querySelector("iframe").contentDocument.querySelectorAll(".portal").length'),0);
  assert.deepEqual(errors,[]);
  console.log('PASS: slow-request retry, SPA report navigation, query/hash preservation, and nested workspace escape.');
 } finally {ws.close();await fetch(endpoint+'/json/close/'+target.id);}
})().catch(error=>{console.error(error);process.exitCode=1;});
