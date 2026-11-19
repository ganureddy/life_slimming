<script setup>
import { computed, ref, watch } from 'vue';
import { stockAction } from '../../../api/stock';

const props = defineProps({
  branch: { type: String, default: '' },
  selected: { type: Object, default: null },
});
const emit = defineEmits(['select', 'error']);
const query = ref('');
const results = ref([]);
const loading = ref(false);
const searched = ref(false);
let sequence = 0;
const selectedLabel = computed(() => props.selected ? `${props.selected.patient_name || props.selected.name} · ${props.selected.name}` : '');
watch(() => props.selected?.name, () => { if (props.selected) { query.value = selectedLabel.value; results.value = []; } });

async function search() {
  const q = query.value.trim();
  const run = ++sequence;
  results.value = [];
  searched.value = false;
  if (q.length < 2) { loading.value = false; return; }
  loading.value = true;
  try {
    const digits = q.replace(/\D/g, '');
    const or_filters = [['name', 'like', `%${q}%`], ['patient_name', 'like', `%${q}%`]];
    if (digits.length >= 5) or_filters.push(['mobile', 'like', `%${digits}%`]);
    const response = await stockAction('invoke', {
      method: 'frappe.client.get_list',
      args: {
        doctype: 'Patient',
        fields: ['name', 'patient_name', 'mobile', 'branch_name', 'custom_branch', 'status'],
        filters: { status: ['!=', 'Disabled'] },
        or_filters,
        order_by: 'patient_name asc',
        limit_page_length: 50,
      },
    });
    if (run !== sequence) return;
    const branch = props.branch.trim().toLowerCase();
    results.value = (response.data || []).filter(row => !branch || `${row.branch_name || ''} ${row.custom_branch || ''}`.toLowerCase().includes(branch));
    searched.value = true;
  } catch (error) {
    if (run === sequence) emit('error', error?.message || 'Could not search branch clients.');
  } finally {
    if (run === sequence) loading.value = false;
  }
}
function choose(patient) {
  sequence += 1;
  loading.value = false;
  results.value = [];
  searched.value = false;
  query.value = `${patient.patient_name || patient.name} · ${patient.name}`;
  emit('select', patient);
}
function reset() { sequence += 1; query.value = ''; results.value = []; searched.value = false; emit('select', null); }
</script>

<template>
  <div class="stock-special-client-picker">
    <label class="stock-search">Search branch client
      <input v-model="query" type="search" autocomplete="off" placeholder="Client name, ID or mobile" @input="search" />
    </label>
    <p v-if="loading" class="stock-loading" role="status">Searching clients…</p>
    <div v-if="results.length" class="stock-special-client-results" role="listbox" aria-label="Matching clients">
      <button v-for="patient in results" :key="patient.name" type="button" class="stock-employee-option" @click="choose(patient)">
        <strong>{{ patient.patient_name || patient.name }}</strong> · {{ patient.name }} · {{ patient.mobile || 'No mobile' }}
      </button>
    </div>
    <p v-else-if="searched && !loading" class="stock-empty">No matching clients in the selected branch.</p>
    <div v-if="selected" class="stock-selected-client">
      <span>Selected: <strong>{{ selectedLabel }}</strong></span>
      <button type="button" @click="reset">Change client</button>
    </div>
  </div>
</template>

<style scoped>
.stock-special-client-picker{display:grid;gap:10px;min-width:0}
.stock-special-client-results{display:grid;max-height:240px;overflow:auto;border:1px solid #d9e7dd;border-radius:10px;background:#fff}
.stock-special-client-results button{text-align:left;padding:12px;border:0;border-bottom:1px solid #e8eee9;background:white;cursor:pointer}
.stock-special-client-results button:hover{background:#f1f8f3}
.stock-selected-client{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.stock-selected-client button{border:1px solid #d9e7dd;background:white;border-radius:7px;padding:7px 10px}
</style>