<script setup>
import { computed, onErrorCaptured, ref, watch } from "vue";
import { useRoute } from "vue-router";
import ConvoxHistoryDialog from "../components/ConvoxHistoryDialog.vue";
import PortalSidebar from "../components/PortalSidebar.vue";
import AccountDialog from "../components/AccountDialog.vue";
import ConvoxPhone from "../components/ConvoxPhone.vue";
import { session, initials, roleLabel, canAccessModule } from "../lib/session";
const route = useRoute();
const allowed = computed(() => route.name === 'not-found' || canAccessModule(route.meta.accessModule || route.name));
const collapsed = ref(false);
const mobileOpen = ref(false);
const account = ref(null);
const pageError = ref("");
function reloadPage() { window.location.reload(); }
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
</script>

<template>
  <div
    class="portal"
    :class="{ rail: collapsed, 'mobile-open': mobileOpen }"
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
      @toggle="collapsed = !collapsed"
      @close="mobileOpen = false"
    />
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
    <ConvoxPhone />
    <ConvoxHistoryDialog />
  </div>
</template>

<style scoped>
.page-render-error{display:flex;align-items:center;gap:16px;max-width:900px;margin:48px auto;padding:24px;border:1px solid #ead4cf;border-radius:12px;background:#fff;color:#26382e}.page-render-error-code{display:grid;place-items:center;flex:0 0 48px;height:48px;border-radius:12px;background:#fff0ed;color:#a13b30;font-size:28px;font-weight:800}.page-render-error h1{margin:0;font-size:20px}.page-render-error p{margin:6px 0 12px;color:#66746c}.page-render-error details{font-size:12px;color:#58665e}.page-render-error code{display:block;max-width:620px;margin-top:6px;overflow-wrap:anywhere;white-space:pre-wrap}.page-render-error button{margin-left:auto;flex-shrink:0;padding:9px 13px;border:1px solid #ccd9cf;border-radius:7px;background:#fff;color:#245d3d;cursor:pointer}@media(max-width:650px){.page-render-error{align-items:flex-start;flex-direction:column;margin:18px auto;padding:17px}.page-render-error button{margin-left:0}}
</style>
