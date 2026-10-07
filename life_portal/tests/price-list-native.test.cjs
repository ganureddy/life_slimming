const { test } = require('node:test');
const assert = require('node:assert/strict');
const lib = import('../src/lib/price-list.js');

test('packages split into regular and LIFErise without losing records', async () => {
  const { splitPackages } = await lib;
  const rows = [{ plan_name: 'Hair Package' }, { plan_name: 'LIFErise Transformation' }, { plan_name: 'LifeRise Starter' }];
  const groups = splitPackages(rows);
  assert.equal(groups.packages.length, 1);
  assert.equal(groups.liferise.length, 2);
});

test('offers use active item rules for a single session and priority', async () => {
  const { priceListOffer } = await lib;
  const therapy = { item_code: 'T-1', rate: 1000 };
  const rules = [
    { name: 'old', item_code: 'T-1', apply_on: 'Item Code', price_or_product_discount: 'Price', rate: 1, valid_upto: '2026-10-04', priority: 9 },
    { name: 'bulk', item_code: 'T-1', apply_on: 'Item Code', price_or_product_discount: 'Price', rate: 1, min_qty: 2, priority: 8 },
    { name: 'low', item_code: 'T-1', apply_on: 'Item Code', price_or_product_discount: 'Price', discount_percentage: 10, priority: 1 },
    { name: 'high', item_code: 'T-1', apply_on: 'Item Code', price_or_product_discount: 'Price', discount_amount: 125, priority: 2 },
  ];
  assert.deepEqual(priceListOffer(therapy, rules, '2026-10-05'), { name: 'high', rate: 875 });
  assert.equal(priceListOffer({ item_code: 'T-2', rate: 1000 }, rules, '2026-10-05'), null);
});

test('therapy search includes category and offer filter', async () => {
  const { filterPriceRows } = await lib;
  const rows = [{ therapy_type: 'Laser', healthcare_service_unit: 'Hair - LSACPL', offer: { rate: 500 } }, { therapy_type: 'Facial', healthcare_service_unit: 'Skin - LSACPL' }];
  assert.equal(filterPriceRows(rows, 'hair', true).length, 1);
  assert.equal(filterPriceRows(rows, 'skin', true).length, 0);
  assert.equal(filterPriceRows(rows, 'skin').length, 1);
});
