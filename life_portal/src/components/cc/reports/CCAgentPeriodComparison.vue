<script setup>
import {computed,ref} from 'vue';
import {businessCycle} from '../../../lib/cc-visit-report';
import {agentPeriodMetrics,scorecardMetrics} from '../../../lib/cc-report-scorecard';
import {requestVisitReport} from '../../../api/cc-visit-report';
import {downloadCsv} from '../../../lib/cc';
import CCDataTable from '../CCDataTable.vue';
const props=defineProps({anchor:String,owners:{default:null}}),results=ref([]),busy=ref(false),error=ref(''),completed=ref(0),loadedAnchor=ref('');
async function load(){if(busy.value)return;const anchor=props.anchor,refresh=loadedAnchor.value===anchor&&results.value.length===3;busy.value=true;error.value='';completed.value=0;const next=[];try{for(const offset of [-2,-1,0]){const [from_date,to_date]=businessCycle(anchor,offset);const data=await requestVisitReport({from_date,to_date},undefined,refresh);next.push({from_date,to_date,data});completed.value++;}results.value=next;loadedAnchor.value=anchor;}catch(e){error.value=e.message;}finally{busy.value=false;}}
const periods=computed(()=>loadedAnchor.value===props.anchor?results.value:[]);
const metrics=computed(()=>scorecardMetrics.map(([key,label,type])=>({key,label,...Object.fromEntries(periods.value.map((period,index)=>{const value=agentPeriodMetrics(period.data,period,props.owners)[key];return ['period'+index,period.data?.truncated?'Partial data':type==='percent'?value.toFixed(1)+'%':(type==='money'?'₹':'')+Math.round(value).toLocaleString('en-IN')];}))})));
const columns=computed(()=>[{key:'label',label:'Metric'},...periods.value.map((p,index)=>({key:'period'+index,label:p.from_date+' → '+p.to_date}))]);
</script>
<template><details open class="arx-sec cc-agent-periods"><summary class="arx-sh">📆 Three-Month Business Comparison</summary><div class="cc-report-tools"><button :disabled="busy" @click="load">{{busy?'Loading '+completed+' / 3 periods…':periods.length?'Refresh comparison':'Load comparison'}}</button><button :disabled="!periods.length||periods.some(p=>p.data.truncated)" @click="downloadCsv('agent-three-months.csv',columns,metrics)">Export CSV</button></div><p v-if="error" class="cc-error" role="alert">{{error}}</p><p class="arx-note">Sixth-to-fifth business months. Uses the current agent selection and the shared report cache; other tabs reuse these responses.</p><CCDataTable v-if="periods.length" :columns="columns" :rows="metrics"/></details></template>
<style scoped>.cc-report-tools{display:flex;gap:10px;margin:14px;flex-wrap:wrap}.arx-note{padding:0 14px}</style>
