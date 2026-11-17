<script setup>
import { ref, watch } from 'vue';
import { stockAction } from '../../../api/stock';
const props = defineProps({ open: Boolean });
const emit = defineEmits(['close']);
const query = ref('');
const rows = ref([]);
const loading = ref(false);
const error = ref('');
let sequence = 0;
watch(() => props.open, open => { if (!open) { sequence++; loading.value = false; } });
async function search() {
  const q = query.value.trim();
  if (q.length < 2) { error.value = 'Enter at least two characters.'; return; }
  const id = ++sequence;
  loading.value = true; error.value = ''; rows.value = [];
  try {
    // Item Price is the official ERPNext price list source; no Purchase Invoice Item permissions required.
    const result = await stockAction('invoke', { method: 'frappe.client.get_list', args: {
      doctype: 'Item Price',
      fields: ['name', 'item_code', 'item_name', 'price_list', 'price_list_rate', 'currency', 'uom', 'valid_from', 'valid_upto'],
      filters: { buying: 1 },
      or_filters: [['item_code', 'like', `%${q}%`], ['item_name', 'like', `%${q}%`]],
      order_by: 'modified desc', limit_page_length: 100,
    }});
    if (id === sequence) rows.value = result.data || [];
  } catch (e) { if (id === sequence) error.value = e.message || 'Could not load buying prices.'; }
  finally { if (id === sequence) loading.value = false; }
}
</script>
<template>
  <div v-if="open" class="stock-modal-backdrop" @click.self="emit('close')">
    <section class="stock-item-modal stock-toolbar-modal" role="dialog" aria-modal="true" aria-label="Check buying price">
      <div class="stock-panel-head"><div><h2>Check Buying Price</h2><p>ERPNext buying price lists</p></div><button type="button" @click="emit('close')">× Close</button></div>
      <form class="stock-form-grid" @submit.prevent="search">
        <label>Item code or item name<input v-model="query" placeholder="Enter at least 2 characters" autocomplete="off"></label>
        <button class="stock-primary" type="submit" :disabled="loading">{{ loading ? 'Searching…' : 'Search' }}</button>
      </form>
      <p v-if="error" class="stock-error" role="alert">{{ error }}</p>
      <p v-if="loading" class="stock-loading" role="status">Loading buying prices…</p>
      <div v-if="rows.length" class="stock-table-wrap"><table><thead><tr><th>Item</th><th>Price list</th><th>Rate</th><th>UOM</th><th>Valid from</th></tr></thead><tbody>
        <tr v-for="r in rows" :key="r.name"><td><strong>{{ r.item_name || r.item_code }}</strong><small>{{ r.item_code }}</small></td><td>{{ r.price_list }}</td><td>{{ r.currency }} {{ Number(r.price_list_rate || 0).toLocaleString('en-IN', {maximumFractionDigits:2}) }}</td><td>{{ r.uom || '—' }}</td><td>{{ r.valid_from || '—' }}</td></tr>
      </tbody></table></div>
      <p v-else-if="!loading && !error && query.trim().length >= 2" class="stock-empty">No buying price list records returned. This is not the last Purchase Invoice rate.</p>
    </section>
  </div>
</template>