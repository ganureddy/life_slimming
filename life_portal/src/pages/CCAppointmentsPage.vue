<script setup>
import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import { request } from '../api/http';
import { session } from '../lib/session';
import { createRequestId } from '../api/convox';
const route = useRoute();
const bookingDialog=ref(null);
const branches=ref([]), staff=ref([]), leads=ref([]), branch=ref(''), date=ref(''), today=ref(''), timezone=ref('');
const resource=ref(''), role=ref(''), agent=ref(''), lead=ref(typeof route.query.lead === 'string' ? route.query.lead : ''), search=ref(''), duration=ref(45);
const schedules=ref([]), selected=ref(null), loading=ref(false), saving=ref(false), error=ref(''), success=ref('');
let generation=0, searchGeneration=0, timer, requestId=createRequestId(), mounted=true;
const designations=computed(()=>[...new Set(staff.value.map(s=>s.designation||s.role))].sort());
const filteredStaff=computed(()=>staff.value.filter(x=>!role.value||(x.designation||x.role)===role.value));
const visible=computed(()=>schedules.value.filter(x=>!role.value||(x.staff.designation||x.staff.role)===role.value));
const agents=computed(()=>[...new Map(schedules.value.flatMap(x=>x.events.filter(e=>e.agent).map(e=>[e.agent,{id:e.agent,name:e.agent_name||e.agent}]))).values()]);
const selectedLead=computed(()=>leads.value.find(x=>x.name===lead.value));
const availableCount=computed(()=>visible.value.reduce((total,s)=>total+s.slots.filter(slot=>slot.available).length,0));
const agenda=computed(()=>visible.value.flatMap(s=>s.events.filter(e=>!agent.value||e.agent===agent.value).map(e=>({...e,staff:s.staff.name,role:s.staff.designation||s.staff.role}))).sort((a,b)=>a.start.localeCompare(b.start)));
const time=value=>{const [h,m]=String(value).slice(11,16).split(':');return `${Number(h)%12||12}:${m} ${Number(h)<12?'AM':'PM'}`;};
const gridRows=computed(()=>Array.from({length:40},(_,i)=>{
 const start=`${date.value} ${String(10+Math.floor(i/4)).padStart(2,'0')}:${String(i%4*15).padStart(2,'0')}:00`;
 const end=i===39?`${date.value} 20:00:00`:`${date.value} ${String(10+Math.floor((i+1)/4)).padStart(2,'0')}:${String((i+1)%4*15).padStart(2,'0')}:00`;
 return {start,cells:visible.value.map(schedule=>({staff:schedule.staff,slot:schedule.slots.find(slot=>slot.start===start),events:schedule.events.filter(event=>event.start<end&&event.end>start)}))};
}));
const bookedCount=computed(()=>visible.value.reduce((count,s)=>count+s.events.length,0));
function closeBooking(){if(!saving.value){bookingDialog.value?.close();selected.value=null;}}
watch(selected,value=>{if(!value)bookingDialog.value?.close();});
async function call(action,args={}) { return (await request('life_slimming.api.cc_appointments.'+action,{args,csrfToken:session.csrf_token})).message; }
async function init(){try{const d=await call('bootstrap',{selected_lead:lead.value});if(!mounted)return;branches.value=d.branches;leads.value=d.leads;today.value=d.today;date.value=d.today;timezone.value=d.timezone;if(d.branches.length)branch.value=d.branches[0];}catch(e){error.value=e.message;}}
async function refresh(){
 const gen=++generation; selected.value=null;requestId=createRequestId();schedules.value=[];error.value='';
 if(!branch.value||!date.value){loading.value=false;return;}loading.value=true;
 try{const [meta,cal]=await Promise.all([call('bootstrap',{branch:branch.value}),call('calendar',{branch:branch.value,date:date.value,resource:resource.value,duration:duration.value})]);if(gen!==generation||!mounted)return;staff.value=meta.staff;schedules.value=cal.schedules;}
 catch(e){if(gen===generation)error.value=e.message;}finally{if(gen===generation)loading.value=false;}
}
async function findLeads(){const gen=++searchGeneration;try{const d=await call('bootstrap',{query:search.value,selected_lead:lead.value});if(gen===searchGeneration&&mounted)leads.value=d.leads;}catch(e){error.value=e.message;}}
async function choose(person,slot){if(!slot.available||saving.value)return;selected.value={staff:person,slot};requestId=createRequestId();error.value='';success.value='';await nextTick();bookingDialog.value?.showModal();}
async function book(){
 if(!selected.value||!lead.value)return; saving.value=true;error.value='';success.value='';
 try{const d=await call('book',{lead:lead.value,branch:branch.value,resource:selected.value.staff.id,start:selected.value.slot.start,duration:duration.value,request_id:requestId});success.value='Appointment '+d.name+' booked successfully.';await refresh();}
 catch(e){error.value=e.message; /* Keep the same request ID if the response is uncertain. */}
 finally{saving.value=false;}
}
watch(branch,()=>{resource.value='';role.value='';staff.value=[];});
watch([branch,date,resource,duration],refresh);
watch(role,()=>{resource.value='';selected.value=null;});
watch(lead,()=>{requestId=createRequestId();});
watch(search,()=>{clearTimeout(timer);timer=setTimeout(findLeads,250);});
onMounted(init);
onUnmounted(()=>{mounted=false;generation++;searchGeneration++;clearTimeout(timer);});
</script>
<template>
<section class="cc-scheduler" :aria-busy="loading||saving">
 <header><div><RouterLink :to="{name:'leads'}">← CC Dashboard</RouterLink><h1>CC Appointment Scheduler</h1><p>10:00 AM–8:00 PM · Minimum 45 minutes · {{ timezone }}</p></div><button :disabled="loading||saving" @click="refresh">Refresh calendar</button></header>
 <p v-if="error" role="alert" class="error">{{ error }}</p><p v-if="success" role="status" class="success">{{ success }}</p>
 <fieldset :disabled="saving" class="filters"><legend>Branch and consultation staff</legend>
  <label>Branch<select v-model="branch"><option disabled value="">Select branch</option><option v-for="b in branches" :key="b">{{ b }}</option></select></label>
  <label>Date<input v-model="date" type="date" :min="today"></label>
  <label>Session duration<select v-model="duration"><option :value="45">45 minutes</option><option :value="60">60 minutes</option></select></label>
  <label>Designation<select v-model="role"><option value="">All eligible designations</option><option v-for="d in designations" :key="d">{{d}}</option></select></label>
  <label>Staff member<select v-model="resource"><option value="">All staff</option><option v-for="s in filteredStaff" :key="s.id" :value="s.id">{{s.name}} · {{s.designation||s.role}}</option></select></label>
 </fieldset>
 <div class="summary"><div><span>Booked appointments</span><strong>{{bookedCount}}</strong></div><div><span>Available slots</span><strong>{{availableCount}}</strong></div><div><span>Consultation staff</span><strong>{{visible.length}}</strong></div></div>
 <p v-if="loading" role="status">Checking staff calendars…</p>
 <p v-else-if="branch&&!visible.length">No active consultation staff are mapped to this branch and role. Ask the branch administrator to update the staff mapping.</p>
 <div class="legend"><span>+ Available</span><span>— Unavailable</span><span>Availability includes this staff member’s bookings at other branches.</span></div>
 <div v-if="visible.length" class="calendar-wrap" tabindex="0" aria-label="Consultation staff calendar">
  <table class="calendar-grid"><thead><tr><th scope="col" class="time-cell">Time</th><th v-for="schedule in visible" :key="schedule.staff.id" scope="col">{{schedule.staff.name}}<small>{{schedule.staff.designation||schedule.staff.role}}</small></th></tr></thead>
   <tbody><tr v-for="row in gridRows" :key="row.start"><th scope="row" class="time-cell">{{time(row.start)}}</th>
    <td v-for="cell in row.cells" :key="cell.staff.id" :class="{'occupied':cell.events.length}">
     <div v-for="(event,i) in cell.events" :key="event.name||i" class="event-card"><strong>{{event.client||'Booked'}}</strong><small>{{time(event.start)}}–{{time(event.end)}}</small><small v-if="event.agent_name">{{event.agent_name}}</small><small v-if="event.branch!==branch">{{event.branch}}</small></div>
     <button v-if="!cell.events.length&&cell.slot?.available" class="add-slot" :disabled="saving" :aria-label="'Book '+cell.staff.name+' at '+time(row.start)" :title="'Book '+duration+' minutes with '+cell.staff.name" @click="choose(cell.staff,cell.slot)">+</button>
     <span v-else-if="!cell.events.length" class="unavailable" :title="cell.slot?.reason||'Session would end after closing'">—</span>
    </td>
   </tr></tbody>
  </table>
 </div>
 <dialog ref="bookingDialog" class="booking-dialog" aria-labelledby="booking-title" @cancel.prevent="closeBooking">
 <form v-if="selected" class="booking" @submit.prevent="book">
  <header><h2 id="booking-title">Book appointment</h2><button type="button" :disabled="saving" aria-label="Close booking" @click="closeBooking">×</button></header>
  <p v-if="error" role="alert" class="error">{{error}}</p>
  <p>{{branch}} · {{selected.staff.name}} · {{date}} · {{time(selected.slot.start)}}–{{time(selected.slot.end)}}</p>
  <fieldset :disabled="saving"><label>Find assigned lead<input v-model="search" placeholder="Name, mobile number or Lead ID"></label>
  <label>Lead<select v-model="lead" required><option value="">Select lead</option><option v-if="lead&&!leads.some(l=>l.name===lead)" :value="lead">{{lead}}</option><option v-for="l in leads" :key="l.name" :value="l.name">{{l.lead_name}} · {{l.mobile_no}} · {{l.name}}</option></select></label>
  <label>Lead owner / CC agent<input :value="selectedLead?.lead_owner_name || selectedLead?.lead_owner || 'Unassigned'" readonly></label>
  <label>Selected manager / consultation staff<input :value="selected.staff.name + ' · ' + (selected.staff.designation || selected.staff.role)" readonly></label>
  <p>Booked by: {{session.full_name}}. Availability is checked again when saving.</p><button type="submit" :disabled="saving||!lead">{{saving?'Booking…':'Confirm appointment'}}</button><button type="button" :disabled="saving" @click="closeBooking">Cancel</button></fieldset>
 </form>
 </dialog>
 <section class="agenda"><header><h2>Booked appointments</h2><label>Lead owner / CC agent<select v-model="agent"><option value="">All visible agents</option><option v-for="a in agents" :key="a.id" :value="a.id">{{a.name}}</option></select></label></header><p>Agent filtering affects this list only; every occupied staff slot stays blocked.</p><div class="table-wrap"><table><thead><tr><th>Time</th><th>Branch</th><th>Staff / role</th><th>Lead / client</th><th>Lead owner / CC agent</th></tr></thead><tbody><tr v-for="(e,i) in agenda" :key="e.name||i"><td>{{time(e.start)}}–{{time(e.end)}}</td><td>{{e.branch}}</td><td>{{e.staff}} · {{e.role}}</td><td>{{e.client}} {{e.lead}}</td><td>{{e.agent_name||e.agent||'Reserved'}}</td></tr><tr v-if="!agenda.length"><td colspan="5">No appointments to show for this selection.</td></tr></tbody></table></div></section>
