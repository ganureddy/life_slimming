<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { billingCall, billingList } from '../api/billing';
import { indiaStamp } from '../lib/cc';
import { elapsedTargetDays, targetCycleRange, targetKpis } from '../lib/branch-target';
import '../styles/branch-target.css';

const [initialFrom, initialTo] = targetCycleRange();
const from = ref(initialFrom), to = ref(initialTo), preset = ref('this');
const branches = ref([]), branch = ref(''), loading = ref(false), error = ref(''), data = ref(null);
const branchLoading = ref(true), branchError = ref('');
let controller, mounted = true;
const tracker = computed(() => data.value?.daily || null);
const days = computed(() => elapsedTargetDays(tracker.value));
const maxBar = computed(() => Math.max(1, ...days.value.flatMap(day => [Number(day.got || 0), Number(day.req || 0)])));
const kpis = computed(() => targetKpis(tracker.value));
const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value || 0));
const compact = value => { const n = Number(value || 0); return Math.abs(n) >= 10000000 ? `₹${(n / 10000000).toFixed(2)} Cr` : Math.abs(n) >= 100000 ? `₹${(n / 100000).toFixed(2)} L` : money(n); };
const date = value => value ? String(value).slice(0, 10).split('-').reverse().join('/') : '—';

async function loadBranches() {
  branchLoading.value = true; branchError.value = '';
  try {
    const rows = await billingList('Branch', [['name', 'not in', ['Head Office', 'Testing Branch']]], ['name'], { limit: 1000, order: 'name asc' });
    if (!mounted) return;
    branches.value = rows.map(row => row.name);
    if (!branches.value.length) throw new Error('No permitted branch is available.');
    branch.value = branches.value[0];
    await load();
  } catch (failure) { if (mounted) branchError.value = failure.message; }
  finally { if (mounted) branchLoading.value = false; }
}
async function load() {
  if (!branch.value) { error.value = 'Choose a branch.'; return; }
  if (!from.value || !to.value || from.value > to.value) { error.value = 'Choose a valid date range.'; return; }
  controller?.abort(); const current = new AbortController(); controller = current;
  loading.value = true; error.value = ''; data.value = null;
  try {
    const result = await billingCall('branch_command_center', { branch: branch.value, from_date: from.value, to_date: to.value }, current.signal);
    if (mounted && controller === current) data.value = result;
  } catch (failure) { if (mounted && controller === current) error.value = failure.message; }
  finally { if (mounted && controller === current) loading.value = false; }
}
function selectPreset(value) { preset.value = value; [from.value, to.value] = targetCycleRange(value); load(); }
function apply() { preset.value = ''; load(); }
onMounted(loadBranches); onBeforeUnmount(() => { mounted = false; controller?.abort(); });
</script>

