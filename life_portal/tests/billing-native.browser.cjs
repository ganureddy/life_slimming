// Local Vite :5175 + isolated Chrome :9225; every business API is mocked.
const WebSocket = require('../node_modules/ws');
const assert = require('node:assert/strict');
(async()=>{
 const target=await(await fetch('http://127.0.0.1:9225/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));
 let id=0,fail=false,empty=false;const jobs=new Map(),errors=[],calls=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++id,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id,method,params}));});

 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);
  if(m.method!=='Fetch.requestPaused')return;
  const {requestId,request}=m.params;const args=JSON.parse(request.postData||'{}');calls.push({url:request.url,args});let result={ok:true};
  if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'Tester',roles:['System Manager'],csrf_token:'test'};
  if(request.url.includes('lifescc_billing_bootstrap.run'))result={branches:['A','B'],allowed_branches:['A'],user_branch:'B',is_head_office:0};
  if(request.url.includes('lifescc_billing_collections_report.run'))result=fail?{error:'Report temporarily unavailable'}:{rows:empty?[]:[{branch:'A',billed_total:'1050',collected_total:'500',outstanding:'550'},{branch:'B',billed_total:9999}]};
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,75));}throw Error('Timed out: '+expression+'\n'+await evaluate('document.body.innerText'));};
 const click=text=>evaluate(`Array.from(document.querySelectorAll('.billing-native button')).find(b=>(()=>{const c=b.cloneNode(true);c.querySelectorAll('.tab-icon,.billing-count').forEach(n=>n.remove());return c.textContent.trim();})()===${JSON.stringify(text)}).click()`);
 try{
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:5175/api/*'}]});
  for(const width of [1440,390]){
   calls.length=0;
   await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
   await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/native/billing?view=collections'});
   await wait("document.querySelectorAll('.billing-native tbody tr').length===1");
   assert.equal(calls.filter(c=>c.url.includes('lifescc_billing_bootstrap.run')).length,1);
   assert.equal(calls.filter(c=>c.url.includes('lifescc_billing_collections_report.run')).length,1);
   assert.equal(calls.filter(c=>c.url.includes('lifescc_billing_collections_report.run')).at(-1).args.branch,'A');
   assert.equal(await evaluate("document.querySelectorAll('.billing-native select option').length"),1);
   assert.equal(await evaluate("document.querySelectorAll('iframe').length"),0);
   assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
   assert.equal(await evaluate("document.querySelector('.billing-native tfoot').textContent.includes('1,050.00')"),true);
   await click('Today');await wait("document.querySelector('.billing-native tbody tr') && !document.querySelector('.billing-native button').disabled");
   assert.equal(calls.filter(c=>c.url.includes('lifescc_billing_collections_report.run')).at(-1).args.from_date,calls.filter(c=>c.url.includes('lifescc_billing_collections_report.run')).at(-1).args.to_date);
   fail=true;await click('Apply');await wait("document.querySelector('.billing-native [role=alert]')");
   assert.equal(await evaluate("document.querySelectorAll('.billing-native tbody tr').length"),0);
   fail=false;await click('Retry');await wait("document.querySelector('.billing-native tbody tr')");
   empty=true;await click('Apply');await wait("document.querySelector('.billing-native').textContent.includes('No collections found')");
   empty=false;
  }
  assert.deepEqual(errors,[]);
  console.log('Billing browser checks passed: desktop/mobile, branch scope, totals, date presets, errors/retry, empty states, no iframe or overflow.');
 }finally{await send('Page.close');ws.close();}
})().catch(e=>{console.error(e);process.exit(1);});
