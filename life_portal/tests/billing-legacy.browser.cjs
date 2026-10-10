// Local Vite :5175 and Chrome :9225. All business APIs are mocked.
const WebSocket = require('../node_modules/ws');
const assert = require('node:assert/strict');
(async () => {
 const target=await(await fetch('http://127.0.0.1:9225/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(resolve=>ws.on('open',resolve));
 const jobs=new Map(),errors=[];let sequence=0;
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++sequence,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id:sequence,method,params}));});
 ws.on('message',async raw=>{
  const message=JSON.parse(raw);
  if(message.id){jobs.get(message.id)?.(message);jobs.delete(message.id);}
  if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
  if(message.method!=='Fetch.requestPaused')return;
  const {requestId,request}=message.params;let result={ok:true};
  if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'Legacy Billing Tester',roles:['System Manager'],csrf_token:'test'};
  if(request.url.includes('lifescc_billing_bootstrap.run'))result={user:'Administrator',branches:['A'],allowed_branches:['A'],user_branch:'A',is_head_office:0,practitioners:[],therapies:[],templates:[],comp_items:[],offers:[],approvers:[],modes:[{name:'Cash',type:'Cash'}]};
  if(request.url.includes('frappe.client.get_list'))result=[];
  if(request.url.includes('frappe.client.get_count'))result=0;
  if(request.url.includes('collections_report'))result={rows:[]};
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')}).catch(error=>errors.push(error.message));
 });
 const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);return result.result.value;};
 const wait=async expression=>{for(let i=0;i<150;i++){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,75));}throw Error('Timed out: '+expression);};
 try {
  await send('Runtime.enable');await send('Page.enable');
  await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:5175/api/*'}]});
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`{const OriginalDate=Date;window.Date=class extends OriginalDate{constructor(...args){super(...(args.length?args:['2026-10-08T20:00:00Z']));}static now(){return new OriginalDate('2026-10-08T20:00:00Z').getTime();}};}`});
  for(const width of [1440,390]){
   await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
   await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/billing'});
   await wait("document.querySelector('#billing-v2-app .nav-pills') && window.frappe?.datetime?.now_datetime");
   await wait("document.querySelectorAll('#kpis .kpi').length===4");
   assert.equal(await evaluate('frappe.datetime.get_today()'),'2026-10-09');
   assert.equal(await evaluate('frappe.datetime.now_date()'),'2026-10-09');
   assert.equal(await evaluate('frappe.datetime.now_datetime()'),'2026-10-09 01:30:00');
   assert.equal(await evaluate("frappe.datetime.add_days('2026-10-31',1)"),'2026-11-01');
   assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
   assert.equal(await evaluate("(()=>{BILL={};BILL.lines=[{therapy:'Therapy A',qty:2,rate:1000}];BILL.pkg_price=1800;COUPON_AMOUNT=100;COUPON_PCT=5;recalc();return BILL._totals.total;})()"),1890);
   const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
   require('node:fs').writeFileSync('/tmp/billing-ui-legacy-'+width+'.png',Buffer.from(shot.data,'base64'));
  }
  assert.deepEqual(errors,[]);
  console.log('Legacy Billing checks passed: desktop/mobile layout, no overflow or runtime errors, India midnight, date arithmetic and fixed-package preview totals.');
 } finally {await send('Page.close');ws.close();}
})().catch(error=>{console.error(error);process.exit(1);});
