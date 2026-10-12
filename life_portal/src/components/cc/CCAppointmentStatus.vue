<script setup>
import { computed, ref, watch } from 'vue';
import { request } from '../../api/http';
import { session } from '../../lib/session';
const props = defineProps({ lead: { type: Object, required: true } });
const emit = defineEmits(['saved']);
const allowed = computed(() => session.user === 'Administrator' || session.roles.some(role => ['System Manager', 'Call Center Export'].includes(role)));
const status = ref(''), options = ref([]), busy = ref(false), error = ref(''), notice = ref('');
const locked = computed(() => props.lead.custom_appointment_status === 'Visited Booked');
watch(() => [props.lead.name, props.lead.custom_appointment_status], () => { status.value = props.lead.custom_appointment_status || ''; error.value = ''; notice.value = ''; }, { immediate: true });
watch(allowed, async value => {
  if (!value) return;
  try { const result = await request('life_slimming.api.cc_appointment_status.options', { csrfToken: session.csrf_token }); options.value = result.message || []; }
  catch (e) { error.value = e.message; }
}, { immediate: true });
async function save() {
  busy.value = true; error.value = ''; notice.value = '';
  try {
    const result = await request('life_slimming.api.cc_appointment_status.update', { args: { lead: props.lead.name, status: status.value, expected_modified: props.lead.modified }, csrfToken: session.csrf_token });
    emit('saved', result.message); notice.value = 'Appointment status saved.';
  } catch (e) { error.value = e.message; }
  finally { busy.value = false; }
}
</script>
<template>
  <div class="cc-appointment-status">
    <label>Appointment Status
      <select v-if="allowed" v-model="status" :disabled="busy || locked" aria-label="Appointment Status">
        <option value="" disabled>Select status</option>
        <option v-if="status && !options.includes(status)" :value="status" disabled>{{status}}</option>
        <option v-for="option in options" :key="option" :value="option">{{option}}</option>
      </select>
      <span v-else>{{lead.custom_appointment_status || '—'}}</span>
    </label>
    <button v-if="allowed && !locked" type="button" :disabled="busy || !options.includes(status) || status === lead.custom_appointment_status" @click="save">{{busy ? 'Saving…' : 'Save status'}}</button>
    <p v-if="error" role="alert" class="cc-error">{{error}}</p>
    <p v-if="notice" role="status">{{notice}}</p>
  </div>
</template>
