const assert=require('node:assert/strict'),WebSocket=require('ws');
(async()=>{
 const endpoint=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9230',base=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5178';
 const target=await(await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json(),ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(resolve=>ws.on('open',resolve));
 let sequence=0,manager=false,permitted=['Branch A','Branch B'],closing=false;const jobs=new Map(),calls=[],errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++sequence,m=>m.error?reject(new Error(JSON.stringify(m.error))):resolve(m.result));ws.send(JSON.stringify({id:sequence,method,params}));});
 const rows=Array.from({length:25},(_,i)=>({invoice:'INV-A-'+(i+1),invoice_date:'2026-10-14',branch:'Branch A',customer:'Alice Client '+(i+1),booking_type:'Call Center',referring_employee:'Alice',incentive_employee:'Bob',mode_of_payment:'Cash',paid_amount:'₹1,050.00',grand_total:2100,outstanding_amount:i%2?0:1050}));
 const raw=[{invoice:'Total',is_total_row:1},['invalid row'],...rows,{...rows[0]},{invoice:'INV-B',invoice_date:'2026-10-14',branch:'Branch B',customer:'Carol Client',booking_type:'Walk In',referring_employee:'Carol',mode_of_payment:'Credit Card',paid_amount:525,gst_amount:25,paid_amount_without_gst:500,grand_total:525,outstanding_amount:0},{invoice:'FOREIGN',branch:'Foreign Branch',customer:'Foreign Client',paid_amount:999999}];
 ws.on('message',async value=>{
  const m=JSON.parse(value);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
  if(m.method!=='Fetch.requestPaused')return;
  const{requestId,request}=m.params,url=new URL(request.url),method=url.pathname.split('/api/method/')[1];let args=JSON.parse(request.postData||'{}');if(method==='frappe.desk.query_report.run'&&!request.postData)args=Object.fromEntries(url.searchParams);
  calls.push({method,args,headers:request.headers});let message={},headers=[{name:'Content-Type',value:'application/json'}],body;
  if(method==='life_slimming.api.portal.bootstrap')message={user:'sales-master-fixture',session_id:'sales-master-fixture-'+target.id+(manager?'manager':permitted.length),full_name:'Sales Fixture',roles:manager?['System Manager']:['Sales User'],portal_role:'IT',csrf_token:'sales-fixture'};
  if(method==='life_slimming.api.convox.config')message={enabled:false};
  if(method==='frappe.client.get_list')message=permitted.map(name=>({name}));
  if(method==='frappe.desk.query_report.run')message={result:raw};
  if(method==='frappe.desk.query_report.export_query'){body=Buffer.from('fixture-xlsx');headers=[{name:'Content-Type',value:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},{name:'Content-Disposition',value:'attachment; filename="Sales_Report.xlsx"'}];}
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:headers,body:(body||Buffer.from(JSON.stringify({message}))).toString('base64')}).catch(error=>{if(!closing)errors.push(error.message);});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let n=0;n<150;n++){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,40));}throw Error('Timeout: '+expression+'\n'+await evaluate('document.body.innerText'));};
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const input=(selector,value,event='input')=>evaluate(`(()=>{const el=document.querySelector(${JSON.stringify(selector)});el.value=${JSON.stringify(value)};el.dispatchEvent(new Event(${JSON.stringify(event)},{bubbles:true}));})()`);
 async function select(id,value){await click('#'+id+' .rr-ss-display');await wait('!!document.querySelector("#'+id+' .rr-ss-drop")');await click('#'+id+' [data-val="'+value+'"]');}
 const reports=()=>calls.filter(call=>call.method==='frappe.desk.query_report.run');
 try{
  await send('Runtime.enable');await send('Page.enable');await send('Fetch.enable',{patterns:[{urlPattern:'*/api/method/*'}]});
  for(const width of[1440,390]){
   manager=false;permitted=['Branch A','Branch B'];calls.length=0;await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<600});await send('Page.navigate',{url:base+'/life_portal/native/sales-master'});
   await wait('document.querySelector(".rr-pginfo")?.textContent.includes("26 records")');
   assert.equal(await evaluate('!!document.querySelector("iframe")'),false);assert.equal(await evaluate('document.querySelectorAll(".rr-table thead th").length'),12);assert.equal(await evaluate('document.querySelectorAll(".rr-table tbody tr").length'),20);assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true);
   assert.deepEqual(reports().map(call=>JSON.parse(call.args.filters).branch),['Branch A','Branch B']);assert.equal(await evaluate('document.querySelector(".rr-table").textContent.includes("Foreign Client")'),false);assert.equal(await evaluate('document.querySelector(".rr-table tbody tr td:nth-child(2)").textContent'),'14-Oct-26');assert.equal(await evaluate('document.querySelector(".rr-table thead th:nth-child(9)").textContent'),'Therapy Type');assert.equal(await evaluate('document.querySelector(".rr-table tbody tr td:nth-child(11)").textContent'),'₹1,000.00');
   await click('#rr_pg_next');await wait('document.querySelectorAll(".rr-table tbody tr").length === 6');await click('#rr_pg_first');
   await click('#rr_ss_sp .rr-ss-display');await input('#rr_ss_sp .rr-ss-search','bob');assert.equal(await evaluate('document.querySelectorAll("#rr_ss_sp .rr-ss-opt").length'),1);await click('#rr_ss_sp [data-val="Bob"]');
   assert.equal(await evaluate('document.querySelector(".rr-pginfo").textContent.includes("26 records")'),true,'draft filters do not silently change the loaded report');
   await input('#rr_from','2026-10-01');await input('#rr_to','2026-10-14');await click('#rr_apply_btn');await wait('document.querySelector(".rr-pginfo")?.textContent.includes("25 records") && !document.querySelector("#rr_apply_btn").disabled');
   await input('#rr_out_operator','>','change');await input('#rr_out_value','0');await click('#rr_apply_btn');await wait('document.querySelector(".rr-pginfo")?.textContent.includes("13 records") && !document.querySelector("#rr_apply_btn").disabled');
   await evaluate(`window.__downloads=[];window.__downloadBlobs=[];URL.createObjectURL=blob=>{window.__downloadBlobs.push(blob);return 'blob:fixture'};HTMLAnchorElement.prototype.click=function(){window.__downloads.push({name:this.download,url:this.href})}`);await click('[data-f="csv"]');await click('#rr_dl_btn');await wait('window.__downloads.length === 1 && !document.querySelector("#rr_dl_btn").disabled');
   assert.match(await evaluate('window.__downloads[0].name'),/All-Branches.*\.csv$/);assert.equal(calls.some(call=>call.method==='frappe.desk.query_report.export_query'),false,'restricted all-branch export does not send a blank-branch export request');
   await input('#rr_amt_from','2000');await input('#rr_amt_to','1000');const before=reports().length;await click('#rr_apply_btn');await wait('document.querySelector("#rr_msg").textContent.includes("cannot exceed")');assert.equal(reports().length,before);
   await input('#rr_amt_from','');await input('#rr_amt_to','');await input('#rr_out_operator','','change');await select('rr_ss_branch','Branch A');await click('#rr_apply_btn');await wait('!document.querySelector("#rr_apply_btn").disabled && document.querySelector("#rr_branch").value === "Branch A"');
   await input('#rr_customer','Alice Client 1');await click('[data-f="xlsx"]');await click('#rr_dl_btn');await wait('window.__downloads.some(file=>file.name.endsWith(".xls"))');
   const exported=await evaluate('window.__downloadBlobs.at(-1).text()');assert(exported.includes('Therapy Type'));assert(exported.includes('Alice Client 1'));assert(!exported.includes('Carol Client'));assert(!exported.includes('Foreign Client'));assert(exported.includes('ss:Type="Number">1000'));assert.equal(calls.some(call=>call.method==='frappe.desk.query_report.export_query'),false,'exports retain current source client-side filtering for every role');
   console.log('Sales Master Vue workflows passed at width '+width);
  }
  permitted=['Branch A'];calls.length=0;await send('Page.navigate',{url:base+'/life_portal/native/sales-master'});await wait('document.querySelector(".rr-pginfo")?.textContent.includes("25 records")');assert.equal(await evaluate('document.querySelector("#rr_ss_branch .rr-ss-display").disabled'),true);assert.equal(reports().every(call=>JSON.parse(call.args.filters).branch==='Branch A'),true);
  manager=true;permitted=['Branch A','Branch B'];calls.length=0;await send('Page.navigate',{url:base+'/life_portal/native/sales-master'});await wait('!!document.querySelector(".rr-pginfo")');assert.equal(reports().length,1);assert.equal(JSON.parse(reports()[0].args.filters).branch,'');
  assert.deepEqual(errors,[]);
 }finally{closing=true;ws.close();await fetch(endpoint+'/json/close/'+target.id);}
})().catch(error=>{console.error(error);process.exitCode=1;});
