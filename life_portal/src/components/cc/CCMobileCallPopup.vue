<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue';
import { request } from '../../api/http';
import { session } from '../../lib/session';
const emit = defineEmits(['open']);
const call = ref(null), auto = ref(true);
let timer, controller, stopped = false, lastId = '', hiddenId = '';
try { auto.value = localStorage.getItem('life_cc_pop_auto') !== '0'; } catch {}
function saveAuto() { try { localStorage.setItem('life_cc_pop_auto', auto.value ? '1' : '0'); } catch {} }
function hide() { hiddenId = call.value?.id; call.value = null; }
async function tick() {
  if (stopped || document.hidden || controller) return;
  controller = new AbortController();
  try {
    const result = await request('life_cc_mobile_v18', { args: { action: 'live' }, csrfToken: session.csrf_token, signal: controller.signal, timeoutMs: 10000 });
    if (stopped) return;
    const current = result.message?.call;
    const ended = Date.parse(String(current?.ended_on || current?.started_on || '').replace(' ', 'T') + '+05:30');
    call.value = current && current.id !== hiddenId && (current.live || Date.now() - ended < 45000) ? current : null;
    if (call.value?.live && current.id !== lastId) {
      lastId = current.id;
      if (auto.value && current.lead) emit('open', current.lead);
    }
  } catch { /* Polling resumes on the next interval. */ }
  finally { controller = null; }
}
onMounted(() => { timer = setInterval(tick, 3000); document.addEventListener('visibilitychange', tick); tick(); });
onBeforeUnmount(() => { stopped = true; clearInterval(timer); controller?.abort(); document.removeEventListener('visibilitychange', tick); });
</script>

<template>
  <aside v-if="call" class="cc-mobile-call" aria-live="polite">
    <header><strong>{{call.live ? '📱 ON CALL FROM LIFE APP' : '📱 CALL ENDED'}}</strong><button type="button" aria-label="Hide mobile call" @click="hide">×</button></header>
    <strong>{{call.lead_name || call.lead || 'Lead'}}</strong>
    <p>{{call.lead}} · ••••{{call.ph4}}</p>
    <p>{{call.live ? 'Talking' : call.disposition || 'Waiting for result…'}}</p>
    <button type="button" :disabled="!call.lead" @click="emit('open', call.lead)">Open lead</button>
    <label><input v-model="auto" type="checkbox" @change="saveAuto"> Open the lead automatically when a call starts</label>
  </aside>
</template>

<style scoped>
.cc-mobile-call{position:fixed;right:18px;bottom:18px;z-index:10050;width:330px;max-width:calc(100vw - 36px);box-sizing:border-box;padding:14px;background:#fff;border:2px solid #c9a54a;border-radius:14px;box-shadow:0 14px 40px #0a281e40;color:#174b30}.cc-mobile-call header{display:flex;justify-content:space-between;gap:10px;margin-bottom:12px}.cc-mobile-call p{margin:8px 0}.cc-mobile-call label{display:flex;align-items:center;gap:8px;font-size:12px;margin-top:12px}
</style>
