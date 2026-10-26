import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {webcrypto} from 'node:crypto';
import {CASH_ACCOUNT,expenditureRange,expenditurePayload,expenditureCsv,billUrl,rowFlow,journalRow} from '../src/lib/expenditure-domain.js';
const ledgers=JSON.parse(fs.readFileSync(new URL('../src/data/expenditureLedgers.json',import.meta.url)));
const config={branches:['Branch A','Head Office'],default_branch:'Branch A',today:'2026-10-26',entry_min_date:'2026-10-24',cost_centers:{'Branch A':'Branch A - LSACPL','Head Office':'Main - LSACPL'},accounts:[{name:CASH_ACCOUNT,account_type:'Cash'},{name:'BANK',account_type:'Bank'}],can_create:true,can_submit:true,can_export:true};
const staff=[{name:'E-1',employee_name:'Alice',is_approver:false},{name:'E-2',employee_name:'Manager',is_approver:true}];
const form=()=>({request_id:'REQUEST-1',name:'',modified:'',branch:'Branch A',date:'2026-10-26',payment_mode:'Petty Cash',funding_account:CASH_ACCOUNT,reference:'',paid_by:'Alice [E-1]',approved_by:'Manager [E-2]'});
const row=()=>({id:'ROW-1',type:'Electricity Bill',account:ledgers.LM['Electricity Bill'],description:'Electricity',amount:200,remarks:'',bill_required:false,bill_url:'',party_type:'',party:'',file:null});
test('source accounting mappings, permitted staff, dates and non-cash funding are preserved',()=>{
 const original=JSON.parse(fs.readFileSync(new URL('../../life_slimming/portal_pages/branch-expenditure-entry.json',import.meta.url))).javascript;
 const originalConfig=JSON.parse(original.match(/const CFG = (\{[^\n]+\});/)[1]);assert.deepEqual(ledgers.LM,originalConfig.LM);assert.deepEqual(ledgers.LM_OPTIONS,originalConfig.LM_OPTIONS);
 const f=form(),r=row();const p=expenditurePayload(f,[r],staff,config,ledgers);assert.equal(p.paid_by,'E-1');assert.equal(p.approved_by,'E-2');assert.equal(p.request_id,'REQUEST-1');assert.equal(p.items[0].amount,200);
 assert.throws(()=>expenditurePayload({...f,date:'2026-10-23'},[r],staff,config,ledgers),/previous two days/);
 assert.throws(()=>expenditurePayload({...f,approved_by:'Alice [E-1]'},[r],staff,config,ledgers),/valid manager/);
 assert.throws(()=>expenditurePayload({...f,payment_mode:'UPI'},[r],staff,config,ledgers),/payment ledger/);
 assert.equal(expenditurePayload({...f,payment_mode:'UPI',funding_account:'BANK'},[r],staff,config,ledgers).funding_account,'BANK');
});
test('HO transfers, bill attachment and safe links retain their original constraints',()=>{
 const f=form(),r={...row(),type:'Cash Given to Head Office',account:CASH_ACCOUNT};assert.match(rowFlow(r,f,config),/Debit:.*Main · Credit: same account.*Branch A/);
 assert.throws(()=>expenditurePayload({...f,payment_mode:'Bank',funding_account:'BANK'},[r],staff,config,ledgers),/HO transfers require Petty Cash/);
 assert.throws(()=>expenditurePayload({...f,branch:'Head Office'},[r],staff,config,ledgers),/other than Head Office/);
 assert.throws(()=>expenditurePayload(f,[{...row(),bill_required:true}],staff,config,ledgers),/Attach a bill/);
 assert.equal(billUrl('javascript:alert(1)'),'');assert.equal(billUrl('/private/files/bill.pdf'),'/private/files/bill.pdf');
 const parsed=journalRow({remarks:'Electricity | [[BILLURL:%2Fprivate%2Ffiles%2Fbill.pdf]]'});assert.equal(parsed.bill,'/private/files/bill.pdf');assert.equal(parsed.remarks,'Electricity');
});
test('sales-cycle presets and exports retain dates, drafts, quoted text and formula protection',()=>{
 assert.deepEqual(expenditureRange('month','2026-01-05'),['2025-12-06','2026-01-05']);assert.deepEqual(expenditureRange('lastmonth','2026-01-06'),['2025-12-06','2026-01-05']);assert.deepEqual(expenditureRange('yesterday','2026-03-01'),['2026-02-28','2026-02-28']);
 const csv=expenditureCsv([{name:'JE-1',docstatus:0,date:'2026-10-26',items:[{type:'Electricity Bill',description:'=HYPERLINK("bad")',amount:200}]}]);assert(csv.includes('"Draft"'));assert(csv.includes('"\'=HYPERLINK(""bad"")"'));assert(csv.includes('"200"'));
});
const source=fs.readFileSync(new URL('../src/composables/useBranchExpenditure.js',import.meta.url),'utf8').replace(/^import .*;\n/gm,'').replace('export function useBranchExpenditure','function useBranchExpenditure');
async function setup(){const calls=[],storage=new Map();let leave,handler;
 const context={ref:value=>({value}),reactive:value=>value,computed:fn=>({get value(){return fn();}}),watch(){},onMounted(){},onBeforeUnmount(){},onBeforeRouteLeave:fn=>leave=fn,request:async(method,opts)=>{calls.push({method,...opts});return {message:await handler(opts.args.action,opts.args)};},session:{user:'user'},ledgers,CASH_ACCOUNT,expenditureRange,expenditurePayload,expenditureCsv,billUrl,crypto:webcrypto,window:{confirm:()=>true},sessionStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},AbortController,FormData,Blob,URL,document:{createElement:()=>({click(){}})},setInterval,clearInterval,setTimeout,Map,Date,JSON,Number,Object,Array,Error};
 handler=async action=>action==='boot'?config:action==='staff'?{employees:staff}:{entries:[],next_offset:0,has_more:false,summary:{opening:100,cash_in:300,cash_out:200,balance:200}};
 vm.createContext(context);vm.runInContext(source+'\nthis.model=useBranchExpenditure();',context);const model=context.model;await model.initialize();Object.assign(model.form,form());model.rows.value=[row()];return {model,calls,storage,leave:()=>leave(),handle:fn=>handler=fn};
}
test('ambiguous save retries keep their request ID and confirmation uses server cash totals',async()=>{
 const {model,calls,storage,handle}=await setup();let attempts=0;handle(async(action)=>{if(action==='submit'){if(++attempts===1)throw Object.assign(Error('Timed out'),{code:'TimeoutError'});return{name:'JE-1',modified:'v2',docstatus:1};}return{entries:[],next_offset:0,has_more:false,summary:{opening:100,cash_in:300,cash_out:200,balance:200}};});
 await model.save('submit');assert.match(model.error.value,/same entry ID/);assert.equal(model.finished.value,false);assert.equal(JSON.parse([...storage.values()][0]).payload.request_id,'REQUEST-1');
 await model.save('submit');const requests=calls.filter(c=>c.args.action==='submit').map(c=>JSON.parse(c.args.payload));assert.equal(requests.length,2);assert.equal(requests[0].request_id,requests[1].request_id);assert.equal(model.finished.value,true);assert.equal(model.summary.value.balance,200);assert.equal(model.form.name,'JE-1');
});
test('duplicate clicks and navigation are blocked during a pending posting',async()=>{
 const {model,calls,leave,handle}=await setup();let resolve;handle(action=>action==='submit'?new Promise(r=>resolve=r):{entries:[],has_more:false});const pending=model.save('submit');await Promise.resolve();assert.equal(model.busy.value,true);assert.equal(leave(),false);await model.save('submit');assert.equal(calls.filter(c=>c.args.action==='submit').length,1);resolve({name:'JE-2',modified:'v2',docstatus:1});await pending;assert.equal(model.busy.value,false);assert.equal(leave(),true);
});
