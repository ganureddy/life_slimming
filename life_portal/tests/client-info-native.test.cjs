const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const root=path.join(__dirname,'..');
const domain=fs.readFileSync(path.join(root,'src/lib/client-info.js'),'utf8');
const api=vm.runInNewContext(domain.replaceAll('export ','')+'\n({TODAY,addDays,tierFor,planHealth,clientStatus,dueInfo,analyze,buildClientList,clientListTotals,medicalInfo,lookupRule})',{Date,Map,Set});
test('client status, tier and overdue rules preserve legacy boundaries',()=>{
 const today=api.TODAY();assert.equal(api.clientStatus(api.addDays(today,-30),[]),'active');assert.equal(api.clientStatus(api.addDays(today,-31),[]),'irregular');assert.equal(api.clientStatus(api.addDays(today,-90),[]),'irregular');assert.equal(api.clientStatus(api.addDays(today,-91),[]),'stopped');assert.equal(api.clientStatus(today,[{status:'Completed'},{status:'Cancelled'}]),'completed');
 assert.equal(api.tierFor(199999),null);assert.equal(api.tierFor(200000).key,'VIP');assert.equal(api.tierFor(250000).key,'VVIP');assert.equal(api.tierFor(500000).key,'VVIP');assert.equal(api.tierFor(500000.01).key,'HNI');
 const health=api.planHealth({start:api.addDays(today,-15),total:2,done:0});assert.equal(health.estimated,true);assert.equal(health.state,'overdue');assert.equal(health.due,api.addDays(today,-1));assert.equal(api.planHealth({status:'Cancelled',total:2,done:0}).state,'cancelled');
 const due=api.dueInfo([{outstanding_amount:0.99,due_date:'2000-01-01'},{outstanding_amount:100,due_date:today},{outstanding_amount:50,due_date:'2000-01-01'},{outstanding_amount:-20}]);assert.equal(due.pending,150);assert.equal(due.overdue,1);assert.equal(due.next,today);
});
test('list separates period invoice paid, lifetime outstanding and independent collections',()=>{
 const rows=api.buildClientList([{name:'P',patient:'A',patient_name:'Alice',start_date:'2026-10-01',branch:'Clinic A',status:'Active'},{patient:'X',branch:'Testing Branch'}],[{patient:'A',name:'OLD',posting_date:'2026-09-01',base_grand_total:100,outstanding_amount:50},{patient:'A',name:'NEW',posting_date:'2026-10-01',base_grand_total:200,outstanding_amount:25},{patient:'A',name:'RETURN',posting_date:'2026-10-01',base_grand_total:-20,outstanding_amount:0,is_return:1}],[{patient:'A',start_date:api.TODAY(),docstatus:1},{patient:'A',docstatus:2}],[{name:'A',mobile:'+91 9876543210'}],'2026-10-01','2026-10-31');
 assert.equal(rows.length,1);assert.equal(rows[0].paid,155);assert.equal(rows[0].pending,75);assert.equal(rows[0].invCount,2);assert.equal(rows[0].visits,1);assert.equal(rows[0].mobile,'9876543210');
 const totals=api.clientListTotals(rows,[{branch:'Clinic A',mode_of_payment:'Cash',received_amount:250},{branch:'Clinic B',received_amount:100}],'Clinic A');assert.equal(totals.collected,250);assert.equal(totals.balance,-95);
 assert.equal(api.buildClientList([],[],[],[{name:'B',patient_name:'Outside date'}],'','',true)[0].name,'Outside date');
});
test('profile analysis stays pure and preserves medical flags and child therapy quantities',()=>{
 const bundle={patient:{name:'A',patient_name:'Alice',medical_history:'<p>Thyroid condition</p>'},plans:[{name:'P',total_sessions:99,therapy_plan_details:[{therapy_type:'Cryo',no_of_sessions:5,sessions_completed:2}]}],sessions:[],invoices:[],appts:[],followups:[],users:{}};
 const before=JSON.stringify(bundle),metrics=api.analyze(bundle);assert.equal(JSON.stringify(bundle),before);assert.equal(metrics.totalS,5);assert.equal(metrics.doneS,2);assert.equal(metrics.med.isMedical,true);assert.equal(metrics.med.issues[0].text,'Thyroid condition');assert.equal(metrics.planView.length,1);
 assert.equal(api.lookupRule('Al').ok,false);assert.equal(api.lookupRule('Alice').ok,true);
});
const readerSource=fs.readFileSync(path.join(root,'src/api/client-info.js'),'utf8').replace(/^import .*;$/gm,'').replace('export ','');
function reader(request,signal){return vm.runInNewContext(readerSource+'\ncreateClientInfoReader(signal)',{request,signal,session:{csrf_token:'token'},URLSearchParams,DOMException,Map,Promise,Array,Error});}
test('reader paginates, detects truncated reports and refuses malformed lists',async()=>{
 let calls=0;const r=reader(async(method,{args})=>{calls++;return {message:Array.from({length:args.limit_start===0?500:3},(_,i)=>({name:args.limit_start+i}))};});assert.equal((await r.list('Patient',[],['name'],1000)).length,503);assert.equal(calls,2);
 await assert.rejects(reader(async()=>({message:[{name:'extra'}]})).list('Patient',[],['name'],1),/shorter date range/);
 await assert.rejects(reader(async()=>({message:{}})).list('Patient',[],['name']),/invalid record list/);
});
test('lookup treats branch-scoped denial as authoritative without broad fallback',async()=>{
 const calls=[];await assert.rejects(reader(async(method,options)=>{calls.push({method,options});return{message:{ok:false,message:'Branch access denied'}};}).lookup({action:'search',q:'Alice'}),/Branch access denied/);assert.equal(calls.length,1);assert(calls[0].method.includes('branch_patient_lookup.run?action=search&q=Alice'));assert.equal(calls[0].options.httpMethod,'GET');
});
test('background document pool bounds concurrency and honors cancellation',async()=>{
 let running=0,peak=0;const r=reader(async()=>({message:[]}));const rows=await r.pool([1,2,3,4,5,6,7,8,9],async value=>{running++;peak=Math.max(peak,running);await new Promise(resolve=>setTimeout(resolve,2));running--;return value*2;});assert.equal(peak,4);assert.equal(rows[8],18);
 const controller=new AbortController();controller.abort();await assert.rejects(reader(async()=>{throw Error('must not call');},controller.signal).doc('Patient','A'),{name:'AbortError'});
});
test('Client Info preview owns its source and does not replace the incomplete main route',()=>{
 const files=['src/pages/ClientInfoPage.vue','src/api/client-info.js','src/composables/useClientInfo.js','src/composables/useClientMedical.js','src/lib/client-info.js',...fs.readdirSync(path.join(root,'src/components/client-info')).map(name=>'src/components/client-info/'+name)];for(const file of files){assert(!/portal_pages|PortalSourcePage|<iframe|v-html|innerHTML|\beval\s*\(|new Function\s*\(|window\.frappe/.test(fs.readFileSync(path.join(root,file),'utf8')),file);}
 const router=fs.readFileSync(path.join(root,'src/router/index.js'),'utf8');assert(router.includes('/native/client-info'));assert(!router.match(/const nativeModules = new Set\(\[([^\]]+)/)[1].includes('cliinfo'));
});

const medicalSource=fs.readFileSync(path.join(root,'src/composables/useClientMedical.js'),'utf8').replace(/^import .*;$/gm,'').replace('export ','');
function medicalHarness(bundle,list){let cleanup;const state=vm.runInNewContext(medicalSource+'\nuseClientMedical(bundle)',{bundle,AbortController,ref:value=>({value}),onBeforeUnmount:callback=>{cleanup=callback;},createClientInfoReader:signal=>({list:(...args)=>list(signal,...args)}),Promise});return {state,cleanup:()=>cleanup()};}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
test('medical data caches only complete successful responses and stays scoped to its patient',async()=>{
 const calls=[],bundle={pid:'PAT-A',lazy:{}};const harness=medicalHarness(bundle,async(signal,doctype,filters)=>{calls.push({doctype,filters});return [{name:doctype}];});await flush();assert.equal(calls.length,2);assert.equal(calls[0].filters[0][2],'PAT-A');assert.equal(bundle.lazy.medical.vitals.length,1);assert.equal(harness.state.loading.value,false);harness.cleanup();
 const cached=medicalHarness(bundle,()=>{throw Error('must not reread cached profile');});assert.equal(cached.state.data.value,bundle.lazy.medical);cached.cleanup();
 const other={pid:'PAT-B',lazy:{}},pending=[];const closed=medicalHarness(other,(signal)=>new Promise(resolve=>pending.push({signal,resolve})));closed.cleanup();assert(pending.every(row=>row.signal.aborted));pending.forEach(row=>row.resolve([]));await flush();assert.equal(other.lazy.medical,undefined,'a closed tab must not commit stale data');
});
test('medical failures remain errors rather than cached empty records and permit retry',async()=>{
 let denied=true;const bundle={pid:'A',lazy:{}},harness=medicalHarness(bundle,async()=>{if(denied)throw Error('Permission denied');return[];});await flush();assert.equal(harness.state.error.value,'Permission denied');assert.equal(harness.state.data.value,null);assert.equal(bundle.lazy.medical,undefined);assert.equal(harness.state.loading.value,false);denied=false;await harness.state.load();assert.equal(harness.state.error.value,'');assert.equal(bundle.lazy.medical.enc.length,0);harness.cleanup();
});
