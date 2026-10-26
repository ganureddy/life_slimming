// All ERP reads, conflict checks and appointment writes use intercepted fixtures.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const WebSocket = require('../node_modules/ws');
(async () => {
  const endpoint = process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9230', base = process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5178';
  const target = await (await fetch(endpoint + '/json/new?about:blank', { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise(resolve => ws.on('open', resolve));
  let sequence = 0, deny = false, historyFailure = false, conflict = false, writes = 0, holdReschedule = false, heldReschedule;
  const jobs = new Map(), calls = [], errors = [], records = new Map();
  const room1 = 'Room 1 - Clinic A', room2 = 'Room 2 - Clinic A';
  const date = '2030-10-15', nextDate = '2030-10-16';
  function reset() {
    records.clear(); writes = 0;
    const common = { doctype: 'Patient Appointment', branch: 'Clinic A', appointment_date: date, patient: 'PAT-1', patient_name: 'Priya Client', patient_sex: 'Female', custom_client_mobile_no: '9876543210', service_unit: 'Slimming', concern: 'Cryo', service_room: room1, modified: '2026-10-15 10:00:00', docstatus: 0 };
    records.set('APT-A', { ...common, name: 'APT-A', appointment_time: '07:00:00', call_back_status: 'Scheduled' });
    records.set('APT-B', { ...common, name: 'APT-B', appointment_time: '07:30:00', call_back_status: 'Cancel' });
    records.set('APT-C', { ...common, name: 'APT-C', service_room: room2, appointment_time: '08:00:00', call_back_status: 'Closed' });
    records.set('APT-D', { ...common, name: 'APT-D', appointment_date: nextDate, appointment_time: '09:00:00', call_back_status: 'Scheduled', custom_life_move_history: [{ from_date: date, from_time: '08:30:00', from_room: room1, to_date: nextDate, to_time: '09:00:00' }] });
  }
  const send = (method, params = {}) => new Promise((resolve, reject) => { jobs.set(++sequence, message => message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result)); ws.send(JSON.stringify({ id: sequence, method, params })); });
  const fulfill = (id, body, status = 200) => send('Fetch.fulfillRequest', { requestId: id, responseCode: status, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }], body: Buffer.from(JSON.stringify(body)).toString('base64') });
  const reply = (id, message) => fulfill(id, { message });
  const failure = id => fulfill(id, { exc_type: 'PermissionError', _server_messages: JSON.stringify([JSON.stringify({ message: 'Appointment access denied' })]) }, 403);
  ws.on('message', async raw => {
    const event = JSON.parse(raw); if (event.id) { jobs.get(event.id)?.(event); jobs.delete(event.id); return; }
    if (event.method === 'Runtime.exceptionThrown') errors.push(event.params.exceptionDetails.exception?.description || event.params.exceptionDetails.text);
    if (event.method !== 'Fetch.requestPaused') return;
    const { requestId, request } = event.params;
    try {
      const method = new URL(request.url).pathname.split('/api/method/')[1], args = JSON.parse(request.postData || '{}'); calls.push({ method, args });
      if (method === 'life_slimming.api.portal.bootstrap') return reply(requestId, { user: 'manager@example.test', full_name: 'Scheduler Manager', roles: ['System Manager'], portal_role: 'IT', csrf_token: 'fixture', session_id: target.id });
      if (method === 'life_slimming.api.convox.config') return reply(requestId, { enabled: false });
      if (method === 'frappe.desk.reportview.get') {
        const fields = JSON.parse(args.fields).map(field => field.split('`').at(-2));
        let rows = [];
        if (args.doctype === 'Branch') rows = [{ name: 'Clinic A', branch: 'Clinic A' }, { name: 'Head Office', branch: 'Head Office' }, { name: 'Testing Branch', branch: 'Testing Branch' }];
        if (args.doctype === 'Service Room') rows = [{ name: 'Room 10 - Clinic A' }, { name: room2 }, { name: room1 }, { name: 'Room 1 - Clinic B' }];
        if (args.doctype === 'Patient Appointment') {
          if (deny) return failure(requestId);
          const filters = JSON.parse(args.filters), targetDate = filters.find(filter => filter[1] === 'appointment_date')?.[3]?.[0];
          if (holdReschedule && filters.some(filter => filter[1] === 'call_back_status')) { heldReschedule = requestId; return; }
          rows = [...records.values()].filter(row => row.appointment_date === targetDate);
        }
        if (args.doctype === 'Therapy Plan') rows = [{ name: 'PLAN-1', patient: 'PAT-1', start_date: '2026-10-01', modified: '2026-10-15' }];
        return reply(requestId, { keys: fields, values: rows.map(row => fields.map(field => row[field] ?? '')) });
      }
      if (method === 'life_slimming.api.server_scripts.life_appointment_move_history.run') {
        if (historyFailure) return failure(requestId);
        const rows = [];
        for (const row of records.values()) for (const history of row.custom_life_move_history || []) if (history.from_date === args.date && !(row.appointment_date === args.date && row.appointment_time === history.from_time)) rows.push({ name: row.name, patient: row.patient_name, branch: row.branch, service_room: history.from_room, appointment_date: args.date, appointment_time: history.from_time, call_back_status: 'Re-Scheduled', life_ghost: true, life_target_date: row.appointment_date, life_target_time: row.appointment_time });
        return reply(requestId, { rows });
      }
      if (method === 'frappe.desk.search.search_link') return reply(requestId, args.doctype === 'Patient' ? [{ value: 'PAT-1', description: 'Priya Client' }] : [{ value: 'Slimming', description: 'Service Unit' }]);
      if (method === 'frappe.client.validate_link') return reply(requestId, args.doctype === 'Patient' ? { name: 'PAT-1', patient_name: 'Priya Client', sex: 'Female', mobile: '9876543210' } : { name: 'Slimming' });
      if (method === 'frappe.client.get') return reply(requestId, args.doctype === 'Therapy Plan' ? { name: 'PLAN-1', service_unit: 'Slimming', therapy_plan_details: [{ therapy_type: 'Cryo', no_of_sessions: 6, sessions_completed: 2 }, { therapy_type: 'Finished', no_of_sessions: 2, sessions_completed: 2 }] } : records.get(args.name));
      if (method === 'frappe.client.get_list') {
        const filters = args.filters;
        const rows = [...records.values()].filter(row => row.appointment_date === filters.appointment_date && row.service_room === filters.service_room);
        if (conflict) rows.push({ name: 'OTHER-BOOKING', service_room: filters.service_room, appointment_time: '09:30:00', call_back_status: 'Scheduled' });
        return reply(requestId, rows);
      }
      if (method === 'frappe.desk.form.save.savedocs') {
        const doc = JSON.parse(args.doc); writes++;
        const saved = { ...doc, name: doc.__islocal ? 'APT-NEW' : doc.name, modified: '2026-10-15 12:00:00' }; records.set(saved.name, saved);
        return fulfill(requestId, { docs: [saved] });
      }
      return reply(requestId, {});
    } catch (cause) { errors.push(cause.message); }
  });
  const evaluate = async expression => { const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text); return result.result.value; };
  const wait = async expression => { for (let attempt = 0; attempt < 160; attempt++) { if (await evaluate(expression)) return; await new Promise(resolve => setTimeout(resolve, 50)); } throw new Error('Timed out: ' + expression + '\n' + await evaluate('document.body.innerText')); };
  const click = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  const input = (selector, value) => evaluate(`(()=>{const element=document.querySelector(${JSON.stringify(selector)});element.value=${JSON.stringify(value)};element.dispatchEvent(new Event('input',{bubbles:true}));element.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  const mousePick = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true}))`);
  const boardReady = () => wait("!document.querySelector('.refresh-btn').disabled && document.querySelectorAll('.pa-table-head th').length===4");
  try {
    await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*/api/method/*' }] });
    for (const width of [1440, 390]) {
      reset();
      await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: width < 500 });
      await send('Page.navigate', { url: base + '/life_portal/native/appointments' });
      await wait("document.querySelector('.room-count')?.textContent==='3'");
      await input('.date-filter', date); await boardReady(); await wait("document.querySelector('.total-count').textContent==='3'");
      assert.equal(await evaluate('document.querySelectorAll("iframe").length'), 0);
      assert(await evaluate('document.documentElement.scrollWidth<=innerWidth+1'), 'no viewport overflow at ' + width);
      assert.equal(await evaluate('document.querySelectorAll(".pa-table-body > tr").length'), 25);
      assert.equal(await evaluate('document.querySelector(".available-count").textContent'), '73');
      assert.equal(await evaluate('document.querySelector(".cancel-count").textContent'), '1');
      assert.equal(await evaluate('document.querySelectorAll(".life-move-ghost").length'), 1);
      assert.equal(await evaluate('document.querySelectorAll(".branch-filter option").length'), 1);
      assert.deepEqual(await evaluate('Array.from(document.querySelectorAll(".pa-table-head th")).slice(1).map(e=>e.textContent)'), ['Room 1', 'Room 2', 'Room 10']);
      assert(await evaluate(`document.querySelector('.add-appt-btn[data-room="${room1}"][data-slot="07:30 AM"]')!==null`), 'cancelled slot remains bookable');
      fs.writeFileSync('/tmp/appointments-vue-' + width + '.png', Buffer.from((await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })).data, 'base64'));
      await click('.life-move-ghost'); await boardReady(); await wait(`document.querySelector('.date-filter').value==='${nextDate}'`);
      await input('.date-filter', date); await boardReady();
      await click(`.add-appt-btn[data-room="${room1}"][data-slot="07:30 AM"]`);
      await wait("document.querySelector('.pa-modal')");
      assert.equal(await evaluate('document.body.style.overflow'), 'hidden');
      await input('.modal-client', 'Pri'); await wait("document.querySelector('.client-suggestions .client-option strong')"); await mousePick('.client-suggestions .client-option');
      await wait("document.querySelector('.modal-client-details').value.includes('Priya Client')");
      await input('.modal-category', 'Slim'); await evaluate("document.querySelector('.modal-category').dispatchEvent(new FocusEvent('focus'))"); await wait("document.querySelector('.category-suggestions strong')"); await mousePick('.category-suggestions .client-option');
      await evaluate("document.querySelector('.modal-concern').dispatchEvent(new FocusEvent('focus'))");
      await wait("document.querySelector('.concern-suggestions .client-option strong')?.textContent==='Cryo'");
      assert((await evaluate('document.querySelector(".concern-suggestions").textContent')).includes('Pending: 4'));
      assert(!(await evaluate('document.querySelector(".concern-suggestions").textContent')).includes('Finished'));
      await mousePick('.concern-suggestions .client-option'); await wait("!document.querySelector('.create-btn').disabled");
      assert(await evaluate('document.documentElement.scrollWidth<=innerWidth+1'), 'create dialog must fit the viewport');
      assert(await evaluate("(()=>{const body=document.querySelector('.pa-modal .modal-body'),bounds=body.getBoundingClientRect(),padding=parseFloat(getComputedStyle(body).paddingRight);return Array.from(body.querySelectorAll('input,select')).every(field=>field.getBoundingClientRect().right<=bounds.right-padding+1);})()"), 'form controls must fit inside the dialog padding');
      fs.writeFileSync('/tmp/appointment-create-' + width + '.png', Buffer.from((await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })).data, 'base64'));
      await evaluate("(()=>{const button=document.querySelector('.create-btn');button.click();button.click();})()"); await wait("!document.querySelector('.pa-modal') && document.querySelector('.total-count').textContent==='4'");
      assert.equal(writes, 1, 'double click cannot duplicate the booking');
      const created = records.get('APT-NEW'); assert.equal(created.patient, 'PAT-1'); assert.equal(created.concern, 'Cryo'); assert.equal(created.service_unit, 'Slimming'); assert.equal(created.appointment_time, '7:30:00'); assert.equal(created.call_back_status, 'Scheduled');
      await click('.appt-cell[data-name="APT-A"]'); await wait("document.querySelector('.detail-status-select')");
      assert((await evaluate('document.querySelector(".detail-grid").textContent')).includes('9876543210'));
      await input('.detail-status-select', 'Re-Scheduled'); await wait("document.querySelector('.reschedule-date')");
      await input('.reschedule-date', nextDate); await wait("!document.querySelector('.reschedule-slot').disabled && document.querySelectorAll('.reschedule-slot option').length>1");
      assert(!(await evaluate('Array.from(document.querySelectorAll(".reschedule-slot option")).map(e=>e.value)')).includes('09:00 AM'));
      await input('.reschedule-slot', '09:30 AM'); conflict = true; await click('.detail-save-btn');
      await wait("document.querySelector('.detail-error')?.textContent.includes('already booked')"); assert.equal(writes, 1);
      conflict = false; await click('.detail-save-btn'); await wait(`!document.querySelector('.appt-detail-modal') && document.querySelector('.date-filter').value==='${nextDate}'`); await boardReady();
      const moved = records.get('APT-A'); assert.equal(moved.call_back_status, 'Scheduled'); assert.equal(moved.appointment_time, '9:30:00');
      assert.equal(moved.custom_life_move_history[0].from_date, date); assert.equal(moved.custom_life_move_history[0].from_time, '07:00:00'); assert.equal(moved.custom_life_move_history[0].moved_by, 'manager@example.test');
      await input('.date-filter', date); await boardReady(); await wait("document.querySelectorAll('.life-move-ghost').length===2");
      assert(await evaluate(`!!document.querySelector('.add-appt-btn[data-room="${room1}"][data-slot="07:00 AM"]')`));
      await click('.appt-cell[data-name="APT-NEW"]'); await wait("document.querySelector('.detail-status-select')"); await input('.detail-status-select', 'Cancel'); await click('.detail-save-btn'); await wait("!document.querySelector('.appt-detail-modal')"); await boardReady();
      assert.equal(records.get('APT-NEW').call_back_status, 'Cancel');
      historyFailure = true; await click('.refresh-btn'); await wait("document.querySelector('.scheduler-error')?.textContent.includes('Reschedule history could not load')");
      historyFailure = false; await click('.scheduler-error button'); await boardReady(); await wait("!document.querySelector('.scheduler-error')");
      deny = true; await click('.refresh-btn'); await wait("document.querySelector('.scheduler-error')?.textContent.includes('Appointment access denied')");
      deny = false; await click('.scheduler-error button'); await boardReady();
      await input('.date-filter', '2020-01-01'); await boardReady(); assert.equal(await evaluate('document.querySelectorAll(".add-appt-btn").length'), 0);
      assert(!calls.some(call => /`(?:modified|appointment_time) (?:asc|desc)`/.test(call.args.order_by || '')), 'sort direction must be outside SQL field quotes');
    }
    await input('.date-filter', ''); await wait("document.querySelector('.scheduler-error')?.textContent.includes('select branch and date')");
    assert.equal(await evaluate('document.querySelectorAll(".add-appt-btn").length'),0);
    await input('.date-filter', date); await boardReady();
    await click('.appt-cell[data-name="APT-C"]'); await wait("document.querySelector('.detail-status-select')");
    holdReschedule = true; await input('.detail-status-select', 'Re-Scheduled');
    await wait("document.querySelector('.reschedule-slot')?.disabled");
    for (let attempt = 0; attempt < 80 && !heldReschedule; attempt++) await new Promise(resolve => setTimeout(resolve, 25));
    assert(heldReschedule, 'reschedule list is deliberately pending');
    await input('.detail-status-select', 'Cancel');
    await wait("!document.querySelector('.detail-save-btn').disabled");
    await reply(heldReschedule, { keys: [], values: [] }).catch(() => {}); holdReschedule = false;
    await send('Input.dispatchKeyEvent', {type:'keyDown',key:'Escape',code:'Escape'});
    await wait("!document.querySelector('.appt-detail-modal')");
    assert.equal(await evaluate('document.body.style.overflow'), '');
    // Links from Client Info now carry the validated branch and patient.
    reset();
    await send('Page.navigate', {url:base+'/life_portal/native/appointments?branch=Clinic%20A&patient=PAT-1'});
    await wait("document.querySelector('.room-count')?.textContent==='3'");
    await input('.date-filter',date); await boardReady();
    await click(`.add-appt-btn[data-room="${room1}"][data-slot="07:30 AM"]`);
    await wait("document.querySelector('.modal-client-details')?.value.includes('Priya Client')");
    assert.equal(await evaluate("document.querySelector('.modal-client').value"),'Priya Client');
    assert.equal(await evaluate("document.querySelector('.branch-filter').value"),'Clinic A');
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape'});
    await wait("!document.querySelector('.pa-modal')");
    // Vue navigation removes the page and its modal lifecycle without reloading the document.
    await click('a[href="/life_portal/"]'); await wait("!document.querySelector('#client-appointment-page')");
    assert.equal(await evaluate('document.body.style.overflow'), '');
    assert.deepEqual(errors, []);
    console.log('Appointment Scheduler Vue: desktop/mobile, original grid, occupancy and history, pending concerns, create payload/double-submit, conflict checks, reschedule history, cancellation, past slots and error recovery passed.');
  } finally { await send('Page.close').catch(() => {}); ws.close(); }
})().catch(cause => { console.error(cause); process.exitCode = 1; });
