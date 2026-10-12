const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '../..');
const helper = fs.readFileSync(path.join(root, 'life_portal/src/lib/cc-dashboard-groups.js'), 'utf8');
const classify = vm.runInNewContext(helper.replace('export function', 'function') + '\nccDashboardGroup');

test('requested dashboard groups and existing spelling variants', () => {
  const groups = {
    followup: ['call back', 'get back', 'Callback: Scheduled'],
    norespnotreach: ['not responding', 'switch off', 'not reachable', 'No Response', 'Not Response'],
    invalid: ['not in service', 'invalid number', 'not enquired', 'wrong no', 'not interested', 'TNA', 'Wrong number'],
    nid: ['NID', 'Distance', 'non local', 'Non-Local', 'nonlocal'],
  };
  for (const [group, statuses] of Object.entries(groups)) for (const status of statuses) {
    assert.equal(classify({ custom_cc_sub_status: ` ${status.toUpperCase()} ` }), group, status);
    assert.equal(classify({ subStatus: status }), group, status);
    assert.equal(classify({ status, custom_cc_sub_status: 'Lead' }), group, status);
    assert.equal(classify({ portalStatus: status, status: 'INVALID', subStatus: '' }), group, status);
  }
});
test('broad stages and unrelated outcomes are not counted in the requested groups', () => {
  for (const status of ['FOLLOW-UP', 'INVALID', 'Very Positive', 'Price Negotiation', 'Job enquiry', 'Appointment Booked', 'Call Disconnected']) {
    assert.equal(classify({ custom_cc_sub_status: status }), '', status);
  }
  assert.equal(classify({ custom_cc_sub_status: 'Not Interested', status: 'Get Back' }), 'invalid');
});
test('live status and sub-status pairs resolve to one dashboard group', () => {
  for (const [status, substatus, group] of [
    ['Call Back', 'Callback: Scheduled', 'followup'],
    ['Get Back', 'Get Back', 'followup'],
    ['Not Response', 'No Response', 'norespnotreach'],
    ['Switch OFF', 'Switch OFF', 'norespnotreach'],
    ['Wrong number', 'Invalid Number', 'invalid'],
    ['Not interested', 'Not interested', 'invalid'],
    ['NID', 'Distance', 'nid'],
    ['NID', 'NID', 'nid'],
  ]) assert.equal(classify({ status, custom_cc_sub_status: substatus }), group);
  assert.equal(classify({ status: 'Get Back', custom_cc_sub_status: 'No Response' }), 'norespnotreach');
  assert.equal(classify({ status: 'Not Response', custom_cc_sub_status: 'Callback: Scheduled' }), 'followup');
});
test('legacy page uses the same classification for counts and drilldowns', () => {
  const page = JSON.parse(fs.readFileSync(path.join(root, 'life_slimming/portal_pages/cc-new-dashboard-bhuvan-oct2.json'), 'utf8'));
  new vm.Script(page.javascript);
  assert.ok(page.javascript.includes(helper.replace('export function', 'function').trim()));
  for (const group of ['followup', 'norespnotreach', 'invalid', 'nid']) {
    assert.ok(page.javascript.split(`ccDashboardGroup(l) === "${group}"`).length >= 3, group);
  }
});
test('unrelated sub-statuses cannot fall back into a requested dashboard group', () => {
  for (const substatus of ['Job enquiry', 'Franchise Lead', 'Junk/Wrong Call', 'Price Negotiation', 'Very Positive', 'Call & Confirm', 'Out Station', 'Call Disconnected', 'Other clinic', 'Joined Competition', 'Do Not Contact']) {
    assert.equal(classify({custom_cc_sub_status: substatus, status: 'Not Response'}), '', substatus);
    assert.equal(classify({subStatus: substatus, portalStatus: 'Not interested', status: 'INVALID'}), '', substatus);
  }
  assert.equal(classify({custom_cc_sub_status: '', status: 'Call Back'}), 'followup');
  assert.equal(classify({custom_cc_sub_status: 'Lead', status: 'Not Response'}), 'norespnotreach');
});
