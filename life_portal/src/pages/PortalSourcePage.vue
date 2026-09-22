<script setup>
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { visibleMenu } from "../lib/session";
const route = useRoute();
const loading = ref(true);
const allowed = computed(() => visibleMenu.value.some(group => group.items.some(item => item.id === route.name)));
const source = computed(() => {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(route.query)) {
    if (key !== "module" && typeof value === "string") query.set(key, value);
  }
  query.set("module", route.name);
  return "/life_portal_module?" + query.toString();
});
watch(source, () => { loading.value = true; });
</script>

<template>
  <section v-if="allowed" class="portal-source-page">
    <p v-if="loading" role="status" class="source-loading">Loading {{ route.meta.title }}…</p>
    <iframe :key="source" :src="source" :title="route.meta.title" @load="loading = false"></iframe>
  </section>
  <section v-else class="panel"><h1>Access unavailable</h1><p>This module is not enabled for your portal role.</p></section>
</template>

<style scoped>
.portal-source-page{margin:-24px -28px -40px;position:relative;height:calc(100dvh - var(--header-height));min-height:560px;background:#f6f7f9}
iframe{display:block;width:100%;height:100%;border:0;background:white}
.source-loading{position:absolute;top:12px;left:20px;padding:8px 16px;border-radius:8px;background:white;z-index:1}
@media(max-width:980px){.portal-source-page{margin:-25px}}
@media(max-width:600px){.portal-source-page{margin:-22px -16px}}
</style>
