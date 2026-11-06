const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../src/App.vue'), 'utf8');
const start = source.indexOf('const phoneRequested = ref(false);');
const end = source.indexOf('\nwatch(\n  () => route.meta.public', start);
function setup(isPublic, groups) {
  let update;
  const context = {
    route: {meta: {public: isPublic}}, visibleMenu: {value: groups},
    ref: value => ({value}),
    watch: (read, apply) => { update = () => apply(read()); update(); },
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end) + '\nthis.requested = () => phoneRequested.value;', context);
  return {context, update};
}
const ccMenu = [{items: [{id: 'leads'}]}];
test('sign-in and users without lead access do not request the phone chunk', () => {
  assert.equal(setup(true, ccMenu).context.requested(), false);
  assert.equal(setup(false, [{items: [{id: 'billing'}]}]).context.requested(), false);
});
test('authorized entry requests the phone and retains it across routes and session refreshes', () => {
  const {context, update} = setup(true, ccMenu);
  context.route.meta.public = false;
  update();
  assert.equal(context.requested(), true);
  context.visibleMenu.value = [];
  update();
  assert.equal(context.requested(), true);
  context.route.meta.public = true;
  update();
  assert.equal(context.requested(), true);
});
