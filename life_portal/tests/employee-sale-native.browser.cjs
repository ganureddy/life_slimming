// ERP requests, including writes and uploads, are intercepted fixture responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const WebSocket = require('../node_modules/ws');
(async () => {
  const endpoint = process.env.PORTAL_BROWSER_URL || 'http://127.0.0.1:9230';
  const base = process.env.PORTAL_PREVIEW_URL || 'http://127.0.0.1:5178';
  const target = await (await fetch(endpoint + '/json/new?about:blank', { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise(resolve => ws.on('open', resolve));
  let seq = 0, deny = false, restricted = false;
  const jobs = new Map(), calls = [], errors = [];
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    jobs.set(++seq, message => message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result));
    ws.send(JSON.stringify({ id: seq, method, params }));
  });
  const fulfill = (id, message, status = 200) => send('Fetch.fulfillRequest', {
    requestId: id, responseCode: status, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
    body: Buffer.from(JSON.stringify(status === 200 ? { message } : { exc_type: 'PermissionError', _server_messages: JSON.stringify([JSON.stringify({ message: 'Employee report access denied' })]) })).toString('base64'),
  });
  ws.on('message', async raw => {
    const event = JSON.parse(raw);
    if (event.id) { jobs.get(event.id)?.(event); jobs.delete(event.id); return; }
    if (event.method === 'Runtime.exceptionThrown') errors.push(event.params.exceptionDetails.exception?.description || event.params.exceptionDetails.text);
    if (event.method !== 'Fetch.requestPaused') return;
    const { requestId, request } = event.params;
    try {
      const method = new URL(request.url).pathname.split('/api/method/')[1];
      const args = method === 'upload_file' ? {} : JSON.parse(request.postData || '{}'); calls.push({ method, args });
      if (method === 'life_slimming.api.portal.bootstrap') return fulfill(requestId, { user: 'manager@example.test', full_name: 'Registration Manager', roles: restricted ? ['Sales User'] : ['System Manager'], portal_role: 'IT', csrf_token: 'fixture', session_id: target.id });
      if (method === 'life_slimming.api.convox.config') return fulfill(requestId, { enabled: false });
      if (method === 'frappe.client.get_list') {
        if (args.doctype === 'Branch') return fulfill(requestId,[{name:'Clinic A'},{name:'Clinic B'},{name:'Head Office'},{name:'Testing Branch'}]);
        if (args.doctype === 'Mode of Payment') return fulfill(requestId,[{name:'Cash',type:'Cash'},{name:'UPI',type:'Bank'}]);
        if (args.doctype === 'Employee') return fulfill(requestId,[{name:'EMP-1',employee_name:'Priya'},{name:'EMP-2',employee_name:'Arun'}]);
      }
      if (method === 'frappe.desk.query_report.run') {
        const filter = JSON.parse(args.filters), target = filter.branch;
        const make = (invoice,branch,extra={})=>({invoice,branch,invoice_date:'2026-10-15',customer:'Customer One',client_name:'Client One',booking_type:'InHouse',mode_of_payment:'Cash, UPI',paid_amount:1050,paid_amount_without_gst:1000,gst_amount:50,grand_total:2100,outstanding_amount:1050,referring_employee:'Priya',referring_employee_id:'EMP-1',incentive_employee:'Arun',incentive_employee_id:'EMP-2',referring_employee_share:600,incentive_employee_share:400,payment_ids:'PAY-1',payment_dates:'2026-10-15',sharing_type:'Shared',...extra});
        const rows=[make('INV-1','Clinic A'),make('INV-2','Clinic B',{incentive_employee:'Priya',incentive_employee_id:'EMP-1',booking_type:'Reference'})];
        return fulfill(requestId,{result:rows},deny?403:200);
      }
      return fulfill(requestId, {});
    } catch (error) { errors.push(error.message); }
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    return result.result.value;
  };
  const wait = async expression => {
    for (let i = 0; i < 120; i++) { if (await evaluate(expression)) return; await new Promise(resolve => setTimeout(resolve, 50)); }
    throw new Error('Timed out: ' + expression + '\n' + JSON.stringify({errors,calls,body:await evaluate("document.body.innerText.slice(0,3000)")}));
  };
  const click = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  const input = (selector, value) => evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  try {
    await send('Page.enable'); await send('Runtime.enable'); await send('DOM.enable');
    await send('Fetch.enable', { patterns: [{ urlPattern: '*/api/method/*' }] });
    const select = async (id,text,option) => {
      await input('#'+id,text);await evaluate(`document.querySelector('#${id}').dispatchEvent(new FocusEvent('focus'))`);
      await wait(`Array.from(document.querySelectorAll('#${id}-options [role=option]')).some(row=>row.textContent.includes(${JSON.stringify(option)}))`);
      await evaluate(`Array.from(document.querySelectorAll('#${id}-options [role=option]')).find(row=>row.textContent.includes(${JSON.stringify(option)})).dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true}))`);
    };
    for (const width of [1440,390]) {
      await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<500});
      await send('Page.navigate',{url:base+'/life_portal/empsale'});
      await wait("document.querySelector('#ref-status')?.textContent.includes('Loaded 2 invoices')");
      assert.equal(await evaluate('document.querySelectorAll("iframe").length'),0);
      assert(await evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'no overflow at '+width);
      assert.equal(await evaluate('document.querySelectorAll("#ref-ov-tiles .ref-tile").length'),6);
      assert((await evaluate('document.querySelector("#ref-ov-tiles").textContent')).includes('2,000'));
      await click('[data-tab="1"]');await wait("document.querySelector('#ref-mode-1').classList.contains('on')");
      assert.equal(await evaluate('document.querySelectorAll("#ref-emp-body tr").length'),2);
      assert.equal(await evaluate('document.querySelector("#ref-emp-body tr").children[1].textContent'),'Priya');
      assert.equal(await evaluate('document.querySelector("#ref-emp-body tr").children[5].textContent'),'₹1,600');
      await input('#ref-emp-srch','Arun');assert.equal(await evaluate('document.querySelectorAll("#ref-emp-body tr").length'),1);
      await input('#ref-emp-srch','');await input('#ref-emp-mop-srch','No Match');assert((await evaluate('document.querySelector("#ref-emp-body").textContent')).includes('No data'));
      await input('#ref-emp-mop-srch','');
      await click('[data-tab="2"]');assert.equal(await evaluate('document.querySelectorAll("#ref-br-body tr").length'),2);
      await click('[data-tab="3"]');assert.equal(await evaluate('document.querySelectorAll("#ref-txn-body tr").length'),2);
      assert.equal(await evaluate('document.querySelector("#ref-txn-body tr").children.length'),17);
      await evaluate("window.__exportBlobs=[];URL.createObjectURL=blob=>{window.__exportBlobs.push(blob);return 'blob:fixture'};HTMLAnchorElement.prototype.click=function(){};");
      await click('#ref-global-excel-btn');await wait('window.__exportBlobs.length===1');
      const globalXml=await evaluate('window.__exportBlobs[0].text()');for(const value of ['Client One','PAY-1','Shared','ss:Type="Number">600'])assert(globalXml.includes(value),value);
      await click('[data-tab="1"]');await click('#ref-emp-xlsx');await wait('window.__exportBlobs.length===2');assert((await evaluate('window.__exportBlobs[1].text()')).includes('1600'));
      await select('ref-f-emp','Pri','Priya (EMP-1)');await click('#ref-generate-btn');await wait("document.querySelector('#ref-status').textContent.includes('Loaded 2 invoices and 2 employee credits')");
      assert.equal(await evaluate('document.querySelectorAll("#ref-emp-body tr").length'),1);assert.equal(await evaluate('document.querySelector("#ref-emp-body tr").children[5].textContent'),'₹1,600');
      await input('#ref-f-paid-from','9000');await input('#ref-f-paid-to','10');await click('#ref-generate-btn');await wait("document.querySelector('#ref-status').textContent.includes('correct the amount')");
      await click('.ref-reset-btn');await wait("document.querySelector('#ref-status').textContent.includes('Loaded 2 invoices and 3 employee credits')");
      await select('ref-f-branch','Clinic A','Clinic A');await click('#ref-generate-btn');await wait("document.querySelector('#ref-status').textContent.includes('Loaded 1 invoices')");
      assert.equal(JSON.parse(calls.filter(call=>call.method==='frappe.desk.query_report.run').at(-1).args.filters).branch,'Clinic A');
      await click('[data-range="year"]');assert(/-04-01$/.test(await evaluate('document.querySelector("#ref-f-from").value')));
      await click('[data-tab="0"]');fs.writeFileSync('/tmp/employee-vue-'+width+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
      deny=true;await click('#ref-generate-btn');await wait("document.querySelector('#ref-status').textContent.includes('Employee report access denied')");deny=false;await click('#ref-status button');await wait("document.querySelector('#ref-status').textContent.includes('Loaded 1 invoices')");
    }
    restricted=true;calls.length=0;await send('Page.navigate',{url:base+'/life_portal/empsale'});
    await wait("document.querySelector('#ref-status')?.textContent.includes('Loaded 2 invoices')");
    const queries=calls.filter(call=>call.method==='frappe.desk.query_report.run').map(call=>JSON.parse(call.args.filters).branch).sort();
    assert.deepEqual(queries,['Clinic A','Clinic B'],'restricted all-branch requests must explicitly name only permitted branches');
    assert.equal(errors.length,0,errors.join('\n'));
    console.log('Employee Sale Master Vue: desktop/mobile, all views, split/same-employee credits, searches, selectors, amount validation, both Excel exports, restricted branch fan-out and permission recovery passed.');
  } finally { await send('Page.close').catch(() => {}); ws.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
