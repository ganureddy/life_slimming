<script setup>
import { computed, ref } from 'vue';
const props=defineProps({label:String,help:String,options:{type:Array,default:()=>[]}});
const model=defineModel({type:Array,default:()=>[]});
const search=ref('');
const allOptions=computed(()=>props.options.map(option=>typeof option==='object'?option:{value:option,label:option}));
const shown=computed(()=>allOptions.value.filter(option=>String(option.label).toLowerCase().includes(search.value.trim().toLowerCase())));
function toggle(value){model.value=model.value.includes(value)?model.value.filter(item=>item!==value):[...model.value,value];}
</script>
<template>
  <div class="lcx-pk">
    <div class="lcx-pk-h"><b>{{label}}</b><span v-if="help" class="lcx-tip" :title="help" aria-label="Filter help">ⓘ</span><span class="lcx-pk-n">{{model.length?model.length+' selected':'All'}}</span><button type="button" class="lcx-lnk" @click="model=[...new Set([...model,...shown.map(option=>option.value)])]">Select all</button><button type="button" class="lcx-lnk" :disabled="!model.length" @click="model=[]">Clear</button></div>
    <input v-if="allOptions.length>10" v-model="search" class="lcx-pk-s" type="search" :aria-label="'Search '+label" placeholder="Search…">
    <div class="lcx-pk-l"><label v-for="option in shown" :key="option.value" class="lcx-ch" :class="{on:model.includes(option.value)}"><input type="checkbox" :checked="model.includes(option.value)" @change="toggle(option.value)"><span>{{option.label}}</span></label><p v-if="!shown.length" class="cc-note">No matching options.</p></div>
  </div>
</template>
