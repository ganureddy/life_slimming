<script setup>
import { computed, onBeforeUnmount, ref } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const frame = ref(null);
const ready = ref(false);
const failed = ref(false);
const attempt = ref(0);
let observer;
let resizeFrame;

const source = computed(() => {
  const query = new URLSearchParams({ module: route.name, embed: '1' });
  for (const [key, value] of Object.entries(route.query)) {
    if (typeof value === 'string') query.set(key, value);
  }
  return `/life_portal_module?${query.toString()}&vue=${attempt.value}`;
});

function fitReport() {
  cancelAnimationFrame(resizeFrame);
  resizeFrame = requestAnimationFrame(() => {
    try {
      const doc = frame.value?.contentDocument;
      if (!doc?.body) return;
      const styleId = 'life-approvals-vue-frame';
      if (!doc.getElementById(styleId)) {
        const style = doc.createElement('style');
        style.id = styleId;
        style.textContent = `
          html,body{width:100%;max-width:100%;min-height:0!important;height:auto!important;margin:0!important;padding:0!important;overflow-x:hidden!important;overflow-y:visible!important;background:#f5f6f3!important}
          body{font-family:Inter,"Segoe UI",Arial,sans-serif!important}
          .navbar,.web-footer{display:none!important}
          #life-dashboard-root.page{width:100%!important;max-width:none!important;margin:0!important;padding:0!important}
          #life-dashboard-root .sheet{border:0!important;border-radius:0!important;box-shadow:none!important}
          .life-load,.life-approval-overlay{position:fixed!important}
          @media(max-width:760px){#life-dashboard-root .rhead{padding-left:16px!important;flex-wrap:wrap!important}#life-dashboard-root .rhead .life-homeback{display:none!important}}
        `;
        doc.head.appendChild(style);
      }
      const root = doc.getElementById('life-dashboard-root') || doc.body;
      const height = Math.max(600, root.scrollHeight + 12);
      if (frame.value && `${height}px` !== frame.value.style.height) frame.value.style.height = `${height}px`;
      ready.value = true;
      failed.value = false;
    } catch {
      failed.value = true;
    }
  });
}

function connectFrame() {
  try {
    const doc = frame.value?.contentDocument;
    if (!doc?.body) return false;
    observer?.disconnect();
    observer = new MutationObserver(fitReport);
    observer.observe(doc.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style'] });
    frame.value.contentWindow.addEventListener('resize', fitReport);
    doc.addEventListener('change', fitReport);
    doc.addEventListener('click', fitReport);
    fitReport();
    return true;
  } catch {
    failed.value = true;
    return false;
  }
}

function loaded() {
  ready.value = false;
  failed.value = false;
  connectFrame();
}

function retry() {
  attempt.value += 1;
  ready.value = false;
  failed.value = false;
}

onBeforeUnmount(() => {
  observer?.disconnect();
  cancelAnimationFrame(resizeFrame);
});
</script>

<template>
  <main class="approvals-page">
    <header class="approvals-page__header">
      <div><span class="approvals-page__eyebrow">WORKSPACE · REQUESTS</span><h1>Approvals</h1><p>Review requests, track approval activity, and manage decisions.</p></div>
      <button type="button" class="approvals-page__refresh" @click="retry">↻ Refresh report</button>
    </header>
    <p v-if="!ready && !failed" class="approvals-page__status" role="status">Loading approvals report…</p>
    <section v-if="failed" class="approvals-page__error" role="alert"><strong>The approvals report could not be opened.</strong><span>Check your connection and try again.</span><button type="button" @click="retry">Try again</button></section>
    <iframe ref="frame" :key="source" :src="source" title="LIFE approvals report" class="approvals-page__frame" :class="{ 'is-ready': ready }" @load="loaded" />
  </main>
</template>

<style scoped>
.approvals-page{min-height:100%;padding:24px clamp(16px,3vw,40px) 40px;background:#f5f6f3;color:#193126}.approvals-page__header{display:flex;align-items:center;justify-content:space-between;gap:20px;margin:0 auto 18px;max-width:1600px}.approvals-page__eyebrow{color:#668071;font-size:11px;font-weight:800;letter-spacing:.14em}.approvals-page h1{margin:5px 0;font-family:Georgia,serif;font-size:clamp(26px,3vw,36px);font-weight:600}.approvals-page__header p{margin:0;color:#68776f}.approvals-page__refresh,.approvals-page__error button{border:1px solid #cbd8cf;border-radius:8px;background:white;color:#14583a;padding:10px 14px;font-weight:700;cursor:pointer}.approvals-page__status{max-width:1600px;margin:0 auto 10px;color:#60746a}.approvals-page__frame{display:block;width:100%;height:600px;border:0;background:#f5f6f3;opacity:0;transition:opacity .15s}.approvals-page__frame.is-ready{opacity:1}.approvals-page__error{max-width:1600px;margin:12px auto;padding:16px;border:1px solid #efc7c1;border-radius:10px;background:#fff7f5;display:flex;align-items:center;gap:12px;flex-wrap:wrap}.approvals-page__error span{color:#6c625f}.approvals-page__error button{margin-left:auto}@media(max-width:600px){.approvals-page{padding:18px 10px 28px}.approvals-page__header{align-items:flex-start;flex-direction:column}.approvals-page__frame{min-height:75vh}}
</style>
