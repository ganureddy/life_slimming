// ERP requests, including writes and uploads, are intercepted fixture responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const WebSocket = require('../node_modules/ws');
(async () => {
  const endpoint = process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9230';
  const base = process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5178';
  const target = await (await fetch(endpoint + '/json/new?about:blank', { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise(resolve => ws.on('open', resolve));
  let seq = 0, duplicate = false, deny = false, heldSearch;
  const jobs = new Map(), calls = [], errors = [];
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    jobs.set(++seq, message => message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result));
    ws.send(JSON.stringify({ id: seq, method, params }));
  });
  const fulfill = (id, message, status = 200) => send('Fetch.fulfillRequest', {
    requestId: id, responseCode: status, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
    body: Buffer.from(JSON.stringify(status === 200 ? { message } : { exc_type: 'PermissionError', _server_messages: JSON.stringify([JSON.stringify({ message: 'Registration access denied' })]) })).toString('base64'),
  });
  ws.on('message', async raw => {
    const event = JSON.parse(raw);
    if (event.id) { jobs.get(event.id)?.(event); jobs.delete(event.id); return; }
    if (event.method === 'Runtime.exceptionThrown') errors.push(event.params.exceptionDetails.exception?.description || event.params.exceptionDetails.text);
    if (event.method !== 'Fetch.requestPaused') return;
    const { requestId, request } = event.params;
    try {
      const method = new URL(request.url).pathname.split('/api/method/')[1];
      const args = method === 'upload_file' ? {} : JSON.parse(request.postData || '{}'); calls.push({ method, args });
      if (method === 'life_slimming.api.portal.bootstrap') return fulfill(requestId, { user: 'manager@example.test', full_name: 'Registration Manager', roles: ['System Manager'], portal_role: 'IT', csrf_token: 'fixture', session_id: target.id });
      if (method === 'life_slimming.api.convox.config') return fulfill(requestId, { enabled: false });
      if (method === 'frappe.client.get_list') {
        if (args.doctype === 'Patient') return fulfill(requestId, [{ name: 'PAT-OLD', patient_name: 'Existing Client', custom_final_decision: 'Booked', custom_health_flag: 'Green Flag' }], deny ? 403 : 200);
        if (args.filters?.[0]?.[2] === '%Slow%') { heldSearch = requestId; return; }
        if (args.doctype === 'Branch') return fulfill(requestId, [{ name: 'Clinic A' }]);
        if (args.doctype === 'Healthcare Practitioner') return fulfill(requestId, [{ name: 'PRAC-001', practitioner_name: 'Dr Priya' }]);
      }
      if (method === 'frappe.client.get_value') return fulfill(requestId, duplicate ? { patient_name: 'Already Registered' } : {});
      if (method === 'frappe.client.insert') return fulfill(requestId, { ...args.doc, name: 'PAT-NEW' });
      if (method === 'upload_file') return fulfill(requestId, { file_url: '/private/files/pd-fixture.pdf' });
      return fulfill(requestId, {});
    } catch (error) { errors.push(error.message); }
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    return result.result.value;
  };
  const wait = async expression => {
    for (let i = 0; i < 120; i++) { if (await evaluate(expression)) return; await new Promise(resolve => setTimeout(resolve, 50)); }
    throw new Error('Timed out: ' + expression + '\n' + JSON.stringify({errors,calls,body:await evaluate("document.body.innerText.slice(0,3000)")}));
  };
  const click = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  const input = (selector, value) => evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  const pick = async (key, query) => { await input('#' + key, query); await wait(`document.querySelector('#dd-${key} .it')`); await evaluate(`document.querySelector('#dd-${key} .it').dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true}))`); };
  try {
    await send('Page.enable'); await send('Runtime.enable'); await send('DOM.enable');
    await send('Fetch.enable', { patterns: [{ urlPattern: '*/api/method/*' }] });
    for (const width of [1440, 390]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: width < 500 });
      await send('Page.navigate', { url: base + '/life_portal/clireg' });
      await wait("document.querySelector('#regRows')?.textContent.includes('Existing Client')");
      assert.equal(await evaluate('document.querySelectorAll("iframe").length'), 0);
      assert(await evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'no page overflow at ' + width);
      assert.equal(await evaluate('document.querySelectorAll("#riskTbl tbody tr").length'), 5);
      await click('.btn-g'); await wait("document.querySelector('#e-fName')?.textContent.includes('required')");
      assert.equal(calls.filter(call => call.method === 'frappe.client.insert').length, width === 1440 ? 0 : 1);
      await input('#fName', 'priya kumar'); await input('#fGender', 'Female'); await input('#fDob', '1990-03-12');
      await input('#fPhone', '+919876543210'); await input('#fArea', 'Miyapur'); await input('#fWFor', 'Joined for Treatment');
      // Superseded link searches cannot overwrite the chosen result.
      await input('#fBranch', 'Slow'); await wait('true'); await new Promise(resolve => setTimeout(resolve, 240));
      await pick('fBranch', 'Clinic'); await pick('fEmp', 'Priya');
      if (heldSearch) { await fulfill(heldSearch, [{ name: 'Wrong Branch' }]).catch(() => {}); heldSearch = null; }
      await click('#segBook button'); await click('#segRel button:first-child');
      await input('#fRelName', 'Relative Client'); await pick('fRelBr', 'Clinic');
      await click('#riskTbl tbody tr:last-child');
      await input('#fPDNo', 'PD-9');
      assert(await evaluate("document.querySelector('#pvCard').textContent.includes('High Risk')"));
      assert(await evaluate("document.querySelector('#fAge').value.includes('years')"));
      assert.equal(await evaluate("document.querySelector('#fBranch').value"), 'Clinic A');
      fs.writeFileSync('/tmp/registration-vue-' + width + '.png', Buffer.from((await send('Page.captureScreenshot', {format:'png',captureBeyondViewport:false})).data,'base64'));
      duplicate = true; await click('.btn-g'); await wait("document.querySelector('#e-fPhone').textContent.includes('Already Registered')");
      const before = calls.filter(call => call.method === 'frappe.client.insert').length;
      duplicate = false;
      fs.writeFileSync('/tmp/registration-pd-fixture.pdf', '%PDF-1.4\nfixture');
      const document = await send('DOM.getDocument'); const node = await send('DOM.querySelector', { nodeId: document.root.nodeId, selector: '#fPD' });
      await send('DOM.setFileInputFiles', { nodeId: node.nodeId, files: ['/tmp/registration-pd-fixture.pdf'] });
      await wait("document.querySelector('#pdLbl').textContent.includes('registration-pd-fixture.pdf')");
      await click('.btn-g'); await click('.btn-g');
      await wait("location.pathname==='/life_portal/billing' && new URLSearchParams(location.search).get('mobile')==='9876543210'");
      const inserted = calls.filter(call => call.method === 'frappe.client.insert');
      assert.equal(inserted.length, before + 1, 'duplicate clicks must not insert twice');
      const patient = inserted.at(-1).args.doc;
      assert.equal(patient.first_name, 'Priya Kumar'); assert.equal(patient.custom_health_flag, 'Red Flag');
      assert.equal(patient.custom_employee_id, 'PRAC-001'); assert.equal(patient.custom_branch, 'Clinic A');
      assert.equal(patient.custom_pd_form[0].pd_form, '/private/files/pd-fixture.pdf');
      assert(patient.custom_remarks.includes('Relative in LIFE: Relative Client (Clinic A)'));
    }
    deny = true;
    await send('Page.navigate', { url: base + '/life_portal/clireg' });
    await wait("document.querySelector('#regRows')?.textContent.includes('Registration access denied')");
    deny = false; await click('#regRows button'); await wait("document.querySelector('#regRows').textContent.includes('Existing Client')");
    await input('#fName', 'Clear me'); await click('.btn-o'); await wait("document.querySelector('#fName').value===''");
    assert.equal(errors.length, 0, errors.join('\n'));
    console.log('Client Registration Vue: desktop/mobile, validation, links, duplicate blocking, upload, Patient insert, Billing redirect, reset and permission recovery passed.');
  } finally { await send('Page.close').catch(() => {}); ws.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
