<script setup>
import { routeLoading } from "./router";
import { computed, onUnmounted, ref, watch } from "vue";
import { workspaceLoading, loadingDetail } from "./lib/loading";
import { useRoute, useRouter } from "vue-router";
import PortalLoader from "./components/PortalLoader.vue";
import IdleSession from "./components/IdleSession.vue";
import PortalLayout from "./layouts/PortalLayout.vue";
import { session, loadSession, loginUrl } from "./lib/session";
const idleExpired = ref(false);
const busy = computed(() => routeLoading.value || workspaceLoading.value);
const slow = ref(false);
let slowTimer;
watch(busy, (value) => {
  clearTimeout(slowTimer);
  slow.value = false;
  if (value) slowTimer = setTimeout(() => { slow.value = true; }, 15000);
});
onUnmounted(() => clearTimeout(slowTimer));
const route = useRoute();
const router = useRouter();
watch(
  () => route.meta.public,
  async (isPublic) => {
    if (isPublic) { idleExpired.value = false; return; }
    if (!session.user) await loadSession();
    if (session.status === 403 && !route.meta.public) {
      router.replace({
        name: "login",
        query: {
          "redirect-to": window.location.pathname + window.location.search,
        },
      });
    }
  },
  { immediate: true },
);
</script>

<template>
  <RouterView v-if="route.meta.public" />
  <div v-else-if="session.loading" class="startup" role="status">
    <PortalLoader />
  </div>
  <div v-else-if="session.error" class="startup">
    <section class="panel">
      <h1>LIFE Portal</h1>
      <p role="alert">{{ session.error }}</p>
      <div class="actions">
        <a class="primary" :href="loginUrl()">Sign in</a
        ><button @click="loadSession">Try again</button>
      </div>
    </section>
  </div>
  <template v-else>
    <PortalLayout v-if="!idleExpired" />
    <div v-if="busy && !idleExpired" class="route-loader"><PortalLoader :label="loadingDetail.label || 'Opening page'" :detail="slow ? 'This is taking longer than expected.' : 'Loading your workspace…'"><button v-if="slow && loadingDetail.retry" class="primary" @click="loadingDetail.retry">Retry loading</button></PortalLoader></div>
    <IdleSession @expired="idleExpired = true" />
  </template>
</template>

<style scoped>
.route-loader{position:fixed;inset:var(--header-height,64px) 0 0;display:grid;place-items:center;background:#f4f7f4eb;z-index:1000}
</style>
