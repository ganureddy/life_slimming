// Integration test: imported page + compatibility bridge + portal, with fixture APIs.
const WebSocket = require('ws');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../life_slimming');
const parsed = JSON.parse(execFileSync(path.resolve(root, '../../../env/bin/python'), ['-c', `
import json
from bs4 import BeautifulSoup
from pathlib import Path
source=json.loads(Path(${JSON.stringify(path.join(root, 'portal_pages/hrms-dashboard---copy.json'))}).read_text())
soup=BeautifulSoup(source['html'],'html.parser')
scripts=[]
for script in soup.find_all('script'):
 scripts.append(str(script))
 script.decompose()
for tag in soup.find_all(['html','head','body']): tag.unwrap()
for tag in soup.find_all('title'): tag.decompose()
print(json.dumps({'html':str(soup),'scripts':'\\n'.join(scripts)}))
`], { maxBuffer: 5 * 1024 * 1024 }));
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const apiMethod = 'life_slimming.api.server_scripts.life_hrms_360_api.run';
const bootstrap = {
  ok: true, today: '2026-09-21', user: 'Preview HR', roles: ['System Manager'],
  branches: [{ name: 'Madhapur' }],
  employees: [{ name: 'EMP-TEST', employee_name: 'Preview Employee', branch: 'Madhapur',
    department: 'Operations', designation: 'Branch Manager', status: 'Active',
    date_of_joining: '2026-01-01', date_of_birth: '1995-01-01' }],
};
function pageHtml(module) {
  const config = { module, user: 'Administrator', csrf_token: 'fixture', methods: { life_hrms_360_api: apiMethod }, routes: {} };
  return '<!doctype html><html><head><style>' + read('public/css/portal_theme.css') + '</style></head><body>' +
    '<script>window.frappe={call:function(){return Promise.resolve({message:{}})}};window.lifePortalConfig={};window.lifePortalModule=' + JSON.stringify(config) + ';</script>' +
    '<script>' + read('public/js/portal_module_bridge.js') + '</script>' + parsed.html +
    '<style>' + read('public/css/portal_hrms.css') + '</style>' + parsed.scripts +
    '<script>' + read('public/js/portal_hrms.js') + '</script></body></html>';
}

