<script setup>
import { ref } from 'vue';
const props = defineProps({ title: String, count: Number, defaultOpen: Boolean, red: Boolean });
const open = ref(props.defaultOpen);
</script>
<template>
  <div class="csec" :class="{open}"><button class="csec-h" type="button" :aria-expanded="open" @click="open = !open">{{ title }}<span class="cnt num" :class="{r:red}">{{ count }}</span><span class="car">▼</span></button><div class="csec-b"><slot /></div></div>
</template>
