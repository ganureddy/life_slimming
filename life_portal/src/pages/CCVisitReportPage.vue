<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { session } from '../lib/session';
import { reportRange, reportGroups, reportDrilldown, aggregateMoney, businessCycle } from '../lib/cc-visit-report';
import CCVisitMonthStrip from '../components/cc/CCVisitMonthStrip.vue';
import CCAgent360 from '../components/cc/CCAgent360.vue';
import CCActivityReport from '../components/cc/CCActivityReport.vue';
import CCNoFollowupReport from '../components/cc/CCNoFollowupReport.vue';
import CCAttendance from '../components/cc/CCAttendance.vue';
import { request } from '../api/http';
import { ccCall } from '../api/cc';
import { branchOf, dateRange, downloadCsv, indiaStamp, maskPhone, visitMetrics, visitStatus } from '../lib/cc';
import CCDataTable from '../components/cc/CCDataTable.vue';
import CCPager from '../components/cc/CCPager.vue';
import '../styles/cc.css';
const route=useRoute(),router=useRouter();
const initial = reportRange('today'), from = ref(initial[0]), to = ref(initial[1]), period = ref('today');
const branch = ref(''), agent = ref(''), status = ref(''), search = ref(''), sort = ref('date');
const rows = ref([]), page = ref(1), loading = ref(false), error = ref(''), truncated = ref(false), total = ref(0), scoped = ref(false), applied = ref(null);
const financial = ref(null), financialLoading = ref(false), financialError = ref(''), financialPage = ref(1);
const now = ref(indiaStamp()); let clock,changeTimer,changeController;
const newData=ref(false);let changeToken='';
async function checkChanges(){if(document.hidden||!applied.value||changeController)return;const range=applied.value,token=generation;changeController=new AbortController();try{const result=(await request('life_slimming.api.cc_report_activity.changes',{args:range,csrfToken:session.csrf_token,signal:changeController.signal})).message;if(token!==generation||!result?.token)return;if(changeToken&&changeToken!==result.token)newData.value=true;changeToken=result.token;}catch{}finally{changeController=null;}}
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
const tabAliases={branch:'visits',visits:'visits',agent:'agents',agents:'agents',a360:'agent360',agent360:'agent360',cvx:'convox',convox:'convox',lead:'marketing',marketing:'marketing',cm:'consultants',consultants:'consultants',journey:'journey',nofollowup:'nofollowup'};
const reportTab = ref(tabAliases[String(route.query.tab||route.hash.slice(1))]||'visits');
watch(reportTab,tab=>{router.replace({query:{...route.query,tab},hash:''});financialPage.value=1;if(['marketing','consultants'].includes(tab))loadFinancial();});
watch(()=>[route.query.tab,route.hash],([tab,hash])=>{const next=tabAliases[String(tab||hash.slice(1))];if(next)reportTab.value=next;});
const grouping=ref('branch'),summarySort=ref('key'),summaryDescending=ref(false),hidden=ref([]),textSize=ref(12),refreshKey=ref(0),agentSubtab=ref('performance');
const drillDialog=ref(null),drillTitle=ref(''),drillRows=ref([]),drillPage=ref(1),shareDialog=ref(null),shareSections=ref(['visits','groups']),shareNotice=ref(''),attendanceDialog=ref(null),attendanceOpen=ref(false);
const todayDialog=ref(null),todayRows=ref([]),todayBusy=ref(false),todayError=ref('');let todayController;
async function openToday(){await nextTick();todayDialog.value?.showModal();todayController?.abort();todayController=new AbortController();todayBusy.value=true;todayRows.value=[];todayError.value='';try{const day=indiaStamp().slice(0,10);const data=await ccCall('life_cc_agent_marketing_data',{view:'appointments',compact:1,from_date:day,to_date:day},todayController.signal);todayRows.value=data.rows||[];if(data.truncated)todayError.value='Only part of today’s appointments could be loaded.';}catch(e){if(e.name!=='AbortError')todayError.value=e.message;}finally{todayBusy.value=false;}}
const rolling=ref(null),rollingBusy=ref(false),rollingError=ref('');let rollingController,rollingGeneration=0;
const preferencesKey='life_cc_report_layout:'+session.user;
try{const saved=JSON.parse(localStorage.getItem(preferencesKey)||'{}');hidden.value=Array.isArray(saved.hidden)?saved.hidden:[];textSize.value=Math.max(10,Math.min(18,Number(saved.textSize)||12));}catch{}
watch([hidden,textSize],()=>{try{localStorage.setItem(preferencesKey,JSON.stringify({hidden:hidden.value,textSize:textSize.value}));}catch{}},{deep:true});
function toggleSection(section){hidden.value=hidden.value.includes(section)?hidden.value.filter(s=>s!==section):[...hidden.value,section];}
const summaryGroups=computed(()=>reportGroups(filtered.value,grouping.value,now.value).sort((a,b)=>{const result=summarySort.value==='key'?a.key.localeCompare(b.key):Number(a[summarySort.value])-Number(b[summarySort.value]);return summaryDescending.value?-result:result;}));
const visitTotals=computed(()=>reportGroups(filtered.value.map(r=>({...r,branch:'All'})),'branch',now.value)[0]||{});
const invoiceGroups=computed(()=>aggregateMoney(invoiceRows.value,'branch'));
const consultantGroups=computed(()=>aggregateMoney(invoiceRows.value,'consultant',r=>r.consultant_name||r.consultant||r.center_manager||'Not assigned'));
const marketingGroups=computed(()=>{const groups=new Map();for(const row of marketingRows.value){const key=row.source||row.custom_media||'Unknown';const values=groups.get(key)||[];values.push(row);groups.set(key,values);}return [...groups].map(([source,items])=>({source,leads:items.length,...visitMetrics(items,now.value)}));});
function summaryOrder(key){if(summarySort.value===key)summaryDescending.value=!summaryDescending.value;else{summarySort.value=key;summaryDescending.value=key!=='key';}}
function openDrill(key,metric){const subset=filtered.value.filter(r=>!key||(grouping.value==='agent'?r.lead_owner===key:branchOf(r)===key));drillRows.value=reportDrilldown(subset,metric,now.value);drillTitle.value=(key||'All appointments')+' · '+metric;drillPage.value=1;nextTick(()=>drillDialog.value?.showModal());}
function openLead(id){router.push({name:'leads-native',query:{view:'followup',lead:id}});}
function selectDay(day){from.value=day;to.value=day;period.value='custom';load();}
function resetFilters(){branch.value='';agent.value='';status.value='';search.value='';sort.value='date';}
function quickPeriod(value){period.value=value;selectPeriod();load();}
function printReport(){window.print();}
function openAttendance(){attendanceOpen.value=true;nextTick(()=>attendanceDialog.value?.showModal());}
const shareText=computed(()=>{const lines=['LIFE CC REPORT',applied.value?applied.value.from_date+' → '+applied.value.to_date:''];if(shareSections.value.includes('visits'))lines.push('Appointments '+(visitTotals.value.appointments||0)+' | Visits '+(visitTotals.value.visits||0)+' | Booked '+(visitTotals.value.booked||0));if(shareSections.value.includes('groups'))for(const row of summaryGroups.value)lines.push(row.key+': '+row.appointments+' appointments, '+row.visits+' visits, '+row.booked+' booked');if(shareSections.value.includes('rolling'))for(const item of rolling.value||[])lines.push(item.from+' → '+item.to+': '+item.appointments+' appointments, '+item.visits+' visits, '+item.booked+' booked');return lines.join('\n');});
async function copyShare(){try{await navigator.clipboard.writeText(shareText.value);shareNotice.value='Report copied.';}catch{shareNotice.value='Clipboard access is unavailable. Select and copy the preview text.';}}
async function loadRolling(){if(rollingBusy.value)return;const token=++rollingGeneration;rollingController?.abort();rollingController=new AbortController();rollingBusy.value=true;rollingError.value='';try{const results=await Promise.all([0,-1,-2].map(async offset=>{const [start,end]=businessCycle(applied.value?.to_date||now.value.slice(0,10),offset);const data=await ccCall('life_cc_agent_marketing_data',{view:'appointments',compact:1,from_date:start,to_date:end},rollingController.signal);return {from:start,to:end,partial:!!data.truncated,...visitMetrics((data.rows||[]).filter(r=>(!branch.value||branchOf(r)===branch.value)&&(!agent.value||r.lead_owner===agent.value)),now.value)};}));if(token===rollingGeneration)rolling.value=results;}catch(e){if(token===rollingGeneration&&e.name!=='AbortError')rollingError.value=e.message;}finally{if(token===rollingGeneration)rollingBusy.value=false;}}
watch([branch,agent],()=>{rollingGeneration++;rollingController?.abort();rolling.value=null;rollingBusy.value=false;});

