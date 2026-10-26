const { test } = require('node:test');
const assert = require('node:assert/strict');
const { computed, ref } = require('../node_modules/vue');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const component = fs.readFileSync(path.join(__dirname, '../src/pages/Stores360NativePage.vue'), 'utf8');
const helpers = fs.readFileSync(path.join(__dirname, '../src/lib/record-index.js'), 'utf8').replaceAll('export ', '');
function setup(payload) {
  const context = { computed, data: ref(payload), clientMatches: ref([]), category: ref(''), stockType: ref(''), vendorFilter: ref(''), branch: ref(''), query: ref(''), today: new Date(2026, 9, 15) };
  context.vendors = computed(() => context.data.value?.suppliers || []);
  vm.createContext(context);
  const from = component.indexOf('const branches ='), to = component.indexOf('const totals =', from);
  vm.runInContext(helpers + '\n' + component.slice(component.indexOf('function localDate('), component.indexOf('const branches =')) + '\n' + component.slice(from, to) + '\nthis.stockRows = stockRows; this.clientById = clientById;', context);
  return context;
}
test('indexed stock calculations preserve inventory, forecast and supplier filters', () => {
  const context = setup({ items: [{ code: 'A', name: 'Item A', cat: 'Clinic', type: 'Stock', rl: 2 }, { code: 'B', name: 'Item B', rl: 0 }],
    suppliers: [{ code: 'V1', name: 'Vendor One', phone: '123' }], clients: [{ id: 'P1', name: 'Original Client' }],
    ho_stock: { A: 3 }, branch_stock: { A: { 'Branch A': 4 } }, po_ordered_month: { A: 5 },
    stock_requests: [{ item: 'A', reqDate: '2026-10-01', reqQty: 10, pendingQty: 2 }, { item: 'A', reqDate: '2026-09-01', reqQty: 4, pendingQty: 1 }],
    purchases: [{ item: 'A', vendor: 'V1' }], lifetime_purchases: [{ item: 'A', qty: 20, val: 100 }],
    dispatch: [{ item: 'A', qty: 6, val: 30 }], returns: [{ item: 'A', qty: 1 }], adjust: [{ item: 'A', qty: -1 }] });
  const row = context.stockRows.value[0];
  assert.equal(row.onHand, 7); assert.equal(row.openDemand, 3);
  assert.equal(row.currentMonthDemand, 10); assert.equal(row.lastMonthDemand, 4);
  assert.equal(row.avgMonthlyDemand, 7); assert.equal(row.quarterNeed, 35); assert.equal(row.suggestedQty, 28);
  assert.equal(row.lifetimePurchaseQty, 20); assert.equal(row.lifetimePurchaseWorth, 100);
  assert.equal(row.sentQty, 6); assert.equal(row.returnedQty, 1); assert.equal(row.adjustedQty, -1);
  context.vendorFilter.value = 'V1';
  assert.equal(context.stockRows.value.length, 1);
  context.branch.value = 'HO'; assert.equal(context.stockRows.value[0].onHand, 3);
  context.clientMatches.value = [{ id: 'P1', name: 'Search Client' }];
  assert.equal(context.clientById('P1').name, 'Original Client');
  context.data.value.ho_stock.A = 10;
  assert.equal(context.stockRows.value[0].onHand, 10, 'index updates must remain reactive');
});

test('a large movement dataset is indexed once and reused across filter changes', () => {
  let reads = 0;
  const requests = Array.from({ length: 10000 }, (_, i) => ({ get item() { reads++; return 'I' + (i % 1000); }, reqDate: '2026-10-01', reqQty: 1, pendingQty: 0 }));
  const context = setup({ items: Array.from({ length: 1000 }, (_, i) => ({ code: 'I' + i, name: 'Item ' + i })), stock_requests: requests });
  assert.equal(context.stockRows.value.length, 1000);
  assert.equal(reads, 10000, 'one pass through movements instead of one pass per item');
  context.query.value = 'Item 1';
  assert.equal(context.stockRows.value.length, 111);
  assert.equal(reads, 10000, 'text filters reuse the movement index');
});
