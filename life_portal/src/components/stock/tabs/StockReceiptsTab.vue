<script setup>
import { onMounted, proxyRefs, ref } from 'vue';
import { useStockReceipts } from '../../../composables/useStockReceipts';
import { stockAction } from '../../../api/stock';
import StockReceiptModal from '../modals/StockReceiptModal.vue';
const stock = proxyRefs(useStockReceipts());
const selected = ref(null);
const busy = ref(false);
const actionError = ref('');
const success = ref('');
onMounted(() => stock.load());
function open(row) { selected.value = row; actionError.value = ''; success.value = ''; }
async function submit({ mode, entry, employee, remarks, items }) {
  if (busy.value) return;
  busy.value = true; actionError.value = ''; success.value = '';
  try {
    const action = mode === 'discrepancy' ? 'submit_receipt_adjustment' : 'confirm_branch_receipt';
    const payload = { stock_entry: entry.name, received_by: employee, receipt_remarks: remarks,
      items: mode === 'discrepancy' ? items : items.map(({ row_name, received_qty }) => ({ row_name, received_qty })) };
    const result = await stockAction(action, payload);
    success.value = result.message || (mode === 'discrepancy' ? 'Discrepancy submitted for review.' : 'Receipt confirmed.');
    selected.value = null;
    await stock.load({ force: true });
  } catch (error) { actionError.value = error.message || 'Could not submit receipt.'; }
  finally { busy.value = false; }
}
</script>
<template>
  <section class="stock-panel">
    <div class="stock-panel-head"><div><h2>Branch Receipts</h2><p>Released transfers awaiting branch receipt confirmation.</p></div><button :disabled="stock.loading || busy" @click="stock.load({force:true})">{{stock.loading?'Loading…':'↻ Refresh'}}</button></div>
    <label class="stock-search">Search receipts<input v-model="stock.query" type="search" placeholder="Stock entry, warehouse, or status"></label>
    <p v-if="stock.error || (actionError && !selected)" class="stock-error">{{stock.error || actionError}}</p>
    <p v-if="success" role="status">{{success}}</p>
    <p v-if="stock.loading" class="stock-loading">Loading branch receipts…</p>
    <div class="stock-table-wrap"><table><thead><tr><th>Stock entry</th><th>Warehouse</th><th>Released</th><th>Released by</th><th>Items</th><th>Status</th><th>Actions</th><th>ERP</th></tr></thead><tbody><tr v-for="row in stock.rows" :key="row.name"><td>{{row.name}}</td><td>{{row.set_warehouse||'—'}}</td><td>{{String(row.posting_date||row.creation||'').slice(0,10)||'—'}}</td><td>{{row.released_by||'—'}}</td><td>{{(row.items||[]).length}}</td><td><span class="stock-status">{{row.workflow_state||row.status||'—'}}</span></td><td><button :disabled="busy" @click="open(row)">View / Confirm</button></td><td><a class="stock-document-link" :href="`/app/stock-entry/${encodeURIComponent(row.name)}`" target="_blank" rel="noopener">Open</a></td></tr><tr v-if="!stock.loading&&!stock.rows.length"><td colspan="8" class="stock-empty">No open branch receipts.</td></tr></tbody></table></div>
    <StockReceiptModal :open="!!selected" :entry="selected" :busy="busy" :error="actionError" @close="selected=null" @submit="submit" />
  </section>
</template>