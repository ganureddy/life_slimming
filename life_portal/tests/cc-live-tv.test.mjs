import { test } from 'node:test';
import assert from 'node:assert/strict';
import { leaderboard, rank, changes, sortedAgents, waitingLeads, highlights } from '../src/lib/cc-live-tv.js';
const row = {name:'L1',lead_name:'Client',lead_owner:'a',creation:'2026-10-09 09:00:00',modified:'2026-10-09 09:00:00',custom_appointment_date_and_time:'2026-10-09 14:00:00',custom_appointment_status:'Scheduled'};
const snapshot = rows => ({rows,agents:{a:'Agent A',b:'Agent B',c:'Agent C'},month_start:'2026-10-06',month_end:'2026-11-06',today:'2026-10-09',timestamp:'2026-10-09 10:00:00'});
test('counts use creation and scheduled dates, not modification; unassigned excluded from podium', () => {
 const data = snapshot([row,{...row,name:'L2',lead_owner:'b',creation:'2026-09-01 10:00:00',custom_appointment_status:'Visited Booked'}, {...row,name:'L3',lead_owner:null}, {...row,name:'L4',custom_appointment_status:'Cancelled'}]);
 const agents = leaderboard(data);
 assert.deepEqual(agents.find(a=>a.id==='a').today,{leads:2,booked:1,walkins:0,visitedBooked:0,visitStatus:0});
 assert.deepEqual(agents.find(a=>a.id==='b').today,{leads:0,booked:1,walkins:1,visitedBooked:1,visitStatus:0});
 assert.equal(rank(agents,'today')[0].id,'b');
 assert.equal(rank(agents,'today').length,2);
});
test('initial load, repeated snapshots, unrelated edits and day rollover are silent', () => {
 const data=snapshot([row]);
 assert.deepEqual(changes(null,data),[]);
 assert.deepEqual(changes(data,data),[]);
 assert.deepEqual(changes(data,snapshot([{...row,modified:'2026-10-09 11:00:00'}])),[]);
 assert.deepEqual(changes(data,{...data,today:'2026-10-10'}),[]);
});
test('new leads, reschedules and visited transitions announce once', () => {
 const before=snapshot([row]);
 const next=snapshot([{...row,custom_appointment_status:'Visited Booked',modified:'2026-10-09 10:01:00'}, {...row,name:'L2',creation:'2026-10-09 10:01:00',modified:'2026-10-09 10:01:00',custom_appointment_date_and_time:null}]);
 assert.deepEqual(changes(before,next).map(e=>e.type),['walkin','lead']);
 assert.deepEqual(changes(next,next),[]);
 assert.equal(changes(before,snapshot([{...row,custom_appointment_date_and_time:'2026-10-10 14:00:00'}]))[0].type,'booked');
});

test('daily podium excludes agents with only earlier monthly activity', () => {
 const agents = leaderboard(snapshot([{...row,creation:'2026-10-07 09:00:00',custom_appointment_date_and_time:'2026-10-07 14:00:00'}]));
 assert.equal(rank(agents,'today').length,0);
 assert.equal(rank(agents,'month').length,1);
});

test('visited booked is a subset of visits and uses appointment day and month', () => {
 const data = snapshot([
  {...row,name:'booked',custom_appointment_status:'Visited Booked'},
  {...row,name:'not-booked',custom_appointment_status:'Visited Not Booked'},
  {...row,name:'pending',custom_appointment_status:'Visited'},
  {...row,name:'earlier',custom_appointment_status:'Visited Booked',custom_appointment_date_and_time:'2026-10-07 10:00:00'},
  {...row,name:'undated',custom_appointment_status:'Visited Booked',custom_appointment_date_and_time:null},
 ]);
 const agent = leaderboard(data)[0];
 assert.equal(agent.today.walkins,3);
 assert.equal(agent.today.visitedBooked,1);
 assert.equal(agent.month.walkins,4);
 assert.equal(agent.month.visitedBooked,2);
 const updated = leaderboard(snapshot([{...row,custom_appointment_status:'Visited Not Booked'}]))[0];
 assert.equal(updated.today.visitedBooked,0);
 assert.equal(updated.today.walkins,1);
});

