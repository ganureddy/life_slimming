const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../src/lib/dom-page-runtime.js'),'utf8').replace(/^import .*;\n/gm,'').replace('export function createDomPageRuntime','function createDomPageRuntime');
function setup(){
 const calls=[],listeners=[],removed=[],timers=[],cancelled=[],pending=[];
 class Observer{constructor(callback){this.callback=callback;}disconnect(){this.disconnected=true;}}
 const win={location:{href:'https://portal.test/life_portal/tasks',origin:'https://portal.test'},CSS:{escape:v=>v},MutationObserver:Observer,
 setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:id=>cancelled.push(id),setInterval:()=>99,clearInterval:id=>cancelled.push(id),
 addEventListener:(...args)=>listeners.push(args),removeEventListener:(...args)=>removed.push(args),
 fetch:async(url,options)=>{calls.push({url,options});return {ok:true};}};
 const root={id:'page',matches:s=>s==='#page',querySelector:s=>({selector:s}),querySelectorAll:()=>[],append(){},appendChild(){}};
 const doc={defaultView:win,addEventListener:win.addEventListener,removeEventListener:win.removeEventListener};root.ownerDocument=doc;
 const status={reads:0,writes:0,error:'',notice:''},ctx={URL,Headers,AbortController,DOMException,Set,Proxy,JSON,Error,Object,String,console,
 apiUrl:path=>'https://erp.test'+path,apiCredentials:()=> 'include',endpoints:{report:'app.report'},
 request:(method,options)=>new Promise(resolve=>pending.push({method,options,resolve}))};
 vm.createContext(ctx);vm.runInContext(source+'\nthis.create=createDomPageRuntime;',ctx);
 return {runtime:ctx.create({root,session:{user:'agent',roles:[],csrf_token:'secret'},status}),status,win,root,calls,pending,listeners,removed,timers,cancelled};
}
test('dashboard runtime isolates page DOM, global state and event cleanup',()=>{
 const s=setup();s.runtime.window.privateFlag=true;assert.equal(s.win.privateFlag,undefined);assert.equal(s.runtime.document.getElementById('page'),s.root);
 s.runtime.window.addEventListener('resize',()=>{});s.runtime.document.addEventListener('click',()=>{});
 const observer=new s.runtime.MutationObserver(()=>{});s.runtime.setTimeout(()=>{},50);s.runtime.setInterval(()=>{},100);
 s.runtime.dispose();assert.equal(s.removed.length,2);assert.equal(observer.disconnected,true);assert(s.cancelled.includes(99));assert(s.cancelled.includes(1));
});
test('dashboard requests map to configured ERP and keep credentials off external hosts',async()=>{
 const s=setup();await s.runtime.fetch('/api/method/report');const first=s.calls[0];assert.equal(first.url,'https://erp.test/api/method/app.report');assert.equal(first.options.method,'POST');assert.equal(first.options.credentials,'include');assert.equal(first.options.headers.get('X-Frappe-CSRF-Token'),'secret');
 await s.runtime.fetch('https://external.test/data');assert.equal(s.calls[1].options.headers.has('X-Frappe-CSRF-Token'),false);assert.equal(s.calls[1].options.credentials,'same-origin');
});
test('unmount aborts outstanding reads and suppresses callbacks from the old page',async()=>{
 const s=setup();let applied=false;const result=s.runtime.frappe.call({method:'frappe.client.get',args:{doctype:'Note'},callback:()=>applied=true});
 assert.equal(s.status.reads,1);s.runtime.dispose();assert.equal(s.pending[0].options.signal.aborted,true);s.pending[0].resolve({message:[]});await result;assert.equal(applied,false);
});
