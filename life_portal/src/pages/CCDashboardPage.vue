<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { ccCall } from '../api/cc';
import { dateRange, maskPhone } from '../lib/cc';
import CCDataTable from '../components/cc/CCDataTable.vue';
import CCPager from '../components/cc/CCPager.vue';
import '../styles/cc.css';
const [today] = dateRange('today');
const from = ref(today), to = ref(today), mode = ref('created'), query = ref('');
const rows = ref([]), total = ref(0), page = ref(1), more = ref(false), searching = ref(false), scoped = ref(false);
const loading = ref(false), error = ref(''), applied = ref('');
const dialog = ref(null), detail = ref(null), detailLoading = ref(false), detailError = ref('');
let controller, detailController, generation = 0, detailGeneration = 0;
const columns = [
  { key: 'name', label: 'Lead ID' }, { key: 'lead_name', label: 'Client' },
  { key: 'mobile_no', label: 'Phone', value: r => maskPhone(r.mobile_no) },
  { key: 'branch', label: 'Branch', value: r => r.branch || r.lead_assign_to_branch },
  { key: 'lead_owner', label: 'Agent' }, { key: 'custom_cc_sub_status', label: 'Status', value: r => r.custom_cc_sub_status || r.status },
  { key: 'custom_appointment_date_and_time', label: 'Appointment' }, { key: 'custom_next_followup_date', label: 'Next follow-up' },
];
const pages = computed(() => searching.value ? page.value + (more.value ? 1 : 0) : Math.max(1, Math.ceil(total.value / 40)));
// Capture applied filters so changing a draft cannot mix pagination cohorts.
let filters = {};
function apply() {
  error.value = '';
  if (query.value.trim() && query.value.trim().length < 2) { error.value = 'Enter at least two characters to search.'; return; }
  if (!query.value.trim() && (!from.value || !to.value || from.value > to.value)) { error.value = 'Choose a valid date range.'; return; }
  filters = query.value.trim() ? { query: query.value.trim() } : { from_date: from.value, to_date: to.value, date_mode: mode.value, page_size: 40 };
  searching.value = !!filters.query;
  applied.value = filters.query ? 'Search across permitted history: ' + filters.query : `${from.value} → ${to.value} · ${mode.value}`;
  load(1);
}
async function load(nextPage) {
  const token = ++generation; controller?.abort(); controller = new AbortController();
  page.value = nextPage; loading.value = true; error.value = ''; rows.value = []; total.value = 0;
  try {
    const data = await ccCall('cc_get_leads', { ...filters, start: (nextPage - 1) * (searching.value ? 20 : 40) }, controller.signal);
    if (token !== generation) return;
    rows.value = data.rows || []; total.value = data.total || 0; more.value = !!data.more; scoped.value = !!data.scoped_to_owner;
  } catch (e) { if (token === generation && e.name !== 'AbortError') error.value = e.message; }
  finally { if (token === generation) loading.value = false; }
}
async function openDetail(row) {
  detailController?.abort(); detailController = new AbortController(); const token = ++detailGeneration;
  detail.value = row; detailError.value = ''; detailLoading.value = true; dialog.value.showModal();
  try {
    const data = await ccCall('cc_get_leads', { query: row.name, detail: 1 }, detailController.signal);
    if (token !== detailGeneration) return;
    const found = data.rows?.find(item => item.name === row.name);
    if (!found) throw new Error('This lead is no longer available to your account.');
    detail.value = found;
  } catch (e) { if (token === detailGeneration && e.name !== 'AbortError') detailError.value = e.message; }
  finally { if (token === detailGeneration) detailLoading.value = false; }
}
function closeDetail() { detailGeneration++; detailController?.abort(); dialog.value.close(); }
onMounted(apply);
onUnmounted(() => { generation++; detailGeneration++; controller?.abort(); detailController?.abort(); });
</script>
<template>
<section class="cc-native">
  <header><div><h1>CC Dashboard</h1><p class="cc-note">Native Vue preview · Leads, appointments and follow-ups</p></div><div class="cc-actions"><RouterLink :to="{name:'ccvisit-native'}">Visit Report preview</RouterLink><RouterLink :to="{name:'leads'}">Current dashboard</RouterLink></div></header>
  <form class="cc-filters" @submit.prevent="apply">
    <label>From<input v-model="from" type="date"></label><label>To<input v-model="to" type="date"></label>
    <label>Date basis<select v-model="mode"><option value="created">Created</option><option value="updated">Updated</option><option value="appointment">Appointments</option><option value="followup">Follow-ups</option><option value="posting">Posting date</option></select></label>
    <label>Search all history<input v-model="query" type="search" placeholder="Name, Lead ID or phone"></label><button type="submit">Apply</button>
  </form>
  <p v-if="error" class="cc-error" role="alert">{{ error }} <button @click="load(page)">Retry</button></p>
  <p role="status">{{ loading ? 'Loading leads…' : searching ? rows.length + ' matches on this page' : total + ' matching leads' }} · {{ applied }}<span v-if="scoped"> · Your assigned leads</span></p>
  <CCDataTable :columns="columns" :rows="rows" :busy="loading"><template #actions="{row}"><button @click="openDetail(row)">Details</button><RouterLink :to="{name:'cc-appointments',query:{lead:row.name}}">Book / reschedule</RouterLink><RouterLink :to="{name:'convox-history',params:{leadId:row.name}}">Calls</RouterLink></template></CCDataTable>
  <CCPager :page="page" :pages="pages" :busy="loading" @change="load" />
  <dialog ref="dialog" aria-labelledby="lead-title" @cancel.prevent="closeDetail">
    <template v-if="detail"><header><h2 id="lead-title">{{ detail.lead_name || detail.name }}</h2><button @click="closeDetail">Close</button></header>
      <p>{{ detail.name }} · {{ maskPhone(detail.mobile_no) }}</p><p v-if="detailLoading" role="status">Loading details…</p><p v-if="detailError" role="alert" class="cc-error">{{ detailError }}</p>
      <template v-if="!detailLoading && !detailError"><p>Stage: {{ detail.custom_cc_stage }} · {{ detail.custom_cc_sub_status }}</p><p>Next follow-up: {{ detail.custom_next_followup_date || 'Not scheduled' }}</p><p>Conclusion: {{ detail.custom_conclusion_remark || 'Not recorded' }}</p>
      <h3>Status history</h3><ul><li v-for="(event,index) in detail.workflow_hint?.legacy_events || []" :key="index">{{ event.at }} · {{ event.by }} · {{ event.from }} → {{ event.to }}</li></ul><p v-if="!detail.workflow_hint?.legacy_events?.length">No status changes recorded.</p></template>
      <p class="cc-note">Use the current dashboard for lead creation, contact edits and follow-up updates during migration.</p>
    </template>
  </dialog>
</section>
</template>
