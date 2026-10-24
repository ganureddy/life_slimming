const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = file => fs.readFileSync(path.join(__dirname, '../src', file), 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));

test('Unjoined starts records without waiting for the branch master list', async () => {
  const code = source('composables/useUnjoined.js');
  const start = code.indexOf('  async function initialize()');
  const end = code.indexOf('  function resetDraft(', start);
  let releaseBranches, releaseRecords, starts = 0;
  const context = { manager: {}, branches: {}, notice: {}, disposed: false,
    portalSession: { roles: ['System Manager'] },
    load: () => { starts++; return new Promise(resolve => { releaseRecords = resolve; }); },
    api: () => new Promise(resolve => { releaseBranches = resolve; }) };
  vm.createContext(context); vm.runInContext(code.slice(start, end), context);
  let completed = false;
  const pending = context.initialize().then(() => { completed = true; });
  assert.equal(starts, 1);
  releaseBranches([{ name: 'Branch A' }, { name: 'Testing Branch' }]);
  await tick();
  assert.equal(completed, false);
  assert.equal(context.branches.value.join(','), 'Branch A');
  releaseRecords(); await pending;
  assert.equal(completed, true);
});

test('documents prioritizes the visible tab and stops background warming on unmount', async () => {
  const code = source('pages/FormsDocumentsPage.vue');
  const start = code.indexOf('async function initializeTabs()');
  const end = code.indexOf('onMounted(', start);
  const calls = [], pending = [];
  const context = { state: { forms: {}, sops: {}, diet: {} }, activeTab: { value: 'forms' }, alive: { value: true }, tabs: [{ key: 'forms' }, { key: 'sops' }, { key: 'diet' }],
    loadTab: key => { calls.push(key); return new Promise(resolve => pending.push(resolve)); } };
  vm.createContext(context); vm.runInContext(code.slice(start, end), context);
  const result = context.initializeTabs();
  assert.deepEqual(calls, ['forms']);
  pending.shift()(); await tick();
  assert.deepEqual(calls, ['forms', 'sops']);
  context.alive.value = false; pending.shift()(); await result;
  assert(!calls.includes('diet'));
});

test('document attachment loading stops on transport failure before later batches', async () => {
  const code = source('pages/FormsDocumentsPage.vue');
  const start = code.indexOf('async function fullDocsInBatches(');
  const end = code.indexOf('async function loadTab(', start);
  let calls = 0;
  const failure = Object.assign(new Error('Timed out'), { code: 'TimeoutError' });
  const context = { frappeCall: async () => { calls++; throw failure; } };
  vm.createContext(context); vm.runInContext(code.slice(start, end), context);
  await assert.rejects(context.fullDocsInBatches(Array.from({ length: 100 }, (_, i) => ({ name: 'DOC-' + i })), { doctype: 'Forms And Documents' }), error => error === failure);
  assert.equal(calls, 8, 'do not keep starting attachment batches after a connection failure');
});

test('a document connection failure does not warm unopened categories', async () => {
  const code = source('pages/FormsDocumentsPage.vue');
  const start = code.indexOf('async function initializeTabs()'), end = code.indexOf('onMounted(', start);
  const calls = [];
  const context = { activeTab: { value: 'forms' }, alive: { value: true }, state: { forms: { transportError: true } },
    tabs: [{ key: 'forms' }, { key: 'sops' }], loadTab: async key => calls.push(key) };
  vm.createContext(context); vm.runInContext(code.slice(start, end), context);
  await context.initializeTabs();
  assert.deepEqual(calls, ['forms']);
});
