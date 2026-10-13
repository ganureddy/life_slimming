// Native Vue workflows with mocked, permission-shaped ERP responses. No live writes.
const assert = require('node:assert/strict');
const WebSocket = require('ws');
(async () => {
 const endpoint = process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9230';
 const base = process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5178';
 const target = await (await fetch(endpoint + '/json/new?about:blank', {method:'PUT'})).json();
 const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise(resolve => ws.on('open',resolve));
 const jobs = new Map(), calls = [], errors = [], forms = new Map();
 let sequence = 0, manager = false, duplicate = false, failPhoto = false, photoUploads = 0;
 const send = (method,params={}) => new Promise((resolve,reject)=>{jobs.set(++sequence,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id:sequence,method,params}));});
 const fulfill = (id,message,status=200) => send('Fetch.fulfillRequest',{requestId:id,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message,...(status!==200?{exc_type:'PermissionError'}:{})})).toString('base64')});
 const patient = name => ({doctype:'Patient',name,patient_name:'Ravi Client',mobile:'9876543210',phone:'9123456789',custom_branch:'Branch A',custom_joining_date:'2026-10-13',custom_final_decision:'Not-Booked',custom_client_visited_for_:'Slimming',custom_remarks:'Call 9876543210 on 2026-10-13',image:'https://outside.test/photo.png'});
 ws.on('message', async raw => {
  const message=JSON.parse(raw);if(message.id){jobs.get(message.id)?.(message);jobs.delete(message.id);return;}
  if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails.exception?.description||message.params.exceptionDetails.text);
  if(message.method!=='Fetch.requestPaused')return;
  const {requestId,request}=message.params;
  try {
   const method=decodeURIComponent(new URL(request.url).pathname.split('/api/method/')[1]||'');
   const args=method==='upload_file'?{}:JSON.parse(request.postData||'{}');calls.push({method,args});
   if(method==='life_slimming.api.portal.bootstrap')return fulfill(requestId,{user:'vue-agent@example.test',session_id:'unjoined-vue-fixture',full_name:'Vue Agent',roles:manager?['System Manager']:['Sales User'],portal_role:'IT',csrf_token:'fixture'});
   if(method==='life_slimming.api.convox.config')return fulfill(requestId,{enabled:false});
   if(method==='frappe.client.get_list'){
    const {doctype,fields=[],filters={}}=args;
    if(doctype==='Branch')return fulfill(requestId,[{name:'Branch A'},{name:'Testing Branch'}]);
    if(doctype==='File')return fulfill(requestId,[{name:'FILE-1',file_name:'Attachment 9876543210',file_url:'/files/attachment.pdf'},{name:'FILE-2',file_name:'Outside',file_url:'https://outside.test/photo.png'}]);
    if(doctype==='Unjoined Client Form'&&!Array.isArray(filters)){
     if(filters.custom_source_document&&typeof filters.custom_source_document==='string'){
      if(duplicate)return fulfill(requestId,[{name:'DUP-1'},{name:'DUP-2'}]);
      return fulfill(requestId,[...forms.values()].filter(form=>form.custom_source_document===filters.custom_source_document).map(form=>({name:form.name})));
     }
     if(Array.isArray(filters.custom_source_document))return fulfill(requestId,[...forms.values()]);
     return fulfill(requestId,[]);
    }
    if(doctype==='Patient'&&!Array.isArray(filters))return fulfill(requestId,[{name:'PAT-LINKED'}]);
    if(fields.includes('count(name) as total'))return fulfill(requestId,[{total:doctype==='Patient'?21:doctype==='Unjoined Client Form'?forms.size:1}]);
    if(doctype==='Patient')return fulfill(requestId,args.limit_start===20?[patient('PAT-21')]:Array.from({length:args.limit_page_length===500?21:20},(_,i)=>patient('PAT-'+(i+1))));
    if(doctype==='Lead')return fulfill(requestId,[{name:'LEAD-1',lead_name:'Lead Client',mobile_no:'9876543210',branch:'Branch A',category:'Slimming',custom_appointment_status:'Booked',custom_appointment_date_and_time:'2026-10-12 10:00:00'}]);
    if(doctype==='Patient Appointment')return fulfill(requestId,[{name:'APPT-1',patient:'PAT-LINKED',patient_name:'Appointment Client',custom_client_mobile_no:'9876543210',branch:'Branch A',appointment_date:'2026-10-13',status:'Scheduled'}]);
    if(doctype==='Unjoined Client Form')return fulfill(requestId,[...forms.values()]);
    return fulfill(requestId,[]);
   }
   if(method==='frappe.client.get'){
    if(args.doctype==='Patient')return fulfill(requestId,patient(args.name));
    if(args.doctype==='Unjoined Client Form')return fulfill(requestId,forms.get(args.name));
    if(args.doctype==='Lead')return fulfill(requestId,{doctype:'Lead',name:args.name,lead_name:'Lead Client',mobile_no:'9876543210',branch:'Branch A',category:'Slimming'});
    return fulfill(requestId,{doctype:args.doctype,name:args.name,patient:'PAT-LINKED',patient_name:'Appointment Client',custom_client_mobile_no:'9876543210',branch:'Branch A'});
   }
   if(['frappe.client.insert','frappe.client.save'].includes(method)){
    const doc={...args.doc,name:args.doc.name||'UJ-'+(forms.size+1)};forms.set(doc.name,doc);return fulfill(requestId,doc);
   }
   if(method==='upload_file'){
    photoUploads++;if(failPhoto)return fulfill(requestId,'Photo denied',403);
    return fulfill(requestId,{file_url:'/private/files/photo.png'});
   }
   return fulfill(requestId,{});
  } catch(error){errors.push(error.stack);await fulfill(requestId,error.message,500);}
 });
 const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);return result.result.value;};
 const wait=async expression=>{for(let tries=0;tries<150;tries++){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,40));}throw Error('Timeout: '+expression+'\n'+await evaluate('document.body.innerText'));};
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const input=(selector,value,event='input')=>evaluate(`(() => {const el=document.querySelector(${JSON.stringify(selector)});el.value=${JSON.stringify(value)};el.dispatchEvent(new Event(${JSON.stringify(event)},{bubbles:true}));})()`);
 try {
  await send('Runtime.enable');await send('Page.enable');await send('Fetch.enable',{patterns:[{urlPattern:'*/api/method/*'}]});
  for(const width of [1440,390]){
   forms.clear();duplicate=false;manager=false;calls.length=0;
   await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<600});
   await send('Page.navigate',{url:base+'/life_portal/unjoined'});
   await wait('document.querySelector("#ujNotice")?.textContent.startsWith("Loaded")');
   assert.equal(await evaluate('!!document.querySelector("iframe")'),false,'native route has no legacy frame');
   assert.equal(await evaluate('document.querySelectorAll("#ujBranch option").length'),2);
   assert.equal(await evaluate('document.querySelectorAll("#uj-clients tbody tr").length'),20);
   assert.equal(await evaluate('document.querySelector("#uj-clients").textContent.includes("9876543210")'),false);
   assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true,'no viewport overflow');
   await click('#uj-clients .uj-paging button:last-child');
   await wait('document.querySelector("#uj-clients .uj-person small")?.textContent === "PAT-21"');
   assert(calls.some(call=>call.args.doctype==='Patient'&&call.args.limit_start===20));
   await input('#ujFrom','2026-10-01');await input('#ujTo','2026-10-13');await input('#ujBasis','created','change');await input('#ujSearch','Ravi');
   await click('#ujApply');await wait('document.querySelector("#uj-clients .uj-person small")?.textContent === "PAT-1" && !document.querySelector("#ujApply").disabled');
   const read=calls.filter(call=>call.args.doctype==='Patient'&&Array.isArray(call.args.filters)).at(-1);
   assert(read.args.filters.some(filter=>filter[0]==='creation'&&filter[1]==='<'&&filter[2]==='2026-10-14'));
   assert(read.args.filters.some(filter=>filter[0]==='custom_branch'&&filter[1]==='!='&&filter[2]==='Testing Branch'));
   await click('#uj-clients .uj-primary');
   await wait('document.querySelector("#ujEdit-contact_number") && !document.querySelector("#ujSaveForm").disabled');
   assert.equal(await evaluate('document.querySelector("#ujEdit-contact_number").value'),'987****210');
   assert.equal(await evaluate('document.querySelector("#ujEdit-contact_number").readOnly'),true);
   await input('#ujEdit-status','Follow Up Scheduled','change');
   assert.equal(await evaluate('document.querySelector("#ujEdit-next_follow_up_scheduled_date").required'),true);
   const inserts=calls.filter(call=>call.method==='frappe.client.insert').length;
   await click('#ujSaveForm');await new Promise(resolve=>setTimeout(resolve,100));
   assert.equal(calls.filter(call=>call.method==='frappe.client.insert').length,inserts,'date is required before saving');
   await input('#ujEdit-next_follow_up_scheduled_date','2026-10-15');await input('#ujEdit-remarks','Call 987****210 on 2026-10-13');
   await click('#ujSaveForm');await wait('document.querySelector("#ujSaveState")?.textContent.startsWith("Saved successfully") && !document.querySelector("#ujSaveForm").disabled');
   const created=calls.find(call=>call.method==='frappe.client.insert').args.doc;
   assert.equal(created.contact_number,'9876543210');assert.equal(created.custom_source_document,'PAT-1');assert.equal(created.custom_source_doctype,'Patient');assert.equal(created.custom_linked_client,'PAT-1');assert.match(created.custom_source_key,/^[a-f0-9]{64}$/);
   await click('.uj-detail-tabs button:first-child');await wait('document.querySelector("#ujDetails").textContent.includes("Unjoined Client Form")');
   assert.equal(await evaluate('document.querySelector("#ujDetails").textContent.includes("9876543210")'),false);
   assert.equal(await evaluate('Array.from(document.querySelectorAll("#ujDetails a")).some(a=>a.href.includes("outside.test"))'),false);
   await click('#ujClose');duplicate=true;
   await click('#uj-clients .uj-primary');await wait('document.querySelector("#ujFollowPane").textContent.includes("Multiple follow-up records")');
   assert.equal(await evaluate('document.querySelector("#ujSaveForm").disabled'),true);await click('#ujClose');duplicate=false;
   await click('#uj-clients .uj-primary');await wait('document.querySelector("#ujEditForm") && !document.querySelector("#ujSaveForm").disabled');
   await evaluate(`(()=>{const input=document.querySelector('#ujPhotoFile'),transfer=new DataTransfer();transfer.items.add(new File(['image-fixture'],'photo.png',{type:'image/png'}));input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));})()`);
   await click('#ujSaveForm');await wait('document.querySelector("#ujSaveState")?.textContent.startsWith("Saved successfully") && !document.querySelector("#ujSaveForm").disabled');
   assert(photoUploads>0);assert.equal(calls.filter(call=>call.method==='frappe.client.insert').length,1,'editing reuses linked followup');assert.equal(forms.get('UJ-1').custom_client_photo_attach,'/private/files/photo.png');
   await click('#ujClose');
   await evaluate(`window.__exportName='';HTMLAnchorElement.prototype.click=function(){window.__exportName=this.download};`);
   await click('.uj-tools button:first-of-type');await wait('window.__exportName.endsWith(".xlsx") && document.querySelector("#ujNotice").textContent.startsWith("Prepared")');
   assert(calls.some(call=>call.args.limit_page_length===500),'export reads all filtered records');
   await click('#ujCards button:nth-child(3)');
   assert.equal(await evaluate('document.querySelectorAll("#ujSections section").length'),2);
   assert.equal(await evaluate('document.querySelector("#uj-pending").textContent.includes("Overdue")'),true);
   assert.equal(await evaluate('document.querySelector("#uj-appointments").textContent.includes("Today")'),true);
   console.log('Unjoined Vue workflows passed at width '+width);
  }
  manager=true;
  await send('Page.navigate',{url:base+'/life_portal/native/unjoined'});await wait('document.querySelector("#ujNotice")?.textContent.startsWith("Loaded")');
  assert.equal(await evaluate('document.querySelector("#uj-clients").textContent.includes("9876543210")'),true);
  assert.deepEqual(errors,[]);
  console.log('Passed: native route, five cohorts/four tabs, filters, masking, pagination, required followup date, source-linked insert/save, photo upload, duplicate protection, full export and manager visibility.');
 } finally {ws.close();await fetch(endpoint+'/json/close/'+target.id);}
})().catch(error=>{console.error(error);process.exitCode=1;});
