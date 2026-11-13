<script setup>
import {computed,inject} from 'vue';
import {useRoute} from 'vue-router';
import {agentReportKey} from '../../../lib/cc-agent-report-context';
import {watchVisibleReport} from '../../../lib/cc-visible-report';
import {packageSplit} from '../../../lib/cc-report-financials';
import {branchOf,visitStatus} from '../../../lib/cc';
const route=useRoute(),context=inject(agentReportKey);
const {applied,filtered,branch,agent,financial,financialLoading,financialError,loadFinancial,openDrill,grouping}=context;
watchVisibleReport(()=>[applied.value?.from_date,applied.value?.to_date],()=>route.meta.reportTab==='visits'&&!!applied.value,loadFinancial,()=>!!financial.value);
const money=computed(()=>packageSplit((financial.value?.cc_invoice_report_summary?.rows||[]).filter(r=>(!branch.value||branchOf(r)===branch.value)&&(!agent.value||r.lead_owner===agent.value)),applied.value?.from_date,applied.value?.to_date));
const cards=computed(()=>{const count=status=>filtered.value.filter(r=>visitStatus(r)===status).length,b=count('Visited-BKD'),nb=count('Visited-Not BKD'),pending=count('Visited'),visits=b+nb+pending;return [['Total Appointments',filtered.value.length,'appointments'],['Visit but Pending in Branch',pending,'visits'],['Total Visit Count',b+nb,'visits'],['Visited + Total Visit Count',visits,'visits'],['Booked',b,'booked'],['Not Booked',nb,'notBooked'],['Not Visited',count('Not Visited'),'noShow'],['Scheduled / Awaiting Visit',count('Appt Fixed'),'awaiting'],['New Package With GST',money.value.withGst,'money'],['New Package Without GST',money.value.withoutGst,'money'],['New Package Paid Amount',money.value.paid,'money'],['Old Package Paid Amount',money.value.oldPackagePaid,'money'],['Old Package Paid + New Package Paid',money.value.paid+money.value.oldPackagePaid,'money'],['New Package Balance Amount',money.value.balance,'money'],['Booking Conversion',visits?Math.round(b/visits*100)+'%':'—','ratio']];});
function open(key){if(['money','ratio'].includes(key))return;grouping.value='branch';openDrill(branch.value,key);}
</script>
<template><section class="branch-summary-cards" aria-label="Branch report totals"><button v-for="[label,value,key] in cards" :key="label" class="kpi" :disabled="key==='money'||key==='ratio'" @click="open(key)"><b>{{key==='money'?(financialLoading?'…':'₹'+Number(value).toLocaleString('en-IN')):value}}</b><span>{{label}}</span></button><p v-if="financialError" role="alert">Financial details: {{financialError}} <button @click="loadFinancial">Retry</button></p></section></template>
<style scoped>.branch-summary-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:9px;margin:14px 0}.branch-summary-cards .kpi{display:grid;gap:5px;text-align:left;border:1px solid #d5b66b;border-top:3px solid #216640;border-radius:9px;background:#fffdf7;color:#16402d;padding:13px;font:inherit}.branch-summary-cards .kpi:disabled{opacity:1}.kpi b{font-size:23px}.kpi span{font-size:11px}.branch-summary-cards>p{grid-column:1/-1}</style>
