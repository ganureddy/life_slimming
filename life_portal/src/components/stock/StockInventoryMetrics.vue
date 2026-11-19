<script setup>
defineProps({ metrics: { type: Object, required: true }, format: { type: Function, required: true }, isHo: Boolean });
</script>
<template>
  <div class="stock-cards stock-inventory-metrics">
    <div><span>Distinct stocked items</span><strong>{{ metrics.items }}</strong></div>
    <div><span>Total quantity on hand</span><strong>{{ format(metrics.qty) }}</strong></div>
    <div><span>Zero stock rows</span><strong>{{ metrics.zero }}</strong></div>
    <div><span>Low stock rows · ≤ 5</span><strong>{{ metrics.low }}</strong></div>
    <div v-if="isHo"><span>Dead stock · no movement 180 days</span><strong>{{ metrics.dead }}</strong></div>
    <div><span>Damaged stock</span><strong>{{ metrics.damaged ?? '—' }}</strong><small>register totals</small></div>
    <div><span>Missing stock</span><strong>{{ metrics.missing ?? '—' }}</strong><small>register totals</small></div>
    <div><span>Item masters</span><strong>{{ metrics.itemMasters ?? metrics.items }}</strong><small>stock items</small></div>
  </div>
</template>
