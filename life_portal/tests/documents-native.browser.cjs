// All document APIs are intercepted; no live files or ERP records are changed.
const assert=require('node:assert/strict'),WebSocket=require('ws');
(async()=>{
 const endpoint=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9230',base=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5178';
 const target=await(await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json(),ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(resolve=>ws.on('open',resolve));
 let sequence=0,denyCircular=true,closing=false;const jobs=new Map(),calls=[],errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++sequence,m=>m.error?reject(new Error(JSON.stringify(m.error))):resolve(m.result));ws.send(JSON.stringify({id:sequence,method,params}));});
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
  if(m.method!=='Fetch.requestPaused')return;
  const{requestId,request}=m.params,method=new URL(request.url).pathname.split('/api/method/')[1],args=JSON.parse(request.postData||'{}');calls.push({method,args});let message={},status=200;
  if(method==='life_slimming.api.portal.bootstrap')message={user:'documents-fixture',session_id:'documents-fixture-'+target.id,full_name:'Documents Fixture',roles:['System Manager'],portal_role:'IT',csrf_token:'fixture'};
  if(method==='life_slimming.api.convox.config')message={enabled:false};
  if(method==='frappe.desk.reportview.get')message={keys:['name','modified','docstatus'],values:[['FORM-1','2026-10-13',0],['FORM-2','2026-10-13',0],['DENIED','2026-10-13',0]]};
  if(method==='frappe.client.get_list'){
   if(args.doctype==='Circular'&&denyCircular){status=403;message='Circular denied';}
   else message=[{name:args.doctype+'-1',modified:'2026-10-13',docstatus:args.filters?.[0]?.[2]||0}];
  }
  if(method==='frappe.client.get'){
   if(args.name==='DENIED'){status=403;message='Denied full document';}
   else if(args.doctype==='Forms And Documents')message={name:args.name,name1:args.name==='FORM-1'?'Client <form> & Photo':'Another Form',date:'2026-10-13',forms_and_documents:args.name==='FORM-1'?[{files:'/private/files/client%20form.pdf'},{file:'/files/photo.png'}]:[{attachment:'/files/other.pdf'}]};
   else if(args.doctype==='Life Rise SOPs')message={name:args.name,name1:'SOP without attachment',forms_and_document:[]};
   else if(args.doctype==='Circular')message={name:args.name,name1:'Clinic Circular',posting_date:'2026-10-13',documents:[{document_file:'/files/circular.pdf'}]};
   else if(args.doctype==='Service Certificates')message={name:args.name,name1:'Service Certificate',date:'2026-10-13',forms_and_documents:[{file_url:'/files/certificate.pdf'}]};
   else if(args.doctype==='Consent Form')message={name:args.name,name1:'Consent',posting_date:'2026-10-13',forms_and_document:[{attach_file:'/files/consent.pdf'}]};
   else message={name:args.name,title:args.doctype,posting_date:'2026-10-13',document:[{file:'/files/document.pdf'}]};
  }
  await send('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message,...(status!==200?{exc_type:'PermissionError'}:{})})).toString('base64')}).catch(error=>{if(!closing)errors.push(error.message);});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let n=0;n<150;n++){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,40));}throw Error('Timeout: '+expression+'\n'+await evaluate('document.body.innerText'));};
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 try{
  await send('Runtime.enable');await send('Page.enable');await send('Fetch.enable',{patterns:[{urlPattern:'*/api/method/*'}]});
  for(const width of[1440,390]){
   calls.length=0;denyCircular=true;await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<600});await send('Page.navigate',{url:base+'/life_portal/documents'});
   await wait('document.querySelectorAll("#fad-forms-grid .fad-card").length === 3 && document.querySelectorAll(".fad-loading").length === 0');
   assert.equal(await evaluate('!!document.querySelector("iframe")'),false);assert.equal(await evaluate('document.querySelectorAll(".fad-tab").length'),7);assert.equal(await evaluate('document.querySelector("#fad-count-badge").textContent.trim()'),'2 Documents');assert.equal(await evaluate('document.querySelector("#fad-pill-forms").textContent'),'2');
   assert.equal(await evaluate('document.querySelector(".fad-card-icon").textContent'),'📄');assert.equal(await evaluate('document.querySelector(".fad-card-title").textContent'),'Client <form> & Photo');assert.equal(await evaluate('document.querySelector(".fad-card-sub").textContent'),'13-Oct-2026');assert.equal(await evaluate('!!document.querySelector(".fad-card form")'),false);
   assert.equal(calls.filter(call=>['frappe.desk.reportview.get','frappe.client.get_list'].includes(call.method)).length,7,'all tab counts load together');
   const diet=calls.find(call=>call.args.doctype==='Diet'&&call.method==='frappe.client.get_list');assert.deepEqual(diet.args.filters,[['docstatus','=',0]]);const consent=calls.find(call=>call.args.doctype==='Consent Form'&&call.method==='frappe.client.get_list');assert.deepEqual(consent.args.filters,[['docstatus','=',1]]);
   await click('#fad-forms-grid .fad-card');await wait('!!document.querySelector("#fad-modal-overlay")');
   await evaluate(`window.__openFile=null;window.open=(...args)=>{window.__openFile=args;return null};window.__download=null;HTMLAnchorElement.prototype.click=function(){window.__download={url:this.href,name:this.download}}`);
   await click('#fad-open-document');assert.deepEqual(await evaluate('window.__openFile'),[base+'/private/files/client%20form.pdf','_blank','noopener,noreferrer']);
   await click('#fad-download-document');assert.equal((await evaluate('window.__download')).name,'client form.pdf');await click('#fad-modal-close');
   await click('[data-tab="sops"]');assert.equal(await evaluate('document.querySelector("#fad-panel-sops").textContent.includes("No documents attached")'),true);assert.equal(await evaluate('document.querySelector("#fad-count-badge").textContent.trim()'),'0 Documents');
   await click('[data-tab="circular"]');assert.equal(await evaluate('!!document.querySelector("#fad-panel-circular .fad-error")'),true);denyCircular=false;await click('#fad-panel-circular .fad-error button');await wait('document.querySelectorAll("#fad-circular-grid .fad-card").length === 1');assert.equal(await evaluate('document.querySelector("#fad-count-badge").textContent.trim()'),'1 Document');
   for(const key of['diet','audit','service','consent']){await click('[data-tab="'+key+'"]');assert.equal(await evaluate('document.querySelector("#fad-count-badge").textContent.trim()'),'1 Document');assert.equal(await evaluate('document.querySelectorAll("#fad-panel-'+key+' .fad-card").length'),1);}
   assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true);
   console.log('Forms & Documents Vue workflows passed at width '+width);
  }
  assert.deepEqual(errors,[]);
 }finally{closing=true;ws.close();await fetch(endpoint+'/json/close/'+target.id);}
})().catch(error=>{console.error(error);process.exitCode=1;});
