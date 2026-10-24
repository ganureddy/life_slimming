// Full task/ticket requests are intercepted. This test never writes ERP data.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const WebSocket = require('../node_modules/ws');
(async () => {
  const endpoint = process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9230', base = process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5178';
  const target = await (await fetch(endpoint + '/json/new?about:blank', { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise(resolve => ws.on('open', resolve));
  let sequence = 0, manager = true, denyTasks = false, heldUserRequest;
  const jobs = new Map(), calls = [], errors = [], todos = new Map(), issues = new Map();
  const user = 'manager@example.test';
  const users = [{ name: user, full_name: 'Task Manager', enabled: 1 }, { name: 'priya@example.test', full_name: 'Priya Agent', enabled: 1 }, { name: 'arun@example.test', full_name: 'Arun Resolver', enabled: 1 }];
  const description = (details, extra = {}) => '<!--LIFE_TASK_META:' + JSON.stringify({ category: 'IT', start_date: '2026-10-15', deadline_datetime: '2030-10-15T18:00', update_to: [user], ...extra }) + '-->\n' + details;
  todos.set('TASK-1', { doctype: 'ToDo', name: 'TASK-1', description: description('Check clinic laptop'), allocated_to: user, assigned_by: 'priya@example.test', owner: 'priya@example.test', priority: 'High', status: 'Open', date: '2030-10-15', custom_task_queue_no: 1, custom_queue_active: 1, modified: '2026-10-15 10:00:00' });
  todos.set('TASK-2', { doctype: 'ToDo', name: 'TASK-2', description: description('Review clinic stock'), allocated_to: 'priya@example.test', assigned_by: user, owner: user, priority: 'Medium', status: 'Open', date: '2030-10-15', custom_task_queue_no: 1, custom_queue_active: 1, modified: '2026-10-15 09:00:00' });
  issues.set('ISSUE-1', { doctype: 'Issue', name: 'ISSUE-1', subject: 'IT / ERP / Software - ERP Login Issue', description: '<!--LIFE_TICKET_META:' + JSON.stringify({ branch: 'Head Office', category: 'IT / ERP / Software', issue: 'ERP Login Issue', tag_to: user, cc_to: [] }) + '-->\nExisting login issue', owner: 'priya@example.test', raised_by: 'priya@example.test', priority: 'High', status: 'Open', modified: '2026-10-15 10:00:00' });
  const send = (method, params = {}) => new Promise((resolve, reject) => { jobs.set(++sequence, message => message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result)); ws.send(JSON.stringify({ id: sequence, method, params })); });
  const fulfill = (id, message, status = 200) => send('Fetch.fulfillRequest', { requestId: id, responseCode: status, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }], body: Buffer.from(JSON.stringify(status === 200 ? { message } : { exc_type: 'PermissionError', _server_messages: JSON.stringify([JSON.stringify({ message: 'Task access denied' })]) })).toString('base64') });
  ws.on('message', async raw => {
    const event = JSON.parse(raw); if (event.id) { jobs.get(event.id)?.(event); jobs.delete(event.id); return; }
    if (event.method === 'Runtime.exceptionThrown') errors.push(event.params.exceptionDetails.exception?.description || event.params.exceptionDetails.text);
    if (event.method !== 'Fetch.requestPaused') return;
    const { requestId, request } = event.params;
    try {
      const method = new URL(request.url).pathname.split('/api/method/')[1];
      const args = method === 'upload_file' ? {} : JSON.parse(request.postData || '{}'); calls.push({ method, args });
      if (method === 'life_slimming.api.portal.bootstrap') return fulfill(requestId, { user, session_id: 'task-fixture-' + target.id + manager, full_name: 'Task Manager', roles: manager ? ['System Manager'] : ['Sales User'], portal_role: 'IT', csrf_token: 'fixture' });
      if (method === 'life_slimming.api.convox.config') return fulfill(requestId, { enabled: false });
      if (method === 'frappe.client.get_list') {
        if (args.doctype === 'User') { heldUserRequest = requestId; return; }
        if (args.doctype === 'File') return fulfill(requestId, []);
        if (args.doctype === 'ToDo') {
          if (denyTasks) return fulfill(requestId, null, 403);
          let rows = [...todos.values()];
          if (args.filters?.allocated_to) rows = rows.filter(row => row.allocated_to === args.filters.allocated_to);
          return fulfill(requestId, rows);
        }
        if (args.doctype === 'Issue') return fulfill(requestId, [...issues.values()]);
        return fulfill(requestId, []);
      }
      if (method === 'frappe.client.get') return fulfill(requestId, (args.doctype === 'ToDo' ? todos : issues).get(args.name));
      if (method === 'frappe.client.insert') {
        const map = args.doc.doctype === 'ToDo' ? todos : issues;
        const doc = { ...args.doc, name: (args.doc.doctype === 'ToDo' ? 'TASK-' : 'ISSUE-') + (map.size + 1), owner: user, modified: '2026-10-15 12:00:00' };
        map.set(doc.name, doc); return fulfill(requestId, doc);
      }
      if (method === 'frappe.client.save') { (args.doc.doctype === 'ToDo' ? todos : issues).set(args.doc.name, args.doc); return fulfill(requestId, args.doc); }
      if (method === 'frappe.client.set_value') {
        const doc = todos.get(args.name); const values = typeof args.fieldname === 'object' ? args.fieldname : { [args.fieldname]: args.value };
        Object.assign(doc, values); return fulfill(requestId, doc);
      }
      if (method === 'upload_file') return fulfill(requestId, { file_url: '/private/files/task-photo.png' });
      return fulfill(requestId, {});
    } catch (error) { errors.push(error.stack); await fulfill(requestId, null, 500); }
  });
  const evaluate = async expression => { const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text); return result.result.value; };
  const wait = async expression => { for (let i = 0; i < 140; i++) { if (await evaluate(expression)) return; await new Promise(resolve => setTimeout(resolve, 50)); } throw new Error('Timeout: ' + expression + '\n' + await evaluate('document.body.innerText') + '\nErrors:' + JSON.stringify(errors)); };
  const click = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  const input = (selector, value) => evaluate(`(() => { const el=document.querySelector(${JSON.stringify(selector)}); el.value=${JSON.stringify(value)}; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); })()`);
  const releaseUsers = async () => { if (heldUserRequest) { const id = heldUserRequest; heldUserRequest = null; await fulfill(id, users); } };
  try {
    await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*/api/method/*' }] });
    for (const width of [1440, 390]) {
      calls.length = 0; denyTasks = false;
      await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
      await send('Page.navigate', { url: base + '/life_portal/tasks' });
      await wait("document.querySelector('#mytask-to-body')?.textContent.includes('IT')");
      assert(heldUserRequest, 'records must not wait for the user master list');
      assert.equal(calls.some(call => call.method === 'frappe.client.get' && call.args.doctype === 'User'), false, 'bootstrap supplies authenticated identity');
      await releaseUsers();
      assert.equal(await evaluate('!!document.querySelector("iframe")'), false);
      assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true, 'viewport overflow at ' + width);
      assert.equal(await evaluate('document.querySelector("#logged-in-user-name").textContent'), 'Task Manager');
      await click('[data-task-sub="2"]'); await wait("document.querySelector('#mytask-to-body')?.textContent.includes('IT')");
      assert(await evaluate("document.querySelector('#mytask-by-body').textContent.includes('Priya')"));
      if (width === 1440) {
        await click('#mytask-to-body .task-done-btn[data-name="TASK-1"]');
        await wait("document.querySelector('.task-field-dialog textarea')");
        await input('.task-field-dialog textarea', 'Laptop checks completed'); await click('.task-field-dialog button[type="submit"]');
        await wait("document.querySelector('#mytask-to-body')?.textContent.includes('Completed')");
        assert(todos.get('TASK-1').description.includes('Laptop checks completed'));
        assert.equal(todos.get('TASK-1').status, 'Open', 'assignee completion waits for assigner review');
        await click('#mytask-by-body .task-cancel-btn[data-name="TASK-2"]');
        await wait("document.querySelector('.task-field-dialog textarea')");
        await input('.task-field-dialog textarea', 'Clinic work deferred'); await click('.task-field-dialog button[type="submit"]');
        await wait("document.querySelector('#mytask-by-body')?.textContent.includes('Cancelled')");
        assert.equal(todos.get('TASK-2').status, 'Cancelled'); assert.equal(todos.get('TASK-2').custom_queue_active, 0);
        await click('#mytask-by-body .task-reopen-cancelled-btn[data-name="TASK-2"]');
        await wait("document.querySelector('.task-field-dialog textarea')");
        await input('.task-field-dialog textarea', 'Clinic work resumed'); await click('.task-field-dialog button[type="submit"]');
        await wait("document.querySelector('#mytask-by-body .task-reassign-btn[data-name=\"TASK-2\"]')");
        assert.equal(todos.get('TASK-2').status, 'Open'); assert.equal(todos.get('TASK-2').custom_queue_active, 1);
        await click('#mytask-by-body .task-reassign-btn[data-name="TASK-2"]');
        await wait("document.querySelector('.task-field-dialog input[list]')");
        await input('.task-field-dialog input[list]', 'arun@example.test');
        await input('.task-field-dialog textarea', 'Hand over stock review'); await click('.task-field-dialog button[type="submit"]');
        await wait("document.querySelector('#mytask-by-body')?.textContent.includes('Arun')");
        assert.equal(todos.get('TASK-2').allocated_to, 'arun@example.test'); assert(todos.get('TASK-2').description.includes('Hand over stock review'));
        await click('[data-task-sub="0"]'); await click('#task-submit-btn'); await wait("document.querySelector('#modal-title')?.textContent === 'Select Assignee'"); await click('#modal-ok-btn');
        await input('#task-assignto-search', 'Priya'); await wait("document.querySelector('#task-assignto-results')?.textContent.includes('Priya')");
        await click('#task-assignto-results > *');
        await input('#task-category', 'IT'); await input('#task-deadline', '2030-10-15T18:00'); await input('#task-details', 'Prepare the clinic report');
        fs.writeFileSync('/tmp/task-vue-fixture.png', Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jZ4sAAAAASUVORK5CYII=', 'base64'));
        const doc = await send('DOM.getDocument');
        const fileInput = await send('DOM.querySelector', { nodeId: doc.root.nodeId, selector: '#task-file-input' });
        await send('DOM.setFileInputFiles', { nodeId: fileInput.nodeId, files: ['/tmp/task-vue-fixture.png'] });
        await wait("document.querySelector('#task-attach-list')?.textContent.includes('task-vue-fixture.png')");
        await click('#task-priority-grp [data-p="High"]'); await click('#task-submit-btn'); await wait("document.querySelector('#modal-title')?.textContent.includes('Task Assigned')");
        assert.equal(todos.size, 3); const created = todos.get('TASK-3');
        assert.equal(calls.filter(call => call.method === 'upload_file').length, 1);
        assert.equal(created.allocated_to, 'priya@example.test'); assert.equal(created.assigned_by, user); assert(created.description.includes('LIFE_TASK_META')); assert(created.description.includes('Prepare the clinic report'));
        await click('#modal-ok-btn');
      }
      await click('[data-task-sub="1"]'); await input('#tr-view-mode', 'list');
      await input('#tr-priority', 'Medium'); await click('#task-report-apply');
      await wait("document.querySelector('#task-report-count')?.textContent === '1'");
      assert(await evaluate("document.querySelector('#task-report-body').textContent.includes('Arun')"));
      await input('#tr-category', 'Sales'); await click('#task-report-apply');
      await wait("document.querySelector('#task-report-count')?.textContent === '0'");
      await input('#tr-category', ''); await input('#tr-priority', ''); await click('#task-report-apply');
      await wait("document.querySelector('#task-report-count')?.textContent === '3'");
      await input('#life-task-assignee-search', 'Arun');
      await wait("document.querySelector('#task-report-count')?.textContent === '1'");
      await click('#life-task-assignee-clear');
      await click('#life-manage-queue-btn'); await wait("document.querySelector('#life-web-assignee-search')");
      await input('#life-web-assignee-search', 'Arun'); await click('#life-web-assignee-results button');
      await wait("document.querySelector('#life-web-queue-overlay .life-web-queue-no')");
      assert(await evaluate("document.querySelector('#life-tt-app').contains(document.querySelector('#life-web-queue-overlay'))"));
      assert.equal(await evaluate("document.querySelectorAll('#life-manage-queue-web-style').length"), 1);
      await click('#life-web-queue-close');
      await click('#toggle-ticket'); await click('[data-ticket-sub="2"]'); await wait("document.querySelector('#myticket-tome-body')?.textContent.includes('ERP Login Issue')");
      if (width === 1440) {
        await click('#myticket-tome-body .ticket-resolve-btn[data-name="ISSUE-1"]');
        await wait("document.querySelector('.task-field-dialog textarea')"); await input('.task-field-dialog textarea', 'Access restored');
        await click('.task-field-dialog button[type="submit"]'); await wait("document.querySelector('#myticket-tome-body')?.textContent.includes('Resolved')");
        assert.equal(issues.get('ISSUE-1').status, 'Resolved'); assert(issues.get('ISSUE-1').description.includes('Access restored'));
      }
      await click('[data-ticket-sub="0"]');
      if (width === 1440) {
        await input('#ticket-category', 'IT / ERP / Software'); await input('#ticket-issue', 'ERP Login Issue');
        await input('#ticket-tagto-search', 'Arun'); await wait("document.querySelector('#ticket-tagto-results')?.textContent.includes('Arun')"); await click('#ticket-tagto-results > *');
        await input('#ticket-details', 'Please restore clinic access'); await click('#ticket-priority-grp [data-p="Medium"]'); await click('#ticket-submit-btn'); await wait("document.querySelector('#modal-title')?.textContent.includes('Ticket Raised') || document.querySelector('#modal-title')?.textContent.includes('Ticket Submitted')");
        assert.equal(issues.size, 2); assert(issues.get('ISSUE-2').description.includes('arun@example.test')); await click('#modal-ok-btn');
      }
      // Capture the actual page for review alongside the canonical source CSS.
      fs.writeFileSync('/tmp/tasks-native-' + width + '.png', Buffer.from((await send('Page.captureScreenshot', { format: 'png' })).data, 'base64'));
      console.log('Task/ticket Vue checks passed at width ' + width);
    }
    manager = false;
    todos.set('OUTSIDE-TASK', { ...todos.get('TASK-2'), name: 'OUTSIDE-TASK', allocated_to: 'outsider@example.test', assigned_by: 'outsider@example.test', owner: 'outsider@example.test', description: description('Outside-only task') });
    await send('Page.navigate', { url: base + '/life_portal/tasks' });
    await wait("document.querySelector('#mytask-to-body')?.textContent.includes('IT')");
    await releaseUsers();
    assert.equal(await evaluate("document.querySelector('[data-task-sub=\"1\"]').style.display"), 'none');
    assert.equal(await evaluate("document.querySelector('[data-ticket-sub=\"1\"]').style.display"), 'none');
    assert.equal(await evaluate("document.querySelector('#task-report-body').textContent.includes('Outside-only task')"), false);
    denyTasks = true; await click('#life-refresh-btn');
    await wait("document.querySelector('.task-page-error')?.textContent.includes('Task access denied')");
    await releaseUsers(); await wait("!document.querySelector('#life-refresh-btn').disabled");
    assert.equal(await evaluate("document.querySelector('#life-refresh-note').textContent"), 'Refresh failed. Please retry.');
    denyTasks = false; await click('.task-page-error button');
    await wait("document.querySelector('#mytask-to-body')?.textContent.includes('IT')");
    await releaseUsers(); await wait("!document.querySelector('#life-refresh-btn').disabled");
    assert.equal(await evaluate("!!document.querySelector('.task-page-error')"), false);
    await send('Page.navigate', { url: base + '/life_portal/clusterhome' });
    await wait("!document.querySelector('#life-tt-app')");
    assert.equal(await evaluate("!!document.querySelector('#life-manage-queue-web-style')"), false);
    console.log('Task permissions, file upload, error/retry and page cleanup checks passed.');
    assert.deepEqual(errors, []);
  } finally { ws.close(); await fetch(endpoint + '/json/close/' + target.id); }
})().catch(error => { console.error(error); process.exitCode = 1; });
