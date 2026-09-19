<script setup>
import { watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import PortalLayout from "./layouts/PortalLayout.vue";
import { session, loadSession, loginUrl } from "./lib/session";
const route = useRoute();
const router = useRouter();
watch(
  () => route.meta.public,
  async (isPublic) => {
    if (isPublic) return;
    await loadSession();
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
    Loading LIFE Portal…
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
  <PortalLayout v-else />
</template>
