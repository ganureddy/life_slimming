<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';
import CCLeadUpdates from '../CCLeadUpdates.vue';
const { openDetail } = toRefs(inject(ccDashboardKey));
</script>

<template>
<CCLeadUpdates @open="id=>openDetail({name:id})" />
</template>
