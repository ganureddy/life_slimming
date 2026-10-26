<script setup>
import {ref} from 'vue';
defineProps({nodes:Array,total:Number,level:{type:Number,default:0},expanded:Boolean});const opened=ref(new Set());
const label=v=>v==='__NONE__'?'(Unmapped)':v;
const money=v=>'₹'+Number(v||0).toLocaleString('en-IN',{maximumFractionDigits:2});
function toggle(k){const next=new Set(opened.value);next.has(k)?next.delete(k):next.add(k);opened.value=next;}
</script>
<template><div v-for="node in nodes" :key="node.k" class="treatment-node"><div class="treatment-line" :style="{paddingLeft:level*20+'px'}"><button v-if="node.kids.length" type="button" :aria-expanded="expanded||opened.has(node.k)" @click="toggle(node.k)">{{expanded||opened.has(node.k)?'▾':'▸'}}</button><strong>{{label(node.k)}}</strong><span>{{node.invoices}} invoices · {{node.clients}} clients · {{node.employees}} employees</span><b>{{money(node.share)}}</b><small>{{total?(node.share/total*100).toFixed(1):0}}% · Full invoice {{money(node.full)}}</small></div><TreatmentTree v-if="node.kids.length&&(expanded||opened.has(node.k))" :nodes="node.kids" :total="total" :level="level+1" :expanded="expanded"/></div></template>
<style scoped>.treatment-line{display:flex;gap:12px;align-items:center;padding:10px;border-bottom:1px solid #dce9de;flex-wrap:wrap}.treatment-line b{margin-left:auto}.treatment-line span,.treatment-line small{color:#687d6e;font-size:12px}button{border:0;background:transparent}</style>
