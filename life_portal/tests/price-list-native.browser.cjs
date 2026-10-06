// Requires local Vite :5175 and isolated Chrome :9225. All APIs are mocked.
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
    if(request.url.includes('frappe.client.get_list')){
      if(args.doctype==='Therapy Type')result=[{therapy_type:'Laser',healthcare_service_unit:'Hair - LSACPL',item_code:'T-1',rate:1000,minimum_price:800,maximum_price:1200},{therapy_type:'Facial',healthcare_service_unit:'Skin - LSACPL',item_code:'T-2',rate:500}];
      else if(args.doctype==='Therapy Plan Template')result=[{name:'PKG-1',plan_name:'Hair Package',item_code:'P-1',total_sessions:4,total_amount:4000,offer_price:3500,custom_including_gst:3675,is_active:1},{name:'PKG-2',plan_name:'LIFErise Starter',item_code:'P-2',total_sessions:2,total_amount:2000,offer_price:1800,custom_including_gst:1890,is_active:1}];
    }
    if(request.url.includes('price_list_api.active_offers'))result={offers:[{name:'OFFER-1',item_code:'T-1',apply_on:'Item Code',price_or_product_discount:'Price',discount_percentage:10,priority:1}]};
    if(request.url.includes('frappe.client.get')&&!request.url.includes('get_list'))result={name:'PKG-1',plan_name:'Hair Package',item_code:'P-1',is_active:1,total_sessions:4,total_amount:4000,offer_price:3500,custom_including_gst:3675,therapy_types:[{therapy_type:'Laser',no_of_sessions:4,rate:1000,amount:4000}]};
    await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({message:result})).toString('base64')});
  });
  const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.text);return result.result.value;};
  const wait=async expression=>{for(let attempt=0;attempt<100;attempt++){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,75));}throw Error('Timed out: '+expression+'\n'+await evaluate('document.body.innerText'));};
  try{
    await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:5175/api/*'}]});
    for(const width of [1440,390]){
      await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
      await send('Page.navigate',{url:'http://127.0.0.1:5175/life_portal/'+(width===1440?'pricelist':'native/pricelist')});
      await wait("document.querySelector('.price-list-native tbody')?.textContent.includes('Laser')");
      await wait("document.querySelector('.price-offer')?.textContent.includes('900')");
      assert.equal(await evaluate("document.querySelector('.price-list-native tbody').textContent.includes('Facial')"),true);
      await evaluate("document.querySelector('.price-filters button').click()");
      await wait("document.querySelectorAll('.price-list-native tbody tr').length===1");
      await evaluate("Array.from(document.querySelectorAll('.price-tabs button')).find(b=>b.textContent==='Packages').click()");
      await wait("document.querySelector('.price-list-native tbody')?.textContent.includes('Hair Package')");
      assert.equal(await evaluate("document.querySelector('.price-list-native tbody').textContent.includes('LIFErise Starter')"),false);
      await evaluate("document.querySelector('.price-list-native tbody button').click()");
      await wait("document.querySelector('.price-dialog')?.textContent.includes('Included Therapy Types')");
      assert.equal(await evaluate("document.querySelector('.price-dialog').textContent.includes('Laser')"),true);
      await evaluate("document.querySelector('.price-dialog header button').click()");
      await evaluate("Array.from(document.querySelectorAll('.price-tabs button')).find(b=>b.textContent==='LIFErise Packages').click()");
      await wait("document.querySelector('.price-list-native tbody')?.textContent.includes('LIFErise Starter')");
      assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"),true);
    }
    assert.equal(calls.some(call=>call.url.includes('price_list_api.active_offers')),true);
    assert.deepEqual(errors,[]);
    console.log('Price-List browser checks passed on desktop and mobile.');
  }finally{await send('Page.close');ws.close();}
})().catch(error=>{console.error(error);process.exit(1);});
