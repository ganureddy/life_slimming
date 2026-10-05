<script setup>
import { computed, ref, watch, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { beginLoading } from "../lib/loading";
const route = useRoute();
const router = useRouter();
const frame = ref(null);
const attempt = ref(0);
const busy = ref(false);
const stalled = ref(false);
let loadWatchdog;
let receivedActivity = false;
let finishLoading = null;
function setLoading(value) {
  clearTimeout(loadWatchdog);
  busy.value = value;
  stalled.value = false;
  if (value) {
    finishLoading?.();
    finishLoading = beginLoading(`Loading ${route.meta.title}`, retry, 50000);
    // A legacy page may never send its final loading event. Stop showing an
    // active global loader after 45 seconds and leave a local retry affordance.
    loadWatchdog = setTimeout(() => {
      busy.value = false;
      stalled.value = true;
      finishLoading?.();
      finishLoading = null;
    }, 45000);
  } else {
    finishLoading?.();
    finishLoading = null;
  }
}
function retry() { receivedActivity = false; attempt.value++; setLoading(true); }
function loaded() {
  let url;
  try {
    const frameWindow = frame.value?.contentWindow;
    url = frameWindow?.location;
    // Some legacy Web Pages apply overflow:hidden to body while initializing
    // full-screen layouts. The frame is the scroll container in this portal,
    // so restore document scrolling after each same-origin navigation.
    const doc = frameWindow?.document;
    if (doc?.head && !doc.getElementById("life-portal-scroll-fix")) {
      const style = doc.createElement("style");
      style.id = "life-portal-scroll-fix";
      style.textContent = "html,body{overflow-y:auto!important;overscroll-behavior-y:auto!important}html{min-height:100%;height:auto!important}body{min-height:100%;height:auto!important}";
      doc.head.appendChild(style);
    }
  } catch { setLoading(false); return; }
  if (url?.pathname === "/life_portal/login") {
    window.location.assign(url.href);
    return;
  }
  // Recover legacy script redirects without leaving a second portal in the frame.
  if (url?.pathname.startsWith("/life_portal/")) {
    router.replace(url.pathname.slice("/life_portal".length) + url.search + url.hash);
    setLoading(false);
    return;
  }
  // Frappe error/login responses do not run the module bridge.
  if (!receivedActivity) setLoading(false);
}
function activity(event) {
  if (event.origin !== window.location.origin || event.source !== frame.value?.contentWindow) return;
  if (event.data?.type === "life-portal:navigate" && typeof event.data.path === "string") {
    const url = new URL(event.data.path, window.location.origin);
    if (url.origin === window.location.origin && url.pathname.startsWith('/life_portal/')) {
      const target = url.pathname.slice('/life_portal'.length) + url.search + url.hash;
      if (router.resolve(target).name !== 'not-found') router.push(target);
    }
    return;
  }
  if (event.data?.type !== "life-portal:loading" || event.data.module !== route.name || typeof event.data.busy !== "boolean") return;
  receivedActivity = true;
  // Repeated activity must not reset the slow-request timer.
  if (busy.value !== event.data.busy) setLoading(event.data.busy);
}
window.addEventListener("message", activity);
onUnmounted(() => { window.removeEventListener("message", activity); clearTimeout(loadWatchdog); finishLoading?.(); });
const source = computed(() => {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(route.query)) {
    if (!["module", "embed"].includes(key)) {
      for (const item of Array.isArray(value) ? value : [value]) {
        if (typeof item === 'string') query.append(key, item);
      }
    }
  }
  query.set("module", route.name);
  query.set("embed", "1");
  return "/life_portal_module?" + query.toString();
});
watch(source, () => { receivedActivity = false; setLoading(true); }, { immediate: true });
</script>

<template>
  <section class="portal-source-page">
    <div v-if="stalled" class="module-stalled" role="alert" aria-live="polite">
      <span>{{ route.meta.title }} is taking longer than expected.</span>
      <button type="button" @click="retry">Retry loading</button>
    </div>
    <iframe ref="frame" :key="source + attempt" :src="source" :title="route.meta.title" @load="loaded"></iframe>
  </section>
</template>

<style scoped>
.portal-source-page{margin:-24px -28px -40px;position:relative;height:calc(100dvh - var(--header-height));min-height:560px;min-width:0;background:#f6f7f9;display:flex;flex-direction:column;overflow:visible}
.module-stalled{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 18px;background:#fff8e8;color:#6e5311;font-size:13px;border-bottom:1px solid #e8d8a8;flex-shrink:0}
.module-stalled button{background:white;border:1px solid #d7c48e;border-radius:6px;padding:6px 12px;color:inherit;cursor:pointer;white-space:nowrap}
iframe{display:block;width:100%;flex:1;min-height:0;border:0;background:white;overflow:auto}
@media(max-width:980px){.portal-source-page{margin:-25px}}
@media(max-width:600px){.portal-source-page{margin:-22px -16px}}
</style>
