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
const externalPhone = ref(false);
function openExternalPhone(event) {
  if (url.value && !window.confirm('Switch to the separate ConVox tab? This closes the embedded phone and may interrupt an active call.')) {
    event.preventDefault();
    return;
  }
  url.value = '';
  externalPhone.value = true;
  notice.value = 'Sign in as your mapped agent in the ConVox tab and set it to Idle. Keep that tab open while calling from this lead workspace.';
}
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
const visible = computed(() => permitted.value && (route.name === 'leads' || Boolean(url.value)));
const controller = new AbortController();
let stopped = false, timer, cursor = '';
const dashboardCallPending = ref(false);
const callRequests = createCallRequests();
const seen = new Set();

async function loadConfig() {
  error.value = '';
  try {
    settings.value = await convoxApi.config(controller.signal);
    cursor = settings.value.server_time;
    if (settings.value.callbacks_ready && !timer) timer = setTimeout(pollEvents, 5000);
  } catch (e) { if (e.name !== 'AbortError') error.value = e.message; }
}
async function pollEvents() {
  timer = undefined;
  try {
    const result = await convoxApi.poll(cursor, controller.signal);
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
    if (e.name === 'AbortError') return;
    pollError.value = 'Call updates are temporarily unavailable. Calling controls remain in the ConVox phone.';
    if ([401, 403].includes(e.status)) return;
  }
  if (!stopped) timer = setTimeout(pollEvents, pollError.value ? 15000 : 5000);
}
async function showPhone() {
  open.value = true;
  if (!settings.value) await loadConfig();
  await nextTick();
  panel.value?.focus();
}
function minimize() {
  open.value = false;
  launcher.value?.focus();
}
async function connect(manual = preferManual.value, reconnect = false) {
  if (starting.value || (url.value && !manual && !reconnect)) return;
  if (url.value && !window.confirm('Reload the phone for sign-in? This will disconnect any active phone session.')) return;
  starting.value = true;
  error.value = '';
  try {
    const result = await convoxApi.widgetSession(controller.signal, manual);
    if (!validWidgetUrl(result.url)) throw new Error('The phone returned an unexpected address. Contact your administrator.');
    url.value = result.url;
    externalPhone.value = false;
    manualLogin.value = result.mode === 'manual';
    preferManual.value = manual;
    try {
      if (manual) localStorage.setItem(loginPreferenceKey(), '1');
      else localStorage.removeItem(loginPreferenceKey());
    } catch { /* Storage can be disabled. */ }
    frameVersion.value++;
    notice.value = 'Allow microphone access when prompted. Sign in and set your agent to Idle before calling.';
  } catch (e) { if (e.name !== 'AbortError') error.value = e.message; }
  finally { starting.value = false; }
}
async function callSelected(lead = selectedLead.value) {
  if (calling.value) return { success: false, status: 'BUSY', message: 'A call request is already in progress.' };
  if (!lead || (!url.value && !externalPhone.value) || !settings.value?.click_to_call_ready) {
    return { success: false, status: 'SETUP_REQUIRED', message: 'Complete the phone setup before calling.' };
  }
  calling.value = true;
  error.value = '';
  notice.value = '';
  // Reuse the request ID after transport errors, preventing a duplicate dial on retry.
  const requestId = callRequests.forLead(lead);
  try {
    const result = await convoxApi.callLead(lead, requestId, controller.signal);
    if (result.success) notice.value = result.message;
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
    if (!url.value && !externalPhone.value) await connect();
    if (!url.value && !externalPhone.value) {
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
watch(selectedLead, async lead => {
  target.value = null;
  targetError.value = '';
  if (!lead) return;
  try {
    const result = await convoxApi.callTarget(lead, controller.signal);
    if (selectedLead.value === lead) target.value = result;
  } catch (e) {
    if (selectedLead.value === lead && e.name !== 'AbortError') targetError.value = e.message;
  }
});
onMounted(() => {
  window.addEventListener('message', receive);
  if (permitted.value) loadConfig();
});
onBeforeUnmount(() => {
  stopped = true;
  clearTimeout(timer);
  controller.abort();
  window.removeEventListener('message', receive);
});
</script>

<template>
  <div v-if="visible" class="convox-phone">
    <aside v-if="incoming && !open" class="convox-incoming" role="status">
      <strong>Incoming call</strong><span>{{ incoming.mobile_number }}</span>
      <div><button @click="showPhone">Open phone</button><button aria-label="Dismiss incoming call notification" @click="incoming = null">Dismiss</button></div>
    </aside>
    <button ref="launcher" class="convox-launch" :aria-expanded="open" aria-controls="convox-panel" @click="open ? minimize() : showPhone()">
      <span aria-hidden="true">☎</span> ConVox phone
      <span v-if="events.length" class="convox-count">{{ events.length }}</span>
    </button>
    <!-- v-show preserves the softphone session while minimized and across portal routes. -->
    <section v-show="open" id="convox-panel" ref="panel" class="convox-panel" tabindex="-1" aria-label="ConVox calling panel" @keydown.esc.stop="minimize">
      <header><div><strong>ConVox phone</strong><small>{{ settings?.agent_id ? `Agent ${settings.agent_id}` : 'Call centre workspace' }}</small></div><button aria-label="Minimize ConVox phone" @click="minimize">−</button></header>
      <div class="convox-body">
        <p v-if="error" class="convox-error" role="alert">{{ error }}</p>
        <p v-if="notice" class="convox-note" role="status">{{ notice }}</p>
        <p v-if="pollError" class="convox-error" role="status">{{ pollError }}</p>
        <template v-if="!settings"><p>Loading phone settings…</p><button v-if="error" @click="loadConfig">Try again</button></template>
        <div v-if="settings?.setup_issues?.length" class="convox-setup">
          <strong>Connect your ConVox account</strong>
          <p>Calling is not ready yet. Your administrator needs to complete these settings on this local site:</p>
          <ul><li v-for="issue in settings.setup_issues" :key="issue">{{ issue }}</li></ul>
          <ol v-if="settings.can_manage" class="convox-steps">
            <li><a href="/app/system-settings" target="_blank" rel="noopener">Open System Settings</a> → ConVox integration. Use automatic token retrieval with the vendor’s token-generation key, enter the confirmed dial prefix, then enable ConVox and save.</li>
            <li><a :href="settings.user_settings_url" target="_blank" rel="noopener">Open your User account</a> → ConVox agent mapping. Enter your real ConVox agent ID, enable ConVox for this user and save.</li>
            <li>For encrypted sign-in, enter the vendor-confirmed SSO secret, IV and IV interpretation in System Settings. Set your mapped email in your User account, then enable SSO.</li>
          </ol>
          <p>Then click <strong>Check again</strong>, open the phone, sign in and set your agent to Idle before clicking Start Call.</p>
          <button @click="loadConfig">Check again</button>
        </div>
        <template v-if="settings && !settings.enabled && !settings.setup_issues?.length"><p>ConVox is not enabled for your account yet. Ask your administrator to finish the phone setup.</p><button @click="loadConfig">Check again</button></template>
        <template v-else-if="settings?.enabled">
          <p><a :href="`${CONVOX_ORIGIN}/ConVoxCCS/`" target="_blank" rel="noopener noreferrer" @click="openExternalPhone">Open ConVox in new tab ↗</a></p>
          <p v-if="externalPhone" class="convox-hint">Phone controls are in the ConVox tab. This portal cannot verify whether that tab is signed in.</p>
          <div v-if="!url" class="convox-connect"><p>Make and receive calls alongside your lead workspace.</p><button :disabled="starting" @click="connect()">{{ starting ? 'Opening phone…' : settings.sso_ready && !preferManual ? 'Connect phone securely' : 'Open ConVox sign-in' }}</button></div>
          <div v-if="settings.sso_ready && !manualLogin" class="convox-connect"><p>If encrypted sign-in is rejected, try your ConVox credentials using manual sign-in.</p><button :disabled="starting || calling" @click="connect(true)">Use manual sign-in</button></div>
          <button v-if="settings.sso_ready" :disabled="starting || calling || dashboardCallPending" @click="connect(false, true)">Sign in with SSO</button>
          <p v-if="url" class="convox-hint">Sign-in mode: {{ manualLogin ? 'Manual credentials' : 'Encrypted SSO' }}</p>
          <iframe v-if="url" :key="frameVersion" :src="url" :allow="`microphone ${CONVOX_ORIGIN}`" referrerpolicy="no-referrer" title="ConVox agent softphone" class="convox-widget"></iframe>
          <button v-if="url && manualLogin" :disabled="starting || calling" @click="connect(true)">Reload manual sign-in</button>
          <p v-if="url" class="convox-hint">Minimizing keeps the phone connected. Reloading this page may interrupt a call.</p>
          <div v-if="(url || externalPhone) && route.name === 'leads'" class="convox-call">
            <span>{{ selectedLead ? `Selected lead: ${selectedLead}` : 'Open a lead summary or follow-up to select a client.' }}</span>
            <strong v-if="target">Call to: {{ target.phone_number }}</strong>
            <small v-else-if="selectedLead">{{ targetError || 'Checking saved lead number…' }}</small>
            <small v-if="target">Uses the saved lead number. Save any mobile number changes before calling.</small>
            <button :disabled="!selectedLead || !settings.click_to_call_ready || calling || dashboardCallPending" @click="callSelected()">{{ calling ? 'Requesting call…' : 'Call selected lead' }}</button>
            <small v-if="!settings.click_to_call_ready">Click-to-call setup is pending. You can use the phone’s manual dialer.</small>
          </div>
        </template>
        <div v-if="events.length" class="convox-events"><h3>Recent call updates</h3><article v-for="event in events" :key="event.name"><strong>{{ event.call_status || event.call_type || event.event_type }}</strong><span>{{ event.mobile_number }} <span v-if="event.disposition">· {{ event.disposition }}</span></span><button v-if="route.name === 'leads' && event.mobile_number" @click="findCaller(event)">Find caller in leads</button></article></div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.convox-setup p{margin-top:10px}.convox-setup ul,.convox-steps{padding-left:20px}.convox-setup li{margin:10px 0;line-height:1.55}.convox-setup a{color:#145b45;text-decoration:underline;font-weight:700}
.convox-phone{position:fixed;right:24px;bottom:20px;z-index:110;font-size:13px;color:#183d2b}.convox-launch{display:flex;align-items:center;gap:9px;background:#164c3f;color:white;border-color:#b8901f;box-shadow:0 5px 22px #12332525;min-height:46px}.convox-incoming{display:grid;gap:8px;background:#fffdf7;border:1px solid #dcd8c9;border-radius:12px;padding:14px;margin-bottom:10px;box-shadow:0 8px 24px #0a281e25}.convox-incoming>div{display:flex;gap:8px}.convox-count{background:#f1d476;color:#173d2b;border-radius:20px;padding:2px 7px}.convox-panel{position:absolute;right:0;bottom:58px;width:min(430px,calc(100vw - 32px));max-height:calc(100dvh - 160px);background:#fffdf7;border:1px solid #dcd8c9;border-radius:15px;box-shadow:0 18px 50px #0a281e40;overflow:auto}.convox-panel>header{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 18px;background:#164c3f;color:white;position:sticky;top:0;z-index:1}.convox-panel header small{display:block;color:#d3e8d7;font-size:11px;margin-top:3px}.convox-panel header button{color:white;background:#ffffff14;padding:4px 12px;font-size:22px}.convox-body{padding:14px}.convox-body p{margin:0 0 12px}.convox-error{padding:10px;background:#fff0e9;color:#8e351d;border-radius:8px}.convox-note{padding:10px;background:#e8f3ec;color:#245c3e;border-radius:8px}.convox-connect button,.convox-call>button{background:#164c3f;color:white;min-height:44px}.convox-widget{width:100%;height:510px;border:1px solid #dde6dc;border-radius:8px;background:white}.convox-hint{font-size:11px;color:#627769;margin-top:8px!important}.convox-call{display:grid;gap:10px;padding:12px 0;border-top:1px solid #e3e7df;overflow-wrap:anywhere}.convox-call small{color:#617566}.convox-events h3{font-size:14px;margin:12px 0}.convox-events article{display:grid;gap:6px;padding:12px 0;border-top:1px solid #e3e7df;overflow-wrap:anywhere}.convox-events article button{justify-self:start}.convox-events article span{color:#52675a;font-size:12px}@media(max-width:600px){.convox-phone{right:12px;bottom:12px}.convox-panel{max-height:calc(100dvh - 135px);bottom:56px}.convox-widget{height:480px}.convox-body{padding:10px}}
</style>
