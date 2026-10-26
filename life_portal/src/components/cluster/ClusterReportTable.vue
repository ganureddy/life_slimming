<script setup>
import {ref,watch} from 'vue';
const props=defineProps({rows:Array,columns:Array,total:{type:Boolean,default:true}});const shown=ref(15);watch(()=>props.rows,()=>{shown.value=Math.max(15,Math.min(shown.value,props.rows.length));});
const value=(r,c)=>c.v?c.v(r):r[c.k];
const format=(v,c)=>v==null?'—':c.t==='amt'?'₹ '+Number(v).toLocaleString('en-IN',{maximumFractionDigits:0}):c.t==='pct'?Number(v).toFixed(1)+'%':String(v);
const sum=c=>props.rows.every(r=>value(r,c)!=null)?props.rows.reduce((n,r)=>n+(Number(value(r,c))||0),0):null;
</script>
<template><div><div class="cl-table-wrap"><table><thead><tr><th v-for="c in columns" :key="c.k">{{c.l}}</th></tr></thead><tbody><tr v-for="(r,i) in rows.slice(0,shown)" :key="r.id||r.name||i"><td v-for="c in columns" :key="c.k" :data-label="c.l"><slot name="cell" :row="r" :column="c" :value="value(r,c)">{{format(value(r,c),c)}}</slot></td></tr><tr v-if="!rows.length"><td :colspan="columns.length" class="cl-empty">No records for this selection.</td></tr><tr v-if="total&&rows.length" class="cl-total"><td v-for="(c,i) in columns" :key="c.k">{{i===0?'GRAND TOTAL':c.t==='pct'?'100%':['amt','int'].includes(c.t)?format(sum(c),c):'—'}}</td></tr></tbody></table></div><button v-if="rows.length>shown" type="button" class="cl-more" @click="shown+=15">Load 15 more · Showing {{shown}} of {{rows.length}}</button></div></template>
