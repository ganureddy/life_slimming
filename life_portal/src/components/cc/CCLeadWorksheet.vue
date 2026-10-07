<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';
import reference from '../../data/cc-reference.json';
import { ccCall } from '../../api/cc';
import { request } from '../../api/http';
import { session } from '../../lib/session';
import { maskPhone } from '../../lib/cc';
import { useRouter } from 'vue-router';

const props = defineProps({ lead: { type: Object, required: true }, manager: Boolean, busy: Boolean, error: String, notice: String });
const router = useRouter();
const draft = defineModel('draft', { required: true });
const followup = defineModel('followup', { required: true });
const categories = defineModel('categories', { required: true });
const interests = defineModel('interests', { required: true });
const emit = defineEmits(['save', 'back', 'start-call', 'stop-call', 'history']);
const result = ref(''), choice = ref(''), issueSearch = ref(''), issues = ref([]), alias = ref('');
const phones = ref([]), primary = ref(''), savedPhones = ref(new Set()), revealed = ref(-1), validation = ref('');
const sources=ref([]),contactMatches=ref({}),previousOwner=ref('Checking history…'),assignment=ref('Checking history…');
const assessment = ref({}), medical = ref([]), historyDialog = ref(null);
const leadHistory = ref([]), leadHistoryLoading = ref(false), leadHistoryError = ref('');
const toast = ref(null), clockNow = ref(Date.now()); let toastTimer, clockTimer;
const profilePattern = /\[CC_PROFILE_V1\]([\s\S]*?)\[\/CC_PROFILE_V1\]/;
const digits = value => String(value || '').replace(/\D/g, '').slice(-10);
function profileOf(lead) { try { return JSON.parse(String(lead.custom_remarks || '').match(profilePattern)?.[1] || '{}'); } catch { return {}; } }
const savedProfile = computed(() => profileOf(props.lead));
const progressSteps = ['Source','Personal','Location','Treatment','Assessment','Status','Action'];
const stepComplete = computed(() => [
  Boolean(draft.value.source),
  Boolean(draft.value.first_name && phones.value.some(number => number.length === 10)),
  Boolean(draft.value.city && draft.value.branch),
  Boolean(categories.value.length),
  Boolean(Object.values(assessment.value).some(value => value !== '' && value != null)),
  Boolean(result.value && choice.value),
  Boolean(followup.value.conclusion || followup.value.next_followup),
]);
const progress = computed(() => Math.round(stepComplete.value.filter(Boolean).length / progressSteps.length * 100));
const clientName = computed(() => (draft.value.first_name || props.lead.lead_name || '') + (alias.value ? ` (${alias.value})` : ''));
const age = computed(() => {
  const raw=String(props.lead.creation||props.lead.custom_posting_date||'').trim();
  let time;
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) time=new Date(raw.includes('T')?raw:raw.replace(' ','T')+'+05:30');
  else { const match=/^(\d{2})-(\d{2})-(\d{4})/.exec(raw); if(match)time=new Date(Number(match[3]),Number(match[2])-1,Number(match[1])); }
  if(!time||!Number.isFinite(time.getTime()))return '—';
  return `${Math.max(0,Math.floor((clockNow.value-time.getTime())/86400000))}d`;
});
const calls = computed(() => savedProfile.value.workflow?.attempt_count ?? props.lead.custom_call_count ?? 0);
const savedStatus = computed(() => (reference.WF.RETRY.includes(props.lead.custom_cc_sub_status) ? props.lead.workflow_hint?.prior_connected : '') || props.lead.custom_cc_sub_status || 'Lead');
const wf = reference.WF;
const phase = computed(() => {
  const status = savedStatus.value, appt = props.lead.custom_appointment_status;
  if (status === 'Walked In & Booked' || appt === 'Visited Booked') return 'won';
  if (status === 'Do Not Contact') return 'dnc';
  if (status === 'Existing Client') return 'existing';
  if (wf.LOST.includes(status)) return 'lost';
  if ([...wf.INVALID, ...wf.BADNUM].includes(status)) return 'invalid';
  if (status === 'Walked In: Not Booked' || appt === 'Visited Not Booked') return 'walkin';
  if (['Appointment Booked', wf.APPT_NR].includes(status)) return 'booked';
  if (wf.ACTIVE.includes(status)) return 'active';
  return 'new';
});
const phaseLabels = { new: 'Untouched / not yet connected', active: 'Follow-up · active discussion', booked: 'Appointment booked · awaiting visit', walkin: 'Walked in · not booked (post-visit loop)', won: 'Success - Client Booked ✓', existing: 'Existing client · protected', lost: 'Lost · locked', invalid: 'Invalid · locked', dnc: 'Do Not Contact · permanent lock' };
const locked = computed(() => ['won','existing','lost','invalid','dnc'].includes(phase.value));
const canReopen = computed(() => locked.value && props.manager && !['won','dnc'].includes(phase.value));
const groups = computed(() => {
  if (locked.value) return canReopen.value && result.value === 'Connected' ? [['Manager reopen · follow-up','fu',wf.ACTIVE],['Manager reopen · book appointment','ok',['Appointment Booked']]] : [];
  if (result.value === 'Not Connected') {
    if (phase.value === 'booked') return [['Appointment call outcome','fu',[wf.APPT_NR,...wf.RETRY]]];
    if (phase.value === 'walkin') return [['Retry · stays Walked In: Not Booked','fu',wf.RETRY]];
    if (phase.value === 'active') return [['Retry · pipeline stays','fu',wf.RETRY]];
    return [['Retry · pipeline stays','fu',wf.RETRY],['Bad number · INVALID (locks)','inv',wf.BADNUM]];
  }
  if (result.value !== 'Connected') return [];
  if (phase.value === 'booked') return [['Appointment · confirm / reschedule','ok',['Appointment Booked']],['Clinic visit outcome','win',wf.VISIT],['Postpone','fu',['Callback: Scheduled','Out Station']],['Lost · locks record','lost',wf.LOST]];
  if (phase.value === 'walkin') return [['Still deciding · stays in clinic loop','fu',['Walked In: Not Booked']],['Re-consultation','ok',['Appointment Booked']],['Closed won','win',['Walked In & Booked']],['Lost · locks record','lost',wf.LOST]];
  return [['Follow-up · active discussion','fu',wf.ACTIVE],['Success','ok',wf.SUCCESS],['Lost · locks record','lost',wf.LOST],['Invalid · locks record','inv',wf.INVALID]];
});
const canEditSource = computed(() => session.user === 'Administrator' || session.roles.some(role => ['System Manager','Call Center Export'].includes(role)));
const needsDate = computed(() => result.value === 'Connected' && [...wf.ACTIVE, 'Walked In: Not Booked'].includes(choice.value));
const matches = computed(() => issueSearch.value.trim() ? reference.OCT_MASTER.filter(row => [row[1], row[2], row[3], row[6]].join(' ').toLowerCase().includes(issueSearch.value.trim().toLowerCase()) && !issues.value.some(selected => selected[1] === row[1])).slice(0,12) : []);
const conditions = computed(() => [...new Map(categories.value.flatMap(category => reference.MED_CONDITIONS[category] || reference.MED_CONDITIONS.Slimming || []).map(condition => [condition.name, condition])).values()]);
const assessmentSections = computed(() => {
  const sections = [];
  if (categories.value.some(x => ['Slimming','Life Rise'].includes(x))) sections.push({ title:'Slimming / Weight Assessment', fields:[{key:'weight',label:'Current Weight (kg)',type:'number'},{key:'height',label:'Height (cm)',type:'number'},{key:'height_ft',label:'Height (ft/in)',placeholder:'e.g. 5.6'},{key:'custom_target_weight',label:'Target Weight (kg)',type:'number'},{key:'custom_bmi',label:'BMI (auto)',readonly:true},{key:'custom_previous_attempts',label:'Previous Weight-loss Attempts',placeholder:'Diet, gym, other clinics...'}] });
  if (categories.value.includes('Hair')) sections.push({ title:'Hair Assessment', fields:[{key:'hair_duration',label:'Hair Problem Duration',options:['Less than 6 months','6-12 months','1-3 years','More than 3 years']},{key:'hair_stage',label:'Baldness Stage',options:['Early thinning','Receding hairline','Crown balding','Advanced baldness']},{key:'hair_family',label:'Family History of Baldness',options:['Yes','No']}] });
  if (categories.value.includes('HT (Hair Transplant)')) sections.push({ title:'Hair Transplant Assessment', fields:[{key:'ht_donor',label:'Donor Area Density',options:['Good','Moderate','Poor']},{key:'ht_method',label:'Preferred Method',options:['FUE','DHI','FUT','Beard Transplant']},{key:'ht_budget',label:'Budget Discussed?',options:['Yes','Needs EMI info']}] });
  for (const category of categories.value.filter(x => ['Skin / Dermat','Laser','Aesthetics'].includes(x))) sections.push({title:`${category} Assessment`,fields:[{key:'skin_duration',label:'Skin Concern Duration',options:['Recent','Few months','Chronic (years)']},{key:'skin_previous',label:'Previous Treatments Taken'},{key:'skin_sensitivity',label:'Skin Sensitivity / Allergy',options:['None known','Sensitive skin','Known allergies']}]});
  return sections;
});
watch(() => props.lead, lead => {
  const profile = profileOf(lead);
  alias.value = profile.alias || '';
  issues.value = (profile.issues || []).map(key => reference.OCT_MASTER.find(row => row[1] === key)).filter(Boolean);
  phones.value = [...new Set((profile.phones?.length ? profile.phones : [lead.mobile_no,lead.phone]).map(digits).filter(Boolean))].slice(0,4);
  if (!phones.value.length) phones.value = [''];
  savedPhones.value = new Set(phones.value.filter(Boolean));
  primary.value = digits(profile.primary || phones.value[0]);
  assessment.value = profile.assessment || {};
  medical.value = profile.medical_conditions || [];
  result.value = ''; choice.value = ''; validation.value = '';
}, { immediate: true });
watch(() => [draft.value.weight,draft.value.height], ([weight,height]) => { draft.value.custom_bmi = Number(weight) > 0 && Number(height) > 0 ? (Number(weight) / (Number(height)/100)**2).toFixed(1) : ''; });
async function showHistory(){historyDialog.value?.showModal();if(leadHistory.value.length||leadHistoryLoading.value)return;leadHistoryLoading.value=true;leadHistoryError.value='';try{const rows=await ccCall('cc_get_lead_history',{lead:props.lead.name});leadHistory.value=Array.isArray(rows)?rows:rows?.rows||[]}catch(error){leadHistoryError.value=error.message||'Could not load lead history.'}finally{leadHistoryLoading.value=false}}
function dismissToast(){toast.value=null;clearTimeout(toastTimer)}
function showToast(message,type='success'){toast.value={message,type};clearTimeout(toastTimer);toastTimer=setTimeout(()=>dismissToast(),10000)}
onBeforeUnmount(()=>{clearTimeout(toastTimer);clearInterval(clockTimer);});
function leadHistoryChanges(event){try{return (JSON.parse(event.data||'{}').changed||[]).filter(change=>['status','custom_cc_stage','custom_cc_sub_status','lead_owner','custom_appointment_status','branch','lead_assign_to_branch','custom_next_followup_date','custom_conclusion_remark','source'].includes(change[0]))}catch{return []}}
const historyLabels={status:'Status',custom_cc_stage:'CC Stage',custom_cc_sub_status:'Sub-status',lead_owner:'Lead Owner',custom_appointment_status:'Appointment',branch:'Branch',lead_assign_to_branch:'Assigned Branch',custom_next_followup_date:'Next Follow-up',custom_conclusion_remark:'Conclusion',source:'Source'};
function openConvoxHistory(){router.push({name:'convox-history',params:{leadId:props.lead.name}})}
function jumpToStep(index) { document.getElementById(['ffsec-1','ffsec-2','ffsec-1','ffsec-3','ffsec-4','ff-status-area','wf-panel'][index])?.scrollIntoView({behavior:'smooth',block:'center'}); }
function chooseConnection(value) { result.value = value; choice.value = ''; validation.value = ''; }
function chooseOutcome(value) {
  choice.value = value;
  if (result.value === 'Not Connected' && value !== wf.APPT_NR && !wf.BADNUM.includes(value)) {
    followup.value.sub_status = props.lead.custom_cc_sub_status || ''; 
    followup.value.stage = props.lead.custom_cc_stage || 'UNTOUCHED';
  } else {
    followup.value.sub_status = value;
    followup.value.stage = [...wf.BADNUM,...wf.INVALID].includes(value) ? 'INVALID' : wf.LOST.includes(value) ? 'LOST' : ['Appointment Booked','Existing Client','Walked In & Booked'].includes(value) ? 'SUCCESS' : 'FOLLOW-UP';
  }
}
function addIssue(row) { issues.value.push(row); issueSearch.value = ''; syncIssues(); }
function removeIssue(index) { issues.value.splice(index,1); syncIssues(); }
function syncIssues() {
  const category = value => value === 'Skin (Dermatology)' ? 'Skin / Dermat' : value === 'HT' ? 'HT (Hair Transplant)' : value;
  draft.value.enquired_for=issues.value.map(row=>row[1]).join('; ');
  categories.value = [...new Set(issues.value.map(row => category(row[3])))];
  interests.value = [...new Set(issues.value.map(row => row[2]))];
}
function addPhone(index) { if (phones.value.length >= 4 || phones.value.some(number => !number)) return; phones.value.splice(index+1,0,''); }
function removePhone(index) { const number=phones.value[index]; if (number && savedPhones.value.has(number) && !props.manager) return; phones.value.splice(index,1); if (!phones.value.length) phones.value=['']; if (primary.value===number) primary.value=phones.value.find(Boolean)||''; }
function setPhone(index,event) { phones.value[index] = event.target.value.replace(/\D/g,'').slice(0,10); event.target.value=phones.value[index];if(phones.value[index].length===10)lookupPhone(phones.value[index]); }
async function lookupPhone(phone){try{const data=await ccCall('cc_phone_lookup',{phone,lead:props.lead.name});contactMatches.value={...contactMatches.value,[phone]:data.matches||[]}}catch{}}
onMounted(async()=>{clockTimer=setInterval(()=>clockNow.value=Date.now(),60000);try{const data=await request('frappe.client.get_list',{args:{doctype:'Lead Source',fields:['name'],limit_page_length:500},csrfToken:session.csrf_token});sources.value=data.message||[]}catch{}});
watch(()=>props.lead.name,async lead=>{previousOwner.value='Checking history…';assignment.value='Checking history…';try{const rows=await ccCall('cc_get_lead_history',{lead});if(props.lead.name!==lead)return;let prior='';for(const row of (Array.isArray(rows)?rows:[]).sort((a,b)=>String(b.creation).localeCompare(String(a.creation)))){try{const change=(JSON.parse(row.data||'{}').changed||[]).find(change=>change[0]==='lead_owner'&&change[1]&&change[1]!==change[2]);if(change){prior=change[1];break}}catch{}}previousOwner.value=prior||'No prior owner recorded';assignment.value=prior?'Reassigned':'No reassignment recorded'}catch{previousOwner.value='History unavailable';assignment.value='Not verified'}}, {immediate:true});
async function copyPhone(number) { try { await navigator.clipboard.writeText(number); } catch { validation.value = 'Could not copy the phone number.'; } }
function submit(checkOnly=false) {
  validation.value = '';
  if (locked.value && !canReopen.value) validation.value = 'This lead is locked. Its status cannot be changed.';
  else if (!result.value) validation.value = 'Select whether this call connected.';
  else if (!choice.value) validation.value = 'Select the call outcome.';
  else if (!phones.value.filter(Boolean).length || phones.value.some(number=>number && number.length!==10)) validation.value = 'Each phone number must be exactly 10 digits.';
  else if (new Set(phones.value.filter(Boolean)).size !== phones.value.filter(Boolean).length) validation.value = 'Duplicate phone number. Each contact must be unique.';
  else if (needsDate.value && !followup.value.next_followup) validation.value = 'Choose the next follow-up date and time.';
  else if ([...wf.LOST,...wf.INVALID].includes(choice.value) && followup.value.conclusion.trim().length<5) validation.value = 'Give the specific reason in Conclusion Remark before closing (at least 5 characters).';
  else if (['Price Negotiation','Walked In: Not Booked'].includes(choice.value) && followup.value.remarks.trim().length<5) validation.value='Write the pricing discussion or counsellor reason in Agent Notes.';
  else if (canReopen.value && followup.value.remarks.trim().length<10) validation.value='Manager reopen requires an audit reason of at least 10 characters in Agent Notes.';
  if (validation.value) { showToast(validation.value,'error'); return; }
  if(!checkOnly&&!categories.value.length&&!['LOST','INVALID'].includes(followup.value.stage)){validation.value='Select at least one Treatment Interest (Section 3)';showToast(validation.value,'error');return;}
  if(!checkOnly&&!followup.value.conclusion.trim()){if(choice.value==='Appointment Booked')followup.value.conclusion='Walk-in happened - treatment not booked yet';else{validation.value='Please select a Conclusion Remark';showToast(validation.value,'error');return;}}
  if (checkOnly) { validation.value = 'Update checked. No record changed.'; showToast(validation.value); return; }
  const profile = { ...savedProfile.value, alias:alias.value, phones:phones.value.filter(Boolean), primary:primary.value||phones.value.find(Boolean), issues:issues.value.map(row=>row[1]), assessment:assessment.value, medical_conditions:medical.value };
  emit('save', { profile, result:result.value, reason:result.value==='Not Connected'?choice.value:'', nextAction:choice.value==='Appointment Booked'?'book':needsDate.value?'followup':'stop' });
}
watch(()=>props.notice,value=>{if(value)showToast(value)});
watch(()=>props.error,value=>{if(value)showToast(value,'error')});
</script>

