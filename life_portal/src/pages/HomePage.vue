<script setup>
import { computed } from "vue";
import { session, visibleMenu } from "../lib/session";
const groups = computed(() =>
  visibleMenu.value
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => item.id !== "home"),
    }))
    .filter((group) => group.items.length),
);
const date = new Intl.DateTimeFormat("en-IN", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
}).format(new Date());
</script>

<template>
  <section class="home-heading">
    <div>
      <p class="eyebrow">LIFE ENTERPRISE PORTAL</p>
      <h1>Welcome, {{ session.full_name.split(" ")[0] }}</h1>
      <p class="muted">Your workspace for branches, clients and teams.</p>
    </div>
    <span class="date">{{ date }}</span>
  </section>
  <section class="welcome-banner">
    <span class="home-mark" aria-hidden="true">⌂</span>
    <div>
      <h2>Everything starts here</h2>
      <p>Choose a module from the menu to open your workspace.</p>
    </div>
  </section>
  <section v-for="group in groups" :key="group.label" class="module-section">
    <h2 class="section-title">{{ group.label }}</h2>
    <div class="module-grid">
      <RouterLink
        v-for="item in group.items"
        :key="item.id"
        :to="{ name: item.id }"
        class="module-card"
      >
        <span class="module-icon" aria-hidden="true">{{ item.icon }}</span>
        <div>
          <h3>{{ item.label }}</h3>
          <p>{{ item.description }}</p>
        </div>
        <span class="card-arrow" aria-hidden="true">↗</span>
      </RouterLink>
    </div>
  </section>
  <section v-if="!groups.length" class="panel">
    <h2>Your portal workspace</h2>
    <p>
      Your account does not have a portal role configured yet. Contact your
      administrator to enable the appropriate menu.
    </p>
  </section>
</template>
