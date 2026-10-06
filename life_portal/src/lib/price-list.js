export const priceListTabs = [
  ['types', 'Therapy Types'],
  ['packages', 'Packages'],
  ['liferise', 'LIFErise Packages'],
];

export function splitPackages(rows) {
  return {
    packages: rows.filter(row => !/liferise/i.test(row.plan_name || '')),
    liferise: rows.filter(row => /liferise/i.test(row.plan_name || '')),
  };
}

export function priceListOffer(therapy, rules, today) {
  if (!therapy.item_code) return null;
  const matching = rules.filter(rule =>
    rule.item_code === therapy.item_code &&
    rule.apply_on === 'Item Code' &&
    (rule.price_or_product_discount || 'Price') === 'Price' &&
    (!rule.valid_from || String(rule.valid_from).slice(0, 10) <= today) &&
    (!rule.valid_upto || String(rule.valid_upto).slice(0, 10) >= today) &&
    (!Number(rule.min_qty) || Number(rule.min_qty) <= 1) &&
    (!Number(rule.max_qty) || Number(rule.max_qty) >= 1)
  ).sort((a, b) => Number(b.priority || 0) - Number(a.priority || 0));
  const rule = matching[0];
  if (!rule) return null;
  const base = Number(therapy.rate || 0);
  const rate = Number(rule.rate) > 0 ? Number(rule.rate)
    : Number(rule.discount_percentage) > 0 ? base * (1 - Number(rule.discount_percentage) / 100)
    : base - Number(rule.discount_amount || 0);
  return { name: rule.name, rate: Math.round(Math.max(0, rate) * 100) / 100 };
}

export function filterPriceRows(rows, query, offerOnly = false) {
  const term = query.trim().toLocaleLowerCase();
  return rows.filter(row => {
    const text = [row.therapy_type, row.healthcare_service_unit, row.plan_name, row.item_code]
      .join(' ').toLocaleLowerCase();
    return text.includes(term) && (!offerOnly || !!row.offer);
  });
}
