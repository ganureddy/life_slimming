<script setup>
defineProps({ items: { type: Array, required: true }, activeView: { type: String, required: true }, requestTotal: { type: Number, default: 0 } });
defineEmits(['select']);
</script>

<template>
  <nav class="stock-nav" aria-label="Stock management modules">
    <button v-for="[id,label] in items" :key="id" :class="{active:activeView===id}" @click="$emit('select', id)">{{ label }}<b v-if="id==='requests'">{{ requestTotal }}</b></button>
  </nav>
</template>
