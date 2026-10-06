<script setup>
import { useRoute } from "vue-router";
const route = useRoute();
</script>

<template>
  <section class="panel module-placeholder">
    <template v-if="route.name === 'users'">
      <h1>Users testing</h1>
    </template>
    <template v-else>
    <span class="placeholder-icon" aria-hidden="true">{{ route.meta.icon }}</span>
    <p>{{ route.meta.description }}</p>
    <p class="muted">This module is not connected yet.</p>
    <RouterLink class="primary" :to="{ name: 'home' }">Back to Home</RouterLink>
    </template>
  </section>
</template>
