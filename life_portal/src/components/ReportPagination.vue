<script setup>
import { computed } from 'vue';
const props = defineProps({ modelValue: { type: Number, default: 1 }, total: { type: Number, default: 1 } });
const emit = defineEmits(['update:modelValue']);
const pages = computed(() => { const start = Math.max(1, props.modelValue - 3), end = Math.min(props.total, start + 6); return Array.from({ length: end - start + 1 }, (_, index) => start + index); });
</script>
<template>
  <div v-if="total > 1" class="wl-pagination">
    <button class="wl-page-btn" :disabled="modelValue === 1" @click="emit('update:modelValue', modelValue - 1)">Prev</button>
    <button v-for="page in pages" :key="page" class="wl-page-btn" :class="{ active: page === modelValue }" :aria-current="page === modelValue ? 'page' : undefined" @click="emit('update:modelValue', page)">{{ page }}</button>
    <button class="wl-page-btn" :disabled="modelValue === total" @click="emit('update:modelValue', modelValue + 1)">Next</button>
  </div>
</template>
