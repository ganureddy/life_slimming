<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { request } from '../../api/http';
import { session } from '../../lib/session';
const props = defineProps({ lead: { type: Object, required: true } });
const emit = defineEmits(['saved']);
const allowed = computed(() => session.user === 'Administrator' || session.roles.some(role => ['System Manager', 'Call Center Export'].includes(role)));
const status = ref(''), options = ref([]), busy = ref(false), error = ref(''), notice = ref('');
const optionsError = ref(''), optionsLoading = ref(false);
let optionsController, mounted = true;
const locked = computed(() => props.lead.custom_appointment_status === 'Visited Booked' && !session.roles.includes('Call Center Export'));
watch(() => [props.lead.name, props.lead.custom_appointment_status], () => { status.value = props.lead.custom_appointment_status || ''; error.value = ''; notice.value = ''; }, { immediate: true });
async function loadOptions() {
  optionsController?.abort();
  const controller = new AbortController(); optionsController = controller;
  options.value = []; optionsError.value = '';
  if (!allowed.value) { optionsLoading.value = false; return; }
  optionsLoading.value = true;
  try {
    const result = await request('life_slimming.api.cc_appointment_status.options', { csrfToken: session.csrf_token, signal: controller.signal });
    if (!mounted || controller.signal.aborted) return;
    if (!Array.isArray(result.message) || result.message.some(value => typeof value !== 'string'))
      throw new Error('Appointment status options could not be loaded. Please retry.');
    options.value = [...new Set(result.message.map(value => value.trim()).filter(Boolean))];
  } catch (cause) { if (mounted && !controller.signal.aborted) optionsError.value = cause.message; }
  finally { if (mounted && optionsController === controller) optionsLoading.value = false; }
}
watch(allowed, loadOptions, { immediate: true });
onBeforeUnmount(() => { mounted = false; optionsController?.abort(); });
async function save() {
  if (busy.value || optionsLoading.value || !allowed.value || locked.value || !options.value.includes(status.value) || status.value === props.lead.custom_appointment_status) return;
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
      <select v-if="allowed" v-model="status" :disabled="busy || locked || optionsLoading || !!optionsError" aria-label="Appointment Status">
        <option value="" disabled>Select status</option>
        <option v-if="status && !options.includes(status)" :value="status" disabled>{{status}}</option>
        <option v-for="option in options" :key="option" :value="option">{{option}}</option>
      </select>
      <span v-else>{{lead.custom_appointment_status || '—'}}</span>
    </label>
    <button v-if="allowed && !locked" type="button" :disabled="busy || optionsLoading || !options.includes(status) || status === lead.custom_appointment_status" @click="save">{{busy ? 'Saving…' : 'Save status'}}</button>
    <p v-if="optionsLoading" role="status">Loading appointment statuses…</p>
    <p v-if="optionsError" role="alert" class="cc-error">{{optionsError}} <button type="button" @click="loadOptions">Retry</button></p>
    <p v-if="error" role="alert" class="cc-error">{{error}}</p>
    <p v-if="notice" role="status">{{notice}}</p>
  </div>
</template>
