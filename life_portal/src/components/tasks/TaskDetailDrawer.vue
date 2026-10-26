<script setup>
import {nextTick,onBeforeUnmount,onMounted,ref,watch} from 'vue';
const props=defineProps({title:String,subtitle:String,busy:Boolean});const open=defineModel({type:Boolean,default:false});
const root=ref(null),closeButton=ref(null);let focus,overflow;
watch(open,async value=>{if(value){focus=document.activeElement;overflow=document.body.style.overflow;document.body.style.overflow='hidden';await nextTick();closeButton.value?.focus();}else{document.body.style.overflow=overflow??'';focus?.focus();}});
function keydown(e){if(!open.value||document.querySelector('dialog[open]'))return;if(e.key==='Escape'&&!props.busy)open.value=false;if(e.key==='Tab'){const items=[...root.value.querySelectorAll('button,input,select,textarea,a[href]')].filter(x=>!x.disabled&&x.getClientRects().length),first=items[0],last=items.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}}
onMounted(()=>document.addEventListener('keydown',keydown));onBeforeUnmount(()=>{document.removeEventListener('keydown',keydown);if(open.value)document.body.style.overflow=overflow??'';});
</script>
<template><div id="ovl" class="ovl" :class="{show:open}" @click="!busy&&(open=false)"></div><aside id="drawer" ref="root" class="drawer" :class="{show:open}" :aria-hidden="!open" :inert="!open" role="dialog" aria-modal="true" :aria-label="title"><header class="dh"><slot name="heading"><div class="pi"><div class="pm">{{subtitle}}</div><div class="nw task-detail-title">{{title}}</div></div></slot><button ref="closeButton" type="button" class="x" aria-label="Close details" :disabled="busy" @click="open=false">×</button></header><div class="db"><slot/></div><footer class="da"><slot name="actions"/></footer></aside></template>
<style scoped>.task-detail-title{font-size:16px;font-weight:700}</style>
