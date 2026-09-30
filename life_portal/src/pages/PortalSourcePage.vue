<script setup>
import { computed, ref, watch, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { beginLoading } from "../lib/loading";
const route = useRoute();
const frame = ref(null);
const attempt = ref(0);
let finish;
let receivedActivity = false;
function setLoading(busy) {
  if (busy && !finish) finish = beginLoading(`Loading ${route.meta.title}`, retry);
  if (!busy) { finish?.(); finish = null; }
}
function retry() { receivedActivity = false; attempt.value++; setLoading(true); }
function loaded() {
  const url = frame.value?.contentWindow?.location;
  if (url?.pathname === "/life_portal/login") {
    window.location.assign(url.href);
    return;
  }
  // Frappe error/login responses do not run the module bridge.
  if (!receivedActivity) setLoading(false);
}
function activity(event) {
  if (event.origin !== window.location.origin || event.source !== frame.value?.contentWindow) return;
  if (event.data?.type !== "life-portal:loading" || event.data.module !== route.name || typeof event.data.busy !== "boolean") return;
  receivedActivity = true;
  setLoading(event.data.busy);
}
window.addEventListener("message", activity);
onUnmounted(() => { window.removeEventListener("message", activity); finish?.(); });
const source = computed(() => {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(route.query)) {
    if (!["module", "embed"].includes(key) && typeof value === "string") query.set(key, value);
  }
  query.set("module", route.name);
  query.set("embed", "1");
  return "/life_portal_module?" + query.toString();
});
watch(source, () => { receivedActivity = false; setLoading(false); setLoading(true); }, { immediate: true });
</script>

<template>
  <section class="portal-source-page">
    <iframe ref="frame" :key="source + attempt" :src="source" :title="route.meta.title" @load="loaded"></iframe>
  </section>
</template>

<style scoped>
.portal-source-page{margin:-24px -28px -40px;position:relative;height:calc(100dvh - var(--header-height));min-height:560px;background:#f6f7f9}
iframe{display:block;width:100%;height:100%;border:0;background:white}
@media(max-width:980px){.portal-source-page{margin:-25px}}
@media(max-width:600px){.portal-source-page{margin:-22px -16px}}
</style>
