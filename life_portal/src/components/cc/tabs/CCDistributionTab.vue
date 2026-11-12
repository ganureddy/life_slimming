<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';
import CCDistribution from '../CCDistribution.vue';
const { load } = toRefs(inject(ccDashboardKey));
</script>

<template>
<CCDistribution @changed="load(1)" />
</template>
