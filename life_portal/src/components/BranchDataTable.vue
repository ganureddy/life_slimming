<script setup>
defineProps({ rows: Array, columns: Array, caption: String });
function display(value, kind) {
  if (value === null || value === undefined || value === '') return '—';
  if (kind === 'money') return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value));
  return value;
}
</script>
<template>
  <div class="branch-table" tabindex="0" :aria-label="caption">
    <table><caption>{{ caption }}</caption><thead><tr><th v-for="c in columns" :key="c.key" scope="col">{{ c.label }}</th></tr></thead>
      <tbody><tr v-for="(row, i) in rows || []" :key="row.id || i"><td v-for="c in columns" :key="c.key">{{ display(row[c.key], c.kind) }}</td></tr>
      <tr v-if="!rows?.length"><td :colspan="columns.length">No records returned for this selection.</td></tr></tbody>
    </table>
  </div>
</template>
