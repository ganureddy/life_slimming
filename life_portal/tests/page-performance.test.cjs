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
