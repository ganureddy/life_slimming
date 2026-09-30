<script setup>
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { canAccessModule } from '../lib/session';
import ConvoxHistoryPage from '../pages/ConvoxHistoryPage.vue';
const dialog = ref(null), leadId = ref('');
const route = useRoute();
function close() { dialog.value?.close(); leadId.value = ''; }
async function receive(event) {
  const frame = document.querySelector('.portal-source-page iframe');
  if (route.name !== 'leads' || !canAccessModule('leads') || !frame || event.source !== frame.contentWindow || event.origin !== window.location.origin) return;
  if (event.data?.type !== 'life-convox-history' || typeof event.data.lead_id !== 'string' || !event.data.lead_id || event.data.lead_id.length > 140) return;
  leadId.value = event.data.lead_id;
  await nextTick(); dialog.value?.showModal();
}
onMounted(() => window.addEventListener('message', receive));
onUnmounted(() => window.removeEventListener('message', receive));
watch(() => route.fullPath, close);
</script>
<template>
  <dialog ref="dialog" class="convox-history-dialog" aria-label="ConVox call history" @close="leadId = ''" @click="event => { if (event.target === dialog) close(); }">
    <button class="history-close" aria-label="Close ConVox history" @click="close">Close ×</button>
    <ConvoxHistoryPage v-if="leadId" :key="leadId" :lead-id="leadId" modal />
  </dialog>
</template>
<style scoped>
.convox-history-dialog{width:min(1100px,94vw);max-height:90dvh;box-sizing:border-box;border:1px solid #d4e1d8;border-radius:16px;padding:24px;background:#f6f9f7;overflow:auto}.convox-history-dialog::backdrop{background:#102a24a6}.history-close{display:block;margin-left:auto;padding:8px 14px;background:white;border:1px solid #bdcfc3;border-radius:8px;cursor:pointer}@media(max-width:600px){.convox-history-dialog{padding:14px;width:96vw}}
</style>