test('weekly ranking spans month boundaries and excludes next week', () => {
 const data = {...snapshot([]),today:'2026-11-01',week_start:'2026-10-26',week_end:'2026-11-02'};
 data.rows = ['2026-10-25','2026-10-26','2026-11-01','2026-11-02'].map((day,i)=>({...row,name:`week-${i}`,custom_appointment_status:'Visited Booked',custom_appointment_date_and_time:day+' 10:00:00'}));
 const agent = leaderboard(data)[0];
 assert.equal(agent.week.walkins,2);
 assert.equal(agent.today.walkins,1);
 assert.equal(agent.month.walkins,4);
});
test('visited booked breaks ranking ties; roster retains zero-activity owners', () => {
 const agents = leaderboard(snapshot([{...row,lead_owner:'a',custom_appointment_status:'Visited'}, {...row,name:'b',lead_owner:'b',custom_appointment_status:'Visited Booked'}, {...row,name:'c',lead_owner:'c',creation:'2026-09-01',custom_appointment_date_and_time:null}]));
 assert.equal(rank(agents,'today')[0].id,'b');
 assert.equal(sortedAgents(agents,'today').length,3);
 assert.equal(rank(agents,'today').length,2);
});
test('waiting uses confirmed zero calls, site timestamp, threshold and current day', () => {
 const waiting = {...row, custom_appointment_date_and_time:null,custom_appointment_status:'',custom_call_count:0,custom_last_call_time:null,creation:'2026-10-09 09:50:00'};
 const data = snapshot([waiting,{...waiting,name:'called',custom_call_count:1}, {...waiting,name:'last-call',custom_last_call_time:'2026-10-09 09:55:00'}, {...waiting,name:'unknown',custom_call_count:null}, {...waiting,name:'yesterday',creation:'2026-10-08 09:00:00'}, {...waiting,name:'recent',creation:'2026-10-09 09:51:00'}, {...waiting,name:'converted',status:'Converted'}]);
 assert.deepEqual(waitingLeads(data).map(r=>r.name),['L1']);
 assert.equal(waitingLeads(data)[0].minutes,10);
 assert.equal(waitingLeads(data,60000).length,2);
 assert.equal(waitingLeads(snapshot([row])).length,0);
});
test('highlights require actual thresholds', () => {
 const agent = {id:'a',name:'Agent A',today:{walkins:5,visitedBooked:3,booked:5,leads:2},month:{walkins:50}};
 assert.equal(highlights([agent]).length,4);
 assert.match(highlights([agent])[3],/60%/);
 assert.equal(highlights([]).length,1);
});


test('monthly cycle includes the 6th through the next 5th for all metrics', () => {
 const data = snapshot(['2026-10-05','2026-10-06','2026-10-31','2026-11-01','2026-11-05','2026-11-06'].map((day,i) => ({...row,name:`month-${i}`,creation:day+' 23:59:59',custom_appointment_date_and_time:day+' 23:59:59',custom_appointment_status:'Visited Booked'})));
 assert.deepEqual(leaderboard(data)[0].month,{leads:4,booked:4,walkins:4,visitedBooked:4,visitStatus:0});
});
test('disabled owners never rank or announce but their activity remains in totals', () => {
 const before = snapshot([row]);
 const data = {...snapshot([{...row,custom_appointment_status:'Visited Booked',modified:'2026-10-09 10:01:00'}]),agents:{}};
 const agents = leaderboard(data);
 for (const period of ['today','month','week']) assert.deepEqual(sortedAgents(agents,period),[]);
 assert.equal(agents[0].today.walkins,1);
 assert.equal(highlights(agents).length,1);
 assert.deepEqual(changes(before,data),[]);
});

 test('activity carries the exact Lead Visit Status independently of appointment status', () => {
 const before = snapshot([row]);
 const next = snapshot([{...row, custom_visit_status:'Follow up required', custom_appointment_date_and_time:'2026-10-10 14:00:00'}]);
 assert.equal(changes(before,next)[0].visitStatus,'Follow up required');
 assert.equal(changes(before,snapshot([{...row,custom_appointment_date_and_time:'2026-10-10 14:00:00'}]))[0].visitStatus,'');
 });

test('raw visit status breakdowns use scheduled dates, falling back to creation for unscheduled leads', () => {
 const data = {...snapshot([]), week_start:'2026-10-05', week_end:'2026-10-12'};
 data.rows = [
  {...row,custom_visit_status:'Visited',creation:'2026-09-01'},
  {...row,name:'pending',custom_visit_status:'Pending',custom_appointment_date_and_time:null},
  {...row,name:'older',custom_visit_status:'Visited',custom_appointment_date_and_time:'2026-10-08 10:00:00'},
  {...row,name:'unset',custom_appointment_date_and_time:null},
 ];
 const agent=leaderboard(data)[0];
 assert.deepEqual(agent.visitStatuses.today, {Visited:1,Pending:1,'Not set':1});
 assert.deepEqual(agent.visitStatuses.month, {Visited:2,Pending:1,'Not set':1});
 assert.deepEqual(agent.visitStatuses.week, {Visited:2,Pending:1,'Not set':1});
});

test('Visit Status tile counts explicit visits and refreshes even when appointment status stays Booked', () => {
 const before=snapshot([{...row,custom_appointment_status:'Booked',custom_visit_status:''}]);
 const next=snapshot([{...row,custom_appointment_status:'Booked',custom_visit_status:'Visited'}]);
 assert.equal(leaderboard(before)[0].today.visitStatus,0);
 assert.equal(leaderboard(next)[0].today.visitStatus,1);
 assert.equal(leaderboard(next)[0].today.walkins,1);
 assert.equal(changes(before,next)[0].type,'walkin');
 assert.equal(leaderboard(snapshot([{...row,custom_visit_status:'Not Visited'}]))[0].today.visitStatus,0);
});
