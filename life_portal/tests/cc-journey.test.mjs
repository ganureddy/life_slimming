import test from 'node:test';
import assert from 'node:assert/strict';
import { matchesJourney, parseLeadCsv } from '../src/lib/cc-journey.js';
test('CSV preserves quoted commas, line breaks, leading zeroes and escaped quotes',()=>{
 const rows=parseLeadCsv('\uFEFFname,mobile,source,branch,notes\r\n"A, B",0123456789,Website,Ho CC,"Asked ""when""\nCall tomorrow"');
 assert.equal(rows[0].name,'A, B');assert.equal(rows[0].mobile,'0123456789');assert.equal(rows[0].notes,'Asked "when"\nCall tomorrow');
});
test('CSV rejects malformed files and incomplete headers',()=>{
 assert.throws(()=>parseLeadCsv('name,mobile\nA,123'),/source and branch/);
 assert.throws(()=>parseLeadCsv('name,mobile,source,branch\n"unclosed'),/unclosed/);
});
test('recovery flags distinguish business milestone from last failed call',()=>{
 const summary={milestone:'Appointment Booked',last_call_result:'No Response',unreachable_streak:3,next_action_due:'2026-11-11 10:00:00'};
 assert.equal(matchesJourney(summary,'Appointment Booked'),true);
 assert.equal(matchesJourney(summary,'Appointment Missed'),false);
 assert.equal(matchesJourney(summary,'failed'),true);
 assert.equal(matchesJourney(summary,'unreachable'),true);
 assert.equal(matchesJourney(summary,'overdue',Date.parse('2026-11-11T05:00:00Z')),true);
 assert.equal(matchesJourney(summary,'overdue',Date.parse('2026-11-11T04:00:00Z')),false);
 assert.equal(matchesJourney(null,'unreachable'),false);
});
