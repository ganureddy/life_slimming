<script setup>
import {nextTick,onBeforeUnmount,ref,watch} from 'vue';
const props=defineProps({title:String,busy:Boolean});const open=defineModel({type:Boolean,default:false});const dialog=ref(null);let focus;
watch(open,async value=>{if(value){focus=document.activeElement;await nextTick();dialog.value?.showModal();}else{dialog.value?.close();focus?.focus();}});
onBeforeUnmount(()=>dialog.value?.close());
</script>
<template><dialog ref="dialog" class="native-dialog" @cancel.prevent="!busy&&(open=false)" @click="event=>{if(event.target===dialog&&!busy)open=false}"><header><h2>{{title}}</h2><button type="button" :disabled="busy" aria-label="Close" @click="open=false">×</button></header><slot/></dialog></template>
<style scoped>.native-dialog{position:fixed;inset:0;margin:auto;width:min(1100px,94vw);max-height:90dvh;overflow:auto;border:1px solid #b3c9ba;border-radius:14px;padding:20px;color:#143923;background:#fff;z-index:1000}.native-dialog::backdrop{background:#061d16a6}header{display:flex;align-items:center;justify-content:space-between;gap:16px}h2{font-size:20px}header button{font-size:25px;background:none;border:0}input,textarea,select{font:inherit}</style>
