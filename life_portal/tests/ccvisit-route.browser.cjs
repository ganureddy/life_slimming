// Business calls are mocked; no live records are changed.
const WebSocket=require('../node_modules/ws'),assert=require('node:assert/strict'),fs=require('node:fs');
const contrastAudit=require('./cc-report-contrast.helper.cjs');
(async()=>{
 const base=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5178',endpoint=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9230',target=await(await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));let id=0,emptyData=false,failData=false;const jobs=new Map(),calls=[],readEvents=[],errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++id,m=>m.error?reject(m.error):resolve(m.result));ws.send(JSON.stringify({id,method,params}));});
 ws.on('message',async raw=>{const m=JSON.parse(raw);if(m.id){jobs.get(m.id)?.(m);jobs.delete(m.id);return;}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description);if(m.method!=='Fetch.requestPaused')return;
 const {requestId,request}=m.params;calls.push(request.url);readEvents.push({url:request.url,args:JSON.parse(request.postData||'{}')});let result={};
 if(request.url.includes('login_context'))result={authenticated:true};
 if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'Route Tester',roles:['System Manager'],csrf_token:'test'};
 if(request.url.includes('cc_report_walkin.run'))result={lead:'LEAD-1',patient:'PAT-1',pd_number:'PD-1',images:[],history:[],status:'Visited Booked'};
 if(request.url.includes('cc_report_bills.run'))result={leads:{'LEAD-1':{paid:500,has_bill:true,invoices:[{invoice:'INV-1',invoice_date:'2026-11-12',paid:500,billed:1000,balance:500}]}}};
 if(request.url.includes('cc_untouched.run'))result={rows:[],total:0};
 if(request.url.includes('life_cc_nofu_v1.run'))result={rows:[],total:0,agents:[],statuses:[],buckets:[]};
 if(request.url.includes('cc_core.run'))result={funnel:{leads:0},agents:[],joined:[],moves:[],last_call_mix:{}};
 if(request.url.includes('cc_report_history.history'))result={rows:[],has_more:false};
 if(request.url.includes('cc_report_activity.run'))result={rows:[{agent:'cc@example.com',name:'Test Agent',convox:3,mobile:1,answered:3,talk:120,appointments:1,walkins:1,booked:1,updates:2,idle_minutes:15,updated_no_call:0,talked_no_update:0,appointment_without_booking:0,events:[],dispositions:{Connected:3}}],warnings:[],timeline_available:true};
 if(request.url.includes('life_cc_agent_marketing_data')){const args=JSON.parse(request.postData||'{}'),day=args.from_date||'2026-11-12';const row={name:'LEAD-1',lead_name:'Test Client',lead_owner:'cc@example.com',branch:'Test Branch',source:'Website',ad_set:'Ad Set 1',enquired_for:'Skin',creation:day+' 09:00:00',custom_appointment_status:'Visited Booked',custom_appointment_date_and_time:day+' 10:00:00',lifeVisit:2,consultant_name:'Test Consultant',consultant_id:'EMP-1',consultant_eligible:true,manager_name:'Test Manager'};result={rows:[row],consultant_appointments:[row],days:[],total:1,cc_invoice_report_summary:{rows:[],payment_rows:[],totals:{}}};}
 if(emptyData&&request.url.includes('life_cc_agent_marketing_data'))result={rows:[],ranking_rows:[],consultant_appointments:[],days:[],total:0,cc_invoice_report_summary:{rows:[],payment_rows:[],totals:{}}};
 await send('Fetch.fulfillRequest',{requestId,responseCode:failData&&request.url.includes('life_cc_agent_marketing_data')?500:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')}).catch(error=>{if(!/Invalid InterceptionId|No resource|Target closed/i.test(error.message||''))errors.push(error);});});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description);return r.result.value;};
 const wait=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error('Timeout '+expression+' '+await evaluate('document.body.innerText'));};
 try{await send('Network.clearBrowserCookies');await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:base+'/api/*'}]});await send('Page.navigate',{url:base+'/life_portal/ccvisit'});
 await wait("document.querySelector('.cc-branch-visits-page') && !document.querySelector('.cc-visit-v26').textContent.includes('Loading appointment schedule…') && document.querySelector('.branch-summary-cards')");
 assert.equal(await evaluate("document.querySelectorAll('iframe').length"),0);
 assert.equal(calls.filter(u=>u.includes('life_cc_agent_marketing_data')).length,3,'appointment, calendar and one shared financial read on entry');
 assert.equal(calls.filter(u=>u.includes('cc_report_walkin.run')).length,0,'PD forms must be lazy');
 const pdButton="Array.from(document.querySelectorAll('.cc-branch-visits-page button')).find(e=>e.textContent==='PD Forms / visit history')";
 await evaluate(pdButton+".click()");await wait("document.querySelector('.cc-visit-details')?.textContent.includes('PD-1')");
 assert.equal(calls.filter(u=>u.includes('cc_report_walkin.run')).length,1);
 await evaluate("document.querySelector('.cc-visit-details header button').click()");
 await wait("!document.querySelector('.cc-visit-details')");
 await evaluate(pdButton+".click()");await wait("document.querySelector('.cc-visit-details')?.textContent.includes('PD-1')");
 assert.equal(calls.filter(u=>u.includes('cc_report_walkin.run')).length,1,'reopening same PD dialog reuses data');
 await evaluate("document.querySelector('.cc-visit-details header button').click()");
 for(const label of ['LEAD & DIGITAL MARKETING','CONSULTANT / MANAGER REPORT','CC — BRANCH VISITS']){await evaluate(`Array.from(document.querySelectorAll('.cc-report-tabs a')).find(e=>e.textContent.includes(${JSON.stringify(label)})).click()`);await new Promise(r=>setTimeout(r,350));}
 assert.equal(await evaluate("location.pathname"),'/life_portal/ccvisit');
 assert.equal(calls.filter(u=>u.includes('life_cc_agent_marketing_data')).length,3,'financial response reused between report tabs');
 assert.equal(calls.some(u=>u.includes('frappe.client.get_list')),false);
 for(const [label,path,selector] of [['CC — BRANCH VISITS','/ccvisit','.cc-branch-visits-page'],['AGENT REPORT','/ccvisit/agents','.arx-root'],['LEAD & DIGITAL MARKETING','/ccvisit/marketing','.life-mkt-root'],['CONSULTANT / MANAGER REPORT','/ccvisit/consultants','.cc-consultant-report'],['CLUSTER REPORT','/ccvisit/cluster','.cc-cluster-report'],['AGENT 360','/ccvisit/activity','.cc-card'],['LEAD JOURNEY','/ccvisit/journey','.card']]){
  await evaluate(`Array.from(document.querySelectorAll('.cc-report-tabs a')).find(e=>e.textContent.includes(${JSON.stringify(label)})).click()`);await wait(`document.querySelector(${JSON.stringify(selector)})!==null`);if(label==='AGENT REPORT'){await evaluate("Array.from(document.querySelectorAll('.arx-filters button')).find(e=>e.textContent==='Single Agent').click()");await evaluate("(()=>{const select=document.querySelector('.arx-filters select');select.value='cc@example.com';select.dispatchEvent(new Event('change',{bubbles:true}));})()");await wait("document.querySelector('.cc-agent-scorecard')");}assert.equal(await evaluate('location.pathname'),'/life_portal'+path);
  for(const width of [1440,390]){await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});await new Promise(r=>setTimeout(r,350));assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'page must fit viewport');const contrast=await evaluate(contrastAudit);if(contrast.length)console.error(JSON.stringify({label,width,contrast},null,2));assert.deepEqual(contrast,[],label+' contrast at '+width+'px');const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync('/tmp/report-'+path.split('/').pop()+'-'+width+'.png',Buffer.from(shot.data,'base64'));await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'start'})`);await new Promise(r=>setTimeout(r,200));const contentShot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync('/tmp/report-'+path.split('/').pop()+'-content-'+width+'.png',Buffer.from(contentShot.data,'base64'));}
  if(label==='AGENT REPORT'){
   const periodStart=readEvents.length;
   await evaluate("Array.from(document.querySelectorAll('.cc-agent-periods button')).find(e=>e.textContent==='Load comparison').click()");
   await wait("document.querySelector('.cc-agent-periods .cc-table')&&!document.querySelector('.cc-agent-periods').textContent.includes('Loading')");
   const periodReads=readEvents.slice(periodStart).filter(r=>r.url.includes('life_cc_agent_marketing_data'));
   assert.equal(periodReads.length,3,'three-month comparison reads each period once, only on demand');
   assert.equal(new Set(periodReads.map(r=>JSON.stringify(r.args))).size,3);
   assert.deepEqual(await evaluate(contrastAudit),[],'three-month comparison contrast');
   await evaluate("Array.from(document.querySelectorAll('.arx-filters button')).find(e=>e.textContent==='All Agents').click()");
  }
  if(label==='AGENT 360'){await evaluate("document.querySelector('.cc-history-count').click()");await wait("document.querySelector('.cc-history-dialog')&&!document.querySelector('.cc-history-dialog').textContent.includes('Loading')");assert.deepEqual(await evaluate(contrastAudit),[],'history dialog contrast');await evaluate("document.querySelector('.cc-history-dialog header button').click()");}
 }
 const before=calls.filter(u=>u.includes('life_cc_agent_marketing_data')).length;
 const clickSidebar=async label=>evaluate(`Array.from(document.querySelectorAll('.portal > .sidebar .nav-item')).find(e=>e.getAttribute('aria-label')===${JSON.stringify(label)}).click()`);
 await clickSidebar('Agent 360');
 await wait("document.querySelector('.cc-agent360-standalone') && !document.querySelector('.cc-agent360-standalone').textContent.includes('Loading')");
 assert.equal(await evaluate('location.pathname'),'/life_portal/agent-360');
 assert.equal(await evaluate("document.querySelectorAll('.cc-agent360-standalone .cc-report-tabs > *').length"),1);
 assert.equal(await evaluate("document.querySelector('.portal > .sidebar a[aria-label=\"Agent 360\"]').getAttribute('aria-current')"),'page');
 assert.equal(await evaluate("document.querySelector('.portal > .sidebar a[aria-label=\"Branch Visit Report\"]').getAttribute('aria-current')"),null);
 assert.equal(calls.filter(u=>u.includes('life_cc_agent_marketing_data')).length,before,'standalone activity must not load appointment/calendar/financial reports');
 assert.equal(calls.filter(u=>u.includes('cc_report_activity.run')).length,1);
 await evaluate("document.querySelector('.cc-agent360-standalone form button[type=submit]').click()");
 await wait("!document.querySelector('.cc-agent360-standalone').textContent.includes('Loading')");
 assert.equal(calls.filter(u=>u.includes('cc_report_activity.run')).length,2,'Apply refreshes exactly once');
 await clickSidebar('Branch Visit Report');await wait("document.querySelector('.cc-branch-visits-page')");
 assert.equal(await evaluate("document.querySelectorAll('.cc-report-tabs a').length"),7);
 assert.equal(calls.filter(u=>u.includes('life_cc_agent_marketing_data')).length,before,'reopening Branch Visit Report reuses cached appointments and financials');
 await clickSidebar('Agent 360');await wait("document.querySelector('.cc-agent360-standalone') && !document.querySelector('.cc-agent360-standalone').textContent.includes('Loading')");
 assert.equal(calls.filter(u=>u.includes('cc_report_activity.run')).length,2,'returning to standalone reuses saved activity');
 // Prime KeepAlive children, then refresh another tab. Hidden reports must stay idle.
 await clickSidebar('Branch Visit Report');await wait("document.querySelector('.cc-branch-visits-page')");
 const reportClick=async text=>evaluate(`Array.from(document.querySelectorAll('.cc-report-tabs a')).find(e=>e.textContent.includes(${JSON.stringify(text)})).click()`);
 await reportClick('LEAD JOURNEY');await wait("document.querySelector('.card-hdr')?.textContent.includes('Lead Journey')");
 await reportClick('AGENT 360');await wait("document.querySelector('.cc-card')?.textContent.includes('Agent 360')");
 await reportClick('AGENT REPORT');await wait("document.querySelector('.arx-root')");
 await evaluate("Array.from(document.querySelectorAll('nav[aria-label=\"Agent reports\"] button')).find(e=>e.textContent==='Untouched').click()");
 await wait("document.querySelector('.cc-card')?.textContent.includes('Untouched leads')");
 await reportClick('LEAD & DIGITAL MARKETING');await wait("document.querySelector('.life-mkt-root')");
 await new Promise(r=>setTimeout(r,150));const hiddenStart=readEvents.length;
 await evaluate("(()=>{const inputs=document.querySelectorAll('form.cc-filters input[type=date]');for(const input of inputs){input.value='2026-11-01';input.dispatchEvent(new Event('input',{bubbles:true}));}document.querySelector('form.cc-filters').requestSubmit();})()");
 await wait("location.search.includes('from=2026-11-01')&&!document.body.textContent.includes('Loading appointment schedule')&&!document.body.textContent.includes('Loading report data')");
 await new Promise(r=>setTimeout(r,250));
 const refreshReads=readEvents.slice(hiddenStart);
 assert.equal(refreshReads.filter(r=>/cc_report_activity|cc_untouched|cc_core\.run|life_cc_nofu/.test(r.url)).length,0,'hidden cached reports must not read on another tab refresh');
 const mainReads=refreshReads.filter(r=>r.url.includes('life_cc_agent_marketing_data'));
 assert.equal(mainReads.length,3,'one appointment, one calendar and one financial read per refresh');
 assert.equal(new Set(mainReads.map(r=>JSON.stringify(Object.entries(r.args).sort()))).size,3,'each report payload must be distinct');
 // Contrast must hold when data is absent and a request fails, too.
 emptyData=true;await reportClick('AGENT REPORT');await wait("document.querySelector('.arx-root')");
 await evaluate("document.querySelector('form.cc-filters').requestSubmit()");
 await wait("!document.body.textContent.includes('Loading appointment schedule')&&!document.body.textContent.includes('Loading Agent data')");
 assert.deepEqual(await evaluate(contrastAudit),[],'empty report contrast');
 failData=true;await evaluate("document.querySelector('form.cc-filters').requestSubmit()");
 await wait("document.querySelector('.cc-error[role=alert]')");
 assert.deepEqual(await evaluate(contrastAudit),[],'error state contrast');
 assert.deepEqual(errors,[]);console.log('Report audit passed: separate routes/sidebar, shared caches, distinct refresh reads and no hidden-tab requests.');
 }finally{await send('Page.close').catch(()=>{});ws.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
