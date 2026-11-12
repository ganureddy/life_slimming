<script setup>
import { activeCcAgents } from "../lib/cc-agents";
import { openConvoxHistory } from "../lib/convox-history";
import { provide, reactive, computed, watch, nextTick, onMounted, onUnmounted, onBeforeUnmount, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ccCore } from '../api/cc-core';
import { journeyFlags, matchesJourney } from '../lib/cc-journey';
import { ccCall } from '../api/cc';
import { convoxApi } from '../api/convox';
import { request } from '../api/http';
import { dateRange, maskPhone, downloadCsv } from '../lib/cc';
import { enquiryDate, mergeEnquiryRows, enquiryLabel, repeatEnquiryRows } from '../lib/cc-enquiry';
import { ccDashboardGroup } from '../lib/cc-dashboard-groups';
import { session } from '../lib/session';
import CCMobileCallPopup from '../components/cc/CCMobileCallPopup.vue';
import '../styles/cc.css';
import '../styles/cc-legacy.css';
import '../styles/cc-runtime.css';
import ccReference from '../data/cc-reference.json';
import { ccRoute, ccViewOfRoute } from '../lib/cc-navigation';
import { ccDashboardKey } from '../lib/cc-dashboard-context';
const [today] = dateRange('today');
const router=useRouter();
const route=useRoute();
const routeValue=value=>Array.isArray(value)?String(value[0]||''):String(value||'');
const validDate=value=>/^\d{4}-\d{2}-\d{2}$/.test(value);
const from = ref(validDate(routeValue(route.query.from))?routeValue(route.query.from):today), to = ref(validDate(routeValue(route.query.to))?routeValue(route.query.to):today), mode = ref(['created','posting','updated'].includes(routeValue(route.query.mode))?routeValue(route.query.mode):'created'), query = ref('');
const rows = ref([]), total = ref(0), page = ref(1), more = ref(false), searching = ref(false), scoped = ref(false);
const queueOwner=ref('');
const tlCollapsed=ref(false);
const queueFlag=ref(''),journeys=ref({}),journeyError=ref('');

let journeyGeneration=0;
onBeforeUnmount(()=>journeyGeneration++);
watch(rows,async values=>{const token=++journeyGeneration;journeys.value={};journeyError.value='';try{for(let i=0;i<values.length;i+=500){const result=await ccCore('summary',{leads:JSON.stringify(values.slice(i,i+500).map(r=>r.name))});if(token!==journeyGeneration)return;journeys.value={...journeys.value,...result.leads};}}catch(e){if(token===journeyGeneration)journeyError.value=e.message;}});


const matrixFilter=ref(null);
const queueStatus=ref(''), queueCategory=ref(''), queueSubStatus=ref(''), queueSearch=ref('');
const incomplete=ref(false);
const createdIds=ref(new Set()), appointmentCohort=ref([]);
const contactManager = ref(false);
const loading = ref(false), error = ref(''), applied = ref('');
const tlConfig=ref(null),tlConfigBusy=ref(false),tlConfigError=ref(''),tlPreviewSource=ref(''),tlPreview=ref(null),tlPreviewBusy=ref(false),tlPreviewError=ref('');
const salesData=ref(null),salesBusy=ref(false),salesError=ref(''),salesSearch=ref(''),salesLoadedRange=ref('');let salesRequest=0;
const summaryLead=ref(null);
function viewLead(row){summaryLead.value=row;nextTick(()=>dialog.value?.showModal())}
const dialog = ref(null), leadHistoryDialog=ref(null), leadHistoryLead=ref(null), leadHistoryRows=ref([]), leadHistoryBusy=ref(false), leadHistoryError=ref(''), detail = ref(null), detailLoading = ref(false), detailError = ref('');
let historyGeneration=0;
async function openLeadHistory(row){const token=++historyGeneration;leadHistoryLead.value=row;leadHistoryRows.value=[];leadHistoryError.value='';leadHistoryBusy.value=true;await nextTick();leadHistoryDialog.value?.showModal();try{const result=await ccCall('cc_get_lead_history',{lead:row.name});if(token!==historyGeneration)return;leadHistoryRows.value=Array.isArray(result)?result:result?.rows||[]}catch(error){if(token===historyGeneration)leadHistoryError.value=error.message||'Could not load lead history.'}finally{if(token===historyGeneration)leadHistoryBusy.value=false}}
const createBusy = ref(false), createError = ref(''),
  createForm = ref({first_name:'', mobile_no:'', phone:'', email_id:'', age:'', gender:'', city:'', source:'', branch:'', category:'', lead_owner:'', enquired_for:'', custom_remarks:''});
const matchNotice=ref('');
const createDuplicate=ref(null),createSources=ref([]),createBranches=ref([]),createCategories=ref([]),createMastersLoading=ref(false);
const followup = ref({stage:'', sub_status:'', status:'', next_followup:'', conclusion:'', remarks:''});
const savingFollowup = ref(false), actionError = ref(''), actionNotice = ref('');
const viewNames=['create','testing','dashboard','queue','followup','worksheet','tl','reports','assign','duplicates','scripts','faq','treatments','objections','branches','doctors','distribution'];
const initialView=ccViewOfRoute(route);
const selectedView = ref(viewNames.includes(initialView)?initialView:'dashboard');

