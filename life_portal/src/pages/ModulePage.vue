<script setup>
import { useRoute } from "vue-router";
const route = useRoute();
</script>

<template>
  <section class="panel module-placeholder">
    <span class="placeholder-icon" aria-hidden="true">{{ route.meta.icon }}</span>
    <p>{{ route.meta.description }}</p>
    <p class="muted">This module is not connected yet.</p>
    <RouterLink class="primary" :to="{ name: 'home' }">Back to Home</RouterLink>
  </section>
</template>
