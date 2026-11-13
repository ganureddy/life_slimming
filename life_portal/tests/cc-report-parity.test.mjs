import test from 'node:test';
import assert from 'node:assert/strict';
import {marketingReport} from '../src/lib/cc-marketing-report.js';
import {reportRoute,reportTabs} from '../src/lib/cc-report-navigation.js';
test('each legacy tab has its own route and old queries keep date filters',()=>{
 assert.equal(new Set(reportTabs.map(t=>reportRoute(t.key).path)).size,7);
 assert.deepEqual(reportRoute('marketing',{tab:'marketing',from:'2026-11-01'}),{path:'/ccvisit/marketing',query:{from:'2026-11-01'}});
 assert.equal(reportRoute('nofollowup').path,'/ccvisit/agents/no-follow-up');
});
test('marketing preserves separate receipt, appointment and payment cohorts',()=>{
 const common={source:'Website',branch:'A',enquired_for:'Skin'};
 const rows=[{...common,name:'old',creation:'2026-10-01',custom_appointment_date_and_time:'2026-11-10',custom_appointment_status:'Visited Booked',custom_cc_sub_status:'Walked in: not booked'},
 {...common,name:'new',creation:'2026-11-10',status:'Interested'},
 {...common,name:'junk',creation:'2026-11-10',status:'Wrong Number'}];
 const payment={...common,therapy_plan:'TP-1',therapy_plan_media:'Call Center',payment_date:'2026-11-10',paid:500};
 const data={rows,cc_invoice_report_summary:{payment_rows:[payment,{...payment,payment_entry:'P-2',is_later_collection:1},{...payment,therapy_plan_already_taken:1},{...payment,payment_date:'2026-10-01'}]}};
 const report=marketingReport(data,{from_date:'2026-11-01',to_date:'2026-11-30'});
 assert.equal(report.totals.raw,2);assert.equal(report.totals.quality,1);assert.equal(report.totals.junk,1);assert.equal(report.totals.connected,1);
 assert.equal(report.totals.visits,1);assert.equal(report.totals.booked,1);assert.equal(report.totals.unbooked,0);
 assert.equal(report.totals.paid,1000);assert.equal(report.totals.outstanding,500);
 assert.equal(marketingReport(data,{from_date:'2026-11-01',to_date:'2026-11-30'},{agencies:['Other']}).totals.raw,0);
});

test('legacy ranking caps achievements and withholds ranks without approved inputs',async()=>{
 const {rankReportAgents}=await import('../src/lib/cc-report-ranking.js');
 const appointments=Array.from({length:20},(_,i)=>({lead_owner:'agent',custom_appointment_status:i<10?'Visited Booked':'Visited Not Booked'}));
 assert.equal(rankReportAgents(appointments,[])[0].rank,null);
 const [row]=rankReportAgents(appointments,[],{agent:{bookingTarget:10,visitTarget:20,handling:100,followup:100}});
 assert.equal(row.score,90);assert.equal(row.rank,1);
 const [low]=rankReportAgents(appointments.slice(0,4),[],{agent:{bookingTarget:2,visitTarget:4,handling:100,followup:100}});
 assert.equal(low.score,80);assert.equal(low.bookingAchievement,100);assert.equal(low.conversionWeight,0);
});
test('old-package collections never inflate new-package invoice values',async()=>{
 const {packageSplit,consultantRollingRange}=await import('../src/lib/cc-report-financials.js');
 const base={therapy_plan:'TP',therapy_plan_media:'Call Center',with_gst:1000,without_gst:900,balance:500,paid:500};
 const totals=packageSplit([{...base,invoice_date:'2026-11-10'},{...base,invoice_date:'2026-10-01'},{...base,invoice_date:'2026-11-10',therapy_plan_already_taken:1}],'2026-11-01','2026-11-30');
 assert.equal(totals.withGst,1000);assert.equal(totals.paid,500);assert.equal(totals.oldPackagePaid,500);
 assert.deepEqual(consultantRollingRange('2026-09-15'),['2026-06-16','2026-09-15']);
});

test('agent scorecard uses the legacy core-agent benchmark and appointment outcomes',async()=>{
 const {agentBenchmarks,agentPeriodMetrics}=await import('../src/lib/cc-report-scorecard.js');
 const make=(owner,count)=>Array.from({length:count},(_,index)=>({name:owner+index,lead_owner:owner,creation:'2026-11-12 09:00:00',custom_appointment_date_and_time:'2026-11-12 10:00:00',custom_appointment_status:index%2?'Visited Not Booked':'Visited Booked'}));
 const data={rows:[...make('A',20),...make('B',1),...make('C',3)]},range={from_date:'2026-11-12',to_date:'2026-11-12'};
 const metrics=agentPeriodMetrics(data,range,['A']);assert.equal(metrics.appointments,20);assert.equal(metrics.visits,20);assert.equal(metrics.booked,10);assert.equal(metrics.conversion,50);
 assert.deepEqual(agentBenchmarks(data,range,'A').core.map(r=>r.agent),['A','C']);
 assert.deepEqual(agentBenchmarks(data,range,'B').core.map(r=>r.agent),['A','B','C']);
});
