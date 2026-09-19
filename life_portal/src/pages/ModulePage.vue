<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { visibleMenu } from "../lib/session";
const route = useRoute();
const allowed = computed(() =>
  visibleMenu.value.some((group) =>
    group.items.some((item) => item.id === route.name),
  ),
);
</script>

<template>
  <section class="panel module-placeholder">
    <template v-if="allowed"
      ><span class="placeholder-icon" aria-hidden="true">{{
        route.meta.icon
      }}</span>
      <p class="eyebrow">LIFE PORTAL</p>
      <h1>{{ route.meta.title }}</h1>
      <p>{{ route.meta.description }}</p>
      <p class="muted">
        This page is not available in the new portal yet.
      </p></template
    >
    <template v-else
      ><h1>Access unavailable</h1>
      <p>This module is not enabled for your portal role.</p></template
    >
    <RouterLink class="primary" :to="{ name: 'home' }">Back to Home</RouterLink>
  </section>
</template>
