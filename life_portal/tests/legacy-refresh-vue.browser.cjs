// Local browser only: every ERP request is fulfilled with fixtures.
const assert=require('node:assert/strict');
const WebSocket=require('../node_modules/ws');
(async()=>{
 const endpoint=process.env.PORTAL_BROWSER_URL||'http://127.0.0.1:9225',base=process.env.PORTAL_PREVIEW_URL||'http://127.0.0.1:5178';
 const target=await(await fetch(endpoint+'/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.on('open',r));
 let sequence=0;const jobs=new Map(),errors=[],calls=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++sequence,m=>m.error?reject(Error(JSON.stringify(m.error))):resolve(m.result));ws.send(JSON.stringify({id:sequence,method,params}));});
 const evalJs=async expression=>(await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result.value;
 const reply=(id,body)=>send('Fetch.fulfillRequest',{requestId:id,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify(body)).toString('base64')});
 ws.on('message',async raw=>{const message=JSON.parse(raw);if(message.id){jobs.get(message.id)?.(message);jobs.delete(message.id);return;}
 if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails.exception?.description||message.params.exceptionDetails.text);
 if(message.method!=='Fetch.requestPaused')return;
 const {requestId,request}=message.params;
 try{
 const url=new URL(request.url),method=decodeURIComponent(url.pathname.split('/api/method/')[1]||''),args=request.postData?(request.postData.trim().startsWith('{')?JSON.parse(request.postData):Object.fromEntries(new URLSearchParams(request.postData))):Object.fromEntries(url.searchParams);calls.push({method,args,url:request.url});
 if(method==='life_slimming.api.portal.bootstrap')return reply(requestId,{message:{user:'Administrator',full_name:'Vue Refresh Tester',roles:['System Manager'],portal_role:'IT',csrf_token:'fixture',session_id:target.id}});
 if(method.endsWith('convox.config'))return reply(requestId,{message:{enabled:false}});
 if(method==='frappe.client.get_list'){
  const rows=args.doctype==='Branch'?[{name:'Gachibowli',branch:'Gachibowli'}]:args.doctype==='User'?[{name:'Administrator',full_name:'Vue Refresh Tester',enabled:1}]:[];
  return reply(requestId,{message:rows});
 }
 if(method==='frappe.client.get')return reply(requestId,{message:{name:args.name,full_name:'Vue Refresh Tester',doctype:args.doctype}});
 if(method==='frappe.desk.query_report.run')return reply(requestId,{message:{result:[]}});
 if(method==='frappe.desk.form.load.getdoctype')return reply(requestId,{docs:[{doctype:'DocType',name:args.doctype,fields:[]}]});
 if(method==='frappe.auth.get_logged_user')return reply(requestId,{message:'Administrator'});
 if(method==='life_branch_shared_layout')return reply(requestId,{message:{layout:{revision:'fixture',orders:{}},can_save:false,can_view_sales_amounts:false}});
 if(method==='life_stock_fast_requests')return reply(requestId,{message:{rows:[],total:0,has_more:false}});
 if(url.pathname.startsWith('/api/resource/'))return reply(requestId,{data:{name:url.pathname.split('/').at(-1)}});
 return reply(requestId,{message:[]});
 }catch(error){errors.push(error.message);await reply(requestId,{message:[]});}
 });
 async function wait(expression){for(let i=0;i<100;i++){if(await evalJs(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error('Timeout: '+expression+'\n'+await evalJs('document.body.innerText.slice(-1500)')+'\n'+JSON.stringify({calls:calls.slice(0,12),errors}));}
 try{
 await send('Runtime.enable');await send('Page.enable');await send('Fetch.enable',{patterns:[{urlPattern:'*/api/method/*'},{urlPattern:'*/api/resource/*'}]});
 for(const width of [1440,390]){
 await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
 for(const [route,ready]of [['tasks',"document.querySelector('#life-tm #view') && !document.querySelector('#life-tm #view').textContent.includes('Loading tasks')"],['empsale',"document.querySelector('#esr-root') && document.querySelector('#esr-root').textContent.includes('Treatment')"],['clusterhome',"document.querySelector('#cl-status') && !document.querySelector('#cl-refresh').disabled"]]){
  await send('Page.navigate',{url:base+'/life_portal/'+route});await wait(ready);
  assert.equal(await evalJs("document.querySelectorAll('iframe.portal-source-frame').length"),0);
  const overflow=await evalJs('document.documentElement.scrollWidth > innerWidth + 2');
  console.log(JSON.stringify({route,width,ready:true,overflow}));
 }
 }
 await evalJs(`document.querySelector('a[href="/life_portal/native/tasks"]').click()`);
 await wait("document.querySelector('#life-tm #view') && !document.querySelector('#life-tm #view').textContent.includes('Loading tasks')");
 assert.equal(await evalJs("!!document.querySelector('#clusterApp')"),false);
 assert.deepEqual(errors,[]);assert(calls.some(call=>call.method==='frappe.desk.query_report.run'));
 console.log('Updated Tasks, Employee Sale and Cluster Vue fixtures passed.');
 }finally{await send('Page.close');ws.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
