<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { billingCall, billingList } from '../../api/billing';
import { dateRange, indiaStamp } from '../../lib/cc';
const props=defineProps({ branch:String, branches:Array, headOffice:Boolean });
const emit=defineEmits(['counts']);
const values=ref(null),error=ref(''),busy=ref(false);let controller;
const money=v=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(Number(v || 0));
const exGst=report=>(report.rows || []).filter(row=>!props.branch || row.branch===props.branch).reduce((sum,row)=>sum+Number(row.collected_ex_gst || 0),0);
const paid=report=>(report.rows || []).filter(row=>!props.branch || row.branch===props.branch).reduce((sum,row)=>sum+Number(row.collected_total ?? (Number(row.collected_gst || 0)+Number(row.collected_nongst || 0))),0);
async function load(){
 busy.value=true;error.value='';values.value=null;controller?.abort();controller=new AbortController();
 try{
  if(!props.headOffice && !props.branches.length)throw new Error('No permitted branch is available.');
  const today=indiaStamp().slice(0,10),[from]=dateRange('month',today);
  const scope=props.branch?[['branch','=',props.branch]]:props.headOffice?[]:[['branch','in',props.branches]];
  const [daily,monthly,invoices,pending]=await Promise.all([
   billingCall('lifescc_billing_collections_report',{from_date:today,to_date:today,branch:props.branch},controller.signal),
   billingCall('lifescc_billing_collections_report',{from_date:from,to_date:today,branch:props.branch},controller.signal),
   billingCall('frappe.client.get_count',{doctype:'Sales Invoice',filters:[['docstatus','=',1],['posting_date','=',today],...scope]},controller.signal),
   billingList('Sales Invoice',[['docstatus','=',1],['outstanding_amount','>',0],...scope],['sum(outstanding_amount) as outstanding','count(name) as count'],{limit:1,order:'',signal:controller.signal}),
  ]);
  values.value={daily:paid(daily),dailyEx:exGst(daily),monthly:paid(monthly),monthlyEx:exGst(monthly),from,invoices:Number(invoices),outstanding:Number(pending[0]?.outstanding || 0),pending:Number(pending[0]?.count || 0)};emit('counts',values.value.pending);
 }catch(e){if(e.name!=='AbortError')error.value=e.message;}finally{busy.value=false;}
}
onMounted(load);onBeforeUnmount(()=>controller?.abort());
</script>
<template>
  <section class="billing-overview" aria-label="Billing overview">
    <p v-if="busy" class="billing-loading" role="status">Loading live figures…</p>
    <p v-if="error" role="alert">{{ error }} <button @click="load">Retry figures</button></p>
    <div v-if="values" class="billing-kpis">
      <article class="billing-kpi tone-green"><span class="kpi-icon" aria-hidden="true">₹</span><strong>{{ money(values.daily) }}</strong><h3>Today's collection</h3><p>Excl. GST {{ money(values.dailyEx) }} · GST {{ money(values.daily-values.dailyEx) }}</p></article>
      <article class="billing-kpi tone-blue"><span class="kpi-icon" aria-hidden="true">▤</span><strong>{{ values.invoices }}</strong><h3>Invoices today</h3><p>{{ indiaStamp().slice(0,10) }}</p></article>
      <article class="billing-kpi tone-red"><span class="kpi-icon" aria-hidden="true">◷</span><strong>{{ money(values.outstanding) }}</strong><h3>Total pending</h3><p>{{ values.pending }} bills with due</p></article>
      <article class="billing-kpi tone-amber"><span class="kpi-icon" aria-hidden="true">▦</span><strong>{{ money(values.monthly) }}</strong><h3>Business month collected</h3><p>{{ values.from }} → {{ indiaStamp().slice(0,10) }}</p><p>Excl. GST {{ money(values.monthlyEx) }} · GST {{ money(values.monthly-values.monthlyEx) }}</p></article>
    </div>
  </section>
</template>
