<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';
import CCWorksheet from '../CCWorksheet.vue';
const {  } = toRefs(inject(ccDashboardKey));
</script>

<template>
<CCWorksheet />
</template>