function pageQuery(){const {view,lead,history,...queryParams}=route.query;return {...queryParams,from:from.value||undefined,to:to.value||undefined,mode:mode.value==='created'?undefined:mode.value};}
watch([from,to,mode],()=>{
  const queryParams={...route.query,from:from.value||undefined,to:to.value||undefined,mode:mode.value==='created'?undefined:mode.value};
  if(['from','to','mode'].some(key=>String(route.query[key]||'')!==String(queryParams[key]||'')))router.replace({query:queryParams});
});
watch(()=>[route.meta.ccView,route.params.leadId,route.query.from,route.query.to,route.query.mode],([view,leadId,start,end,dateMode])=>{
  let nextView=viewNames.includes(view)?view:'dashboard';
  if(['assign','duplicates'].includes(nextView)&&!canManageLeads.value){router.replace(ccRoute('dashboard',pageQuery()));return;}
  const nextFrom=validDate(routeValue(start))?routeValue(start):today;
  const nextTo=validDate(routeValue(end))?routeValue(end):today;
  const nextMode=['created','posting','updated'].includes(routeValue(dateMode))?routeValue(dateMode):'created';
  const changedRange=from.value!==nextFrom||to.value!==nextTo||mode.value!==nextMode;
  from.value=nextFrom;to.value=nextTo;mode.value=nextMode;
  if(changedRange){selectedView.value=nextView;apply();initializeView(nextView);}
  else if(nextView!==selectedView.value)showView(nextView,false);
  if(nextView==='followup'&&leadId&&detail.value?.name!==leadId)openDetail({name:routeValue(leadId)});
  else if(nextView==='followup'&&!leadId&&detail.value){stopCall();detailGeneration++;detailController?.abort();detail.value=null;}
});
const ownerRoles=['System Manager','Call Center Export','Sales Manager'];
const canEditLeadOwner=computed(()=>ownerRoles.some(role=>session.roles.includes(role)));
const canManageLeads=canEditLeadOwner;
const canViewSourceReports=computed(()=>[...ownerRoles,'Team Lead','TL'].some(role=>session.roles.includes(role))||contactManager.value);
const groupPanel = ref('');
const globalSearch=ref(''), globalMatches=ref([]), globalSearchBusy=ref(false), globalSearchError=ref(''), globalSearchMore=ref(false);
let globalSearchTimer, globalSearchController, globalSearchGeneration=0;
watch(globalSearch, value=>{
  clearTimeout(globalSearchTimer);globalSearchController?.abort();
  const token=++globalSearchGeneration, term=value.trim();
  globalMatches.value=[];globalSearchError.value='';globalSearchMore.value=false;globalSearchBusy.value=false;
  if(term.length<2)return;
  globalSearchBusy.value=true;
  globalSearchTimer=setTimeout(async()=>{
    const controller=new AbortController();globalSearchController=controller;
    try{
      const data=await ccCall('cc_get_leads',{query:term},controller.signal);
      if(token!==globalSearchGeneration)return;
      globalMatches.value=(data.rows||[]).map(lead=>({lead,title:(lead.lead_name||lead.first_name||lead.name)+' · '+maskPhone(lead.mobile_no),sub:lead.name+' · '+(lead.custom_cc_sub_status||lead.status||'')}));
      globalSearchMore.value=!!data.more;
    }catch(error){if(token===globalSearchGeneration&&error.name!=='AbortError')globalSearchError.value='Search unavailable. Please try again.'}
    finally{if(token===globalSearchGeneration)globalSearchBusy.value=false}
  },250);
});
function chooseGlobal(item){openDetail(item.lead);globalSearch.value=''}
const repeatWebsiteRows=computed(()=>repeatEnquiryRows(rows.value.filter(row=>canManageLeads.value||row.lead_owner===session.user),from.value,to.value));
const myLeads = computed(()=>rows.value.filter(row=>createdIds.value.has(row.name)&&row.lead_owner===session.user));
const tileDialog=ref(null),tileTitle=ref(''),tileRows=ref([]),tileOwner=ref('');
function closeTileOnBackdrop(event){if(event.target!==tileDialog.value)return;const rect=tileDialog.value.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)tileDialog.value.close();}
const filteredTileRows=computed(()=>tileRows.value.filter(row=>!tileOwner.value||row.lead_owner===tileOwner.value));
const tileOwners=computed(()=>{const owners=new Map();for(const row of tileRows.value)if(row.lead_owner)owners.set(row.lead_owner,{id:row.lead_owner,name:row.lead_owner_name||row.lead_owner});return [...owners.values()].sort((a,b)=>a.name.localeCompare(b.name))});
function openTile(kind){
  const created=rows.value.filter(row=>createdIds.value.has(row.name));
  const apptToday=row=>String(row.custom_appointment_date_and_time||'').slice(0,10)===todayISO;
  const createdToday=row=>String(row.creation||'').slice(0,10)===todayISO;
  const groups={
    assigned:['All Assigned Leads',created],
    repeat:['Repeat Website Enquiries',repeatWebsiteRows.value],
    mine:['My Leads — selected date range',myLeads.value],
    untouched:['Untouched Leads',created.filter(row=>row.custom_cc_stage==='UNTOUCHED')],
    followup:['FOLLOW UPS',dashboardGroups.value.followup],
    norespnotreach:['NOT RESPONDING / NOT REACHABLE',dashboardGroups.value.norespnotreach],
    invalid:['INVALID',dashboardGroups.value.invalid],
    nid:['NID',dashboardGroups.value.nid],
    success:['Successful Conversions',created.filter(row=>row.custom_cc_stage==='SUCCESS')],
    appts:['Appointments Booked',appointmentRows.value],
    apptsame:['Created & Appt Today',created.filter(row=>apptToday(row)&&createdToday(row))],
    apptdiff:['Older Lead, Appt Today',created.filter(row=>apptToday(row)&&!createdToday(row))],
    converted:['Converted',convertedRows.value],
    convsame:['Created & Converted Today',convertedRows.value.filter(row=>apptToday(row)&&createdToday(row))],
    convdiff:['Older Lead Converted',convertedRows.value.filter(row=>apptToday(row)&&!createdToday(row))],
  };
  tileOwner.value='';[tileTitle.value,tileRows.value]=groups[kind];nextTick(()=>tileDialog.value?.showModal());
}
const knowledgeTab = ref('scripts'), faqSearch = ref(''), doctorRows = ref([]), doctorLoading = ref(false), doctorError = ref(''), copyNotice = ref(''), doctorBranches = ref([]), doctorBranch = ref('');
const scripts = ccReference.CALL_SCRIPTS, objections = ccReference.OBJECTIONS, faqs = ccReference.FAQS, treatments = ccReference.TREATMENT_KB, branches = ccReference.BRANCHES;
const filteredFaqs = computed(()=>faqs.filter(item=>!faqSearch.value.trim()||`${item.cat} ${item.q} ${item.a}`.toLowerCase().includes(faqSearch.value.trim().toLowerCase())));
function leadHistoryChanges(event){try{return (JSON.parse(event.data||'{}').changed||[]).filter(change=>['status','custom_cc_stage','custom_cc_sub_status','lead_owner','custom_appointment_status','branch','lead_assign_to_branch','custom_next_followup_date','custom_conclusion_remark','source'].includes(change[0]))}catch{return []}}
const stages = ['UNTOUCHED','FOLLOW-UP','SUCCESS','LOST','INVALID'];
const leadHistoryLabels={status:'Status',custom_cc_stage:'CC Stage',custom_cc_sub_status:'Sub-status',lead_owner:'Lead Owner',custom_appointment_status:'Appointment',branch:'Branch',lead_assign_to_branch:'Assigned Branch',custom_next_followup_date:'Next Follow-up',custom_conclusion_remark:'Conclusion',source:'Source'};
const stageCounts = computed(()=>Object.fromEntries(stages.map(stage=>[stage,rows.value.filter(r=>(stage==='FOLLOW-UP'||createdIds.value.has(r.name))&&(r.custom_cc_stage||r.status)===stage).length])));
const sourceCounts = computed(()=>{const counts={};rows.value.forEach(r=>{const key=r.source||r.custom_media||'Unknown';counts[key]=(counts[key]||0)+1});return Object.entries(counts).sort((a,b)=>b[1]-a[1]).slice(0,12)});
const categoryCounts=computed(()=>{const counts={};rows.value.forEach(row=>String(row.custom_treatment_interests||'').split(';').map(value=>value.trim()).filter(Boolean).forEach(value=>counts[value]=(counts[value]||0)+1));return Object.entries(counts).sort((a,b)=>b[1]-a[1])});
const subStatusCounts=computed(()=>{const counts={};rows.value.forEach(row=>{const key=row.custom_cc_sub_status||'(none)';counts[key]=(counts[key]||0)+1});return Object.entries(counts).sort((a,b)=>b[1]-a[1])});
const pipelineRows=computed(()=>rows.value.filter(row=>row.custom_pipeline_date_and_time).slice().sort((a,b)=>String(a.custom_pipeline_date_and_time).localeCompare(String(b.custom_pipeline_date_and_time))));
function reportMatrix(field){const groups={};for(const row of rows.value){const key=row[field]||'(unassigned)',sub=row.custom_cc_sub_status||'(none)';(groups[key]||={})[sub]=((groups[key]||{})[sub]||0)+1}return Object.entries(groups).sort((a,b)=>a[0].localeCompare(b[0]))}
const matrixStatuses=computed(()=>[...new Set(rows.value.map(row=>row.custom_cc_sub_status||'(none)'))].sort());
const matrixRows=field=>{const groups={};for(const row of rows.value){const key=row[field]||'(none)';const group=groups[key]||={key,counts:{},total:0};const status=row.custom_cc_sub_status||'(none)';group.counts[status]=(group.counts[status]||0)+1;group.total++}return Object.values(groups).sort((a,b)=>b.total-a.total)};
function openMatrixCell(field,key,status){queueSearch.value='';queueOwner.value='';queueStatus.value='';queueSubStatus.value='';queueCategory.value='';matrixFilter.value={field,key,status};showView('queue');page.value=1}
function matrixMatches(row){const filter=matrixFilter.value;return !filter||((row[filter.field]||'(none)')===filter.key&&(!filter.status||(row.custom_cc_sub_status||'(none)')===filter.status))}
function exportMatrixCsv(field){
  if(incomplete.value || searching.value){error.value='Choose a complete date range before exporting report totals.';return;}
  const statuses=matrixStatuses.value;
  const columns=[{key:'key',label:'Group'},...statuses.map((status,index)=>({key:'s'+index,label:status})),{key:'total',label:'Total'}];
  const output=matrixRows(field).map(row=>({key:row.key,...Object.fromEntries(statuses.map((status,index)=>['s'+index,row.counts[status]||0])),total:row.total}));
  output.push({key:'Total',...Object.fromEntries(statuses.map((status,index)=>['s'+index,rows.value.filter(row=>(row.custom_cc_sub_status||'(none)')===status).length])),total:rows.value.length});
  downloadCsv(`cc-${field}-sub-status.csv`,columns,output);
}

