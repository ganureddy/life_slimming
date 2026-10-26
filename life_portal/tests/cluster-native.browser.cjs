const assert=require('node:assert/strict'),WebSocket=require('ws');
(async()=>{
 const endpoint=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9230',base=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5178';
 const target=await(await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json(),ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(resolve=>ws.on('open',resolve));
 const jobs=new Map(),calls=[],errors=[];let sequence=0,mode='success';
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++sequence,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id:sequence,method,params}));});
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
  if(m.method!=='Fetch.requestPaused')return;
  const{requestId,request}=m.params;const method=new URL(request.url).pathname.split('/api/method/')[1];let message={};
  const args=JSON.parse(request.postData||'{}');calls.push({method,args,headers:request.headers});
  if(method==='life_slimming.api.portal.bootstrap')message={user:'cluster-fixture',session_id:'cluster-fixture-'+target.id,full_name:'Cluster Fixture',roles:['System Manager'],portal_role:'IT',csrf_token:'cluster-csrf'};
  if(method==='life_slimming.api.convox.config')message={enabled:false};
  if(method==='life_slimming.api.server_scripts.cluster_dashboard_api.run')message={cluster:args.cluster||'My Cluster',from_date:args.from_date,to_date:args.to_date,available_clusters:['Cluster A','Cluster B'],branches:['Branch A'],totals:{sales_amt:123456,sales_count:8,collections:99999,outstanding:23457},rows:mode==='empty'?[]:[{branch:'Branch A',sales_amt:123456,sales_count:8,collections:99999,outstanding:23457}]};
  const failure=mode==='denied'&&method==='life_slimming.api.server_scripts.cluster_dashboard_api.run';
  await send('Fetch.fulfillRequest',{requestId,responseCode:failure?403:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify(failure?{exc_type:'PermissionError',message:'Denied'}:{message})).toString('base64')});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let n=0;n<150;n++){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,40));}throw Error('Timeout: '+expression)};
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const input=(selector,value)=>evaluate(`(()=>{const el=document.querySelector(${JSON.stringify(selector)});el.value=${JSON.stringify(value)};el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 try{
  await send('Runtime.enable');await send('Page.enable');await send('Fetch.enable',{patterns:[{urlPattern:'*/api/method/*'}]});
  for(const width of[1440,390]){
   mode='success';calls.length=0;await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<600});await send('Page.navigate',{url:base+'/life_portal/native/cluster-dashboard'});
   await wait('document.querySelector("#cdCards") && !document.querySelector(".cd-btn").disabled');
   assert.equal(await evaluate('!!document.querySelector("iframe")'),false);assert.equal(await evaluate('document.querySelectorAll(".cd-card").length'),4);assert.equal(await evaluate('document.querySelector(".cd-card .v").textContent'),'₹1,23,456');
   assert.equal(await evaluate('document.querySelectorAll("#cdClusterSel option").length'),4);assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true);
   await input('#cdFrom','2026-10-01');await input('#cdTo','2026-10-13');await input('#cdClusterSel','Cluster B');await click('.cd-btn');await wait('document.querySelector("#cdTitle").textContent === "Cluster B"');
   const call=calls.filter(c=>c.method==='life_slimming.api.server_scripts.cluster_dashboard_api.run').at(-1);assert.deepEqual(call.args,{from_date:'2026-10-01',to_date:'2026-10-13',cluster:'Cluster B'});assert.equal(call.headers['X-Frappe-CSRF-Token'],'cluster-csrf');
   mode='empty';await click('.cd-btn');await wait('document.querySelector("#cdTbody").textContent.includes("No branches configured")');
   mode='denied';await click('.cd-btn');await wait('document.querySelector("#cdSub").textContent === "Failed to load data."');
   mode='success';await click('.cd-btn');await wait('document.querySelector("#cdTbody").textContent.includes("Branch A") && !document.querySelector(".cd-btn").disabled');
   await input('#cdFrom','2026-11-01');const before=calls.filter(c=>c.method==='life_slimming.api.server_scripts.cluster_dashboard_api.run').length;await click('.cd-btn');await wait('document.querySelector("#cdSub").textContent === "Choose a valid date range."');assert.equal(calls.filter(c=>c.method==='life_slimming.api.server_scripts.cluster_dashboard_api.run').length,before);
   console.log('Cluster Vue workflows passed at width '+width);
  }
  assert.deepEqual(errors,[]);
 }finally{ws.close();await fetch(endpoint+'/json/close/'+target.id);}
})().catch(error=>{console.error(error);process.exitCode=1;});
