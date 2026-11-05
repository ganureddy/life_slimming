<script setup>
import { maskRecoveryMobile } from '../../lib/recovery-domain';
defineProps({row:{type:Object,required:true},detail:{type:Object,default:()=>({})}});
const date=value=>value?String(value).slice(0,10).split('-').reverse().join('-'):'—';
</script>
<template><b>{{row.client}}</b><span class="pdr-appointment">📅 {{detail.appointment?date(detail.appointment.appointment_date)+' '+String(detail.appointment.appointment_time||'').slice(0,5):detail.loaded?'No upcoming appointment':detail.failed?'Appointment unavailable':'Appointment loading…'}}</span><div class="pdr-phones"><span v-for="(phone,index) in [...new Set((detail.phones||[row.mobile]).filter(Boolean))]" :key="phone" class="pdr-phone" tabindex="0" :aria-label="(index?'Alternative phone':'Primary phone')+' — hover or focus to reveal'"><span class="phone-mask">{{maskRecoveryMobile(phone)}}</span><span class="phone-full">{{phone}}</span></span></div></template>
