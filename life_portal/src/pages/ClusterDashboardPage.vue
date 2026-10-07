<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { request } from '../api/http';
import { indiaStamp } from '../lib/cc';
const today=indiaStamp().slice(0,10);
const from=ref(today.slice(0,8)+'01'),to=ref(today),cluster=ref(''),data=ref(null),loading=ref(false),error=ref('');
let controller;
const money=value=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(Number(value||0));
async function load(){
  if(!from.value||!to.value||from.value>to.value){error.value='Choose a valid date range.';return;}
  controller?.abort();const current=new AbortController();controller=current;
  loading.value=true;error.value='';
  try{
    const result=await request('cluster_dashboard_api',{args:{from_date:from.value,to_date:to.value,...(cluster.value?{cluster:cluster.value}:{})},signal:current.signal});
    if(controller===current){if(!result.message||!Array.isArray(result.message.rows))throw new Error('The dashboard returned an invalid response.');data.value=result.message;}
  }catch(e){if(controller===current&&e.name!=='AbortError')error.value=e.message;}
  finally{if(controller===current)loading.value=false;}
}
onMounted(load);onBeforeUnmount(()=>controller?.abort());
</script>
<template>
  <section class="cluster-dashboard">
    <header><div><h1>{{ data?.cluster || 'Cluster Dashboard' }}</h1><p v-if="data">{{ data.from_date }} → {{ data.to_date }} · {{ data.branches?.length || 0 }} branches</p></div><RouterLink :to="{name:'clusterhome'}">Current dashboard</RouterLink></header>
    <form @submit.prevent="load"><label v-if="data?.available_clusters?.length">Cluster<select v-model="cluster"><option value="">My cluster</option><option value="ALL">All branches</option><option v-for="name in data.available_clusters" :key="name" :value="name">{{ name }}</option></select></label><label>From<input v-model="from" type="date" required></label><label>To<input v-model="to" type="date" required></label><button :disabled="loading">{{ loading?'Loading…':'Apply' }}</button></form>
    <p v-if="error" role="alert">{{ error }} <button :disabled="loading" @click="load">Retry</button></p>
    <p v-if="loading" role="status">Loading cluster dashboard…</p>
    <template v-if="data">
      <p v-if="!data.available_clusters?.length" role="status">Cluster assignments are not configured on the server. These figures cover all returned branches.</p>
      <div class="cluster-cards"><article><span>Sales</span><strong>{{ money(data.totals?.sales_amt) }}</strong></article><article><span>Invoices</span><strong>{{ data.totals?.sales_count || 0 }}</strong></article><article><span>Collections</span><strong>{{ money(data.totals?.collections) }}</strong></article><article><span>Outstanding</span><strong>{{ money(data.totals?.outstanding) }}</strong></article></div>
      <div class="cluster-table"><table><thead><tr><th>Branch</th><th>Sales</th><th>Invoices</th><th>Collections</th><th>Outstanding</th></tr></thead><tbody><tr v-for="row in data.rows" :key="row.branch"><td>{{ row.branch }}</td><td>{{ money(row.sales_amt) }}</td><td>{{ row.sales_count }}</td><td>{{ money(row.collections) }}</td><td>{{ money(row.outstanding) }}</td></tr><tr v-if="!data.rows.length"><td colspan="5">No branches configured for this cluster.</td></tr></tbody></table></div>
    </template>
  </section>
</template>
<style scoped>
.cluster-dashboard{padding:24px;max-width:1300px;margin:auto;color:#19332b}.cluster-dashboard header{display:flex;justify-content:space-between;align-items:center;gap:16px}.cluster-dashboard h1{margin:0}.cluster-dashboard p{color:#586f65}.cluster-dashboard form{display:flex;flex-wrap:wrap;align-items:end;gap:12px;margin:24px 0}.cluster-dashboard label{display:grid;gap:5px;font-size:13px}.cluster-dashboard input,.cluster-dashboard select,.cluster-dashboard button{font:inherit;padding:9px 12px;border:1px solid #c9d8cf;border-radius:8px;background:white}.cluster-dashboard button{cursor:pointer;background:#245f4a;color:white}.cluster-dashboard button:disabled{opacity:.5}.cluster-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0}.cluster-cards article{background:#f4f8f5;border:1px solid #d7e5da;border-radius:12px;padding:18px;display:grid;gap:8px}.cluster-cards strong{font-size:24px}.cluster-table{overflow-x:auto}.cluster-table table{width:100%;border-collapse:collapse;min-width:620px}.cluster-table th,.cluster-table td{padding:13px;text-align:left;border-bottom:1px solid #dbe6de}.cluster-table th{background:#f4f8f5}@media(max-width:700px){.cluster-dashboard{padding:16px}.cluster-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.cluster-cards strong{font-size:18px}}
</style>
