<script setup>
defineProps({
  rows: { type: Array, default: () => [] },
  format: { type: Function, required: true },
  title: { type: String, default: 'HO Stock Overview' },
});
function categoryRows(rows, category) {
  return rows.filter(row => String(row.item_group || '').toLowerCase() === category.toLowerCase()).slice(0, 6);
}
</script>
<template>
  <section class="stock-category-grid" aria-label="Stock category summaries">
    <article class="stock-category-card stock-overview-card">
      <h3>{{ title }}</h3><p><strong>{{ new Set(rows.map(row => row.item_code)).size }}</strong> item codes</p>
      <div class="stock-category-lines"><span>Monthly <b>{{ rows.filter(row => /monthly/i.test(row.item_group || '')).length }}</b></span><span>Consumable <b>{{ rows.filter(row => /consum/i.test(row.item_group || '')).length }}</b></span><span>Advance Stk <b>{{ rows.filter(row => /advance/i.test(row.item_group || '')).length }}</b></span></div>
      <small>Item-code counts. Advance: last 12 months; may overlap categories.</small>
    </article>
    <article v-for="category in [...new Set(rows.map(row => row.item_group).filter(Boolean))].slice(0, 7)" :key="category" class="stock-category-card">
      <h3>{{ category }}</h3>
      <div class="stock-category-lines"><span v-for="row in categoryRows(rows, category)" :key="row.warehouse + row.item_code"><span>{{ row.item_name || row.item_code }}</span><b>{{ format(row.actual_qty) }} {{ row.stock_uom || 'Nos' }}</b></span></div>
      <small>HO balance · stock units</small>
    </article>
  </section>
</template>
