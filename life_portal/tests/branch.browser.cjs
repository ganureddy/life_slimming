// All business data and credentials below are test fixtures, never production data.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(10000);
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  let connected = false, fail = false, expiry = false, calls = [];
  await page.route('**/api/method/life_slimming.api.portal.bootstrap', r => r.fulfill({ json: { message: { user: 'Administrator', full_name: 'Test Admin', roles: ['System Manager'], csrf_token: 'test-csrf', portal_role: '', access_config: null } } }));
  await page.route('**/api/method/life_slimming.api.remote_erp.*', async r => {
    const action = r.request().url().split('.').pop();
    const args = r.request().postDataJSON(); calls.push({ action, args });
    assert.equal(r.request().method(), 'POST');
    assert.equal(r.request().headers()['x-frappe-csrf-token'], 'test-csrf');
    let message;
    if (action === 'connect') {
      if (!args.otp) message = { verification: true, method: 'SMS' };
      else { connected = true; message = { connected: true }; assert.deepEqual(args, { otp: '123456' }); }
    } else if (action === 'disconnect') { connected = false; message = { connected: false }; }
    else if (!connected || expiry) message = { authentication_required: true };
    else if (fail) message = { error: 'ERP Portal could not be reached. Please retry.' };
    else message = { connected: true, user: 'viewer@example.test', branches: ['Demo Branch A', 'Demo Branch B'], ...(args.branch ? { data: {
      branch: args.branch, window: [args.from_date, args.to_date], target_window: [args.from_date, args.to_date],
      target: 100000, achieved: args.branch.endsWith('A') ? 75000 : 0, achieved_gross: 80000, paid_today_gross: 5000,
      pend_total: { due: 25000, inv: 3, cust: 2 }, days: [{ d: args.to_date, g: 80000 }],
      pm_window_detail: [{ m: 'Cash', v: 80000, gst: 4000, cut: 1000, final: 75000 }],
      ap_rows: [{ id: 'TEST-1', n: 'Fixture Client', st: 'Booked', dt: args.to_date, src: 'Referral' }],
      pend: [], att: [], emps: [], media: [], stock_zero_items: [],
      ap_cycle: { total: 1 }, leads: { t: 2 }, stock: { zero: 0 }, work: { open_: 1 },
    } } : {}) };
    await r.fulfill({ json: { message } });
  });
  await page.goto('http://127.0.0.1:5173/life_portal/bdash');
  await page.getByRole('heading', { name: 'Connect your ERP Portal' }).waitFor();
  await page.getByLabel('ERP email or username').fill('viewer@example.test');
  await page.getByLabel('ERP password').fill('fixture-password');
  await page.getByRole('button', { name: 'Connect ERP Portal', exact: true }).click();
  await page.getByLabel('Verification code').fill('123456');
  await page.getByRole('button', { name: 'Verify and connect' }).click();
  await page.getByRole('heading', { name: '75% achieved' }).waitFor();
  await page.screenshot({ path: '/tmp/life-branch-dashboard-desktop.png', fullPage: true });
  await page.getByRole('button', { name: 'Appointments', exact: true }).click();
  await page.getByText('Fixture Client', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'People', exact: true }).click();
  assert.equal(await page.getByText('No records returned for this selection.').count(), 2);
  await page.getByRole('button', { name: 'Dashboard', exact: true }).click();
  await page.getByLabel('Branch', { exact: true }).selectOption('Demo Branch B');
  await page.getByRole('heading', { name: '0% achieved' }).waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile layout must not overflow');
  await page.screenshot({ path: '/tmp/life-branch-dashboard-mobile.png', fullPage: true });
  fail = true;
  await page.getByRole('button', { name: 'Apply / refresh' }).click();
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByRole('heading', { name: '0% achieved' }).count(), 0, 'Stale figures hidden on failure');
  fail = false; expiry = true;
  await page.getByRole('button', { name: 'Retry', exact: true }).click();
  await page.getByRole('heading', { name: 'Connect your ERP Portal' }).waitFor();
  assert(calls.some(c => c.action === 'dashboard' && c.args.branch === 'Demo Branch B'));
  assert.deepEqual(errors, []);
  await browser.close();
  console.log('PASS: ERP connection/OTP, scoped requests, desktop/mobile, empty states, failure and expiry.');
})().catch(e => { console.error(e); process.exit(1); });
