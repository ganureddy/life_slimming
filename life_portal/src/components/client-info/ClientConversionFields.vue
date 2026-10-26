<script setup>
import {computed} from 'vue';
import {money} from '../../lib/client-info';
import {plainText,safeFileUrl} from '../../lib/client-profile-sections';
import ClientPhone from './ClientPhone.vue';
const props=defineProps({doc:Object});
const internal=new Set(['doctype','owner','modified_by','modified','idx','docstatus','parent','parentfield','parenttype','naming_series','amended_from']);
const fields=computed(()=>Object.entries(props.doc||{}).filter(([k,v])=>!internal.has(k)&&!k.startsWith('_')&&!/snapshot|json|hash|source_row|ledger|applied_on/.test(k)&&v!=null&&v!==''&&(!Array.isArray(v)||v.length)));
const label=k=>k.replace(/_/g,' ').replace(/\b\w/g,s=>s.toUpperCase());
const format=(v,k)=>/amount|balance|total_billed|total_received|duers/i.test(k)&&Number.isFinite(Number(v))?money(Number(v)):typeof v==='number'&&(v===0||v===1)&&!/count|qty|quantity|sessions|step/.test(k)?v?'Yes':'No':plainText(v);
const signature=v=>typeof v==='string'&&/^data:image\/(png|jpeg|webp);base64,[a-z0-9+/=\s]+$/i.test(v);
</script>
<template><div class="c3-conversion-fields"><span v-for="[key,value] in fields" :key="key" class="c3-conversion-field"><small>{{label(key)}}</small><span><template v-if="Array.isArray(value)"><span v-for="(row,i) in value" :key="row?.name||i" class="c3-conversion-item"><b>#{{i+1}}</b><ClientConversionFields v-if="row&&typeof row==='object'" :doc="row"/><template v-else>{{plainText(row)}}</template></span></template><ClientConversionFields v-else-if="value&&typeof value==='object'" :doc="value"/><img v-else-if="signature(value)" class="c3-conversion-signature" :src="value" :alt="label(key)+' — recorded'"><a v-else-if="typeof value==='string'&&/^\/(?:private\/)?files\//.test(value)&&safeFileUrl(value)" :href="safeFileUrl(value)" target="_blank" rel="noopener">View attachment ↗</a><ClientPhone v-else-if="/mobile|phone/.test(key)" :value="String(value)"/><template v-else>{{format(value,key)}}</template></span></span></div></template>
