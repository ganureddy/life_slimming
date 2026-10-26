<script setup>
import {nextTick,onBeforeUnmount,ref,watch} from 'vue';
const props=defineProps({title:String,busy:Boolean});const open=defineModel({type:Boolean,default:false});const dialog=ref(null);let focus;
watch(open,async value=>{if(value){focus=document.activeElement;await nextTick();dialog.value?.showModal();}else{dialog.value?.close();focus?.focus();}});onBeforeUnmount(()=>dialog.value?.close());
</script>
<template><dialog ref="dialog" class="modal wide task-modal" :class="{show:open}" @cancel.prevent="!busy&&(open=false)"><header class="mdh"><b>{{title}}</b><button type="button" class="x" aria-label="Close" :disabled="busy" @click="open=false">×</button></header><div class="mdb"><slot/></div></dialog></template>
<style scoped>.task-modal{border:0;padding:0;margin:0;max-height:90dvh;overflow:auto}.task-modal::backdrop{background:#0a1e1473}.task-modal:not([open]){display:none!important}</style>
