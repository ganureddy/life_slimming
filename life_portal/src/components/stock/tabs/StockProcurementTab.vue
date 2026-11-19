<script setup>
import { onMounted, proxyRefs } from 'vue';
import { useStockProcurement } from '../../../composables/useStockProcurement';
const stock = proxyRefs(useStockProcurement());
const money = value => Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 });
onMounted(() => stock.load());
</script>

<template>
  <section class="stock-panel">
    <div class="stock-panel-head"><div><h2>Purchase Orders, Receipts &amp; Invoices</h2><p>Current ERP purchasing documents, loaded once for this workspace.</p></div><button :disabled="stock.loading" @click="stock.load({ force: true })">{{ stock.loading ? 'Loading…' : '↻ Refresh' }}</button></div>
    <label class="stock-search">Filter purchasing documents<input v-model="stock.query" type="search" placeholder="Document, supplier, or status"></label><p v-if="stock.error" class="stock-error">{{ stock.error }}</p><p v-if="stock.loading" class="stock-loading">Loading purchasing records…</p>
    <section v-for="[doctype,title] in [['Purchase Order','Purchase Orders'],['Purchase Receipt','Purchase Receipts'],['Purchase Invoice','Purchase Invoices']]" :key="doctype" class="stock-intel-table"><h3>{{ title }} · {{ stock.matches(doctype).length }}</h3><div class="stock-table-wrap"><table><thead><tr><th>Document</th><th>Date</th><th>Supplier</th><th>Status</th><th>Amount</th><th v-if="doctype==='Purchase Invoice'">Outstanding</th><th>ERP</th></tr></thead><tbody><tr v-for="row in stock.matches(doctype)" :key="row.name"><td>{{ row.name }}</td><td>{{ String(row.transaction_date || row.posting_date || '').slice(0,10) || '—' }}</td><td>{{ row.supplier_name || row.supplier || '—' }}</td><td><span class="stock-status">{{ row.workflow_state || row.status || '—' }}</span></td><td>{{ row.currency || '' }} {{ money(row.grand_total) }}</td><td v-if="doctype==='Purchase Invoice'">{{ money(row.outstanding_amount) }}</td><td><a class="stock-document-link" :href="`/app/${doctype.toLowerCase().replaceAll(' ','-')}/${encodeURIComponent(row.name)}`" target="_blank" rel="noopener">Open</a></td></tr><tr v-if="!stock.loading && !stock.matches(doctype).length"><td :colspan="doctype==='Purchase Invoice'?7:6" class="stock-empty">No matching documents.</td></tr></tbody></table></div></section>
  </section>
</template>
