<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { request } from '../api/http';
import { apiCredentials, apiUrl } from '../api/config';
import { session } from '../lib/session';
import { indiaStamp } from '../lib/cc';
import AppointmentSchedulerPage from './AppointmentSchedulerPage.vue';
import '../styles/weight-loss-report.css';

const tabs = [
  { id: 'scheduler', label: 'Scheduler' },
  { id: 'appointments', label: 'Appointment Report' },
  { id: 'sessions', label: 'Therapy Session Report' },
  { id: 'entry', label: 'New Session Entry' },
  { id: 'slimming', label: 'Slimming Execution' },
  { id: 'dermat', label: 'Dermat Execution' },
];
const tab = ref('appointments'), today = indiaStamp().slice(0, 10);
const branch = ref(''), status = ref('all'), query = ref('');
const reportFrom = ref(today), reportTo = ref(today), executionFrom = ref(today), executionTo = ref(today), executionQuery = ref('');
const sessionFrom=ref(today), sessionTo=ref(today), executionPreset=ref('all');
const therapyCategoryMap=ref({});
const rows = ref([]), branches = ref([]), totalRows = ref(0), loading = ref(false), error = ref(''), page = ref(1), pageSize = 10;
const clientSearch = ref(''), clientSuggestions = ref([]), client = ref(null), clientLoading = ref(false);
const planRows = ref([]), plan = ref(null), planLoading = ref(false), sessionSaving = ref(false), sessionNotice = ref('');
const practitioners = ref([]), practitioner = ref(''), doctor = ref(''), physiotherapist = ref(''), dietitian = ref('');
const staffByRole = ref({ doctors: [], physiotherapists: [], dietitians: [] });
const sessionBranch = ref('');
const sessionMeta = ref(null), dynamicFields = ref([]), dynamicValues = ref({}), therapyTypeMeta = ref({});
const requiresConsent = ref(false), consentFile = ref(null), photoFiles = ref({ before: [], after: [] }), consentUploaded=ref(false);
const nextAppointment = ref({ date: '', time: '' });
const existingNextAppointment=ref(null);
const slimmingExecutionNumber=ref(1), cryoFirstToday=ref(false);
const repeatCryoToday = ref(false);
const kpis = ref({ today: 0, month: 0, pending: 0, sessions: 0 });
const selectedAppointment = ref(null), appointmentStatus = ref(''), rescheduleDate = ref(''), rescheduleTime = ref(''), appointmentSaving = ref(false), detailLoading = ref(false);
const sessionForm = ref({ date: today, startTime: '', endTime: '', duration: 30, quantity: 1, bloodPressure: '', bloodSugar: '', pulse: '', beforeWeight: '', afterWeight: '', bmi: '', water: '', neck: '', fat: '', tummy: '', thighs: '', bmr: '', arms: '', hip: '', waist: '', bodyFat: '', muscleMass: '', visceralFat: '', metabolicAge: '', remarks: '' });
const vitalAlerts=computed(()=>{const alerts=[];const bp=String(sessionForm.value.bloodPressure||'').match(/^\s*(\d{2,3})\s*\/\s*(\d{2,3})\s*$/);if(bp&&(Number(bp[1])>140||Number(bp[2])>90))alerts.push('Blood pressure is above the 140/90 alert threshold.');const sugar=Number(sessionForm.value.bloodSugar);if(sessionForm.value.bloodSugar!==''&&(sugar<70||sugar>140))alerts.push('Blood sugar is outside the 70–140 alert range.');const pulse=Number(sessionForm.value.pulse);if(sessionForm.value.pulse!==''&&(pulse<50||pulse>100))alerts.push('Pulse is outside the 50–100 alert range.');return alerts;});
const nextRooms = ref([]), nextRoom = ref('');
const rooms = ref([]), roomOpen = ref(false), roomLoading = ref(false), roomBranch = ref(''), newRoom = ref('');
const isPagedList = computed(() => isSessionList.value || tab.value === 'appointments');
const pageCount = computed(() => Math.max(1, Math.ceil((isPagedList.value ? totalRows.value : searchableRows.value.length) / pageSize)));
const visible = computed(() => isPagedList.value ? searchableRows.value : searchableRows.value.slice((page.value - 1) * pageSize, page.value * pageSize));
const isSessionList = computed(() => ['sessions', 'slimming', 'dermat'].includes(tab.value));
function displayTime(value){if(!value)return '—';const m=String(value).match(/(\d{1,2}):(\d{2})/);if(!m)return String(value);const h=Number(m[1]);return `${h%12||12}:${m[2]} ${h>=12?'PM':'AM'}`;}
function displayDate(value){if(!value)return '—';const [y,m,d]=String(value).slice(0,10).split('-');return y&&m&&d?`${d}/${m}/${y}`:String(value);}
function sessionCell(row,col){const value=col.value?col.value(row):(col.fields||[]).map(k=>row[k]).find(v=>v!==undefined&&v!==null&&v!=='');return value||'—';}
function rowPhoto(row,col){const value=sessionCell(row,col);return typeof value==='string' && (/\.(png|jpe?g|gif|webp|pdf)(?:[?#].*)?$/i.test(value) || value.startsWith('/files/') || value.startsWith('/private/files/'));}
const sessionFieldCandidates = ['name','owner','patient_name','patient','therapy_plan','therapy_type','service_unit','start_date','custom_actual_session_date','patient_age','gender','location','custom_doctor','custom_doctor_name','custom_physiotherapist','custom_physiotherapist_name','custom_dietitian_id','custom_dietitian_name','healthcare_practitioner','custom_healthcare_practitioner','start_time','custom_in_time_','custom_out_time','end_time','duration','practitioner','custom_practitioner_name','custom_doctor_assistant_ht','custom_doctor_assitant_name','custom_results_manager_id','custom_results_manager_name','custom_results_manager','results_manager','results_manager_name','result_manager','result_manager_name','manager','manager_name','custom_total_sessions_count','custom_sessions_complted','custom_bp_mmhg','custom_blood_sugar_mgdl','custom_pulse_bpm','custom_bp','custom_sugar','custom_pulse','before_weight','after_weight','custom_before_weight','custom_after_weight','weight_loss','bmi','custom_machine','custom_body_fat','custom_muscle_mass','custom_visceral_fat','custom_metabolic_age','custom_assured_weight_target','custom_assured_inch_target','custom_health_status','custom_upload_images','custom_after_photo','custom_client_photos_in_session','custom_remarks','remarks','branch','docstatus','creation','modified'];
const sessionFields = computed(() => {
  const names = new Set([...['name','owner','creation','modified','docstatus'], ...(sessionMeta.value?.fields || []).map(field => field.fieldname)]);
  return names.size ? sessionFieldCandidates.filter(field => names.has(field)) : ['name', 'patient_name', 'patient', 'therapy_type', 'start_time', 'practitioner', 'custom_practitioner_name', 'branch', 'docstatus', 'creation'];
});
const appointmentFields = ['name','patient_name','patient','appointment_date','appointment_time','concern','service_room','call_back_status','status','owner','creation','branch'];
const sessionReportColumns = [
  { label:'Client', fields:['patient_name','patient'] }, {label:'Service', fields:['therapy_type']},
  {label:'Session', value:row=>row.__progress || `${row.custom_sessions_complted||0}/${row.custom_total_sessions_count||'—'}`},
  {label:'In', value:row=>`${displayDate(row.start_date||row.custom_actual_session_date)} ${displayTime(row.custom_in_time_||row.start_time)}`},
  {label:'Out', value:row=>displayTime(row.custom_out_time||row.end_time)},
  {label:'BP/Sugar/Pulse', value:row=>[row.custom_bp_mmhg||row.custom_bp,row.custom_blood_sugar_mgdl||row.custom_sugar,row.custom_pulse_bpm||row.custom_pulse].filter(Boolean).join(' / ')||'—'},
  {label:'Wt Before', fields:['custom_before_weight','before_weight']},{label:'Wt After',fields:['custom_after_weight','after_weight']},
  {label:'ΔWt', value:row=>row.weight_loss ?? (Number(row.before_weight||row.custom_before_weight)-Number(row.after_weight||row.custom_after_weight)||'—')},
  {label:'Consent',value:row=>row.__consentUrl},{label:'Before Photo',value:row=>row.__beforePhoto},{label:'After Photo',value:row=>row.__afterPhoto},
  {label:'Therapist',fields:['custom_practitioner_name','practitioner']},{label:'Physiotherapist',fields:['custom_doctor_assitant_name','custom_doctor_assistant_ht']},
  {label:'Doctor',fields:['custom_doctor_name','custom_doctor']},{label:'Dietitian',fields:['custom_dietitian_name','custom_dietitian_id','dilatation']},
  {label:'Results Manager',fields:['__resultsManagerName','custom_results_manager_name','results_manager_name','result_manager_name','manager_name','custom_results_manager_id','custom_results_manager']},
  {label:'Machine',fields:['custom_machine']},{label:'Remarks',fields:['custom_remarks','remarks']},
];
const reportColumns = computed(()=>tab.value==='sessions' ? sessionReportColumns.filter(c=>!['Consent','Before Photo','After Photo'].includes(c.label)) : tab.value==='slimming' ? sessionReportColumns.filter(c=>!['Dietitian'].includes(c.label)) : sessionReportColumns.filter(c=>!['Wt Before','Wt After','ΔWt','Dietitian'].includes(c.label)));
let controller, alive = true; const timers = { search: null };


function dateISO(date){return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;}
function applyExecutionPreset(){
  const now=new Date();const todayDate=new Date(`${today}T12:00:00`);let fromDate=todayDate,toDate=todayDate;
  if(executionPreset.value==='yesterday'){fromDate=new Date(todayDate);fromDate.setDate(fromDate.getDate()-1);toDate=new Date(fromDate);}
  if(executionPreset.value==='thisweek'){fromDate=new Date(todayDate);fromDate.setDate(fromDate.getDate()-((fromDate.getDay()+6)%7));toDate=new Date(fromDate);toDate.setDate(toDate.getDate()+6);}
  if(executionPreset.value==='thismonth'){const start=new Date(todayDate.getFullYear(),todayDate.getMonth(),6,12);if(todayDate.getDate()<6)start.setMonth(start.getMonth()-1);fromDate=start;toDate=new Date(start.getFullYear(),start.getMonth()+1,5,12);}
  if(executionPreset.value==='lastmonth'){let start=new Date(todayDate.getFullYear(),todayDate.getMonth(),6,12);if(todayDate.getDate()<6)start.setMonth(start.getMonth()-1);start=new Date(start.getFullYear(),start.getMonth()-1,6,12);fromDate=start;toDate=new Date(start.getFullYear(),start.getMonth()+1,5,12);} 
  if(executionPreset.value==='all'){executionFrom.value='';executionTo.value='';return;}
  executionFrom.value=dateISO(fromDate);executionTo.value=dateISO(toDate);
}
async function enrichSessions(items,signal){
  const docs=await Promise.all(items.map(async row=>{try{return (await call('frappe.client.get',{doctype:'Therapy Session',name:row.name},signal)).message;}catch(e){if(e.name==='AbortError')throw e;return row;}}));
  const planNames=[...new Set(docs.map(d=>d.therapy_plan).filter(Boolean))];
  const plans=new Map();
  const planDocs=await Promise.all(planNames.map(async name=>{try{return (await call('frappe.client.get',{doctype:'Therapy Plan',name},signal)).message;}catch(e){if(e.name==='AbortError')throw e;return null;}}));
  planDocs.forEach((d,i)=>plans.set(planNames[i],d));
  const planFilters=[];for(let i=0;i<planNames.length;i+=20)planFilters.push(planNames.slice(i,i+20));
  const history=await Promise.all(planFilters.map(async chunk=>{try{return (await call('frappe.client.get_list',{doctype:'Therapy Session',fields:['name','therapy_plan','therapy_type','start_date','start_time','custom_in_time_','creation','docstatus'],filters:[['Therapy Session','therapy_plan','in',chunk],['Therapy Session','docstatus','=',1]],order_by:'start_date asc, start_time asc, creation asc',limit_page_length:2000},signal)).message||[];}catch(e){if(e.name==='AbortError')throw e;return [];}}));
  const ordinals=new Map();const grouped=new Map();history.flat().forEach(d=>{const key=`${d.therapy_plan||''}|${d.therapy_type||''}`;if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(d);});grouped.forEach(list=>{list.sort((a,b)=>`${a.start_date||''}|${a.custom_in_time_||a.start_time||''}|${a.creation||''}|${a.name||''}`.localeCompare(`${b.start_date||''}|${b.custom_in_time_||b.start_time||''}|${b.creation||''}|${b.name||''}`));list.forEach((d,i)=>ordinals.set(d.name,i+1));});
  for(let i=0;i<items.length;i++){
    const row=items[i],doc=docs[i]||row;Object.assign(row,doc);
    const planDoc=plans.get(doc.therapy_plan);const details=planDoc?.therapy_plan_details||planDoc?.therapy_plan_detail||planDoc?.therapy_plan_table||[];const line=details.find(d=>(d.therapy_type||d.therapy)===doc.therapy_type);const total=Number(line?.no_of_sessions||line?.total_sessions||doc.custom_total_sessions_count||0),ordinal=ordinals.get(doc.name)||Number(doc.custom_sessions_complted||0);row.__progress=total?`${Math.min(ordinal,total)}/${total}`:'—';
    const lookup=(...fields)=>fields.map(key=>doc[key]).find(Boolean);
    row.__consentUrl=lookup('custom_client_consent_form','custom_client_consent_image','custom_consent_form','custom_consent_image','client_consent_form','client_consent_image','consent_form')||'';
    row.__beforePhoto=extractFileUrl(doc.custom_upload_images)||'';row.__afterPhoto=extractFileUrl(doc.custom_after_photo,doc.custom_client_photos_in_session)||'';
    row.__resultsManagerName=lookup('custom_results_manager_name','results_manager_name','result_manager_name','manager_name')||'';
    if(!row.__resultsManagerName){const manager=lookup('custom_results_manager_id','custom_results_manager','results_manager','result_manager','manager');if(manager){try{const emp=(await call('frappe.client.get',{doctype:'Employee',name:manager},signal)).message;row.__resultsManagerName=emp.employee_name||emp.name;}catch{row.__resultsManagerName=manager;}}}
    if(!row.__consentUrl||!row.__beforePhoto||!row.__afterPhoto){try{const files=(await call('frappe.client.get_list',{doctype:'File',fields:['file_name','file_url'],filters:[['File','attached_to_doctype','=','Therapy Session'],['File','attached_to_name','=',row.name]],limit_page_length:200},signal)).message||[];for(const f of files){const n=String(f.file_name||'').toLowerCase();if(!row.__consentUrl&&n.includes('consent'))row.__consentUrl=f.file_url;if(!row.__beforePhoto&&/^before/.test(n))row.__beforePhoto=f.file_url;if(!row.__afterPhoto&&/^after/.test(n))row.__afterPhoto=f.file_url;}}catch(e){if(e.name==='AbortError')throw e;}}
  }
  return items;
}

function extractFileUrl(...values){for(const value of values){if(typeof value==='string'&&(/\/files\//.test(value)||/\.(png|jpe?g|gif|webp)(?:[?#].*)?$/i.test(value)))return value;if(Array.isArray(value)){const found=extractFileUrl(...value);if(found)return found;}if(value&&typeof value==='object'){const found=extractFileUrl(...Object.values(value));if(found)return found;}}return '';}
function reportArgs(doctype, fields, filters, start = 0) {
  const orderField=doctype==='Patient Appointment'?'appointment_date':'creation';
  return { doctype, fields: JSON.stringify(fields.map(field => `\`tab${doctype}\`.\`${field}\``)), filters: JSON.stringify(filters), order_by: `\`tab${doctype}\`.\`${orderField}\` desc`, start, page_length: 500, view: 'List', group_by: '', with_comment_count: 0 };
}
function reportRows(response) {
  const data = response.message || {}, keys = data.keys || [];
  return (data.values || []).map(values => Object.fromEntries(keys.map((key, index) => [key, values[index]])));
}
function filtersFor(doctype) {
  const filters = [];
  const dateField = doctype === 'Patient Appointment' ? 'appointment_date' : 'start_date';
  const range = tab.value==='sessions' ? [sessionFrom.value,sessionTo.value] : isSessionList.value ? [executionFrom.value, executionTo.value] : [reportFrom.value, reportTo.value];
  if (range[0] && range[1]) filters.push([doctype, dateField, 'Between', range]);
  else if(range[0])filters.push([doctype,dateField,'>=',range[0]]);
  else if(range[1])filters.push([doctype,dateField,'<=',range[1]]);
  if (branch.value) filters.push([doctype, 'branch', '=', branch.value]);
  if(doctype==='Patient Appointment'&&status.value!=='all'){
    const appointmentStatuses={Pending:['Open','Pending'],Cancel:['Cancel'],Scheduled:['Scheduled'],'Re-Confirm':['Re-Confirm'],Reconfirm:['Reconfirm'],'Not Answering':['Not Answering'],Confirmed:['Confirmed'],Visited:['Visited'],Executed:['Executed'],Closed:['Closed'],Postponed:['Postponed'],'Re-Scheduled':['Re-Scheduled']};
    if(appointmentStatuses[status.value])filters.push([doctype,'call_back_status','in',appointmentStatuses[status.value]]);
  }
  if (doctype === 'Therapy Session') {
    if (status.value === 'Draft') filters.push([doctype, 'docstatus', '=', 0]);
    if (status.value === 'Submitted') filters.push([doctype, 'docstatus', '=', 1]);
    if (status.value === 'Cancelled') filters.push([doctype, 'docstatus', '=', 2]);
  }
  return filters;
}
const searchableRows = computed(() => rows.value.filter(row => { const needle=(isSessionList.value ? executionQuery.value : query.value).trim().toLowerCase(); return !needle || (tab.value==='appointments' ? [row.name,row.patient_name,row.patient,row.concern,row.service_room,row.branch,row.call_back_status].some(value=>String(value||'').toLowerCase().includes(needle)) : [row.name,row.patient_name,row.patient,row.therapy_type,row.service_unit,row.branch,row.custom_practitioner_name,row.practitioner].some(value=>String(value||'').toLowerCase().includes(needle))); }));
function matchesAppointmentStatus(row) {
  if (status.value === 'all') return true;
  const value = `${row.call_back_status || ''} ${row.status || ''}`.toLowerCase();
  if (status.value === 'Pending') return !value || value.includes('pending') || value.includes('open');
  if (status.value === 'Cancelled') return /cancelled/.test(value);
  if (status.value === 'No Show') return /no.?show/.test(value);
  if (status.value === 'Cancel') return /\bcancel\b/.test(value);
  if (status.value === 'Postponed') return /postponed/.test(value);
  return value.includes(status.value.toLowerCase());
}
function selectTab(id) { status.value = 'all'; tab.value = id; if (id !== 'scheduler' && id !== 'entry') load(); }
function clearSessionDates(){sessionFrom.value='';sessionTo.value='';}
function queueClientSearch() { clearTimeout(timers.search); timers.search = setTimeout(searchClients, 220); }
async function loadKpis() {
  const cycleStart=new Date(); cycleStart.setHours(12,0,0,0); cycleStart.setDate(6); if (new Date().getDate() < 6) cycleStart.setMonth(cycleStart.getMonth()-1);
  const endDate=new Date(cycleStart.getFullYear(),cycleStart.getMonth()+1,5,12);
  const start=`${cycleStart.getFullYear()}-${String(cycleStart.getMonth()+1).padStart(2,'0')}-06`;
  const end=`${endDate.getFullYear()}-${String(endDate.getMonth()+1).padStart(2,'0')}-${String(endDate.getDate()).padStart(2,'0')}`;
  try {
    const branchFilters = branch.value ? [['Patient Appointment','branch','=',branch.value]] : [];
    const pendingStatuses=['Scheduled','Re-Confirm','Reconfirm','Not Answering','Open','Pending','Confirmed'];
    const counts = await Promise.all([
      call('frappe.client.get_count', { doctype: 'Patient Appointment', filters: [['Patient Appointment','appointment_date','=',today], ...branchFilters] }),
      call('frappe.client.get_count', { doctype: 'Therapy Session', filters: [['Therapy Session','creation','>=',`${today} 00:00:00`],['Therapy Session','creation','<=',`${today} 23:59:59`], ...(branch.value ? [['Therapy Session','branch','=',branch.value]] : [])] }),
      call('frappe.client.get_count', { doctype: 'Patient Appointment', filters: [['Patient Appointment','appointment_date','Between',[start,end]], ...branchFilters] }),
      call('frappe.client.get_count', { doctype: 'Patient Appointment', filters: [['Patient Appointment','appointment_date','>=',start],['Patient Appointment','appointment_date','<',today],['Patient Appointment','call_back_status','in',pendingStatuses], ...branchFilters] }),
      call('frappe.client.get_count', { doctype: 'Patient Appointment', filters: [['Patient Appointment','appointment_date','=',today],['Patient Appointment','appointment_time','<',new Date().toTimeString().slice(0,8)],['Patient Appointment','call_back_status','in',pendingStatuses], ...branchFilters] })
    ]);
    kpis.value = { today: Number(counts[0]?.message||0), sessions: Number(counts[1]?.message||0), month: Number(counts[2]?.message||0), pending: Number(counts[3]?.message||0)+Number(counts[4]?.message||0) };
  } catch { /* KPI counts are supplementary; the reports remain usable. */ }
}
async function getSessionCount(filters,orFilters,signal){
  const args={doctype:'Therapy Session',fields:['count(name) as total'],filters,limit_start:0,limit_page_length:1};if(orFilters?.length)args.or_filters=orFilters;
  try{const result=await call('frappe.client.get_list',args,signal);const row=(result.message||[])[0];if(row)return Number(row.total??row.count??0);}catch{}
  if(!orFilters?.length){try{return Number((await call('frappe.client.get_count',{doctype:'Therapy Session',filters},signal)).message||0);}catch{}}
  return 0;
}
async function getAppointmentCount(filters,orFilters,signal){
  const args={doctype:'Patient Appointment',fields:['count(name) as total'],filters,limit_start:0,limit_page_length:1};if(orFilters?.length)args.or_filters=orFilters;
  try{const result=await call('frappe.client.get_list',args,signal);const row=(result.message||[])[0];return Number(row?.total??row?.count??0);}catch{return 0;}
}
async function call(method, args, signal) {
  return request(method, { args, signal, csrfToken: session.csrf_token });
}
async function loadBranches() {
  try {
    const response = await call('frappe.desk.reportview.get', reportArgs('Branch', ['name', 'branch'], []));
    if (!alive) return;
    branches.value = [...new Set(reportRows(response).map(row => row.branch || row.name).filter(name => name && !/testing branch|head office/i.test(name)))].sort();
  } catch (e) { if (alive) error.value = e.message; }
}
async function loadTherapyCategoryMap(){
  const candidates=['healthcare_service_unit','service_unit','medical_department','department','category','custom_category'];
  try{const meta=await call('frappe.desk.form.load.getdoctype',{doctype:'Therapy Type',with_parent:0});const dt=(meta.docs||[]).find(d=>d.name==='Therapy Type');const available=new Set((dt?.fields||[]).map(f=>f.fieldname));const fields=['name',...candidates.filter(f=>available.has(f))];const res=await call('frappe.client.get_list',{doctype:'Therapy Type',fields,limit_page_length:5000,order_by:'name asc'});therapyCategoryMap.value=Object.fromEntries((res.message||[]).map(row=>[row.name,[...candidates.map(f=>row[f]).filter(Boolean),row.name].join(' ')]));}catch{therapyCategoryMap.value={};}
}
function sessionCategory(row){const source=`${row.service_unit||''} ${row.therapy_type||''} ${therapyCategoryMap.value[row.therapy_type]||''}`.toLowerCase();if(/hair|skin|laser|dermat|cosmetic|facial|acne|peel|pigment|tattoo|hydra|botox|filler|prp|meso|q[ -]?switch|carbon|hifu|microneed|glow|rejuven|anti[ -]?age/.test(source))return 'dermat';if(/slim|cryo|weight|inch|tummy|body contour|cavitation|lipolysis|fat|ems|weight maintenance|body therapy/.test(source))return 'slimming';return 'slimming';}
async function loadPractitioners() {
  try {
    const response = await call('frappe.desk.reportview.get', reportArgs('Healthcare Practitioner', ['name', 'practitioner_name'], []));
    practitioners.value = reportRows(response).map(item => ({ value: item.name, label: item.practitioner_name || item.name }));
    staffByRole.value = { doctors: practitioners.value, physiotherapists: practitioners.value, dietitians: practitioners.value };
  } catch { practitioners.value = []; }
}
async function loadSessionMetadata() {
  try {
    const url = apiUrl('/api/method/frappe.desk.form.load.getdoctype?doctype=Therapy%20Session&with_parent=0');
    const response = await fetch(url, { credentials: apiCredentials(), headers: { Accept: 'application/json' } });
    const data = await response.json();
    if (!response.ok) throw new Error('Could not load Therapy Session fields.');
    const docs = data.docs || [];
    sessionMeta.value = docs.find(item => item?.doctype === 'DocType' && item.name === 'Therapy Session') || docs.find(item => item?.name === 'Therapy Session' && Array.isArray(item.fields)) || null;
    const standard = new Set(['custom_doctor','custom_doctor_name','custom_physiotherapist','custom_physiotherapist_name','custom_dietitian_id','custom_dietitian_name','patient','patient_name','therapy_plan','therapy_type','branch','service_unit','company','duration','start_date','start_time','end_time','practitioner','remarks','before_weight','after_weight','weight_loss','bmi','custom_before_weight','custom_after_weight','custom_upload_images','custom_after_photo','docstatus','name']);
    dynamicFields.value = (sessionMeta.value?.fields || []).filter(field => Number(field.reqd) === 1 && field.fieldname && !['appointment','department'].includes(field.fieldname) && !['Section Break','Column Break','Tab Break','HTML','Button','Heading','Fold','Check'].includes(field.fieldtype) && !standard.has(field.fieldname) && !field.hidden && !field.read_only);
    const defaults = { ...dynamicValues.value };
    dynamicFields.value.forEach(field => { if (defaults[field.fieldname] === undefined && fieldDefault(field) !== undefined) defaults[field.fieldname] = fieldDefault(field); });
    dynamicValues.value = defaults;
  } catch (e) { sessionMeta.value = null; error.value = e.message; }
}
function inputType(field) {
  return ({Date:'date',Time:'time',Int:'number',Float:'number',Currency:'number',Percent:'number',Check:'checkbox'}[field.fieldtype] || 'text');
}
function fieldDefault(field) {
  const value = field.default;
  return String(value || '').trim() === 'Today' ? today : value;
}
function validateSessionDocument(doc) {
  const missing = [];
  for (const field of sessionMeta.value?.fields || []) {
    if (Number(field.reqd) !== 1 || !field.fieldname || ['appointment','department'].includes(field.fieldname) || ['Section Break','Column Break','Tab Break','HTML','Button','Heading','Fold','Check'].includes(field.fieldtype)) continue;
    let value = doc[field.fieldname];
    if ((value === undefined || value === null || String(value).trim() === '') && fieldDefault(field) !== undefined && fieldDefault(field) !== null && String(fieldDefault(field)).trim() !== '' && !String(fieldDefault(field)).startsWith('eval:')) {
      value = fieldDefault(field); doc[field.fieldname] = value;
    }
    if (value === undefined || value === null || String(value).trim() === '') missing.push(field.label || field.fieldname);
  }
  if (missing.length) throw new Error(`Complete the mandatory Therapy Session fields: ${missing.join(', ')}`);
}
async function repairPlanInvoiceFlag(selectedPlan) {
  if (!selectedPlan || Number(selectedPlan.invoiced || 0) === 1) return;
  try {
    const response = await call('frappe.client.get_list', { doctype: 'Sales Invoice', fields: ['name','therapy_plan_reference_id','posting_date','docstatus','is_return'], filters: [['Sales Invoice','docstatus','=',1],['Sales Invoice','patient','=',client.value.name]], order_by: 'posting_date desc, creation desc', limit_page_length: 100 });
    let linked = null;
    for (const invoice of response.message || []) {
      if (Number(invoice.docstatus) !== 1 || Number(invoice.is_return) === 1) continue;
      if (invoice.therapy_plan_reference_id === selectedPlan.plan) { linked = invoice; break; }
      try {
        const full = (await call('frappe.client.get', { doctype: 'Sales Invoice', name: invoice.name })).message;
        if ([full.therapy_plan_reference_id, full.custom_therapy_plan, full.therapy_plan].includes(selectedPlan.plan)) { linked = invoice; break; }
      } catch { /* Ignore unreadable invoices; only a verified matching invoice can repair this flag. */ }
    }
    if (!linked) return;
    await call('frappe.client.set_value', { doctype: 'Therapy Plan', name: selectedPlan.plan, fieldname: 'invoiced', value: 1 });
    selectedPlan.invoiced = 1;
    if (selectedPlan.planDoc) selectedPlan.planDoc.invoiced = 1;
  } catch { /* Leave normal server-side session validation in control when invoice verification is unavailable. */ }
}
async function searchClients() {
  const text = clientSearch.value.trim();
  client.value = null; plan.value = null; planRows.value = []; clientSuggestions.value = [];
  if (text.length < 2) return;
  clientLoading.value = true;
  try {
    const result = await call('frappe.desk.search.search_link', { txt: text, doctype: 'Patient', reference_doctype: 'Therapy Session', page_length: 15, ignore_user_permissions: 1, filters: JSON.stringify({ status: 'Active' }) });
    clientSuggestions.value = result.message || [];
  } catch (e) { error.value = e.message; }
  finally { clientLoading.value = false; }
}
async function chooseClient(option) {
  clientLoading.value = true; error.value = ''; clientSuggestions.value = []; sessionBranch.value = '';
  try {
    const response = await call('frappe.client.get', { doctype: 'Patient', name: option.value });
    client.value = response.message;
    practitioner.value='';doctor.value='';physiotherapist.value='';dietitian.value='';plan.value=null;planRows.value=[];dynamicValues.value={};photoFiles.value={before:[],after:[]};
    clientSearch.value = client.value.patient_name || client.value.name;
    try {
      const prior = await call('frappe.client.get_count', { doctype: 'Therapy Session', filters: [['Therapy Session', 'patient', '=', client.value.name], ['Therapy Session', 'docstatus', '=', 1]] });
      requiresConsent.value = Number(prior.message || 0) === 0;
    } catch { requiresConsent.value = true; }
    consentFile.value = null; consentUploaded.value=false;
    planLoading.value = true;
    const result = await call('frappe.desk.reportview.get', reportArgs('Therapy Plan', ['name', 'start_date', 'status', 'docstatus'], [['Therapy Plan', 'patient', '=', client.value.name]], 0));
    const plans = reportRows(result);
    const detailRows = await Promise.all(plans.slice(0, 50).map(async item => {
      try {
        const full = (await call('frappe.client.get', { doctype: 'Therapy Plan', name: item.name })).message;
        const lines = full.therapy_plan_details || full.therapy_plan_detail || full.therapy_plan_table || full.therapy_details || full.plan_details || [];
        return lines.map(line => ({ plan: item.name, therapy: line.therapy_type || line.therapy || '', category: line.category || full.category || full.service_unit || '', unit: line.service_unit || full.service_unit || '', therapyDoc: null, branch: full.branch || client.value.branch_name || client.value.custom_branch || '', total: Number(line.no_of_sessions || line.total_sessions || line.sessions || 1), done: Number(line.sessions_completed || line.total_sessions_completed || 0), invoiced: Number(full.invoiced || 0), company: full.company || 'Life Slimming And Cosmetic Pvt Ltd', duration: Number(line.duration || full.duration || 30), rate: Number(line.rate || full.rate || 0), planDoc: full }));
      } catch { return []; }
    }));
    planRows.value = detailRows.flat().filter(item => item.therapy && item.total > item.done && Number(item.planDoc?.docstatus || 0) !== 2 && !/cancel/i.test(String(item.planDoc?.status || '')));
    const types = [...new Set(planRows.value.map(item => item.therapy))];
    const docs = await Promise.all(types.map(async name => { try { return (await call('frappe.client.get', { doctype:'Therapy Type', name })).message; } catch { return null; } }));
    therapyTypeMeta.value = Object.fromEntries(docs.filter(Boolean).map(doc => [doc.name, doc]));
    planRows.value.forEach(item => { item.therapyDoc = therapyTypeMeta.value[item.therapy] || null; item.category = item.category || item.therapyDoc?.medical_department || item.therapyDoc?.category || item.therapyDoc?.custom_category || item.therapyDoc?.department || item.therapyDoc?.healthcare_service_unit || item.therapyDoc?.service_unit || ''; item.requiresAfterPhoto = Boolean(item.therapyDoc && Object.entries(item.therapyDoc).some(([key,value]) => {const flag=[true,1,'1','yes','true','required','mandatory','on'].includes(typeof value==='string'?value.toLowerCase():value);const photo=/photo|image/i.test(key),required=/mandatory|required|reqd/i.test(key);return flag&&photo&&required&&(/after|before_after/.test(key)||(!/before/.test(key)&&!/after/.test(key)));})); });
  } catch (e) { error.value = e.message; }
  finally { clientLoading.value = false; planLoading.value = false; }
}
async function refreshClinicalSequence(){
  if(!client.value)return;
  const filters=[['Therapy Session','patient','=',client.value.name],['Therapy Session','docstatus','=',1]];
  const sessions=(await call('frappe.client.get_list',{doctype:'Therapy Session',fields:['name','therapy_type','therapy_plan','service_unit','start_date'],filters,limit_page_length:5000,order_by:'start_date asc, creation asc'})).message||[];
  const slimmingRows=sessions.filter(row=>sessionCategory(row)==='slimming');slimmingExecutionNumber.value=slimmingRows.length+1;
  const isCryo=/4\s*d.*cryo|cryo.*4\s*d/i.test(`${plan.value?.therapy||''} ${plan.value?.category||''}`);
  cryoFirstToday.value=isCryo&&!sessions.some(row=>row.therapy_type===plan.value?.therapy&&row.therapy_plan===plan.value?.plan&&String(row.start_date||'').slice(0,10)===today);
  repeatCryoToday.value=isCryo&&!cryoFirstToday.value;
  existingNextAppointment.value=null;
  if(repeatCryoToday.value){try{const next=await call('frappe.client.get_list',{doctype:'Patient Appointment',fields:['name','patient','appointment_type','appointment_date','appointment_time','branch','service_room','call_back_status','status','docstatus'],filters:[['Patient Appointment','patient','=',client.value.name]],order_by:'appointment_date asc, appointment_time asc',limit_page_length:1000});existingNextAppointment.value=(next.message||[]).find(a=>{const status=`${a.status||''} ${a.call_back_status||''}`.toLowerCase();return Number(a.docstatus||0)!==2&&(!a.appointment_type||String(a.appointment_type).toLowerCase()==='session')&&!/cancel|no.?show|closed|executed|visited|postpon/.test(status)&&String(a.appointment_date||'').slice(0,10)>today;})||null;}catch{existingNextAppointment.value=null;}}
}
async function createSession() {
  if(sessionSaving.value)return;
  const takingBy=practitioner.value||physiotherapist.value||dietitian.value||doctor.value;
  if (!client.value || !plan.value || !takingBy || !sessionBranch.value) { error.value = 'Select a client, therapy plan line, clinician, and branch.'; return; }
  if (!sessionForm.value.date || !sessionForm.value.startTime || Number(sessionForm.value.duration)<=0) { error.value = 'Session date and in time are required.'; return; }
  try { await refreshClinicalSequence(); } catch { error.value='Could not verify the client’s submitted session history. Retry before saving.'; return; }
  if (Number(sessionForm.value.quantity) !== 1) { error.value = 'Session quantity must be exactly 1.'; return; }
  const balance = Number(plan.value.total || 0) - Number(plan.value.done || 0);
  if (plan.value.total <= 0 || plan.value.done >= plan.value.total || balance <= 0) { error.value = 'This therapy plan has no remaining sessions.'; return; }
  if(balance>0&&!repeatCryoToday.value&&nextAppointment.value.date&&nextAppointment.value.date<today){error.value='The next appointment date cannot be in the past.';return;}
  const cryoRepeat = /4\s*d.*cryo|cryo.*4\s*d/i.test(`${plan.value.therapy} ${plan.value.category||''}`) && repeatCryoToday.value;
  if (balance > 0 && !cryoRepeat && (!nextAppointment.value.date || !nextAppointment.value.time || !nextRoom.value)) { error.value = 'Choose a service room and next appointment time before saving; sessions remain on the plan.'; return; }
  const isSlimming=/slim|cryo|weight|inch|tummy|body contour|cavitation|lipolysis|fat|ems|body therapy/i.test(`${plan.value.unit} ${plan.value.therapy} ${plan.value.category||''}`);
  const isCryo=/4\s*d.*cryo|cryo.*4\s*d/i.test(`${plan.value.therapy} ${plan.value.category||''}`);
  if (isSlimming && !sessionForm.value.bloodPressure.trim()) { error.value = 'BP is mandatory for every slimming execution.'; return; }
  if (sessionForm.value.bloodPressure.trim() && !/^\s*\d{2,3}\s*\/\s*\d{2,3}\s*$/.test(sessionForm.value.bloodPressure)) { error.value = 'Enter blood pressure as systolic/diastolic, for example 120/80.'; return; }
  const measurementFields=[['BMI','bmi'],['Before Weight','beforeWeight'],['After Weight','afterWeight'],['Water','water'],['Neck','neck'],['Fat','fat'],['Tummy','tummy'],['Thighs','thighs'],['BMR','bmr'],['Arms','arms'],['Hip','hip'],['Waist','waist']];
  const measurementCheckpoint=isSlimming&&(slimmingExecutionNumber.value===1||slimmingExecutionNumber.value%4===0);
  if(measurementCheckpoint&&(!isCryo||cryoFirstToday.value)){const missing=measurementFields.filter(([,key])=>!String(sessionForm.value[key]||'').trim()||Number(sessionForm.value[key])<=0);if(missing.length){error.value=`Required for slimming session ${slimmingExecutionNumber.value}: ${missing.map(([label])=>label).join(', ')}. Measurements must be greater than zero.`;return;}}
  if (isCryo && cryoFirstToday.value) { const required=[...measurementFields,['Dietitian','dietitian']];const missing=required.filter(([,key])=>key==='dietitian'?!dietitian.value:!String(sessionForm.value[key]||'').trim()||Number(sessionForm.value[key])<=0);if(missing.length){error.value=`Required for the first 4D Cryo execution today: ${missing.map(([label])=>label).join(', ')}. Measurements must be greater than zero.`;return;} }
  const beforeRequired = /hair/i.test(String(`${plan.value.category || ''} ${plan.value.unit || ''} ${plan.value.therapyDoc?.category||''} ${plan.value.therapyDoc?.medical_department||''} ${plan.value.therapyDoc?.department||''} ${plan.value.therapyDoc?.healthcare_service_unit||''}`));
  const afterRequired = Boolean(plan.value.requiresAfterPhoto);
  if (beforeRequired && !photoFiles.value.before.length) { error.value = 'A before photo is mandatory for Hair category treatment.'; return; }
  if (afterRequired && !photoFiles.value.after.length) { error.value = 'An after photo is mandatory for this therapy type.'; return; }
  if (photoFiles.value.before.length > 3 || photoFiles.value.after.length > 6) { error.value = 'Add up to 3 before photos and 6 after photos.'; return; }
  const signatures = [...photoFiles.value.before, ...photoFiles.value.after].map(file => `${file.name.toLowerCase()}|${file.size}|${file.lastModified}`);
  if (new Set(signatures).size !== signatures.length) { error.value = 'Duplicate session photos are not allowed.'; return; }
  if (globalThis.crypto?.subtle) {
    const photoHashes=[];
    for (const file of [...photoFiles.value.before,...photoFiles.value.after]) { const digest=await globalThis.crypto.subtle.digest('SHA-256',await file.arrayBuffer());photoHashes.push(Array.from(new Uint8Array(digest),value=>value.toString(16).padStart(2,'0')).join('')); }
    if(new Set(photoHashes).size!==photoHashes.length){error.value='The same image cannot be used for more than one session photo.';return;}
  }
  if (requiresConsent.value && !consentFile.value) { error.value = 'A signed consent form is required for this client’s first submitted therapy session.'; return; }
  for (const file of [...photoFiles.value.before, ...photoFiles.value.after]) if (!file.type.startsWith('image/') || file.size > 8 * 1024 * 1024) { error.value = 'Session photos must be images under 8 MB each.'; return; }
  if (consentFile.value && (consentFile.value.size > 5 * 1024 * 1024 || !/^(application\/pdf|image\/(jpeg|png))$/i.test(consentFile.value.type))) { error.value = 'Consent must be a PDF, JPG, or PNG under 5 MB.'; return; }
  sessionSaving.value = true; error.value = ''; sessionNotice.value = '';
  try {
    const firstCheck = await call('frappe.client.get_list', { doctype:'Therapy Session', fields:['name'], filters:[['Therapy Session','patient','=',client.value.name],['Therapy Session','docstatus','=',1]], order_by:'creation asc', limit_page_length:1 });
    requiresConsent.value = !(firstCheck.message || []).length;
    if (requiresConsent.value && !consentFile.value) throw new Error('A signed consent form is required for this client’s first submitted therapy session.');
    await repairPlanInvoiceFlag(plan.value);
    let mapped = {};
    try { const result = await call('healthcare.healthcare.doctype.therapy_plan.therapy_plan.make_therapy_session', { patient: client.value.name, therapy_type: plan.value.therapy, company: 'Life Slimming And Cosmetic Pvt Ltd', therapy_plan: plan.value.plan, practitioner: takingBy }); mapped = result.message || result; } catch { /* Match the legacy module's direct document fallback when the mapper is unavailable. */ }
    const total = Number(plan.value.total || 0), done = Number(plan.value.done || 0), completed = total ? Math.min(total, done + 1) : done + 1;
    const doc = { ...mapped, doctype: 'Therapy Session', naming_series: mapped.naming_series || 'HLC-THP-.YYYY.-', patient: client.value.name, patient_name: client.value.patient_name || client.value.name, patient_age: client.value.age || '', gender: client.value.sex || '', therapy_plan: plan.value.plan, therapy_type: plan.value.therapy, practitioner: takingBy, custom_practitioner_name: practitioners.value.find(item => item.value === takingBy)?.label || staffByRole.value.physiotherapists.find(item => item.value === takingBy)?.label || staffByRole.value.dietitians.find(item => item.value === takingBy)?.label || staffByRole.value.doctors.find(item => item.value === takingBy)?.label || takingBy, custom_doctor: doctor.value, custom_doctor_name: staffByRole.value.doctors.find(item => item.value === doctor.value)?.label || doctor.value, custom_physiotherapist: physiotherapist.value, custom_physiotherapist_name: staffByRole.value.physiotherapists.find(item => item.value === physiotherapist.value)?.label || physiotherapist.value, custom_dietitian_id: dietitian.value, custom_dietitian_name: staffByRole.value.dietitians.find(item => item.value === dietitian.value)?.label || dietitian.value, custom_dietitian: dietitian.value, dietitian: dietitian.value, healthcare_practitioner: takingBy, custom_healthcare_practitioner: takingBy, branch: sessionBranch.value, service_unit: plan.value.unit || '', company: mapped.company || plan.value.company || 'Life Slimming And Cosmetic Pvt Ltd', duration: Number(mapped.duration || sessionForm.value.duration || plan.value.duration || 30), rate: Number(mapped.rate || plan.value.rate || 0), invoiced: plan.value.invoiced, custom_actual_session_date: sessionForm.value.date, start_date: sessionForm.value.date, location: 'Center', custom_in_time_: `${sessionForm.value.startTime}:00`, start_time: `${sessionForm.value.startTime}:00`, before_weight: sessionForm.value.beforeWeight || null, custom_before_weight: sessionForm.value.beforeWeight || null, after_weight: sessionForm.value.afterWeight || null, custom_after_weight: sessionForm.value.afterWeight || null, weight_loss: sessionForm.value.beforeWeight && sessionForm.value.afterWeight ? Number(sessionForm.value.beforeWeight) - Number(sessionForm.value.afterWeight) : null, custom_bp_mmhg: sessionForm.value.bloodPressure || '', custom_blood_sugar_mgdl: sessionForm.value.bloodSugar || '', custom_pulse_bpm: sessionForm.value.pulse || '', custom_total_sessions_count: String(total), custom_sessions_complted: String(completed), custom_remaining_sessions: String(Math.max(0, total - completed)), custom_completed_percentage: total ? completed / total * 100 : 0, custom_assured_weight_target: plan.value.planDoc?.custom_assured_weight_target || '', custom_assured_inch_target: plan.value.planDoc?.custom_assured_inch_target || '', custom_health_status: plan.value.planDoc?.custom_health_status || client.value.custom_medical_history || '', bmi: sessionForm.value.bmi || client.value.bmi || '', remarks: sessionForm.value.remarks || '', docstatus: 0 };
    if (photoFiles.value.before.length) doc.custom_upload_images = [];
    if (photoFiles.value.after.length) doc.custom_after_photo = [];
    doc.custom_bp = sessionForm.value.bloodPressure || ''; doc.custom_sugar=sessionForm.value.bloodSugar||''; doc.custom_pulse=sessionForm.value.pulse||'';
    if (sessionForm.value.endTime) { doc.custom_out_time = `${sessionForm.value.endTime}:00`; doc.end_time = `${sessionForm.value.endTime}:00`; }
    for (const [input, field] of [['water','water'],['neck','neck'],['fat','fat'],['tummy','tummy_region_of_maximum_girth'],['thighs','thighs_9'],['bmr','bmr'],['arms','arms_mid_pt'],['hip','hip_most_prominent_widest_part_of_hipwhile_lying_down'],['waist','waist_1_above_the_iliac_crest'],['bodyFat','custom_body_fat'],['muscleMass','custom_muscle_mass'],['visceralFat','custom_visceral_fat'],['metabolicAge','custom_metabolic_age']]) if (sessionForm.value[input] !== '') doc[field] = sessionForm.value[input];
    for (const field of dynamicFields.value) if (dynamicValues.value[field.fieldname] !== undefined && dynamicValues.value[field.fieldname] !== '') doc[field.fieldname] = dynamicValues.value[field.fieldname];
    validateSessionDocument(doc);
    const existing = await call('frappe.client.get_list', { doctype: 'Therapy Session', fields: ['name'], filters: [['Therapy Session','docstatus','=',0],['Therapy Session','patient','=',doc.patient],['Therapy Session','therapy_plan','=',doc.therapy_plan],['Therapy Session','therapy_type','=',doc.therapy_type],['Therapy Session','branch','=',doc.branch],['Therapy Session','start_date','=',doc.start_date],['Therapy Session','owner','=',session.user]], order_by: 'modified desc', limit_page_length: 5 });
    let result;
    if (existing.message?.length) result = { message: (await call('frappe.client.get', { doctype: 'Therapy Session', name: existing.message[0].name })).message };
    else result = await call('frappe.client.insert', { doc });
    const sessionName = result.message?.name;
    if (Number(result.message?.docstatus || 0) !== 0) throw new Error('The matching session record is no longer a draft. Reload the client and start a fresh entry.');
    if (requiresConsent.value && sessionName && !consentUploaded.value) { await uploadConsent(sessionName); consentUploaded.value=true; }
    if (sessionName) {
      for (const [index,file] of photoFiles.value.before.entries()) await uploadAttachment(sessionName, file, 'custom_upload_images', index + 1);
      for (const [index,file] of photoFiles.value.after.entries()) await uploadAttachment(sessionName, file, 'custom_after_photo', index + 1);
    }
    if (balance > 0 && !cryoRepeat) await saveNextAppointment();
    else if(balance>0&&cryoRepeat&&existingNextAppointment.value) nextAppointment.value={date:existingNextAppointment.value.appointment_date,time:String(existingNextAppointment.value.appointment_time||'').slice(0,5)};
    else if(balance>0&&cryoRepeat&&!existingNextAppointment.value) throw new Error('No future appointment was found to reuse for this repeat 4D Cryo session. The session draft is saved; book its next appointment before submission.');
    const submitted=await submitSessionDraft(sessionName);
    sessionNotice.value = `Therapy Session ${sessionName} submitted${balance > 0 ? (cryoRepeat ? ' with the existing 4D Cryo booking' : ' and the next appointment booked') : ''}.`;
    sessionForm.value = { ...sessionForm.value, startTime: '', endTime: '', bloodPressure: '', bloodSugar: '', pulse: '', beforeWeight: '', afterWeight: '', remarks: '' };
  } catch (e) { error.value = e.message; }
  finally { sessionSaving.value = false; }
}
async function submitSessionDraft(name){
  let submitted=null,lastError=null;
  for(let attempt=0;attempt<4;attempt++){
    try{
      if(attempt)await new Promise(resolve=>setTimeout(resolve,350));
      const latest=(await call('frappe.client.get',{doctype:'Therapy Session',name})).message;
      if(!latest?.name)throw new Error(`Could not reload Therapy Session ${name} before submission.`);
      if(Number(latest.docstatus)!==0)throw new Error(`Therapy Session ${name} is no longer a draft.`);
      const result=await call('frappe.client.submit',{doc:latest});submitted=result.message||result;break;
    }catch(e){lastError=e;const message=String(e.message||'').toLowerCase();if(!/modified after|has been modified|timestamp/.test(message)||attempt===3)throw e;}
  }
  if(!submitted)throw lastError||new Error('Therapy Session submission failed.');
  if(Number(submitted.docstatus||0)!==1)submitted=(await call('frappe.client.get',{doctype:'Therapy Session',name})).message;
  if(Number(submitted?.docstatus)!==1)throw new Error(`Therapy Session ${name} was saved but the server did not confirm submission.`);
  return submitted;
}
async function saveNextAppointment() {
  const existing=await call('frappe.client.get_list',{doctype:'Patient Appointment',fields:['name','appointment_date','appointment_time','service_room','branch','status','call_back_status','docstatus'],filters:[['Patient Appointment','patient','=',client.value.name],['Patient Appointment','appointment_date','=',nextAppointment.value.date],['Patient Appointment','appointment_time','=',`${nextAppointment.value.time}:00`]],limit_page_length:100});
  const duplicate=(existing.message||[]).find(a=>Number(a.docstatus||0)!==2&&a.branch===sessionBranch.value&&a.service_room===nextRoom.value&&!/cancel|no.?show|closed|executed|visited|postpon/.test(`${a.status||''} ${a.call_back_status||''}`.toLowerCase()));
  if(duplicate?.name)return duplicate;
  const doc={docstatus:0,doctype:'Patient Appointment',name:`new-patient-appointment-${Date.now()}`,__islocal:1,__unsaved:1,naming_series:'HLC-APP-.YYYY.-',status:'',call_back_status:'Scheduled',appointment_for:'Practitioner',company:plan.value.company||'Life Slimming And Cosmetic Pvt Ltd',add_video_conferencing:0,invoiced:0,appointment_based_on_check_in:0,reminded:0,appointment_type:'Session',service_unit:plan.value.unit||'',patient:client.value.name,patient_name:client.value.patient_name||client.value.name,patient_sex:client.value.sex||'',custom_client_mobile_no:client.value.mobile||'',service_room:nextRoom.value,concern:plan.value.therapy,appointment_date:nextAppointment.value.date,appointment_time:`${nextAppointment.value.time}:00`,branch:sessionBranch.value};
  const response=await call('frappe.desk.form.save.savedocs',{doc:JSON.stringify(doc),action:'Save'});
  const saved=response.docs?.[0]||response.message?.docs?.[0]; if(!saved?.name) throw new Error('Next appointment was not saved. Please retry.');
}
async function uploadAttachment(sessionName, file, fieldname, slot) {
  const prefix = fieldname === 'custom_after_photo' ? 'AFTER' : 'BEFORE';
  const safeName=`${prefix}_${slot}_${file.name.replace(/[^a-zA-Z0-9._-]+/g, '_')}`;
  try { const files=(await call('frappe.client.get_list',{doctype:'File',fields:['file_name'],filters:[['File','attached_to_doctype','=','Therapy Session'],['File','attached_to_name','=',sessionName],['File','file_name','=',safeName]],limit_page_length:1})).message||[];if(files.length)return; } catch {}
  const form = new FormData();
  const taggedFile = new File([file], safeName, { type: file.type, lastModified: file.lastModified });
  form.append('file', taggedFile, taggedFile.name); form.append('is_private', '1'); form.append('doctype', 'Therapy Session'); form.append('docname', sessionName); form.append('fieldname', '');
  const response = await fetch(apiUrl('/api/method/upload_file'), { method: 'POST', credentials: apiCredentials(), headers: { 'X-Frappe-CSRF-Token': session.csrf_token || '' }, body: form });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || !body.message?.file_url) throw new Error(`The draft was saved, but ${fieldname} photo upload failed.`);
}
async function uploadConsent(sessionName) {
  try { const files=(await call('frappe.client.get_list',{doctype:'File',fields:['file_name'],filters:[['File','attached_to_doctype','=','Therapy Session'],['File','attached_to_name','=',sessionName]],limit_page_length:100})).message||[];if(files.some(file=>String(file.file_name||'').toLowerCase().includes('consent')))return; } catch {}
  const form = new FormData();
  form.append('file', consentFile.value, `CONSENT_FORM_${consentFile.value.name.replace(/[^a-zA-Z0-9._-]+/g, '_')}`);
  form.append('is_private', '1'); form.append('doctype', 'Therapy Session'); form.append('docname', sessionName);
  const response = await fetch(apiUrl('/api/method/upload_file'), { method: 'POST', credentials: apiCredentials(), headers: { 'X-Frappe-CSRF-Token': session.csrf_token || '' }, body: form });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || !body.message?.file_url) throw new Error('The draft was saved, but the consent form upload failed. Reopen the draft and attach the consent before submission.');
}
async function openRooms() {
  roomOpen.value = true; roomBranch.value = branch.value || roomBranch.value || branches.value[0] || ''; await loadRooms();
}
async function loadNextRooms() {
  if (!sessionBranch.value) { nextRooms.value = []; return; }
  try { const response = await call('frappe.client.get_list', { doctype:'Service Room', fields:['name','service_room','branch','enable'], filters:[['Service Room','branch','=',sessionBranch.value],['Service Room','enable','=',1]], order_by:'service_room asc', limit_page_length:500 }); nextRooms.value = response.message || []; } catch { nextRooms.value = []; }
}
async function loadRooms() {
  roomLoading.value = true; error.value = '';
  try {
    if (!roomBranch.value) { rooms.value = []; return; }
    const response = await call('frappe.client.get_list', { doctype: 'Service Room', fields: ['name', 'service_room', 'branch', 'enable'], filters: [['Service Room', 'branch', '=', roomBranch.value]], order_by: 'service_room asc, name asc', limit_page_length: 500 });
    rooms.value = response.message || [];
  } catch (e) { error.value = e.message; }
  finally { roomLoading.value = false; }
}
async function addRoom() {
  const name = newRoom.value.trim(); if (!name) return;
  if (!roomBranch.value) { error.value = 'Select a branch before adding a room.'; return; }
  roomLoading.value = true; error.value = '';
  try {
    await call('frappe.client.insert', { doc: { doctype: 'Service Room', enable: 1, service_room: name, branch: roomBranch.value } });
    newRoom.value = ''; await loadRooms();
  } catch (e) { error.value = e.message; roomLoading.value = false; }
}
async function toggleRoom(room) {
  roomLoading.value = true; error.value = '';
  try { await call('frappe.client.set_value', { doctype: 'Service Room', name: room.name, fieldname: 'enable', value: Number(room.enable) ? 0 : 1 }); await loadRooms(); }
  catch (e) { error.value = e.message; roomLoading.value = false; }
}
async function viewAppointment(row) {
  detailLoading.value = true; error.value = '';
  try {
    const response = await call('frappe.client.get', { doctype: 'Patient Appointment', name: row.name });
    selectedAppointment.value = response.message;
    appointmentStatus.value = response.message?.call_back_status || 'Scheduled';
    rescheduleDate.value = response.message?.appointment_date || today;
    rescheduleTime.value = String(response.message?.appointment_time || '').slice(0, 5);
  } catch (e) { error.value = e.message; }
  finally { detailLoading.value = false; }
}
async function saveAppointmentStatus() {
  if (!selectedAppointment.value) return;
  if (appointmentStatus.value === 'Re-Scheduled' && (!rescheduleDate.value || !rescheduleTime.value)) { error.value = 'Choose a new appointment date and time.'; return; }
  if (rescheduleDate.value < today && appointmentStatus.value === 'Re-Scheduled') { error.value = 'The new appointment date cannot be in the past.'; return; }
  appointmentSaving.value = true; error.value = '';
  try {
    const result=await call('life_slimming.api.server_scripts.life_ops_update_appointment_status.run',{
      appointment_name:selectedAppointment.value.name,
      new_status:appointmentStatus.value,
      new_appointment_date:appointmentStatus.value==='Re-Scheduled'?rescheduleDate.value:'',
      new_appointment_time:appointmentStatus.value==='Re-Scheduled'?`${rescheduleTime.value}:00`:''
    });
    const message=result.message||result;
    if(!message.ok)throw new Error(message.message||'The server did not confirm this appointment update.');
    selectedAppointment.value = null;
    await load();
  } catch (e) { error.value = e.message; }
  finally { appointmentSaving.value = false; }
}

async function load() {
  if (['scheduler', 'entry'].includes(tab.value)) return;
  const range = tab.value==='sessions' ? [sessionFrom.value,sessionTo.value] : isSessionList.value ? [executionFrom.value, executionTo.value] : [reportFrom.value, reportTo.value];
  if (range[0] && range[1] && range[0] > range[1]) { error.value = 'From date must be before To date.'; return; }
  controller?.abort(); const current = new AbortController(); controller = current;
  loading.value = true; error.value = ''; rows.value = []; totalRows.value=0;
  const doctype = tab.value === 'appointments' ? 'Patient Appointment' : 'Therapy Session';
  if(isSessionList.value&&!Object.keys(therapyCategoryMap.value).length)await loadTherapyCategoryMap();
  const fields = doctype === 'Patient Appointment' ? appointmentFields : sessionFields.value;
  try {
    const filters=filtersFor(doctype);
    const requestArgs=reportArgs(doctype, fields, filters, isSessionList.value ? (page.value-1)*pageSize : 0);
    requestArgs.page_length=isPagedList.value?pageSize:500;
    requestArgs.order_by=doctype==='Patient Appointment'?`\`tab${doctype}\`.\`appointment_date\` desc, \`tab${doctype}\`.\`appointment_time\` desc`:`\`tab${doctype}\`.\`start_date\` desc, \`tab${doctype}\`.\`start_time\` desc, \`tab${doctype}\`.\`creation\` desc`;
    let fetchedRows;
    if(isSessionList.value){let sessionFilters=filters;if(tab.value==='slimming'||tab.value==='dermat'){const types=Object.entries(therapyCategoryMap.value).filter(([name,category])=>sessionCategory({therapy_type:name,service_unit:category})===tab.value).map(([name])=>name);if(types.length)sessionFilters=[...filters,['Therapy Session','therapy_type','in',types]];else sessionFilters=[...filters,['Therapy Session','name','=','__no_matching_therapy_type__']];}const needle=executionQuery.value.trim();const or_filters=needle?fields.filter(f=>['name','patient','patient_name','therapy_plan','therapy_type','custom_practitioner_name','practitioner','custom_doctor_name','custom_dietitian_name','custom_machine','custom_remarks'].includes(f)).map(f=>['Therapy Session',f,'like',`%${needle}%`]):undefined;const result=await call('frappe.client.get_list',{doctype,fields,filters:sessionFilters,or_filters,limit_start:(page.value-1)*pageSize,limit_page_length:pageSize,order_by:'start_date desc, start_time desc, creation desc'},current.signal);fetchedRows=result.message||[];}
    else if(tab.value==='appointments'){const needle=query.value.trim();const or_filters=needle?['name','patient','patient_name','concern','service_room','branch'].map(field=>['Patient Appointment',field,'like',`%${needle}%`]):undefined;const result=await call('frappe.client.get_list',{doctype,fields,filters,or_filters,limit_start:(page.value-1)*pageSize,limit_page_length:pageSize,order_by:'appointment_date desc, appointment_time desc'},current.signal);fetchedRows=result.message||[];}
    else fetchedRows=reportRows(await call('frappe.desk.reportview.get',requestArgs,current.signal));
    if (!alive || controller !== current) return;
    const fetched=fetchedRows.filter(row => {
      const service = `${row.therapy_type || ''} ${row.service_unit || ''}`.toLowerCase();
      const matchesExecution = tab.value === 'slimming' ? sessionCategory(row)==='slimming' : tab.value === 'dermat' ? sessionCategory(row)==='dermat' : true;
      return matchesExecution && (doctype !== 'Patient Appointment' || matchesAppointmentStatus(row));
    });
    if(isSessionList.value){
      const catTypes=(tab.value==='slimming'||tab.value==='dermat')?Object.entries(therapyCategoryMap.value).filter(([name,category])=>sessionCategory({therapy_type:name,service_unit:category})===tab.value).map(([name])=>name):[];
      const countFilters=(tab.value==='slimming'||tab.value==='dermat')?(catTypes.length?[...filters,['Therapy Session','therapy_type','in',catTypes]]:[...filters,['Therapy Session','name','=','__no_matching_therapy_type__']]):filters;
      const orFilters=executionQuery.value.trim()?fields.filter(f=>['name','patient','patient_name','therapy_plan','therapy_type','practitioner','custom_practitioner_name','custom_doctor_name','custom_dietitian_name','custom_machine','custom_remarks'].includes(f)).map(f=>['Therapy Session',f,'like',`%${executionQuery.value.trim()}%`]):[];
      totalRows.value=await getSessionCount(countFilters,orFilters,current.signal);
    }else if(tab.value==='appointments'){const needle=query.value.trim();const orFilters=needle?['name','patient','patient_name','concern','service_room','branch'].map(field=>['Patient Appointment',field,'like',`%${needle}%`]):[];totalRows.value=await getAppointmentCount(filters,orFilters,current.signal);}
    else totalRows.value=fetched.length;
    rows.value = doctype === 'Therapy Session' ? await enrichSessions(fetched,current.signal) : fetched;
  } catch (e) { if (alive && controller === current && e.name !== 'AbortError') error.value = e.message; }
  finally { if (alive && controller === current) loading.value = false; }
}
async function csv() {
  const columns = tab.value === 'appointments' ? appointmentFields : reportColumns.value;
  let exportRows=rows.value;
  if(tab.value==='appointments'){
    try{
      exportRows=[];const filters=filtersFor('Patient Appointment');const needle=query.value.trim();const or_filters=needle?['name','patient','patient_name','concern','service_room','branch'].map(field=>['Patient Appointment',field,'like',`%${needle}%`]):undefined;
      for(let offset=0;offset<5000;offset+=500){const result=await call('frappe.client.get_list',{doctype:'Patient Appointment',fields:appointmentFields,filters,or_filters,limit_start:offset,limit_page_length:500,order_by:'appointment_date asc, appointment_time asc, creation asc'});const batch=result.message||[];exportRows.push(...batch);if(batch.length<500)break;}
    }catch(e){error.value=`Appointment export stopped: ${e.message}`;return;}
  }
  const quote = value => { const text = String(value ?? ''); return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text; };
  const content = [columns.map(column=>typeof column==='string'?column:column.label), ...exportRows.map(row => columns.map(column=>{if(typeof column==='string')return row[column];const val=column.value?column.value(row):(column.fields||[]).map(k=>row[k]).find(v=>v!==undefined&&v!==null&&v!=='');return val??'';}))].map(row => row.map(quote).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob(['\ufeff', content], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = `service-${tab.value}-${today}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function sessionRecordUrl(name) { return `/app/therapy-session/${encodeURIComponent(name)}`; }
watch(plan, async value => { if (value?.branch) sessionBranch.value = value.branch; else if (!sessionBranch.value) sessionBranch.value = client.value?.branch_name || client.value?.custom_branch || ''; nextRoom.value=''; repeatCryoToday.value=false; loadNextRooms(); if (value && client.value && /4\s*d.*cryo|cryo.*4\s*d/i.test(`${value.therapy} ${value.category||''}`)) { try { const count=await call('frappe.client.get_count',{doctype:'Therapy Session',filters:[['Therapy Session','patient','=',client.value.name],['Therapy Session','therapy_plan','=',value.plan],['Therapy Session','therapy_type','=',value.therapy],['Therapy Session','docstatus','=',1],['Therapy Session','start_date','=',today]]}); repeatCryoToday.value=Number(count.message||0)>0; } catch { repeatCryoToday.value=false; } } });
watch(sessionBranch, () => { nextRoom.value=''; loadNextRooms(); });
watch([tab, reportFrom, reportTo, sessionFrom, sessionTo, executionFrom, executionTo, branch, status], () => { if (!['scheduler', 'entry'].includes(tab.value)) { if(page.value!==1)page.value=1;else load(); } });
watch([query, executionQuery], () => { if(page.value!==1)page.value=1;else if(isPagedList.value)load(); });
watch(page, () => { if(isPagedList.value) load(); });
watch(executionPreset, () => { if(isSessionList.value) load(); });
watch(branch, () => loadKpis());
onMounted(async () => { await loadSessionMetadata(); loadTherapyCategoryMap(); loadBranches(); loadPractitioners(); loadKpis(); load(); });
onBeforeUnmount(() => { alive = false; controller?.abort(); clearTimeout(timers.search); });
</script>

<template>
  <main class="service-page">
    <header class="service-header"><div><span>CLIENTS &amp; CLINICAL</span><h1>Operations &amp; Service</h1><p>Appointments, therapy sessions and service execution</p></div><div class="service-head-actions"><button @click="selectTab('entry')">+ New Session</button><button @click="selectTab('scheduler')">+ Book Appointment</button><button @click="selectTab('sessions')">Therapy Session Report</button><button @click="openRooms">⚙ Manage Rooms</button><button v-if="!['scheduler','entry'].includes(tab)" :disabled="loading" @click="load">{{ loading ? 'Loading…' : '↻ Refresh' }}</button></div></header>
    <section class="service-kpis"><article><span>Today appointments</span><strong>{{kpis.today}}</strong></article><article><span>This month (6th–5th)</span><strong>{{kpis.month}}</strong></article><article><span>Pending follow-up</span><strong>{{kpis.pending}}</strong></article><article><span>Today session entries</span><strong>{{kpis.sessions}}</strong></article></section>
    <nav class="service-tabs" aria-label="Service sections"><button v-for="item in tabs.filter(item=>item.id!=='sessions')" :key="item.id" :class="{active:tab===item.id}" @click="selectTab(item.id)">{{ item.label }}</button></nav>
    <AppointmentSchedulerPage v-if="tab==='scheduler'" />
    <section v-else-if="tab==='entry'" class="service-entry-card">
      <div class="service-section-heading"><div><span>THERAPY SESSION</span><h2>New Session Entry</h2><p>Choose a client and an available therapy plan line, then save a draft for review.</p></div></div>
      <div class="service-entry-grid">
        <label class="service-client-search">Client search<input v-model="clientSearch" type="search" placeholder="Name, ID or mobile" @input="queueClientSearch" @keydown.enter.prevent="searchClients"><button type="button" :disabled="clientLoading" @click="searchClients">{{clientLoading?'Searching…':'Search'}}</button></label>
        <div v-if="clientSuggestions.length" class="service-suggestions"><button v-for="item in clientSuggestions" :key="item.value" @click="chooseClient(item)"><strong>{{item.description||item.label||item.value}}</strong><small>{{item.value}}</small></button></div>
        <p v-if="client" class="service-selected-client">Selected: <strong>{{client.patient_name||client.name}}</strong> · {{client.name}}</p>
        <label>Therapy plan line<select v-model="plan" :disabled="!planRows.length"><option :value="null">{{planLoading?'Loading plans…':'Select service'}}</option><option v-for="item in planRows" :key="item.plan+'|'+item.therapy+'|'+item.unit" :value="item">{{item.therapy}} · {{item.unit||'Service'}} · {{item.plan}} <template v-if="item.total">· {{item.done}} / {{item.total}} done</template></option></select></label>
        <label>Therapist<select v-model="practitioner"><option value="">Select therapist</option><option v-for="item in practitioners" :key="item.value" :value="item.value">{{item.label}}</option></select></label>
        <label>Doctor<select v-model="doctor"><option value="">Select doctor</option><option v-for="item in staffByRole.doctors" :key="item.value" :value="item.value">{{item.label}}</option></select></label><label>Physiotherapist<select v-model="physiotherapist"><option value="">Select physiotherapist</option><option v-for="item in staffByRole.physiotherapists" :key="item.value" :value="item.value">{{item.label}}</option></select></label><label>Dietitian<select v-model="dietitian"><option value="">Select dietitian</option><option v-for="item in staffByRole.dietitians" :key="item.value" :value="item.value">{{item.label}}</option></select></label>
        <label>Branch *<select v-model="sessionBranch" required><option value="">Select branch</option><option v-if="sessionBranch&&!branches.includes(sessionBranch)" :value="sessionBranch">{{sessionBranch}}</option><option v-for="item in branches" :key="item">{{item}}</option></select></label>
        <label>Session date<input v-model="sessionForm.date" type="date" required></label><label>In time<input v-model="sessionForm.startTime" type="time" required></label><label>Out time<input v-model="sessionForm.endTime" type="time"></label>
        <template v-if="plan && Number(plan.total)>Number(plan.done) && !repeatCryoToday"><label>Next appointment date *<input v-model="nextAppointment.date" type="date" :min="today" required></label><label>Next appointment time *<input v-model="nextAppointment.time" type="time" required></label><label>Next service room *<select v-model="nextRoom" required><option value="">Select enabled room</option><option v-for="room in nextRooms" :key="room.name" :value="room.name">{{room.service_room||room.name}}</option></select></label></template>
        <p v-else-if="repeatCryoToday" class="service-note service-wide">A repeat 4D Cryo session reuses the client’s existing upcoming Session appointment.</p>
        <label>Blood pressure<input v-model="sessionForm.bloodPressure" placeholder="e.g. 120/80"></label><label>Blood sugar<input v-model="sessionForm.bloodSugar" type="number" min="0"></label><label>Pulse<input v-model="sessionForm.pulse" type="number" min="0"></label><p v-if="vitalAlerts.length" class="service-vital-alert service-wide" role="alert">{{vitalAlerts.join(' ')}}</p>
        <label>Weight before (kg)<input v-model="sessionForm.beforeWeight" type="number" min="0" step="0.1"></label><label>Weight after (kg)<input v-model="sessionForm.afterWeight" type="number" min="0" step="0.1"></label><label>BMI<input v-model="sessionForm.bmi" type="number" min="0" step="0.1"></label>
        <template v-if="/slim|weight|body|cryo|inch/i.test(plan?.unit||'')"><label>Water<input v-model="sessionForm.water" type="number" min="0" step="0.1"></label><label>Neck<input v-model="sessionForm.neck" type="number" min="0" step="0.1"></label><label>Fat<input v-model="sessionForm.fat" type="number" min="0" step="0.1"></label><label>Tummy<input v-model="sessionForm.tummy" type="number" min="0" step="0.1"></label><label>Thighs<input v-model="sessionForm.thighs" type="number" min="0" step="0.1"></label><label>BMR<input v-model="sessionForm.bmr" type="number" min="0" step="0.1"></label><label>Arms<input v-model="sessionForm.arms" type="number" min="0" step="0.1"></label><label>Hip<input v-model="sessionForm.hip" type="number" min="0" step="0.1"></label><label>Waist<input v-model="sessionForm.waist" type="number" min="0" step="0.1"></label><label>Body fat %<input v-model="sessionForm.bodyFat" type="number" min="0" step="0.1"></label><label>Muscle mass<input v-model="sessionForm.muscleMass" type="number" min="0" step="0.1"></label><label>Visceral fat<input v-model="sessionForm.visceralFat" type="number" min="0" step="0.1"></label><label>Metabolic age<input v-model="sessionForm.metabolicAge" type="number" min="0"></label></template>
        <label class="service-wide">Before-session photos<input type="file" accept="image/*" multiple @change="photoFiles.before=Array.from($event.target.files||[]).slice(0,3)"><small>Up to 3 images, 8 MB each</small></label><label class="service-wide">After-session photos<input type="file" accept="image/*" multiple @change="photoFiles.after=Array.from($event.target.files||[]).slice(0,6)"><small>Up to 6 images, 8 MB each</small></label>
        <label v-if="requiresConsent" class="service-wide">Signed consent form *<input type="file" accept="application/pdf,image/jpeg,image/png" @change="consentFile=$event.target.files?.[0]||null"><small>PDF, JPG, or PNG · maximum 5 MB</small></label>
        <label v-for="field in dynamicFields" :key="field.fieldname">{{field.label||field.fieldname}} *<select v-if="field.fieldtype==='Select'" v-model="dynamicValues[field.fieldname]"><option value="">Select</option><option v-for="option in String(field.options||'').split('\n').filter(Boolean)" :key="option">{{option}}</option></select><input v-else v-model="dynamicValues[field.fieldname]" :type="inputType(field)" :step="['Float','Currency','Percent'].includes(field.fieldtype)?'0.01':undefined" required></label>
        <label class="service-wide">Remarks<textarea v-model="sessionForm.remarks" rows="3"></textarea></label>
      </div>
      <p v-if="sessionNotice" class="service-success" role="status">{{sessionNotice}}</p><p v-if="error" class="service-error" role="alert">{{error}}</p>
      <footer><button :disabled="sessionSaving||!client||!plan||(!practitioner&&!doctor&&!physiotherapist&&!dietitian)||!sessionBranch" @click="createSession">{{sessionSaving?'Saving…':'Save draft session'}}</button></footer>
    </section>
    <template v-else>
      <section class="service-filters"><template v-if="tab==='sessions'"><label>From<input v-model="sessionFrom" type="date"></label><label>To<input v-model="sessionTo" type="date"></label><button type="button" @click="clearSessionDates">Clear Dates</button></template><template v-else-if="isSessionList"><label>From<input v-model="executionFrom" type="date"></label><label>To<input v-model="executionTo" type="date"></label><label>Period<select v-model="executionPreset" @change="applyExecutionPreset"><option value="all">Custom / all</option><option value="today">Today</option><option value="yesterday">Yesterday</option><option value="thisweek">This week</option><option value="lastmonth">Last month</option><option value="thismonth">This month</option></select></label></template><template v-else><label>From<input v-model="reportFrom" type="date"></label><label>To<input v-model="reportTo" type="date"></label></template><label>Branch<select v-model="branch"><option value="">All permitted branches</option><option v-for="item in branches" :key="item">{{ item }}</option></select></label><label>Status<select v-model="status"><option value="all">All statuses</option><template v-if="tab==='appointments'"><option>Scheduled</option><option>Re-Confirm</option><option>Reconfirm</option><option>Not Answering</option><option>Confirmed</option><option>Open</option><option>Pending</option><option>Visited</option><option>Executed</option><option>Closed</option><option>Postponed</option><option>Re-Scheduled</option><option>Cancel</option></template><template v-else><option>Draft</option><option>Submitted</option><option>Cancelled</option></template></select></label><label v-if="!isSessionList" class="service-search">Search<input v-model="query" type="search" placeholder="Client, service, branch or staff"></label><template v-if="isSessionList"><label class="service-search">Search<input v-model="executionQuery" type="search" placeholder="Client, service, therapist"></label></template><button :disabled="loading" @click="load">Apply</button><button :disabled="loading||!rows.length" @click="csv">Export CSV</button></section>
      <p v-if="error" class="service-error" role="alert">{{ error }} <button @click="load">Retry</button></p>
      <p v-else-if="loading" role="status">Loading {{ tabs.find(item=>item.id===tab)?.label.toLowerCase() }}…</p>
      <p v-else class="service-count" role="status">{{ (isSessionList?totalRows:rows.length).toLocaleString('en-IN') }} records · Page {{ page }} of {{ pageCount }}</p>
      <div class="service-table-wrap"><table><thead><tr><th v-for="field in (tab==='appointments'?appointmentFields:reportColumns)" :key="typeof field==='string'?field:field.label">{{ typeof field==='string'?field.replace(/^custom_/, '').replaceAll('_',' '):field.label }}</th><th>Action</th></tr></thead><tbody><tr v-for="row in visible" :key="row.name"><td v-for="field in (tab==='appointments'?appointmentFields:reportColumns)" :key="typeof field==='string'?field:field.label"><template v-if="tab==='appointments'">{{row[field]??'—'}}</template><template v-else-if="rowPhoto(row,field)"><a :href="sessionCell(row,field)" target="_blank" rel="noopener">Open</a></template><template v-else>{{sessionCell(row,field)}}</template></td><td><button v-if="tab==='appointments'" class="service-row-action" @click="viewAppointment(row)">Update</button><a v-else class="service-row-action" :href="sessionRecordUrl(row.name)" target="_blank" rel="noopener">{{Number(row.docstatus)===1?'View in ERP':Number(row.docstatus)===2?'Cancelled':'Review / Submit'}}</a></td></tr><tr v-if="!loading&&!visible.length"><td :colspan="(tab==='appointments'?appointmentFields.length:reportColumns.length)+1" class="service-empty">No records match these filters.</td></tr></tbody></table></div>
      <footer class="service-pager"><button :disabled="page<=1||loading" @click="page--">← Previous</button><span>Page {{ page }} of {{ pageCount }}</span><button :disabled="page>=pageCount||loading" @click="page++">Next →</button></footer>
    </template>
    <div v-if="roomOpen" class="service-overlay" @click.self="roomOpen=false"><section class="service-dialog" role="dialog" aria-modal="true" aria-labelledby="service-room-title"><header><h2 id="service-room-title">Service Rooms</h2><button @click="roomOpen=false">×</button></header><label>Branch<select v-model="roomBranch" :disabled="roomLoading" @change="loadRooms"><option value="">Select branch</option><option v-for="item in branches" :key="item">{{item}}</option></select></label><p v-if="roomLoading" role="status">Loading rooms…</p><ul v-else><li v-for="room in rooms" :key="room.name"><span>{{room.service_room||room.name}}</span><button :disabled="roomLoading" @click="toggleRoom(room)">{{Number(room.enable)?'Disable':'Enable'}}</button></li><li v-if="!rooms.length">No rooms found for this branch.</li></ul><form @submit.prevent="addRoom"><label>New room<input v-model="newRoom" required placeholder="Room name"></label><button :disabled="roomLoading">Add room</button></form><p class="service-note">Room changes follow your ERP permissions and branch scope.</p></section></div>
    <div v-if="selectedAppointment" class="service-overlay" @click.self="selectedAppointment=null"><section class="service-dialog" role="dialog" aria-modal="true" aria-labelledby="service-appt-title"><header><h2 id="service-appt-title">Appointment status</h2><button :disabled="appointmentSaving" @click="selectedAppointment=null">×</button></header><p v-if="detailLoading" role="status">Loading appointment…</p><template v-else><p><strong>{{selectedAppointment.patient_name||selectedAppointment.patient}}</strong><br>{{selectedAppointment.name}} · {{selectedAppointment.branch}}</p><label>Booking status<select v-model="appointmentStatus"><option>Scheduled</option><option>Re-Confirm</option><option>Re-Scheduled</option><option>Not Answering</option><option>Closed</option><option>Cancel</option></select></label><div v-if="appointmentStatus==='Re-Scheduled'" class="service-reschedule"><label>New date<input v-model="rescheduleDate" type="date" :min="today"></label><label>New time<input v-model="rescheduleTime" type="time"></label></div><footer><button :disabled="appointmentSaving" @click="selectedAppointment=null">Cancel</button><button :disabled="appointmentSaving" @click="saveAppointmentStatus">{{appointmentSaving?'Saving…':'Save status'}}</button></footer></template></section></div>
  </main>
</template>

<style scoped>
.service-page{max-width:1500px;margin:auto;padding:8px 0 28px;color:#183a2c}
.service-header{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px 22px;border-radius:14px;background:linear-gradient(120deg,#123e2c,#23734a);color:#fff}
.service-header span{font-size:11px;letter-spacing:.12em;opacity:.8}.service-header h1{margin:4px 0;font-size:28px}.service-header p{margin:0;color:#dbe9df}.service-head-actions{display:flex;gap:8px;flex-wrap:wrap}
.service-header button,.service-filters button,.service-pager button,.service-entry-card footer button,.service-dialog form button{border:1px solid #cfdbd2;border-radius:8px;padding:9px 12px;background:#fff;color:#204734;cursor:pointer}
.service-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}.service-kpis article{display:grid;gap:8px;padding:15px 18px;border:1px solid #dce8df;border-radius:12px;background:#fff}.service-kpis span{font-size:12px;color:#65776c}.service-kpis strong{font-size:24px;color:#1b6740}
.service-tabs{display:flex;gap:8px;overflow-x:auto;padding:16px 0}.service-tabs button{white-space:nowrap;border:1px solid #d3e0d6;border-radius:9px;padding:10px 14px;background:#fff;color:#315843;cursor:pointer}.service-tabs button.active{background:#eaf5ed;border-color:#79a98a;color:#145c39;font-weight:700}
.service-filters{display:flex;align-items:end;flex-wrap:wrap;gap:10px;padding:14px;background:#f5f8f5;border:1px solid #dce8df;border-radius:12px;margin-bottom:14px}.service-filters label,.service-entry-grid label,.service-dialog form label{display:grid;gap:5px;font-size:12px;color:#53685d}
.service-filters input,.service-filters select,.service-entry-grid input,.service-entry-grid select,.service-entry-grid textarea,.service-dialog form input,.service-dialog select,.service-dialog input{min-width:130px;padding:9px;border:1px solid #cfdbd2;border-radius:8px;background:#fff;color:#183a2c;font:inherit}.service-search{flex:1}.service-search input{min-width:190px}
.service-count{color:#65776c}.service-error{padding:12px;background:#fff0ed;color:#8b3426;border-radius:8px}.service-success{padding:12px;background:#eaf7ee;color:#1d6940;border-radius:8px}.service-note{color:#65776c}
.service-table-wrap{overflow:auto;background:#fff;border:1px solid #dce8df;border-radius:12px}.service-table-wrap table{width:100%;border-collapse:collapse;min-width:1100px}.service-table-wrap th,.service-table-wrap td{padding:10px 12px;border-bottom:1px solid #edf1ed;text-align:left;white-space:nowrap}.service-table-wrap th{position:sticky;top:0;background:#f1f7f2;text-transform:capitalize;color:#365b46;font-size:12px}.service-empty{text-align:center!important;padding:30px!important;color:#718076}
.service-pager{display:flex;align-items:center;justify-content:center;gap:16px;padding:16px}.service-pager button:disabled,.service-header button:disabled{opacity:.5;cursor:wait}.service-row-action{border:1px solid #c9d9ce;border-radius:6px;padding:6px 10px;background:#f4f8f5;color:#20553b;cursor:pointer}
.service-entry-card{padding:18px;background:#fff;border:1px solid #dce8df;border-radius:12px}.service-section-heading span{font-size:11px;letter-spacing:.12em;color:#508267}.service-section-heading h2{margin:5px 0}.service-section-heading p{color:#65776c}.service-entry-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:18px 0}.service-entry-grid .service-wide{grid-column:1/-1}.service-client-search{grid-column:1/-1;display:grid;grid-template-columns:1fr auto;align-items:end}.service-selected-client{grid-column:1/-1;margin:0;color:#53685d}.service-suggestions{grid-column:1/-1;display:grid;max-height:220px;overflow:auto;border:1px solid #dce8df;border-radius:8px}.service-suggestions button{display:grid;text-align:left;padding:10px;background:#fff;border:0;border-bottom:1px solid #edf1ed;cursor:pointer}.service-suggestions small{color:#65776c}.service-vital-alert{grid-column:1/-1;margin:0;padding:9px 11px;border-radius:8px;background:#fff6e8;color:#8b4d0c;font-size:12px}
.service-entry-card footer,.service-dialog footer{display:flex;justify-content:flex-end;gap:8px;margin-top:16px}.service-overlay{position:fixed;inset:0;z-index:1000;background:#10281c88;display:grid;place-items:center;padding:16px}.service-dialog{width:min(520px,100%);max-height:85vh;overflow:auto;padding:20px;background:#fff;border-radius:14px}.service-dialog header{display:flex;align-items:center;justify-content:space-between}.service-dialog header h2{margin:0}.service-dialog header button{border:0;background:transparent;font-size:25px;cursor:pointer}.service-dialog ul{padding-left:22px;max-height:45vh;overflow:auto}.service-dialog form{display:flex;align-items:end;gap:8px}.service-dialog form label{flex:1}.service-dialog form input{width:100%;box-sizing:border-box}.service-reschedule{display:grid;grid-template-columns:1fr 1fr;gap:10px}.service-reschedule label{display:grid;gap:5px}
@media(max-width:700px){.service-kpis{grid-template-columns:repeat(2,1fr)}.service-page{padding:8px 0 20px}.service-header{align-items:flex-start;flex-direction:column}.service-header h1{font-size:24px}.service-filters{align-items:stretch}.service-filters label,.service-search{width:100%}.service-filters input,.service-filters select{width:100%;box-sizing:border-box}.service-tabs button{padding:9px 11px}.service-entry-grid{grid-template-columns:1fr}.service-entry-grid .service-wide,.service-client-search{grid-column:auto}.service-dialog form{align-items:stretch;flex-direction:column}.service-reschedule{grid-template-columns:1fr}}
</style>
