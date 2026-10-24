// ERP requests, including writes and uploads, are intercepted fixture responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const WebSocket = require('../node_modules/ws');
(async () => {
  const endpoint = process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9230';
  const base = process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5178';
  const target = await (await fetch(endpoint + '/json/new?about:blank', { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise(resolve => ws.on('open', resolve));
  let seq = 0, deny = false, heldBranches;
  const jobs = new Map(), calls = [], errors = [];
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    jobs.set(++seq, message => message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result));
    ws.send(JSON.stringify({ id: seq, method, params }));
  });
  const fulfill = (id, message, status = 200) => send('Fetch.fulfillRequest', {
    requestId: id, responseCode: status, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
    body: Buffer.from(JSON.stringify(status === 200 ? { message } : { exc_type: 'PermissionError', _server_messages: JSON.stringify([JSON.stringify({ message: 'Report access denied' })]) })).toString('base64'),
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
      if (method === 'life_slimming.api.server_scripts.life_discount_invoice_report.run') {
        if (args.action === 'branches') { heldBranches = requestId; return; }
        return fulfill(requestId, { success: true, data: [{ sales_invoice: 'INV-' + (args.page || 1), invoice_date: '2026-10-15', branch: 'Clinic A', client_name: 'Fixture Client', masked_mobile: '987****210', mobile_number: '9876543210', referring_name: 'Dr Priya', original_bill_total: 2100, grand_total: 2000, paid_amount: 1500, discount_used: 100, discount_percentage: 5, approved_by: 'L2: Manager', approval_breakup: 'L1 2%; L2 3%', approval_status: 'Approved', outstanding_amount: 500, payment_entries: 'PAY-1', last_payment_date: '2026-10-15', latest_approval_at: '2026-10-15 10:00' }], summary: { invoice_count: 21, total_original_bill: 44100, total_grand_total: 42000, total_paid: 31500, total_discount: 2100, total_outstanding: 10500 }, pagination: { page: args.page || 1, total_pages: 2, total_rows: 21 } }, deny ? 403 : 200);
      }
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
  try {
    await send('Page.enable'); await send('Runtime.enable'); await send('DOM.enable');
    await send('Fetch.enable', { patterns: [{ urlPattern: '*/api/method/*' }] });
    for (const width of [1440, 390]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: width < 500 });
      await send('Page.navigate', { url: base + '/life_portal/discountaudit' });
      await wait("document.querySelector('#ldr-body')?.textContent.includes('Fixture Client')");
      // Independent report data must not wait for the branch list.
      await wait('true'); assert(heldBranches, 'branch request is still pending');
      assert.equal(await evaluate('document.querySelectorAll("iframe").length'), 0);
      assert(await evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'no overflow at ' + width);
      assert.equal(await evaluate("document.querySelector('#ldr-count').textContent"), '21');
      assert((await evaluate("document.querySelector('#ldr-grand').textContent")).includes('42,000'));
      await fulfill(heldBranches, { success: true, branches: ['Clinic A'] }); heldBranches = null;
      await wait("document.querySelectorAll('#ldr-branch option').length===2");
      await input('#ldr-branch','Clinic A'); await input('#ldr-status','Approved'); await input('#ldr-level','L2'); await input('#ldr-search','INV');
      await click('#ldr-run'); await wait("!document.querySelector('#ldr-run').disabled");
      const report = calls.filter(call=>call.args.action==='report').at(-1).args;
      assert.equal(report.branch,'Clinic A');assert.equal(report.approval_status,'Approved');assert.equal(report.approval_level,'L2');assert.equal(report.search,'INV');
      await click('#ldr-next');await wait("document.querySelector('#ldr-body').textContent.includes('INV-2')");
      await click('#ldr-body .ldr-view-btn');await wait("document.querySelector('#ldr-modal-backdrop')");
      const details = await evaluate("document.querySelector('#ldr-modal-body').textContent");
      for (const text of ['Fixture Client','Dr Priya','Approval breakup:','L1 2%; L2 3%','PAY-1']) assert(details.includes(text),text);
      assert.equal(await evaluate('document.body.style.overflow'),'hidden');
      assert.equal(await evaluate('document.activeElement.id'),'ldr-modal-close');
      await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape'});
      await wait("!document.querySelector('#ldr-modal-backdrop')");assert.equal(await evaluate('document.body.style.overflow'),'');
      await click('#ldr-today');await wait("!document.querySelector('#ldr-run').disabled");
      assert.equal(await evaluate("document.querySelector('#ldr-from').value"),await evaluate("document.querySelector('#ldr-to').value"));
      await click('#ldr-reset');await wait("!document.querySelector('#ldr-run').disabled");
      assert.equal(await evaluate("document.querySelector('#ldr-branch').value"),'');
      // Capture the actual Excel Blob rather than writing a browser download.
      await evaluate("window.__exportBlobs=[];URL.createObjectURL=blob=>{window.__exportBlobs.push(blob);return 'blob:fixture'};HTMLAnchorElement.prototype.click=function(){};");
      await click('#ldr-export');await wait('window.__exportBlobs.length===1');
      const xml = await evaluate('window.__exportBlobs[0].text()');
      assert(xml.includes('Fixture Client'));assert(xml.includes('ss:Type="Number">2100'));
      assert(calls.some(call=>call.args.export===1 && call.args.page_length===5000));
      fs.writeFileSync('/tmp/discount-vue-' + width + '.png', Buffer.from((await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
      deny = true;await click('#ldr-run');await wait("document.querySelector('.ldr-request-error')?.textContent.includes('Report access denied')");
      deny=false;await click('.ldr-request-error button');await wait("document.querySelector('#ldr-body').textContent.includes('Fixture Client')");
    }
    assert.equal(errors.length,0,errors.join('\n'));
    console.log('Discount Audit Vue: desktop/mobile, report before branches, totals, filters, paging, details/Escape, business dates, Excel export and permission recovery passed.');
  } finally { await send('Page.close').catch(() => {}); ws.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
