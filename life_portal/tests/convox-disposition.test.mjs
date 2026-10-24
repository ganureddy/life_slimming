import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { portalDisposition } from '../src/lib/convox-disposition.js';
const wf = JSON.parse(fs.readFileSync(new URL('../src/data/cc-reference.json', import.meta.url))).WF;
test('explicit vendor dispositions map to portal options, transport results do not', () => {
  assert.equal(portalDisposition({disposition:'NR'}, wf), 'No Response');
  assert.equal(portalDisposition({disposition:'CallDisconnected'}, wf), 'Call Disconnected');
  assert.equal(portalDisposition({disposition:'Not Interested'}, wf), 'Not Interested');
  assert.equal(portalDisposition({disposition:'CONGESTION',call_status:'ANSWERED'}, wf), '');
  assert.equal(portalDisposition({disposition:'NR',disposition_3:'Very Positive'}, wf), 'Very Positive');
});
