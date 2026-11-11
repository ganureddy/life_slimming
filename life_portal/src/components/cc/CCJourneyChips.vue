<script setup>
defineProps({ summary: Object });
</script>
<template><span v-if="summary" class="cc-journey-chips"><span class="pill p-green">{{summary.milestone}}</span><span v-if="summary.last_call_result" class="pill p-gy">📞 {{summary.last_call_result}}</span><span v-if="summary.unreachable_streak>=3" class="pill p-red">⚠ Unreachable {{summary.unreachable_streak}}×</span><span v-if="summary.protected" class="pill p-gold">🔒 {{summary.protected}}</span></span></template>
<style scoped>.cc-journey-chips{display:inline-flex;flex-wrap:wrap;gap:5px;margin:5px 0}</style>
