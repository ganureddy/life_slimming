const WebSocket = require(process.cwd() + '/node_modules/ws');
const fs = require('node:fs'), assert = require('node:assert/strict');
(async () => {
  const target = await (await fetch('http://127.0.0.1:9222/json/new?about:blank', { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(resolve => ws.on('open', resolve));
  let id = 0, enabled = true, callStatus = 'CL000', widgetLoads = 0;
  const jobs = new Map(), errors = [], calls = [];
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    jobs.set(++id, message => message.error ? reject(message.error) : resolve(message.result));
    ws.send(JSON.stringify({ id, method, params }));
  });
  const bridge = fs.readFileSync('../life_slimming/public/js/convox_cc_bridge.js', 'utf8');
  const source = JSON.parse(fs.readFileSync('../life_slimming/portal_pages/cc-new-dash.json', 'utf8'));
  const notifications = fs.readFileSync('../life_slimming/public/js/cc_notifications.js', 'utf8');
  const toastCode = source.javascript.slice(source.javascript.indexOf('  function toast(msg, type)'), source.javascript.indexOf('  function showLoader'));
  const dashboard = source.javascript.slice(source.javascript.indexOf('  let callRequestPending'), source.javascript.indexOf('  function openLeadSummary'));
  ws.on('message', async raw => {
    const message = JSON.parse(raw);
    if (message.id) { jobs.get(message.id)?.(message); jobs.delete(message.id); }
    if (message.method === 'Page.javascriptDialogOpening') { errors.push('Blocking browser dialog'); await send('Page.handleJavaScriptDialog', {accept: true}); }
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.exception?.description);
    if (message.method !== 'Fetch.requestPaused') return;
    const { requestId, request } = message.params;
    const url = request.url;
    let payload, contentType = 'application/json';
    if (url.includes('/life_portal_module?')) {
      contentType = 'text/html';
      payload = `<!doctype html><div class="hdr-right"></div><button id="start" onclick="startCallTimer()">Start Call</button><button id="controls" onclick="stopCallTimer()">Phone controls</button><span data-convox-timer>No call requested</span><script>let currentFollowUpLead={id:'LEAD-TEST',callCount:0},callTimerInterval=null,callSeconds=0;window.lifePortalModule={module:'leads'};window.frappe={};${notifications};window.notices=[];${toastCode};const realToast=toast;toast=(m,t)=>{notices.push(m);realToast(m,t)};${dashboard}</script><script>${bridge}</script>`;
    } else if (url.startsWith('https://lifeslimming.deepijatel.in/')) {
      widgetLoads++; contentType = 'text/html'; payload = '<h1>Fixture ConVox phone — no real calls</h1>';
    } else {
      let result = {};
      if (url.includes('login_context')) result = { authenticated: true };
      else if (url.includes('portal.bootstrap')) result = { user: 'Administrator', full_name: 'Test Agent', roles: ['System Manager'], csrf_token: 'fixture-csrf' };
      else if (url.includes('convox.config')) result = { enabled, agent_id: enabled ? 'AGENT1' : '', sso_ready: true, click_to_call_ready: enabled, callbacks_ready: false, can_manage: true, user_settings_url: '/app/user/Administrator', setup_issues: enabled ? [] : ['Enable ConVox in System Settings.', 'Enter your ConVox agent ID in your User account.'], server_time: '2026-09-21 10:00:00' };
      else if (url.includes('convox.widget_session')) result = { url: 'https://lifeslimming.deepijatel.in/ConVoxCCS/?ExternalUserName=fixture-ciphertext', mode: 'sso' };
      else if (url.includes('convox.click_to_call')) {
        calls.push(JSON.parse(request.postData));
        result = { success: callStatus === 'CL000', status: callStatus, refno: 'LIFE12345678', message: callStatus === 'CL000' ? 'Call request accepted.' : 'Call outcome is unconfirmed. Check the phone.' };
      }
      payload = JSON.stringify({ message: result });
    }
    await send('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: contentType + '; charset=utf-8' }], body: Buffer.from(payload).toString('base64') });
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description);
    return result.result.value;
  };
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  async function waitFor(expression) {
    for (let i = 0; i < 80; i++) { if (await evaluate(expression)) return; await sleep(100); }
    throw new Error('Timed out: ' + expression);
  }
  const frame = `document.querySelector('.portal-source-page iframe').contentWindow`;
  await send('Page.enable'); await send('Runtime.enable');
  await send('Fetch.enable', { patterns: [{ urlPattern: 'http://127.0.0.1:5173/api/*' }, { urlPattern: '*/life_portal_module?*' }, { urlPattern: 'https://lifeslimming.deepijatel.in/*' }] });
  for (const width of [1440, 390]) {
    enabled = true; callStatus = 'CL000';
    await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
    await send('Page.navigate', { url: 'http://127.0.0.1:5173/life_portal/leads' });
    await waitFor(`!!document.querySelector('.convox-launch') && !!document.querySelector('.portal-source-page iframe')?.contentDocument?.querySelector('#start')`);
    await sleep(200);
    const before = calls.length;
    await evaluate(`window.postMessage({type:'life-convox-call',lead_id:'FORGED',request_id:'a'.repeat(32)},location.origin)`);
    await sleep(100); assert.equal(calls.length, before);
    await evaluate(`${frame}.document.querySelector('#start').click();${frame}.document.querySelector('#start').click()`);
    await waitFor(`${frame}.document.querySelector('[data-convox-timer]').textContent.startsWith('Requested')`);
    assert.equal(calls.length, before + 1);
    assert.equal(calls.at(-1).lead_id, 'LEAD-TEST');
    assert.equal(await evaluate(`document.querySelector('.convox-widget').getAttribute('allow')`), 'microphone https://lifeslimming.deepijatel.in');
    assert.ok(await evaluate(`document.querySelector('.convox-widget').src.includes('ExternalUserName=fixture-ciphertext')`));
    const rect = await evaluate(`({left:document.querySelector('.convox-panel').getBoundingClientRect().left,right:document.querySelector('.convox-panel').getBoundingClientRect().right})`);
    assert.ok(rect.left >= 0 && rect.right <= width);
    const count = widgetLoads;
    await evaluate(`document.querySelector('[aria-label="Minimize ConVox phone"]').click();${frame}.document.querySelector('#controls').click()`);
    await waitFor(`document.querySelector('.convox-panel').style.display !== 'none'`);
    assert.equal(widgetLoads, count);
    callStatus = 'UNKNOWN';
    await evaluate(`${frame}.document.querySelector('#start').click()`);
    await waitFor(`${frame}.notices.at(-1).includes('unconfirmed')`);
    const uncertain = calls.at(-1).request_id;
    await evaluate(`${frame}.lifeConvoxSelectLead('LEAD-OTHER');${frame}.lifeConvoxSelectLead('LEAD-TEST');${frame}.document.querySelector('#start').click()`);
    await sleep(250);
    assert.equal(calls.at(-1).request_id, uncertain);
    const shot = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(require('node:path').join(require('node:os').tmpdir(), `cc-notifications-${width}.png`), Buffer.from(shot.data, 'base64'));
    console.log('Start Call, encrypted widget URL, duplicate clicks, retry ID, controls, layout passed at width', width);
  }
  await evaluate(`document.getElementById('life-toast-host')?.remove();${frame}.alert('Toast timing fixture');`);
  await waitFor(`document.querySelector('#life-toast-host')?.textContent.includes('Toast timing fixture')`);
  await sleep(9500);
  assert.ok(await evaluate(`document.querySelector('#life-toast-host').textContent.includes('Toast timing fixture')`));
  await sleep(1000);
  assert.equal(await evaluate(`document.querySelector('#life-toast-host').textContent.includes('Toast timing fixture')`), false);
  await evaluate(`${frame}.frappe.msgprint({message:'Validation fixture: <b>Select a branch</b>',indicator:'red'});`);
  assert.ok(await evaluate(`document.querySelector('#life-toast-host').textContent.includes('Validation fixture: Select a branch')`));
  assert.equal(await evaluate(`document.querySelector('#life-toast-host b')`), null);
  await evaluate(`document.querySelector('#life-toast-host .life-toast').dispatchEvent(new MouseEvent('mouseenter'));`);
  await sleep(10500);
  assert.ok(await evaluate(`document.querySelector('#life-toast-host').textContent.includes('Validation fixture')`));
  await evaluate(`document.querySelector('#life-toast-host [aria-label="Dismiss notification"]').click()`);
  assert.equal(await evaluate(`document.querySelector('#life-toast-host').children.length`), 0);
  console.log('Real iframe alert/msgprint -> parent toast; minimum 10 seconds; hover pause; plain text; dismissal passed');
  enabled = false;
  await send('Page.navigate', { url: 'http://127.0.0.1:5173/life_portal/leads' });
  await waitFor(`!!document.querySelector('.convox-launch') && !!document.querySelector('.portal-source-page iframe')?.contentDocument?.querySelector('#start')`);
  const before = calls.length;
  await evaluate(`${frame}.document.querySelector('#start').click()`);
  await waitFor(`${frame}.notices.at(-1)?.includes('incomplete')`);
  assert.equal(calls.length, before);
  assert.equal(await evaluate(`!!document.querySelector('.convox-widget')`), false);
  assert.equal(await evaluate(`document.querySelector('.convox-setup li').textContent`), 'Enable ConVox in System Settings.');
  assert.equal(await evaluate(`${frame}.document.querySelector('[data-convox-timer]').textContent`), 'No call requested');
  assert.deepEqual(errors, []);
  console.log('Disabled setup, no false timer and zero runtime errors passed. No real calls placed.');
  await send('Page.close'); ws.close();
})().catch(error => { console.error(error); process.exit(1); });