const agentRows = computed(()=>{const grouped={};rows.value.forEach(r=>{const key=r.lead_owner||'Unassigned';(grouped[key] ||= []).push(r)});return Object.entries(grouped).map(([name,items])=>({name,total:items.length,called:items.filter(r=>Number(r.custom_call_count)>0).length,success:items.filter(r=>(r.custom_cc_stage||r.status)==='SUCCESS').length,followups:items.filter(r=>r.custom_next_followup_date).length}))});
const tlSearch=ref(''),tlOwner=ref(''),tlStatus=ref(''),tlPage=ref(1);
const tlFiltered=computed(()=>rows.value.filter(row=>(!tlOwner.value||row.lead_owner===tlOwner.value)&&(!tlStatus.value||(row.custom_cc_stage||row.status)===tlStatus.value)&&(!tlSearch.value.trim()||[row.name,row.lead_name,row.mobile_no,row.city,row.lead_owner,row.source].some(value=>String(value||'').toLowerCase().includes(tlSearch.value.trim().toLowerCase())))));
const tlPages=computed(()=>Math.max(1,Math.ceil(tlFiltered.value.length/10)));
const tlVisible=computed(()=>tlFiltered.value.slice((tlPage.value-1)*10,tlPage.value*10));
const assignmentEnquiries=computed(()=>[...new Set(rows.value.map(row=>row.enquired_for).filter(Boolean))].sort());
const duplicatePages=computed(()=>Math.max(1,Math.ceil(duplicateFiltered.value.length/20)));
const duplicateVisible=computed(()=>duplicateFiltered.value.slice((duplicatePage.value-1)*20,duplicatePage.value*20));
const salesInvoiceRows=computed(()=>salesData.value?.cc_invoice_report_summary?.rows||[]);
const visibleSalesRows=computed(()=>canManageLeads.value?salesInvoiceRows.value:salesInvoiceRows.value.filter(row=>row.lead_owner===session.user));
const salesSummary=computed(()=>salesData.value?.cc_invoice_report_summary?.totals||{});
const salesOwnerName=row=>row.lead_owner_name||salesData.value?.agent_names?.[row.lead_owner]||row.lead_owner||'Unknown';
const salesFilteredRows=computed(()=>{const q=salesSearch.value.trim().toLowerCase();return visibleSalesRows.value.filter(row=>!q||[row.lead_name,row.lead,row.invoice,row.customer,row.lead_owner,salesData.value?.agent_names?.[row.lead_owner],row.branch].some(value=>String(value||'').toLowerCase().includes(q)))});
const salesAgentRows=computed(()=>{const groups={};visibleSalesRows.value.forEach(row=>{const key=salesOwnerName(row);const g=groups[key]||=( {name:key,count:0,billed:0,paid:0,balance:0});g.count++;g.billed+=Number(row.with_gst)||0;g.paid+=Number(row.paid_with_gst??row.paid)||0;g.balance+=Number(row.balance)||0});return Object.values(groups).sort((a,b)=>b.paid-a.paid)});
const visibleSalesSummary=computed(()=>visibleSalesRows.value.reduce((sum,row)=>{sum.with_gst+=Number(row.with_gst)||0;sum.paid+=Number(row.paid_with_gst??row.paid)||0;sum.balance+=Number(row.balance)||0;sum.invoice_count++;return sum},{with_gst:0,paid:0,balance:0,invoice_count:0}));
const salesClientRows=computed(()=>{const groups={};visibleSalesRows.value.forEach(row=>{const key=row.lead||row.customer||row.lead_name||'Unknown client';const group=groups[key]||=( {key,label:row.lead_name||row.customer||row.lead||'Unknown client',lastInvDate:'',count:0,billed:0,paid:0,outstanding:0});const date=row.invoice_date||'';if(date>group.lastInvDate)group.lastInvDate=date;group.count++;group.billed+=Number(row.with_gst)||0;group.paid+=Number(row.paid_with_gst??row.paid)||0;group.outstanding+=Number(row.balance)||0});return Object.values(groups).sort((a,b)=>b.billed-a.billed)});
const salesClientSearch=ref(''),salesClientPage=ref(1);
const salesClientFiltered=computed(()=>{const q=salesClientSearch.value.trim().toLowerCase();return salesClientRows.value.filter(row=>!q||row.label.toLowerCase().includes(q)||row.key.toLowerCase().includes(q))});
const salesClientPages=computed(()=>Math.max(1,Math.ceil(salesClientFiltered.value.length/10)));
const salesClientVisible=computed(()=>salesClientFiltered.value.slice((salesClientPage.value-1)*10,salesClientPage.value*10));
const money=value=>'₹'+Number(value||0).toLocaleString('en-IN',{maximumFractionDigits:0});
const appointmentRows = computed(()=>appointmentCohort.value);
const appointmentStatusCounts=computed(()=>{const counts={};appointmentRows.value.forEach(row=>{const key=row.custom_appointment_status||'Unspecified';counts[key]=(counts[key]||0)+1});return Object.entries(counts).sort((a,b)=>b[1]-a[1])});
const appointmentAgentRows=computed(()=>{const groups={};appointmentRows.value.forEach(row=>{const key=row.lead_owner||'(unassigned)',group=groups[key]||=( {key,name:row.lead_owner_name||key,booked:0,vb:0,vnb:0,nv:0,cancelled:0,pending:0,converted:0,branches:{},billed:0,paid:0});group.booked++;const status=String(row.custom_appointment_status||'').toLowerCase();if(status==='visited booked'){group.vb++;group.converted++}else if(status==='visited not booked')group.vnb++;else if(status==='not visited')group.nv++;else if(status==='cancelled')group.cancelled++;else group.pending++;const branch=row.lead_assign_to_branch||row.branch;if(branch)group.branches[branch]=(group.branches[branch]||0)+1;});const leadAgent={};appointmentRows.value.forEach(row=>leadAgent[row.name]=row.lead_owner||'(unassigned)');salesInvoiceRows.value.forEach(row=>{const key=leadAgent[row.lead_id||row.lead];if(!key||!groups[key])return;groups[key].billed+=Number(row.with_gst??row.grand_total)||0;groups[key].paid+=Number(row.paid_with_gst??row.paid_amount??row.paid)||0});return Object.values(groups).map(group=>({...group,visited:group.vb+group.vnb,rate:group.booked?Math.round(group.converted*100/group.booked):0,preferredBranch:Object.entries(group.branches).sort((a,b)=>b[1]-a[1])[0]?.[0]||'—'})).sort((a,b)=>b.converted-a.converted||b.booked-a.booked)});
const recoveryFlags=computed(()=>[{flag:'Appointment Missed',label:'🚨 No-show recovery'},{flag:'Visited - Not Booked',label:'🏥 Post-consult closing'},{flag:'unreachable',label:'⚠ Unreachable 3+'},{flag:'overdue',label:'⏰ Follow-up overdue'}].map(item=>({...item,count:rows.value.filter(row=>matchesJourney(journeys.value[row.name],item.flag)).length})));
function openRecovery(flag){queueFlag.value=flag;showView('queue');}
const dashQueueRows = computed(()=>rows.value.filter(r=>['UNTOUCHED','FOLLOW-UP'].includes(r.custom_cc_stage||r.status)).slice(0,60));
const reminderRows = computed(()=>rows.value.filter(r=>r.custom_next_followup_date||['Call Back','Get Back','Followup'].includes(r.status)));
const reminderBuckets = computed(()=>({overdue:reminderRows.value.filter(r=>r.custom_next_followup_date&&String(r.custom_next_followup_date).slice(0,10)<todayISO),today:reminderRows.value.filter(r=>String(r.custom_next_followup_date||'').slice(0,10)===todayISO),upcoming:reminderRows.value.filter(r=>String(r.custom_next_followup_date||'').slice(0,10)>todayISO),nodate:reminderRows.value.filter(r=>!r.custom_next_followup_date)}));
const todayISO = dateRange('today')[0];
const dashboardGroups = computed(()=>{
  const groups={followup:[],norespnotreach:[],invalid:[],nid:[]};
  for(const row of rows.value){
    const group=ccDashboardGroup(row);
    if(group && (group==='followup'||createdIds.value.has(row.name))) groups[group].push(row);
  }
  return groups;
});
const convertedRows = computed(()=>rows.value.filter(r=>createdIds.value.has(r.name)&&r.custom_appointment_status==='Visited Booked'));
const sameDayAppointments = computed(()=>rows.value.filter(r=>createdIds.value.has(r.name)&&String(r.custom_appointment_date_and_time||'').slice(0,10)===todayISO&&String(r.creation||'').slice(0,10)===todayISO).length);
const olderLeadAppointments = computed(()=>rows.value.filter(r=>createdIds.value.has(r.name)&&String(r.custom_appointment_date_and_time||'').slice(0,10)===todayISO&&String(r.creation||'').slice(0,10)!==todayISO).length);
const sameDayConverted = computed(()=>convertedRows.value.filter(r=>String(r.custom_appointment_date_and_time||'').slice(0,10)===todayISO&&String(r.creation||'').slice(0,10)===todayISO).length);
const olderConverted = computed(()=>convertedRows.value.filter(r=>String(r.custom_appointment_date_and_time||'').slice(0,10)===todayISO&&String(r.creation||'').slice(0,10)!==todayISO).length);
async function copyText(value){try{await navigator.clipboard.writeText(value);copyNotice.value='Copied to clipboard.'}catch{copyNotice.value='Clipboard access is unavailable in this browser.'}setTimeout(()=>copyNotice.value='',2500)}
const directoryManagers=ref([]),directoryLoaded=ref(false);
const doctorDesignations=['Doctor','Consultant Doctor','Doctor Consultant','Assistant Doctor','Dermatologist','Chief HT Surgeon','HOD Hair transplant surgery'];
const managerDesignations=['Center Manager','Assistant Centre Manager','ACM','ACM(TRAINEE)','CM(TRAINEE)'];
async function directoryEmployees(designations){
  const rows=[];
  for(let start=0;;start+=500){
    const response=await request('frappe.client.get_list',{args:{doctype:'Employee',fields:['name','employee_name','designation','branch','cell_number'],filters:{status:'Active',designation:['in',designations]},order_by:'branch asc, name asc',limit_start:start,limit_page_length:500},csrfToken:session.csrf_token});
    const batch=response.message||[];rows.push(...batch);if(batch.length<500)return rows;
  }
}
async function loadDoctors(){
  if(doctorLoading.value)return;
  doctorLoading.value=true;doctorError.value='';
  const results=await Promise.allSettled([directoryEmployees(doctorDesignations),directoryEmployees(managerDesignations)]);
  doctorRows.value=results[0].status==='fulfilled'?results[0].value:[];
  directoryManagers.value=results[1].status==='fulfilled'?results[1].value:[];
  if(results.some(result=>result.status==='rejected'))doctorError.value='Some employee directory data is unavailable for your login.';
  doctorBranches.value=[...new Set(doctorRows.value.map(row=>row.branch||'Head Office / Unassigned'))].sort();
  directoryLoaded.value=true;doctorLoading.value=false;
}
function branchManager(branch,assistant=false){return directoryManagers.value.find(row=>row.branch===branch&&(assistant?['Assistant Centre Manager','ACM','ACM(TRAINEE)']:['Center Manager','CM(TRAINEE)']).includes(row.designation))?.employee_name||'Not assigned'}
let tlConfigPromise;
async function loadTlConfig(refresh=false){
  if(tlConfigPromise)return tlConfigPromise;
  if(tlConfig.value&&!refresh)return tlConfig.value;
  tlConfigBusy.value=true;tlConfigError.value='';
  tlConfigPromise=(async()=>{try{tlConfig.value=await ccCall('lead_assignment_configuration',{action:'get'});return tlConfig.value;}catch(e){tlConfigError.value=e.message||'Assignment settings are unavailable for this account.';}finally{tlConfigBusy.value=false;tlConfigPromise=null;}})();
  return tlConfigPromise;
}
async function previewTlAssignment(){if(!tlPreviewSource.value.trim()){tlPreviewError.value='Select a lead source to preview assignment.';return}tlPreviewBusy.value=true;tlPreviewError.value='';try{tlPreview.value=await ccCall('lead_assignment_preview',{source:tlPreviewSource.value.trim()})}catch(e){tlPreviewError.value=e.message||'Could not preview lead assignment.'}finally{tlPreviewBusy.value=false}}
async function loadSales(preserve=false){if(!preserve){salesData.value=null;salesClientPage.value=1;}const token=++salesRequest,range=`${from.value}|${to.value}`;salesBusy.value=true;salesError.value='';try{const data=await ccCall('life_cc_agent_marketing_data',{from_date:from.value,to_date:to.value});if(token!==salesRequest)return;salesData.value=data;salesLoadedRange.value=range}catch(e){if(token===salesRequest)salesError.value=e.message||'Call-centre invoice report is unavailable.'}finally{if(token===salesRequest)salesBusy.value=false}}
function showView(view,navigate=true){
  if(['assign','duplicates'].includes(view)&&!canManageLeads.value)view='dashboard';
  const changed=selectedView.value!==view;selectedView.value=view;detail.value=null;
  if(navigate&&ccViewOfRoute(route)!==view)router.push(ccRoute(view,pageQuery()));
  initializeView(view);
  if(changed&&view==='duplicates'){generation++;controller?.abort();loading.value=false;loadDuplicateLeads();}
  else if(changed&&['dashboard','queue','followup','tl','reports','assign'].includes(view)&&(view!=='followup'||searching.value)){
    const key=leadDataKey();
    if(!(loading.value&&activeLeadKey===key)&&!(loadedLeadKey===key&&Date.now()-leadLoadedAt<60000))load(1,{preserveSelection:view==='assign'});
  }
}
function initializeView(view){
  if(['doctors','branches'].includes(view)&&!directoryLoaded.value)loadDoctors();
  if(view==='tl'&&!tlConfig.value&&!tlConfigError.value)loadTlConfig();
  if(view==='reports'&&!salesBusy.value&&salesLoadedRange.value!==`${from.value}|${to.value}`)loadSales();
  if(['assign','create'].includes(view))loadCreateMasters();
}
function printReport(){window.print()}
const callOutcomes = ['No Response','Not Reachable','Switch OFF','Call Disconnected','Appointment no response','Invalid Number','Wrong number','Not in Service','Callback: Scheduled','Price Negotiation','Get Back','Very Positive','Call & Confirm','Out Station','Appointment Booked','Existing Client','Walked In & Booked','Walked In: Not Booked','Not Interested','Other clinic','Joined Competition','Do Not Contact','Job enquiry','Franchise Lead','Junk/Wrong Call','Not Enquired','TNA','NID'];
const steps = ['Source','Personal','Location','Treatment','Assessment','Status','Action'];
const activeStep = ref(0);
const categoryInterests = {
  'Slimming':['Weight Loss Programs','Inch Loss / Body Contouring','Fat Reduction','Nutrition & Diet Consultation','Metabolic & Lifestyle Management','Wellness Programs','Lifestyle Management','CoolSculpting / Cryolipolysis','HIFU Fat Reduction','RF Body Tightening','Body Contouring','EMS Muscle Stimulation','GLP-1 Program','LIFE RISE – Weight Management'],
  'Skin / Dermat':['Acne & Acne Scar Treatment','Pigmentation & Melasma','Skin Brightening','Anti-Aging Treatments','Laser Treatments','Chemical Peels','Skin Infections','General Dermatology','HydraFacial','Carbon Laser Facial','Skin Rejuvenation','Skin Tightening','Mole/Wart Removal','Anti-Tan Treatment','MNRF','Microneedling'],
  'Hair Patch':['Hair Patch Consultation','Hair Patch Maintenance'],
  Hair:['Hair Fall Treatment','Hair Regrowth Therapy','PRP Hair Treatment','GFC Hair Treatment','Mesotherapy','Dandruff & Scalp Treatment','Stem Cell Hair Therapy','Hair Transplant Consultation','Non-Surgical Hair Replacement'],
  'HT (Hair Transplant)':['Hair Transplant (FUE)','Hair Transplant (DHI)','Hair Transplant (FUT)','Beard Transplant'],
  Laser:['Laser Hair Removal (LHR)','Q-Switch Laser','Tattoo Removal'],
  Aesthetics:['Botox','Dermal Fillers','Botox + Fillers Combo'],
  'Life Rise':['Lifestyle Counseling','Nutritional Guidance','Preventive Health Programs','Health & Wellness Coaching','Lifestyle Disease Management','LIFE RISE – GLP Program','LIFE RISE – Nutrition Program','LIFE RISE – Gut Health Program'],
  'Online Consultation':['Online Consultation'],
};
const treatmentCategories = Object.keys(categoryInterests);
const treatmentInterests = computed(()=>[...new Set(selectedCategories.value.flatMap(category=>categoryInterests[category]||[]))]);
const leadDraft = ref({}), selectedCategories=ref([]), selectedInterests=ref([]), actionType=ref(''), historyRows=computed(()=>detail.value?.workflow_hint?.legacy_events||[]);
const stepComplete=computed(()=>[!!leadDraft.value.source,!!leadDraft.value.first_name&&!!leadDraft.value.gender,!!leadDraft.value.city,selectedCategories.value.length>0,!!(leadDraft.value.weight||leadDraft.value.medical_history),!!followup.value.sub_status,!!actionType.value]);
const progress=computed(()=>Math.round(stepComplete.value.filter(Boolean).length*100/steps.length));
const callSeconds=ref(0), callRunning=ref(false); let callInterval, autoRefreshTimer;
const callClock=computed(()=>`${String(Math.floor(callSeconds.value/60)).padStart(2,'0')}:${String(callSeconds.value%60).padStart(2,'0')}`);
function startCall(){if(callRunning.value||!detail.value)return;window.dispatchEvent(new CustomEvent('life-convox-native',{detail:{type:'life-convox-call',lead_id:detail.value.name,onResult:result=>{if(!result.success){actionError.value=result.message||'Call could not be started.';return;}callRunning.value=true;callSeconds.value=0;callInterval=setInterval(()=>callSeconds.value++,1000);}}}));}
function openPhone(){window.dispatchEvent(new CustomEvent('life-convox-native',{detail:{type:'life-convox-open',lead_id:detail.value?.name}}));}
function stopCall(){callRunning.value=false;clearInterval(callInterval);}
function goStep(index){activeStep.value=index;document.getElementById('cc-form-step-'+index)?.scrollIntoView({behavior:'smooth',block:'start'});}
let controller, detailController, generation = 0, detailGeneration = 0;
async function refreshOpenLead(){if(selectedView.value!=='followup'||!detail.value||detailLoading.value||savingFollowup.value)return;const id=detail.value.name;try{const result=await ccCall('cc_get_leads',{query:id,detail:1});const latest=result.rows?.find(row=>row.name===id);if(!latest||detail.value?.name!==id)return;if(String(latest.modified)!==String(detail.value.modified)){actionError.value='This lead changed in another session. Your edits are preserved. Reload the lead before saving to review the latest status.';}}catch{}}
function handleWindowFocus(){refreshOpenLead()}
onMounted(()=>window.addEventListener('focus',handleWindowFocus));
onUnmounted(()=>window.removeEventListener('focus',handleWindowFocus));
const columns = [
  { key: 'name', label: 'Lead ID' }, { key: 'lead_name', label: 'Client' },
  { key: 'mobile_no', label: 'Phone', value: r => maskPhone(r.mobile_no) },
  { key: 'branch', label: 'Branch', value: r => r.branch || r.lead_assign_to_branch },
  { key: 'lead_owner', label: 'Agent' }, { key: 'custom_cc_sub_status', label: 'Status', value: r => r.custom_cc_sub_status || r.status },
  { key: 'custom_appointment_status', label: 'Appointment Status' },
  { key: 'custom_appointment_date_and_time', label: 'Appointment' }, { key: 'custom_next_followup_date', label: 'Next follow-up' },
];
const queuePageRows=computed(()=>searching.value?visibleLeads.value:visibleLeads.value.slice((page.value-1)*10,page.value*10));
const pages = computed(() => searching.value ? page.value + (more.value ? 1 : 0) : Math.max(1, Math.ceil(visibleLeads.value.length / 10)));
const visibleLeads=computed(()=>rows.value.filter(row=>matchesJourney(journeys.value[row.name],queueFlag.value)&&matrixMatches(row)&&(!queueStatus.value||(row.custom_cc_stage||row.status)===queueStatus.value)&&(!queueOwner.value||row.lead_owner===queueOwner.value)&&(!queueSubStatus.value||(queueSubStatus.value==='No Response / Not Reachable'?['No Response','Not Reachable'].includes(row.custom_cc_sub_status):row.custom_cc_sub_status===queueSubStatus.value))&&(!queueCategory.value||String(row.custom_treatment_interests||'').toLowerCase().includes(queueCategory.value.toLowerCase()))&&(!queueSearch.value.trim()||[row.name,row.lead_name,row.mobile_no,row.branch,row.lead_owner].some(v=>String(v||'').toLowerCase().includes(queueSearch.value.trim().toLowerCase())))));
// Capture applied filters so changing a draft cannot mix pagination cohorts.
watch([queueOwner,queueStatus,queueSubStatus,queueCategory,queueSearch],()=>{if(!searching.value)page.value=1;});
watch(salesClientSearch,()=>salesClientPage.value=1);
// Reuse a complete cohort for tab navigation for up to one refresh interval.
// Apply, explicit refresh, and successful writes still call load directly.
let filters = {from_date:from.value,to_date:to.value,date_mode:mode.value};
let loadedLeadKey='', activeLeadKey='', leadLoadedAt=0;
function leadDataKey(){return JSON.stringify([filters,searching.value?page.value:0,selectedView.value==='assign'?'assign':'shared']);}
function apply() {
  error.value = '';
  if (query.value.trim() && query.value.trim().length < 2) { error.value = 'Enter at least two characters to search.'; return; }
  if (!query.value.trim() && (!from.value || !to.value || from.value > to.value)) { error.value = 'Choose a valid date range.'; return; }
  filters = query.value.trim() ? { query: query.value.trim() } : { from_date: from.value, to_date: to.value, date_mode: mode.value };
  searching.value = !!filters.query;
  applied.value = filters.query ? 'Search across permitted history: ' + filters.query : `${from.value} → ${to.value} · ${mode.value}`;
  matrixFilter.value=null;
  if(selectedView.value==='duplicates'){
    generation++;controller?.abort();rows.value=[];loading.value=false;loadDuplicateLeads();return;
  }
  if(['dashboard','queue','followup','tl','reports','assign'].includes(selectedView.value)&&(selectedView.value!=='followup'||searching.value))load(1);
  if(selectedView.value==='reports'&&!salesBusy.value)loadSales();
}
async function load(nextPage,{preserveRows=false,preserveSelection=false}={}) {
  const token = ++generation; controller?.abort(); controller = new AbortController();
  page.value = nextPage; loading.value = true; error.value = '';
  const requestKey=leadDataKey(), assignmentLoad=selectedView.value==='assign';
  activeLeadKey=requestKey;loadedLeadKey='';
  if(!preserveRows){rows.value=[];total.value=0;more.value=false;createdIds.value=new Set();appointmentCohort.value=[];incomplete.value=false;tlPage.value=1;}
  if(!preserveSelection)assignSelected.value=new Set();
  try {
    let data;
    if(searching.value){
      if(filters.convoxMobile){
        const result=await convoxApi.findLeads(filters.convoxMobile,controller.signal);
        data={rows:result.rows||[],more:false};
        if(token===generation&&result.truncated)error.value='More than 100 leads match this number. Narrow the search in CRM.';
      }else data=await ccCall('cc_get_leads',{...filters,start:(nextPage-1)*20},controller.signal);
      if(token!==generation)return;
    }
    if(!searching.value){
      // Load bounded pages concurrently; avoid a redundant 5k-row request.
      const loadCohort = async date_mode => {
        const pageSize=500, cohortRows=[];
        let start=0, cohort;
        do {
          cohort=await ccCall('cc_get_leads',{...filters,date_mode,page_size:pageSize,start},controller.signal);
          cohortRows.push(...(cohort.rows||[]));
          start+=pageSize;
        } while(cohort.has_more && token===generation);
        return {...cohort,rows:cohortRows};
      };
      const cohortModes=assignmentLoad?[filters.date_mode]:
        [filters.date_mode,...['followup','appointment',...(filters.date_mode==='created'?['posting']:[])].filter(value=>value!==filters.date_mode)];
      const cohorts=await Promise.all(cohortModes.map(loadCohort));
      if(token!==generation)return;
      let createdCohort=cohorts[cohortModes.indexOf(filters.date_mode)]||null;
      if(filters.date_mode==='created' && !assignmentLoad && createdCohort){
        const repeatRows=cohorts[cohortModes.indexOf('posting')]?.rows||[];
        const enquiryRows=mergeEnquiryRows(createdCohort.rows,repeatRows,filters.from_date,filters.to_date);
        createdCohort={...createdCohort,rows:enquiryRows,total:enquiryRows.length};
        cohorts[cohortModes.indexOf(filters.date_mode)]=createdCohort;
        // Posting results outside this cohort must not leak into the queue.
        const postingIndex=cohortModes.indexOf('posting');
        if(postingIndex>=0)cohorts[postingIndex]={...cohorts[postingIndex],rows:[]};
      }
      createdIds.value=new Set((createdCohort?.rows||[]).map(row=>row.name));
      appointmentCohort.value=cohorts[cohortModes.indexOf('appointment')]?.rows||[];
      data={...(createdCohort||cohorts[0]),rows:[...new Map(cohorts.flatMap(cohort=>cohort.rows||[]).map(row=>[row.name,row])).values()]};
      incomplete.value=cohorts.some(cohort=>cohort.truncated);
      if(incomplete.value) error.value='The selected range exceeds the lead limit. Choose a shorter range to view all leads.';
    }
    if (token !== generation) return;
    if(searching.value){createdIds.value=new Set((data.rows||[]).map(row=>row.name));appointmentCohort.value=(data.rows||[]).filter(row=>row.custom_appointment_date_and_time)}
    rows.value = data.rows || []; total.value = searching.value?createdIds.value.size:(data.total??createdIds.value.size); more.value = !!data.more; scoped.value = !!data.scoped_to_owner; contactManager.value=!!data.contact_manager;
    loadedLeadKey=requestKey;leadLoadedAt=Date.now();
  } catch (e) { if (token === generation && e.name !== 'AbortError') error.value = e.message; }
  finally { if (token === generation) loading.value = false; }
}
function refreshCurrentView(){
  if(document.hidden||detail.value||savingFollowup.value||loading.value||(selectedView.value==='followup'&&!searching.value))return;
  if(selectedView.value==='duplicates'){if(canManageLeads.value&&!duplicateLoading.value)loadDuplicateLeads(true);return;}
  if(!['dashboard','queue','followup','tl','reports','assign'].includes(selectedView.value))return;
  load(page.value,{preserveRows:true,preserveSelection:true});
  if(selectedView.value==='reports'&&!salesBusy.value)loadSales(true);
}

