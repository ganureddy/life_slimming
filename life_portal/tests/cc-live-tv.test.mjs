import { test } from 'node:test';
import assert from 'node:assert/strict';
import { leaderboard, rank, changes } from '../src/lib/cc-live-tv.js';
const row = {name:'L1',lead_name:'Client',lead_owner:'a',creation:'2026-10-09 09:00:00',modified:'2026-10-09 09:00:00',custom_appointment_date_and_time:'2026-10-09 14:00:00',custom_appointment_status:'Scheduled'};
const snapshot = rows => ({rows,agents:{a:'Agent A',b:'Agent B'},today:'2026-10-09',timestamp:'2026-10-09 10:00:00'});
test('counts use creation and scheduled dates, not modification; unassigned excluded from podium', () => {
 const data = snapshot([row,{...row,name:'L2',lead_owner:'b',creation:'2026-09-01 10:00:00',custom_appointment_status:'Visited Booked'}, {...row,name:'L3',lead_owner:null}, {...row,name:'L4',custom_appointment_status:'Cancelled'}]);
 const agents = leaderboard(data);
 assert.deepEqual(agents.find(a=>a.id==='a').today,{leads:2,booked:1,walkins:0,visitedBooked:0});
 assert.deepEqual(agents.find(a=>a.id==='b').today,{leads:0,booked:1,walkins:1,visitedBooked:1});
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
 const agents = leaderboard(snapshot([{...row,creation:'2026-10-02 09:00:00',custom_appointment_date_and_time:'2026-10-02 14:00:00'}]));
 assert.equal(rank(agents,'today').length,0);
 assert.equal(rank(agents,'month').length,1);
});

test('visited booked is a subset of visits and uses appointment day and month', () => {
 const data = snapshot([
  {...row,name:'booked',custom_appointment_status:'Visited Booked'},
  {...row,name:'not-booked',custom_appointment_status:'Visited Not Booked'},
  {...row,name:'pending',custom_appointment_status:'Visited'},
  {...row,name:'earlier',custom_appointment_status:'Visited Booked',custom_appointment_date_and_time:'2026-10-02 10:00:00'},
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
