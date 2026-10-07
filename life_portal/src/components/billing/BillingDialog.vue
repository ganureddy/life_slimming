<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
const props=defineProps({ title:String, canClose:{type:Boolean,default:true} });
const emit=defineEmits(['close']);const dialog=ref(null);
function cancel(event){event.preventDefault();if(props.canClose)emit('close');}
onMounted(()=>dialog.value.showModal());
onBeforeUnmount(()=>dialog.value?.close());
</script>
<template><dialog ref="dialog" class="billing-native billing-dialog" :aria-label="title" @cancel="cancel"><slot /></dialog></template>
