import test from 'node:test';
import assert from 'node:assert/strict';
import { reportRange,businessCycle,cycleDays,reportGroups,reportDrilldown,aggregateMoney } from '../src/lib/cc-visit-report.js';
test('report uses Monday weeks and sixth-to-fifth business cycles',()=>{
 assert.deepEqual(reportRange('week','2026-11-11'),['2026-11-09','2026-11-15']);
 assert.deepEqual(reportRange('lastweek','2026-11-11'),['2026-11-02','2026-11-08']);
 assert.deepEqual(businessCycle('2026-01-03'),['2025-12-06','2026-01-05']);
 assert.deepEqual(reportRange('lastmonth','2026-11-11'),['2026-10-06','2026-11-05']);
 const days=cycleDays('2024-02-11');assert.equal(days.length,29);assert.equal(days.at(-1),'2024-03-05');
});
test('group summary and drilldowns use the same appointment population',()=>{
 const rows=[{name:'1',branch:'A',lead_owner:'x',custom_appointment_status:'Visited Booked'}, {name:'2',branch:'A',lead_owner:'y',custom_appointment_status:'Visited Not Booked'}, {name:'3',branch:'B',lead_owner:'x',custom_appointment_status:'Booked',custom_appointment_date_and_time:'2026-11-01 09:00:00'}, {name:'4',branch:'B',lead_owner:'y',custom_appointment_status:'Not Visited'}];
 const groups=reportGroups(rows,'branch','2026-11-11 10:00:00');
 assert.equal(groups[0].visits,2);assert.equal(groups[0].booked,1);assert.equal(groups[0].conversion,50);assert.equal(groups[1].pending,1);
 assert.deepEqual(reportDrilldown(rows,'booked').map(r=>r.name),['1']);assert.deepEqual(reportDrilldown(rows,'noShow').map(r=>r.name),['4']);
 assert.equal(reportGroups(rows,'agent')[0].appointments,2);
});
test('money summaries preserve GST-inclusive paid amount and outstanding',()=>{
 const [row]=aggregateMoney([{branch:'A',with_gst:100,paid_with_gst:60,paid:50,balance:40},{branch:'A',with_gst:200,paid:100,balance:100}],'branch');
 assert.equal(row.billed,300);assert.equal(row.paid,160);assert.equal(row.balance,140);
});
