const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../src/api/http.js'), 'utf8').replace(/^import .*;\n/gm, '').replaceAll('export ', '');
function setup(status, body) {
  const context = { apiUrl: v => v, apiCredentials: () => 'same-origin', fetch: async () => ({ ok: false, status, json: async () => body }) };
  vm.createContext(context);
  vm.runInContext(code + '\nthis.send = request;', context);
  return context.send('fixture');
}
test('validation errors show the server message as plain text', async () => {
  await assert.rejects(setup(417, { exc_type: 'ValidationError', _server_messages: JSON.stringify([JSON.stringify({ message: 'Select a <b>branch</b> before saving.' })]) }), /Select a branch before saving/);
});
test('CSRF errors explain refreshing rather than missing permission', async () => {
  await assert.rejects(setup(403, { exc_type: 'CSRFTokenError' }), /Refresh the page/);
});
test('unexpected server errors do not display raw tracebacks', async () => {
  await assert.rejects(setup(500, { exc_type: 'DatabaseError', exception: 'private-server-detail', _server_messages: 'malformed' }), error => !error.message.includes('private-server-detail') && error.message.includes('try again'));
});
