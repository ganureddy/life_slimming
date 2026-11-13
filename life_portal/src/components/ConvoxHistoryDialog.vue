<script setup>
import { defineAsyncComponent, ref, nextTick, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { canAccessModule } from '../lib/session';
const ConvoxHistoryPage = defineAsyncComponent(() => import('../pages/ConvoxHistoryPage.vue'));
const dialog = ref(null), leadId = ref('');
const route = useRoute();
function close(clear = false) { dialog.value?.querySelectorAll('audio').forEach(audio => audio.pause());dialog.value?.close();if (clear) leadId.value = ''; }
async function showLead(id) {
  if (!canAccessModule('leads') || typeof id !== 'string' || !id || id.length > 140) return;
  leadId.value = id;await nextTick();if (!dialog.value?.open) dialog.value?.showModal();
}
function openNative(event) { showLead(event.detail?.leadId); }
function openLinkedHistory() { if (route.query.history === 'convox') showLead(route.params.leadId||route.query.lead); }
async function receive(event) {
  const frame = document.querySelector('.portal-source-page iframe');
  if (route.name !== 'leads' || !canAccessModule('leads') || !frame || event.source !== frame.contentWindow || event.origin !== window.location.origin) return;
  if (event.data?.type !== 'life-convox-history' || typeof event.data.lead_id !== 'string' || !event.data.lead_id || event.data.lead_id.length > 140) return;
  await showLead(event.data.lead_id);
}
onMounted(() => { window.addEventListener('message', receive);window.addEventListener('life-convox-history-open', openNative);openLinkedHistory(); });
onUnmounted(() => { window.removeEventListener('message', receive);window.removeEventListener('life-convox-history-open', openNative); });
watch(() => route.fullPath, () => { close(true);openLinkedHistory(); });
</script>
<template>
  <dialog ref="dialog" class="convox-history-dialog crm-history-modal" aria-label="ConVox call history" @close="dialog?.querySelectorAll('audio').forEach(audio => audio.pause())" @click="event => { if (event.target === dialog) close(); }">
    <button class="history-close" aria-label="Close ConVox history" @click="close()">Close ×</button>
    <ConvoxHistoryPage v-if="leadId" :key="leadId" :lead-id="leadId" modal />
  </dialog>
</template>
<style scoped>
.convox-history-dialog{width:min(1100px,94vw);max-height:90dvh;box-sizing:border-box;border:1px solid #d4e1d8;border-radius:16px;padding:24px;background:#f6f9f7;overflow:auto}.convox-history-dialog::backdrop{background:#102a24a6}.history-close{display:block;margin-left:auto;padding:8px 14px;background:white;border:1px solid #bdcfc3;border-radius:8px;cursor:pointer}@media(max-width:600px){.convox-history-dialog{padding:14px;width:96vw}}
</style>
