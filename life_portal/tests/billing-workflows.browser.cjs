// Local Vite :5175 + isolated Chrome :9225; every business API is mocked.
const WebSocket = require('../node_modules/ws');
const assert = require('node:assert/strict');
(async()=>{
 const target=await(await fetch('http://127.0.0.1:9225/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));
 let olderPaid=false;
 let id=0,docstatus=0,outstanding=1050,registered=false,approved=false,rejected=false;const jobs=new Map(),errors=[],calls=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++id,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id,method,params}));});


 const boot={user:'Administrator',branches:['A','B'],allowed_branches:['A'],user_branch:'A',is_head_office:0,practitioners:[{name:'DOC-1',practitioner_name:'Doctor One',designation:'Doctor',branch:'A',status:'Active'},{name:'DOC-2',practitioner_name:'Other Branch Doctor',designation:'Doctor',branch:'B',all_branches:1,status:'Active'},{name:'EMP-1',practitioner_name:'Consultant One',branch:'A',status:'Active'}],therapies:[{n:'Therapy A',item:'TA',rate:1000,min:800,max:1200,show_in_billing:1}],templates:[{name:'PKG',plan_name:'Package',offer_price:900,lines:[{therapy_type:'Therapy A',no_of_sessions:1,rate:1000}]}],comp_items:[],offers:[],approvers:[{user:'Administrator',full_name:'Admin',approval_level:'L1'},{user:'md',full_name:'MD',approval_level:'L4'}],modes:[{name:'Cash',type:'Cash'},{name:'Bank',type:'Bank'},{name:'Carepay',type:'Bank'}]};
 const patient={name:'PAT-1',patient_name:'Test Client',mobile:'9876543210',custom_branch:'A'};
 const invoice=()=>({name:'INV-1',patient:'PAT-1',patient_name:'Test Client',branch:'A',docstatus,grand_total:1050,outstanding_amount:outstanding,status:docstatus?'Unpaid':'Draft',posting_date:'2026-10-05',net_total:1000,total_taxes_and_charges:50,custom_product_cost:300,custom_clinical_operational_cost:700,custom_total_cost:1050,custom_net_profit:0,items:[{name:'I1',item_name:'Therapy A',qty:1,rate:1000,amount:1000}]});
 ws.on('message',async raw=>{
  const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
  if(m.method!=='Fetch.requestPaused')return;
  const {requestId,request}=m.params;let args={};try{args=JSON.parse(request.postData||'{}');}catch{}calls.push({url:request.url,args});let result={ok:true};
  if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'Native Billing Tester',roles:['System Manager'],csrf_token:'test'};
  if(request.url.includes('lifescc_billing_bootstrap.run'))result={...boot,discount_requests:args.invoice_name?[{name:'REQ-1',linked_invoice:'INV-1',status:rejected?'Rejected':approved?'Approved':'Pending',selected_approver:'Administrator',approval_level:'L1',requested_discount_pct:5,bill_total:1050,reason:'Test discount'}]:[]};
  if(request.url.includes('frappe.client.get_list')){
    if(args.doctype==='Patient')result=(args.filters?.some(f=>f[0]==='mobile'&&f[1]==='=')&&!registered)?[]:[patient];
    else if(args.doctype==='Sales Invoice')result=args.fields.some(f=>f.includes('sum('))?[{outstanding, count:1, billed:1050, due:outstanding}]:[invoice()];
    else result=[];
    if(args.doctype==='Patient' && args.or_filters?.some(f=>f[2]==='%Slow%')){result=[{...patient,patient_name:'Slow Client'}];await new Promise(r=>setTimeout(r,500));}
  }
  if(request.url.includes('frappe.client.get_count'))result=args.filters?.some(f=>f[0]==='patient')?(olderPaid?1:0):1;
  if(request.url.includes('get_html_and_style'))result={html:'<h1>Rendered invoice INV-1</h1>',style:'h1{color:green}'};
  if(request.url.endsWith('frappe.client.get'))result=args.doctype==='Patient'?patient:invoice();
  if(request.url.includes('create_plan_and_invoice_test.run'))result={sales_invoice:'INV-1',grand_total:1050};
  if(request.url.includes('apply_invoice_discount_net_final_v2.run')){approved=true;result={grand_total:997.5};}
  if(request.url.includes('frappe.client.set_value')){if(args.doctype==='Discount Approval Request')rejected=true;result={name:args.name};}
  if(request.url.includes('submit_invoice.run')){docstatus=1;result={sales_invoice:'INV-1'};}
  if(request.url.includes('collect_payment_v4.run')){outstanding=0;result={payment_entries:['PE-1'],allocated:JSON.parse(args.payments).reduce((sum,p)=>sum+p.amount,0),outstanding:0};}
  if(request.url.includes('create_payment_link'))result={short_url:'https://example.invalid/pay',payment_link_id:'LINK-1'};
  if(request.url.includes('check_payment_link_payment')){outstanding=0;result={status:'paid',payment_entry:'PE-RZ',payment_id:'RZ-1'};}
  if(request.url.includes('send_client_whatsapp_otp'))result={status:'sent'};
  if(request.url.includes('verify_client_otp'))result='verified';
  if(request.url.includes('upload_file'))result={file_url:'/private/files/pd.pdf'};
  if(request.url.includes('create_client.run')){registered=true;result={name:'PAT-1'};}
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')}).catch(error=>{if(!/Invalid InterceptionId|Invalid interceptionId|Invalid requestId/i.test(error.message || ''))throw error;});
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);return r.result.value;};
 const wait=async expression=>{for(let i=0;i<150;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,75));}throw Error('Timed out: '+expression+'\n'+await evaluate('document.body.innerText'));};
 const click=async text=>{await wait(`Array.from(document.querySelectorAll('.billing-native button')).some(b=>(()=>{const c=b.cloneNode(true);c.querySelectorAll('.tab-icon,.billing-count').forEach(n=>n.remove());return c.textContent.trim();})()===${JSON.stringify(text)} && !b.disabled)`);return evaluate(`Array.from(document.querySelectorAll('.billing-native button')).find(b=>(()=>{const c=b.cloneNode(true);c.querySelectorAll('.tab-icon,.billing-count').forEach(n=>n.remove());return c.textContent.trim();})()===${JSON.stringify(text)} && !b.disabled).click()`);};
 const screenshot=async name=>{const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});require('node:fs').writeFileSync('/tmp/billing-ui-'+name+'.png',Buffer.from(shot.data,'base64'));};
 const fill=(label,value)=>evaluate(`(()=>{const label=Array.from(document.querySelectorAll('.billing-native label')).find(l=>l.firstChild.textContent.trim()===${JSON.stringify(label)});if(!label)throw Error('Missing label '+${JSON.stringify(label)});const input=label.querySelector('input,select,textarea');input.value=${JSON.stringify(String(value))};input.dispatchEvent(new Event(input.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);
 try{
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:5175/api/*'}]});
  for(const width of [1440,390]){
   docstatus=0;outstanding=1050;approved=false;rejected=false;registered=false;calls.length=0;
   await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
   await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/native/billing'});
   await wait("document.querySelector('nav[aria-label=\"Billing views\"]') && document.querySelector('.billing-native select option')");
   await wait("document.querySelectorAll('.billing-overview .billing-kpi').length===4");
   assert.ok(await evaluate("document.querySelector('.billing-hero') && document.querySelector('.billing-empty')"));
   await screenshot('home-'+width);
   await fill('Search clients','Slow');await click('Search');
   await wait("document.querySelector('.billing-search-status')");await fill('Search clients','');
   await new Promise(r=>setTimeout(r,650));
   assert.equal(await evaluate("document.querySelector('.billing-search-results')===null"),true);
   await fill('Search clients','Test');await click('Search');await wait("document.querySelector('.billing-native').textContent.includes('Test Client · PAT-1')");
   await evaluate("Array.from(document.querySelectorAll('.billing-native button')).find(b=>b.textContent.includes('Test Client · PAT-1')).click()");
   await wait("Array.from(document.querySelectorAll('.billing-native button')).some(b=>b.textContent==='New bill')");
   await click('New bill');await fill('Consultant Employee','Consultant');await click('Consultant One');await fill('Source / Media','DIRECT WALKIN');await fill('Doctor consultant (optional)','DOC-1');
   assert.ok(!await evaluate("Array.from(document.querySelectorAll('label')).find(l=>l.firstChild.textContent.trim()==='Doctor consultant (optional)').textContent.includes('Other Branch Doctor')"));
   assert.equal(await evaluate("document.querySelectorAll('.billing-block').length"),5);
   assert.ok(await evaluate("document.querySelector('.billing-sticky-summary')"));
   await click('📦 Package / Template');await fill('📋 Load from Therapy Plan Template','PKG');
   await wait("document.querySelector('.billing-sticky-summary').textContent.includes('Package discount')");
   assert.equal(await evaluate("document.querySelector('#bl-disc-sec')===null && document.querySelector('#bl-coupon-sec')===null"),true);
   await click('🧾 Individual Therapy');
   await wait("document.querySelector('#bl-disc-sec') && !document.querySelector('.billing-sticky-summary').textContent.includes('Package discount')");
   await screenshot('editor-'+width);
   await fill('Therapy','Therapy A');await evaluate("document.querySelector('.billing-therapy-results button').click()");
   await fill('Therapy','Unknown therapy');await click('👁 Preview Invoice');
   assert.equal(await evaluate("document.querySelector('.billing-review-panel')===null"),true);
   await fill('Therapy','Therapy A');await evaluate("document.querySelector('.billing-therapy-results button').click()");await click('👁 Preview Invoice');await wait("document.querySelector('.billing-review-panel')");
   await send('Emulation.setEmulatedMedia',{media:'print'});
   assert.equal(await evaluate("getComputedStyle(document.querySelector('.billing-review-panel footer')).display"),'none');
   assert.equal(await evaluate("getComputedStyle(document.querySelector('.billing-review-panel')).visibility"),'visible');
   await send('Emulation.setEmulatedMedia',{media:''});
   await screenshot('preview-'+width);
   await click('✅ Confirm & Generate Invoice');await wait("document.querySelector('.billing-invoice') && document.querySelector('.billing-invoice').textContent.includes('Pending')");
   const payload=calls.find(c=>c.url.includes('create_plan_and_invoice_test.run')).args;
   assert.equal(payload.doctor_practitioner,'DOC-1');assert.equal(payload.doctor_name,'Doctor One');assert.equal(payload.patient,'PAT-1');assert.equal(payload.draft_only,1);assert.equal(payload.lines[0].therapy_type,'Therapy A');
   await evaluate("window.open=(...args)=>{window.__billingPrint=args;return null;}");
   await click('View bill');
   assert.ok(await evaluate("document.querySelector('.billing-cost-details').textContent.includes('Net profit')"));
   await screenshot('invoice-'+width);
   assert.ok(await evaluate("window.__billingPrint[0].includes('INV-1') && window.__billingPrint[2]==='noopener,noreferrer'"));
   await click('Approve discount');await click('Confirm approval');await wait("document.querySelector('.billing-invoice').textContent.includes('Discount approved.')");
   await click('Submit invoice');await click('Confirm submit');await wait("document.querySelector('.billing-invoice').textContent.includes('Collect payment · INV-1')");
   await fill('Amount','1100');await click('Record collection');await wait("document.querySelector('.billing-invoice').textContent.includes('Payments exceed')");
   assert.equal(calls.filter(c=>c.url.includes('collect_payment_v4.run')).length,0);
   await fill('Amount','1050');await click('Record collection');await wait("document.querySelector('.billing-invoice').textContent.includes('Payment receipt')");
   assert.equal(calls.filter(c=>c.url.includes('collect_payment_v4.run')).length,1);
   const payment=calls.find(c=>c.url.includes('collect_payment_v4.run')).args;assert.equal(JSON.parse(payment.payments)[0].amount,1050);
   assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
   await click('Close collection');await wait("!document.querySelector('.billing-native').textContent.includes('Collect payment · INV-1')");await click('Close invoice');
   await click('Register client');
   for(const [label,value] of [['Full name *','New Client'],['Mobile *','9876543210'],['Gender *','Female'],['Consultation employee *','EMP-1'],['Visited for *','Skin'],['Decision *','Booked'],['Treatment category *','Skin/Laser'],['PD form number *','PD-1']])await fill(label,value);
   await evaluate(`(()=>{const input=Array.from(document.querySelectorAll('.billing-native input[type=file]'))[0];const transfer=new DataTransfer();transfer.items.add(new File(['PD'],'pd.pdf',{type:'application/pdf'}));input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));})()`);
   await screenshot('registration-'+width);
   await click('Send WhatsApp OTP');await wait("document.querySelector('.billing-native').textContent.includes('Six-digit OTP')");
   await fill('Six-digit OTP','123456');await click('Verify OTP');await wait("document.querySelector('.billing-native').textContent.includes('Mobile verified.')");
   await click('Register client');await wait("document.querySelector('.billing-native').textContent.includes('Client registered.')");
   assert.equal(calls.filter(c=>c.url.includes('create_client.run')).length,1);
   assert.equal(calls.find(c=>c.url.includes('create_client.run')).args.pd_form_file,'/private/files/pd.pdf');
   assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
   await click('Recent bills');await wait("document.querySelector('.billing-native tbody tr')");
   await click('Pending dues');await wait("document.querySelector('.billing-month')");
   await screenshot('pending-'+width);
   await click('All dates');await wait("document.querySelector('.billing-month tbody tr')");
   const pendingCall=calls.filter(c=>c.url.includes('frappe.client.get_list')&&c.args.doctype==='Sales Invoice').at(-1);
   assert.ok(!pendingCall.args.filters.some(f=>f[0]==='posting_date'));
   await click('This business month');await wait("document.querySelector('.billing-month tbody tr')");
   await click('Collapse all');assert.equal(await evaluate("document.querySelectorAll('.billing-month tbody tr').length"),0);
   await click('Expand all');await wait("document.querySelector('.billing-month tbody tr')");
   await click('Approvals');await wait("document.querySelector('.billing-native').textContent.includes('No pending discount requests')");
   assert.equal(await evaluate("document.querySelectorAll('iframe').length"),0);
  }

  olderPaid=true;
  await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/native/billing'});
  await wait("document.querySelector('.billing-hero')");await fill('Search clients','Test');await click('Search');
  await wait("document.querySelector('.billing-search-results button')");await evaluate("document.querySelector('.billing-search-results button').click()");
  await click('New bill');
  assert.equal(await evaluate("Array.from(document.querySelectorAll('label')).find(l=>l.firstChild.textContent.trim()==='Source / Media').querySelector('select').value"),'Existing Customer');
  assert.ok(await evaluate("Array.from(document.querySelectorAll('label')).find(l=>l.firstChild.textContent.trim()==='Source / Media').querySelector('select').disabled"));
  olderPaid=false;
  docstatus=1;outstanding=1050;
  await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/native/billing?invoice=INV-1'});
  await wait("document.querySelector('.billing-invoice') && document.querySelector('.billing-invoice').textContent.includes('Submitted')");
  await click('Collect payment');await fill('Mode','Razorpay Software Pvt Ltd -Link');await fill('Amount','1050');
  await click('Payment link + QR');await wait(`document.querySelector('a[href="https://example.invalid/pay"]')?.parentElement.textContent.includes('paid ·')`);
  const manualBefore=calls.filter(c=>c.url.includes('collect_payment_v4.run')).length;
  await click('Record collection');await wait("document.querySelector('.billing-invoice').textContent.includes('PE-RZ')");
  assert.equal(calls.filter(c=>c.url.includes('collect_payment_v4.run')).length,manualBefore);
  docstatus=0;outstanding=1050;approved=false;rejected=false;
  await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/native/billing?invoice=INV-1'});
  await wait("document.querySelector('.billing-invoice') && document.querySelector('.billing-invoice').textContent.includes('Pending')");
  await click('Reject discount');await fill('Rejection reason','Incorrect request');await click('Confirm rejection');
  await wait("document.querySelector('.billing-invoice').textContent.includes('Request rejected.')");
  assert.ok(calls.some(c=>c.url.includes('frappe.client.set_value') && c.args.fieldname?.status==='Rejected' && c.args.fieldname.rejection_reason==='Incorrect request'));
  await click('Request discount approval');await fill('L1 approver','Administrator');await fill('Percentage','0.1');await fill('Reason','Check minimum');await click('Send discount request');
  await wait("document.querySelector('.billing-invoice').textContent.includes('between 0.5% and 5%')");
  await fill('L4 approver','md');await fill('Final amount including GST','900');await fill('Reason','Final amount request');await click('Send discount request');
  await wait("document.querySelector('.billing-invoice').textContent.includes('Discount request sent.')");
  const l4=calls.find(c=>c.url.includes('create_discount_approval_request.run')).args;assert.equal(l4.requested_final_amount,900);assert.equal(l4.approval_level,'L4');

  docstatus=1;outstanding=30000;
  await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/native/billing?invoice=INV-1'});
  await wait("document.querySelector('.billing-invoice') && document.querySelector('.billing-invoice').textContent.includes('Submitted')");
  await click('Collect payment');await fill('Mode','Carepay');await fill('Amount','30000');await fill('Reference / UTR','LOAN-REF');
  await click('Record collection');await wait("document.querySelector('.billing-invoice').textContent.includes('Loan Aadhaar')");
  for(const [label,value] of [['Aadhaar card','123412341234'],['PAN card','ABCDE1234F'],['Loan transaction ID','LOAN-ID']])await fill(label,value);
  await evaluate(`(()=>{for(const input of document.querySelectorAll('.billing-invoice input[type=file]:not([accept="video/*"])')){const t=new DataTransfer();t.items.add(new File(['proof'],'proof.png',{type:'image/png'}));input.files=t.files;input.dispatchEvent(new Event('change',{bubbles:true}));}})()`);
  await click('Record collection');await wait("document.querySelector('.billing-invoice').textContent.includes('Record and verify')");
  await evaluate(`(()=>{Object.defineProperty(navigator.mediaDevices,'getUserMedia',{value:async()=>new MediaStream(),configurable:true});window.SpeechRecognition=class{start(){setTimeout(()=>this.onresult?.({resultIndex:0,results:[Object.assign([{transcript:'test client loan life'}],{isFinal:true})]}),20);}stop(){}};window.MediaRecorder=class{constructor(){this.state='inactive';this.mimeType='video/webm';}start(){this.state='recording';}stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['video'],{type:'video/webm'})});setTimeout(()=>this.onstop?.(),0);}};})()`);
  await click('Record declaration');await wait("Array.from(document.querySelectorAll('.billing-native button')).some(b=>b.textContent==='Stop and verify'&&!b.disabled)");
  assert.ok(await evaluate("Array.from(document.querySelectorAll('.billing-native button')).find(b=>b.textContent==='Close invoice').disabled"));
  await new Promise(r=>setTimeout(r,100));await click('Stop and verify');await wait("document.querySelector('.billing-invoice').textContent.includes('Declaration verified and uploaded.')");
  await evaluate(`(()=>{const input=document.querySelector('.billing-loan-video input[type=file]');const t=new DataTransfer();t.items.add(new File(['video'],'declaration.mp4',{type:'video/mp4'}));input.files=t.files;input.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  await wait("document.querySelector('.billing-video-review')");
  assert.ok(await evaluate("Array.from(document.querySelectorAll('.billing-video-review button')).find(b=>b.textContent==='Verify and upload').disabled"));
  await evaluate("document.querySelector('.billing-video-review input[type=checkbox]').click()");
  await click('Verify and upload');await wait("!document.querySelector('.billing-video-review') && document.querySelector('.billing-loan-video').textContent.includes('Declaration verified and uploaded.')");
  await click('Record collection');await wait("document.querySelector('.billing-invoice').textContent.includes('Payment receipt')");
  const loan=calls.filter(c=>c.url.includes('collect_payment_v4.run')).at(-1).args;
  assert.equal(JSON.parse(loan.loan_docs)[0].transaction_id,'LOAN-ID');assert.equal(JSON.parse(loan.loan_docs)[0].consent_video,'/private/files/pd.pdf');
  assert.equal(JSON.parse(loan.payments)[0].amount,30000);
  assert.deepEqual(errors,[]);
  console.log('Native Billing workflows passed on desktop/mobile: client search, draft payload, approval, submission, overcollection guard, payment receipt, OTP registration/upload, tabs and no overflow.');
 }finally{await send('Page.close');ws.close();}
})().catch(e=>{console.error(e);process.exit(1);});