const agentRows = computed(()=>financial.value?.ranking_rows || rows.value);
const performanceGroups=computed(()=>reportGroups(agentRows.value.filter(r=>!agent.value||r.lead_owner===agent.value),'agent',now.value));
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
function selectPeriod() { if(period.value!=='custom') [from.value,to.value]=reportRange(period.value); }
async function load() {
  if(!from.value||!to.value||from.value>to.value){error.value='Choose a valid date range.';return;}
  newData.value=false;changeToken='';changeController?.abort();
  rollingGeneration++;rollingController?.abort();rolling.value=null;rollingBusy.value=false;
  const token=++generation;controller?.abort();financialController?.abort();controller=new AbortController();
  rows.value=[];financial.value=null;financialLoading.value=false;financialError.value='';financialPage.value=1;page.value=1;loading.value=true;error.value='';applied.value=null;truncated.value=false;
  const range={from_date:from.value,to_date:to.value};
  try {
    const data=await ccCall('life_cc_agent_marketing_data',{...range,view:'appointments',compact:1},controller.signal);
    if(token!==generation)return;
    rows.value=(data.rows||[]).filter(r=>r.name&&r.lead_owner&&r.custom_appointment_date_and_time);
    total.value=data.total;truncated.value=!!data.truncated;scoped.value=!!data.restricted_to_owner;applied.value=range;
    branch.value='';agent.value='';status.value='';refreshKey.value++;
    if(['marketing','consultants'].includes(reportTab.value))loadFinancial();
  } catch(e){if(token===generation&&e.name!=='AbortError')error.value=e.message;}
  finally{if(token===generation)loading.value=false;}
}
async function loadFinancial() {
  if(!applied.value||financialLoading.value||financial.value)return;
  const token=generation;financialController?.abort();financialController=new AbortController();financialLoading.value=true;financialError.value='';
  try{const data=await ccCall('life_cc_agent_marketing_data',applied.value,financialController.signal);if(token===generation)financial.value=data;}
  catch(e){if(token===generation&&e.name!=='AbortError')financialError.value=e.message;}
  finally{if(token===generation)financialLoading.value=false;}
}
function exportFinancial(){if(!financial.value||truncated.value)return;const cols=reportTab.value==='agents'?agentColumns:reportTab.value==='marketing'?marketingColumns:invoiceColumns;const source=reportTab.value==='agents'?agentRows.value:reportTab.value==='marketing'?marketingRows.value:invoiceRows.value;downloadCsv('cc-'+reportTab.value+'.csv',cols,source.filter(row=>!agent.value||row.lead_owner===agent.value));}
function exportRows(){if(!truncated.value&&applied.value)downloadCsv(`cc-visits-${applied.value.from_date}-${applied.value.to_date}.csv`,columns,filtered.value);}
onMounted(()=>{load();changeTimer=setInterval(checkChanges,90000);clock=setInterval(()=>{now.value=indiaStamp();},60000);});
onUnmounted(()=>{generation++;controller?.abort();financialController?.abort();clearInterval(clock);todayController?.abort();clearInterval(changeTimer);changeController?.abort();rollingGeneration++;rollingController?.abort();});
</script>
<template>
<section class="cc-native cc-native-shell cc-report-native cc-visit-v26" :style="{'--report-text-size':textSize+'px'}">
  <header class="cc-workspace-head"><div class="cc-brand"><span class="cc-brand-mark">L</span><div><strong>🎧 LIFE CALL CENTRE REPORTS</strong><small>Branch appointments · visits · agent performance</small></div></div><div class="cc-report-header-actions"><button @click="shareNotice='';shareDialog.showModal()" :disabled="!applied||truncated">Share preview</button><button @click="printReport">Print</button><button @click="openToday">Today’s appointments</button><button @click="openAttendance">On-floor staff</button></div><RouterLink class="cc-report-back" :to="{name:'leads-native'}">← Back to Dashboard</RouterLink></header>
  <div class="cc-app-layout"><aside class="cc-sidebar"><div class="cc-nav-caption">MAIN</div><RouterLink :to="{name:'leads-native'}">📊 Dashboard</RouterLink><RouterLink :to="{name:'leads-native'}">📋 My Lead Queue</RouterLink><RouterLink :to="{name:'cc-appointments'}">📅 Appointments</RouterLink><div class="cc-nav-caption">REPORTING</div><RouterLink class="active" :to="{name:'ccvisit-native'}">📈 CC Reports</RouterLink><div class="cc-sidebar-foot">LIFE CC Command<small>Call Centre · Reports</small></div></aside><main class="cc-main">
  <div class="cc-section-heading"><div><p class="cc-eyebrow">HOME › REPORTS</p><h1>CC Branch Visits &amp; Performance</h1></div><RouterLink :to="{name:'leads-native'}">🎧 Agent Dashboard ↗</RouterLink></div>
  <nav class="cc-report-tabs" aria-label="CC reports"><button :class="{active:reportTab==='visits'}" @click="reportTab='visits'">📅 CC Branch Visits</button><button :class="{active:reportTab==='agents'}" @click="reportTab='agents'">🎧 Agent Report</button><button :class="{active:reportTab==='marketing'}" @click="reportTab='marketing';loadFinancial()">📣 Lead &amp; Digital Marketing</button><button :class="{active:reportTab==='consultants'}" @click="reportTab='consultants';loadFinancial()">👥 Consultant / Manager Report</button><button :class="{active:reportTab==='agent360'}" @click="reportTab='agent360'">🔗 Agent 360</button><button :class="{active:reportTab==='journey'}" @click="reportTab='journey'">🧭 Lead Journey</button></nav>
  <CCVisitMonthStrip v-if="applied" :branch="branch" :agent="agent" :refresh-key="refreshKey" @select="selectDay"/>
  <form class="cc-filters" @submit.prevent="load"><label>Period<select v-model="period" @change="selectPeriod"><option value="today">Today</option><option value="yesterday">Yesterday</option><option value="lastweek">Last Week</option><option value="lastmonth">Last Month</option><option value="tomorrow">Tomorrow</option><option value="week">This Week</option><option value="ten">Next 10 days · including today</option><option value="month">This Month</option><option value="nextmonth">Next Month</option><option value="custom">Custom</option></select></label><label>From<input v-model="from" type="date" required @change="period='custom'"></label><label>To<input v-model="to" type="date" required @change="period='custom'"></label><button type="submit">Apply / refresh</button></form>
  <div class="cc-report-tools"><button v-for="[value,label] in [['today','Today'],['week','This Week'],['lastweek','Last Week'],['month','This Month'],['lastmonth','Last Month']]" :key="value" @click="quickPeriod(value)">{{label}}</button><button @click="resetFilters">Reset filters</button><button @click="toggleSection('cards')">{{hidden.includes('cards')?'Show':'Hide'}} branch cards</button><label>Restore section<select @change="hidden=hidden.filter(s=>s!==$event.target.value);$event.target.value='' "><option value="">Choose…</option><option v-for="key in hidden" :key="key">{{key}}</option></select></label><button aria-label="Smaller report text" @click="textSize=Math.max(10,textSize-1)">A−</button><button aria-label="Larger report text" @click="textSize=Math.min(18,textSize+1)">A+</button></div>
  <nav v-if="reportTab==='agents'" class="cc-report-tools" aria-label="Agent reports"><button @click="agentSubtab='performance'">Performance</button><button @click="agentSubtab='convox'">ConVox dispositions</button><button @click="agentSubtab='nofollowup'">No follow-up</button></nav>
  <button v-if="newData" class="cc-new-data" @click="load">New data available · Refresh report</button><p v-if="error" role="alert" class="cc-error">{{error}} <button @click="load">Retry</button></p>
  <p v-if="loading" role="status">Loading appointment schedule…</p>
  <p v-if="applied" role="status">{{applied.from_date}} → {{applied.to_date}} · {{filtered.length}} matching appointments<span v-if="scoped"> · Owner restricted</span></p>
  <p v-if="truncated" role="alert" class="cc-error">Only the first 10,000 records were returned; more appointments exist. Counts are partial; narrow the dates before exporting.</p>
  <div v-if="reportTab==='visits'" class="cc-filters"><label>Branch<select v-model="branch"><option value="">All returned branches</option><option v-for="b in branches" :key="b">{{b}}</option></select></label><label>Agent<select v-model="agent"><option value="">All returned agents</option><option v-for="a in agents" :key="a">{{a}}</option></select></label><label>Status<select v-model="status"><option value="">All statuses</option><option v-for="s in statuses" :key="s">{{s}}</option></select></label><label>Search<input v-model="search" type="search" placeholder="Client, Lead ID, branch or agent"></label><label>Sort<select v-model="sort"><option value="date">Appointment date</option><option value="branch">Branch</option></select></label><button :disabled="loading||!applied||truncated||!filtered.length" @click="exportRows">Export filtered CSV</button></div>
  <template v-if="reportTab==='visits'"><div v-if="applied&&!hidden.includes('cards')" class="cc-cards"><button v-for="card in cards" :key="card.name" :aria-pressed="branch===card.name" @click="branch=card.name"><strong>{{card.name||'All returned branches'}}</strong><span>Appointments: {{card.appointments}}</span><span>Visits: {{card.visits}}</span><span>Booked: {{card.booked}}</span><span>Branch pending: {{card.pending}}</span><small v-if="card.overdue">{{card.overdue}} visit updates overdue</small></button></div><p class="cc-note">Pending includes visited outcomes still pending and past appointments awaiting a branch update. Dates and overdue checks use India time. CSV includes every filtered row with masked phone numbers.</p><section v-if="applied&&!hidden.includes('summary')" class="cc-report-summary"><header><h2>{{grouping==='branch'?'Branch-wise':'CC Agent-wise'}} summary</h2><div><button @click="grouping='branch'" :aria-pressed="grouping==='branch'">Branch-wise</button><button @click="grouping='agent'" :aria-pressed="grouping==='agent'">CC Agent-wise</button><button @click="toggleSection('summary')">Hide summary</button></div></header><div class="cc-table"><table><thead><tr><th v-for="[key,label] in [['key',grouping==='branch'?'Branch':'Agent'],['appointments','Appointments'],['visits','Visits'],['booked','Booked'],['notBooked','Not booked'],['pending','Pending'],['noShow','Not visited'],['cancelled','Cancelled'],['showup','Show-up %'],['conversion','Booking %']]" :key="key"><button @click="summaryOrder(key)">{{label}}</button></th></tr></thead><tbody><tr v-for="row in summaryGroups" :key="row.key"><th>{{row.key}}</th><td v-for="key in ['appointments','visits','booked','notBooked','pending','noShow','cancelled']" :key="key"><button @click="openDrill(row.key,key)">{{row[key]}}</button></td><td>{{row.showup}}%</td><td>{{row.conversion}}%</td></tr></tbody></table></div></section>
  <section class="cc-report-summary"><header><h2>Last three business months · conversion</h2><button :disabled="rollingBusy||!applied" @click="loadRolling">{{rollingBusy?'Loading…':'Load comparison'}}</button></header><p v-if="rollingError" role="alert" class="cc-error">{{rollingError}}</p><div v-if="rolling" class="cc-cards"><article v-for="item in rolling" :key="item.from"><strong>{{item.from}} → {{item.to}}</strong><p>{{item.appointments}} appointments · {{item.visits}} visits · {{item.booked}} booked</p><p>Show-up {{item.appointments?Math.round(item.visits*100/item.appointments):0}}% · Booking {{item.visits?Math.round(item.booked*100/item.visits):0}}%</p><span v-if="item.partial" class="cc-error">Partial totals</span></article></div></section>
  <CCDataTable :columns="columns" :rows="visible" :busy="loading"><template #actions="{row}"><button @click="openLead(row.name)">Open lead</button></template></CCDataTable><CCPager :page="page" :pages="pages" :busy="loading" @change="page=$event" /></template>
  <CCActivityReport v-else-if="applied&&reportTab==='agent360'" :from="applied.from_date" :to="applied.to_date" @open="openLead"/>
  <CCAgent360 title="Lead Journey" :show-full-report="false" v-else-if="applied&&reportTab==='journey'" :from="applied.from_date" :to="applied.to_date" @open="openLead"/>
  <CCActivityReport v-else-if="applied&&reportTab==='agents'&&agentSubtab==='convox'" :from="applied.from_date" :to="applied.to_date" channel="convox" @open="openLead"/>
  <CCNoFollowupReport v-else-if="applied&&reportTab==='agents'&&agentSubtab==='nofollowup'" @open="openLead"/>
  <section v-else-if="applied&&reportTab==='agents'" class="cc-report-panel"><h2>Agent performance</h2><CCDataTable :columns="[{key:'key',label:'Agent'},{key:'appointments',label:'Appointments'},{key:'visits',label:'Walk-ins'},{key:'booked',label:'Booked'},{key:'showup',label:'Show-up %'},{key:'conversion',label:'Booking %'}]" :rows="performanceGroups"/><CCDataTable :columns="agentColumns" :rows="agentRows.slice((financialPage-1)*40,financialPage*40)"/><CCPager :page="financialPage" :pages="Math.max(1,Math.ceil(agentRows.length/40))" @change="financialPage=$event"/></section>
  <section v-else class="cc-report-panel"><button :disabled="!financial||financialLoading||truncated" @click="exportFinancial">Export report CSV</button><p class="cc-note">{{financialLoading?'Loading report data…':financialError||'Report data is based on the selected date range and your account permissions.'}}</p><button v-if="!financial&&!financialLoading" :disabled="!applied" @click="loadFinancial">Load report data</button><template v-if="financial"><template v-if="reportTab==='agents'"><h2>Agent performance</h2><label>Agent<select v-model="agent"><option value="">All permitted agents</option><option v-for="a in agents" :key="a">{{a}}</option></select></label><CCDataTable :columns="[{key:'key',label:'Agent'},{key:'appointments',label:'Appointments'},{key:'visits',label:'Walk-ins'},{key:'booked',label:'Booked'},{key:'showup',label:'Show-up %'},{key:'conversion',label:'Booking %'}]" :rows="performanceGroups"/><div class="cc-cards cc-report-metrics"><div><strong>{{financial.agent_report_summary?.counts?.appointments ?? 0}}</strong><span>Appointments</span></div><div><strong>{{financial.agent_report_summary?.counts?.visited ?? 0}}</strong><span>Visited</span></div><div><strong>{{financial.agent_report_summary?.counts?.booked ?? 0}}</strong><span>Booked</span></div><div><strong>{{financial.agent_report_summary?.counts?.booking_percent ?? 0}}%</strong><span>Booking rate</span></div></div><CCDataTable :columns="agentColumns" :rows="agentRows" /></template><template v-else-if="reportTab==='marketing'"><h2>Lead &amp; digital marketing</h2><CCDataTable :columns="[{key:'source',label:'Source'},{key:'leads',label:'Leads'},{key:'appointments',label:'Records'},{key:'visits',label:'Visited'},{key:'booked',label:'Booked'}]" :rows="marketingGroups"/><p v-if="financial.marketing_agencies?.length" class="cc-note">Campaign / agency sources: {{financial.marketing_agencies.map(x=>x.label).join(' · ')}}</p><CCDataTable :columns="marketingColumns" :rows="marketingRows.slice((financialPage-1)*40,financialPage*40)" /><CCPager :page="financialPage" :pages="Math.max(1,Math.ceil(marketingRows.length/40))" @change="financialPage=$event" /></template><template v-else><h2>Consultant / manager report · invoices</h2><h3>Branch collections</h3><CCDataTable :columns="[{key:'name',label:'Branch'},{key:'count',label:'Invoices'},{key:'billed',label:'Billed'},{key:'paid',label:'Paid'},{key:'balance',label:'Outstanding'}]" :rows="invoiceGroups"/><h3>Consultant / manager collections</h3><p class="cc-note">Attribution uses the linked Therapy Plan consultant. Missing attribution remains “Not assigned”.</p><CCDataTable :columns="[{key:'name',label:'Consultant / manager'},{key:'count',label:'Invoices'},{key:'billed',label:'Billed'},{key:'paid',label:'Paid'},{key:'balance',label:'Outstanding'}]" :rows="consultantGroups"/><div class="cc-cards cc-report-metrics"><div><strong>{{financial.cc_invoice_report_summary?.totals?.invoice_count ?? invoiceRows.length}}</strong><span>Call centre invoices</span></div><div><strong>₹{{financial.cc_invoice_report_summary?.totals?.with_gst ?? '0.00'}}</strong><span>Invoice total</span></div><div><strong>₹{{financial.cc_invoice_report_summary?.totals?.paid ?? '0.00'}}</strong><span>Collected</span></div><div><strong>₹{{financial.cc_invoice_report_summary?.totals?.balance ?? '0.00'}}</strong><span>Outstanding</span></div></div><CCDataTable :columns="invoiceColumns" :rows="invoiceRows.slice((financialPage-1)*40,financialPage*40)" /><CCPager :page="financialPage" :pages="Math.max(1,Math.ceil(invoiceRows.length/40))" @change="financialPage=$event" /><h3>Payment events</h3><CCDataTable :columns="financialColumns" :rows="financialRows.slice((financialPage-1)*40,financialPage*40)" /></template></template></section>
