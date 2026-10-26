<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { convoxApi } from '../../api/convox';
import reference from '../../data/cc-reference.json';
import { portalDisposition } from '../../lib/convox-disposition';
const emit = defineEmits(['apply-disposition']);
const suggestion = computed(() => portalDisposition(latest.value, reference.WF));
const props = defineProps({ lead: { type: Object, required: true } });
const latest = ref(null), count = ref(0), error = ref('');
let controller;
async function load() {
  controller?.abort();
  const request = new AbortController(); controller = request;
  try {
    const data = await convoxApi.leadHistory(props.lead.name, 0, request.signal);
    if (request.signal.aborted) return;
    latest.value = data.events?.find(event => event.event_type === 'Call Status') || data.events?.[0] || null;
    count.value = data.total_calls || 0; error.value = '';
  } catch (e) { if (!request.signal.aborted) error.value = e.message || 'Call details unavailable.'; }
}
function changed(event) {
  if (event.detail?.crm_lead === props.lead.name) load();
}
watch(() => props.lead.name, () => { latest.value = null; count.value = 0; load(); }, { immediate: true });
onMounted(() => window.addEventListener('life-convox-event', changed));
onBeforeUnmount(() => { controller?.abort(); window.removeEventListener('life-convox-event', changed); });
</script>

<template>
  <section class="form-section" aria-label="Latest ConVox call">
    <strong>ConVox calls · {{ count }}</strong>
    <p v-if="error" role="status">{{ error }} <button type="button" @click="load">Retry</button></p>
    <template v-else-if="latest">
      <p>{{ latest.call_status || latest.event_type }} · {{ latest.call_datetime || latest.received_on }} · {{ latest.call_duration ?? 0 }} seconds</p>
      <p v-if="latest.disposition || latest.disposition_2 || latest.disposition_3">{{ [latest.disposition, latest.disposition_2, latest.disposition_3].filter(Boolean).join(' · ') }}</p>
      <p v-if="suggestion">Portal status: {{ suggestion }} <button type="button" @click="emit('apply-disposition', suggestion)">Use this disposition</button></p>
      <p v-if="latest.remarks">{{ latest.remarks }}</p>
    </template>
    <p v-else>No call events received yet.</p>
    <RouterLink :to="{name: 'convox-history', params: {leadId: lead.name}}">View call details and recordings</RouterLink>
  </section>
</template>
