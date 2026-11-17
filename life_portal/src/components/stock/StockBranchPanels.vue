<script setup>
import { computed, ref } from 'vue';
const props = defineProps({ rows: { type: Array, default: () => [] }, format: { type: Function, required: true } });
const query = ref('');
const open = ref('');
const groups = computed(() => {
  const map = new Map();
  for (const row of props.rows) {
    const key = row.warehouse || 'Unassigned';
    if (!map.has(key)) map.set(key, { name:key, rows:[], qty:0 });
    const group = map.get(key); group.rows.push(row); group.qty += Number(row.actual_qty || 0);
  }
  const q = query.value.trim().toLowerCase();
  return [...map.values()].filter(group => !q || `${group.name} ${group.rows.map(row => `${row.item_code} ${row.item_name || ''}`).join(' ')}`.toLowerCase().includes(q));
});
</script>
<template>
  <section class="stock-branch-panels"><header><div><h2>Branch-Wise Stock Detail <span>{{ groups.length }}</span></h2><p>Stock grouped by authorized branch warehouse.</p></div><input v-model="query" type="search" placeholder="Search branch, item, code, category or unit…"></header>
    <article v-for="group in groups" :key="group.name" class="stock-branch-panel"><button class="stock-branch-toggle" @click="open = open === group.name ? '' : group.name"><span>🏢 <strong>{{ group.name }}</strong> <small>({{ group.rows.length }} stock rows · {{ format(group.qty) }} qty)</small></span><b>{{ open === group.name ? '▾' : '▸' }}</b></button><div v-if="open === group.name" class="stock-branch-rows"><div v-for="row in group.rows.slice(0,20)" :key="row.item_code + row.warehouse"><span>{{ row.item_name || row.item_code }}</span><small>{{ row.item_code }} · {{ row.item_group || '—' }}</small><strong>{{ format(row.actual_qty) }}</strong></div></div></article>
    <p v-if="!groups.length" class="stock-empty">No branch stock matches the filters.</p>
  </section>
</template>
