<script setup>
import { onMounted, proxyRefs } from 'vue';
import { useStockSuppliers } from '../../../composables/useStockSuppliers';
const stock = proxyRefs(useStockSuppliers());
onMounted(() => stock.load());
</script>
<template>
  <section class="stock-panel"><div class="stock-panel-head"><div><h2>Suppliers</h2><p>Supplier directory from ERP, loaded once per workspace.</p></div><button :disabled="stock.loading" @click="stock.load({force:true})">{{ stock.loading?'Loading…':'↻ Refresh' }}</button></div><label class="stock-search">Search supplier<input v-model="stock.query" type="search" placeholder="Supplier name, ID, email, or mobile"></label><p v-if="stock.error" class="stock-error">{{ stock.error }}</p><p v-if="stock.loading" class="stock-loading">Loading supplier directory…</p><div class="stock-table-wrap"><table><thead><tr><th>Supplier</th><th>Group</th><th>Type</th><th>Contact</th><th>Status</th><th>ERP</th></tr></thead><tbody><tr v-for="row in stock.rows" :key="row.name"><td>{{ row.supplier_name||row.name }}<small>{{ row.name }}</small></td><td>{{ row.supplier_group||'—' }}</td><td>{{ row.supplier_type||'—' }}</td><td>{{ row.email_id||row.mobile_no||'—' }}</td><td><span class="stock-status">{{ row.disabled?'Disabled':row.on_hold?'On hold':'Active' }}</span></td><td><a class="stock-document-link" :href="`/app/supplier/${encodeURIComponent(row.name)}`" target="_blank" rel="noopener">Open</a></td></tr><tr v-if="!stock.loading&&!stock.rows.length"><td colspan="6" class="stock-empty">No matching suppliers.</td></tr></tbody></table></div></section>
</template>
