<script setup>
defineProps({ counts: { type: Object, default: () => ({}) }, onOpen: { type: Function, required: true } });
</script>
<template>
  <div class="stock-cards stock-request-summary">
    <button v-for="[key,label] in [['pending','Pending review'],['approved','Approved / awaiting release'],['released','Released / in transit'],['rejected','Rejected']]" :key="key" @click="onOpen(key)">
      <span>{{ label }}</span><strong>{{ counts[key] || 0 }}</strong>
    </button>
  </div>
</template>
