// Fixture-only browser integration; run against Vite and a dedicated CDP browser.
const WebSocket = require('ws');
const assert = require('node:assert/strict');
(async () => {
 const endpoint=process.env.IDLE_BROWSER_URL||'http://127.0.0.1:9224';
 const base=process.env.IDLE_PREVIEW_URL||'http://127.0.0.1:5175';
 const target=await (await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));
 let sequence=0,loggedOut=false;const jobs=new Map(),requests=[],errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++sequence,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id:sequence,method,params}));});
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description);
  if(m.method!=='Fetch.requestPaused')return;
  const {requestId,request}=m.params;requests.push(request.url);
  let message={},payload,type='application/json';
  if(request.url.includes('/life_portal_module?')){type='text/html';payload='<html><body><input id="activity" aria-label="Fixture field"></body></html>';}
  else if(request.url.includes('portal.bootstrap'))message={user:'idle-fixture',session_id:'idle-session',full_name:'Idle Fixture',roles:['System Manager'],csrf_token:'fixture'};
  else if(request.url.includes('login_context'))message={authenticated:!loggedOut,csrf_token:'fixture',password_login_enabled:true};
  else if(request.url.includes('/logout')){loggedOut=true;message='Logged Out';}
  else if(request.url.includes('convox.config'))message={enabled:false};
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:type}],body:Buffer.from(payload||JSON.stringify({message})).toString('base64')});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let n=0;n<100;n++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error('Timed out: '+expression);};
 try{
  await send('Runtime.enable');await send('Page.enable');
  await send('Fetch.enable',{patterns:[{urlPattern:'*/api/method/*'},{urlPattern:'*/life_portal_module?*'}]});
  await send('Page.addScriptToEvaluateOnNewDocument',{source:'window.idleOffset=0;const nativeNow=Date.now.bind(Date);Date.now=()=>nativeNow()+window.idleOffset;'});
  await send('Page.navigate',{url:base+'/life_portal/cliinfo'});
  await wait('document.querySelector("iframe")?.contentDocument?.querySelector("#activity")');
  assert.equal(requests.filter(u=>u.includes('portal.bootstrap')).length,1);
  assert.equal(requests.filter(u=>u.includes('login_context')).length,0);
  await evaluate('window.idleOffset=57*60*1000');await wait('document.querySelector(".idle-dialog")?.open');
  assert.match(await evaluate('document.querySelector(".idle-countdown").textContent'),/^2:5\d$|^3:00$/);
  await evaluate('document.querySelector(".idle-dialog button").click()');await wait('!document.querySelector(".idle-dialog").open');
  // Keyboard input in the same-origin ERP iframe must renew the parent timer.
  await evaluate('window.idleOffset+=56*60*1000;document.querySelector("iframe").contentDocument.querySelector("input").focus()');
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'a',code:'KeyA',text:'a'});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key:'a',code:'KeyA'});
  await evaluate('window.idleOffset+=2*60*1000');await new Promise(r=>setTimeout(r,1200));
  assert.equal(await evaluate('document.querySelector(".idle-dialog").open'),false,'Iframe interaction resets idle deadline');
  await evaluate('window.idleOffset+=61*60*1000');await wait('location.pathname.endsWith("/login") && !!document.querySelector("input[type=password]")');
  assert.equal(loggedOut,true);assert.ok(requests.some(u=>u.endsWith('/logout')));
  assert.match(await evaluate('document.body.textContent'),/one hour of inactivity/);
  assert.deepEqual(errors,[]);
  process.stdout.write('PASS: single bootstrap, 57-minute warning, stay signed in, iframe activity, expiry after sleep, server logout and login redirect.\n');
 }catch(error){process.stderr.write(JSON.stringify({requests,errors,page:await evaluate("document.body.innerText"),url:await evaluate("location.href")})+"\n");throw error;}finally{ws.close();await fetch(endpoint+'/json/close/'+target.id);}
})().catch(error=>{process.stderr.write(String(error.stack||error)+'\n');process.exitCode=1;});
