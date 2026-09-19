<template>
  <section class="panel module-placeholder">
    <p class="eyebrow">404</p>
    <h1>Page not found</h1>
    <p>The page you requested does not exist.</p>
    <RouterLink class="primary" :to="{ name: 'home' }">Back to Home</RouterLink>
  </section>
</template>
