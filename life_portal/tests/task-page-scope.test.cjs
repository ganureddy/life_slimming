const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../src/lib/task-page-scope.js'), 'utf8').replace(/^import .*;\n/gm, '').replaceAll('export ', '');
function setup(request) {
  const document = new EventTarget(), status = { reads: 0, writes: 0, error: '', notice: '' };
  let removed = 0;
  document.defaultView = { setTimeout, clearTimeout, CSS: { escape: value => value }, confirm: () => true };
  document.head = { appendChild: node => node };
  const root = { ownerDocument: document, id: 'life-tt-app', matches: selector => selector === '#life-tt-app', querySelector: () => null, querySelectorAll: () => [], appendChild: node => node };
  const context = { request, AbortController, DOMException, Promise, Map, Set, JSON, Error };
  vm.createContext(context); vm.runInContext(code, context);
  const scope = context.createTaskPageScope({ root, session: { user: 'test@example.test', full_name: 'Test User', roles: ['System Manager'], csrf_token: 'fixture' }, status,
    dialogs: { create() {}, setUsers() {}, confirm() {}, dispose() { removed++; } } });
  return { scope, status, document, removed: () => removed };
}
test('callbacks finish with permission errors and expose a retryable page error', async () => {
  let errors = 0;
  const fixture = setup(async () => { throw Object.assign(new Error('No task access'), { code: 'PermissionError' }); });
  await assert.rejects(fixture.scope.frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'ToDo' }, error: () => errors++ }), /No task access/);
  assert.equal(errors, 1); assert.equal(fixture.status.reads, 0); assert.match(fixture.status.error, /No task access/);
  assert.equal((await fixture.scope.whenIdle()).ok, false);
  fixture.scope.dispose();
});
test('unmount aborts reads and suppresses callbacks on detached content', async () => {
  let callback = false, aborted = false;
  const fixture = setup((method, { signal }) => new Promise((resolve, reject) => signal.addEventListener('abort', () => { aborted = true; reject(new DOMException('Closed', 'AbortError')); })));
  const pending = fixture.scope.frappe.call({ method: 'frappe.client.get_list', callback: () => { callback = true; }, error: () => { callback = true; } });
  fixture.scope.dispose(); await assert.rejects(pending, { name: 'AbortError' });
  assert.equal(aborted, true); assert.equal(callback, false); assert.equal(fixture.removed(), 1);
});
test('page timers, document handlers and injected styles are removed on unmount', async () => {
  const fixture = setup(async () => ({ message: [] }));
  let events = 0, timers = 0, removed = 0;
  fixture.scope.document.addEventListener('fixture', () => events++);
  const style = { id: 'task-style', remove() { removed++; } };
  fixture.scope.document.head.appendChild(style);
  assert.equal(fixture.scope.document.getElementById('task-style'), style, 'reuse only styles owned by this instance');
  fixture.scope.setTimeout(() => timers++, 5);
  fixture.document.dispatchEvent(new Event('fixture')); assert.equal(events, 1);
  fixture.scope.dispose(); fixture.document.dispatchEvent(new Event('fixture'));
  await new Promise(resolve => setTimeout(resolve, 15));
  assert.equal(events, 1); assert.equal(timers, 0); assert.equal(removed, 1);
  assert.equal(fixture.document.defaultView.frappe, undefined, 'never install page globals');
});
test('writes are tracked and never automatically replayed or aborted as reads', async () => {
  let resolve, signal, calls = 0;
  const fixture = setup((method, options) => { calls++; signal = options.signal; return new Promise(done => { resolve = done; }); });
  const pending = fixture.scope.frappe.call({ method: 'frappe.client.save', args: { doc: { name: 'TASK-1' } } });
  assert.equal(fixture.status.writes, 1); assert.equal(fixture.status.reads, 0);
  fixture.scope.dispose(); assert.equal(signal.aborted, false);
  resolve({ message: { name: 'TASK-1' } }); await pending;
  assert.equal(calls, 1);
});

test('a controller callback failure is visible and does not leave a read pending', async () => {
  const fixture = setup(async () => ({ message: [] }));
  await assert.rejects(fixture.scope.frappe.call({ method: 'frappe.client.get_list', callback() { throw new Error('Could not render task rows'); } }), /Could not render/);
  assert.equal(fixture.status.reads, 0); assert.match(fixture.status.error, /Could not render task rows/);
  assert.equal((await fixture.scope.whenIdle()).ok, false);
  fixture.scope.dispose();
});
