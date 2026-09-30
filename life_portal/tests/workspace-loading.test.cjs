const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../../life_slimming/public/js/portal_module_loading.js'), 'utf8');
const settle = () => new Promise(resolve => setTimeout(resolve, 160));
function setup() {
  const messages = [], requests = [];
  let onload;
  class XHR {
    open() {}
    send() { if(this.fail) throw Error('send failed'); }
    addEventListener(_, done) { this.done = done; }
  }
  const context = { URL, Request, WeakMap, setTimeout, clearTimeout, XMLHttpRequest: XHR,
    location: {href:'https://local.test/life_portal_module?module=tasks',origin:'https://local.test'},
    lifePortalModule:{module:'tasks'},
    addEventListener: (_, callback) => {onload=callback;},
    parent: {postMessage: message => messages.push(message)},
    fetch: () => new Promise((resolve,reject) => requests.push({resolve,reject})),
  };
  context.window=context;
  vm.runInNewContext(code,context);
  onload();
  return {context,messages,requests,XHR};
}
test('overlapping requests keep the main loader active through success and rejection', async () => {
  const {context,messages,requests}=setup();
  const first=context.fetch('/api/one');
  const second=context.fetch('/api/two').catch(()=>{});
  await settle();assert.equal(messages.at(-1).busy,true);
  requests[0].resolve({});await first;await settle();assert.equal(messages.at(-1).busy,true);
  requests[1].reject(Error('network'));await second;await settle();assert.equal(messages.at(-1).busy,false);
});
test('XHR loadend, abort/error completion, and synchronous failures release activity', async () => {
  const {messages,XHR}=setup();
  const first=new XHR();first.open('GET','/api/one');first.send();
  const second=new XHR();second.open('GET','/api/two');second.send();
  first.done();await settle();assert.equal(messages.at(-1).busy,true);
  second.done();await settle();assert.equal(messages.at(-1).busy,false);
  const failing=new XHR();failing.fail=true;failing.open('GET','/api/three');
  assert.throws(()=>failing.send());await settle();assert.equal(messages.at(-1).busy,false);
});
test('unrelated external requests do not block the workspace', async () => {
  const {context,messages,requests}=setup();
  const request=context.fetch('https://external.test/api/one');
  await settle();assert.equal(messages.at(-1).busy,false);
  requests[0].resolve({});await request;
});
