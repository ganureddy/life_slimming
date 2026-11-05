<script setup>
import { computed } from 'vue';
import { recoverySchedule } from '../../lib/recovery-domain';
const props=defineProps({rows:{type:Array,required:true}}),cards=computed(()=>recoverySchedule(props.rows));
const money=value=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',minimumFractionDigits:0,maximumFractionDigits:2}).format(value);
const date=value=>value.toLocaleDateString('en-IN',{day:'numeric',month:'short'});
const colors=[['#fff1e8','#9a5134'],['#eaf2fc','#366e9f'],['#f0ecfa','#76549c'],['#fcf5de','#8f7130']];
</script>
<template><div class="pdr-due-grid" id="pdrDueCards"><article v-for="(card,index) in cards" :key="card.name" class="pdr-due-card" :style="{'--due-tint':colors[index][0],'--due-ink':colors[index][1]}"><div class="pdr-due-top"><div><h3>{{card.name}}</h3><small>{{date(card.from)}}{{card.from.getTime()!==card.to.getTime()?' – '+date(card.to):''}}</small></div><span class="pdr-due-icon">{{['01','02','07','M'][index]}}</span></div><div class="pdr-due-scheduled"><span class="pdr-due-label">ERP scheduled dues</span><strong class="pdr-due-value">{{money(card.scheduled)}}</strong><span class="pdr-due-count">{{card.invoices}} invoices · ERP next due date</span></div><div class="pdr-due-confirmed"><div><span class="pdr-due-label">Confirmed collectable</span><span class="pdr-due-count">{{card.commitments}} commitments · promised date</span></div><strong>{{money(card.confirmed)}}</strong></div></article></div></template>