<dialog ref="drillDialog" class="cc-report-dialog"><header><h2>{{drillTitle}} ({{drillRows.length}})</h2><button @click="drillDialog.close()">Close</button><button :disabled="truncated" @click="downloadCsv('cc-visit-drilldown.csv',columns,drillRows)">Export CSV</button></header><CCDataTable :columns="columns" :rows="drillRows.slice((drillPage-1)*40,drillPage*40)"><template #actions="{row}"><button @click="drillDialog.close();openLead(row.name)">Open lead</button></template></CCDataTable><CCPager :page="drillPage" :pages="Math.max(1,Math.ceil(drillRows.length/40))" @change="drillPage=$event"/></dialog>
<dialog ref="shareDialog" class="cc-report-dialog"><h2>Report share preview</h2><div class="cc-report-tools"><label v-for="key in ['visits','groups',...(rolling?['rolling']:[])]" :key="key"><input v-model="shareSections" type="checkbox" :value="key">{{key}}</label></div><textarea :value="shareText" readonly aria-label="Report preview" rows="14"></textarea><p role="status">{{shareNotice}}</p><button @click="copyShare">Copy report</button><button @click="shareDialog.close()">Close</button></dialog>
<dialog ref="todayDialog" class="cc-report-dialog" @close="todayController?.abort()"><header><h2>Today’s appointments</h2><button @click="todayDialog.close()">Close appointments</button></header><p v-if="todayError" role="alert" class="cc-error">{{todayError}}</p><CCDataTable :columns="columns" :rows="todayRows" :busy="todayBusy"><template #actions="{row}"><button @click="todayDialog.close();openLead(row.name)">Open lead</button></template></CCDataTable></dialog>
<dialog ref="attendanceDialog" class="cc-report-dialog" @close="attendanceOpen=false"><button @click="attendanceDialog.close()">Close staff</button><CCAttendance v-if="attendanceOpen"/></dialog>
</main></div>
</section>
</template>

