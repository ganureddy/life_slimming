<script setup>
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from "vue";
import { session, loginUrl } from "../lib/session";
import { call } from "../lib/api";
import { createIdleTimer } from "../lib/idle";
const emit = defineEmits(["expired"]);
const seconds = ref(0), expired = ref(false), dialog = ref(null);
const countdown = computed(() => Math.floor(seconds.value / 60) + ":" + String(seconds.value % 60).padStart(2, "0"));
const key = "life-portal-idle:" + session.user + ":" + session.session_id;
let timer, interval, observer, lastEvent = 0, memory = null;
const cleanups = [];
const bound = new WeakSet();
function read() { try { return JSON.parse(localStorage.getItem(key)) || memory; } catch { return memory; } }
function write(value) { memory = value; try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Memory fallback when storage is unavailable. */ } }
async function logout() {
  expired.value = true;
  emit("expired");
  try { sessionStorage.setItem("life-portal-logout-pending", "1"); } catch { /* Logout still runs. */ }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    await call("logout", {}, { csrfToken: session.csrf_token, signal: controller.signal });
    try { sessionStorage.removeItem("life-portal-logout-pending"); } catch { /* No storage. */ }
  } catch { /* Login retries invalidating the session before allowing entry. */ }
  finally { clearTimeout(timeout); window.location.replace(loginUrl() + "&reason=idle"); }
}
function activity(event) {
  if (event && !event.isTrusted) return;
  if (Date.now() - lastEvent < 1000) return;
  lastEvent = Date.now();
  timer?.activity();
}
function bind(doc) {
  if (!doc || bound.has(doc)) return;
  bound.add(doc);
  for (const name of ["pointerdown", "pointermove", "keydown", "wheel", "touchstart", "input"]) {
    doc.addEventListener(name, activity, { capture: true, passive: true });
    cleanups.push(() => doc.removeEventListener(name, activity, true));
  }
  function frames() {
    for (const frame of doc.querySelectorAll("iframe")) {
      try { bind(frame.contentDocument); } catch { /* External widgets cannot expose their DOM. */ }
    }
  }
  doc.addEventListener("load", frames, true);
  cleanups.push(() => doc.removeEventListener("load", frames, true));
  frames();
}
function check() { timer?.check(); }
watch(() => seconds.value > 0 || expired.value, async (show) => {
  await nextTick();
  if (show && !dialog.value?.open) dialog.value?.showModal();
  else if (!show) dialog.value?.close();
});
onMounted(() => {
  timer = createIdleTimer({ read, write, warning: value => seconds.value = value, expire: logout });
  bind(document);
  observer = new MutationObserver(() => { for (const f of document.querySelectorAll("iframe")) { try { bind(f.contentDocument); } catch { /* External widget. */ } } });
  observer.observe(document.body, { childList: true, subtree: true });
  window.addEventListener("storage", check);
  window.addEventListener("focus", check);
  document.addEventListener("visibilitychange", check);
  interval = setInterval(check, 1000);
  check();
});
onUnmounted(() => {
  clearInterval(interval); observer?.disconnect(); cleanups.forEach(fn => fn());
  window.removeEventListener("storage", check); window.removeEventListener("focus", check);
  document.removeEventListener("visibilitychange", check);
});
</script>
<template>
  <dialog ref="dialog" class="idle-dialog" aria-labelledby="idle-title" aria-describedby="idle-description" @cancel.prevent>
    <span class="idle-symbol" aria-hidden="true">◷</span>
    <h2 id="idle-title">{{ expired ? "Signing you out" : "ERP is going to auto logout" }}</h2>
    <p id="idle-description">{{ expired ? "You have been inactive for one hour. Redirecting to sign in…" : "Your session is inactive. Continue using ERP to stay signed in." }}</p>
    <template v-if="!expired"><div class="idle-countdown" role="timer" aria-label="Time until automatic logout">{{ countdown }}</div><button class="primary" autofocus @click="timer.activity()">Stay signed in</button></template>
  </dialog>
</template>
<style scoped>
.idle-dialog{max-width:440px;width:calc(100% - 32px);border:1px solid #d5ddcf;border-radius:22px;padding:32px;text-align:center;box-shadow:0 24px 90px #12291e33;color:#173d2b}.idle-dialog::backdrop{background:#102b2066;backdrop-filter:blur(5px)}.idle-dialog h2{font-size:23px}.idle-dialog p{color:#617068;line-height:1.6}.idle-symbol{font-size:40px;color:#ad8b38}.idle-countdown{font-size:44px;font-weight:700;font-variant-numeric:tabular-nums;margin:20px;color:#174d2b}.idle-dialog button{width:100%;min-height:46px}
</style>