async function openDetail(row) {
  loadLeadSources().catch(()=>{});
  if(canEditLeadOwner.value)loadTlConfig();
  window.dispatchEvent(new CustomEvent('life-convox-native',{detail:{type:'life-convox-select',lead_id:row.name}}));
  stopCall();
  detailController?.abort(); detailController = new AbortController(); const token = ++detailGeneration;
  detail.value = row; detailError.value = ''; detailLoading.value = true; actionError.value=''; actionNotice.value=matchNotice.value; matchNotice.value=''; followup.value={stage:'',sub_status:'',status:'',next_followup:'',conclusion:'',remarks:''}; actionType.value=''; activeStep.value=0; selectedView.value='followup';
  if(ccViewOfRoute(route)!=='followup'||route.params.leadId!==row.name)await router.push(ccRoute('followup',{...pageQuery(),lead:row.name}));
  try {
    const data = await ccCall('cc_get_leads', { query: row.name, detail: 1 }, detailController.signal);
    if (token !== detailGeneration) return;
    const found = data.rows?.find(item => item.name === row.name);
    if (!found) throw new Error('This lead is no longer available to your account.');
    contactManager.value=!!data.contact_manager; detail.value = found; initLeadDraft(found);
  } catch (e) { if (token === detailGeneration && e.name !== 'AbortError') detailError.value = e.message; }
  finally { if (token === detailGeneration) detailLoading.value = false; }
}
function closeDetail() { stopCall(); detailGeneration++; detailController?.abort(); detail.value=null; showView('queue'); }
function initLeadDraft(row) {
  const dateTime = String(row.custom_next_followup_date||'').replace(' ','T').slice(0,16);
  const interests=String(row.custom_treatment_interests||'').split(';').map(x=>x.trim()).filter(Boolean);
  selectedCategories.value=treatmentCategories.filter(x=>interests.includes(x));
  selectedInterests.value=String(row.custom_specific_interests||'').split(';').map(x=>x.trim()).filter(Boolean);
  leadDraft.value={lead_owner:row.lead_owner||'',consultant:row.consultant||'',first_name:row.first_name||row.lead_name||'',email_id:row.email_id||'',age:row.age||'',gender:row.gender||'',city:row.city||'',source:row.source||'',custom_media:row.custom_media||'',custom_posting_date:row.custom_posting_date||'',branch:row.branch||'',lead_assign_to_branch:row.lead_assign_to_branch||'',enquired_for:row.enquired_for||'',phone:row.phone||'',custom_marital_status:row.custom_marital_status||'',custom_no_of_kids:row.custom_no_of_kids||'',custom_delivery_type:row.custom_delivery_type||'',custom_breastfeeding:row.custom_breastfeeding||'',weight:row.weight||'',height:row.height||'',custom_bmi:row.custom_bmi||'',custom_target_weight:row.custom_target_weight||'',medical_history:row.medical_history||'',custom_current_medication:row.custom_current_medication||'',custom_previous_attempts:row.custom_previous_attempts||'',custom_hospitalized:row.custom_hospitalized||'',custom_cc_stage:row.custom_cc_stage||row.status||'UNTOUCHED',custom_cc_sub_status:row.custom_cc_sub_status||'',custom_next_followup_date:dateTime,custom_conclusion_remark:row.custom_conclusion_remark||'',custom_remarks:row.custom_remarks||'',custom_chat_script:row.custom_chat_script||''};
  followup.value={stage:row.custom_cc_stage||row.status||'UNTOUCHED',sub_status:row.custom_cc_sub_status||'',status:row.status||'',next_followup:dateTime,conclusion:row.custom_conclusion_remark||'',remarks:String(row.custom_remarks||'').replace(/\[CC_PROFILE_V1\][\s\S]*?\[\/CC_PROFILE_V1\]/g,'').trim()};
}
function toggleCategory(category){selectedCategories.value=selectedCategories.value.includes(category)?selectedCategories.value.filter(x=>x!==category):[...selectedCategories.value,category];}
function toggleInterest(interest){selectedInterests.value=selectedInterests.value.includes(interest)?selectedInterests.value.filter(x=>x!==interest):[...selectedInterests.value,interest];}
function stageFromOutcome(outcome){if(['Appointment Booked','Existing Client','Walked In & Booked'].includes(outcome))return 'SUCCESS';if(['Not Interested','Other clinic','Joined Competition','Do Not Contact'].includes(outcome))return 'LOST';if(['Invalid Number','Wrong number','Not in Service','Job enquiry','Franchise Lead','Junk/Wrong Call','Not Enquired','TNA','NID'].includes(outcome))return 'INVALID';if(['Very Positive','Call & Confirm','Callback: Scheduled','Price Negotiation','Out Station','Walked In: Not Booked','Get Back','No Response','Not Reachable','Switch OFF','Call Disconnected','Appointment no response'].includes(outcome))return 'FOLLOW-UP';return followup.value.stage||'FOLLOW-UP';}
const createOwners=computed(()=>activeCcAgents(tlConfig.value?.agents||[]).map(agent=>({id:agent.agent,name:agent.employee_name||agent.agent})).sort((a,b)=>a.name.localeCompare(b.name)));
const assignRecipients=createOwners;
let sourcesLoaded=false, sourcesPromise;
async function loadLeadSources(){
  if(sourcesLoaded)return createSources.value;
  if(sourcesPromise)return sourcesPromise;
  sourcesPromise=request('frappe.client.get_list',{args:{doctype:'Lead Source',fields:['name'],order_by:'name asc',limit_page_length:1000},csrfToken:session.csrf_token}).then(result=>{createSources.value=(result.message||[]).map(row=>row.name);sourcesLoaded=true;return createSources.value;}).finally(()=>sourcesPromise=null);
  return sourcesPromise;
}
let createMastersLoaded=false;
async function loadCreateMasters(){
  if(createMastersLoading.value||createMastersLoaded)return;
  createMastersLoading.value=true;
  try{
    const [branchRows,sourceRows,categoryRows]=await Promise.all([
      request('frappe.client.get_list',{args:{doctype:'Branch',fields:['name'],filters:[['name','!=','Testing Branch']],order_by:'name asc',limit_page_length:500},csrfToken:session.csrf_token}),
      loadLeadSources(),
      request('frappe.client.get_list',{args:{doctype:'Healthcare Service Unit',fields:['name'],filters:[['name','!=','All Healthcare Service Units - LSACPL']],order_by:'name asc',limit_page_length:500},csrfToken:session.csrf_token}),
      canEditLeadOwner.value?loadTlConfig():Promise.resolve(),
    ]);
    createBranches.value=(branchRows.message||[]).map(row=>row.name);
    createSources.value=sourceRows;
    createCategories.value=(categoryRows.message||[]).map(row=>row.name);
    createMastersLoaded=true;
  }catch(error){createError.value=error.message||'Could not load lead form options.';}finally{createMastersLoading.value=false;}
}
async function openCreate() { createError.value='';createDuplicate.value=null;showView('create');await loadCreateMasters(); }
async function createLead() {
  createBusy.value=true; createError.value='';
  try {
    const mobile=String(createForm.value.mobile_no||'').replace(/\D/g,'');
    if(!createForm.value.first_name.trim())throw new Error('Name is required.');
    if(!/^[6-9]\d{9}$/.test(mobile))throw new Error('Enter a valid 10-digit mobile number.');
    if(!createForm.value.source)throw new Error('Source is required.');
    if(!createForm.value.branch)throw new Error('Branch is required.');
    const values={...createForm.value,mobile_no:mobile,status:'Lead',custom_cc_stage:'UNTOUCHED',custom_media:'CC Team',custom_posting_date:today};
    if(canEditLeadOwner.value&&values.lead_owner&&!assignRecipients.value.some(agent=>agent.id===values.lead_owner))throw new Error('Choose an active call-centre agent.');
    if(!canEditLeadOwner.value)values.lead_owner=session.user;
    else if(!values.lead_owner)delete values.lead_owner;
    const result=await ccCall('cc_create_lead',{values:JSON.stringify(values)});
    const matched=result.duplicate;
    if(matched){createDuplicate.value=matched;return;}
    const id=result.created;
    if(!id) throw new Error('The lead was not created. Please retry.');
    createForm.value={first_name:'',mobile_no:'',phone:'',email_id:'',age:'',gender:'',city:'',source:'',branch:'',category:'',lead_owner:'',enquired_for:'',custom_remarks:''};
    filters={query:id};searching.value=true;applied.value=matched?`Matched existing client · ${id}`:`Created lead · ${id}`;query.value=id;
    await load(1);
    matchNotice.value='';
    await openDetail({name:id,lead_name:values.first_name});
  } catch(e) { createError.value=e.message; }
  finally { createBusy.value=false; }
}
async function openDuplicateLead(row){const phone=String(row.phone||'').replace(/\D/g,'').slice(-10);if(!phone)return;try{const result=await ccCall('cc_get_leads',{phone});const lead=(result.rows||[])[0];if(!lead){error.value=`No original lead found for ${maskPhone(phone)}.`;return}await openDetail(lead)}catch(e){error.value=e.message||'Could not find the original lead.'}}
const duplicateRows=ref([]),duplicateLoading=ref(false),duplicateError=ref(''),duplicateSearch=ref(''),duplicatePage=ref(1);
watch([tlSearch,tlOwner,tlStatus],()=>tlPage.value=1);
watch(duplicateSearch,()=>duplicatePage.value=1);
const duplicateFiltered=computed(()=>{const query=duplicateSearch.value.trim().toLowerCase();return duplicateRows.value.filter(row=>!query||[row.name1,row.phone,row.enquired_for].some(value=>String(value||'').toLowerCase().includes(query)))});
async function loadDuplicateLeads(preservePage=false){if(!canManageLeads.value)return;duplicateLoading.value=true;duplicateError.value='';try{const result=await request('frappe.client.get_list',{args:{doctype:'Duplicate Lead',fields:['name','name1','phone','enquired_for','creation'],filters:[['creation','>=',from.value+' 00:00:00'],['creation','<=',to.value+' 23:59:59']],order_by:'creation desc',limit_page_length:500},csrfToken:session.csrf_token});duplicateRows.value=result.message||[];if(!preservePage)duplicatePage.value=1}catch(e){duplicateError.value=e.message||'Could not load duplicate submissions (check Duplicate Lead permissions).'}finally{duplicateLoading.value=false}}
const assignSearch=ref(''),assignOwnerFilter=ref(''),assignStatusFilter=ref(''),assignEnquiryFilter=ref(''),assignSelected=ref(new Set()),assignTo=ref(''),assignBusy=ref(false),assignError=ref(''),autoTransferStatus=ref('');
const assignRows=computed(()=>rows.value);
let assignSearchTimer;
watch(assignSearch,()=>{clearTimeout(assignSearchTimer);assignSearchTimer=setTimeout(()=>{if(selectedView.value==='assign'){query.value=assignSearch.value;apply();}},350)});
onBeforeUnmount(()=>clearTimeout(assignSearchTimer));
const assignOwners=computed(()=>{const map=new Map();[...createOwners.value,...rows.value.filter(row=>row.lead_owner).map(row=>({id:row.lead_owner,name:row.lead_owner_name||row.lead_owner}))].forEach(row=>{if(row.id&&!map.has(row.id))map.set(row.id,row)});return [...map.values()].sort((a,b)=>a.name.localeCompare(b.name))});
const assignAutoRows=computed(()=>autoTransferStatus.value?rows.value.filter(row=>(row.custom_cc_stage||row.status)===autoTransferStatus.value):[]);
function toggleAssignLead(id,checked){const values=new Set(assignSelected.value);checked?values.add(id):values.delete(id);assignSelected.value=values}
function selectAllAssign(checked){assignSelected.value=checked?new Set(assignRows.value.map(row=>row.name)):new Set()}
async function recoverJunk(row){try{await request('life_slimming.api.cc_access.recover_junk',{args:{lead:row.name},csrfToken:session.csrf_token});dialog.value?.close();await openDetail(row);}catch(e){error.value=e.message;}}
async function updateLeadOwner(lead,owner){if(!assignRecipients.value.some(agent=>agent.id===owner))throw new Error('Choose an active call-centre agent.');return ccCall('cc_update_lead',{lead,values:JSON.stringify({lead_owner:owner})})}
async function applyManualAssignment(){if(!assignSelected.value.size){assignError.value='Select at least one lead.';return}if(!assignRecipients.value.some(agent=>agent.id===assignTo.value)){assignError.value='Choose an active call-centre agent.';return}assignBusy.value=true;assignError.value='';const ids=[...assignSelected.value];let success=0,failed=0;for(let index=0;index<ids.length;index+=10){const result=await Promise.allSettled(ids.slice(index,index+10).map(id=>updateLeadOwner(id,assignTo.value)));result.forEach(item=>item.status==='fulfilled'?success++:failed++)}assignBusy.value=false;assignSelected.value=new Set();assignError.value=`Reassigned ${success} lead(s)${failed?`; ${failed} failed`:''}.`;await load(page.value)}
async function runAutoTransfer(){const selected=assignAutoRows.value.slice().sort((a,b)=>a.name.localeCompare(b.name)),owners=assignRecipients.value;if(!selected.length){assignError.value='No leads match that status.';return}if(!owners.length){assignError.value='No lead owners are available in this date range.';return}assignBusy.value=true;assignError.value='';let success=0,failed=0;for(let index=0;index<selected.length;index+=10){const slice=selected.slice(index,index+10);const results=await Promise.allSettled(slice.map((row,offset)=>updateLeadOwner(row.name,owners[(index+offset)%owners.length].id)));results.forEach(item=>item.status==='fulfilled'?success++:failed++)}assignBusy.value=false;assignError.value=`Auto-transferred ${success} lead(s) across ${owners.length} owner(s)${failed?`; ${failed} failed`:''}.`;await load(page.value)}
async function saveFollowup(payload) {
  if(!detail.value) return;
  actionType.value=payload.nextAction;
  const outcome=followup.value.sub_status||leadDraft.value.custom_cc_sub_status;
  const stage=followup.value.stage||stageFromOutcome(outcome);
  savingFollowup.value=true; actionError.value=''; actionNotice.value='';
  try {
    const values={...leadDraft.value,custom_cc_stage:stage,custom_cc_sub_status:outcome,custom_treatment_interests:selectedCategories.value.join('; '),custom_specific_interests:selectedInterests.value.join('; '),custom_next_followup_date:followup.value.next_followup,custom_conclusion_remark:followup.value.conclusion,custom_remarks:followup.value.remarks+"\n[CC_PROFILE_V1]"+JSON.stringify(payload.profile)+"[/CC_PROFILE_V1]"};
    if(payload.result==='Not Connected'&&['No Response','Not Response','Not Reachable','Switch OFF','TNA','Call Disconnected','Appointment no response','Busy','Not Lifted'].includes(payload.reason||outcome)) {
      const result=await ccCore('attempt',{lead:detail.value.name,reason:payload.reason||outcome,expected_modified:detail.value.modified,remarks:values.custom_remarks});
      actionNotice.value=`Call attempt saved · ${result.streak} in a row · retry ${result.next_followup}${result.tl_review?' · TL review required':''}`;
      stopCall();detailGeneration++;detailController?.abort();detail.value=null;selectedView.value='dashboard';await load(1);return;
    }
    if(actionType.value==='pipeline') { values.custom_pipeline_date_and_time=followup.value.next_followup; values.custom_cc_stage='PIPELINE'; }
    const saveArgs={lead:detail.value.name,values:JSON.stringify(values),expected_modified:detail.value.modified,attempt:JSON.stringify({result:payload.result,reason:payload.reason,expected_modified:detail.value.modified})};
    const nextActions={'Appointment Booked':'Confirm appointment','Price Negotiation':'Discount / price follow-up','Callback: Scheduled':'Call back','Call & Confirm':'Confirm appointment','Walked In: Not Booked':'Convert follow-up','Very Positive':'Book appointment','Out Station':'Call back later','Get Back':'Call back later','Existing Client':'Client care / renewal','Walked In & Booked':'Client care / renewal'};
    const update=payload.result==='Connected'?await ccCore('save_connected',{...saveArgs,next_action:nextActions[outcome]||'',next_action_due:values.custom_next_followup_date}):await ccCall('cc_update_lead',saveArgs);
    // Older Server Scripts return {message:{...}} while newer versions return the payload directly.
    const updateResult=update?.message&&typeof update.message==='object'?update.message:update;
    if(!updateResult||(updateResult.ok!==1&&updateResult.ok!==true)){if(updateResult?.conflict){const conflictMessage=updateResult.error||'This lead changed elsewhere. Reload and review the latest status.';await openDetail({name:detail.value.name});actionError.value=conflictMessage;throw new Error('')}throw new Error(updateResult?.error||'Lead update was not saved'+(updateResult?.skipped?.length?': '+updateResult.skipped.join(', '):''));}
    const portalStatuses={'UNTOUCHED':'Lead','FOLLOW-UP':'Followup','SUCCESS':'Interested','LOST':'Not interested','INVALID':'Not Response','PIPELINE':'Followup'};
    if(actionType.value!=='book'){
      const followupResult=await ccCall('cc_add_lead_followup',{lead:detail.value.name,cc_stage:values.custom_cc_stage,cc_sub_status:values.custom_cc_sub_status,status:outcome==='Appointment no response'?outcome:portalStatuses[values.custom_cc_stage]||'Followup',next_followup:values.custom_next_followup_date,conclusion:values.custom_conclusion_remark,remarks:followup.value.remarks});
      const followupPayload=followupResult?.message&&typeof followupResult.message==='object'?followupResult.message:followupResult;
      if(followupPayload?.ok===0||followupPayload?.success===false)throw new Error(followupPayload.error||'Call outcome was not recorded.');
    }
    actionNotice.value=actionType.value==='book'?'Lead saved. Choose the appointment slot next.':'Lead update and call outcome saved.';
    const id=detail.value.name;
    if(actionType.value==='book') {
      await router.push({name:'cc-appointments',query:{lead:id,branch:leadDraft.value.branch||''}});
    } else {
      stopCall();detailGeneration++;detailController?.abort();detail.value=null;selectedView.value='dashboard';
      load(1);
    }
  } catch(e) { if(e.message)actionError.value=e.message; }
  finally { savingFollowup.value=false; }
}
function quickRange(period){
 let range;
 if(period==='tomorrow'||period==='yesterday'){
   const date=new Date(today+'T12:00:00Z');date.setUTCDate(date.getUTCDate()+(period==='tomorrow'?1:-1));range=[date.toISOString().slice(0,10),date.toISOString().slice(0,10)];
 }else if(period==='month')range=dateRange('month',today);
 else if(period==='lastmonth'){
   const [start]=dateRange('month',today),date=new Date(start+'T12:00:00Z');date.setUTCDate(date.getUTCDate()-1);range=dateRange('month',date.toISOString().slice(0,10));
 }else if(period==='nextmonth')range=dateRange('nextmonth',today);
 else range=[today,today];
 [from.value,to.value]=range;query.value='';apply();
}
function clearRange(){
  // The legacy Clear action removes date filtering; this API requires a bounded
  // range, so reset to the dashboard's default day and clear all draft filters.
  query.value='';queueSearch.value='';queueOwner.value='';queueStatus.value='';queueSubStatus.value='';queueCategory.value='';
  [from.value,to.value]=dateRange('today');apply();
}
async function findConvoxLead(event){
  if(typeof event.detail?.mobile_number!=='string')return;
  let mobile=event.detail.mobile_number.replace(/[\s()+.-]/g,'');
  if(mobile.length===12&&mobile.startsWith('91'))mobile=mobile.slice(2);
  else if(mobile.length===11&&mobile.startsWith('0'))mobile=mobile.slice(1);
  if(!/^\d{10}$/.test(mobile))return;
  detailGeneration++;detailController?.abort();detailLoading.value=false;detailError.value='';
  matrixFilter.value=null;queueSearch.value='';queueOwner.value='';queueStatus.value='';queueSubStatus.value='';queueCategory.value='';
  showView('queue');query.value=mobile;globalSearch.value=mobile;filters={convoxMobile:mobile};searching.value=true;applied.value='ConVox caller: '+maskPhone(mobile);
  controller?.abort(); controller=new AbortController(); const token=++generation;
  loading.value=true;error.value='';
  try {
    const result=await convoxApi.findLeads(mobile,controller.signal);
    if(token!==generation)return;
    rows.value=result.rows||[];total.value=rows.value.length;page.value=1;more.value=false;
    createdIds.value=new Set(rows.value.map(row=>row.name));
    if(result.truncated)error.value='More than 100 leads match this number. Narrow the search in CRM.';
    if(rows.value.length===1)await openDetail(rows.value[0]);
  } catch(e){if(token===generation&&e.name!=='AbortError')error.value=e.message;}
  finally{if(token===generation)loading.value=false;}
}
onMounted(()=>{if(initialView==='create')openCreate();initializeView(selectedView.value);if(['assign','duplicates'].includes(selectedView.value)&&!canManageLeads.value)showView('dashboard');if(route.params.leadId||route.query.lead)openDetail({name:routeValue(route.params.leadId||route.query.lead)});else if(route.query.caller)findConvoxLead({detail:{mobile_number:routeValue(route.query.caller)}});else apply();window.addEventListener('life-convox-find-native',findConvoxLead);autoRefreshTimer=setInterval(refreshCurrentView,60000)});
onUnmounted(() => { clearTimeout(globalSearchTimer);globalSearchController?.abort();globalSearchGeneration++;generation++;historyGeneration++;salesRequest++; detailGeneration++; controller?.abort(); detailController?.abort(); clearInterval(callInterval);clearInterval(autoRefreshTimer);window.removeEventListener('life-convox-find-native',findConvoxLead); });
// One page-owned state keeps tab navigation from recreating requests or losing drafts.
provide(ccDashboardKey, reactive({
  maskPhone, today, from, to, mode, rows, total,
  scoped, journeys, journeyError, loading, error, followup, groupPanel,
  repeatWebsiteRows, myLeads, openTile, stageCounts, agentRows, appointmentRows, recoveryFlags,
  openRecovery, dashQueueRows, reminderRows, reminderBuckets, dashboardGroups, convertedRows, sameDayAppointments,
  olderLeadAppointments, sameDayConverted, olderConverted, showView, openDetail, load,
  journeyFlags, page, searching, queueOwner, queueFlag, matrixFilter, queueStatus,
  queueCategory, queueSubStatus, queueSearch, applied, viewLead, callOutcomes, treatmentCategories,
  queuePageRows, pages, visibleLeads, filters, assignOwners, assignRecipients, query,
  sourceCounts, columns, enquiryDate, enquiryLabel, stages, apply,
  assignSearch, assignSelected, assignTo, assignBusy, assignError, autoTransferStatus, assignRows,
  assignAutoRows, toggleAssignLead, selectAllAssign, applyManualAssignment, runAutoTransfer, duplicatePages, duplicateVisible,
  openDuplicateLead, duplicateLoading, duplicateError, duplicateSearch, duplicatePage, duplicateFiltered, loadDuplicateLeads,
  tlCollapsed, tlConfig, tlConfigBusy, tlConfigError, tlPreviewSource, tlPreview, tlPreviewBusy,
  tlPreviewError, tlSearch, tlOwner, tlStatus, tlPage, tlFiltered, tlPages,
  tlVisible, loadTlConfig, previewTlAssignment, printReport, incomplete, salesData, salesBusy,
  salesError, salesSearch, canViewSourceReports, categoryCounts, subStatusCounts, pipelineRows, matrixStatuses,
  matrixRows, openMatrixCell, exportMatrixCsv, visibleSalesRows, salesOwnerName, salesFilteredRows, salesAgentRows,
  visibleSalesSummary, salesClientSearch, salesClientPage, salesClientPages, salesClientVisible, money, appointmentAgentRows,
  loadSales, knowledgeTab, copyNotice, scripts, objections, faqs, copyText,
  faqSearch, filteredFaqs, treatments, doctorLoading, doctorError, branches, loadDoctors,
  branchManager, doctorRows, doctorBranches, contactManager, detail, detailLoading, detailError,
  savingFollowup, actionError, actionNotice, leadDraft, selectedCategories, selectedInterests, callClock, callRunning, startCall,
  openPhone, closeDetail, recoverJunk, saveFollowup,
  createForm, createBusy, createError, createDuplicate, createMastersLoading, createSources, createBranches, createCategories, createOwners, canEditLeadOwner, createLead,
}));
</script>
<template>
<section class="cc-erp-root cc-dashboard-vue" :class="{'cc-native':selectedView!=='followup','cc-native-shell':selectedView!=='followup'}">
  <CCMobileCallPopup @open="id => openDetail({name:id})" />
  <header class="hdr portal-module-toolbar"><div class="hdr-brand"><div class="logo">L</div><div><div class="bn">🎧 LIFE CALL CENTRE</div><div class="bs">CC Command ERP</div></div></div><div class="hdr-center"><div class="search-wrap"><span class="si">🔍</span><input id="global-search" v-model="globalSearch" type="search" placeholder="Search client name, mobile or lead ID…" aria-label="Search all leads" autocomplete="off" @keydown.esc="globalSearch=''" @keydown.enter.prevent="globalMatches.length===1&&chooseGlobal(globalMatches[0])"><div v-if="globalSearch.trim().length>=2" class="search-results show" role="region" aria-label="Lead search results"><div v-if="globalSearchBusy" class="sr-item" role="status">Searching all leads…</div><div v-else-if="globalSearchError" class="sr-item" role="alert">{{globalSearchError}}</div><template v-else><button v-for="item in globalMatches" :key="item.lead.name" class="sr-item search-item" @click="chooseGlobal(item)"><strong>{{item.title}}</strong><span class="sr-cat">{{item.sub}}</span></button><div v-if="!globalMatches.length" class="sr-item">No matching lead found.</div><div v-if="globalSearchMore" class="sr-item">More matches exist. Add part of the name or phone to narrow the results.</div></template></div></div></div><div class="hdr-right"><div class="agent-info"><div class="an">{{session?.full_name||'Agent Name'}}</div><div class="ai">Call Center</div></div><div class="agent-avatar">{{String(session?.full_name||'A').slice(0,1).toUpperCase()}}</div></div></header>
  <div class="body-wrap"><main class="main">
  <form v-if="['dashboard','queue','tl','reports','duplicates'].includes(selectedView)" id="cc-quick-range" class="cc-rangebar" @submit.prevent="query='';apply()"><strong>📅 Enquiry Date Range</strong><button type="button" class="btn btn-sm cc-qr-btn" @click="quickRange('today')">Today</button><button type="button" class="btn btn-sm cc-qr-btn" @click="quickRange('yesterday')">Yesterday</button><button type="button" class="btn btn-sm cc-qr-btn" @click="quickRange('tomorrow')">Tomorrow</button><button type="button" class="btn btn-sm cc-qr-btn" @click="quickRange('month')">This Month</button><button type="button" class="btn btn-sm cc-qr-btn" @click="quickRange('nextmonth')">Next Month</button><button type="button" class="btn btn-sm cc-qr-btn" @click="quickRange('lastmonth')">Last Month</button><label>From <input v-model="from" type="date"></label><label>To <input v-model="to" type="date"></label><label>Filter <select id="cc-date-mode" v-model="mode"><option value="created">Created</option><option value="posting">Posting</option><option value="updated">Updated</option></select></label><button class="btn btn-g btn-sm cc-qr-btn" data-range="apply">Apply</button><button type="button" class="btn btn-gy btn-sm" @click="clearRange">Clear</button></form>
  <div class="page-breadcrumb">Home <span>›</span><span class="cur">{{({create:'Create Lead',testing:'Testing',dashboard:'Dashboard',queue:'My Lead Queue',followup:'Lead Follow-Up Form',tl:'TL Control Panel',reports:'Reports',worksheet:'My Worksheet',assign:'Assign Leads',duplicates:'Duplicate Leads',scripts:'Call Scripts',faq:'FAQ / Knowledge Base',treatments:'Treatment Guide',objections:'Objection Handling',branches:'Branch Directory',doctors:'Doctor Directory',distribution:'Lead Distribution'})[selectedView]||'Dashboard'}}</span><button v-if="['dashboard','queue','followup','tl','reports'].includes(selectedView)" class="btn btn-g btn-sm" @click="openCreate">＋ Create lead</button></div>

  <p v-if="error" class="cc-error" role="alert">{{ error }} <button @click="load(page)">Retry</button></p>
  <div class="page-section active" :id="({dashboard:'page-dashboard',queue:'page-my-leads',followup:'page-followup',tl:'page-tl-panel'})[selectedView]||'page-'+selectedView">
  <RouterView v-slot="{ Component }"><KeepAlive :max="17"><component :is="Component" /></KeepAlive></RouterView>
  </div></main></div>
  <dialog ref="tileDialog" @click="closeTileOnBackdrop($event)" class="modal-box cc-summary-modal" aria-labelledby="cc-tile-title"><h2 id="cc-tile-title" class="modal-title">{{tileTitle}} ({{filteredTileRows.length}})</h2><div class="cc-queue-filters"><label>Agent <select v-model="tileOwner" aria-label="Filter card leads by agent"><option value="">All Agents</option><option v-for="owner in tileOwners" :key="owner.id" :value="owner.id">{{owner.name}}</option></select></label></div><article v-for="row in filteredTileRows" :key="row.name" class="queue-item"><div><div class="qi-name">{{row.lead_name||row.name}}</div><div class="qi-sub">{{maskPhone(row.mobile_no)}} | {{row.city||'—'}} | {{row.custom_cc_chat_returned?'New Lead to the Same Agent':(row.custom_cc_stage||row.status)}}</div><div class="qi-sub">👤 {{row.lead_owner_name||row.lead_owner||'Unassigned'}}</div><div v-if="enquiryLabel(row)" class="qi-sub"><strong>{{enquiryLabel(row)}}</strong> · Enquiry: {{enquiryDate(row)}} · Original ID: {{row.name}}</div><div class="qi-tags"><span class="pill p-green">{{row.custom_appointment_status||'Pending'}}</span><span v-if="row.custom_next_followup_date" class="pill p-gold">📅 {{row.custom_next_followup_date}}</span></div></div><button class="btn btn-n btn-sm" @click="tileDialog.close();openDetail(row)">Open</button></article><p v-if="!filteredTileRows.length" class="cc-empty-state">No leads in this category.</p><div class="btn-row"><button class="btn btn-gy btn-sm" @click="tileDialog.close()">Close</button></div></dialog>
  <dialog ref="dialog" class="modal-box cc-summary-modal"><template v-if="summaryLead"><h2 class="modal-title">Lead Summary — {{summaryLead.lead_name||summaryLead.name}}</h2><div class="form-section">👤 Lead Owner: {{summaryLead.lead_owner||'Unassigned'}} · 🆔 {{summaryLead.name}}</div><div class="form-grid"><div v-for="[label,value] in [['ID',summaryLead.name],['Name',summaryLead.lead_name],['Phone',maskPhone(summaryLead.mobile_no)],['Age / Gender',(summaryLead.age||'—')+' / '+(summaryLead.gender||'—')],['Area',summaryLead.city],['Branch',summaryLead.branch||summaryLead.lead_assign_to_branch],['Source',summaryLead.source],['Assigned To',summaryLead.lead_owner],['Status',summaryLead.custom_cc_stage],['Sub-status',summaryLead.custom_cc_chat_returned?'New Lead to the Same Agent':summaryLead.custom_cc_sub_status],['Categories',summaryLead.custom_treatment_interests],['Calls Made',summaryLead.custom_call_count||0],['Next Follow-up',summaryLead.custom_next_followup_date],['Portal Status',summaryLead.status],['Posting Date',summaryLead.custom_posting_date],['Enquiry Date',enquiryDate(summaryLead)],['Original Created On',summaryLead.creation],['Last Updated',summaryLead.modified],['Conclusion',summaryLead.custom_conclusion_remark],['Remarks',String(summaryLead.custom_remarks||'').replace(/\[CC_PROFILE_V1\][\s\S]*?\[\/CC_PROFILE_V1\]/g,'').trim()]]" :key="label"><strong>{{label}}:</strong> {{value||'—'}}</div></div><div class="btn-row"><button v-if="['Junk/Wrong Call','Not Enquired'].includes(summaryLead.custom_cc_sub_status)" class="btn btn-gy btn-sm" @click="recoverJunk(summaryLead)">Unlock junk lead</button><button class="btn btn-n btn-sm" @click="dialog.close();openDetail(summaryLead)">📞 Open Follow-Up Form</button><button class="btn btn-gy btn-sm" @click="dialog.close();openLeadHistory(summaryLead)">🕘 Lead History</button><button class="btn btn-gy btn-sm" @click="dialog.close();openConvoxHistory(summaryLead.name)">🎧 ConVox history</button><RouterLink class="btn btn-gy btn-sm" :to="{name:'cc-appointments',query:{lead:summaryLead.name}}" @click="dialog.close()">📅 Create Appointment</RouterLink><button class="btn btn-gy btn-sm" @click="dialog.close()">Close</button></div></template></dialog>
  <dialog ref="leadHistoryDialog" class="modal-box cc-summary-modal"><h2 class="modal-title">Lead History — {{leadHistoryLead?.lead_name||leadHistoryLead?.name}}</h2><p v-if="leadHistoryBusy" role="status">Loading history…</p><p v-if="leadHistoryError" class="cc-error" role="alert">{{leadHistoryError}}</p><div v-for="(event,index) in leadHistoryRows" :key="index" class="wf-event"><b>{{event.creation||event.time||"Lead change"}} · {{event.owner||event.by||"User"}}</b><template v-for="(change,changeIndex) in leadHistoryChanges(event)" :key="changeIndex"><span><strong>{{leadHistoryLabels[change[0]]||change[0]}}:</strong> {{change[1]||"—"}} → {{change[2]||"—"}}</span></template></div><p v-if="!leadHistoryBusy&&!leadHistoryError&&!leadHistoryRows.length">No tracked changes are available for this lead.</p><div class="btn-row"><button v-if="leadHistoryLead" class="btn btn-gy btn-sm" @click="leadHistoryDialog?.close();openConvoxHistory(leadHistoryLead.name)">🎧 ConVox history</button><button class="btn btn-gy btn-sm" @click="leadHistoryDialog?.close()">Close</button></div></dialog>

</section>
</template>
