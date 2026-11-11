<script setup>
defineProps({ summary: Object });
const colours={'New':'p-gy','Contacted':'p-blue','Interested':'p-gold','Appointment Booked':'p-blue','Appointment Missed':'p-red','Visited':'p-teal','Visited - Not Booked':'p-teal','Booked - Payment Pending':'p-gold','Joined Client':'p-green'};
</script>
<template><span v-if="summary" class="cc-journey-chips"><span :class="['pill',colours[summary.milestone]||'p-gy']">{{summary.milestone}}</span><span v-if="summary.last_call_result" class="pill p-gy">📞 {{summary.last_call_result}}</span><span v-if="summary.unreachable_streak>=3" class="pill p-red">⚠ Unreachable {{summary.unreachable_streak}}×</span><span v-if="summary.protected" class="pill p-gold">🔒 {{summary.protected}}</span></span></template>
<style scoped>.cc-journey-chips{display:inline-flex;flex-wrap:wrap;gap:5px;margin:5px 0}</style>
