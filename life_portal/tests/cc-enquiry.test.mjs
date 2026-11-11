import test from 'node:test';
import assert from 'node:assert/strict';
import { enquiryDate, enquiryLabel, mergeEnquiryRows, repeatEnquiryRows } from '../src/lib/cc-enquiry.js';
const repeat={name:'OLD-LEAD',creation:'2025-01-01 10:00:00',custom_posting_date:'2026-11-10',source:'WEBSITE CHAT',custom_cc_stage:'FOLLOW-UP'};
test('repeat enquiries use posting date and preserve ID, creation and follow-up',()=>{
  const before={...repeat};
  assert.equal(enquiryDate(repeat),'2026-11-10');
  assert.equal(enquiryLabel(repeat),'New Enquiry · continuing follow-up');
  assert.deepEqual(repeat,before);
});
test('creation cohort and repeat cohort deduplicate without losing old repeat lead',()=>{
  const fresh={name:'FRESH',creation:'2026-11-10 10:00:00',source:'Facebook'};
  assert.deepEqual(mergeEnquiryRows([fresh],[repeat,fresh],'2026-11-10','2026-11-10').map(row=>row.name),['FRESH','OLD-LEAD']);
});
test('old-source leads with V5 marker are included; unrelated posting edits are excluded',()=>{
  const migrated={...repeat,source:'Facebook',custom_remarks:'[NEW WEBSITE CHAT ENQUIRY 2026-11-10 10:00:00]'};
  const unrelated={...repeat,name:'OTHER',source:'Facebook'};
  assert.deepEqual(mergeEnquiryRows([],[migrated,unrelated],'2026-11-10','2026-11-10').map(row=>row.name),['OLD-LEAD']);
});
test('missing or older posting date falls back to original creation',()=>{
  assert.equal(enquiryDate({...repeat,custom_posting_date:''}),'2025-01-01');
  assert.equal(enquiryDate({...repeat,custom_posting_date:'2024-01-01'}),'2025-01-01');
});
test('repeat not counted again on original creation day; same-day repeats deduplicate',()=>{
  assert.deepEqual(mergeEnquiryRows([repeat],[],'2025-01-01','2025-01-01'),[]);
  const sameDay={...repeat,creation:'2026-11-10 08:00:00',custom_remarks:'[NEW WEBSITE CHAT ENQUIRY 2026-11-10 10:00:00]'};
  assert.equal(mergeEnquiryRows([sameDay],[sameDay],'2026-11-10','2026-11-10').length,1);
  assert.match(enquiryLabel(sameDay),/^New Enquiry/);
});

test('repeat card excludes fresh leads and dates outside the selected range',()=>{
  const fresh={name:'NEW',creation:'2026-11-10 09:00:00',custom_posting_date:'2026-11-10',source:'WEBSITE CHAT'};
  const older={...repeat,name:'OLDER',custom_posting_date:'2026-11-09'};
  const before={...repeat};
  assert.deepEqual(repeatEnquiryRows([repeat,repeat,fresh,older],'2026-11-10','2026-11-10').map(row=>row.name),['OLD-LEAD']);
  assert.deepEqual(repeat,before);
});
test('repeat card includes same-day V5 repeats without changing assignment or status',()=>{
  const sameDay={...repeat,name:'SAME-DAY',creation:'2026-11-10 08:00:00',lead_owner:'agent@example.test',custom_remarks:'[NEW WEBSITE CHAT ENQUIRY 2026-11-10 10:00:00]'};
  const selected=repeatEnquiryRows([sameDay],'2026-11-10','2026-11-10');
  assert.equal(selected.length,1);
  assert.equal(selected[0].lead_owner,'agent@example.test');
  assert.equal(selected[0].custom_cc_stage,'FOLLOW-UP');
});
