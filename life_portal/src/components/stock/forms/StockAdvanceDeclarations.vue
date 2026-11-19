<script setup>
const props = defineProps({ modelValue: { type: Object, required: true }, disabled: Boolean });
const emit = defineEmits(['update:modelValue']);
const options = [
  ['cluster', 'Sales Cluster Head approval has been obtained'],
  ['stock', 'Requested items are unavailable at the branch'],
  ['records', 'Client and treatment records will be maintained'],
  ['responsibility', 'Branch accepts stock handling responsibility'],
];
function change(key, checked) { emit('update:modelValue', { ...props.modelValue, [key]: checked }); }
</script>
<template>
  <fieldset class="stock-advance-declarations" :disabled="disabled">
    <legend>Advance Material Request declarations</legend>
    <label v-for="[key, title] in options" :key="key">
      <input type="checkbox" :checked="Boolean(modelValue[key])" @change="change(key, $event.target.checked)" />
      <span>{{ title }}</span>
    </label>
  </fieldset>
</template>
<style scoped>
.stock-advance-declarations{display:grid;gap:12px;border:1px solid #d9e7dd;border-radius:12px;padding:16px;min-width:0}
.stock-advance-declarations legend{font-weight:700;color:#165b3b;padding:0 6px}
.stock-advance-declarations label{display:flex;align-items:flex-start;gap:10px}
.stock-advance-declarations input{margin-top:3px;accent-color:#165b3b}
</style>