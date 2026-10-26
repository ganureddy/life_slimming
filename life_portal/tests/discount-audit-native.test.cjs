const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const page = fs.readFileSync(path.join(root, 'src/pages/DiscountAuditPage.vue'), 'utf8');
function setup(today) {
  const NativeDate = Date;
  class Clock extends NativeDate { constructor(...args) { super(...(args.length ? args : [today])); } }
  const script = page.split('<script setup>')[1].split('</script>')[0].replace(/^import .*;\n/gm, '');
  return vm.runInNewContext(script + '\n({businessRange,from,to,branch,status,level,search,reportArgs,xml,statusClass})', {
    Date: Clock, ref: value => ({value}), computed: fn => ({get value(){return fn();}}), watch(){}, onMounted(){}, onBeforeUnmount(){},
  });
}
test('Discount Audit preserves 6th-to-5th reporting periods across year boundaries', () => {
  for (const [now, offset, expected] of [
    ['2026-01-04T12:00:00',0,['2025-12-06','2026-01-05']],
    ['2026-01-06T12:00:00',0,['2026-01-06','2026-02-05']],
    ['2026-01-06T12:00:00',-1,['2025-12-06','2026-01-05']],
  ]) assert.deepEqual(Array.from(setup(now).businessRange(offset)), expected);
});
test('Discount Audit forwards every filter and retains numeric Excel cell types', () => {
  const s = setup('2026-10-15T12:00:00');
  Object.assign(s.from,{value:'2026-10-06'}); s.to.value='2026-11-05'; s.branch.value='Clinic A';
  s.status.value='Approved';s.level.value='L2';s.search.value=' INV-1 ';
  const args = s.reportArgs(3);
  assert.equal(args.page,3); assert.equal(args.page_length,20); assert.equal(args.search,'INV-1');
  assert.equal(args.branch,'Clinic A'); assert.equal(args.approval_status,'Approved'); assert.equal(args.approval_level,'L2');
  assert.equal(s.xml('<&"'), '&lt;&amp;&quot;'); assert.equal(s.statusClass('Pending Approval'),'pending');
  assert(page.includes("numeric.has(keys[col]) ? 'Number' : 'String'"));
  assert(!/portal_pages|<iframe|v-html|innerHTML|\beval\s*\(|new Function\s*\(/.test(page));
});
