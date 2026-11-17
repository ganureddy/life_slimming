<script setup>
import { onMounted, proxyRefs, watch } from 'vue';
import { useStockRequests } from '../../../composables/useStockRequests';

const stock = proxyRefs(useStockRequests());
onMounted(() => stock.load());
watch(() => stock.group, () => { stock.page = 1; stock.load({ force: true }); });
function reject(row) {
  const remarks = window.prompt(`Reason for rejecting ${row.name}:`);
  if (remarks?.trim()) stock.decide(row, 'reject', remarks.trim());
}
</script>

<template>
  <section class="stock-panel">
    <div class="stock-panel-head"><div><h2>Requests &amp; Approvals</h2><p>Material requests from your authorized Stock Dashboard scope.</p></div><button :disabled="stock.loading" @click="stock.load({ force: true })">{{ stock.loading ? 'Loading…' : '↻ Refresh' }}</button></div>
    <p v-if="stock.error" class="stock-error">{{ stock.error }}</p>
    <div class="stock-cards compact"><button v-for="[key,label] in [['all','All'],['pending','Pending'],['approved','Approved'],['released','Released'],['rejected','Rejected']]" :key="key" :class="{selected:stock.group===key}" @click="stock.group=key"><span>{{ label }}</span><strong>{{ key === 'all' ? stock.rows.length : stock.counts[key] || 0 }}</strong></button></div>
    <label class="stock-search">Search requests<input v-model="stock.query" type="search" placeholder="Request number, branch, or status"></label>
    <p v-if="stock.loading" class="stock-loading">Loading material requests…</p>
    <div class="stock-table-wrap"><table><thead><tr><th>Request</th><th>Requested</th><th>Branch / target</th><th>Request type</th><th>Items</th><th>Status</th><th v-if="stock.context?.is_ho">Actions</th></tr></thead><tbody><tr v-for="row in stock.filteredRows" :key="row.name"><td>{{ row.name }}<small>{{ row.title || '' }}</small></td><td>{{ String(row.transaction_date || row.creation || '').slice(0, 10) || '—' }}</td><td>{{ row.set_warehouse || row.branch || '—' }}</td><td>{{ row.custom_stock_request_type || row.material_request_type || '—' }}</td><td>{{ (row.items || []).length }}</td><td><span class="stock-status">{{ row.workflow_state || row.status || '—' }}</span></td><td v-if="stock.context?.is_ho"><button v-if="row._group==='pending'" :disabled="stock.busy" @click="stock.decide(row,'approve')">Approve requested qty</button><button v-if="row._group==='pending'" :disabled="stock.busy" @click="reject(row)">Reject</button><span v-if="row._group!=='pending'">—</span></td></tr><tr v-if="!stock.loading && !stock.filteredRows.length"><td :colspan="stock.context?.is_ho?7:6" class="stock-empty">No requests match the filters.</td></tr></tbody></table></div>
  </section>
</template>
