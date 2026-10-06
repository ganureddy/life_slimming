<script setup>
defineProps({ page: Number, pages: Number, busy: Boolean });
defineEmits(['change']);
</script>
<template><nav class="cc-pager" aria-label="Table pagination"><button :disabled="busy || page <= 1" @click="$emit('change', page - 1)">Previous</button><span>Page {{ page }} / {{ Math.max(1, pages) }}</span><button :disabled="busy || page >= pages" @click="$emit('change', page + 1)">Next</button></nav></template>
