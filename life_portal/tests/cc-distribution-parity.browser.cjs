// All business requests are intercepted; this test never moves live leads.
const WebSocket=require('../node_modules/ws');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const endpoint=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9230',baseUrl=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5178';
 const target=await(await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(resolve=>ws.on('open',resolve));
 let sequence=0;const pending=new Map(),calls=[],errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{pending.set(++sequence,message=>message.error?reject(message.error):resolve(message.result));ws.send(JSON.stringify({id:sequence,method,params}));});
 const rule={name:'RULE-1',rule_name:'New leads',rule_type:'Time-over New Lead',enabled:1,test_mode:1,time_value:15,time_unit:'Minutes',method:'Best Conversion'};
 ws.on('message',async raw=>{
  const message=JSON.parse(raw);if(message.id){pending.get(message.id)?.(message);pending.delete(message.id);return;}
  if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails.exception?.description);
  if(message.method!=='Fetch.requestPaused')return;
  const {requestId,request}=message.params,args=JSON.parse(request.postData||'{}');calls.push({url:request.url,args});let result={};
  if(request.url.includes('login_context'))result={authenticated:true};
  if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'Distribution Tester',roles:['System Manager'],csrf_token:'test'};
  if(request.url.includes('life_cc_core')||request.url.includes('cc_core.run')){
   result={ok:true};
   switch(args.action){
    case 'perm':Object.assign(result,{can_move:true,can_edit_perm:true,movers:['Administrator']});break;
    case 'agents':Object.assign(result,{agents:[{agent:'agent@example.com',name:'Active CC Agent',checked_in:true,open:10,overdue:2}],settings:{cap_on:1,cap_overdue:150,cap_open:1000,open_days:60,overdue_days:30,dormant_days:90,seniors:[]}});break;
    case 'rules':result.rules=[rule];break;
    case 'bulk_meta':Object.assign(result,{sources:['Website','Meta Chat'],branches:['Test Branch']});break;
    case 'dist_preview':Object.assign(result,{count:1,items:[{lead:'LEAD-1',owner:'agent@example.com',milestone:'Interested',last_call_result:'No Response',next_action:'Call back'}]});break;
    case 'rank':result.rows=[{agent:'agent@example.com',name:'Active CC Agent',rank:1,booked:5,walkins:8,conv:63,open:10}];break;
    case 'dist_move':Object.assign(result,{count:1,batch:'TEST-BATCH'});break;
    case 'dist_undo':result.undone=1;break;
    case 'rule_save':result.saved=1;break;
    case 'settings_save':result.settings=JSON.parse(args.settings);break;
   }
  }
  await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')});
 });
 const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description);return result.result.value;};
 const wait=async expression=>{for(let i=0;i<120;i++){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,75));}throw Error('Timeout: '+expression+'\n'+await evaluate('document.body.innerText'));};
 const click=async(selector,text)=>{await wait(`(()=>{const el=[...document.querySelectorAll(${JSON.stringify(selector)})].find(item=>item.textContent.includes(${JSON.stringify(text)}));if(!el||el.disabled)return false;el.click();return true;})()`);};
 const count=action=>calls.filter(call=>call.args.action===action).length;
 try{
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:baseUrl+'/api/*'}]});
  for(const width of [1440,390]){
   const start=calls.length;
   await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
   await send('Page.navigate',{url:baseUrl+'/life_portal/leads/distribution'});
   await wait("document.querySelectorAll('.cc-distribution .lcx-grid .lcx-pk').length===8");
   assert.equal(await evaluate("new URLSearchParams(location.search).has('view')"),false);
   assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'filter layout overflow '+width);
   assert.equal(calls.slice(start).filter(call=>call.args.action==='perm').length,1,'sidebar and distribution share permission lookup');
   await click('.cc-distribution .lcx-ch','No Response');
   await evaluate("const limit=document.querySelector('[aria-label=\"Maximum leads\"]');limit.value='27';limit.dispatchEvent(new Event('input',{bubbles:true}));const include=[...document.querySelectorAll('.lcx-opt')].find(item=>item.textContent.includes('Include protected')).querySelector('input');include.click()");
   await evaluate('window.scrollTo(0,0)');
   fs.writeFileSync('/tmp/cc-distribution-legacy-'+width+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
   await click('.cc-distribution button','Find leads → Step 2');
   await wait("document.querySelector('.cc-distribution .tbl-wrap')?.textContent.includes('LEAD-1')");
   const preview=calls.filter(call=>call.args.action==='dist_preview').at(-1).args;
   assert.deepEqual(JSON.parse(preview.last_results),['No Response']);assert.equal(preview.limit,27);assert.equal(preview.include_protected,1);
   await evaluate("document.querySelector('[aria-label=\"Select all preview leads\"]').click()");
   assert.equal(await evaluate("[...document.querySelectorAll('.cc-distribution button')].find(button=>button.textContent.includes('Choose receiving agents')).disabled"),true);
   await evaluate("document.querySelector('[aria-label=\"Select all preview leads\"]').click()");
   await click('.cc-distribution button','Choose receiving agents');
   await click('.cc-distribution .lcx-ch','Active CC Agent');
   await wait("document.querySelector('.cc-distribution .lcx-rank')?.textContent.includes('Active CC Agent')");
   assert.equal(calls.filter(call=>call.args.action==='rank').at(-1).args.method,'conversion','legacy default priority is best conversion');
   assert.equal(await evaluate("document.querySelectorAll('.cc-distribution .lcx-card').length"),7);
   const moves=count('dist_move');
   await click('.cc-distribution button','Move 1 selected leads');
   await wait("!!document.querySelector('.crm-distribution-confirm[open]')");
   assert.equal(count('dist_move'),moves,'reviewing a move does not mutate');
   await click('.crm-distribution-confirm button','Cancel');
   await click('.cc-distribution button','Move 1 selected leads');
   await click('.crm-distribution-confirm button','Yes, move leads');
   await wait("document.querySelector('.cc-distribution [role=status]')?.textContent.includes('1 leads moved.')");
   assert.equal(count('dist_move'),moves+1);
   await click('.cc-distribution button','Undo last move');
   await click('.crm-distribution-confirm button','Yes, undo');
   await wait("document.querySelector('.cc-distribution [role=status]')?.textContent.includes('1 leads moved back.')");
   await click('.distribution-tabs button','Auto Rules');
   assert.equal(await evaluate("document.querySelectorAll('.distribution-preset').length"),7,'all legacy rule templates are present');
   await click('.distribution-preset button','New lead in 15 min');
   assert.equal(await evaluate("document.querySelector('.distribution-rule-form input[required]').value"),'New lead not called');
   const saves=count('rule_save');
   await click('.distribution-rule-form button','Review rule');
   assert.equal(count('rule_save'),saves,'template review does not save');
   await click('.rule-applied button','Accept & Apply');
   await wait("document.querySelector('.cc-distribution [role=status]')?.textContent.includes('Rule saved')");
   for(const label of ['Agents & Priority','Bulk Upload','Permissions']){
    await click('.distribution-tabs button',label);
    assert.equal(await evaluate("document.querySelector('.cc-distribution').getBoundingClientRect().height>0"),true);
   }
   const agentLoads=count('agents');
   await click('.portal > .sidebar .nav-item','Call Scripts');await wait("location.pathname.endsWith('/leads/scripts') && !!document.querySelector('#scripts-area')");
   await click('.portal > .sidebar .nav-item','Lead Distribution');await wait("location.pathname.endsWith('/leads/distribution') && !!document.querySelector('.cc-distribution')");
   assert.equal(count('agents'),agentLoads,'returning to distribution preserves its data');
   await evaluate('history.back()');await wait("location.pathname.endsWith('/leads/scripts') && !!document.querySelector('#scripts-area')");
   assert.equal(await evaluate("document.querySelector('.page-render-error')===null"),true);
  }
  assert.deepEqual(errors,[]);console.log('Distribution parity passed: legacy filters/templates, rank, move review/undo, separate routes, shared data, desktop/mobile.');
 }finally{await send('Page.close');ws.close();}
})().catch(error=>{console.error(error);process.exit(1)});