<template>
  <section class="branch-target">
    <header class="target-head"><div><span class="target-eyebrow">BRANCH HOME</span><h1>Target &amp; Realisation</h1><p>Daily net collections against the 6th–5th sales cycle</p></div></header>
    <form class="target-filters" @submit.prevent="apply"><label>Branch<select v-model="branch" :disabled="branchLoading || loading" @change="load"><option v-for="name in branches" :key="name" :value="name">{{ name }}</option></select></label><label>From<input v-model="from" type="date" required @change="preset='' "></label><label>To<input v-model="to" type="date" required @change="preset='' "></label><button type="submit" :disabled="loading || !branch">Apply</button><button type="button" :class="{selected:preset==='this'}" :disabled="loading || !branch" @click="selectPreset('this')">This Cycle</button><button type="button" :class="{selected:preset==='last'}" :disabled="loading || !branch" @click="selectPreset('last')">Last Cycle</button></form>
    <p v-if="branchLoading" role="status">Loading branches…</p><p v-if="branchError" class="target-error" role="alert">{{ branchError }} <button @click="loadBranches">Retry</button></p>
    <p v-if="loading" role="status">Loading target data…</p><p v-if="error" class="target-error" role="alert">{{ error }} <button @click="load">Retry</button></p>
    <template v-if="tracker">
      <div v-if="!tracker.days" class="target-note">Daily target tracking is unavailable for this branch.</div>
      <template v-else>
        <div class="target-kpis"><article v-for="[label,value] in kpis" :key="label"><strong>{{ typeof value==='number' && !/days|realisation/i.test(label) ? compact(value) : value }}</strong><span>{{ label }}</span></article></div>
        <section class="target-hero" :class="{good:tracker.is_closed?Number(tracker.pct)>=100:!!tracker.on_track}"><p>{{ tracker.is_closed?'Closed cycle':'To hit '+compact(tracker.target)+' by '+date(tracker.cycle_to) }} · {{ date(tracker.cycle_from) }} → {{ date(tracker.cycle_to) }}</p><strong v-if="tracker.is_closed">{{ tracker.pct }}% <small>of target</small></strong><strong v-else>{{ money(tracker.req_per_day) }} <small>/ day needed</small></strong><p v-if="tracker.is_closed">{{ compact(tracker.achieved) }} collected against {{ compact(tracker.target) }} · {{ tracker.hit_days }} of {{ tracker.total_days }} days hit</p><p v-else>{{ compact(tracker.gap) }} still to collect across {{ tracker.days_left }} days</p></section>
        <details class="target-section" open><summary>Pace check</summary><div class="target-pace"><template v-if="tracker.is_closed"><div><span>Average per day</span><strong>{{ money(tracker.run_rate) }}</strong></div><div><span>Needed per day</span><strong>{{ money(Number(tracker.target)/Math.max(1,Number(tracker.total_days))) }}</strong></div><div><span>Result</span><strong>{{ Number(tracker.pct)>=100?'TARGET MET':'MISSED by '+compact(tracker.gap) }}</strong></div><div><span>Cycle length</span><strong>{{ tracker.total_days }} days</strong></div></template><template v-else><div><span>Current run rate</span><strong>{{ money(tracker.run_rate) }} / day</strong></div><div><span>Required run rate</span><strong>{{ money(tracker.req_per_day) }} / day</strong></div><div><span>Projected at this pace</span><strong>{{ compact(tracker.projected) }}</strong></div><div><span>Status</span><strong>{{ tracker.on_track?'ON TRACK':'BEHIND by '+compact(Math.max(0,Number(tracker.target)-Number(tracker.projected))) }}</strong></div></template><div><span>Days hit</span><strong>{{ tracker.hit_days }}</strong></div><div><span>Days missed</span><strong>{{ tracker.miss_days }}</strong></div></div></details>
        <details class="target-section" open><summary>Daily collections vs required · {{ days.length }} days</summary><div v-if="days.length" class="target-bars"><div v-for="day in days" :key="day.d" class="target-bar" :title="date(day.d)+' · collected '+money(day.got)+' of '+money(day.req)"><div class="target-bar-track"><i :class="day.hit?'hit':'miss'" :style="{height:Math.min(100,Number(day.got||0)/maxBar*100)+'%'}"></i><b :style="{bottom:Math.min(100,Number(day.req||0)/maxBar*100)+'%'}"></b></div><span>{{ String(day.d).slice(8,10) }}</span></div></div><p v-else>No elapsed days in this cycle yet.</p><p class="target-legend">Green: hit · Red: miss · Line: required that day</p></details>
        <details class="target-section" open><summary>Day by day · newest first</summary><div class="target-table-wrap"><table><thead><tr><th>Date</th><th>Gross</th><th>GST</th><th>Loan cut</th><th>Collected (net)</th><th>Target that day</th><th>+/−</th><th>Cumulative</th><th>Result</th></tr></thead><tbody><tr v-for="day in [...days].reverse()" :key="day.d"><td>{{ date(day.d) }}</td><td>{{ money(day.gross) }}</td><td>{{ money(day.gst) }}</td><td>{{ Number(day.cut)>0?'−'+money(day.cut):'—' }}</td><td><strong>{{ money(day.got) }}</strong></td><td>{{ money(day.req) }}</td><td :class="day.diff>=0?'target-positive':'target-negative'">{{ day.diff>=0?'+':'' }}{{ money(day.diff) }}</td><td>{{ compact(day.cum) }}</td><td><span class="target-pill" :class="day.hit?'hit':'miss'">{{ day.hit?'HIT':'MISS' }}</span></td></tr><tr v-if="!days.length"><td colspan="9">No elapsed days yet.</td></tr></tbody><tfoot><tr><th>Total</th><td>{{ money(tracker.gross) }}</td><td>{{ money(tracker.gst) }}</td><td>{{ Number(tracker.cut)>0?'−'+money(tracker.cut):'—' }}</td><td>{{ money(tracker.achieved) }}</td><td></td><td></td><td>{{ compact(tracker.achieved) }}</td><td></td></tr></tfoot></table></div></details>
        <details class="target-section"><summary>How the daily target works</summary><p>Realisation uses net collections: gross receipts minus GST and any loan cut. Loan payment modes lose a further 15% of the ex-GST amount. Each day's target is the remaining monthly target divided by the days left in the cycle, so misses raise the next day's requirement and strong days lower it. The full cycle target is used even when a shorter date range is selected.</p></details>
      </template>
    </template>
  </section>
</template>
