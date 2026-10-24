// Requires Vite and an isolated Chrome with remote debugging already running.
// Each suite intercepts ERP calls; this runner never operates on live records.
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const suites = [
  'tasks-native', 'client-registration-native', 'discount-audit-native', 'employee-sale-native', 'appointment-scheduler-native', 'client-info-native',
  'unjoined-native', 'cluster-native', 'branch-target', 'price-list-native',
  'documents-native', 'sales-master-native', 'weight-loss-native',
  'cc-dashboard-parity', 'billing-native', 'billing-workflows', 'native-performance',
];
const env = {
  ...process.env,
  PORTAL_BROWSER_URL: process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9230',
  PORTAL_PREVIEW_URL: process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5178',
};
let failures = 0;
for (const suite of suites) {
  const result = spawnSync(process.execPath, [path.join(__dirname, suite + '.browser.cjs')], {
    cwd: path.join(__dirname, '../..'), env, stdio: 'inherit', timeout: 60000,
  });
  if (result.error || result.status !== 0) {
    failures++;
    console.error(suite + ' failed' + (result.error ? ': ' + result.error.message : '.'));
  }
}
console.log(`${suites.length - failures}/${suites.length} native browser suites passed.`);
process.exitCode = failures ? 1 : 0;
