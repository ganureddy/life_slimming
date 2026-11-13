<script setup>
import { computed, onBeforeUnmount, onErrorCaptured, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ConvoxHistoryDialog from "../components/ConvoxHistoryDialog.vue";
import PortalSidebar from "../components/PortalSidebar.vue";
import AccountDialog from "../components/AccountDialog.vue";
import { session, initials, roleLabel, canAccessModule } from "../lib/session";
import { goToPreviousPage } from "../lib/navigation";
const route = useRoute();
const router = useRouter();
const isCrmPage = computed(() => ['leads','leads-native','ccvisit','ccvisit-native','cc-roster','cc-appointments','cc-invoices','cc-live-tv'].includes(route.name) || ['leads','ccvisit'].includes(route.meta.accessModule));
const allowed = computed(() => route.name === 'not-found' || canAccessModule(route.meta.accessModule || route.name));
const collapsed = ref(false);
const mobileOpen = ref(false);
const account = ref(null);
const pageError = ref("");
const routeLoading = ref(false);
let stopBeforeNavigation, stopAfterNavigation, routeLoadingTimer;
function toggleSidebar() {
  collapsed.value = !collapsed.value;
}
function reloadPage() { window.location.reload(); }
function goBack() { goToPreviousPage(router, { name: 'home' }); }
onErrorCaptured((error, _instance, info) => {
  pageError.value = `${error?.message || error || "Unknown page error"} (${info})`;
  return false;
});
watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false;
    pageError.value = "";
  },
);
onMounted(() => {
  stopBeforeNavigation = router.beforeEach((_to, _from, next) => {
    clearTimeout(routeLoadingTimer);
    routeLoading.value = true;
    next();
  });
  stopAfterNavigation = router.afterEach(() => {
    // Keep the transition visible long enough to be perceptible; page-owned
    // loaders continue to represent any slower API work after navigation.
    routeLoadingTimer = setTimeout(() => { routeLoading.value = false; }, 250);
  });
});
onBeforeUnmount(() => {
  clearTimeout(routeLoadingTimer);
  stopBeforeNavigation?.();
  stopAfterNavigation?.();
});
</script>

<template>
  <div
    class="portal"
    :class="{ rail: collapsed, 'mobile-open': mobileOpen, 'crm-workspace': isCrmPage }"
    @keydown.esc="mobileOpen = false"
  >
    <a class="skip-link" href="#main-content">Skip to content</a>
    <header class="topbar">
      <div class="brand-wrap">
        <button
          class="icon-button mobile-toggle"
          aria-label="Toggle navigation"
          :aria-expanded="mobileOpen"
          @click="mobileOpen = !mobileOpen"
        >
          ☰
        </button>
        <RouterLink
          :to="{ name: 'home' }"
          class="brand"
          aria-label="LIFE Portal Home"
        >
          <span class="brand-word"
            >LIFE<span>SLIMMING &amp; COSMETIC CLINIC</span></span
          >
        </RouterLink>
      </div>
      <div class="header-context">
        <span>Workspace</span><strong>{{ route.meta.title }}</strong>
      </div>
      <div class="header-actions">
        <button v-if="route.name !== 'home'" class="portal-back" type="button" @click="goBack">← Back</button>
        <span class="workspace-badge"
          ><i aria-hidden="true"></i> LIFE Portal</span
        >
        <button
          class="user-profile"
          @click="account.open()"
          aria-label="Account options"
        >
          <span class="avatar">{{ initials }}</span
          ><span class="user-info"
            ><strong>{{ session.full_name }}</strong
            ><small>{{ roleLabel }}</small></span
          ><span aria-hidden="true">⌄</span>
        </button>
      </div>
    </header>
    <button
      v-if="mobileOpen"
      class="backdrop"
      aria-label="Close navigation"
      @click="mobileOpen = false"
    ></button>
    <PortalSidebar
      :collapsed="collapsed"
      @toggle="toggleSidebar"
      @close="mobileOpen = false"
    />
    <div v-if="routeLoading" class="portal-route-loader" role="status" aria-live="polite">
      <span aria-hidden="true"></span><strong>Loading page…</strong>
    </div>
    <main id="main-content" class="main-content" tabindex="-1">
      <section v-if="pageError" class="page-render-error" role="alert">
        <div class="page-render-error-code">!</div>
        <div><h1>{{ route.meta.title }} could not be displayed</h1><p>The page stopped while rendering. Reload this page to try again.</p><details><summary>Error details</summary><code>{{ pageError }}</code></details></div>
        <button type="button" @click="reloadPage">Reload page</button>
      </section>
      <RouterView v-else-if="allowed" />
      <section v-else class="panel"><h1>Access unavailable</h1><p>This module is not enabled for your portal role.</p></section>
    </main>
    <AccountDialog ref="account" />
    <ConvoxHistoryDialog />
  </div>
</template>

<style scoped>
.portal-back{border:1px solid #bad3c0;border-radius:9px;background:#fff;color:#1d5a3d;padding:9px 13px;font:inherit;font-weight:700;cursor:pointer;white-space:nowrap}.portal-back:hover{background:#edf7ef;border-color:#72a886}@media(max-width:700px){.portal-back{padding:7px 9px;font-size:12px}}
.portal-route-loader{position:fixed;z-index:1000;inset:0;display:flex;align-items:center;justify-content:center;gap:13px;background:#f5faf7c9;color:#175c37;font-size:17px;backdrop-filter:blur(2px);cursor:wait}.portal-route-loader span{width:30px;height:30px;border:4px solid #a9cfb3;border-top-color:#17663d;border-radius:50%;animation:portal-route-spin .7s linear infinite}@keyframes portal-route-spin{to{transform:rotate(360deg)}}
.page-render-error{display:flex;align-items:center;gap:16px;max-width:900px;margin:48px auto;padding:24px;border:1px solid #ead4cf;border-radius:12px;background:#fff;color:#26382e}.page-render-error-code{display:grid;place-items:center;flex:0 0 48px;height:48px;border-radius:12px;background:#fff0ed;color:#a13b30;font-size:28px;font-weight:800}.page-render-error h1{margin:0;font-size:20px}.page-render-error p{margin:6px 0 12px;color:#66746c}.page-render-error details{font-size:12px;color:#58665e}.page-render-error code{display:block;max-width:620px;margin-top:6px;overflow-wrap:anywhere;white-space:pre-wrap}.page-render-error button{margin-left:auto;flex-shrink:0;padding:9px 13px;border:1px solid #ccd9cf;border-radius:7px;background:#fff;color:#245d3d;cursor:pointer}@media(max-width:650px){.page-render-error{align-items:flex-start;flex-direction:column;margin:18px auto;padding:17px}.page-render-error button{margin-left:0}}
</style>
