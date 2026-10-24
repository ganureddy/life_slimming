// Local browser fixtures only; every ERP API is intercepted.
const assert = require('node:assert/strict');
const WebSocket = require('../node_modules/ws');
(async () => {
  const endpoint = process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9230';
  const base = process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5178';
  const target = await (await fetch(endpoint + '/json/new?about:blank', { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(resolve => ws.on('open', resolve));
  const jobs = new Map(), calls = [], errors = [];
  let sequence = 0, heldMetadata, closing = false;
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    jobs.set(++sequence, message => message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result));
    ws.send(JSON.stringify({ id: sequence, method, params }));
  });
  const fulfill = (requestId, body) => send('Fetch.fulfillRequest', { requestId, responseCode: 200,
    responseHeaders: [{ name: 'Content-Type', value: 'application/json' }], body: Buffer.from(JSON.stringify(body)).toString('base64') });
  ws.on('message', async raw => {
    const event = JSON.parse(raw);
    if (event.id) { jobs.get(event.id)?.(event); jobs.delete(event.id); return; }
    if (event.method === 'Runtime.exceptionThrown') errors.push(event.params.exceptionDetails.exception?.description || event.params.exceptionDetails.text);
    if (event.method !== 'Fetch.requestPaused') return;
    const { requestId, request } = event.params;
    try {
      const method = new URL(request.url).pathname.split('/api/method/')[1];
      const args = JSON.parse(request.postData || '{}'); calls.push({ method, args });
      let message = [];
      if (method === 'life_slimming.api.portal.bootstrap') message = { user: 'native-perf-fixture', session_id: 'native-perf-' + target.id, full_name: 'Fixture User', roles: ['System Manager'], portal_role: 'IT', csrf_token: 'fixture' };
      if (method === 'life_slimming.api.convox.config') message = { enabled: false };
      if (method === 'life_slimming.api.server_scripts.life_stores_360_live_api.run') message = { ok: true, items: [{ code: 'ITEM-1', name: 'Clinic Item', cat: 'Clinic', type: 'Stock', rl: 1 }],
        branches: [{ code: 'B1', name: 'Branch A' }], suppliers: [], clients: [], stock_requests: [], purchases: [],
        ho_stock: { 'ITEM-1': 5 }, branch_stock: {}, purchase_invoices: [], lifetime_purchases: [], dispatch: [], returns: [], adjust: [], consumption: [] };
      if (method === 'frappe.desk.form.load.getdoctype') { heldMetadata = requestId; return; }
      if (method === 'frappe.client.get_count') message = 1;
      if (method === 'frappe.client.get_list') {
        if (args.fields?.some(field => field.includes('count('))) message = [{ total: 1 }];
        else if (args.doctype === 'Branch') message = [{ name: 'Branch A' }];
        else if (args.doctype === 'Therapy Type') message = [{ name: 'Slimming Session', healthcare_service_unit: 'Slimming - LSACPL' }];
        else if (args.doctype === 'Patient Appointment') message = [{ name: 'APPT-1', patient: 'PAT-1', patient_name: 'Fixture Client', branch: 'Branch A', appointment_date: '2026-10-15', appointment_time: '10:00:00', status: 'Scheduled' }];
      }
      await fulfill(requestId, { message });
    } catch (error) { if (!closing) errors.push(error.stack); }
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    return result.result.value;
  };
  const wait = async expression => {
    for (let i = 0; i < 120; i++) { if (await evaluate(expression)) return; await new Promise(resolve => setTimeout(resolve, 50)); }
    throw new Error('Timeout: ' + expression + '\n' + await evaluate('document.body.innerText') + '\nRender error: ' + await evaluate('document.querySelector("details code")?.textContent') + '\nErrors: ' + JSON.stringify(errors) + '\nCalls: ' + JSON.stringify(calls));
  };
  const primaryCalls = doctype => calls.filter(call => call.method === 'frappe.client.get_list' && call.args.doctype === doctype && !call.args.fields?.some(field => field.includes('count(')));
  try {
    await send('Page.enable'); await send('Runtime.enable');
    await send('Fetch.enable', { patterns: [{ urlPattern: '*/api/method/*' }] });
    for (const width of [1440, 390]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
      await send('Page.navigate', { url: base + '/life_portal/native/stores360' });
      await wait("document.querySelector('.stores-native')?.textContent.includes('Clinic Item') || document.querySelector('.stores-page')?.textContent.includes('Clinic Item')");
      assert(calls.some(call => call.method === 'life_slimming.api.server_scripts.life_stores_360_live_api.run'));
      assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true);
      assert.equal(await evaluate('!!document.querySelector("iframe")'), false);
      calls.length = 0;
      await send('Page.navigate', { url: base + '/life_portal/native/service' });
      await wait("document.querySelector('.service-page')?.textContent.includes('Fixture Client')");
      assert(heldMetadata, 'primary report must render while metadata is pending');
      assert.equal(primaryCalls('Patient Appointment').length, 1);
      await fulfill(heldMetadata, { docs: [{ doctype: 'DocType', name: 'Therapy Session', fields: [] }] }); heldMetadata = null;
      const before = primaryCalls('Patient Appointment').length;
      await evaluate("(async () => { const input = document.querySelector('.service-filters input[placeholder]'); for (const value of ['Fi','Fix','Fixture']) { input.value=value; input.dispatchEvent(new Event('input',{bubbles:true})); await new Promise(r=>setTimeout(r,20)); } })()");
      await new Promise(resolve => setTimeout(resolve, 400));
      assert.equal(primaryCalls('Patient Appointment').length - before, 1, 'one request for a burst of typing');
      const sessionsBefore = primaryCalls('Therapy Session').length;
      await evaluate("Array.from(document.querySelectorAll('.service-header button')).find(button=>button.textContent.includes('Therapy Session Report')).click()");
      await wait("document.querySelector('.service-page')?.textContent.includes('Therapy Session Report') && !document.querySelector('.service-header button')?.disabled");
      await new Promise(resolve => setTimeout(resolve, 250));
      assert.equal(primaryCalls('Therapy Session').length - sessionsBefore, 1, 'one report fetch per tab change');
      assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true);
      console.log('Native loading checks passed for Stores 360 and Service at width ' + width);
    }
    assert.deepEqual(errors, []);
  } finally { closing = true; ws.close(); await fetch(endpoint + '/json/close/' + target.id); }
})().catch(error => { console.error(error); process.exitCode = 1; });
