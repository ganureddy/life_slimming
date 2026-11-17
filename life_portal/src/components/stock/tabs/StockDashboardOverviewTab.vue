<script setup>
import { onMounted, proxyRefs } from 'vue';
import { useStockDashboardOverview } from '../../../composables/useStockDashboardOverview';

const stock = proxyRefs(useStockDashboardOverview());
const format = value => Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 });
onMounted(() => stock.load());
</script>

<template>
  <section class="stock-panel">
    <div class="stock-welcome"><div><h2>{{ stock.context?.is_ho ? 'Head Office dashboard' : 'Branch stock dashboard' }}</h2><p>The current Stock Dashboard data is loaded once and shared across the dashboard view.</p></div><button :disabled="stock.loading" @click="stock.load({ force: true })">{{ stock.loading ? 'Loading…' : '↻ Refresh inventory' }}</button></div>
    <p v-if="stock.error" class="stock-error">{{ stock.error }}</p>
    <div class="stock-cards"><div><span>Distinct stocked items</span><strong>{{ format(stock.metrics.items) }}</strong></div><div><span>Total quantity on hand</span><strong>{{ format(stock.metrics.quantity) }}</strong></div><div><span>Zero stock rows</span><strong>{{ format(stock.metrics.zero) }}</strong></div><div><span>Low stock rows · ≤ 5</span><strong>{{ format(stock.metrics.low) }}</strong></div></div>
    <div class="stock-report-controls"><label>Branch<select v-model="stock.warehouse"><option value="">All Locations</option><option v-for="row in stock.warehouses" :key="row">{{ row }}</option></select></label><label>Category<select v-model="stock.category"><option value="">All Categories</option><option v-for="row in stock.categories" :key="row">{{ row }}</option></select></label><label>Status<select v-model="stock.status"><option value="">All</option><option>Zero Stock</option><option>Low Stock</option><option>Normal</option></select></label></div>
    <p v-if="stock.loading" class="stock-loading">Loading live stock rows…</p>
    <div v-else class="stock-table-wrap"><table><thead><tr><th>Item code</th><th>Item</th><th>Category</th><th>Warehouse</th><th>On hand</th><th>Projected</th></tr></thead><tbody><tr v-for="row in stock.visibleBins.slice(0, 500)" :key="row.warehouse + row.item_code"><td>{{ row.item_code }}</td><td>{{ row.item_name || row.item_code }}</td><td>{{ row.item_group || '—' }}</td><td>{{ row.warehouse }}</td><td>{{ format(row.actual_qty) }}</td><td>{{ format(row.projected_qty) }}</td></tr><tr v-if="!stock.visibleBins.length"><td colspan="6" class="stock-empty">No stock rows match the filters.</td></tr></tbody></table></div>
  </section>
</template>
