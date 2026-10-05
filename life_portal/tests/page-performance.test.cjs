const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const source=name=>JSON.parse(fs.readFileSync(path.join(__dirname,'../../life_slimming/portal_pages',name+'.json'))).javascript;
const approvals=source('approvals-report');
const counts=approvals.slice(approvals.indexOf('async function refreshBaseCounts()'),approvals.indexOf('function globalClientFiltersActive()'));
for(const manager of [true,false])test('count requests run in one wave with purchase access '+manager,async()=>{
 const pending=[],calls=[];
 const ctx={TOTALS:{},STOCK_TOTALS:{},visibleTypeOrder:()=>['P2P','STK',...(manager?['PO','PI']:[])],isStockReportType:t=>['STK','PO','PI'].includes(t),canAccessPurchaseTabs:()=>manager,STOCK_SOURCE_ORDER:['MR','PO','PI'],SOURCE_CFG:{P2P:{doctype:'Conversion'}},STOCK_SOURCE_CFG:{MR:{doctype:'Request'},PO:{doctype:'Order'},PI:{doctype:'Invoice'}},serverFiltersFor:()=>[],stockServerFilters:()=>[],safeCount:dt=>{calls.push(dt);return new Promise(resolve=>pending.push(resolve));}};
 vm.runInNewContext(counts,ctx);const result=ctx.refreshBaseCounts();
 assert.deepEqual(calls,manager?['Conversion','Request','Order','Invoice']:['Conversion','Request']);
 pending.forEach((resolve,i)=>resolve(i+1));await result;
 assert.equal(ctx.TOTALS.P2P,1);assert.equal(ctx.TOTALS.STK,2);assert.equal(ctx.TOTALS.PO,manager?3:0);assert.equal(ctx.TOTALS.PI,manager?4:0);
});
test('offscreen roster does not request data until first intersection',()=>{
 const branch=source('branch-command-center');const code=branch.slice(branch.indexOf('function portalWhenVisible('),branch.indexOf('// Load branches and initial data'));
 let callback,loads=0,disconnected=0;
 const target={};class Observer{constructor(cb){callback=cb;}observe(node){assert.equal(node,target);}disconnect(){disconnected++;}}
 const ctx={document:{querySelector:()=>target},window:{IntersectionObserver:Observer},IntersectionObserver:Observer};vm.runInNewContext(code,ctx);
 ctx.portalWhenVisible('roster',()=>loads++);assert.equal(loads,0);callback([{isIntersecting:false}]);assert.equal(loads,0);callback([{isIntersecting:true}]);assert.equal(loads,1);assert.equal(disconnected,1);
});

test('branch changes defer unopened roster but refresh it after initialization',()=>{
 const branch=source('branch-command-center');
 const code=branch.slice(branch.indexOf('function syncRosterToBranch(){'),branch.indexOf('function updateWeekLabel(){'));
 let weeks=0,months=0;
 const ctx={curBranch:'Demo B',portalRosterInitialized:false,rosterState:{},document:{querySelector:()=>({}),getElementById:()=>null},loadWeek:()=>weeks++,loadMonthlySummary:()=>months++};
 vm.runInNewContext(code,ctx);
 ctx.syncRosterToBranch();assert.equal(ctx.rosterState.branch,'Demo B');assert.equal(weeks,0);assert.equal(months,0);
 ctx.portalRosterInitialized=true;ctx.syncRosterToBranch();assert.equal(weeks,1);assert.equal(months,1);
});

test('CC lead requests start while master lists are still pending', async () => {
 const dashboard=source('cc-new-dashboard-bhuvan-oct2');
 const start=dashboard.indexOf('  async function seedLeads() {');
 const end=dashboard.indexOf('    const leadResp = fetches[0];',start);
 const calls=[],pending=[];
 const ctx={PORTAL:{loaded:false},window:{},CM_DESIGNATIONS:[],DOCTOR_DESIGNATIONS:[],CM_PRIMARY:[],CM_SECONDARY:[],
  rangeFrom:()=> '2026-10-05',rangeTo:()=> '2026-10-05',console,toast:()=>{},
  portalGetList:(doctype)=>{calls.push(doctype);return new Promise(resolve=>pending.push(()=>resolve([])));},
  frappe:{call:({args})=>{calls.push(args.date_mode);return Promise.resolve({message:[]});}}};
 vm.runInNewContext(dashboard.slice(start,end)+'return fetches;\n}',ctx);
 const result=ctx.seedLeads();
 assert(calls.includes('created')&&calls.includes('appointment')&&calls.includes('followup'));
 assert.equal(ctx.PORTAL.loaded,false);
 pending.splice(0).forEach(resolve=>resolve());
 // Allow the second group of master reads to start together.
 await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(calls.slice(-3),['Employee','Employee','User']);
 pending.splice(0).forEach(resolve=>resolve());
 await result;
 assert.equal(ctx.PORTAL.loaded,true);
});
