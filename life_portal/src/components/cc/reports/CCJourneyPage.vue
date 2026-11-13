<script setup>
import {inject} from 'vue';
import {agentReportKey} from '../../../lib/cc-agent-report-context';
import CCJourneyReport from '../CCJourneyReport.vue';
const {applied,openLead,activityData}=inject(agentReportKey);
</script>
<template><CCJourneyReport v-if="applied" :from="applied.from_date" :to="applied.to_date" @open="openLead" title="Lead Journey"/></template>
