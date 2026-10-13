const assert=require('node:assert/strict');
const WebSocket=require('ws');
(async()=>{
 const endpoint=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9230',base=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5178';
 const target=await(await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(resolve=>ws.on('open',resolve));
 let sequence=0,denyOpen=false;const jobs=new Map(),calls=[],errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++sequence,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id:sequence,method,params}));});
 const fulfill=(id,message,status=200)=>send('Fetch.fulfillRequest',{requestId:id,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message,...(status!==200?{exc_type:'PermissionError'}:{})})).toString('base64')});
 const slimming='Slimming - LSACPL';
 const visit=(name,patient,date,before,after,plan='PLAN-ALPHA')=>({name,patient,start_date:date,before_weight:before,after_weight:after,therapy_plan:plan,docstatus:1});
 const current=[visit('CURRENT-1','ALPHA','2026-10-01',90,88),visit('CURRENT-2','ALPHA','2026-10-13',88,87),visit('BETA-CURRENT','BETA','2026-10-13',80,82,'PLAN-BETA')];
 const previous=[visit('PREVIOUS','ALPHA','2026-09-30',91,90)];
 const history=[visit('FIRST','ALPHA','2026-08-01',100,99),...previous,...current];
 const plan=(name,patient,start,extra={})=>({name,patient,start_date:start,category:slimming,status:'In Progress',docstatus:1,branch:'Branch A',total_sessions:20,total_sessions_completed:0,...extra});
 const plans=[plan('PLAN-ALPHA','ALPHA','2025-01-01'),plan('PLAN-NEW','NEW','2026-10-01',{status:'Not Started'}),plan('PLAN-NEW-B','NEW','2026-10-01',{branch:'Branch B'}),plan('PLAN-COMPLETE','COMPLETE','2026-10-01',{total_sessions_completed:20}),plan('PLAN-CANCEL','CANCEL','2026-10-01',{docstatus:2}),plan('PLAN-BETA','BETA','2025-01-01')];
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
  if(m.method!=='Fetch.requestPaused')return;
  const{requestId,request}=m.params;
  try{
   const method=decodeURIComponent(new URL(request.url).pathname.split('/api/method/')[1]||''),args=JSON.parse(request.postData||'{}');calls.push({method,args});
   if(method==='life_slimming.api.portal.bootstrap')return fulfill(requestId,{user:'weight-fixture@example.test',session_id:'weight-fixture',full_name:'Weight Fixture',roles:['Sales User'],portal_role:'IT',csrf_token:'fixture'});
   if(method==='life_slimming.api.convox.config')return fulfill(requestId,{enabled:false});
   if(method==='frappe.desk.search.search_link')return fulfill(requestId,[{value:'ALPHA',description:'Alpha Client'}]);
   if(method==='frappe.desk.reportview.get'){
    let rows=[];const filters=args.filters||[],has=(field,operator,value)=>filters.some(f=>f[1]===field&&f[2]===operator&&(value===undefined||f[3]===value));
    if(args.doctype==='Branch')rows=[{name:'Branch A',branch:'Branch A'},{name:'Branch B',branch:'Branch B'},{name:'Testing Branch',branch:'Testing Branch'},{name:'Head Office',branch:'Head Office'}];
    if(args.doctype==='Therapy Session'){
     if(args.fields.includes('therapy_plan')&&!args.fields.includes('before_weight'))rows=[visit('ATTEND-OLD','ALPHA','2026-10-01',90,88)];
     else rows=has('start_date','>=','2026-09-01')?previous:has('start_date','>=','2026-10-01')?current:history;
     const selected=filters.find(f=>f[1]==='patient'&&f[2]==='=');if(selected)rows=rows.filter(row=>row.patient===selected[3]);
    }
    if(args.doctype==='Therapy Plan'){
     if(args.fields.includes('docstatus')){if(denyOpen)return fulfill(requestId,'Open Cards unavailable',403);rows=plans;}
     else rows=plans.filter(plan=>['ALPHA','BETA'].includes(plan.patient));
    }
    if(args.doctype==='Patient')rows=['ALPHA','BETA','NEW','COMPLETE','CANCEL'].map(name=>({name,mobile:'+919876543210',branch_name:'Branch A'}));
    return fulfill(requestId,{keys:args.fields,values:rows.map(row=>args.fields.map(field=>row[field]))});
   }
   return fulfill(requestId,{});
  }catch(error){errors.push(error.stack);await fulfill(requestId,error.message,500);}
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let n=0;n<150;n++){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,40));}throw Error('Timeout: '+expression+'\n'+await evaluate('document.body.innerText'));};
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const input=(selector,value,event='input')=>evaluate(`(()=>{const el=document.querySelector(${JSON.stringify(selector)});el.value=${JSON.stringify(value)};el.dispatchEvent(new Event(${JSON.stringify(event)},{bubbles:true}));})()`);
 try{
  await send('Runtime.enable');await send('Page.enable');await send('Fetch.enable',{patterns:[{urlPattern:'*/api/method/*'}]});
  for(const width of [1440,390]){
   calls.length=0;denyOpen=false;
   await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<600});
   await send('Page.navigate',{url:base+'/life_portal/native/weight-loss'});
   await wait('document.querySelector("#totalClients")?.textContent.trim()==="2" && document.querySelector("#totalOpenCards")?.textContent.trim()==="2"');
   assert.equal(await evaluate('!!document.querySelector("iframe")'),false);
   assert.equal(await evaluate('document.querySelectorAll("#branchFilter option").length'),3);
   assert.equal(await evaluate('document.querySelector("#totalSessions").textContent.trim()'),'3');
   assert.equal(await evaluate('document.querySelector("#totalLossSummary").textContent.trim()'),'3.0 kg');
   assert.equal(await evaluate('document.querySelector("#avgLoss").textContent.trim()'),'1.5 kg');
   assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true);
   assert(calls.some(call=>call.args.doctype==='Therapy Session'&&call.args.filters.some(f=>f[1]==='start_date'&&f[3]==='2026-01-01')));
   await click('#totalOpenCardsCard');await wait('!!document.querySelector("#openCardsTableBody")');
   const open=await evaluate('document.querySelector("#openCardsTableBody").textContent');assert(open.includes('NEW'));assert(!open.includes('COMPLETE'));assert(!open.includes('CANCEL'));assert(open.includes('987****210'));assert(!open.includes('9876543210'));
   await click('#openCardsModalClose');await click('#weightTableBody tr');
   await wait('document.querySelector("#modalTotalLoss")?.textContent.includes("13.0")');
   assert.equal(await evaluate('document.querySelector("#modalTotalSessionSummary").textContent.trim()'),'4 / 20');
   assert.equal(await evaluate('document.querySelectorAll("#previousMonthSessionsBody tr").length'),1);
   assert.equal(await evaluate('document.querySelectorAll("#currentMonthSessionsBody tr").length'),2);
   assert.equal(await evaluate('document.querySelector("#modalClientName").textContent.includes("987****210")'),true);
   await click('#wlModalClose');await input('#weightLossFilter','gain','change');
   assert.equal(await evaluate('document.querySelector("#totalClients").textContent.trim()'),'1');
   assert.equal(await evaluate('document.querySelector("#weightTableBody").textContent.includes("BETA")'),true);
   await input('#weightLossFilter','','change');await input('#branchFilter','Branch B','change');
   assert.equal(await evaluate('document.querySelector("#totalOpenCards").textContent.trim()'),'1','multi-branch clients remain eligible in either branch');
   assert.equal(await evaluate('document.querySelector("#totalClients").textContent.trim()'),'0');
   await input('#branchFilter','','change');await input('#clientSearch','alpha');await wait('!!document.querySelector("#clientList button")');
   await click('#clientList button');await wait('document.querySelector("#totalClients").textContent.trim()==="1" && !document.querySelector("#refreshDashboard").disabled');
   assert(calls.some(call=>call.args.doctype==='Therapy Session'&&call.args.filters.some(f=>f[1]==='patient'&&f[2]==='='&&f[3]==='ALPHA')));
   assert.equal(await evaluate('document.querySelector("#totalOpenCards").textContent.trim()'),'1');
   await click('#clearClientSearch');await wait('document.querySelector("#totalClients").textContent.trim()==="2" && !document.querySelector("#refreshDashboard").disabled');
   await evaluate(`window.__exportName='';HTMLAnchorElement.prototype.click=function(){window.__exportName=this.download}`);
   await click('#sendMailBtn');assert.equal(await evaluate('window.__exportName'),'Client_Weight_Loss_October_2026.xls');
   await click('#totalOpenCardsCard');await click('#exportOpenCardsBtn');assert.match(await evaluate('window.__exportName'),/^Open_Cards_All_Branches_.*\.xls$/);await click('#openCardsModalClose');
   denyOpen=true;await click('#refreshDashboard');await wait('document.querySelector("#totalOpenCards").textContent.trim()==="-" && !document.querySelector("#refreshDashboard").disabled');
   assert.equal(await evaluate('document.querySelector("#totalClients").textContent.trim()'),'2','open card errors do not erase the monthly report');
   denyOpen=false;await click('#refreshDashboard');await wait('document.querySelector("#totalOpenCards").textContent.trim()==="2"');
   console.log('Weight Loss Vue workflows passed at width '+width);
  }
  assert.deepEqual(errors,[]);
  console.log('Passed: native Vue layout, monthly/lifetime weights, new joiners, attendance, completed/cancelled exclusion, multi-branch deduplication, client selection, filters, masked XLS exports and independent errors/retry.');
 }finally{ws.close();await fetch(endpoint+'/json/close/'+target.id);}
})().catch(error=>{console.error(error);process.exitCode=1;});
