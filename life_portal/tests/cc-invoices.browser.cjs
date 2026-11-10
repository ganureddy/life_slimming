// Run against an isolated local Vite preview and Chrome. All ERP APIs are mocked.
const WebSocket=require('../node_modules/ws');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const chrome=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9243';
 const base=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5183';
 const target=await(await fetch(chrome+'/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(resolve=>ws.on('open',resolve));
 let serial=0,empty=false,fail=false,pageLoaded;const jobs=new Map(),calls=[],errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++serial,message=>message.error?reject(message.error):resolve(message.result));ws.send(JSON.stringify({id:serial,method,params}));});
 const row={name:'SINV-TEST-001',customer_name:'Ananya Rao',patient:'PAT-001',posting_date:'2026-11-10',branch:'Vizag',status:'Partly Paid',grand_total:16800,outstanding_amount:4800,currency:'INR',mobile:'9876543210',source:'Call Center',source_from:'Invoice',lead_source:'WEBSITE CHAT'};
 ws.on('message',async raw=>{
  const message=JSON.parse(raw);if(message.method==='Page.loadEventFired'){pageLoaded?.();pageLoaded=null;}if(message.id){jobs.get(message.id)?.(message);jobs.delete(message.id);}
  if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails.text);
  if(message.method!=='Fetch.requestPaused')return;
  const {requestId,request}=message.params;let args={};try{args=JSON.parse(request.postData||'{}');}catch{}
  calls.push({url:request.url,args});let result={available:false,enabled:false,rows:[]};
  if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'Test Admin',roles:['System Manager'],csrf_token:'test',portal_role:'IT'};
  if(request.url.includes('cc_invoices.filters'))result={branches:['Vizag','Banjara Hills'],sources:['Call Center','Reference','DIRECT WALKIN'],statuses:['Paid','Partly Paid','Overdue','Cancelled']};
  if(request.url.includes('cc_invoices.list_invoices'))result=fail?{error:'Invoice lookup temporarily unavailable'}:{rows:empty?[]:[{...row,name:Number(args.start)?'SINV-TEST-041':row.name}],total:empty?0:75,start:Number(args.start)||0,more:!empty&&!Number(args.start),outstanding_count:empty?0:12,amounts:empty?[]:[{currency:'INR',billed:500000,outstanding:50000}]};
  if(request.url.includes('cc_invoices.invoice'))result={...row,name:args.name,due_date:'2026-11-20',net_total:16000,total_taxes_and_charges:800,discount_amount:0,items:[{name:'ITEM-1',item_name:'Consultation',item_code:'CONSULT',qty:1,uom:'Nos',rate:16000,amount:16000}]};
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')});
 });
 const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.text);return result.result.value;};
 const wait=async expression=>{for(let n=0;n<120;n++){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,100));}throw Error('Timed out: '+expression);};
 const fill=async(selector,value)=>evaluate(`(()=>{const input=document.querySelector(${JSON.stringify(selector)});input.value=${JSON.stringify(value)};input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 try{
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'*/api/method/*'}]});
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:base+'/life_portal/cc-invoices'});
  await wait("document.querySelector('.invoice-link') && document.querySelectorAll('.filter-grid select option').length>5");
  assert.equal(await evaluate("document.querySelector('.mobile-cell').textContent"),'9876543210');
  assert.equal(await evaluate("document.querySelector('.source-badge').textContent"),'Call Center');
  assert.equal(await evaluate("document.querySelectorAll('.bill-stats article').length"),0);
  await fill('input[type=tel]','+91 98765 43210');await fill('.filter-grid select:nth-of-type(1)','');
  await fill('.filter-grid label:nth-child(1) input','2026-11-01');await fill('.filter-grid label:nth-child(2) input','2026-11-10');
  await fill('.filter-grid label:nth-child(3) select','Vizag');await fill('.filter-grid label:nth-child(4) select','Partly Paid');await fill('.filter-grid label:nth-child(5) select','Call Center');
  await click('.apply-button');await wait("document.querySelector('.filter-chips') && document.querySelectorAll('.filter-chips>span').length===6");
  let last=calls.filter(call=>call.url.includes('list_invoices')).at(-1).args;
  assert.equal(last.mobile,'+91 98765 43210');assert.equal(last.source,'Call Center');assert.equal(last.branch,'Vizag');assert.equal(last.status,'Partly Paid');assert.equal(last.from_date,'2026-11-01');
  await click('.bill-results footer>div button:last-child');await wait("document.querySelector('.invoice-link')?.textContent==='SINV-TEST-041'");
  last=calls.filter(call=>call.url.includes('list_invoices')).at(-1).args;assert.equal(last.start,40);assert.equal(last.mobile,'+91 98765 43210');
  await click('.view-bill');await wait("document.querySelector('.invoice-dialog[open] .detail-items')");
  const dialogText=await evaluate("document.querySelector('.invoice-dialog').textContent");
  assert.ok(dialogText.includes('Call Center'));assert.ok(dialogText.includes('WEBSITE CHAT'));assert.ok(dialogText.includes('9876543210'));assert.ok(dialogText.includes('Consultation'));
  assert.equal(await evaluate("document.querySelectorAll('.invoice-dialog button').length"),2);
  await click('.close-detail');await wait("!document.querySelector('.invoice-dialog').open");
  empty=true;await click('.reset-button');await wait("document.querySelector('.bill-empty h3')?.textContent==='No bills found'");
  assert.equal(await evaluate("document.querySelector('.bill-results footer>div button:last-child').disabled"),true);
  empty=false;fail=true;await click('.refresh-button');await wait("document.querySelector('.bill-error[role=alert]')");
  assert.equal(await evaluate("document.querySelectorAll('.invoice-link').length"),0);
  fail=false;await click('.bill-error button');await wait("document.querySelector('.invoice-link')");
  assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
  await new Promise(resolve=>setTimeout(resolve,150));
  fs.writeFileSync('/tmp/cc-invoices-desktop.png',Buffer.from((await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  const loaded=new Promise(resolve=>{pageLoaded=resolve;});
  await send('Page.reload',{ignoreCache:true});await loaded;
  await wait("document.querySelector('.invoice-link')");
  await send('Emulation.setPageScaleFactor',{pageScaleFactor:1});
  await new Promise(resolve=>setTimeout(resolve,150));
  assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
  assert.equal(await evaluate("Math.round(visualViewport.width)"),390);
  fs.writeFileSync('/tmp/cc-invoices-mobile.png',Buffer.from((await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  assert.deepEqual(errors,[]);
  console.log('PASS: invoice/mobile/source display, combined filters, pagination, read-only detail, empty/error/retry states, desktop and mobile layouts.');
 }catch(error){console.error('Browser state:',await evaluate("document.body.innerText.slice(0,2500)"),errors,calls.map(call=>call.url));throw error;}finally{await send('Page.close');ws.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
