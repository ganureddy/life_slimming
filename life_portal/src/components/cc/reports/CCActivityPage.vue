<script setup>
import {inject} from 'vue';
import {agentReportKey} from '../../../lib/cc-agent-report-context';
import CCActivityReport from '../CCActivityReport.vue';
const {applied,openLead,activityData}=inject(agentReportKey);
</script>
<template><CCActivityReport v-if="applied" :from="applied.from_date" :to="applied.to_date" @open="openLead" @loaded="activityData=$event"/></template>
