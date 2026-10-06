<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { ccCall } from '../api/cc';
import { branchOf, dateRange, downloadCsv, indiaStamp, maskPhone, visitMetrics, visitStatus } from '../lib/cc';
import CCDataTable from '../components/cc/CCDataTable.vue';
import CCPager from '../components/cc/CCPager.vue';
import '../styles/cc.css';
const initial = dateRange('today'), from = ref(initial[0]), to = ref(initial[1]), period = ref('today');
const branch = ref(''), agent = ref(''), status = ref(''), search = ref(''), sort = ref('date');
const rows = ref([]), page = ref(1), loading = ref(false), error = ref(''), truncated = ref(false), total = ref(0), scoped = ref(false), applied = ref(null);
const financial = ref(null), financialLoading = ref(false), financialError = ref(''), financialPage = ref(1);
const now = ref(indiaStamp()); let clock;
let controller, financialController, generation = 0;
const columns = [
  { key:'branch', label:'Branch', value:branchOf }, { key:'lead_name', label:'Client' },
  { key:'name', label:'Lead ID' }, { key:'mobile_no', label:'Phone', value:r=>maskPhone(r.mobile_no) },
  { key:'lead_owner', label:'CC Agent' }, { key:'custom_appointment_date_and_time', label:'Date / time' },
  { key:'status', label:'Present status', value:visitStatus },
];
const financialColumns = [
  {key:'sales_invoice',label:'Invoice'}, {key:'lead_name',label:'Client'}, {key:'branch',label:'Branch'},
  {key:'event_date',label:'Event date'}, {key:'paid_amount',label:'Paid amount'}, {key:'mode_of_payment',label:'Mode of payment'},
];
const branches = computed(()=>[...new Set(rows.value.map(branchOf))].sort());
const agents = computed(()=>[...new Set(rows.value.map(r=>r.lead_owner).filter(Boolean))].sort());
const statuses = computed(()=>[...new Set(rows.value.map(visitStatus))].sort());
const baseRows = computed(()=>rows.value.filter(r=>(!agent.value||r.lead_owner===agent.value)&&(!status.value||visitStatus(r)===status.value)&&(!search.value.trim()||[r.name,r.lead_name,branchOf(r),r.lead_owner].some(v=>String(v||'').toLowerCase().includes(search.value.trim().toLowerCase())))));
const filtered = computed(()=>baseRows.value.filter(r=>!branch.value||branchOf(r)===branch.value).sort((a,b)=>String(sort.value==='branch'?branchOf(a):a.custom_appointment_date_and_time).localeCompare(String(sort.value==='branch'?branchOf(b):b.custom_appointment_date_and_time))||a.name.localeCompare(b.name)));
const visible = computed(()=>filtered.value.slice((page.value-1)*40,page.value*40));
const pages = computed(()=>Math.max(1,Math.ceil(filtered.value.length/40)));
const cards = computed(()=>['',...branches.value].map(name=>({name, ...visitMetrics(baseRows.value.filter(r=>!name||branchOf(r)===name),now.value)})));
const financialRows = computed(()=>financial.value?.financial_events || []);
watch([branch,agent,status,search,sort],()=>{page.value=1;});
function selectPeriod() { if(period.value!=='custom') [from.value,to.value]=dateRange(period.value); }
async function load() {
  if(!from.value||!to.value||from.value>to.value){error.value='Choose a valid date range.';return;}
  const token=++generation;controller?.abort();financialController?.abort();controller=new AbortController();
  rows.value=[];financial.value=null;financialLoading.value=false;financialError.value='';financialPage.value=1;page.value=1;loading.value=true;error.value='';applied.value=null;truncated.value=false;
  const range={from_date:from.value,to_date:to.value};
  try {
    const data=await ccCall('life_cc_agent_marketing_data',{...range,view:'appointments'},controller.signal);
    if(token!==generation)return;
    rows.value=(data.rows||[]).filter(r=>r.name&&r.lead_owner&&r.custom_appointment_date_and_time);
    total.value=data.total;truncated.value=!!data.truncated;scoped.value=!!data.restricted_to_owner;applied.value=range;
    branch.value='';agent.value='';status.value='';
  } catch(e){if(token===generation&&e.name!=='AbortError')error.value=e.message;}
  finally{if(token===generation)loading.value=false;}
}
async function loadFinancial() {
  if(!applied.value||financialLoading.value)return;
  const token=generation;financialController?.abort();financialController=new AbortController();financialLoading.value=true;financialError.value='';
  try{const data=await ccCall('life_cc_agent_marketing_data',applied.value,financialController.signal);if(token===generation)financial.value=data;}
  catch(e){if(token===generation&&e.name!=='AbortError')financialError.value=e.message;}
  finally{if(token===generation)financialLoading.value=false;}
}
function exportRows(){if(!truncated.value&&applied.value)downloadCsv(`cc-visits-${applied.value.from_date}-${applied.value.to_date}.csv`,columns,filtered.value);}
onMounted(()=>{load();clock=setInterval(()=>{now.value=indiaStamp();},60000);});
onUnmounted(()=>{generation++;controller?.abort();financialController?.abort();clearInterval(clock);});
</script>
<template>
<section class="cc-native">
  <header><div><h1>CC Visit Report</h1><p class="cc-note">Native Vue preview · Call centre → branch appointment schedule</p></div><div class="cc-actions"><RouterLink :to="{name:'leads-native'}">Dashboard preview</RouterLink><RouterLink :to="{name:'ccvisit'}">Current full report</RouterLink></div></header>
  <form class="cc-filters" @submit.prevent="load"><label>Period<select v-model="period" @change="selectPeriod"><option value="today">Today</option><option value="tomorrow">Tomorrow</option><option value="week">Next 7 days · from tomorrow</option><option value="ten">Next 10 days · including today</option><option value="month">Sales month · 6th–5th</option><option value="nextmonth">Next sales month</option><option value="custom">Custom</option></select></label><label>From<input v-model="from" type="date" required @change="period='custom'"></label><label>To<input v-model="to" type="date" required @change="period='custom'"></label><button type="submit">Apply / refresh</button></form>
  <p v-if="error" role="alert" class="cc-error">{{error}} <button @click="load">Retry</button></p>
  <p v-if="loading" role="status">Loading appointment schedule…</p>
  <p v-if="applied" role="status">{{applied.from_date}} → {{applied.to_date}} · {{filtered.length}} matching appointments<span v-if="scoped"> · Owner restricted</span></p>
  <p v-if="truncated" role="alert" class="cc-error">Only the first 10,000 of {{total}} records were returned. Counts are partial; narrow the dates before exporting.</p>
  <div class="cc-filters"><label>Branch<select v-model="branch"><option value="">All returned branches</option><option v-for="b in branches" :key="b">{{b}}</option></select></label><label>Agent<select v-model="agent"><option value="">All returned agents</option><option v-for="a in agents" :key="a">{{a}}</option></select></label><label>Status<select v-model="status"><option value="">All statuses</option><option v-for="s in statuses" :key="s">{{s}}</option></select></label><label>Search<input v-model="search" type="search" placeholder="Client, Lead ID, branch or agent"></label><label>Sort<select v-model="sort"><option value="date">Appointment date</option><option value="branch">Branch</option></select></label><button :disabled="loading||!applied||truncated||!filtered.length" @click="exportRows">Export filtered CSV</button></div>
  <div v-if="applied" class="cc-cards"><button v-for="card in cards" :key="card.name" :aria-pressed="branch===card.name" @click="branch=card.name"><strong>{{card.name||'All returned branches'}}</strong><span>Appointments: {{card.appointments}}</span><span>Visits: {{card.visits}}</span><span>Booked: {{card.booked}}</span><span>Branch pending: {{card.pending}}</span><small v-if="card.overdue">{{card.overdue}} visit updates overdue</small></button></div>
  <p class="cc-note">Pending includes visited outcomes still pending and past appointments awaiting a branch update. Dates and overdue checks use India time. CSV includes every filtered row with masked phone numbers.</p>
  <CCDataTable :columns="columns" :rows="visible" :busy="loading" />
  <CCPager :page="page" :pages="pages" :busy="loading" @change="page=$event" />
  <section><h2>Financial events</h2><p class="cc-note">Loads separately for the applied dates and your API permissions. Schedule filters above do not apply to financial events.</p><button :disabled="!applied||loading||financialLoading" @click="loadFinancial">{{financialLoading?'Loading financial events…':'Load financial events'}}</button><p v-if="financialError" role="alert" class="cc-error">{{financialError}}</p><template v-if="financial"><CCDataTable :columns="financialColumns" :rows="financialRows.slice((financialPage-1)*40,financialPage*40)" /><CCPager :page="financialPage" :pages="Math.max(1,Math.ceil(financialRows.length/40))" @change="financialPage=$event" /></template></section>
</section>
</template>
