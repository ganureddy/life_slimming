<script setup>
import { onMounted, proxyRefs } from 'vue';
import { useStockReport } from '../../../composables/useStockReport';

const stock = proxyRefs(useStockReport());
onMounted(() => stock.load());
</script>

<template>
  <section class="stock-panel">
    <div class="stock-panel-head"><div><h2>Stock Reports</h2><p>ERP Stock Balance with the same date filters and export workflow.</p></div><button :disabled="stock.loading" @click="stock.load({ force: true })">{{ stock.loading ? 'Running…' : 'Run report' }}</button></div>
    <div class="stock-report-controls"><label>From<input v-model="stock.from" type="date"></label><label>To<input v-model="stock.to" type="date"></label><label>Search<input v-model="stock.query" type="search" placeholder="Filter report rows"></label><button :disabled="!stock.visibleRows.length" @click="stock.exportCsv">Export CSV</button></div>
    <p v-if="stock.error" class="stock-error">{{ stock.error }}</p><p v-if="stock.loading" class="stock-loading">Running Stock Balance…</p>
    <div v-if="stock.columns.length" class="stock-table-wrap"><table><thead><tr><th v-for="column in stock.columns" :key="column.fieldname">{{ column.label || column.fieldname }}</th></tr></thead><tbody><tr v-for="(row,index) in stock.visibleRows" :key="row.name || index"><td v-for="column in stock.columns" :key="column.fieldname">{{ row[column.fieldname] ?? '—' }}</td></tr><tr v-if="!stock.visibleRows.length"><td :colspan="stock.columns.length" class="stock-empty">No report rows match the filters.</td></tr></tbody></table></div>
  </section>
</template>
