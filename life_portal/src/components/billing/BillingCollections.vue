<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { request } from '../../api/http';
import endpoints from '../../api/endpoints.json';
import { session } from '../../lib/session';
import { dateRange, indiaStamp } from '../../lib/cc';
import { billingBranches, collectionColumns, collectionRow, collectionTotals } from '../../lib/billing';

const props = defineProps({ bootstrap: Object, branch: String });
const [initialFrom, initialTo] = dateRange('month');
const from = ref(initialFrom), to = ref(initialTo), branch = ref('');
const branches = ref([]), headOffice = ref(false), ready = ref(false);
const rows = ref([]), busy = ref(false), error = ref('');
const totals = computed(() => collectionTotals(rows.value));
const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(value);
let controller, generation = 0;
async function call(id, args, signal) {
  const response = await request(endpoints[id], { args, signal, csrfToken: session.csrf_token });
  if (!response.message || response.message.error || response.message.ok === false) throw new Error(response.message?.error || 'No data returned. Please retry.');
  return response.message;
}
async function load() {
  const current = ++generation;
  controller?.abort();
  controller = new AbortController();
  const activeController = controller;
  const signal = activeController.signal;
  busy.value = true; error.value = ''; rows.value = [];
  const timeout = setTimeout(() => activeController.abort(), 45000);
  try {
    if (!ready.value) {
      const scope = billingBranches(props.bootstrap);
      if (signal.aborted) return;
      branches.value = scope.branches; headOffice.value = scope.headOffice;
      branch.value = props.branch==='' && scope.headOffice ? '' : scope.branches.includes(props.branch) ? props.branch : scope.selected; ready.value = true;
    }
    if (!from.value || !to.value || from.value > to.value) throw new Error('Choose a valid date range.');
    if (!headOffice.value && !branches.value.includes(branch.value)) throw new Error('No permitted branch is available for this account.');
    const result = await call('lifescc_billing_collections_report', { from_date: from.value, to_date: to.value, branch: branch.value }, signal);
    if (!Array.isArray(result.rows)) throw new Error('The collections response could not be read. Please retry.');
    if (current === generation) rows.value = result.rows.filter(row => !branch.value || row.branch === branch.value).map(collectionRow);
  } catch (failure) {
    if (current === generation) error.value = signal.aborted ? 'Billing request timed out. Please retry.' : failure.message;
  } finally {
    clearTimeout(timeout);
    if (current === generation) busy.value = false;
  }
}
function preset(period) {
  [from.value, to.value] = dateRange(period, indiaStamp().slice(0, 10));
  load();
}
onMounted(load);
onBeforeUnmount(() => { generation++; controller?.abort(); });
</script>

<template>
  <section class="billing-collections">
    <header class="billing-list-head"><div><h2>Collections — branch wise</h2><p>Billed, collected and outstanding amounts · GST / Non-GST</p></div><span class="billing-badge tone-green">{{ branch || 'Head Office — All branches' }}</span></header>
    <form class="billing-filter-bar" @submit.prevent="load"><label>From<input v-model="from" type="date" :disabled="busy" required></label><label>To<input v-model="to" type="date" :disabled="busy" required></label><button class="billing-primary" :disabled="busy">{{ busy?'Loading…':'Apply' }}</button><button type="button" :disabled="busy" @click="preset('today')">Today</button><button type="button" :disabled="busy" @click="preset('month')">Business month</button></form>
    <p class="billing-muted">Business month runs from the 6th through the 5th.</p>
    <div v-if="error" role="alert"><p>{{ error }}</p><button :disabled="busy" @click="load">Retry</button></div><p v-else-if="busy" class="billing-loading" role="status">Loading collections…</p>
    <template v-else>
      <div class="billing-kpis"><article class="billing-kpi tone-blue"><h3>Grand total</h3><strong>{{ money(totals.billed_total) }}</strong><p>{{ rows.length }} branch(es)</p></article><article class="billing-kpi tone-green"><h3>Collected</h3><strong>{{ money(totals.collected_total) }}</strong><p>Excl. GST {{ money(totals.collected_ex_gst) }}</p></article><article class="billing-kpi tone-red"><h3>Outstanding</h3><strong>{{ money(totals.outstanding) }}</strong></article><article class="billing-kpi tone-amber"><h3>Billed excl. GST</h3><strong>{{ money(totals.billed_ex_gst) }}</strong></article></div>
      <div v-if="!rows.length" class="billing-empty"><span aria-hidden="true">▦</span><h3>No collections found in this range.</h3><p>Try another date range or branch.</p></div>
      <section v-else class="billing-panel"><header class="billing-section-head"><h3>Branch-wise — billed vs collected vs outstanding</h3></header><div class="table-wrap" tabindex="0" aria-label="Branch collections" role="region"><table><thead><tr><th scope="col">Branch</th><th v-for="[key,label] in collectionColumns" :key="key" scope="col">{{ label }}</th></tr></thead><tbody><tr v-for="row in rows" :key="row.branch"><th scope="row">{{ row.branch }}</th><td v-for="[key] in collectionColumns" :key="key">{{ money(row[key]) }}</td></tr></tbody><tfoot><tr><th scope="row">Total</th><td v-for="[key] in collectionColumns" :key="key">{{ money(totals[key]) }}</td></tr></tfoot></table></div></section>
    </template>
  </section>
</template>