<style scoped>
.cc-visit-v26 .cc-workspace-head{min-height:48px;height:auto;padding:8px 16px}.cc-report-header-actions{display:flex;gap:7px;flex-wrap:wrap}.cc-report-header-actions button{border:1px solid #ffffff55;background:transparent;color:white;border-radius:6px;padding:6px 9px}.cc-report-tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0}.cc-report-tools button,.cc-report-tools select,.cc-report-summary button,.cc-report-dialog button{border:1px solid #d5b66b;background:#fffdf5;color:#174b30;border-radius:6px;padding:6px 9px;cursor:pointer}.cc-report-summary{background:white;border:1px solid #e3dccb;border-radius:10px;padding:12px;margin:12px 0;min-width:0}.cc-report-summary header,.cc-report-dialog header{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}.cc-report-summary h2{font-size:15px;margin:6px 0}.cc-report-summary .cc-table table{font-size:var(--report-text-size)}.cc-report-summary .cc-cards article{padding:12px;background:#f8f6ed;border:1px solid #e3dccb;border-radius:8px}.cc-report-dialog{width:min(1200px,95vw);max-height:90vh;box-sizing:border-box;overflow:auto;border:1px solid #d5b66b;border-radius:12px;padding:18px;color:#174b30}.cc-report-dialog::backdrop{background:#122e2466}.cc-report-dialog textarea{width:100%;box-sizing:border-box;border:1px solid #e3dccb;padding:12px;font:inherit}.cc-report-tabs{display:grid;grid-template-columns:repeat(6,minmax(125px,1fr));overflow:auto}.cc-visit-v26 :deep(.cc-table){font-size:var(--report-text-size)}button:disabled{opacity:.55;cursor:default}@media(max-width:700px){.cc-report-header-actions{flex-basis:100%}.cc-report-dialog{padding:10px}}@media print{.cc-sidebar,.cc-report-back,.cc-report-tools,.cc-report-tabs,.cc-filters,.cc-report-header-actions,button,dialog{display:none!important}.cc-app-layout{display:block}.cc-main{padding:0}.cc-month-scroll,.cc-table{overflow:visible!important}.cc-month-strip{break-inside:avoid}}
</style>
