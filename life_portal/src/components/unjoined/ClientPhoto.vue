<script setup>
import { computed, ref, watch } from 'vue';
import { sameOriginFile } from '../../lib/unjoined';
const props = defineProps({ value: String, large: Boolean });
const failed = ref(false);
const url = computed(() => sameOriginFile(props.value, window.location.origin));
watch(url, () => failed.value = false);
</script>

<template>
  <div class="uj-photo" :class="{ 'uj-photo-large': large }">
    <img v-if="url && !failed" :src="url" loading="lazy" alt="Client photo" @error="failed = true">
    <span v-else>Image not attached</span>
  </div>
</template>
