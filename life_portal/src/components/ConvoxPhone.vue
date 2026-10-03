<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { convoxApi, CONVOX_ORIGIN, createCallRequests, isDashboardMessage, validWidgetUrl } from '../api/convox';
import { session, visibleMenu } from '../lib/session';
import '../../../life_slimming/public/js/cc_notifications.js';

const route = useRoute();
const permitted = computed(() => visibleMenu.value.some(group => group.items.some(item => item.id === 'leads')));
const settings = ref(null);
const open = ref(false);
const url = ref('');
const starting = ref(false);
const calling = ref(false);
const error = ref('');
const notice = ref('');
const pollError = ref('');
const selectedLead = ref('');
const target = ref(null);
const targetError = ref('');
const manualLogin = ref(false);
const phoneConfirmed = ref(false);
const readinessInput = ref(null);
const embeddedMicrophoneAvailable = window.isSecureContext && Boolean(navigator.mediaDevices?.getUserMedia);
const frameVersion = ref(0);
const preferManual = ref(false);
function loginPreferenceKey() { return `life-convox-manual:${session.user}`; }
function restoreLoginPreference() {
  try { preferManual.value = localStorage.getItem(loginPreferenceKey()) === '1'; }
  catch { preferManual.value = false; }
}
watch(() => session.user, restoreLoginPreference, { immediate: true });
const events = ref([]);
const incoming = ref(null);
const launcher = ref(null);
const panel = ref(null);
const position = ref(null);
const size = ref({ width: 760, height: 780 });
const resizing = ref(false);
let resizeOrigin;
const dragging = ref(false);
let dragOrigin;
const panelStyle = computed(() => ({
  width: `${size.value.width}px`, height: `${size.value.height}px`,
  ...(position.value ? { left: `${position.value.x}px`, top: `${position.value.y}px`, right: 'auto', bottom: 'auto' } : {}),
}));
function resizeTo(width, height) {
  size.value = {
    width: Math.min(Math.max(360, width), window.innerWidth - 16),
    height: Math.min(Math.max(360, height), window.innerHeight - 96),
  };
}
async function changeSize(delta) {
  resizeTo(size.value.width + delta, size.value.height + delta);
  await nextTick();
  fitPanel();
}
function startResize(event) {
  if (event.button !== 0) return;
  const rect = panel.value.getBoundingClientRect();
  position.value = { x: rect.left, y: rect.top };
  resizeOrigin = { x: event.clientX, y: event.clientY, width: rect.width, height: rect.height };
  resizing.value = true;
  event.currentTarget.setPointerCapture(event.pointerId);
  event.preventDefault();
}
function moveResize(event) {
  if (!resizing.value) return;
  resizeTo(
    Math.min(resizeOrigin.width + event.clientX - resizeOrigin.x, window.innerWidth - position.value.x - 8),
    Math.min(resizeOrigin.height + event.clientY - resizeOrigin.y, window.innerHeight - position.value.y - 8),
  );
  fitPanel();
}
function stopResize() { resizing.value = false; }
function clampPosition(x, y) {
  const rect = panel.value?.getBoundingClientRect();
  return { x: Math.max(8, Math.min(x, window.innerWidth - (rect?.width || 560) - 8)),
    y: Math.max(8, Math.min(y, window.innerHeight - (rect?.height || 600) - 8)) };
}
function startDrag(event) {
  if (event.button !== 0 || event.target.closest('button')) return;
  const rect = panel.value.getBoundingClientRect();
  dragOrigin = { x: event.clientX - rect.left, y: event.clientY - rect.top };
  dragging.value = true;
  event.currentTarget.setPointerCapture(event.pointerId);
}
function moveDrag(event) {
  if (dragging.value) position.value = clampPosition(event.clientX - dragOrigin.x, event.clientY - dragOrigin.y);
}
function stopDrag() { dragging.value = false; }
function fitPanel() {
  resizeTo(size.value.width, size.value.height);
  if (position.value) position.value = clampPosition(position.value.x, position.value.y);
}
function resetPosition() { position.value = null; resizeTo(760, 780); }

