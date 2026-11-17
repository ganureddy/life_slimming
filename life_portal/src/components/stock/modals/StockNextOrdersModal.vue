<script setup>
import { computed } from 'vue';
const props = defineProps({ open: Boolean, orders: { type: Array, default: () => [] }, loading: Boolean });
const emit = defineEmits(['close', 'refresh']);
const pending = computed(() => props.orders.filter(row => Number(row.docstatus) !== 2 && Number(row.per_received || 0) < 100));
</script>
<template>
  <div v-if="open" class="stock-modal-backdrop" @click.self="emit('close')"><section class="stock-item-modal stock-toolbar-modal" role="dialog" aria-modal="true" aria-label="Next order list">
    <div class="stock-panel-head"><div><h2>🛒 Next Order List</h2><p>Purchase orders not fully received (loaded procurement records)</p></div><div><button type="button" :disabled="loading" @click="emit('refresh')">↻ Refresh</button><button type="button" @click="emit('close')">× Close</button></div></div>
    <p v-if="loading" class="stock-loading">Loading purchase orders…</p>
    <div class="stock-table-wrap"><table><thead><tr><th>Purchase Order</th><th>Supplier</th><th>Date</th><th>Received</th><th>Status</th></tr></thead><tbody>
      <tr v-for="r in pending" :key="r.name"><td><a :href="`/app/purchase-order/${encodeURIComponent(r.name)}`" target="_blank" rel="noopener">{{ r.name }}</a></td><td>{{ r.supplier_name || r.supplier }}</td><td>{{ r.transaction_date || '—' }}</td><td>{{ r.per_received || 0 }}%</td><td>{{ r.status }}</td></tr>
      <tr v-if="!pending.length && !loading"><td colspan="5" class="stock-empty">No unreceived purchase orders in the loaded records.</td></tr>
    </tbody></table></div>
  </section></div>
</template>