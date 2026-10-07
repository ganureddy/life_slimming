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
const reportTab = ref('visits');
const agentRows = computed(()=>financial.value?.ranking_rows || []);
const marketingRows = computed(()=>financial.value?.rows || []);
const invoiceRows = computed(()=>financial.value?.cc_invoice_report_summary?.rows || []);
const agentColumns = [
  {key:'lead_owner',label:'CC Agent'}, {key:'custom_appointment_date_and_time',label:'Appointment date'},
  {key:'custom_appointment_status',label:'Appointment status'}, {key:'status',label:'Lead status'},
];
const marketingColumns = [
  {key:'name',label:'Lead ID'}, {key:'lead_name',label:'Client'},
  {key:'branch',label:'Branch',value:branchOf}, {key:'lead_owner',label:'CC Agent'},
  {key:'source',label:'Source'}, {key:'enquired_for',label:'Interest'},
  {key:'status',label:'Status'}, {key:'custom_appointment_date_and_time',label:'Appointment'},
];
const invoiceColumns = [
  {key:'invoice',label:'Invoice'}, {key:'lead_name',label:'Client'},
  {key:'branch',label:'Branch'}, {key:'lead_owner',label:'CC Agent'},
  {key:'invoice_date',label:'Date'}, {key:'with_gst',label:'Invoice amount'},
  {key:'paid',label:'Paid'}, {key:'balance',label:'Outstanding'},
];
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
<section class="cc-native cc-native-shell cc-report-native">
  <header class="cc-workspace-head"><div class="cc-brand"><span class="cc-brand-mark">L</span><div><strong>🎧 LIFE CALL CENTRE REPORTS</strong><small>CC Command ERP · Branch Visits &amp; Agent Performance</small></div></div><RouterLink class="cc-report-back" :to="{name:'leads-native'}">← Back to Dashboard</RouterLink></header>
  <div class="cc-app-layout"><aside class="cc-sidebar"><div class="cc-nav-caption">MAIN</div><RouterLink :to="{name:'leads-native'}">📊 Dashboard</RouterLink><RouterLink :to="{name:'leads-native'}">📋 My Lead Queue</RouterLink><RouterLink :to="{name:'cc-appointments'}">📅 Appointments</RouterLink><div class="cc-nav-caption">REPORTING</div><RouterLink class="active" :to="{name:'ccvisit-native'}">📈 CC Reports</RouterLink><div class="cc-sidebar-foot">LIFE CC Command<small>Call Centre · Reports</small></div></aside><main class="cc-main">
  <div class="cc-section-heading"><div><p class="cc-eyebrow">HOME › REPORTS</p><h1>CC Branch Visits &amp; Performance</h1></div><RouterLink :to="{name:'leads-native'}">🎧 Agent Dashboard ↗</RouterLink></div>
  <nav class="cc-report-tabs" aria-label="CC reports"><button :class="{active:reportTab==='visits'}" @click="reportTab='visits'">📅 CC Branch Visits</button><button :class="{active:reportTab==='agents'}" @click="reportTab='agents';loadFinancial()">🎧 Agent Report</button><button :class="{active:reportTab==='marketing'}" @click="reportTab='marketing';loadFinancial()">📣 Lead &amp; Digital Marketing</button><button :class="{active:reportTab==='consultants'}" @click="reportTab='consultants';loadFinancial()">👥 Consultant / Manager Report</button></nav>
  <form class="cc-filters" @submit.prevent="load"><label>Period<select v-model="period" @change="selectPeriod"><option value="today">Today</option><option value="tomorrow">Tomorrow</option><option value="week">This Week</option><option value="ten">Next 10 days · including today</option><option value="month">This Month</option><option value="nextmonth">Next Month</option><option value="custom">Custom</option></select></label><label>From<input v-model="from" type="date" required @change="period='custom'"></label><label>To<input v-model="to" type="date" required @change="period='custom'"></label><button type="submit">Apply / refresh</button></form>
  <p v-if="error" role="alert" class="cc-error">{{error}} <button @click="load">Retry</button></p>
  <p v-if="loading" role="status">Loading appointment schedule…</p>
  <p v-if="applied" role="status">{{applied.from_date}} → {{applied.to_date}} · {{filtered.length}} matching appointments<span v-if="scoped"> · Owner restricted</span></p>
  <p v-if="truncated" role="alert" class="cc-error">Only the first 10,000 of {{total}} records were returned. Counts are partial; narrow the dates before exporting.</p>
  <div v-if="reportTab==='visits'" class="cc-filters"><label>Branch<select v-model="branch"><option value="">All returned branches</option><option v-for="b in branches" :key="b">{{b}}</option></select></label><label>Agent<select v-model="agent"><option value="">All returned agents</option><option v-for="a in agents" :key="a">{{a}}</option></select></label><label>Status<select v-model="status"><option value="">All statuses</option><option v-for="s in statuses" :key="s">{{s}}</option></select></label><label>Search<input v-model="search" type="search" placeholder="Client, Lead ID, branch or agent"></label><label>Sort<select v-model="sort"><option value="date">Appointment date</option><option value="branch">Branch</option></select></label><button :disabled="loading||!applied||truncated||!filtered.length" @click="exportRows">Export filtered CSV</button></div>
  <template v-if="reportTab==='visits'"><div v-if="applied" class="cc-cards"><button v-for="card in cards" :key="card.name" :aria-pressed="branch===card.name" @click="branch=card.name"><strong>{{card.name||'All returned branches'}}</strong><span>Appointments: {{card.appointments}}</span><span>Visits: {{card.visits}}</span><span>Booked: {{card.booked}}</span><span>Branch pending: {{card.pending}}</span><small v-if="card.overdue">{{card.overdue}} visit updates overdue</small></button></div><p class="cc-note">Pending includes visited outcomes still pending and past appointments awaiting a branch update. Dates and overdue checks use India time. CSV includes every filtered row with masked phone numbers.</p><CCDataTable :columns="columns" :rows="visible" :busy="loading" /><CCPager :page="page" :pages="pages" :busy="loading" @change="page=$event" /></template>
  <section v-else class="cc-report-panel"><p class="cc-note">{{financialLoading?'Loading report data…':financialError||'Report data is based on the selected date range and your account permissions.'}}</p><button v-if="!financial&&!financialLoading" :disabled="!applied" @click="loadFinancial">Load report data</button><template v-if="financial"><template v-if="reportTab==='agents'"><h2>Agent performance</h2><div class="cc-cards cc-report-metrics"><div><strong>{{financial.agent_report_summary?.counts?.appointments ?? 0}}</strong><span>Appointments</span></div><div><strong>{{financial.agent_report_summary?.counts?.visited ?? 0}}</strong><span>Visited</span></div><div><strong>{{financial.agent_report_summary?.counts?.booked ?? 0}}</strong><span>Booked</span></div><div><strong>{{financial.agent_report_summary?.counts?.booking_percent ?? 0}}%</strong><span>Booking rate</span></div></div><CCDataTable :columns="agentColumns" :rows="agentRows" /></template><template v-else-if="reportTab==='marketing'"><h2>Lead &amp; digital marketing</h2><p v-if="financial.marketing_agencies?.length" class="cc-note">Campaign / agency sources: {{financial.marketing_agencies.map(x=>x.label).join(' · ')}}</p><CCDataTable :columns="marketingColumns" :rows="marketingRows.slice((financialPage-1)*40,financialPage*40)" /><CCPager :page="financialPage" :pages="Math.max(1,Math.ceil(marketingRows.length/40))" @change="financialPage=$event" /></template><template v-else><h2>Consultant / manager report · invoices</h2><div class="cc-cards cc-report-metrics"><div><strong>{{financial.cc_invoice_report_summary?.totals?.invoice_count ?? invoiceRows.length}}</strong><span>Call centre invoices</span></div><div><strong>₹{{financial.cc_invoice_report_summary?.totals?.with_gst ?? '0.00'}}</strong><span>Invoice total</span></div><div><strong>₹{{financial.cc_invoice_report_summary?.totals?.paid ?? '0.00'}}</strong><span>Collected</span></div><div><strong>₹{{financial.cc_invoice_report_summary?.totals?.balance ?? '0.00'}}</strong><span>Outstanding</span></div></div><CCDataTable :columns="invoiceColumns" :rows="invoiceRows.slice((financialPage-1)*40,financialPage*40)" /><CCPager :page="financialPage" :pages="Math.max(1,Math.ceil(invoiceRows.length/40))" @change="financialPage=$event" /><h3>Payment events</h3><CCDataTable :columns="financialColumns" :rows="financialRows.slice((financialPage-1)*40,financialPage*40)" /></template></template></section>
</main></div>
</section>
</template>
