<script setup>
import { ref } from 'vue';
import { cleanMobile, maskMobile } from '../../lib/client-info';
defineProps({ value: [String,Number], label: String });
const revealed=ref(false);
</script>
<template><span v-if="value" class="c3-phone" tabindex="0" @mouseenter="revealed=true" @mouseleave="revealed=false" @focus="revealed=true" @blur="revealed=false"><small v-if="label">{{ label }}</small><span>{{ revealed?cleanMobile(value):maskMobile(value) }}</span></span><span v-else>—</span></template>
