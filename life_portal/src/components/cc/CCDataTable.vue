<script setup>
defineProps({ columns: Array, rows: Array, busy: Boolean, rowKey: { type: String, default: 'name' } });
</script>
<template>
  <div class="cc-table" tabindex="0" aria-label="Report table" :aria-busy="busy">
    <table><thead><tr><th v-for="column in columns" :key="column.key" scope="col">{{ column.label }}</th><th v-if="$slots.actions" scope="col">Actions</th></tr></thead>
      <tbody><tr v-for="(row, index) in rows" :key="row[rowKey] || index"><td v-for="column in columns" :key="column.key">{{ column.value ? column.value(row) : row[column.key] }}</td><td v-if="$slots.actions"><slot name="actions" :row="row" /></td></tr>
        <tr v-if="!rows.length"><td :colspan="columns.length + ($slots.actions ? 1 : 0)">{{ busy ? 'Loading…' : 'No records match this selection.' }}</td></tr></tbody>
    </table>
  </div>
</template>
