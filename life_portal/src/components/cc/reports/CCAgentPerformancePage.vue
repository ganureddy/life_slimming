<script setup>
import { inject } from 'vue';
import { agentReportKey } from '../../../lib/cc-agent-report-context';
import CCActivityReport from '../CCActivityReport.vue';
import CCNoFollowupReport from '../CCNoFollowupReport.vue';
import CCUntouchedReport from '../CCUntouchedReport.vue';
import CCDataTable from '../CCDataTable.vue';
import CCPager from '../CCPager.vue';
import CCAgentPerformanceView from './CCAgentPerformanceView.vue';
const { from, to, rows, page, applied, untouchedData, financialPage, columns, agents, pages, reportTab, agentSubtab, openLead, agentRows, performanceGroups, agentColumns } = inject(agentReportKey);
</script>
<template><KeepAlive :max="4">  <CCActivityReport v-if="applied&&reportTab==='agents'&&agentSubtab==='convox'" :from="applied.from_date" :to="applied.to_date" channel="convox" @open="openLead"/>
  <CCNoFollowupReport v-else-if="applied&&reportTab==='agents'&&agentSubtab==='nofollowup'" @open="openLead"/>
  <CCUntouchedReport v-else-if="applied&&reportTab==='agents'&&agentSubtab==='untouched'" :from="applied.from_date" :to="applied.to_date" @open="openLead" @loaded="untouchedData=$event"/><CCAgentPerformanceView v-else-if="applied&&reportTab==='agents'"/></KeepAlive></template>
<style scoped src="../../../styles/cc-agent-report.css"></style>