const visible = computed(() => permitted.value && (route.name === 'leads' || Boolean(url.value)));
const controller = new AbortController();
let stopped = false, timer, cursor = '';
let sessionGeneration = 0;
let pollingGeneration = null;
const dashboardCallPending = ref(false);
const callRequests = createCallRequests();
const seen = new Set();

async function loadConfig() {
  const generation = sessionGeneration;
  error.value = '';
  try {
    const result = await convoxApi.config(controller.signal);
    if (stopped || generation !== sessionGeneration) return;
    settings.value = result;
    if (!cursor) cursor = settings.value.server_time;
    if (!settings.value.callbacks_ready) { clearTimeout(timer); timer = undefined; }
    if (settings.value.callbacks_ready && !timer && pollingGeneration !== generation) timer = setTimeout(pollEvents, 5000);
  } catch (e) { if (e.name !== 'AbortError') error.value = e.message; }
}
async function pollEvents() {
  const generation = sessionGeneration;
  timer = undefined;
  if (stopped || !settings.value?.callbacks_ready || pollingGeneration === generation) return;
  pollingGeneration = generation;
  try {
    const result = await convoxApi.poll(cursor, controller.signal);
    if (stopped || generation !== sessionGeneration || !settings.value?.callbacks_ready) return;
    cursor = result.cursor;
    for (const event of result.events || []) {
      const key = `${event.name}:${event.received_on}`;
      if (seen.has(key)) continue;
      seen.add(key);
      events.value = [event, ...events.value.filter(row => row.name !== event.name)].slice(0, 20);
      if (route.name === 'leads') {
        document.querySelector('.portal-source-page iframe')?.contentWindow?.postMessage({
          type: 'life-convox-status', call_reference: event.call_reference,
          event_type: event.event_type, call_status: event.call_status,
        }, window.location.origin);
      }
      if (event.event_type === 'Call Status' && incoming.value?.call_reference === event.call_reference) incoming.value = null;
      if (event.event_type === 'Call Popup' && event.call_type === 'incoming') incoming.value = event;
    }
    while (seen.size > 500) seen.delete(seen.values().next().value);
    pollError.value = '';
  } catch (e) {
    if (e.name === 'AbortError' || stopped || generation !== sessionGeneration) return;
    pollError.value = 'Call updates are temporarily unavailable. Calling controls remain in the ConVox phone.';
    if ([401, 403].includes(e.status)) return;
  }
  finally { if (pollingGeneration === generation) pollingGeneration = null; }
  if (!stopped && generation === sessionGeneration && settings.value?.callbacks_ready && !timer) timer = setTimeout(pollEvents, pollError.value ? 15000 : 5000);
}
async function showPhone() {
  open.value = true;
  if (!settings.value) await loadConfig();
  await nextTick();
  fitPanel();
  panel.value?.focus();
}
function minimize() {
  open.value = false;
  launcher.value?.focus();
}
async function connect(manual = preferManual.value, reconnect = false) {
  if (starting.value || (url.value && !reconnect)) return;
  if (url.value && !window.confirm('Reload the phone for sign-in? This will disconnect any active phone session.')) return;
  const generation = sessionGeneration;
  starting.value = true;
  phoneConfirmed.value = false;
  error.value = '';
  try {
    const user = session.user;
    const result = await convoxApi.widgetSession(controller.signal, manual);
    if (stopped || generation !== sessionGeneration || user !== session.user) return;
    if (!validWidgetUrl(result.url)) throw new Error('The phone returned an unexpected address. Contact your administrator.');
    url.value = result.url;
    manualLogin.value = result.mode === 'manual';
    preferManual.value = manual;
    try {
      if (manual) localStorage.setItem(loginPreferenceKey(), '1');
      else localStorage.removeItem(loginPreferenceKey());
    } catch { /* Storage can be disabled. */ }
    frameVersion.value++;
    notice.value = '';
  } catch (e) { if (e.name !== 'AbortError') error.value = e.message; }
  finally { if (generation === sessionGeneration) starting.value = false; }
}
async function callSelected(lead = selectedLead.value) {
  if (calling.value) return { success: false, status: 'BUSY', message: 'A call request is already in progress.' };
  if (!lead || !url.value || !settings.value?.click_to_call_ready) {
    return { success: false, status: 'SETUP_REQUIRED', message: 'Complete the phone setup before calling.' };
  }
  if (!phoneConfirmed.value) {
    open.value = true;
    await nextTick();
    readinessInput.value?.scrollIntoView({ block: 'nearest' });
    readinessInput.value?.focus({ preventScroll: true });
    return { success: false, status: 'PHONE_NOT_READY', message: 'Tick “Phone Registered, agent Idle” above the phone, then click Start Call again. No call was sent.' };
  }
  calling.value = true;
  error.value = '';
  notice.value = '';
  // Reuse the request ID after transport errors, preventing a duplicate dial on retry.
  const requestId = callRequests.forLead(lead);
  try {
    const result = await convoxApi.callLead(lead, requestId, controller.signal);
    if (['CL003', 'CL004', 'CL005', 'CL006'].includes(result.status)) phoneConfirmed.value = false;
    if (result.success) notice.value = `${result.message}${result.refno ? ` Reference: ${result.refno}.` : ''}`;
    else error.value = result.message;
    // UNKNOWN is deliberately sticky: check the phone before choosing another call.
    callRequests.settle(lead, requestId, result.status);
    return result;
  } catch (e) {
    const result = { success: false, status: 'UNKNOWN', message: e.message + ' Check the phone before retrying.' };
    if (e.name !== 'AbortError') error.value = result.message;
    return result;
  }
  finally { calling.value = false; }
}
async function callFromDashboard(event) {
  const reply = result => event.source.postMessage({
    type: 'life-convox-call-result', request_id: event.data.request_id,
    lead_id: event.data.lead_id, ...result,
  }, event.origin);
  if (dashboardCallPending.value || calling.value) {
    reply({ success: false, status: 'BUSY', message: 'A call request is already in progress.' });
    return;
  }
  dashboardCallPending.value = true;
  try {
    await showPhone();
    if (!settings.value?.click_to_call_ready) {
      reply({ success: false, status: 'SETUP_REQUIRED', message: 'ConVox setup is incomplete. Check the phone panel for the missing settings.' });
      return;
    }
    if (!url.value) await connect();
    if (!url.value) {
      reply({ success: false, status: 'SETUP_REQUIRED', message: error.value || 'Open and sign in to the ConVox phone before calling.' });
      return;
    }
    // Do not dial if the agent changed pages/leads while the phone was opening.
    if (route.name !== 'leads' || selectedLead.value !== event.data.lead_id) {
      reply({ success: false, status: 'CANCELLED', message: 'Lead selection changed. Click Start Call on the intended lead.' });
      return;
    }
    reply(await callSelected(event.data.lead_id));
  } finally { dashboardCallPending.value = false; }
}
function receive(event) {
  if (route.name !== 'leads' || !permitted.value) return;
  const frame = document.querySelector('.portal-source-page iframe');
  if (!isDashboardMessage(event, frame, window.location.origin)) return;
  if (event.data.lead_id && event.data.lead_id !== selectedLead.value) {
    selectedLead.value = event.data.lead_id;
    notice.value = '';
  }
  if (event.data.type === 'life-convox-open') showPhone();
  if (event.data.type === 'life-convox-call') callFromDashboard(event);
}
function findCaller(event) {
  if (route.name !== 'leads') return;
  const frame = document.querySelector('.portal-source-page iframe');
  frame?.contentWindow?.postMessage({ type: 'life-convox-find', mobile: event.mobile_number }, window.location.origin);
  minimize();
}
watch(() => route.name, () => { selectedLead.value = ''; });
watch([selectedLead, () => settings.value?.enabled], async ([lead, enabled]) => {
  target.value = null;
  targetError.value = '';
  if (!lead || !enabled) return;
  try {
    const result = await convoxApi.callTarget(lead, controller.signal);
    if (selectedLead.value === lead) target.value = result;
  } catch (e) {
    if (selectedLead.value === lead && e.name !== 'AbortError') targetError.value = e.message;
  }
});
// Keep the iframe alive while ERP refreshes the same user's session data.
const phoneIdentity = computed(previous => {
  if (session.loading) return previous || '';
  return session.user && session.user !== 'Guest' && permitted.value ? session.user : '';
});
watch(phoneIdentity, async (user, _, onCleanup) => {
  sessionGeneration++;
  starting.value = false;
  let cancelled = false;
  onCleanup(() => { cancelled = true; });
  url.value = '';
  phoneConfirmed.value = false;
  settings.value = null;
  selectedLead.value = '';
  events.value = [];
  incoming.value = null;
  seen.clear();
  cursor = '';
  pollError.value = '';
  clearTimeout(timer);
  timer = undefined;
  if (!user) return;
  await loadConfig();
  // Each ERP login attempts SSO when configured; an earlier manual fallback
  // must not permanently disable automatic login for this account.
  if (!cancelled && settings.value?.enabled) await connect(!settings.value.sso_ready);
}, { immediate: true });
function warnBeforeLeaving(event) {
  if (!url.value) return;
  event.preventDefault();
  event.returnValue = '';
}
onMounted(() => {
  window.addEventListener('message', receive);
  window.addEventListener('resize', fitPanel);
  window.addEventListener('beforeunload', warnBeforeLeaving);
});
onBeforeUnmount(() => {
  stopped = true;
  clearTimeout(timer);
  controller.abort();
  window.removeEventListener('message', receive);
  window.removeEventListener('resize', fitPanel);
  window.removeEventListener('beforeunload', warnBeforeLeaving);
});
</script>

