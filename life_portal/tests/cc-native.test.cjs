const {test}=require('node:test');
const assert=require('node:assert/strict');
const lib=import('../src/lib/cc.js');
test('India date and sales cycle boundaries do not depend on browser timezone',async()=>{
 const {indiaStamp,dateRange}=await lib;
 assert.equal(indiaStamp(new Date('2026-10-04T20:00:00Z')).slice(0,10),'2026-10-05');
 assert.deepEqual(dateRange('month','2026-10-05'),['2026-09-06','2026-10-05']);
 assert.deepEqual(dateRange('month','2026-10-06'),['2026-10-06','2026-11-05']);
 assert.deepEqual(dateRange('nextmonth','2026-12-31'),['2027-01-06','2027-02-05']);
 assert.deepEqual(dateRange('week','2026-12-31'),['2027-01-01','2027-01-07']);
});
test('live status precedence, pending outcomes and overdue counts',async()=>{
 const {visitStatus,visitMetrics}=await lib;
 assert.equal(visitStatus({custom_appointment_status:'Scheduled',custom_visit_status:'Visited & Booked'}),'Visited-BKD');
 assert.equal(visitStatus({custom_appointment_status:'Visited – Not Booked'}),'Visited-Not BKD');
 const rows=[{status:'Scheduled',custom_appointment_date_and_time:'2026-10-05 10:00:00'},{status:'Scheduled',custom_appointment_date_and_time:'2026-10-06 10:00:00'},{status:'Visited'},{status:'Visited & Booked'},{status:'Not Visited'}];
 assert.deepEqual(visitMetrics(rows,'2026-10-05 11:00:00'),{appointments:5,visits:2,booked:1,pending:2,overdue:1});
});
test('CSV escapes quotes and formulas; exported phone values remain masked',async()=>{
 const {csvText,maskPhone}=await lib;
 const csv=csvText([{key:'name',label:'Client'},{key:'mobile',label:'Phone',value:r=>maskPhone(r.mobile)}],[{name:' =HYPERLINK("bad")',mobile:'9876543210'},{name:'a,b\nc',mobile:''}]);
 assert.ok(csv.includes('"\' =HYPERLINK(""bad"")"'));assert.ok(csv.includes('"a,b\nc"'));assert.ok(csv.includes('98******10'));assert.ok(!csv.includes('9876543210'));
});
