<script setup>
defineProps({ rows: { type: Array, default: () => [] }, format: { type: Function, required: true } });
</script>
<template>
  <section class="stock-recent-out"><h3>Recent Stock Out ›</h3><p>Each branch · item lines across last 4 dispatches</p><div class="stock-recent-table"><div class="stock-recent-head"><span>Br.</span><span>Recent Category</span><span>Items</span></div><div v-for="row in rows.slice(0, 20)" :key="row.warehouse + row.item_code" class="stock-recent-row"><span>{{ (row.warehouse || '—').slice(0, 2).toUpperCase() }}</span><span>{{ row.item_group || '—' }}</span><strong>{{ format(row.actual_qty) }}</strong></div><div v-if="!rows.length" class="stock-empty">No recent stock-out rows.</div></div></section>
</template>