<template>
  <div v-if="visible" class="convox-phone">
    <div v-if="dragging || resizing" class="convox-drag-shield" aria-hidden="true"></div>
    <aside v-if="incoming && !open" class="convox-incoming" role="status">
      <strong>Incoming call</strong><span>{{ incoming.mobile_number }}</span>
      <div><button @click="showPhone">Open phone</button><button aria-label="Dismiss incoming call notification" @click="incoming = null">Dismiss</button></div>
    </aside>
    <button ref="launcher" class="convox-launch" :aria-expanded="open" aria-controls="convox-panel" @click="open ? minimize() : showPhone()">
      <span aria-hidden="true">☎</span> ConVox phone
      <span v-if="events.length" class="convox-count">{{ events.length }}</span>
    </button>
    <!-- v-show preserves the softphone session while minimized and across portal routes. -->
    <section v-show="open" id="convox-panel" ref="panel" :style="panelStyle" :class="{ dragging, resizing }" class="convox-panel" tabindex="-1" aria-label="ConVox calling panel" @keydown.esc.stop="minimize">
      <header @pointerdown="startDrag" @pointermove="moveDrag" @pointerup="stopDrag" @pointercancel="stopDrag" @lostpointercapture="stopDrag">
        <div><strong>ConVox phone</strong><small>{{ settings?.agent_id ? `Agent ${settings.agent_id}` : 'Call centre workspace' }} · Drag to move</small></div>
        <div class="convox-tools convox-window-tools">
          <button aria-label="Decrease phone size" title="Make smaller" @click="changeSize(-100)">−</button>
          <button aria-label="Increase phone size" title="Make larger" @click="changeSize(100)">+</button>
          <button aria-label="Reset phone size and position" title="Reset size and position" @click="resetPosition">↺</button>
          <button aria-label="Minimize ConVox phone" title="Minimize phone" @click="minimize">▁</button>
        </div>
      </header>
      <div class="convox-body">
        <p v-if="error" class="convox-error" role="alert">{{ error }}</p>
        <p v-if="notice" class="convox-note" role="status">{{ notice }}</p>
        <p v-if="pollError" class="convox-error" role="status">{{ pollError }}</p>
        <template v-if="!settings"><p>Loading phone settings…</p><button v-if="error" @click="loadConfig">Try again</button></template>
        <div v-if="settings?.setup_issues?.length" class="convox-setup">
          <strong>Connect your ConVox account</strong>
          <p>Complete setup to enable calls:</p>
          <ul><li v-for="issue in settings.setup_issues" :key="issue">{{ issue }}</li></ul>
          <p v-if="settings.can_manage"><a href="/app/system-settings" target="_blank" rel="noopener">Settings</a> · <a :href="settings.user_settings_url" target="_blank" rel="noopener">Agent mapping</a></p>
          <button @click="loadConfig">Check again</button>
        </div>
        <template v-if="settings && !settings.enabled && !settings.setup_issues?.length"><p>ConVox is not enabled for your account yet. Ask your administrator to finish the phone setup.</p><button @click="loadConfig">Check again</button></template>
        <template v-else-if="settings?.enabled">
          <p v-if="!embeddedMicrophoneAvailable" class="convox-error">Microphone unavailable. Open the portal using HTTPS or localhost.</p>
          <div v-if="!url" class="convox-connect"><button :disabled="starting" @click="connect()">{{ starting ? 'Opening phone…' : settings.sso_ready && !preferManual ? 'Connect phone securely' : 'Open ConVox sign-in' }}</button></div>
          <details class="convox-login-options"><summary>Sign-in options</summary>
            <div class="convox-tools"><button :disabled="starting || calling" @click="connect(true, true)">Manual sign-in</button><button v-if="settings.sso_ready" :disabled="starting || calling || dashboardCallPending" @click="connect(false, true)">Retry automatic sign-in</button></div>
          </details>
          <label v-if="url && selectedLead && route.name === 'leads'" class="convox-ready"><input ref="readinessInput" type="checkbox" v-model="phoneConfirmed" :disabled="calling || starting"> <span>Phone Registered, agent Idle — I confirm.</span></label>
          <iframe @load="phoneConfirmed = false" v-if="url" :key="frameVersion" :src="url" sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups" :allow="`microphone ${CONVOX_ORIGIN}`" referrerpolicy="no-referrer" title="ConVox agent softphone" class="convox-widget"></iframe>
          <div v-if="url && route.name === 'leads'" class="convox-call">
            <span>{{ selectedLead ? `Selected lead: ${selectedLead}` : 'Select a lead to call.' }}</span>
            <strong v-if="target">Call to: {{ target.phone_number }}</strong>
            <small v-else-if="selectedLead">{{ targetError || 'Checking saved lead number…' }}</small>
            <button :disabled="!phoneConfirmed || !selectedLead || !settings.click_to_call_ready || calling || dashboardCallPending" @click="callSelected()">{{ calling ? 'Requesting call…' : 'Call selected lead' }}</button>
            <small v-if="!settings.click_to_call_ready">Calling setup incomplete.</small>
          </div>
        </template>
        <div v-if="events.length" class="convox-events"><h3>Recent call updates</h3><article v-for="event in events" :key="event.name"><strong>{{ event.call_status || event.call_type || event.event_type }}</strong><span>{{ event.mobile_number }} <span v-if="event.disposition">· {{ event.disposition }}</span></span><button v-if="route.name === 'leads' && event.mobile_number" @click="findCaller(event)">Find caller in leads</button></article></div>
      </div>
      <button class="convox-resize" aria-label="Resize phone panel" title="Drag to resize, or use arrow keys"
        @pointerdown="startResize" @pointermove="moveResize" @pointerup="stopResize" @pointercancel="stopResize" @lostpointercapture="stopResize"
        @keydown.right.prevent="changeSize(40)" @keydown.down.prevent="changeSize(40)"
        @keydown.left.prevent="changeSize(-40)" @keydown.up.prevent="changeSize(-40)">◢</button>
    </section>
  </div>
