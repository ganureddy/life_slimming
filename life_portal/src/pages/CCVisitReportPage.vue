<script setup>
import { provide, computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { session, canAccessTab } from '../lib/session';
import { reportRange, reportGroups, reportDrilldown, aggregateMoney, businessCycle } from '../lib/cc-visit-report';
import CCVisitMonthStrip from '../components/cc/CCVisitMonthStrip.vue';
import CCJourneyReport from '../components/cc/CCJourneyReport.vue';
import CCActivityReport from '../components/cc/CCActivityReport.vue';
import CCNoFollowupReport from '../components/cc/CCNoFollowupReport.vue';
import CCUntouchedReport from '../components/cc/CCUntouchedReport.vue';
import { request } from '../api/http';
import { requestVisitReport } from '../api/cc-visit-report';
import { branchOf, dateRange, downloadCsv, indiaStamp, maskPhone, visitMetrics, visitStatus } from '../lib/cc';
import CCDataTable from '../components/cc/CCDataTable.vue';
import CCPager from '../components/cc/CCPager.vue';
import '../styles/cc.css';
import '../styles/cc-marketing-legacy.css';
import '../styles/cc-agent-legacy.css';
import '../styles/cc-report-theme.css';
import { agentReportKey } from '../lib/cc-agent-report-context';
import { reportTabs, reportRoute } from '../lib/cc-report-navigation';
const route=useRoute(),router=useRouter();
const validDay=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value);
const initial = reportRange('today'), from = ref(validDay(route.query.from)?route.query.from:initial[0]), to = ref(validDay(route.query.to)?route.query.to:initial[1]), period = ref(validDay(route.query.from)?'custom':'today');
const branch = ref(''), agent = ref(''), status = ref(''), search = ref(''), sort = ref('date');
const rows = ref([]), page = ref(1), loading = ref(false), error = ref(''), truncated = ref(false), total = ref(0), scoped = ref(false), applied = ref(null);
const ownerNames=ref({});
const untouchedData=ref(null),activityData=ref(null),agentScope=ref({mode:'all',single:'',multiple:[]});
const financial = ref(null), financialLoading = ref(false), financialError = ref(''), financialPage = ref(1);
const now = ref(indiaStamp()); let clock,changeTimer,changeController;
const newData=ref(false);let changeToken='';
async function checkChanges(){if(document.hidden||!applied.value||changeController)return;const range=applied.value,token=generation;changeController=new AbortController();try{const result=(await request('life_slimming.api.cc_report_activity.changes',{args:range,csrfToken:session.csrf_token,signal:changeController.signal})).message;if(token!==generation||!result?.token)return;if(changeToken&&changeToken!==result.token)newData.value=true;changeToken=result.token;}catch{}finally{changeController=null;}}
let controller, financialController, generation = 0, refreshFinancial = false;
const columns = [
  { key:'branch', label:'Branch', value:branchOf }, { key:'lead_name', label:'Client' },
  { key:'name', label:'Lead ID' }, { key:'mobile_no', label:'Phone', value:r=>maskPhone(r.mobile_no) },
  { key:'lead_owner', label:'CC Agent' }, { key:'custom_appointment_date_and_time', label:'Date / time' },
  { key:'lifeVisit', label:'Visit', value:r=>Number.isFinite(r.lifeVisit)?'V'+r.lifeVisit:'Not verified' },
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
const reportTab=computed(()=>route.meta.reportTab||'visits');
function showReport(tab){router.push(reportRoute(tab,route.query));}
watch(reportTab,tab=>{financialPage.value=1;if(['agents','marketing','consultants'].includes(tab))loadFinancial();});
const grouping=ref('branch'),summarySort=ref('key'),summaryDescending=ref(false),hidden=ref([]),textSize=ref(12),refreshKey=ref(0),agentSubtab=computed(()=>route.meta.agentSubtab||'performance');
const drillDialog=ref(null),drillTitle=ref(''),drillRows=ref([]),drillPage=ref(1),shareDialog=ref(null),shareSections=ref(['visits','groups']),shareNotice=ref('');
const todayDialog=ref(null),todayRows=ref([]),todayBusy=ref(false),todayError=ref('');let todayController;
async function openToday(){await nextTick();todayDialog.value?.showModal();todayController?.abort();todayController=new AbortController();todayBusy.value=true;todayRows.value=[];todayError.value='';try{const day=indiaStamp().slice(0,10);const data=await requestVisitReport({view:'appointments',compact:1,from_date:day,to_date:day},todayController.signal,true);todayRows.value=data.rows||[];if(data.truncated)todayError.value='Only part of today’s appointments could be loaded.';}catch(e){if(e.name!=='AbortError')todayError.value=e.message;}finally{todayBusy.value=false;}}
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
function quickPeriod(value){period.value=value;selectPeriod();load({refresh:true});}
function printReport(){window.print();}
const shareText=computed(()=>{const lines=['LIFE CC REPORT',applied.value?applied.value.from_date+' → '+applied.value.to_date:''];if(shareSections.value.includes('visits'))lines.push('Appointments '+(visitTotals.value.appointments||0)+' | Visits '+(visitTotals.value.visits||0)+' | Booked '+(visitTotals.value.booked||0));if(shareSections.value.includes('groups'))for(const row of summaryGroups.value)lines.push(row.key+': '+row.appointments+' appointments, '+row.visits+' visits, '+row.booked+' booked');if(shareSections.value.includes('paid')){const totals=financial.value?.cc_invoice_report_summary?.totals;lines.push(totals?'PAID BILLS | Invoices '+(totals.invoice_count||0)+' | Billed ₹'+(totals.with_gst||0)+' | Paid ₹'+(totals.paid_with_gst??totals.paid??0)+' | Outstanding ₹'+(totals.balance||0):'PAID BILLS | Load billed totals to include this section.');}if(shareSections.value.includes('activity')){if(activityData.value){lines.push('AGENT | CONVOX | MOBILE | ANSWERED | TALK MIN');for(const row of activityData.value.rows||[])lines.push([row.name,row.convox,row.mobile,row.answered,(row.talk/60).toFixed(1)].join(' | '));}else lines.push('ACTIVITY | Open Agent 360 to load this section.');}if(shareSections.value.includes('untouched'))lines.push('UNTOUCHED | '+(untouchedData.value?.total??'Open the Untouched report to load its total.'));if(shareSections.value.includes('rolling'))for(const item of rolling.value||[])lines.push(item.from+' → '+item.to+': '+item.appointments+' appointments, '+item.visits+' visits, '+item.booked+' booked');return lines.join('\n');});
const shareReady=computed(()=>shareSections.value.length>0&&(!shareSections.value.includes('paid')||!!financial.value)&&(!shareSections.value.includes('activity')||!!activityData.value)&&(!shareSections.value.includes('untouched')||!!untouchedData.value));
async function shareReport(){try{if(navigator.share)await navigator.share({title:'LIFE CC Report',text:shareText.value});else await copyShare();}catch(e){if(e.name!=='AbortError')shareNotice.value=e.message;}}
async function copyShare(){try{await navigator.clipboard.writeText(shareText.value);shareNotice.value='Report copied.';}catch{shareNotice.value='Clipboard access is unavailable. Select and copy the preview text.';}}
async function loadRolling(){if(rollingBusy.value)return;const token=++rollingGeneration;rollingController?.abort();rollingController=new AbortController();rollingBusy.value=true;rollingError.value='';try{const results=await Promise.all([0,-1,-2].map(async offset=>{const [start,end]=businessCycle(applied.value?.to_date||now.value.slice(0,10),offset);const data=await requestVisitReport({view:'appointments',compact:1,from_date:start,to_date:end},rollingController.signal);return {from:start,to:end,partial:!!data.truncated,...visitMetrics((data.rows||[]).filter(r=>(!branch.value||branchOf(r)===branch.value)&&(!agent.value||r.lead_owner===agent.value)),now.value)};}));if(token===rollingGeneration)rolling.value=results;}catch(e){if(token===rollingGeneration&&e.name!=='AbortError')rollingError.value=e.message;}finally{if(token===rollingGeneration)rollingBusy.value=false;}}
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
async function load(options = {}) {
  const refresh = options.refresh === true;
  if(!from.value||!to.value||from.value>to.value){error.value='Choose a valid date range.';return;}
  if(route.query.from!==from.value||route.query.to!==to.value)router.replace(reportRoute(reportTab.value,{...route.query,from:from.value,to:to.value}));
  newData.value=false;changeToken='';changeController?.abort();
  rollingGeneration++;rollingController?.abort();rolling.value=null;rollingBusy.value=false;
  const token=++generation;controller?.abort();financialController?.abort();controller=new AbortController();
  rows.value=[];financial.value=null;activityData.value=null;untouchedData.value=null;financialLoading.value=false;financialError.value='';financialPage.value=1;page.value=1;loading.value=true;error.value='';applied.value=null;truncated.value=false;
  const range={from_date:from.value,to_date:to.value};
  refreshFinancial = refresh;
  try {
    const data=await requestVisitReport({...range,view:'appointments',compact:1,visit_history:1},controller.signal,refresh);
    if(token!==generation)return;
    ownerNames.value=data.agent_names||{};
    rows.value=(data.rows||[]).filter(r=>r.name&&r.lead_owner&&r.custom_appointment_date_and_time);
    total.value=data.total;truncated.value=!!data.truncated;scoped.value=!!data.restricted_to_owner;applied.value=range;
    branch.value='';agent.value='';status.value='';refreshKey.value++;
    if(['agents','marketing','consultants'].includes(reportTab.value))loadFinancial();
  } catch(e){if(token===generation&&e.name!=='AbortError')error.value=e.message;}
  finally{if(token===generation)loading.value=false;}
}
async function loadFinancial(options = {}) {
  if(!applied.value||financialLoading.value||financial.value)return;
  const token=generation;financialController?.abort();financialController=new AbortController();financialLoading.value=true;financialError.value='';
  try{const data=await requestVisitReport(applied.value,financialController.signal,options.refresh === true || refreshFinancial);if(token===generation){financial.value=data;refreshFinancial=false;}}
  catch(e){if(token===generation&&e.name!=='AbortError')financialError.value=e.message;}
  finally{if(token===generation)financialLoading.value=false;}
}
watch(()=>[route.query.from,route.query.to],([start,end])=>{if(validDay(start)&&validDay(end)&&(start!==from.value||end!==to.value)){from.value=start;to.value=end;period.value='custom';load();}});
function exportFinancial(){if(!financial.value||truncated.value)return;const cols=reportTab.value==='agents'?agentColumns:reportTab.value==='marketing'?marketingColumns:invoiceColumns;const source=reportTab.value==='agents'?agentRows.value:reportTab.value==='marketing'?marketingRows.value:invoiceRows.value;downloadCsv('cc-'+reportTab.value+'.csv',cols,source.filter(row=>!agent.value||row.lead_owner===agent.value));}
function exportRows(){if(!truncated.value&&applied.value)downloadCsv(`cc-visits-${applied.value.from_date}-${applied.value.to_date}.csv`,columns,filtered.value);}
onMounted(()=>{load();changeTimer=setInterval(checkChanges,90000);clock=setInterval(()=>{now.value=indiaStamp();},60000);});
onUnmounted(()=>{generation++;controller?.abort();financialController?.abort();clearInterval(clock);todayController?.abort();clearInterval(changeTimer);changeController?.abort();rollingGeneration++;rollingController?.abort();});
provide(agentReportKey, { ownerNames, refreshKey, agentScope, printReport, activityData, agent, agentColumns, agentRows, agentSubtab, agents, applied, branch, branches, cards, columns, consultantGroups, error, exportFinancial, exportRows, filtered, financial, financialColumns, financialError, financialLoading, financialPage, financialRows, from, grouping, hidden, invoiceColumns, invoiceGroups, invoiceRows, loadFinancial, loadRolling, loading, marketingColumns, marketingGroups, marketingRows, openDrill, openLead, page, pages, performanceGroups, reportTab, rolling, rollingBusy, rollingError, rows, search, sort, status, statuses, summaryGroups, summaryOrder, to, toggleSection, total, truncated, untouchedData, visible });
</script>
<template>
<section class="cc-native cc-native-shell cc-report-native cc-visit-v26" :style="{'--report-text-size':textSize+'px'}">
  <header class="cc-workspace-head"><div class="cc-brand"><span class="cc-brand-mark">L</span><div><h1>📊 LIFE BRANCH VISIT REPORT</h1><small>Branch appointments · visits · agent performance</small></div></div><div class="cc-report-header-actions"><button @click="shareNotice='';shareDialog.showModal()" :disabled="!applied||truncated">Share preview</button><button @click="printReport">Print</button><button @click="openToday">Today’s appointments</button></div><RouterLink class="cc-report-back" :to="{name:'leads-native'}">← Back to Dashboard</RouterLink></header>
  <div class="cc-app-layout"><main class="cc-main">

  <nav class="cc-report-tabs" aria-label="CC reports"><RouterLink v-for="tab in reportTabs.filter(tab=>canAccessTab('ccvisit',tab.key))" :key="tab.key" :class="{active:reportTab===tab.key}" :to="reportRoute(tab.key,route.query)">{{tab.label}}</RouterLink></nav>
  <CCVisitMonthStrip v-if="refreshKey>0" :branch="branch" :agent="agent" :refresh-key="refreshKey" @select="selectDay"/>
  <form class="cc-filters" @submit.prevent="load({refresh:true})"><label>Period<select v-model="period" @change="selectPeriod"><option value="today">Today</option><option value="yesterday">Yesterday</option><option value="lastweek">Last Week</option><option value="lastmonth">Last Month</option><option value="tomorrow">Tomorrow</option><option value="week">This Week</option><option value="ten">Next 10 days · including today</option><option value="month">This Month</option><option value="nextmonth">Next Month</option><option value="custom">Custom</option></select></label><label>From<input v-model="from" type="date" required @change="period='custom'"></label><label>To<input v-model="to" type="date" required @change="period='custom'"></label><button type="submit">Apply / refresh</button></form>
  <div class="cc-report-tools"><button v-for="[value,label] in [['today','Today'],['week','This Week'],['lastweek','Last Week'],['month','This Month'],['lastmonth','Last Month']]" :key="value" @click="quickPeriod(value)">{{label}}</button><button @click="resetFilters">Reset filters</button><button @click="toggleSection('cards')">{{hidden.includes('cards')?'Show':'Hide'}} branch cards</button><label>Restore section<select @change="hidden=hidden.filter(s=>s!==$event.target.value);$event.target.value='' "><option value="">Choose…</option><option v-for="key in hidden" :key="key">{{key}}</option></select></label><button aria-label="Smaller report text" @click="textSize=Math.max(10,textSize-1)">A−</button><button aria-label="Larger report text" @click="textSize=Math.min(18,textSize+1)">A+</button></div>
  <nav v-if="reportTab==='agents'" class="cc-report-tools" aria-label="Agent reports"><button v-if="canAccessTab('ccvisit','agents')" @click="showReport('agents')">Performance</button><button v-if="canAccessTab('ccvisit','convox')" @click="showReport('convox')">ConVox dispositions</button><button v-if="canAccessTab('ccvisit','nofollowup')" @click="showReport('nofollowup')">No follow-up</button><button v-if="canAccessTab('ccvisit','untouched')" @click="showReport('untouched')">Untouched</button></nav>
  <button v-if="newData" class="cc-new-data" @click="load({refresh:true})">New data available · Refresh report</button><p v-if="error" role="alert" class="cc-error">{{error}} <button @click="load({refresh:true})">Retry</button></p>
  <p v-if="loading" role="status">Loading appointment schedule…</p>
  <p v-if="applied" role="status">{{applied.from_date}} → {{applied.to_date}} · {{filtered.length}} matching appointments<span v-if="scoped"> · Owner restricted</span></p>
  <p v-if="truncated" role="alert" class="cc-error">Only the first 10,000 records were returned; more appointments exist. Counts are partial; narrow the dates before exporting.</p>
<RouterView v-slot="{Component}"><KeepAlive :max="6"><component :is="Component"/></KeepAlive></RouterView>
<dialog ref="drillDialog" class="cc-report-dialog"><header><h2>{{drillTitle}} ({{drillRows.length}})</h2><button @click="drillDialog.close()">Close</button><button :disabled="truncated" @click="downloadCsv('cc-visit-drilldown.csv',columns,drillRows)">Export CSV</button></header><CCDataTable :columns="columns" :rows="drillRows.slice((drillPage-1)*40,drillPage*40)"><template #actions="{row}"><button @click="drillDialog.close();openLead(row.name)">Open lead</button></template></CCDataTable><CCPager :page="drillPage" :pages="Math.max(1,Math.ceil(drillRows.length/40))" @change="drillPage=$event"/></dialog>
<dialog ref="shareDialog" class="cc-report-dialog"><h2>Report share preview</h2><div class="cc-report-tools"><label v-for="key in ['visits','groups','paid','activity','untouched',...(rolling?['rolling']:[])]" :key="key"><input v-model="shareSections" type="checkbox" :value="key">{{key}}</label></div><p v-if="shareSections.includes('paid')&&!financial"><button :disabled="financialLoading" @click="loadFinancial">Load billed totals for sharing</button></p><p v-if="shareSections.includes('activity')&&!activityData"><button @click="shareDialog.close();showReport('agent360')">Open Agent 360 to load call totals</button></p><p v-if="shareSections.includes('untouched')&&!untouchedData"><button @click="shareDialog.close();showReport('untouched')">Open Untouched report</button></p><div class="cc-share-table"><table><tbody><tr v-for="(line,index) in shareText.split('\n')" :key="index"><td v-for="(cell,i) in line.split(' | ')" :key="i">{{cell}}</td></tr></tbody></table></div><textarea :value="shareText" readonly aria-label="Report preview" rows="14"></textarea><p role="status">{{shareNotice}}</p><button :disabled="!shareReady" @click="copyShare">Copy report</button><button :disabled="!shareReady" @click="shareReport">Share selected sections</button><a v-if="shareReady" :href="'https://wa.me/?text='+encodeURIComponent(shareText)" target="_blank" rel="noopener noreferrer">WhatsApp</a><button @click="shareDialog.close()">Close</button></dialog>
<dialog ref="todayDialog" class="cc-report-dialog" @close="todayController?.abort()"><header><h2>Today’s appointments</h2><button @click="todayDialog.close()">Close appointments</button></header><p v-if="todayError" role="alert" class="cc-error">{{todayError}}</p><CCDataTable :columns="columns" :rows="todayRows" :busy="todayBusy"><template #actions="{row}"><button @click="todayDialog.close();openLead(row.name)">Open lead</button></template></CCDataTable></dialog>
</main></div>
</section>
</template>

<style scoped src="../styles/cc-agent-report.css"></style>
