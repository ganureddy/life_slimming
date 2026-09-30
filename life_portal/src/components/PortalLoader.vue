<script setup>
defineProps({ label: { type: String, default: "Loading your workspace" }, detail: { type: String, default: "Preparing LIFE ERP…" } });
</script>
<template>
  <div class="life-loader" role="status" aria-live="polite">
    <div class="life-loader-mark" aria-hidden="true"><span></span><b>L</b></div>
    <strong>{{ label }}</strong><p>{{ detail }}</p>
    <div class="life-loader-track" aria-hidden="true"><i></i></div>
    <slot />
  </div>
</template>
<style scoped>
.life-loader{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:32px;text-align:center;color:#174d2b;background:radial-gradient(ellipse at top,#edf5ee,transparent 70%),#fff;min-height:240px;border-radius:20px}.life-loader p{margin:0;color:#627367;font-size:13px}.life-loader strong{font-size:18px}.life-loader-mark{position:relative;display:grid;place-items:center;width:68px;height:68px;margin-bottom:8px}.life-loader-mark b{font:700 32px Georgia;color:#174d2b}.life-loader-mark span{position:absolute;inset:0;border:3px solid #e4ece5;border-top-color:#b99a50;border-right-color:#174d2b;border-radius:50%;animation:life-spin 1.2s linear infinite}.life-loader-track{width:160px;height:3px;background:#e5eee7;overflow:hidden;border-radius:4px}.life-loader-track i{display:block;width:45%;height:100%;background:linear-gradient(90deg,#174d2b,#c6ac69);animation:life-track 1.6s ease-in-out infinite}@keyframes life-spin{to{transform:rotate(360deg)}}@keyframes life-track{0%{transform:translateX(-110%)}100%{transform:translateX(330%)}}@media(prefers-reduced-motion:reduce){.life-loader-mark span,.life-loader-track i{animation:none}}
</style>
