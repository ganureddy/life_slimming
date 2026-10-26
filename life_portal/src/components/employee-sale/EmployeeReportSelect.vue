<script setup>
import {computed,nextTick,onBeforeUnmount,onMounted,ref} from 'vue';
const props=defineProps({options:Array,label:String,allLabel:String});const model=defineModel({type:Array,default:()=>[]});
const root=ref(null),search=ref(null),open=ref(false),query=ref('');
const rows=computed(()=>props.options.filter(x=>String(x.label+' '+x.value).toLowerCase().includes(query.value.toLowerCase())));
const labels=computed(()=>model.value.map(v=>props.options.find(o=>o.value===v)?.label||v));
function toggle(v){model.value=model.value.includes(v)?model.value.filter(x=>x!==v):[...model.value,v];}
async function show(){open.value=!open.value;if(open.value){query.value='';await nextTick();search.value?.focus();}}
function close(e){if(!root.value?.contains(e.target))open.value=false;}
onMounted(()=>document.addEventListener('pointerdown',close));onBeforeUnmount(()=>document.removeEventListener('pointerdown',close));
</script>
<template><div ref="root" class="esr-ms" @keydown.esc.stop="open=false"><button type="button" class="esr-ms-btn" :class="{has:model.length}" :aria-label="label" :aria-expanded="open" :title="labels.join(', ')" @click="show"><span class="esr-ms-txt">{{!labels.length?allLabel:labels[0]+(labels.length>1?' + '+(labels.length-1)+' more':'')}}</span><span v-if="labels.length>1" class="esr-ms-n">{{labels.length}}</span></button><div v-if="open" class="esr-dd open employee-select-dropdown"><div class="esr-dd-top"><input ref="search" v-model="query" class="esr-dd-search" type="search" placeholder="Search…" :aria-label="'Search '+label"><div class="esr-dd-acts"><button type="button" @click="model=[...new Set([...model,...rows.map(o=>o.value)])]">Select shown</button><button type="button" @click="model=[]">Clear</button></div></div><div class="esr-dd-list"><label v-for="o in rows" :key="o.value" class="esr-dd-item" :class="{none:o.value==='__NONE__'}"><input type="checkbox" :checked="model.includes(o.value)" @change="toggle(o.value)"><span class="t">{{o.label}}</span><span v-if="o.count!=null" class="c">{{o.count}}</span></label><div v-if="!rows.length" class="esr-dd-empty">No match</div></div><div class="esr-dd-foot"><span>{{rows.length}} of {{options.length}}</span><span>{{model.length?model.length+' selected':''}}</span></div></div></div></template>
<style scoped>.esr-ms{position:relative}.employee-select-dropdown{position:absolute;display:block;left:0;top:100%;width:max(100%,260px);max-width:80vw;z-index:100}</style>
