const path = require('node:path');
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(path.resolve(__dirname, '..', 'src/pages/ControlPage.vue'), 'utf8').split('<script setup>')[1].split('</script>')[0].replace(/^import .*;$/gm, '');
function setup(fail = false) {
  const calls = [];
  const session = { user: 'fixture', csrf_token: 'csrf', access_config: { BM: { groups: ['MAIN'], hide: ['two'], show: ['three'] } } };
  const context = {
    session, roleKey: {value:'IT'}, labels: { IT:'IT Admin', BM:'Branch Manager' }, groupRoles: { BM:['MAIN'] },
    menu: [{label:'MAIN',items:[{id:'one'},{id:'two'}]},{label:'OTHER',items:[{id:'three'}]}],
    ref: value => ({value}), computed: fn => ({get value(){return fn();}}), watch: (_, fn) => fn(),
    call: async (...args) => { calls.push(args); if(fail) throw new Error('Permission denied'); },
  };
  vm.createContext(context);
  vm.runInContext(source + '\n globalThis.panel = { selectedRole, selectedItems, selectedGroups, loadRole, selectAll, toggleGroup, save, error };', context);
  return { ...context, calls };
}
test('individual include and exclude permissions survive saving', async () => {
  const c = setup(); c.panel.selectedRole.value = 'BM'; c.panel.loadRole();
  assert.deepEqual(Array.from(c.panel.selectedItems.value), ['one','three']);
  await c.panel.save();
  const saved = JSON.parse(c.calls[0][1].fieldname.access_config);
  assert.deepEqual(saved.BM, {groups:['MAIN'],show:['three'],hide:['two']});
  assert.equal(c.calls[0][0], 'frappe.client.set_value');
  assert.equal(c.calls[0][2].csrfToken, 'csrf');
});
test('grant and revoke all retain the original configuration format', async () => {
  const c = setup(); c.panel.selectAll(true); await c.panel.save();
  assert.equal(c.session.access_config.IT.groups, 'ALL');
  c.panel.selectAll(false); await c.panel.save();
  assert.deepEqual(JSON.parse(JSON.stringify(c.session.access_config.IT)), {groups:[],show:[],hide:[]});
});
test('failed saves leave session permissions unchanged', async () => {
  const c = setup(true); const before = JSON.stringify(c.session.access_config);
  c.panel.selectAll(false); await c.panel.save();
  assert.equal(JSON.stringify(c.session.access_config), before);
  assert.equal(c.panel.error.value, 'Permission denied');
});
test('other portal roles cannot invoke a save', async () => {
  const c = setup(); c.roleKey.value = 'BM'; await c.panel.save();
  assert.equal(c.calls.length, 0);
});
