<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { billingCall } from '../../api/billing';
const props=defineProps({ name:String, printFormat:{type:String,default:'Consultaion Patient Sales Invoice'} });const emit=defineEmits(['close']);
const source=ref(''),error=ref('');let alive=true;
async function load(){
 error.value='';source.value='';
 try{
  const result=await billingCall('frappe.www.printview.get_html_and_style',{doc:'Sales Invoice',name:props.name,print_format:props.printFormat,no_letterhead:0});
  if(!result.html)throw new Error('The invoice print format could not be rendered.');
  if(alive)source.value='<!doctype html><html><head><meta charset="utf-8"><style>'+String(result.style || '').replace(/<\/style/gi,'')+'</style></head><body>'+result.html+'</body></html>';
 }catch(e){if(alive)error.value=e.message;}
}
onMounted(load);onBeforeUnmount(()=>{alive=false;});
</script>
<template><section class="billing-panel"><header><h3>Invoice print preview · {{ name }}</h3><button @click="emit('close')">Close preview</button></header><p v-if="error" role="alert">{{ error }} <button @click="load">Retry preview</button></p><p v-else-if="!source" role="status">Loading print preview…</p><iframe v-else :srcdoc="source" sandbox title="Read-only invoice print preview" style="width:100%;height:70vh;border:0;background:white"></iframe></section></template>
