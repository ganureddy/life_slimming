// Compare original page CSS directly, so native styling cannot silently drift.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const postcss = require('../node_modules/postcss');
const root = path.join(__dirname, '..');
const pages = [
  ['task-management', 'src/styles/tasks.css'],
  ['appointment-shedular', 'src/styles/appointment-scheduler.css'],
  ['employee-sale-master-data', 'src/styles/employee-sale-master.css'],
  ['life-audit-report', 'src/styles/discount-audit.css'],
  ['new-client-registration', 'src/pages/ClientRegistrationPage.vue'],
  ['unjoined-data', 'src/styles/unjoined.css'],
  ['cluster-head-dashboard', 'src/styles/cluster-dashboard.css'],
  ['branch-home-target', 'src/pages/BranchTargetPage.vue'],
  ['price-list', 'src/pages/PriceListNativePage.vue'],
  ['v', 'src/pages/FormsDocumentsPage.vue'],
  ['sales-master-data', 'src/pages/SalesMasterDataPage.vue'],
  ['client-weight-loss-info', 'src/styles/weight-loss-parity.css'],
];
// These selectors style the surrounding Frappe website, which Vue replaces
// with PortalLayout. They must not hide or resize the portal's own navigation.
const websiteSelectors = new Set([
  '.navbar', '.web-footer',
  'html,body',
  '.container,.container-fluid,.hero-and-content .container,.page_content .container,.web-page-content .container',
  'main,.main-section,.hero-and-content,.page-content-wrapper,.page_content,.web-page-content',
  '.navbar,.navbar-light,.navbar-expand-lg,.website-navbar,header.navbar,.website-footer,.web-footer,footer,.page-footer,.page-header,.page-title,.page-breadcrumbs,.breadcrumbs',
  '.hero-and-content h1,.page_content > h1,.web-page-content > h1',
]);
const normalize = value => value.replace(/\s+/g, ' ').replace(/\s*([,>+~])\s*/g, '$1').trim();
const excluded = new Set([...websiteSelectors].map(normalize));
function rules(css) {
  const result = new Set();
  postcss.parse(css).walkRules(rule => {
    const selector = normalize(rule.selectors.map(selector => selector.startsWith(':deep(') && selector.endsWith(')') ? selector.slice(6,-1) : selector).join(','));
    if (excluded.has(selector)) return;
    const parents = [];
    for (let parent = rule.parent; parent; parent = parent.parent) if (parent.type === 'atrule') parents.unshift(parent.name + ':' + normalize(parent.params));
    const declarations = rule.nodes.filter(node => node.type === 'decl').map(node => `${node.prop}:${node.value.replace(/\s+/g, '')}${node.important ? '!important' : ''}`).join(';');
    result.add(`${parents.join('/')}|${selector}|${declarations}`);
  });
  return result;
}
for (const [source, native] of pages) test(source + ' preserves original page styling', () => {
  const original = JSON.parse(fs.readFileSync(path.join(root, '../life_slimming/portal_pages', source + '.json'), 'utf8'));
  const file = fs.readFileSync(path.join(root, native), 'utf8');
  const css = native.endsWith('.vue') ? [...file.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map(match => match[1]).join('\n') : file;
  const nativeRules = rules(css);
  let sourceCss = [original.css || '', ...[...original.html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map(match => match[1])].join('\n');
  if (source === 'new-client-registration') sourceCss = sourceCss.replace(':root{', '#cr-root{');
  const missing = [...rules(sourceCss)].filter(rule => !nativeRules.has(rule));
  assert.deepEqual(missing, [], 'source styling missing from ' + native);
});

test('every default native conversion is included in the source-style contract', () => {
  const router = fs.readFileSync(path.join(root, 'src/router/index.js'), 'utf8');
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'src/data/portalPages.json'), 'utf8'));
  const declaration = router.match(/const nativeModules = new Set\((\[[^;]+\])\);/);
  assert(declaration, 'default native modules must be explicitly listed');
  // Tasks owns its source and has a standalone dependency/workflow contract.
  const covered = new Set([...pages.map(([source]) => source), 'task-management']);
  for (const id of JSON.parse(declaration[1])) assert(covered.has(manifest[id]?.source), id + ' needs a source parity contract before it becomes a default native page');
});
