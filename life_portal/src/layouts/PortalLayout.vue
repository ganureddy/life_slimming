<script setup>
import { ref, watch } from "vue";
import { useRoute } from "vue-router";
import PortalSidebar from "../components/PortalSidebar.vue";
import AccountDialog from "../components/AccountDialog.vue";
import { session, initials, roleLabel } from "../lib/session";
const route = useRoute();
const collapsed = ref(false);
const mobileOpen = ref(false);
const account = ref(null);
watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false;
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
        <a
          class="icon-button healthcare-link"
          href="/app/healthcare"
          aria-label="Go to Healthcare"
          title="Go to Healthcare"
          >←</a
        >
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
      <RouterView />
    </main>
    <AccountDialog ref="account" />
  </div>
</template>
