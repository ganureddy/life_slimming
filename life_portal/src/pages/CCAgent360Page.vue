<script setup>
import {computed,ref,watch} from 'vue';
import {useRoute,useRouter} from 'vue-router';
import {indiaStamp} from '../lib/cc';
import {reportRange} from '../lib/cc-visit-report';
import CCActivityReport from '../components/cc/CCActivityReport.vue';
import '../styles/cc.css';
import '../styles/cc-report-theme.css';
const route=useRoute(),router=useRouter();
const validDay=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value);
const today=indiaStamp().slice(0,10),from=ref(validDay(route.query.from)?route.query.from:today),to=ref(validDay(route.query.to)?route.query.to:today),period=ref('today');
const applied=ref({from:from.value,to:to.value}),refreshKey=ref(0),error=ref('');
const canApply=computed(()=>from.value&&to.value&&from.value<=to.value);
function apply(refresh=true){
 if(!canApply.value){error.value='Choose a valid date range.';return;}
 if((Date.parse(to.value)-Date.parse(from.value))/86400000>92){error.value='Choose an activity range of up to 93 days.';return;}
 error.value='';applied.value={from:from.value,to:to.value};if(refresh)refreshKey.value++;
 if(route.query.from!==from.value||route.query.to!==to.value)router.replace({name:'agent-360',query:{...route.query,from:from.value,to:to.value}});
}
function quick(value){period.value=value;[from.value,to.value]=reportRange(value);apply();}
watch(()=>[route.query.from,route.query.to],([start,end])=>{if(validDay(start)&&validDay(end)&&(start!==applied.value.from||end!==applied.value.to)){from.value=start;to.value=end;apply(false);}});
</script>
<template><section class="cc-native cc-native-shell cc-report-native cc-agent360-standalone"><header class="cc-workspace-head"><div class="cc-brand"><span class="cc-brand-mark">L</span><div><h1>🔗 LIFE AGENT 360</h1><small>ERP + ConVox + Mobile activity</small></div></div></header><main class="cc-agent360-main"><nav class="cc-report-tabs" aria-label="Agent 360 tabs"><span class="active" aria-current="page">🔗 Agent 360</span></nav>
<form class="cc-filters" @submit.prevent="apply()"><label>From<input v-model="from" type="date" required></label><label>To<input v-model="to" type="date" required></label><button :disabled="!canApply" type="submit">Apply / refresh</button><button v-for="[value,label] in [['today','Today'],['yesterday','Yesterday'],['week','This Week'],['month','This Month']]" :key="value" type="button" @click="quick(value)">{{label}}</button></form><p v-if="error" role="alert" class="cc-error">{{error}}</p>
<CCActivityReport :from="applied.from" :to="applied.to" :refresh-key="refreshKey" @open="id=>router.push({name:'cc-leads-followup',params:{leadId:id}})"/>
</main></section></template>
<style scoped>.cc-agent360-main{padding:18px;min-width:0}.cc-report-tabs{display:flex;margin:12px 0}.cc-report-tabs .active{padding:12px 20px;border-radius:8px;color:white;background:#164b33;font-weight:700}.cc-agent360-standalone .cc-workspace-head{position:relative;height:auto;min-height:58px}.cc-agent360-standalone :deep(.cc-card){padding:14px}.cc-agent360-standalone :deep(.cc-report-metrics){display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin:14px 0}@media(max-width:650px){.cc-agent360-main{padding:10px}}</style>