<template>
  <div class="cc-bar">
    <div id="followup-lead-banner" class="cc-lead-banner oct-profile-title wf-banner-v3">
      <button id="oct-back" class="btn btn-gy btn-sm" title="Back to dashboard" @click="emit('back')">←</button>
      <span class="wf-stamp" :class="phase==='won'?'wf-booked':'wf-text t-proc'"><i v-if="phase==='won'">★ LIFE ★</i><b>{{phase==='won'?'BOOKED':savedStatus.toUpperCase()}}</b><i v-if="phase==='won'">CLIENT</i></span>
      <span class="wf-title-row"><span class="wf-lbl">Client name</span><span class="wf-client" :class="phase==='won'?'is-booked':'not-booked'">{{clientName}}</span><span class="wf-lbl">Agent name</span><span class="wf-agent">{{lead.lead_owner||'Unassigned'}}</span></span>
      <span class="wf-chips"><span class="pill p-blue">{{lead.name}}</span><span class="pill p-teal">{{lead.source||'—'}}</span><span class="pill p-gy">Call #{{calls}}</span></span><span class="wf-age">Lead Age <b>{{age}}</b> · Calls <b>{{calls}}</b></span>
    </div>
    <div class="cc-bar-actions"><button class="btn btn-g btn-sm" @click="emit('start-call')">Start Call</button><button class="btn btn-gy btn-sm" @click="emit('stop-call')">Open phone / hang up</button></div>
  </div>
  <div id="wf-shell">
    <div id="followup-form-body"><div class="ff-form">
      <div id="ff-prog-wrap" class="ff-progress-wrap"><div id="ff-prog-steps" class="ff-prog-steps"><button v-for="(step,index) in progressSteps" :key="step" type="button" class="ff-prog-step" :class="{done:stepComplete[index]}" @click="jumpToStep(index)"><span class="ff-prog-dot" :class="{done:stepComplete[index]}">{{stepComplete[index]?'✓':index+1}}</span><span class="ff-prog-label">{{step}}</span></button></div><div class="ff-prog-bar-wrap"><div id="ff-prog-bar" class="ff-prog-bar" :style="{width:progress+'%'}"></div></div><div class="ff-progress-meta"><span class="ff-progress-identity">Lead ID: <strong>{{lead.name}}</strong> <span aria-hidden="true">·</span> Assigned to: <strong>{{lead.lead_owner_name||lead.lead_owner||'—'}}</strong></span><span class="ff-progress-actions"><button type="button" class="btn btn-gy btn-sm" @click="showHistory">🕘 Lead History</button><button type="button" class="btn btn-gy btn-sm" :disabled="!primary" :title="`ConVox call history matched by mobile ${maskPhone(primary)}`" @click="openConvoxHistory">🎧 ConVox History <span v-if="primary">· {{maskPhone(primary)}}</span></button></span><span id="ff-prog-pct" class="ff-prog-pct">{{progress}}% complete</span></div></div>
      <section id="ffsec-1" class="ff-sec"><div class="ff-sec-hdr"><span class="sec-num">1</span>Lead Source &amp; Location Info</div><div class="ff-sec-body">
        <div class="oct-import-summary"><div v-for="[key,value] in [['Client',clientName],['Phone',maskPhone(primary)],['Source',lead.source],['Assigned',lead.lead_owner],['Posting date',lead.custom_posting_date||'Not recorded'],['Imported',lead.creation],['Previous owner',previousOwner],['Assignment',assignment]]" :key="key"><small>{{key}}</small><span>{{value||'—'}}</span></div></div>
        <div class="ff-row ff-row-4"><label class="ff-field"><span class="ff-label">Lead Source <span class="req">*</span></span><input v-model="draft.source" :disabled="!canEditSource" class="ff-input" list="cc-source-list"><datalist id="cc-source-list"><option :value="lead.source" /><option v-for="source in sources" :key="source.name" :value="source.name" /></datalist></label><label class="ff-field"><span class="ff-label">Source Main Category</span><input v-model="draft.custom_media" class="ff-input" disabled></label><label class="ff-field"><span class="ff-label">Date of Lead (Posting Date)</span><input v-model="draft.custom_posting_date" class="ff-input" type="date"></label><label class="ff-field"><span class="ff-label">Email</span><input v-model="draft.email_id" class="ff-input" type="email" placeholder="client email"></label></div>
        <div class="ff-row ff-row-2"><label class="ff-field"><span class="ff-label">Created On (Portal) <span class="ff-locked-badge">🔒 AUTO</span></span><input :value="lead.creation" class="ff-input" disabled></label><label class="ff-field"><span class="ff-label">Last Updated On <span class="ff-locked-badge">🔒 AUTO</span></span><input :value="lead.modified" class="ff-input" disabled></label></div>
        <div class="ff-row ff-row-4"><label class="ff-field"><span class="ff-label">Client Area / Locality <span class="req">*</span></span><input v-model="draft.city" class="ff-input" placeholder="Type area name"></label><label class="ff-field"><span class="ff-label">Nearest Branch (Auto)</span><input :value="lead.branch||'—'" class="ff-input" disabled></label><label class="ff-field"><span class="ff-label">Preferred Branch <span class="req">*</span></span><select v-model="draft.branch" class="ff-select"><option value="">— Ask client —</option><option v-if="draft.branch&&!reference.BRANCHES.some(branch=>branch.name===draft.branch)" :value="draft.branch">{{draft.branch}}</option><option v-for="branch in reference.BRANCHES" :key="branch.code" :value="branch.name">{{branch.name}} ({{branch.code}})</option></select></label><label class="ff-field"><span class="ff-label">City</span><input :value="reference.BRANCHES.find(branch=>branch.name===draft.branch)?.city||draft.city" class="ff-input" readonly></label></div>
        <div class="ff-row ff-row-2"><label class="ff-field"><span class="ff-label">Lead Owner <span class="ff-locked-badge">{{manager?'EDITABLE':'🔒 LOCKED'}}</span></span><input v-model="draft.lead_owner" class="ff-input" :disabled="!manager" placeholder="Search owner by name…"></label><label class="ff-field"><span class="ff-label">Current Owner (from portal)</span><input :value="lead.lead_owner||'Unassigned'" class="ff-input" disabled></label></div>
        <label class="ff-field"><span class="ff-label">Enquired For</span><select v-model="draft.enquired_for" class="ff-select"><option value="">— Select enquiry —</option><option v-for="enquiry in ['Slimming','Skin','Hair','Laser','HT','Hair Patch','Life Rise']" :key="enquiry">{{enquiry}}</option><option v-if="draft.enquired_for&&!['Slimming','Skin','Hair','Laser','HT','Hair Patch','Life Rise'].includes(draft.enquired_for)">{{draft.enquired_for}}</option></select><small>Select the enquiry; treatment details and concern are recorded below.</small></label>
      </div></section>
      <section id="ffsec-2" class="ff-sec"><div class="ff-sec-hdr"><span class="sec-num">2</span>Client Personal Details</div><div class="ff-sec-body wf-personal">
        <div id="oct-contact-panel"><div class="oct-inline wf-ph-head"><b>Contact numbers</b><small>● Primary number shared with the branch · hover to reveal</small></div><div class="oct-phone-grid"><div v-for="(number,index) in phones" :key="index" class="oct-phone wf-ph-box"><label class="wf-ph-primary"><input v-model="primary" type="radio" :value="number" :disabled="number.length!==10" aria-label="Primary contact"></label><input class="oct-phone-value" :value="revealed===index||manager||!savedPhones.has(number)?number:maskPhone(number)" :readonly="!manager&&savedPhones.has(number)" maxlength="10" inputmode="numeric" aria-label="Contact number" @focus="revealed=index" @mouseenter="revealed=index" @mouseleave="revealed=-1" @blur="revealed=-1" @input="setPhone(index,$event)"><button class="wf-ph-copy" title="Copy phone number" @click="copyPhone(number)">⧉</button><div class="oct-phone-actions"><button :disabled="phones.length>=4||phones.some(x=>!x)" title="Add number" @click="addPhone(index)">+</button><button :disabled="!manager&&savedPhones.has(number)" title="Remove number" @click="removePhone(index)">−</button></div></div></div></div>
        <label class="ff-field"><span class="ff-label">Full Name <span class="req">*</span> / Alias name</span><div class="oct-name-split"><input v-model="draft.first_name" class="ff-input" placeholder="Client's full name"><input id="oct-alias" v-model="alias" class="ff-input" placeholder="Alias name (optional)"></div></label><label class="ff-field"><span class="ff-label">Age</span><input v-model="draft.age" class="ff-input" type="number" min="14" max="90"></label><label class="ff-field"><span class="ff-label">Gender <span class="req">*</span></span><select v-model="draft.gender" class="ff-select"><option value="">Select</option><option>Female</option><option>Male</option><option>Other</option></select></label><label class="ff-field"><span class="ff-label">Marital Status</span><select v-model="draft.custom_marital_status" class="ff-select"><option value="">Select</option><option value="Single">Single / Unmarried</option><option>Married</option><option>Divorced</option><option>Widowed</option></select></label>
        <label v-if="draft.custom_marital_status==='Married'" class="ff-field"><span class="ff-label">Married Since (years)</span><input v-model="assessment.married_years" class="ff-input" type="number"></label><label v-if="draft.gender==='Female'" class="ff-field"><span class="ff-label">Number of Children</span><input v-model="draft.custom_no_of_kids" class="ff-input" type="number" min="0"></label><label v-if="draft.gender==='Female'" class="ff-field"><span class="ff-label">Any Recent Delivery?</span><select v-model="draft.custom_delivery_type" class="ff-select"><option value="">Select</option><option>No</option><option>Within 6 months</option><option>Within 1 year</option><option>More than 1 year ago</option></select></label><label v-if="draft.gender==='Female'" class="ff-field"><span class="ff-label">Currently Breastfeeding?</span><select v-model="draft.custom_breastfeeding" class="ff-select"><option value="">Select</option><option>No</option><option>Yes</option></select></label>
      </div></section>
      <section id="ffsec-3" class="ff-sec"><div class="ff-sec-hdr"><span class="sec-num">3</span>Enquired For · Treatment Interest &amp; Concern <span class="req">(required for booked / follow-up leads)</span></div><div class="ff-sec-body"><input id="oct-issue-search" v-model="issueSearch" class="ff-input" placeholder="Search client issue, e.g. belly, glow, hair fall…" autocomplete="off"><div id="oct-issue-results"><button v-for="row in matches" :key="row[1]" @click="addIssue(row)">{{row[1]}} <small> / {{row[2]}} / {{row[3]}}</small></button></div><div id="oct-selected-issues"><div v-for="(row,index) in issues" :key="row[1]" class="oct-issue"><span>{{row[1]}}</span><span>{{row[2]}}</span><span>{{row[3]}}</span><button :aria-label="'Remove '+row[1]" @click="removeIssue(index)">×</button></div></div><small v-if="!issues.length&&categories.length">Existing interests: {{categories.join(', ')}}. Select matching issues to update.</small><label class="ff-field"><span class="ff-label">Concern in client’s words</span><textarea v-model="draft.consultant" class="ff-textarea"></textarea></label></div></section>
      <details v-if="categories.length" id="ffsec-4" class="ff-sec"><summary class="ff-sec-hdr"><span class="sec-num">4</span>Treatment Assessment ▸</summary><div class="ff-sec-body"><div v-for="section in assessmentSections" :key="section.title" class="tq-block"><div class="tq-title">{{section.title}}</div><div class="ff-row ff-row-3"><label v-for="field in section.fields" :key="field.key" class="ff-field"><span class="ff-label">{{field.label}}</span><select v-if="field.options" v-model="assessment[field.key]" class="ff-select"><option value="">Select</option><option v-for="option in field.options" :key="option">{{option}}</option></select><input v-else-if="['weight','height','custom_target_weight','custom_bmi','custom_previous_attempts'].includes(field.key)" v-model="draft[field.key]" class="ff-input" :type="field.type||'text'" :readonly="field.readonly" :placeholder="field.placeholder"><input v-else v-model="assessment[field.key]" class="ff-input" :type="field.type||'text'" :placeholder="field.placeholder"></label></div></div><div class="tq-block"><div class="tq-title">Medical History</div><div class="ff-tip">Ask gently: “Do you have any health conditions our doctor should know about?” Tap all that apply.</div><div class="med-grid"><label v-for="condition in conditions" :key="condition.name" class="med-chip"><input v-model="medical" type="checkbox" :value="condition.name"><span>{{condition.alert?'⚠️ ':''}}{{condition.name}}</span></label></div><label class="ff-field"><span class="ff-label">Other / Notes (medication, surgery, pregnancy)</span><textarea v-model="draft.medical_history" class="ff-textarea"></textarea></label><label class="ff-field"><span class="ff-label">Current Medication</span><input v-model="draft.custom_current_medication" class="ff-input"></label><label class="ff-field"><span class="ff-label">Ever Hospitalized / Surgery?</span><select v-model="draft.custom_hospitalized" class="ff-select"><option value="">Select</option><option>No</option><option>Yes</option></select></label></div></div></details>
    </div></div>
    <aside id="wf-panel"><header><strong class="wf-h-title">Followup - Lead Disposition</strong><div class="wf-h-client">Client : <b>{{clientName}}</b> / <span class="wf-h-br">{{draft.branch}}</span></div><div class="wf-h-phone">{{maskPhone(primary)}}</div><small>Lead Age: {{age}} · Calls {{calls}}</small></header><div id="wf-pipeline"><small>Current Status</small><strong>{{savedStatus}}</strong><small v-if="lead.custom_next_followup_date">🗓 Scheduled {{lead.custom_next_followup_date}}</small><small v-if="result==='Not Connected'&&choice!==wf.APPT_NR&&!wf.BADNUM.includes(choice)">Failed attempt · pipeline stays unchanged</small></div><div id="wf-call"><div id="ff-status-area"><div class="wf-label">Did the call connect?</div><div class="wf-phase">State: <b>{{phaseLabels[phase]}}</b></div><div v-if="!locked||canReopen" class="oct-inline"><button :aria-pressed="result==='Connected'" @click="chooseConnection('Connected')">✓ {{canReopen?'Connected · manager reopen':'Connected'}}</button><button v-if="!locked" :aria-pressed="result==='Not Connected'" @click="chooseConnection('Not Connected')">☏ Not Connected</button></div><div v-if="locked&&!canReopen" class="wf-lock" :class="{won:phase==='won'}">{{phase==='won'?'🏆 Success - Client Booked ✓':phase==='dnc'?'⛔ Do Not Contact — permanent lock. No calls or status changes.':'🔒 '+phaseLabels[phase]+'. Only a Manager / Admin can reopen with an audit remark.'}}</div><div v-for="[title,tone,options] in groups" :key="title" class="wf-grp" :class="tone"><div class="wf-grp-h">{{title}}</div><div class="wf-opts"><button v-for="option in options" :key="option" :aria-pressed="choice===option" @click="chooseOutcome(option)">{{option}}</button></div></div><div v-if="choice" class="wf-tip"><b>{{choice}} → {{result==='Not Connected'&&choice!==wf.APPT_NR&&!wf.BADNUM.includes(choice)?'pipeline unchanged':followup.stage}}</b>{{wf.TIP[choice]}}</div></div></div>
      <div id="wf-actions"><div v-if="needsDate" id="ff-action-content"><label class="ff-field"><span class="ff-label">Next Follow-Up Date &amp; Time <span class="req">*</span></span><input v-model="followup.next_followup" class="ff-input" type="datetime-local"></label></div><div v-else-if="choice==='Appointment Booked'" class="ff-tip">Save this call, then choose the branch consultation slot.</div></div>
      <div v-if="Object.values(contactMatches).some(matches=>matches.length)" class="wf-review"><template v-for="(matches,phone) in contactMatches" :key="phone"><p v-for="client in matches" :key="client.name">Existing client: {{client.client||client.patient_name||client.patient||client.name}} · {{client.branch||'Branch not recorded'}}</p></template></div>
      <div id="wf-notes"><section id="ffsec-cr" class="ff-sec"><div class="ff-sec-body"><label class="ff-field"><span class="ff-label">Conclusion Remark <span class="req">*</span></span><input v-model="followup.conclusion" class="ff-input" list="ff-conclusion-list" placeholder="Type to search or pick a conclusion…"><datalist id="ff-conclusion-list"><option v-for="remark in reference.CONCLUSION_REMARKS" :key="remark" :value="remark" /></datalist></label><label class="ff-field"><span class="ff-label">Agent Notes / Internal Remarks</span><textarea v-model="followup.remarks" class="ff-textarea" placeholder="Any important notes..."></textarea></label><label class="ff-field"><span class="ff-label">Chat Script</span><textarea v-model="draft.custom_chat_script" class="ff-textarea" placeholder="Paste or note the chat script used..."></textarea></label></div></section></div>
      <p v-if="validation||error" class="wf-review" role="alert">{{validation||error}}</p><div class="wf-save"><button :disabled="busy||locked&&!canReopen" @click="submit()">{{busy?'Saving…':'Save call & update'}}</button><button id="wf-check-update" :disabled="busy" @click="submit(true)">Check update</button></div>
      <button type="button" class="btn btn-gy btn-sm" @click="showHistory">🕘 Call &amp; status history</button><details><summary>Communication tools</summary><div id="ffsec-7" class="ff-sec"><div class="ff-sec-body"><a :href="'tel:'+primary">📞 Open phone</a><a :href="'https://wa.me/'+primary" target="_blank" rel="noopener">💬 WhatsApp</a><button type="button" class="btn btn-gy btn-sm" @click="openConvoxHistory">🎧 ConVox details</button><RouterLink :to="{name:'cc-appointments',query:{lead:lead.name}}">📅 Appointment calendar</RouterLink></div></div></details>
    </aside>
  </div>
  <dialog ref="historyDialog" class="modal-box cc-summary-modal cc-history-dialog">
    <header class="cc-history-header"><div><h2>Lead history</h2><p>{{clientName}} · {{lead.name}}</p></div><button type="button" class="btn btn-gy btn-sm" @click="historyDialog?.close()">Close</button></header>
    <p v-if="leadHistoryLoading" role="status">Loading lead history…</p><p v-if="leadHistoryError" class="wf-review" role="alert">{{leadHistoryError}}</p>
    <div class="cc-history-list">
      <article v-for="(event,index) in [...(savedProfile.workflow?.history||[])].reverse()" :key="'call-'+index" class="cc-history-event"><b>Call {{event.number}} · {{event.result}}</b><small>{{event.at}} · {{event.by}}</small><span>{{event.reason||event.to}}</span><small>{{event.from}} → {{event.to}}</small></article>
      <article v-for="(event,index) in lead.workflow_hint?.legacy_events||[]" :key="'legacy-'+index" class="cc-history-event"><b>Earlier status change</b><small>{{event.at}} · {{event.by}}</small><span>{{event.from}} → {{event.to}}</span></article>
      <article v-for="(event,index) in leadHistory" :key="'lead-history-'+index" class="cc-history-event"><b>{{event.creation||event.time||'Lead change'}} · {{event.owner||event.by||'User'}}</b><span>{{leadHistoryChanges(event).map(change=>`${historyLabels[change[0]]||change[0]}: ${change[1]||'—'} → ${change[2]||'—'}`).join(' · ')||'No tracked field changes'}}</span></article>
      <p v-if="!leadHistoryLoading&&!leadHistoryError&&!savedProfile.workflow?.history?.length&&!lead.workflow_hint?.legacy_events?.length&&!leadHistory.length">No detailed history recorded. Earlier calls: {{calls}}.</p>
    </div>
    <button type="button" class="btn btn-gy btn-sm" @click="leadHistory=[];showHistory()">↻ Refresh history</button>
  </dialog>
  <div v-if="toast" class="cc-worksheet-toast" :class="toast.type" role="status" aria-live="polite" @mouseenter="clearTimeout(toastTimer)" @mouseleave="showToast(toast.message,toast.type)" @focusin="clearTimeout(toastTimer)" @focusout="showToast(toast.message,toast.type)"><span>{{toast.message}}</span><button type="button" aria-label="Dismiss notification" @click="dismissToast">×</button></div>
</template>
