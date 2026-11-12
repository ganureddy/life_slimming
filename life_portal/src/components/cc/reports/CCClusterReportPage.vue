<script setup>
import { computed, inject } from 'vue';
import {useRouter} from 'vue-router';
import {reportGroups} from '../../../lib/cc-visit-report';
import { branchOf, visitStatus, downloadCsv } from '../../../lib/cc';
import { agentReportKey } from '../../../lib/cc-agent-report-context';
const ctx = inject(agentReportKey);
const { rows, applied, loading, error, openLead } = ctx;
const router=useRouter();
const groups = computed(() => reportGroups(rows.value||[],'branch').map(row=>({...row,branch:row.key})));
function filterBranch(branch){ctx.branch.value=branch;router.push({name:'ccvisit',query:{from:applied.value?.from_date,to:applied.value?.to_date}});}
const columns = [
  {key:'branch',label:'Branch'}, {key:'appointments',label:'Appointments'},
  {key:'visits',label:'Visits'}, {key:'booked',label:'Booked'},
  {key:'notBooked',label:'Visited · Not booked'}, {key:'pending',label:'Pending'},
  {key:'showup',label:'Show-up %',value:r=>r.appointments?Math.round(r.visits*100/r.appointments)+'%':'0%'},
  {key:'conversion',label:'Booking %',value:r=>r.visits?Math.round(r.booked*100/r.visits)+'%':'0%'},
];
function exportReport(){downloadCsv('cc-cluster-report.csv',columns,groups.value)}
</script>
<template>
  <section class="cc-card cc-cluster-report">
    <header class="cc-report-section-head"><div><h2>🧩 Cluster Report</h2><p>Branch ownership and conversion roll-up for the selected visit range.</p></div><button :disabled="loading||!applied||!groups.length" @click="exportReport">Export CSV</button></header>
    <p v-if="error" class="cc-error" role="alert">{{ error }}</p>
    <p v-if="!loading&&!groups.length" class="cc-empty">No branch visits match the selected range.</p>
    <div v-else class="cc-table"><table><thead><tr><th v-for="c in columns" :key="c.key">{{ c.label }}</th><th>Actions</th></tr></thead><tbody><tr v-for="row in groups" :key="row.branch"><th>{{ row.branch }}</th><td>{{ row.appointments }}</td><td>{{ row.visits }}</td><td>{{ row.booked }}</td><td>{{ row.notBooked }}</td><td>{{ row.pending }}</td><td>{{ row.appointments?Math.round(row.visits*100/row.appointments):0 }}%</td><td>{{ row.visits?Math.round(row.booked*100/row.visits):0 }}%</td><td><button @click="filterBranch(row.branch)">Filter branch</button></td></tr></tbody></table></div>
  </section>
</template>
<style scoped src="../../../styles/cc-agent-report.css"></style>
