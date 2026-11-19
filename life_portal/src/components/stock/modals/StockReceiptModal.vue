<script setup>
import { computed, reactive, ref, watch } from 'vue';
const props = defineProps({ open: Boolean, entry: { type: Object, default: null }, busy: Boolean, error: { type: String, default: '' } });
const emit = defineEmits(['close', 'submit']);
const employee = ref('');
const remarks = ref('');
const mode = ref('confirm');
const quantities = reactive({});
const validation = ref('');
const items = computed(() => props.entry?.items || []);
const hasDifference = computed(() => items.value.some(item => {
  const q = quantities[item.name];
  return q && (Number(q.missing) > 0 || Number(q.damaged) > 0 || Number(q.received) !== Number(item.qty || 0));
}));
watch(() => [props.open, props.entry?.name], () => {
  if (!props.open) return;
  employee.value = ''; remarks.value = ''; mode.value = 'confirm'; validation.value = '';
  Object.keys(quantities).forEach(key => delete quantities[key]);
  items.value.forEach(item => { quantities[item.name] = { received: Number(item.qty || 0), missing: 0, damaged: 0 }; });
}, { immediate: true });
function submit() {
  validation.value = '';
  if (!employee.value.trim()) { validation.value = 'Receiving employee ID is required.'; return; }
  if (!items.value.length) { validation.value = 'This stock entry has no item lines.'; return; }
  const rows = [];
  for (const item of items.value) {
    const q = quantities[item.name];
    const released = Number(item.qty || 0);
    const received = Number(q?.received);
    const missing = Number(q?.missing);
    const damaged = Number(q?.damaged);
    if (![received, missing, damaged].every(Number.isFinite) || [received, missing, damaged].some(n => n < 0)) {
      validation.value = `Enter valid non-negative quantities for ${item.item_name || item.item_code}.`; return;
    }
    if (received + missing + damaged > released + 0.00001) {
      validation.value = `Total quantities exceed released quantity for ${item.item_name || item.item_code}.`; return;
    }
    if (mode.value === 'confirm' && (received !== released || missing || damaged)) {
      validation.value = 'Use Discrepancy mode for missing, damaged, or short-received items.'; return;
    }
    rows.push({ row_name: item.name, received_qty: received, missing_qty: missing, damaged_qty: damaged,
      discrepancy_remarks: missing || damaged || received < released ? remarks.value.trim() : '' });
  }
  if (mode.value === 'discrepancy') {
    if (!hasDifference.value) { validation.value = 'Enter a quantity difference to report.'; return; }
    if (!remarks.value.trim()) { validation.value = 'Discrepancy remarks are required.'; return; }
  }
  emit('submit', { mode: mode.value, entry: props.entry, employee: employee.value.trim(), remarks: remarks.value.trim(), items: rows });
}
</script>
<template>
  <div v-if="open && entry" class="stock-modal-backdrop" @click.self="!busy && emit('close')">
    <section class="stock-item-modal receipt-modal" role="dialog" aria-modal="true" aria-labelledby="receipt-modal-title">
      <header class="receipt-head"><div><h2 id="receipt-modal-title">Branch Receipt · {{ entry.name }}</h2><p>{{ entry.set_warehouse || 'Warehouse not specified' }}</p></div><button type="button" :disabled="busy" @click="emit('close')">✕ Close</button></header>
      <div class="receipt-mode"><button type="button" :class="{active:mode==='confirm'}" :disabled="busy" @click="mode='confirm'">Confirm full receipt</button><button type="button" :class="{active:mode==='discrepancy'}" :disabled="busy" @click="mode='discrepancy'">Report discrepancy</button></div>
      <div class="receipt-scroll"><table class="receipt-table"><thead><tr><th>Item</th><th>Released</th><th>Received</th><th v-if="mode==='discrepancy'">Missing</th><th v-if="mode==='discrepancy'">Damaged</th></tr></thead><tbody><tr v-for="item in items" :key="item.name"><td><strong>{{ item.item_name || item.item_code }}</strong><small>{{ item.item_code }}</small></td><td>{{ item.qty }}</td><td><input v-model.number="quantities[item.name].received" type="number" min="0" step="any" :disabled="busy || mode==='confirm'" :aria-label="`Received quantity for ${item.item_code}`"></td><td v-if="mode==='discrepancy'"><input v-model.number="quantities[item.name].missing" type="number" min="0" step="any" :disabled="busy" :aria-label="`Missing quantity for ${item.item_code}`"></td><td v-if="mode==='discrepancy'"><input v-model.number="quantities[item.name].damaged" type="number" min="0" step="any" :disabled="busy" :aria-label="`Damaged quantity for ${item.item_code}`"></td></tr></tbody></table></div>
      <div class="receipt-fields"><label>Receiving employee ID <span>*</span><input v-model.trim="employee" placeholder="Employee ID" :disabled="busy"></label><label>Remarks <span v-if="mode==='discrepancy'">*</span><textarea v-model="remarks" rows="2" :disabled="busy" placeholder="Receipt or discrepancy remarks"></textarea></label></div>
      <p v-if="validation || error" class="stock-error" role="alert">{{ validation || error }}</p>
      <footer class="receipt-actions"><button type="button" :disabled="busy" @click="emit('close')">Cancel</button><button type="button" class="stock-primary" :disabled="busy" @click="submit">{{ busy ? 'Submitting…' : mode==='discrepancy' ? 'Submit for Stock Manager review' : 'Confirm receipt' }}</button></footer>
    </section>
  </div>
</template>
<style scoped>
.receipt-modal{width:min(950px,96vw);max-height:92vh;overflow:auto;background:#fff;padding:22px;border-radius:14px}.receipt-head,.receipt-actions{display:flex;justify-content:space-between;align-items:center;gap:12px}.receipt-head h2{margin:0}.receipt-head p{color:#687b70;margin:5px 0}.receipt-mode{display:flex;gap:8px;margin:16px 0}.receipt-mode button{border:1px solid #c9d9ce;background:#f8fbf9;border-radius:8px;padding:10px}.receipt-mode .active{background:#165b3b;color:white}.receipt-scroll{overflow-x:auto}.receipt-table{width:100%;border-collapse:collapse}.receipt-table th,.receipt-table td{padding:10px;border-bottom:1px solid #e4ece6;text-align:left}.receipt-table small{display:block;color:#728478}.receipt-table input{width:100px;max-width:100%;padding:8px;border:1px solid #d2ddd5;border-radius:6px}.receipt-fields{display:grid;grid-template-columns:1fr 2fr;gap:12px;margin:18px 0}.receipt-fields label{display:grid;gap:6px}.receipt-fields input,.receipt-fields textarea{padding:10px;border:1px solid #d2ddd5;border-radius:8px}.receipt-fields span{color:#b53b3b}.receipt-actions{justify-content:flex-end}.receipt-actions button{padding:10px 16px;border-radius:8px;border:1px solid #d2ddd5}.receipt-actions .stock-primary{background:#165b3b;color:#fff}@media(max-width:650px){.receipt-fields{grid-template-columns:1fr}.receipt-modal{padding:14px}}
</style>