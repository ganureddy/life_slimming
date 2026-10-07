// Requires local Vite :5175 and isolated Chrome :9225; APIs are mocked.
const WebSocket = require('../node_modules/ws');
const assert = require('node:assert/strict');
(async()=>{
  const target=await(await fetch('http://127.0.0.1:9225/json/new?about:blank',{method:'PUT'})).json();
  const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(resolve=>ws.on('open',resolve));
  let id=0;const jobs=new Map(),errors=[],calls=[];
  const send=(method,params={})=>new Promise((resolve,reject)=>{jobs.set(++id,message=>message.error?reject(message.error):resolve(message.result));ws.send(JSON.stringify({id,method,params}));});
  ws.on('message',async raw=>{
    const message=JSON.parse(raw);if(message.id){jobs.get(message.id)?.(message);jobs.delete(message.id);}
    if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails.text);
    if(message.method!=='Fetch.requestPaused')return;
    const {requestId,request}=message.params;let args={};try{args=JSON.parse(request.postData||'{}');}catch{}
    calls.push({url:request.url,args});let result={};
    if(request.url.includes('portal.bootstrap'))result={user:'Administrator',full_name:'Tester',roles:['System Manager'],csrf_token:'test'};
    if(request.url.includes('frappe.client.get_list'))result=[{name:'A'},{name:'B'}];
    if(request.url.includes('branch_command_center.run'))result={daily:{basis:'net',cycle_from:'2026-09-06',cycle_to:'2026-10-05',is_closed:0,target:100000,achieved:50000,gross:52500,gst:2500,cut:0,gap:50000,pct:50,total_days:30,days_left:1,req_per_day:50000,run_rate:2000,projected:60000,on_track:0,hit_days:1,miss_days:1,days:[{d:'2026-10-04',gross:2100,gst:100,cut:0,got:2000,req:1800,diff:200,cum:2000,hit:1,future:0},{d:'2026-10-05',gross:1000,gst:48,cut:0,got:952,req:2000,diff:-1048,cum:2952,hit:0,future:0},{d:'2026-10-06',got:0,req:2000,future:1}]}};
    await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')});
  });
  const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.text);return result.result.value;};
  const wait=async expression=>{for(let attempt=0;attempt<100;attempt++){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,75));}throw Error('Timed out: '+expression+'\n'+await evaluate('document.body.innerText'));};
  try{
    await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:5175/api/*'}]});
    for(const width of [1440,390]){
      await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
      await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/'+(width===1440?'conv':'native/branch-target')});
      await wait("document.querySelector('.target-kpis')?.textContent.includes('Cycle realisation')");
      assert.equal(await evaluate("document.querySelectorAll('.target-table-wrap tbody tr').length"),2);
      assert.equal(await evaluate("document.querySelectorAll('.target-bar').length"),2);
      assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
      await evaluate("Array.from(document.querySelectorAll('.target-filters button')).find(b=>b.textContent==='Last Cycle').click()");
      await wait("document.querySelector('.target-filters button.selected')?.textContent==='Last Cycle'");
      assert.equal(calls.filter(call=>call.url.includes('branch_command_center.run')).at(-1).args.from_date,'2026-08-06');
      await evaluate("(()=>{const s=document.querySelector('.target-filters select');s.value='B';s.dispatchEvent(new Event('change',{bubbles:true}));})()");
      await wait("document.querySelector('.target-kpis')?.textContent.includes('Cycle realisation')");
      assert.equal(calls.filter(call=>call.url.includes('branch_command_center.run')).at(-1).args.branch,'B');
    }
    assert.deepEqual(errors,[]);
    console.log('Branch target browser checks passed on desktop and mobile.');
  }finally{await send('Page.close');ws.close();}
})().catch(error=>{console.error(error);process.exit(1);});