</section>
</template>
<style scoped>
.summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.summary>div{background:white;border:1px solid #d9e4db;border-radius:12px;padding:16px}.summary span,.summary strong{display:block}.summary span{font-size:12px}.summary strong{font-size:26px;margin-top:8px}.cc-scheduler{width:100%;min-width:0;margin:auto;padding:16px;box-sizing:border-box;background:#f0f4f8;color:#214638}.cc-scheduler header{display:flex;justify-content:space-between;gap:18px;align-items:center;flex-wrap:wrap}h1{margin:10px 0;font-size:28px}h2{font-size:19px;margin:0 0 16px}h2 small{font-size:13px;color:#64796a;margin-left:10px}p{color:#657369}.filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}fieldset,.staff-calendar,.booking,.agenda{border:1px solid #d9e4db;padding:20px;border-radius:12px;background:white;margin:20px 0}label{display:flex;flex-direction:column;gap:8px;font-size:13px}input,select,button{font:inherit;padding:10px;border:1px solid #c8d8ce;border-radius:7px;background:white;color:#214638;max-width:100%}button{cursor:pointer}button:disabled{cursor:not-allowed;background:#edf0ee;color:#78837d}.slots{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px}.slots button:not(:disabled){background:#f1faf3;border-color:#a5cbb0}.slots button.chosen{background:#1d603e;color:white}.slots strong,.slots small{display:block}.slots small{margin-top:5px}.legend{display:flex;gap:20px;flex-wrap:wrap;font-size:12px;color:#597161}.booking{border:2px solid #27734b}.booking fieldset{border:0;padding:0;display:grid;gap:14px}.error{background:#fff0ef;color:#a22722;padding:14px;border-radius:8px}.success{background:#e9f8ec;color:#22603b;padding:14px;border-radius:8px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}td,th{padding:12px;border-bottom:1px solid #e4ece5}a{color:#216345}@media(max-width:600px){fieldset,.staff-calendar,.booking,.agenda{padding:14px}.slots{grid-template-columns:repeat(2,minmax(0,1fr))}}

.summary{margin-bottom:18px}.summary>div{border-top:3px solid #16a34a;box-shadow:0 2px 5px #172b4d0a}.summary>div:nth-child(2){border-top-color:#2563eb}.summary>div:nth-child(3){border-top-color:#7c3aed}.summary span{font-weight:600;text-transform:uppercase;color:#657369}.summary strong{color:#172b4d}.filters{align-items:end}.calendar-wrap{max-height:640px;overflow:auto;border:1px solid #e1e7e5;border-radius:14px;background:white;margin-top:16px}.calendar-grid{border-collapse:separate;border-spacing:0;table-layout:fixed;min-width:100%}.calendar-grid th,.calendar-grid td{box-sizing:border-box;width:200px;min-width:200px;border-bottom:1px solid #edf1f4;border-right:1px solid #f0f4f8}.calendar-grid thead th{position:sticky;top:0;z-index:2;background:#f8fafc;color:#42566b;text-transform:uppercase;font-size:12px;height:58px}.calendar-grid th small{display:block;font-weight:400;text-transform:none;margin-top:4px}.calendar-grid .time-cell{position:sticky;left:0;width:112px;min-width:112px;background:#f0fdf4;color:#278052;text-align:center;white-space:nowrap;z-index:1;font-weight:500}.calendar-grid thead .time-cell{z-index:3}.calendar-grid td{height:66px;text-align:center;padding:5px 8px;background:#fafbfd}.calendar-grid td:hover{background:#f0fdf4}.calendar-grid td.occupied{background:white}.add-slot{border:1.5px dashed #86efac;border-radius:50%;width:32px;height:32px;padding:0;color:#16a34a;font-size:24px;line-height:28px;background:white}.add-slot:hover{background:#dcfce7}.unavailable{color:#a3afbd}.event-card{text-align:left;background:#eff6ff;border-left:3px solid #3b82f6;border-radius:6px;padding:7px;color:#294d79;overflow-wrap:anywhere}.event-card strong,.event-card small{display:block}.event-card small{font-size:11px;margin-top:3px}.booking-dialog{width:min(600px,calc(100vw - 32px));max-height:85vh;padding:0;border:0;border-radius:14px;color:#214638}.booking-dialog::backdrop{background:#112c2466}.booking-dialog .booking{border:0;margin:0;padding:24px}.booking header{margin-bottom:14px}.booking header h2{margin:0}.booking button[type=submit]{background:#15803d;color:white}.legend{margin:14px 0}.cc-scheduler>header button{background:#15803d;color:white}@media(max-width:600px){.cc-scheduler{padding:8px}.summary{gap:6px}.summary>div{padding:10px}.summary span{font-size:10px}.calendar-grid th,.calendar-grid td{width:170px;min-width:170px}.calendar-grid .time-cell{width:100px;min-width:100px}.booking-dialog .booking{padding:16px}}
</style>
