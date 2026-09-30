<script setup>
import { computed, ref, watch, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { convoxApi } from '../api/convox';
const props = defineProps({ leadId: { type: String, default: '' }, modal: Boolean });
const route = useRoute();
const lookup = ref('');
const selectedLead = computed(() => props.leadId || route.params.leadId || lookup.value.trim());
const data = ref(null), busy = ref(false), error = ref('');
let controller;
async function load(start = 0) {
  controller?.abort();
  if (!selectedLead.value) { data.value = null; busy.value = false; return; }
  const request = new AbortController(); controller = request;
  busy.value = true; error.value = '';
  try { const result = await convoxApi.leadHistory(selectedLead.value, start, request.signal); if (!request.signal.aborted) data.value = result; }
  catch (e) { if (!request.signal.aborted) error.value = e.message || 'Unable to load call history.'; }
  finally { if (controller === request) busy.value = false; }
}
function playRecording(event) {
  document.querySelectorAll('.call-history audio').forEach(audio => {
    if (audio !== event.target) audio.pause();
  });
}
function recordingUrl(value) {
  if (typeof value !== 'string' || !value.trim()) return '';
  const raw = value.trim();
  if (!/^https?:\/\//i.test(raw) && !/^\/(?:private\/)?files\//.test(raw)) return '';
  try { const url = new URL(raw, window.location.origin); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : ''; }
  catch { return ''; }
}
watch(() => props.leadId || route.params.leadId, () => { data.value = null; load(); }, { immediate: true });
onUnmounted(() => controller?.abort());
</script>

<template>
  <section class="call-history" :aria-busy="busy">
    <div class="history-heading">
      <div><RouterLink v-if="!modal" :to="{ name: 'leads' }">← CC dashboard</RouterLink><h1>ConVox call details</h1><p v-if="data">{{ data.lead_name }} · {{ data.lead_id }} · {{ data.mobile_number }}</p></div>
      <button class="history-button" :disabled="busy" @click="load(data?.start || 0)">Refresh</button>
    </div>
    <form v-if="!leadId && !route.params.leadId" class="history-lookup" @submit.prevent="load()">
      <label for="convox-lead">Lead ID</label>
      <input id="convox-lead" v-model="lookup" placeholder="Enter Lead ID" required maxlength="140">
      <button :disabled="busy">View call history</button>
      <p>Or open a lead in CC Dashboard and choose ConVox details beside History.</p>
    </form>
    <p v-if="error" role="alert">{{ error }} <button :disabled="busy" @click="load(data?.start || 0)">Retry</button></p>
    <p v-if="busy" role="status">Loading call events…</p>
    <template v-if="data">
      <div class="history-summary"><div><strong>{{ data.total_calls }}</strong><span>Calls</span></div><div><strong>{{ data.total_events }}</strong><span>Call events</span></div><div><strong>{{ data.mobile_number }}</strong><span>Matched mobile</span></div></div>
      <p>Popup and status events with the same call reference count as one call. {{ data.scope === 'own_agent' ? 'Showing your agent’s events.' : 'Showing events across all agents.' }}</p>
      <p v-if="!data.total_events && !busy">No saved ConVox call events match this lead’s mobile number.</p>
      <article v-for="event in data.events" :key="event.name" class="call-event">
        <header><div><h2>{{ event.call_status || event.event_type || 'Call event' }}</h2><p>{{ event.call_datetime || event.received_on || 'Time unavailable' }} · {{ event.call_reference || event.name }}</p></div><span>{{ event.call_duration || '—' }} <small>duration (as recorded)</small></span></header>
        <div v-if="recordingUrl(event.recording_file_name)" class="recording"><audio controls preload="none" @play="playRecording" :src="recordingUrl(event.recording_file_name)"></audio><a :href="recordingUrl(event.recording_file_name)" target="_blank" rel="noopener noreferrer">Open recording ↗</a></div>
        <p v-else>{{ event.recording_file_name ? 'Recording filename saved; a playable URL is not available.' : 'No recording received for this event.' }}</p>
        <details><summary>View all event details</summary><dl><div v-for="field in data.fields" :key="field.key"><dt>{{ field.label }}</dt><dd>{{ event[field.key] === 0 ? '0' : (event[field.key] || '—') }}</dd></div></dl></details>
      </article>
      <nav v-if="data.total_events" class="history-pagination" aria-label="Call history pages"><button :disabled="busy || data.start === 0" @click="load(Math.max(0, data.start - 50))">Previous</button><span>{{ data.start + 1 }}–{{ data.start + data.events.length }} of {{ data.total_events }} events</span><button :disabled="busy || !data.has_more" @click="load(data.start + 50)">Next</button></nav>
    </template>
  </section>
</template>

<style scoped>
.call-history{max-width:1200px;margin:auto;color:#183e32}.history-heading,.call-event header,.history-pagination{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}.history-heading h1{margin:12px 0 4px}.call-history p{color:#5c6f68;overflow-wrap:anywhere}.history-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:24px}.history-summary>div,.call-event{background:white;border:1px solid #dbe6df;border-radius:12px;padding:20px}.history-summary strong,.history-summary span{display:block}.history-summary strong{font-size:24px;overflow-wrap:anywhere}.call-event{margin:16px 0}.call-event h2{margin:0;font-size:18px}.call-event header>div{min-width:0}.call-event small{display:block}.recording{display:flex;align-items:center;flex-wrap:wrap;gap:16px;margin:18px 0}audio{max-width:100%}summary{cursor:pointer;font-weight:600;padding:10px 0}dl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}dt{font-size:12px;color:#65766e}dd{margin:5px 0 0;white-space:pre-wrap;overflow-wrap:anywhere}button{padding:9px 16px;border:1px solid #bdcfc3;border-radius:8px;background:white;color:#183e32;cursor:pointer}button:disabled{opacity:.5;cursor:default}a{color:#216345}@media(max-width:650px){.history-summary,dl{grid-template-columns:1fr}.history-summary strong{font-size:20px}.call-event{padding:14px}}
</style>
