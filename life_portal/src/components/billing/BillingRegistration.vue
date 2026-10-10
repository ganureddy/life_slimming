<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { billingCall, billingList, uploadBillingFile } from '../../api/billing';
import { normalizeMobile, practitionersFor } from '../../lib/billing';
import { indiaStamp } from '../../lib/cc';
const props = defineProps({ bootstrap: Object, branches: Array, branch: String });
const emit = defineEmits(['registered', 'cancel', 'busy-change']);
const form = reactive({ patient_name: '', mobile: '', sex: '', dob: '', branch: props.branch || props.branches[0] || '', media: 'InHouse', visited_for: '', consultation_employee: '', final_decision: '', treatment_category: '', pd_form_number: '', lead: '' });
const busy = ref(false), error = ref(''), otp = ref(''), sentTo = ref(''), verified = ref(''), pdFile = ref(null), leadChecked = ref(false), leadFound = ref(false), existingClient = ref(null);
const practitioners = computed(() => practitionersFor(props.bootstrap.practitioners, form.branch));
watch(()=>form.mobile,()=>{form.lead='';leadChecked.value=false;leadFound.value=false;existingClient.value=null;verified.value='';sentTo.value='';});
watch(()=>form.branch,()=>{form.consultation_employee='';});
async function action(fn) { if (busy.value) return; busy.value = true; emit('busy-change',true); error.value = ''; try { await fn(); } catch (e) { error.value = e.message; } finally { busy.value = false; emit('busy-change',false); } }
function validate() {
  if (/\d/.test(form.patient_name) || form.patient_name.replace(/[^a-z]/gi, '').length < 2) throw new Error('Enter a client name with at least two letters and no numbers.');
  if (!/^[6-9]\d{9}$/.test(normalizeMobile(form.mobile))) throw new Error('Enter a valid 10-digit Indian mobile number.');
  for (const key of ['sex', 'branch', 'visited_for', 'consultation_employee', 'final_decision', 'treatment_category', 'pd_form_number']) if (!form[key]) throw new Error('Complete all required registration fields.');
  if (!props.branches.includes(form.branch) || !practitioners.value.some(p => p.name === form.consultation_employee)) throw new Error('Select a permitted branch and consultation employee.');
  if (form.dob && (form.dob > indiaStamp().slice(0, 10) || form.dob < '1900-01-01')) throw new Error('Check the date of birth.');
  if (!pdFile.value) throw new Error('Attach the PD form.');
}
function lookup() { const mobile = normalizeMobile(form.mobile); if (!/^[6-9]\d{9}$/.test(mobile)) return; return action(async () => {
  const [lead, patients] = await Promise.all([
    billingCall('lifescc_billing_lead_lookup', { mobile }),
    billingList('Patient', [], ['name','patient_name','mobile','custom_lead'], { limit: 20, order: 'modified desc', orFilters: [['mobile','like','%'+mobile+'%'],['mobile','like','%91'+mobile+'%']] })
  ]);
  if (mobile !== normalizeMobile(form.mobile)) return;
  existingClient.value = patients.find(patient => normalizeMobile(patient.mobile) === mobile) || null;
  form.lead = lead.lead || '';
  leadFound.value = Number(lead.found) === 1 && !!lead.lead;
  leadChecked.value = true;
  if (leadFound.value && lead.patient_name && !form.patient_name) form.patient_name = lead.patient_name;
  if (leadFound.value && lead.sex) form.sex = lead.sex;
  if (leadFound.value && lead.dob) form.dob = String(lead.dob).slice(0, 10);
  if (leadFound.value && props.branches.includes(lead.branch)) form.branch = lead.branch;
  if (leadFound.value && lead.visited_for) form.visited_for = lead.visited_for;
  if (leadFound.value && lead.media) form.media = lead.media;
}); }
function sendOtp() { return action(async () => {
  if (existingClient.value) throw new Error(`Mobile already registered as ${existingClient.value.name}. Search for that client in Billing instead of registering again.`);
  validate(); verified.value = '';
  const mobile = normalizeMobile(form.mobile);
  sentTo.value = '';
  const existing = await billingList('Patient', [['mobile', '=', mobile]], ['name', 'patient_name'], { limit: 1 });
  if (existing.length) throw new Error(`Mobile already registered as ${existing[0].name}.`);
  const result = await billingCall('life_slimming.user_wise_roles.send_client_whatsapp_otp', { mobile });
  if (result === false) throw new Error('OTP service did not confirm sending.');
  sentTo.value = mobile; otp.value = '';
}); }
function verifyOtp() { return action(async () => {
  if (!/^\d{6}$/.test(otp.value)) throw new Error('Enter the six-digit OTP.');
  if (sentTo.value !== normalizeMobile(form.mobile)) throw new Error('Mobile changed. Send a new OTP.');
  const result = await billingCall('life_slimming.user_wise_roles.verify_client_otp', { mobile: sentTo.value, otp: otp.value });
  if (!(result === 'verified' || result === true || result.verified === true || result.status === 'verified')) throw new Error('Invalid or expired OTP.');
  verified.value = sentTo.value;
}); }
function register() { return action(async () => {
  validate();
  if (!verified.value || verified.value !== normalizeMobile(form.mobile)) throw new Error('Verify this mobile number before registering.');
  const payload = { ...form, mobile: verified.value, pd_form_file: await uploadBillingFile(pdFile.value, 'Patient') };
  const result = await billingCall('lifescc_billing_create_client', payload);
  if (!result.name) throw new Error('Registration did not return a client ID.');
  emit('registered', result.name);
}); }
</script>
<template>
  <section class="billing-panel billing-registration"><header class="billing-section-head"><div><span class="billing-eyebrow">NEW CLIENT</span><h2>Register client</h2><p>Client details, PD form and verified WhatsApp mobile.</p></div><span class="billing-badge tone-green">{{ verified?'Mobile verified':sentTo?'OTP sent':'Client details' }}</span><button :disabled="busy" @click="emit('cancel')">Close registration</button></header><form class="billing-registration-form" @submit.prevent="register">
    <label>Full name *<input v-model.trim="form.patient_name" required :disabled="busy"></label>
    <label>Mobile *<input v-model="form.mobile" inputmode="tel" maxlength="12" autocomplete="tel" required @blur="lookup" :disabled="busy"></label><p v-if="existingClient" class="span-full billing-notice tone-amber" role="status">This mobile is already registered to {{ existingClient.patient_name }} ({{ existingClient.name }}). Search for this client in Billing instead of creating a duplicate.<template v-if="existingClient.custom_lead"> Lead: {{ existingClient.custom_lead }}.</template></p><p v-else-if="leadChecked" class="span-full" role="status">{{ leadFound ? 'Matched Lead ID: '+form.lead+' · client details filled from the lead.' : 'No lead matches this mobile number.' }}</p>
    <label>Gender *<select v-model="form.sex" required :disabled="busy"><option value="">Select</option><option>Male</option><option>Female</option><option>Other</option></select></label>
    <label>Date of birth<input v-model="form.dob" type="date" :max="indiaStamp().slice(0,10)" :disabled="busy"></label>
    <label>Branch *<select v-model="form.branch" @change="form.consultation_employee = ''" :disabled="busy"><option v-for="name in branches" :key="name">{{ name }}</option></select></label>
    <label>Consultation employee *<select v-model="form.consultation_employee" required :disabled="busy"><option value="">Select</option><option v-for="p in practitioners" :key="p.name" :value="p.name">{{ p.practitioner_name }}</option></select></label>
    <label>Visited for *<select v-model="form.visited_for" required :disabled="busy"><option value="">Select</option><option v-for="name in ['Slimming','LHT','LifeRise','Hair','Skin']" :key="name">{{ name }}</option></select></label>
    <label>Decision *<select v-model="form.final_decision" required :disabled="busy"><option value="">Select</option><option>Booked</option><option>Not-Booked</option></select></label>
    <label>Treatment category *<select v-model="form.treatment_category" required :disabled="busy"><option value="">Select</option><option v-for="name in ['Slimming/Cryo','Hair / PRP / GFC','Skin/Laser','LIFE RISE']" :key="name">{{ name }}</option></select></label>
    <label>Media / source<select v-model="form.media" :disabled="!!form.lead"><option v-for="name in [...new Set(['InHouse','Call Center','Walk In','Reference','Google','IG',form.media])]" :key="name">{{ name }}</option></select></label>
    <h3 class="span-full">PD form details</h3><label>PD form number *<input v-model.trim="form.pd_form_number" required :disabled="busy"></label><label>PD form attachment *<input type="file" accept="image/*,application/pdf" @change="pdFile = $event.target.files[0]" :disabled="busy"></label>
    <h3 class="span-full">Verify client mobile</h3><button class="billing-primary" type="button" :disabled="busy || !!existingClient" @click="sendOtp">{{ sentTo ? 'Resend WhatsApp OTP' : 'Send WhatsApp OTP' }}</button>
    <template v-if="sentTo"><label>Six-digit OTP<input v-model="otp" inputmode="numeric" maxlength="6" autocomplete="one-time-code" :disabled="busy"></label><button type="button" :disabled="busy" @click="verifyOtp">Verify OTP</button></template>
    <p v-if="verified === normalizeMobile(form.mobile) && verified" role="status">Mobile verified.</p>
    <button class="billing-primary" :disabled="busy || !verified || !!existingClient">Register client</button><button type="button" :disabled="busy" @click="emit('cancel')">Cancel</button>
  </form><p v-if="error" role="alert">{{ error }}</p><p v-if="busy" role="status">Processing registration…</p></section>
</template>
