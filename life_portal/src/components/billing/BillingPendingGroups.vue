<script setup>
import { computed, reactive } from 'vue';
import { indiaStamp } from '../../lib/cc';
const props=defineProps({ rows:Array });const emit=defineEmits(['open','collect']);
const expanded=reactive({});
const groups=computed(()=>{
 const map=new Map();for(const row of props.rows){const month=String(row.posting_date || '').slice(0,7) || 'Unknown';if(!map.has(month))map.set(month,[]);map.get(month).push(row);}
 return [...map].map(([month,rows])=>({month,rows,due:rows.reduce((sum,row)=>sum+Number(row.outstanding_amount || 0),0)}));
});
const money=v=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(Number(v || 0));
const monthLabel=value=>/^\d{4}-\d{2}$/.test(value)?new Intl.DateTimeFormat('en-IN',{month:'long',year:'numeric',timeZone:'Asia/Kolkata'}).format(new Date(value+'-15T12:00:00Z')):value;
const age=row=>Math.floor((Date.parse(indiaStamp().slice(0,10)+'T12:00:00Z')-Date.parse(row.posting_date+'T12:00:00Z'))/86400000);
function toggleAll(value){for(const group of groups.value)expanded[group.month]=value;}
</script>
<template>
  <div class="billing-list-tools"><p>Grouped by invoice month · amounts shown for this page</p><div><button @click="toggleAll(true)">Expand all</button><button @click="toggleAll(false)">Collapse all</button></div></div>
  <section v-for="group in groups" :key="group.month" class="billing-month">
    <button class="billing-month-head" :aria-expanded="expanded[group.month]!==false" @click="expanded[group.month]=expanded[group.month]===false"><span aria-hidden="true">{{ expanded[group.month]===false?'▸':'▾' }}</span><strong>{{ monthLabel(group.month) }}</strong><span class="billing-badge tone-red">{{ group.rows.length }} pending</span><b>Due {{ money(group.due) }}</b></button>
    <div v-if="expanded[group.month]!==false" class="table-wrap" tabindex="0" aria-label="Monthly pending invoices" role="region"><table><thead><tr><th>Invoice</th><th>Date</th><th>Client</th><th>Branch</th><th>Total</th><th>Paid</th><th>Due</th><th>Ageing</th><th>Action</th></tr></thead><tbody><tr v-for="row in group.rows" :key="row.name"><td><button class="billing-text-button" @click="emit('open',row.name)">{{ row.name }}</button></td><td>{{ row.posting_date }}</td><td><strong>{{ row.patient_name }}</strong><small>{{ row.patient }}</small></td><td>{{ row.branch }}</td><td>{{ money(row.grand_total) }}</td><td>{{ money(Number(row.grand_total)-Number(row.outstanding_amount)) }}</td><td class="billing-due">{{ money(row.outstanding_amount) }}</td><td><span class="billing-badge" :class="age(row)>60?'tone-red':age(row)>30?'tone-amber':'tone-grey'">{{ age(row) }} days</span></td><td><button class="billing-primary" @click="emit('collect',row.name)">Collect payment</button></td></tr></tbody></table></div>
  </section>
</template>
