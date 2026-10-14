import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SLIMMING, CARD_START, maskMobile, monthRange, previousMonth, monthRows, openCardRows, closingWeight, openingWeight, sessionDifference, excelTable } from '../src/lib/weight-loss.js';
const plan = (name,patient,start,extra={}) => ({name,patient,start_date:start,category:SLIMMING,status:'In Progress',docstatus:1,branch:'Branch A',total_sessions:20,total_sessions_completed:0,...extra});
test('open cards include new joiners with no visits and old plans with attendance; deduplicate clients across branches',()=>{
 const plans=[plan('NEW','PAT-NEW','2026-10-01'),plan('NEW-B','PAT-NEW','2026-10-01',{branch:'Branch B'}),plan('OLD','PAT-OLD','2025-03-01'),plan('OLD-NO-VISIT','PAT-NO','2025-03-01'),plan('TOTAL-COMPLETE','PAT-COMPLETE','2026-10-01',{total_sessions_completed:20}),plan('CANCELLED','PAT-CANCEL','2026-10-01',{docstatus:2}),plan('FUTURE','PAT-FUTURE','2026-11-01'),plan('EXCLUDED','PAT-TEST','2026-10-01',{branch:'Testing Branch'}),plan('STATUS-COMPLETE','PAT-STATUS','2026-10-01',{status:'Completed'})];
 const rows=openCardRows({attendance:[{name:'TS-1',therapy_plan:'OLD',docstatus:1}],plans,patients:[{name:'PAT-NEW',mobile:'+919876543210'}],today:'2026-10-13'});
 assert.equal(CARD_START,'2026-01-01');assert.deepEqual(rows.map(row=>row.patient),['PAT-NEW','PAT-OLD']);assert.deepEqual(rows[0].open_branches,['Branch A','Branch B']);assert.deepEqual(rows[0].open_plans,['NEW','NEW-B']);assert.equal(rows[0].mobile,'987****210');
});
test('monthly weights use previous closing or current opening and lifetime sessions remain separate',()=>{
 const current=[{name:'CUR-1',patient:'PAT-1',start_date:'2026-10-01',before_weight:90,after_weight:88,docstatus:1},{name:'CUR-2',patient:'PAT-1',start_date:'2026-10-13',before_weight:88,after_weight:87,docstatus:1},{name:'CUR-BETA',patient:'PAT-2',start_date:'2026-10-13',before_weight:80,after_weight:82,docstatus:1}];
 const previous=[{name:'PREV',patient:'PAT-1',start_date:'2026-09-30',before_weight:91,after_weight:90,docstatus:1}];
 const history=[{name:'FIRST',patient:'PAT-1',start_date:'2026-08-01',before_weight:100,after_weight:99,docstatus:1},...previous,...current];
 const rows=monthRows({month:'2026-10',current,previous,history,plans:[plan('PLAN-1','PAT-1','2026-01-01')],patients:[{name:'PAT-1',mobile:'9876543210'}]});
 const alpha=rows.find(row=>row.patient==='PAT-1'),beta=rows.find(row=>row.patient==='PAT-2');
 assert.equal(alpha.month_difference,3);assert.equal(alpha.total_change,13);assert.equal(alpha.completed_sessions,2);assert.equal(alpha.lifetime_sessions.length,4);assert.equal(alpha.mobile,'987****210');assert.equal(alpha.used_current_opening_as_reference,false);assert.equal(beta.month_difference,-2);assert.equal(beta.used_current_opening_as_reference,true);assert.equal(beta.reference_source,'October 2026 Opening Used');
});
test('weight fallbacks skip missing values and zero-weight differences are not fabricated',()=>{
 const rows=[{name:'A',start_date:'2026-10-01',after_weight:90},{name:'B',start_date:'2026-10-02',before_weight:89},{name:'C',start_date:'2026-10-03',before_weight:0,after_weight:0}];
 assert.equal(openingWeight(rows),90);assert.equal(closingWeight(rows),89);assert.equal(sessionDifference(rows[0]),0);
});
test('month ranges handle leap years and year rollover',()=>{
 assert.deepEqual(monthRange('2024-02'),{start:'2024-02-01',end:'2024-02-29'});assert.equal(previousMonth('2026-01'),'2025-12');assert.equal(maskMobile('+91 98765 43210'),'987****210');
});
test('Excel output escapes client text and preserves phone strings',()=>{
 const html=excelTable(['Client','Mobile'],[['<script>alert(1)</script>','987****210']]);assert(html.includes('&lt;script&gt;'));assert(!html.includes('<script>'));assert(html.includes('987****210'));assert(html.includes('mso-number-format'));
});
