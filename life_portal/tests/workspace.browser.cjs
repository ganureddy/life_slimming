// Isolated browser fixtures: no live ERP data or business writes.
const WebSocket = require('ws');
const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
 const endpoint = process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9226';
 const base = process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5176';
 const fixtures = JSON.parse(fs.readFileSync('/tmp/life-workspace-fixtures.json', 'utf8'));
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
   return fulfill(requestId,fixtures[module],'text/html');
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
  for(const module of Object.keys(fixtures).filter(x=>x!=='control')){
   pending.length=0;
   await send('Page.navigate',{url:base+'/life_portal/'+module});
   await wait('document.querySelector("iframe")?.contentDocument?.documentElement?.dataset.portalModule === '+JSON.stringify(module));
   for(let n=0;n<100&&pending.length<2;n++)await new Promise(r=>setTimeout(r,50));
   assert.equal(pending.length,2,module+' starts two fixture requests');
   await wait('!!document.querySelector(".route-loader")');
   assert.equal(await evaluate('document.querySelectorAll(".portal > header").length'),1);
   assert.equal(await evaluate('Array.from(document.querySelector("iframe").contentDocument.querySelectorAll("[data-portal-chrome]")).every(el=>getComputedStyle(el).display==="none")'),true,module+' hides duplicate chrome');
   await fulfill(pending.shift(),'{}');
   await new Promise(r=>setTimeout(r,180));
   assert.equal(await evaluate('!!document.querySelector(".route-loader")'),true,module+' waits for both requests');
   await fulfill(pending.shift(),'{}');
   await wait('!document.querySelector(".route-loader")');
  }
  // Denied native and embedded routes must never mount their business pages.
  role='HR';
  for(const module of ['billing','p2p','cliinfo']){
   await send('Page.navigate',{url:base+'/life_portal/'+module});
   await wait('document.querySelector("main")?.textContent.includes("Access unavailable")');
   assert.equal(await evaluate('document.querySelectorAll("iframe,.billing-compat-page").length'),0);
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: 41 embedded routes, one header, hidden legacy branding, concurrent-request loader, and denied native/embedded routes.');
 } catch(error) { console.error({errors, page: await evaluate('document.body?.innerText'), frames: await evaluate('Array.from(document.querySelectorAll("iframe")).map(f=>({src:f.src,html:f.contentDocument?.documentElement?.outerHTML.slice(0,500)}))')}); throw error; } finally {ws.close();await fetch(endpoint+'/json/close/'+target.id);}
})().catch(error=>{console.error(error);process.exitCode=1;});
