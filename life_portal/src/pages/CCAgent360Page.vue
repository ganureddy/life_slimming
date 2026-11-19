<script setup>
import {computed,ref,watch} from 'vue';
import {useRoute,useRouter} from 'vue-router';
import {indiaStamp} from '../lib/cc';
import {reportRange} from '../lib/cc-visit-report';
import CCActivityReport from '../components/cc/CCActivityReport.vue';
import CCNoFollowupReport from '../components/cc/CCNoFollowupReport.vue';
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
<CCNoFollowupReport @open="id=>router.push({name:'cc-leads-followup',params:{leadId:id}})"/>
</main></section></template>
<style scoped>.cc-agent360-standalone{--a360-ink:#173d2b;--a360-muted:#617567;--a360-green:#17633e;--a360-line:#dbe8de;--a360-wash:#f4f8f5;background:linear-gradient(180deg,#f6faf7 0,#fffdf9 260px);min-height:100%}.cc-agent360-main{max-width:1500px;margin:0 auto;padding:24px;min-width:0}.cc-report-tabs{display:flex;margin:0 0 16px}.cc-report-tabs .active{padding:10px 15px;border-radius:999px;color:white;background:var(--a360-green);font-size:13px;font-weight:800;box-shadow:0 3px 8px #174b3024}.cc-agent360-standalone .cc-workspace-head{position:relative;height:auto;min-height:70px;padding-inline:24px;border-bottom:1px solid #dce8df;background:#fff}.cc-agent360-standalone :deep(.cc-card){margin:18px 0;padding:20px;border:1px solid var(--a360-line);border-radius:16px;background:#fff;box-shadow:0 7px 20px #183d290a}.cc-agent360-standalone :deep(.cc-card>h2){margin:0 0 16px;color:var(--a360-ink);font-size:clamp(19px,2vw,24px);letter-spacing:-.015em}.cc-agent360-standalone :deep(.cc-filters){align-items:end;gap:12px;padding:14px;margin:0 0 14px;border:1px solid #e0ebe2;border-radius:12px;background:var(--a360-wash)}.cc-agent360-standalone :deep(.cc-filters label){gap:5px;color:#496553;font-size:11px;font-weight:800;letter-spacing:.03em;text-transform:uppercase}.cc-agent360-standalone :deep(.cc-filters input),.cc-agent360-standalone :deep(.cc-filters select){min-height:38px;border-color:#bed3c3;border-radius:8px;background:#fff;color:var(--a360-ink)}.cc-agent360-standalone :deep(.cc-filters button),.cc-agent360-standalone :deep(.cc-card>button){min-height:38px;border-radius:8px;font-weight:750}.cc-agent360-standalone :deep(.cc-report-metrics){display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px;margin:18px 0}.cc-agent360-standalone :deep(.cc-table){border:1px solid #e0ebe2;border-radius:11px}.cc-agent360-standalone :deep(.cc-table th){background:#f2f7f3;color:#315542;font-size:11px;letter-spacing:.025em;text-transform:uppercase}.cc-agent360-standalone :deep(.cc-table td),.cc-agent360-standalone :deep(.cc-table th){padding:11px 12px}.cc-agent360-standalone :deep(.cc-error){padding:10px 12px;border:1px solid #f1c2bc;border-radius:9px;background:#fff4f2}.cc-agent360-standalone :deep(.cc-card+ .cc-card){margin-top:22px}@media(max-width:650px){.cc-agent360-main{padding:12px}.cc-agent360-standalone .cc-workspace-head{min-height:58px;padding-inline:14px}.cc-agent360-standalone :deep(.cc-card){padding:14px;border-radius:12px}.cc-agent360-standalone :deep(.cc-filters){gap:9px;padding:10px}.cc-agent360-standalone :deep(.cc-filters label){flex:1 1 135px}.cc-agent360-standalone :deep(.cc-filters button){flex:1 1 auto}}</style>
