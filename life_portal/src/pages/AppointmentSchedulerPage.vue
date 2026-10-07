<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { request } from '../api/http';
import { session } from '../lib/session';
import '../styles/appointment-scheduler.css';



const slots = ['07:00 AM','07:30 AM','08:00 AM','08:30 AM','09:00 AM','09:30 AM','10:00 AM','10:30 AM','11:00 AM','11:30 AM','12:00 PM','12:30 PM','01:00 PM','01:30 PM','02:00 PM','02:30 PM','03:00 PM','03:30 PM','04:00 PM','04:30 PM','05:00 PM','05:30 PM','06:00 PM','06:30 PM','07:00 PM'];
const excludedBranches = ['testing branch', 'head office'];
const branch = ref(''), date = ref(''), branches = ref([]), rooms = ref([]), appointments = ref([]);
const loading = ref(false), error = ref(''), notice = ref(''), createOpen = ref(false), detailOpen = ref(false), saving = ref(false);
const activeSlot = ref(null), appointmentDoc = ref(null), detailLoading = ref(false), detailsError = ref('');
const patientText = ref(''), patientInfo = ref(null), clientDetails = ref(''), patientSuggestions = ref([]), clientSearchLoading = ref(false);
const categoryText = ref(''), selectedCategory = ref(''), categorySuggestions = ref([]), categorySearchLoading = ref(false);
const concernText = ref(''), selectedConcern = ref(''), concernOpen = ref(false), therapyPlans = ref([]), plansLoading = ref(false);
const status = ref('Scheduled'), rescheduleDate = ref(''), rescheduleSlot = ref(''), availableSlots = ref([]), slotsLoading = ref(false);
const searches = { patient: null, category: null };
let boardController, plansController, detailController, rescheduleController, alive = true, clientTimer, categoryTimer;
const totalCount = computed(() => appointments.value.length);
const cancelledCount = computed(() => appointments.value.filter(a => /cancel/i.test(`${a.status||''} ${a.call_back_status||''}`)).length);
const availableCount = computed(() => Math.max(rooms.value.length * slots.length - appointments.value.length, 0));
function roomLabel(room) { let value=String(room||'').trim();const suffix=String(branch.value||'').trim();if(suffix&&value.toLowerCase().endsWith(suffix.toLowerCase()))value=value.slice(0,-suffix.length).replace(/\s*-\s*$/,'');return value.trim(); }
const apptsFor = (slot, room) => appointments.value.filter(a => a.appointment_time === slot && a.service_room === room);
const canBookAt = slot => date.value > today() || (date.value === today() && toMinutes(slot) > new Date().getHours()*60 + new Date().getMinutes());
const readyToCreate = computed(() => !!patientInfo.value && !!activeSlot.value?.room && !!selectedCategory.value && !!selectedConcern.value && !saving.value);
const statusClass = value => ({ cancel: 'cancel', cancelled: 'cancel', closed: 'closed', 're-scheduled': 'rescheduled', rescheduled: 'rescheduled', 're-confirm': 'reconfirm', 'not answering': 'notanswering' }[String(value||'').toLowerCase().trim()] || 'scheduled');
const cleanDate = value => value ? String(value).slice(0,10) : '';
const fmtTime = value => { if (!value) return ''; const [hh='0',mm='00'] = String(value).split(':'); const hour=Number(hh); return `${String(hour%12||12).padStart(2,'0')}:${mm} ${hour>=12?'PM':'AM'}`; };
function today() { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function toMinutes(value) { const [hm,ampm] = value.split(' '); let [hour,minute] = hm.split(':').map(Number); if(ampm==='PM'&&hour!==12)hour+=12;if(ampm==='AM'&&hour===12)hour=0;return hour*60+minute; }
function toERPTime(value) { const [hm,ampm]=value.trim().split(' ');let [hour,minute]=hm.split(':').map(Number);if(ampm==='PM'&&hour!==12)hour+=12;if(ampm==='AM'&&hour===12)hour=0;return `${hour}:${String(minute).padStart(2,'0')}:00`; }
async function call(method,args,signal) { return request(method,{args,signal,csrfToken:session.csrf_token}); }
function parseReport(response) { const msg=response.message||{}, keys=msg.keys||[];return (msg.values||[]).map(values=>Object.fromEntries(keys.map((key,i)=>[key,values[i]]))); }
function reportArgs(doctype,fields,filters,order,pageLength=500) { return {doctype,fields:JSON.stringify(fields.map(field=>`\`tab${doctype}\`.\`${field}\``)),filters:JSON.stringify(filters),order_by:`\`tab${doctype}\`.\`${order}\``,start:0,page_length:pageLength,view:'List',group_by:'',with_comment_count:1}; }
async function loadBranches() {
  error.value='';
  try {
    const response=await call('frappe.desk.reportview.get',reportArgs('Branch',['name','branch'],[],'modified desc',100));
    if(!alive)return;
    branches.value=[...new Set(parseReport(response).map(row=>row.branch||row.name).filter(name=>name&&!excludedBranches.includes(String(name).trim().toLowerCase())))];
    if(!branch.value)branch.value=branches.value[0]||'';
    if(branches.value.length)await loadBoard(); else error.value='No branches found.';
  } catch(e) { if(alive)error.value=e.message; }
}
async function loadBoard() {
  if(!branch.value||!date.value)return;
  boardController?.abort();const ctrl=new AbortController();boardController=ctrl;loading.value=true;error.value='';notice.value='';
  try {
    const filters=[['Patient Appointment','appointment_date','Between',[date.value,date.value]],['Patient Appointment','branch','=',branch.value]];
    const [apptRes,roomRes]=await Promise.all([
      call('frappe.desk.reportview.get',reportArgs('Patient Appointment',['name','status','service_room','branch','appointment_date','patient_name','appointment_time','call_back_status'],filters,'appointment_time asc',500),ctrl.signal),
      call('frappe.desk.reportview.get',reportArgs('Service Room',['name'],[],'idx asc',500),ctrl.signal),
    ]);
    if(!alive||boardController!==ctrl)return;
    appointments.value=parseReport(apptRes).map(row=>({...row,appointment_time:fmtTime(row.appointment_time),service_room:row.service_room||'No Room',patient:row.patient_name||'-'}));
    rooms.value=[...new Set(parseReport(roomRes).map(row=>row.name).filter(name=>name&&String(name).toLowerCase().includes(branch.value.toLowerCase())))].sort((a,b)=>roomLabel(a).localeCompare(roomLabel(b),undefined,{numeric:true,sensitivity:'base'}));
  } catch(e) { if(alive&&boardController===ctrl&&e.name!=='AbortError'){error.value=e.message;appointments.value=[];rooms.value=[];} }
  finally {if(alive&&boardController===ctrl)loading.value=false;}
}
function slotBookings(slot,room) { return apptsFor(slot,room); }
function openCreate(room,slot) {
  activeSlot.value={room,slot};patientText.value='';patientInfo.value=null;clientDetails.value='';patientSuggestions.value=[];selectedCategory.value='';categoryText.value='';categorySuggestions.value=[];concernText.value='';selectedConcern.value='';concernOpen.value=false;therapyPlans.value=[];createOpen.value=true;
}
async function searchLink(doctype,txt,filters={}) {
  const args={txt,doctype,reference_doctype:'Patient Appointment',page_length:20};
  if(doctype==='Patient'){args.ignore_user_permissions=1;args.filters=JSON.stringify({status:'Active'});}
  if(doctype==='Healthcare Service Unit')args.filters=JSON.stringify({});
  const response=await call('frappe.desk.search.search_link',args);
  return response.message||[];
}
function queueSearch(which) {
  const input=which==='patient'?patientText.value:categoryText.value;
  clearTimeout(which==='patient'?clientTimer:categoryTimer);
  const timer=setTimeout(async()=>{
    const controller=new AbortController();searches[which]?.abort();searches[which]=controller;
    if(which==='patient'){clientSearchLoading.value=true;try{patientSuggestions.value=await searchLink('Patient',input);}catch(e){if(alive)error.value=e.message;}finally{clientSearchLoading.value=false;}}
    else {categorySearchLoading.value=true;try{categorySuggestions.value=await searchLink('Healthcare Service Unit',input);}catch(e){if(alive)error.value=e.message;}finally{categorySearchLoading.value=false;}}
  },220);
  if(which==='patient')clientTimer=timer;else categoryTimer=timer;
}
async function selectPatient(option) {
  try {
    const response=await call('frappe.client.validate_link',{doctype:'Patient',docname:option.value,fields:JSON.stringify(['patient_name','inpatient_record','sex','mobile'])});
    patientInfo.value=response.message||null;
    if(!patientInfo.value)throw new Error('Unable to validate this client.');
    patientText.value=patientInfo.value.patient_name||patientInfo.value.name||option.value;
    clientDetails.value=[patientInfo.value.patient_name||patientInfo.value.name,patientInfo.value.sex,patientInfo.value.mobile].filter(Boolean).join(' | ');
    patientSuggestions.value=[];selectedCategory.value='';categoryText.value='';concernText.value='';selectedConcern.value='';await loadTherapyPlans(patientInfo.value.name||option.value);
  } catch(e){error.value=e.message;}
}
async function loadTherapyPlans(patientName) {
  plansController?.abort();const ctrl=new AbortController();plansController=ctrl;plansLoading.value=true;therapyPlans.value=[];
  try {
    const response=await call('frappe.desk.reportview.get',reportArgs('Therapy Plan',['name','patient','start_date','modified'],[['Therapy Plan','patient','=',patientName]],'modified desc',100),ctrl.signal);
    const rows=parseReport(response), plans=[];
    for(let i=0;i<rows.length;i+=8){
      const batch=await Promise.all(rows.slice(i,i+8).map(async row=>{try{return (await call('frappe.client.get',{doctype:'Therapy Plan',name:row.name},ctrl.signal)).message;}catch(e){if(e.name==='AbortError')throw e;return null;}}));
      batch.forEach((doc,index)=>{
        if(!doc)return;const planName=rows[i+index].name,planCategory=doc.service_unit||doc.category||'';
        let details=doc.therapy_plan_details||doc.therapy_plan_detail||doc.therapy_plan_table||doc.therapy_details||doc.plan_details||[];
        if(!details.length)for(const key of Object.keys(doc)){if(Array.isArray(doc[key])&&doc[key].some(row=>row&&(row.therapy_type||row.therapy||row.item||row.item_code||row.procedure_template||row.no_of_sessions||row.sessions||row.total_sessions))){details=doc[key];break;}}
        if(details.length){details.forEach(row=>{const therapy=row.therapy_type||'',unit=row.service_unit||planCategory,total=Number(row.no_of_sessions||0),done=Number(row.sessions_completed||0);if(therapy&&total>done)plans.push({plan:planName,therapy,unit,total,done,pending:total-done,start_date:rows[i+index].start_date});});}
        else {const therapy=doc.therapy_type||doc.therapy_type1||doc.concern||doc.item||'';if(therapy)plans.push({plan:planName,therapy,unit:doc.service_unit||doc.category||doc.healthcare_service_unit||'',total:1,done:0,pending:1,start_date:rows[i+index].start_date});}
      });
    }
    const seen=new Set();therapyPlans.value=plans.filter(p=>{const key=`${p.plan}||${p.therapy}||${p.unit}`;if(seen.has(key))return false;seen.add(key);return true;});
  } catch(e){if(e.name!=='AbortError')error.value=e.message;}
  finally{if(alive&&plansController===ctrl)plansLoading.value=false;}
}
const filteredPlans=computed(()=>therapyPlans.value.filter(plan=>{const unit=String(plan.unit||'').toLowerCase(),cat=selectedCategory.value.toLowerCase(),term=concernText.value.trim().toLowerCase();return(!cat||unit===cat||unit.includes(cat)||cat.includes(unit))&&(!term||`${plan.therapy} ${plan.unit} ${plan.plan}`.toLowerCase().includes(term));}));
async function selectCategory(option) {
  const response=await call('frappe.client.validate_link',{doctype:'Healthcare Service Unit',docname:option.value,fields:'[]'});
  selectedCategory.value=response.message?.name||option.value;categoryText.value=selectedCategory.value;categorySuggestions.value=[];concernText.value='';selectedConcern.value='';
}
function selectConcern(plan) { selectedCategory.value=plan.unit||selectedCategory.value;categoryText.value=selectedCategory.value;concernText.value=plan.therapy;selectedConcern.value=plan.therapy;concernOpen.value=false; }
function closeCreate() { if(!saving.value)createOpen.value=false; }
async function createAppointment() {
  if(!readyToCreate.value)return;
  saving.value=true;error.value='';
  const doc={docstatus:0,doctype:'Patient Appointment',name:`new-patient-appointment-${Date.now()}`,__islocal:1,__unsaved:1,naming_series:'HLC-APP-.YYYY.-',status:'',call_back_status:'Scheduled',appointment_for:'Practitioner',company:'Life Slimming And Cosmetic Pvt Ltd',add_video_conferencing:0,invoiced:0,appointment_based_on_check_in:0,reminded:0,appointment_type:'Session',department:'',service_unit:selectedCategory.value,patient:patientInfo.value.name,patient_name:patientInfo.value.patient_name||patientInfo.value.name,inpatient_record:patientInfo.value.inpatient_record||null,patient_sex:patientInfo.value.sex||'',custom_client_mobile_no:patientInfo.value.mobile||'',duration:null,service_room:activeSlot.value.room,concern:concernText.value,appointment_date:date.value,appointment_time:toERPTime(activeSlot.value.slot),branch:branch.value};
  try {
    const response=await call('frappe.desk.form.save.savedocs',{doc:JSON.stringify(doc),action:'Save'});
    const saved=response.docs?.[0]||response.message?.docs?.[0];if(!saved?.name)throw new Error('Appointment was not saved. Please retry.');
    createOpen.value=false;notice.value='Appointment created successfully.';await loadBoard();
  } catch(e){error.value=e.message||'Failed to create appointment.';}
  finally{saving.value=false;}
}
async function openDetails(name) {
  detailController?.abort();const ctrl=new AbortController();detailController=ctrl;detailOpen.value=true;detailLoading.value=true;detailsError.value='';appointmentDoc.value=null;status.value='Scheduled';rescheduleDate.value=today();rescheduleSlot.value='';availableSlots.value=[];
  try {const response=await call('frappe.client.get',{doctype:'Patient Appointment',name},ctrl.signal);if(alive&&detailController===ctrl){appointmentDoc.value=response.message;status.value=response.message?.call_back_status||'Scheduled';}}
  catch(e){if(alive&&e.name!=='AbortError')detailsError.value=e.message;}
  finally{if(alive&&detailController===ctrl)detailLoading.value=false;}
}
async function loadAvailableSlots() {
  if(!appointmentDoc.value||!rescheduleDate.value)return;
  rescheduleController?.abort();const ctrl=new AbortController();rescheduleController=ctrl;slotsLoading.value=true;
  try {
    const filters=[['Patient Appointment','appointment_date','Between',[rescheduleDate.value,rescheduleDate.value]],['Patient Appointment','branch','=',appointmentDoc.value.branch]];
    const response=await call('frappe.desk.reportview.get',reportArgs('Patient Appointment',['name','appointment_time','service_room'],filters,'appointment_time asc',500),ctrl.signal);
    const booked=parseReport(response).filter(row=>row.name!==appointmentDoc.value.name&&row.service_room===appointmentDoc.value.service_room).map(row=>fmtTime(row.appointment_time));
    availableSlots.value=slots.filter(slot=>!booked.includes(slot));
  } catch(e){if(e.name!=='AbortError')detailsError.value=e.message;}
  finally{if(alive&&rescheduleController===ctrl)slotsLoading.value=false;}
}
watch(status,value=>{if(value==='Re-Scheduled')loadAvailableSlots();});
async function saveAppointmentStatus() {
  if(!appointmentDoc.value)return;
  if(status.value==='Re-Scheduled'&&(!rescheduleDate.value||!rescheduleSlot.value)){detailsError.value='Choose a new date and available time slot.';return;}
  saving.value=true;detailsError.value='';
  const doc={...appointmentDoc.value,call_back_status:status.value,__unsaved:1};
  if(status.value==='Re-Scheduled'){doc.appointment_date=rescheduleDate.value;doc.custom_duration_time=doc.appointment_time;doc.appointment_time=toERPTime(rescheduleSlot.value);}
  try {await call('frappe.desk.form.save.savedocs',{doc:JSON.stringify(doc),action:'Save'});detailOpen.value=false;notice.value='Appointment status updated.';await loadBoard();}
  catch(e){detailsError.value=e.message||'Failed to update appointment status.';}
  finally{saving.value=false;}
}
function closeDetails(){if(!saving.value){detailOpen.value=false;appointmentDoc.value=null;}}
function dismissSuggestions(){setTimeout(()=>{patientSuggestions.value=[];categorySuggestions.value=[];concernOpen.value=false;},160);}
function onKey(event){if(event.key==='Escape'){closeCreate();closeDetails();}}
onMounted(()=>{date.value=today();window.addEventListener('keydown',onKey);loadBranches();});
onBeforeUnmount(()=>{alive=false;boardController?.abort();plansController?.abort();detailController?.abort();rescheduleController?.abort();Object.values(searches).forEach(c=>c?.abort());clearTimeout(clientTimer);clearTimeout(categoryTimer);window.removeEventListener('keydown',onKey);});
</script>

<template>
  <section class="appointment-scheduler">
    <header class="as-header"><div><span class="as-eyebrow">CLIENTS &amp; CLINICAL</span><h1>Client Appointment Scheduler</h1><p>View booked and available room slots branch-wise</p></div><form class="as-filters" @submit.prevent="loadBoard"><label>Branch<select v-model="branch" required @change="loadBoard"><option v-for="name in branches" :key="name" :value="name">{{ name }}</option></select></label><label>Date<input v-model="date" type="date" required @change="loadBoard" /></label><button :disabled="loading">{{ loading?'Loading…':'Refresh' }}</button></form></header>
    <p v-if="notice" class="as-notice" role="status">{{ notice }}</p><p v-if="error" class="as-error" role="alert">{{ error }}</p>
    <div class="as-summary"><article><span>Appointments</span><strong>{{ totalCount }}</strong></article><article><span>Available Slots</span><strong>{{ availableCount }}</strong></article><article><span>Rooms</span><strong>{{ rooms.length }}</strong></article><article><span>Cancelled</span><strong>{{ cancelledCount }}</strong></article></div>
    <div class="as-board-wrap" tabindex="0" role="region" aria-label="Daily appointments by service room"><table class="as-board"><thead><tr><th>⏱</th><th v-for="room in rooms" :key="room">{{ roomLabel(room) }}</th></tr></thead><tbody><tr v-if="loading"><td :colspan="rooms.length+1" class="as-empty">Loading appointments…</td></tr><tr v-else-if="!rooms.length"><td class="as-empty">No service rooms found for this branch.</td></tr><tr v-else v-for="slot in slots" :key="slot"><th class="as-time">{{ slot }}</th><td v-for="room in rooms" :key="room+'-'+slot" :class="{'as-empty-slot':!slotBookings(slot,room).length}"><template v-if="slotBookings(slot,room).length"><button v-for="appt in slotBookings(slot,room)" :key="appt.name" class="as-appointment" :class="statusClass(appt.call_back_status)" @click="openDetails(appt.name)"><strong>{{ appt.patient }}</strong><span>{{ appt.call_back_status||appt.status||'Scheduled' }}</span><small>{{ appt.name.split('-').slice(1).join('-') }}</small></button></template><button v-else-if="canBookAt(slot)" class="as-add" :aria-label="`Add appointment at ${slot} in ${roomLabel(room)}`" @click="openCreate(room,slot)">+</button><span v-else class="as-past">—</span></td></tr></tbody></table></div>
    <div v-if="createOpen" class="as-backdrop" @click.self="closeCreate"><section class="as-dialog" role="dialog" aria-modal="true" aria-labelledby="as-create-title"><header><h2 id="as-create-title">Add Appointment</h2><button aria-label="Close" :disabled="saving" @click="closeCreate">×</button></header><div class="as-form-grid">
      <label class="as-autocomplete">Client *<input v-model="patientText" autocomplete="off" placeholder="Search active client…" @input="queueSearch('patient')" @focus="queueSearch('patient')" @blur="dismissSuggestions"><div v-if="patientSuggestions.length||clientSearchLoading" class="as-suggestions"><p v-if="clientSearchLoading">Searching…</p><button v-for="item in patientSuggestions" :key="item.value" @mousedown.prevent="selectPatient(item)"><strong>{{ item.value }}</strong><small>{{ item.description }}</small></button></div></label>
      <label>Client Details<input :value="clientDetails" readonly /></label><label>Branch<input :value="branch" readonly /></label><label>Service Room<input :value="roomLabel(activeSlot?.room)" readonly /></label>
      <label class="as-autocomplete">Category *<input v-model="categoryText" autocomplete="off" placeholder="Search service unit" @input="queueSearch('category')" @focus="queueSearch('category')" @blur="dismissSuggestions"><div v-if="categorySuggestions.length||categorySearchLoading" class="as-suggestions"><p v-if="categorySearchLoading">Searching…</p><button v-for="item in categorySuggestions" :key="item.value" @mousedown.prevent="selectCategory(item)"><strong>{{ item.value }}</strong><small>{{ item.description }}</small></button></div></label>
      <label class="as-autocomplete">Concern *<input v-model="concernText" :disabled="!patientInfo" placeholder="Search pending concerns" @focus="concernOpen=true" @input="selectedConcern='';concernOpen=true" @blur="dismissSuggestions" /><div v-if="patientInfo&&concernOpen" class="as-suggestions"><p v-if="plansLoading">Loading pending therapy plans…</p><button v-for="plan in filteredPlans" :key="plan.plan+'-'+plan.therapy+'-'+plan.unit" @mousedown.prevent="selectConcern(plan)"><strong>{{ plan.therapy }}</strong><small>{{ plan.unit||'—' }} · Pending {{ plan.pending }} · Done {{ plan.done }}/{{ plan.total }} · Plan {{ plan.plan }}</small></button><p v-if="!plansLoading&&!filteredPlans.length">No pending concerns for this category.</p></div></label>
      <label>Date &amp; Time<input :value="`${date} · ${activeSlot?.slot||''}`" readonly /></label>
    </div><p v-if="!therapyPlans.length&&patientInfo&&!plansLoading" class="as-hint">No pending concerns were found for this client.</p><footer><button :disabled="saving" @click="closeCreate">Cancel</button><button class="as-primary" :disabled="!readyToCreate" @click="createAppointment">{{ saving?'Creating…':'Create Appointment' }}</button></footer></section></div>
    <div v-if="detailOpen" class="as-backdrop" @click.self="closeDetails"><section class="as-dialog" role="dialog" aria-modal="true" aria-labelledby="as-detail-title"><header><h2 id="as-detail-title">Appointment Details</h2><button aria-label="Close" :disabled="saving" @click="closeDetails">×</button></header><p v-if="detailLoading" role="status">Loading appointment details…</p><p v-if="detailsError" class="as-error" role="alert">{{ detailsError }}</p><template v-if="appointmentDoc"><div class="as-details"><div><span>Client</span><strong>{{ appointmentDoc.patient_name||appointmentDoc.patient||'—' }}</strong></div><label>Booking Status<select v-model="status"><option>Scheduled</option><option>Re-Confirm</option><option>Re-Scheduled</option><option>Not Answering</option><option>Closed</option><option>Cancel</option></select></label><div><span>Mobile</span><strong>{{ appointmentDoc.custom_client_mobile_no||'—' }}</strong></div><div><span>Gender</span><strong>{{ appointmentDoc.patient_sex||'—' }}</strong></div><div><span>Branch</span><strong>{{ appointmentDoc.branch||'—' }}</strong></div><div><span>Service Room</span><strong>{{ roomLabel(appointmentDoc.service_room)||'—' }}</strong></div><div><span>Service Unit</span><strong>{{ appointmentDoc.service_unit||'—' }}</strong></div><div><span>Concern</span><strong>{{ appointmentDoc.concern||'—' }}</strong></div><div><span>Date &amp; Time</span><strong>{{ cleanDate(appointmentDoc.appointment_date) }} · {{ fmtTime(appointmentDoc.appointment_time) }}</strong></div></div><div v-if="status==='Re-Scheduled'" class="as-reschedule"><label>New Date<input v-model="rescheduleDate" type="date" :min="today()" @change="loadAvailableSlots" /></label><label>Available Slots<select v-model="rescheduleSlot" :disabled="slotsLoading"><option value="">{{ slotsLoading?'Loading…':'Select slot' }}</option><option v-for="slot in availableSlots" :key="slot">{{ slot }}</option></select></label></div></template><footer><button :disabled="saving" @click="closeDetails">Close</button><button class="as-primary" :disabled="saving||detailLoading||!appointmentDoc" @click="saveAppointmentStatus">{{ saving?'Updating…':'Update Status' }}</button></footer></section></div>
  </section>
</template>
