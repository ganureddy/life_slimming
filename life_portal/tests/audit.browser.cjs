// Run with a headless Chrome debugging endpoint at AUDIT_BROWSER_URL.
const WebSocket = require('ws');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../life_slimming');
const source = JSON.parse(fs.readFileSync(path.join(root, 'portal_pages/audit.json'), 'utf8')).html;
const theme = fs.readFileSync(path.join(root, 'public/css/portal_theme.css'), 'utf8');
const styles = fs.readFileSync(path.join(root, 'public/css/portal_audit.css'), 'utf8');

function fixture(mode) {
  window.auditFixture = mode;
  window.frappe = {
    session: { user: mode.startsWith('branch') ? 'branch@example.test' : 'Administrator' },
    call({ method, args = {} }) {
      const scenario = window.auditFixture;
      let message = [];
      if (method === 'life_audit_branch_access') {
        if (args.action === 'report' && scenario === 'branch-error') return Promise.reject(new Error('Reports unavailable'));
        message = { branch: 'Test Branch', audits: [] };
      } else if (method === 'frappe.client.get_list') {
        if (args.doctype === 'Branch Audit' && scenario === 'report-error') return Promise.reject(new Error('Reports unavailable'));
        if (args.doctype === 'Has Role') message = scenario.startsWith('branch') ? [] : [{ role: 'System Manager' }];
        if (args.doctype === 'Branch Audit Section') {
          if (scenario === 'error') return Promise.reject(new Error('Audit service unavailable'));
          if (scenario === 'loaded') message = [{ name: 'SECTION-1', section_code: 'S1', display_code: '01', section_name: 'Branch standards', weight: 20, raw_max: 2, is_enabled: 1 }];
        }
        if (args.doctype === 'Branch Audit Item') message = [{ name: 'ITEM-1', question: 'Reception is clean and ready for clients', points: 2, idx: 1, custom_is_enabled: 1 }];
        if (args.doctype === 'Branch') message = [{ name: 'Test Branch' }];
      } else {
        return Promise.reject(new Error('Unexpected API call: ' + method));
      }
      return Promise.resolve({ message });
    }
  };
}

(async () => {
  const endpoint = process.env.AUDIT_BROWSER_URL || 'http://127.0.0.1:9223';
  const target = await (await fetch(endpoint + '/json/new?about:blank', { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(resolve => ws.on('open', resolve));
  let id = 0;
  const jobs = new Map(), errors = [];
  ws.on('message', raw => {
    const m = JSON.parse(raw);
    if (m.id) { jobs.get(m.id)?.(m); jobs.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.exception?.description);
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    jobs.set(++id, m => m.error ? reject(m.error) : resolve(m.result));
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description);
    return result.result.value;
  };
  const waitFor = async expression => {
    for (let i = 0; i < 100; i++) {
      if (await evaluate(expression)) return;
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    throw new Error('Timed out: ' + expression);
  };
  try {
    await send('Runtime.enable');
    await send('Page.enable');
    const { frameTree } = await send('Page.getFrameTree');
    for (const width of [1280, 390]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
      for (const mode of ['empty', 'error', 'loaded', 'branch', 'branch-error']) {
        const html = '<!doctype html><html><head><style>body{margin:0}' + theme + styles + '</style></head><body><script>(' + fixture.toString() + ')(' + JSON.stringify(mode) + ')</script>' + source + '</body></html>';
        await send('Page.setDocumentContent', { frameId: frameTree.frame.id, html });
        await waitFor(`document.querySelector('.lifeaudit-root')?.getAttribute('aria-busy') === 'false'`);
        assert.equal(await evaluate(`document.querySelectorAll('.la-view.on').length`), 1, mode);
        assert.ok(await evaluate(`document.documentElement.scrollWidth <= innerWidth`), mode + ' overflow');
        if (mode === 'error' || mode === 'branch-error') {
          assert.equal(await evaluate(`document.querySelector('[data-el="loadStatus"]').hidden`), false);
          assert.equal(await evaluate(`document.querySelector('[data-el="loadStatus"]').getAttribute('role')`), 'alert');
          await evaluate(`window.auditFixture = '${mode === 'error' ? 'loaded' : 'branch'}';document.querySelector('[data-act="retryBoot"]').click()`);
          await waitFor(`document.querySelector('.lifeaudit-root').getAttribute('aria-busy') === 'false'`);
          assert.equal(await evaluate(`document.querySelector('[data-el="loadStatus"]').hidden`), true);
        }
        if (mode === 'empty') {
          assert.match(await evaluate(`document.querySelector('.la-view.on').textContent`), /No audit checklist available/);
          assert.equal(await evaluate(`document.querySelector('[data-act="submitAudit"]').disabled`), true);
          const emptyShot = await send('Page.captureScreenshot', { format: 'png' });
          fs.writeFileSync(`/tmp/audit-checklist-empty-${width}.png`, Buffer.from(emptyShot.data, 'base64'));
          await evaluate(`document.querySelector('[data-act="tab"][data-v="master"]').click()`);
          await waitFor(`document.querySelector('[data-view="master"]').classList.contains('on')`);
          assert.ok(await evaluate(`document.querySelector('[data-el="mTable"]').textContent.length > 0`));
          await evaluate(`window.auditFixture = 'report-error';document.querySelector('[data-el="mfStatus"]').dispatchEvent(new Event('change', {bubbles:true}))`);
          await waitFor(`!!document.querySelector('[data-act="retryReports"]')`);
          assert.equal(await evaluate(`document.querySelector('[data-el="loadStatus"]').getAttribute('role')`), 'alert');
          await evaluate(`window.auditFixture = 'empty';document.querySelector('[data-act="retryReports"]').click()`);
          await waitFor(`document.querySelector('[data-el="loadStatus"]').hidden`);
          assert.equal(await evaluate(`document.querySelector('.la-view.on').dataset.view`), 'master');
        }
        if (mode === 'loaded') {
          assert.match(await evaluate(`document.querySelector('[data-el="conductSecs"]').textContent`), /Reception is clean/);
          assert.equal(await evaluate(`document.querySelector('[data-act="submitAudit"]').disabled`), false);
        }
        if (mode.startsWith('branch')) {
          assert.equal(await evaluate(`document.querySelector('.la-view.on').dataset.view`), 'master');
          assert.equal(await evaluate(`getComputedStyle(document.querySelector('.la-tabs')).display`), 'none');
        }
        const screenshot = await send('Page.captureScreenshot', { format: 'png' });
        fs.writeFileSync(`/tmp/audit-${mode}-${width}.png`, Buffer.from(screenshot.data, 'base64'));
        console.log(`${mode} ${width}px: passed`);
      }
    }
    assert.deepEqual(errors, []);
  } finally {
    await send('Page.close');
    ws.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
