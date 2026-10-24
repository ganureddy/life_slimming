<script setup>
import { computed, onBeforeUnmount, ref } from 'vue';
const props = defineProps({ id: String, modelValue: String, options: { type: Array, default: () => [] }, placeholder: String, disabled: Boolean, remote: Boolean, busy: Boolean, error: String });
const emit = defineEmits(['update:modelValue', 'query', 'choose']);
const open = ref(false), index = ref(-1), root = ref(null);
let blurTimer;
const rows = computed(() => props.remote ? props.options : props.options.filter(row => !props.modelValue || !row.value || row.label.toLowerCase().includes(props.modelValue.toLowerCase())));
function focus() { clearTimeout(blurTimer); open.value = true; if (props.remote) emit('query', props.modelValue); }
function input(event) { index.value = -1; emit('update:modelValue', event.target.value); emit('choose', null); open.value = true; if (props.remote) emit('query', event.target.value); }
function choose(row) { emit('update:modelValue', row.displayValue ?? row.value); emit('choose', row); open.value = false; }
function blur() { blurTimer = setTimeout(() => { open.value = false; }, 120); }
function keydown(event) {
  if (event.key === 'Escape') open.value = false;
  if (['ArrowDown','ArrowUp'].includes(event.key)) { event.preventDefault(); open.value = true; index.value = Math.max(0, Math.min(rows.value.length-1, index.value+(event.key==='ArrowDown'?1:-1))); }
  if (event.key === 'Enter' && open.value && rows.value[index.value]) { event.preventDefault(); choose(rows.value[index.value]); }
}
onBeforeUnmount(() => clearTimeout(blurTimer));
</script>
<template>
  <div ref="root" class="report-search-select">
    <input :id="id" :value="modelValue" :placeholder="placeholder" :disabled="disabled" class="ref-input" autocomplete="off" role="combobox" :aria-expanded="open" :aria-controls="id+'-options'" @focus="focus" @input="input" @keydown="keydown" @blur="blur"><span class="report-select-arrow">▼</span>
    <div v-if="open && !disabled" :id="id+'-options'" role="listbox" class="report-select-options">
      <div v-if="busy" class="report-select-note" role="status">Loading…</div><div v-else-if="error" role="alert" class="report-select-note">{{ error }} <button type="button" @mousedown.prevent="emit('query',modelValue)">Retry</button></div>
      <template v-else><div v-for="(row,i) in rows" :key="row.value" role="option" :aria-selected="index===i" :class="{selected:index===i}" @mousedown.prevent="choose(row)">{{ row.label }}</div><div v-if="!rows.length" class="report-select-note">No results</div></template>
    </div>
  </div>
</template>
<style scoped>
.report-search-select{position:relative;width:100%;min-width:0}.report-search-select input{width:100%;height:34px;padding:0 36px 0 10px;font-size:11.5px;font-family:Inter,Segoe UI,Arial,sans-serif;border:1.5px solid #A5D6A7;border-radius:8px;outline:none;background:#fff;color:#152418;box-shadow:0 1px 2px rgba(15,61,30,.04)}.report-search-select input:disabled{border-color:#D7E4D9;background:#EEF4EF;cursor:not-allowed}.report-select-arrow{position:absolute;right:10px;top:10px;font-size:9px;color:#5F6F63;pointer-events:none}.report-select-options{position:absolute;top:100%;left:0;min-width:100%;max-height:260px;overflow:auto;background:white;border:1.5px solid #A5D6A7;border-radius:9px;box-shadow:0 8px 24px rgba(15,61,30,.16);z-index:1000}.report-select-options>div{padding:9px 14px;font-size:12px;cursor:pointer;color:#152418;white-space:normal}.report-select-options>div:hover,.report-select-options>div.selected{background:#E8F5E9}.report-select-note{color:#5F6F63!important}
</style>
