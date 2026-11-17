<script setup>
defineProps({ lastRequest: String, lowCount: Number, rows: { type: Array, default: () => [] }, format: { type: Function, required: true } });
const emit = defineEmits(['search']);
</script>
<template>
  <h3 class="stock-section-label">Stock Updates</h3>
  <div class="stock-updates"><div><span>Last Material Request</span><strong>{{ lastRequest || '—' }}</strong></div><div><span>Last Stock Received</span><strong>—</strong></div><div><span>Low / Out of Stock Items</span><strong>{{ lowCount }}</strong></div></div>
  <div class="stock-low-list" v-if="rows.length"><button v-for="row in rows.slice(0,8)" :key="row.warehouse + row.item_code" @click="emit('search', row.item_code)"><span>{{ row.item_name || row.item_code }}</span><strong>{{ format(row.actual_qty) }}</strong></button></div>
</template>