(async () => {
  const endpoint = process.env.HRMS_BROWSER_URL || 'http://127.0.0.1:9223';
  const base = process.env.HRMS_PREVIEW_URL || 'http://127.0.0.1:5174';
  const target = await (await fetch(endpoint + '/json/new?about:blank', { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(resolve => ws.on('open', resolve));
  const jobs = new Map(), errors = [], requests = [];
  let id = 0, failBootstrap = false;
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    jobs.set(++id, m => m.error ? reject(m.error) : resolve(m.result));
    ws.send(JSON.stringify({ id, method, params }));
  });
  ws.on('message', async raw => {
    const m = JSON.parse(raw);
    if (m.id) { jobs.get(m.id)?.(m); jobs.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.exception?.description);
    if (m.method !== 'Fetch.requestPaused') return;
    const { requestId, request } = m.params;
    let payload, type = 'application/json', status = 200;
    if (request.url.includes('/life_portal_module?')) {
      type = 'text/html'; payload = pageHtml(new URL(request.url).searchParams.get('module'));
    } else {
      let message = {};
      if (request.url.includes('login_context')) message = { authenticated: true };
      else if (request.url.includes('portal.bootstrap')) message = { user: 'Administrator', full_name: 'Preview HR', roles: ['System Manager'] };
      else if (request.url.includes('convox.config')) message = { enabled: false };
      else if (request.url.includes('life_hrms_360_api')) {
        requests.push(request);
        assert.ok(request.url.includes(apiMethod), 'HRMS API must use local migrated endpoint');
        assert.equal(request.method, 'POST');
        message = bootstrap;
        if (failBootstrap) { status = 503; message = 'Unavailable'; }
      }
      payload = JSON.stringify({ message });
    }
    await send('Fetch.fulfillRequest', { requestId, responseCode: status, responseHeaders: [{ name: 'Content-Type', value: type + '; charset=utf-8' }], body: Buffer.from(payload).toString('base64') });
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description);
    return result.result.value;
  };
  const waitFor = async expression => {
    for (let i = 0; i < 120; i++) {
      if (await evaluate(expression)) return;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    console.log(await evaluate(`(() => {const f=document.querySelector('iframe')?.contentWindow;return {status:f?.document.querySelector('.portal-hrms-status')?.textContent,lock:f?.document.querySelector('#lockmsg')?.textContent,view:f?.V,boot:typeof f?.bootApp,body:f?.document.body.textContent.slice(-500)}})()`));
    console.log('HRMS requests', requests.map(r => r.url));
    throw new Error('Timed out: ' + expression + '\n' + errors.join('\n'));
  };
  const frame = `document.querySelector('iframe').contentWindow`;
  const doc = `${frame}.document`;
  try {
    await send('Page.enable'); await send('Runtime.enable');
    await send('Fetch.enable', { patterns: [{ urlPattern: base + '/api/*' }, { urlPattern: base + '/life_portal_module?*' }] });
    for (const width of [1440, 390]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
      for (const [module, view] of [['employees', 'dash'], ['attend', 'attend'], ['payroll', 'reports']]) {
        await send('Page.navigate', { url: base + '/life_portal/' + module });
        await waitFor(`!!document.querySelector('iframe') && !!${doc}.querySelector('.portal-hrms-status')?.hidden`);
        assert.equal(await evaluate(`${frame}.V`), view);
        assert.equal(await evaluate(`${frame}.getComputedStyle(${doc}.querySelector('.side')).display`), 'none');
        assert.ok(await evaluate(`document.documentElement.scrollWidth <= innerWidth`), 'Outer overflow');
        assert.ok(await evaluate(`${doc}.documentElement.scrollWidth <= ${frame}.innerWidth`), 'Inner overflow');
        assert.ok(await evaluate(`${doc}.querySelector('#wrap').textContent.length > 100`));
        if (module === 'payroll') assert.match(await evaluate(`${doc}.querySelector('#wrap').textContent`), /LIVE PAYROLL DATA/);
        if (module === 'employees') {
          await evaluate(`const input=${doc}.querySelector('#gq');input.value='Preview';input.dispatchEvent(new Event('input',{bubbles:true}))`);
          assert.match(await evaluate(`${doc}.querySelector('#sdrop').textContent`), /Preview Employee/);
          await evaluate(`${doc}.querySelector('#sdrop .it').click()`);
          assert.equal(await evaluate(`${frame}.V`), 'profile');
          assert.match(await evaluate(`${doc}.querySelector('#wrap').textContent`), /Preview Employee/);
          await evaluate(`${doc}.querySelector('.portal-hrms-tabs [data-view="emps"]').click()`);
          assert.equal(await evaluate(`${frame}.V`), 'emps');
          assert.match(await evaluate(`${doc}.querySelector('#wrap').textContent`), /Preview Employee/);
          await evaluate(`${doc}.querySelector('.portal-hrms-picker').open=true`);
          await evaluate(`const s=${doc}.querySelector('.portal-hrms-menu input');s.value='leave';s.dispatchEvent(new Event('input',{bubbles:true}))`);
          assert.ok(await evaluate(`${doc}.querySelectorAll('.portal-hrms-results button').length > 0`));
          await evaluate(`${doc}.querySelector('.portal-hrms-results button[data-view="leave"]').click()`);
          assert.equal(await evaluate(`${frame}.V`), 'leave');
          assert.equal(await evaluate(`${doc}.querySelector('.portal-hrms-picker').open`), false);
          await evaluate(`${frame}.go('dash')`);
        }
        await new Promise(resolve => setTimeout(resolve, 250));
        const shot = await send('Page.captureScreenshot', { format: 'png' });
        fs.writeFileSync(`/tmp/hrms-${module}-${width}.png`, Buffer.from(shot.data, 'base64'));
        console.log(module, width, 'passed');
      }
    }
    failBootstrap = true;
    await send('Page.navigate', { url: base + '/life_portal/employees' });
    await waitFor(`!!document.querySelector('iframe') && ${doc}.querySelector('.portal-hrms-status')?.getAttribute('role') === 'alert'`);
    assert.equal(await evaluate(`${doc}.querySelector('.portal-hrms-status button').textContent`), 'Retry');
    failBootstrap = false;
    await evaluate(`${doc}.querySelector('.portal-hrms-status button').click()`);
    await waitFor(`${doc}.querySelector('.portal-hrms-status')?.hidden`);
    assert.deepEqual(errors, []);
    assert.ok(requests.length >= 8);
    console.log('Bootstrap failure and retry passed');
  } finally { await send('Page.close'); ws.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
