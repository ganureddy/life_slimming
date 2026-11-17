<script setup>
import { computed, ref } from 'vue';
const props = defineProps({ open: Boolean, rows: { type: Array, default: () => [] } });
const emit = defineEmits(['close','select']);
const query = ref('');
const matches = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return props.rows.slice(0, 20);
  return props.rows.filter(row => `${row.item_name || ''} ${row.item_code || ''} ${row.warehouse || ''} ${row.item_group || ''}`.toLowerCase().includes(q)).slice(0, 20);
});
</script>
<template>
  <div v-if="open" class="stock-modal-backdrop" @click.self="emit('close')"><section class="stock-search-client-modal stock-item-modal" role="dialog" aria-modal="true"><header><div><h2>🔍 Search Client / Stock</h2><p>Search loaded stock, item, warehouse, or category records.</p></div><button @click="emit('close')">× Close</button></header><input v-model="query" autofocus class="stock-modal-search" placeholder="Search client, request, item, code, or warehouse…"><div class="stock-modal-results"><button v-for="row in matches" :key="row.warehouse + row.item_code" @click="emit('select', row)"><strong>{{ row.item_name || row.item_code }}</strong><span>{{ row.item_code }} · {{ row.warehouse || '—' }} · {{ row.item_group || '—' }}</span><b>{{ row.actual_qty ?? 0 }}</b></button><p v-if="!matches.length" class="stock-empty">No matching records found.</p></div></section></div>
</template>