</template>

<style scoped>
.convox-setup p{margin-top:10px}.convox-setup ul,.convox-steps{padding-left:20px}.convox-setup li{margin:10px 0;line-height:1.55}.convox-setup a{color:#145b45;text-decoration:underline;font-weight:700}
.convox-phone{position:fixed;right:24px;bottom:20px;z-index:110;font-size:13px;color:#183d2b}.convox-launch{display:flex;align-items:center;gap:9px;background:#164c3f;color:white;border-color:#b8901f;box-shadow:0 5px 22px #12332525;min-height:46px}.convox-incoming{display:grid;gap:8px;background:#fffdf7;border:1px solid #dcd8c9;border-radius:12px;padding:14px;margin-bottom:10px;box-shadow:0 8px 24px #0a281e25}.convox-incoming>div{display:flex;gap:8px}.convox-count{background:#f1d476;color:#173d2b;border-radius:20px;padding:2px 7px}.convox-panel{position:absolute;right:0;bottom:58px;width:min(430px,calc(100vw - 32px));max-height:calc(100dvh - 160px);background:#fffdf7;border:1px solid #dcd8c9;border-radius:15px;box-shadow:0 18px 50px #0a281e40;overflow:auto}.convox-panel>header{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 18px;background:#164c3f;color:white;position:sticky;top:0;z-index:1}.convox-panel header small{display:block;color:#d3e8d7;font-size:11px;margin-top:3px}.convox-panel header button{color:white;background:#ffffff14;padding:4px 12px;font-size:22px}.convox-body{padding:14px}.convox-body p{margin:0 0 12px}.convox-error{padding:10px;background:#fff0e9;color:#8e351d;border-radius:8px}.convox-note{padding:10px;background:#e8f3ec;color:#245c3e;border-radius:8px}.convox-connect button,.convox-call>button{background:#164c3f;color:white;min-height:44px}.convox-widget{width:100%;height:510px;border:1px solid #dde6dc;border-radius:8px;background:white}.convox-hint{font-size:11px;color:#627769;margin-top:8px!important}.convox-call{display:grid;gap:10px;padding:12px 0;border-top:1px solid #e3e7df;overflow-wrap:anywhere}.convox-call small{color:#617566}.convox-events h3{font-size:14px;margin:12px 0}.convox-events article{display:grid;gap:6px;padding:12px 0;border-top:1px solid #e3e7df;overflow-wrap:anywhere}.convox-events article button{justify-self:start}.convox-events article span{color:#52675a;font-size:12px}@media(max-width:600px){.convox-phone{right:12px;bottom:12px}.convox-panel{max-height:calc(100dvh - 135px);bottom:56px}.convox-widget{height:480px}.convox-body{padding:10px}}

.convox-panel{position:fixed;right:24px;bottom:80px;width:min(580px,calc(100vw - 24px));max-height:calc(100dvh - 96px);overflow:hidden;display:flex;flex-direction:column;background:#fff}
.convox-panel{max-width:calc(100vw - 16px)}
.convox-panel>header{flex-shrink:0;cursor:grab;touch-action:none;user-select:none;padding:16px 20px}
.convox-panel.dragging>header{cursor:grabbing}
.convox-panel.dragging iframe,.convox-panel.resizing iframe{pointer-events:none}
.convox-tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.convox-tools button{min-width:36px;min-height:36px}
.convox-body{overflow:auto;padding:18px;line-height:1.5;min-height:0}
.convox-widget{display:block;box-sizing:border-box;height:clamp(360px,62dvh,720px);border-radius:12px}
.convox-login-options{padding:12px 14px;border:1px solid #dce7e0;border-radius:10px;margin-bottom:14px;background:#f5f9f6}
.convox-login-options summary{cursor:pointer;font-weight:600}
.convox-login-options p{margin-top:12px}
.convox-call{margin-top:16px;padding:16px;background:#f5f9f6;border:1px solid #dce7e0;border-radius:12px}
.convox-call strong{font-size:20px;font-variant-numeric:tabular-nums}
@media(max-width:600px){.convox-panel{right:12px;bottom:70px;max-height:calc(100dvh - 86px)}.convox-body{padding:12px}}
.convox-ready{display:flex;align-items:flex-start;gap:12px;padding:14px;margin:0 0 12px;border:1px solid #dce7e0;border-radius:10px;background:#f5f9f6;cursor:pointer}.convox-ready input{margin-top:4px;width:18px;height:18px;flex-shrink:0}.convox-ready small{display:block;color:#627769;margin-top:5px}
.convox-drag-shield{position:fixed;inset:0;z-index:0;cursor:grabbing}.convox-panel{z-index:1}
</style>

<style scoped>
.convox-body{flex:1;padding-bottom:32px}
.convox-widget{height:clamp(420px,65dvh,820px)}
.convox-window-tools{flex-wrap:nowrap;gap:4px}
.convox-panel header .convox-window-tools button{min-width:40px;min-height:40px;padding:4px 8px}
.convox-resize{position:absolute;right:2px;bottom:2px;width:30px;height:30px;padding:0;border:0;border-radius:8px;background:#e8f3ec;color:#164c3f;cursor:nwse-resize;touch-action:none;font-size:22px}
@media(max-width:600px){.convox-panel>header{padding:10px;gap:6px}.convox-panel header small{max-width:150px}.convox-panel header .convox-window-tools button{min-width:32px;padding:2px 6px}}
</style>
