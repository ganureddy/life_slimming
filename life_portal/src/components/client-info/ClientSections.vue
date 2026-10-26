<script setup>
import { computed, ref } from 'vue';
const props=defineProps({name:String,sections:{type:Array,required:true}});
function read(key,fallback){try{const value=JSON.parse(localStorage.getItem('c360.v8.'+props.name+'.'+key));return key==='order'?(Array.isArray(value)?value:fallback):(value&&typeof value==='object'&&!Array.isArray(value)?value:fallback);}catch{return fallback;}}
const order=ref(read('order',[])),collapsed=ref(read('collapsed',{}));
const sorted=computed(()=>[...props.sections].sort((a,b)=>{const left=order.value.indexOf(a.id),right=order.value.indexOf(b.id);return(left<0?999:left)-(right<0?999:right);}));
function save(key,value){try{localStorage.setItem('c360.v8.'+props.name+'.'+key,JSON.stringify(value));}catch{}}
function toggle(id){collapsed.value={...collapsed.value,[id]:!collapsed.value[id]};save('collapsed',collapsed.value);}
function move(id,delta){const ids=sorted.value.map(row=>row.id),index=ids.indexOf(id),target=index+delta;if(target<0||target>=ids.length)return;[ids[index],ids[target]]=[ids[target],ids[index]];order.value=ids;save('order',ids);}
</script>
<template><div class="c3-secs"><section v-for="section in sorted" :key="section.id" class="c3-sec" :class="{'is-collapsed':collapsed[section.id],'is-wide':section.wide}" :data-sec="section.id"><header class="c3-sec-h"><button type="button" class="c3-sec-title" :aria-expanded="!collapsed[section.id]" @click="toggle(section.id)"><span class="c3-sec-ic">{{ section.icon }}</span><span>{{ section.title }}</span><span v-if="section.badge!=null && section.badge!==''" class="c3-sec-badge" :class="'tone-'+(section.tone||'mute')">{{ section.badge }}</span></button><div class="c3-sec-tools"><button type="button" aria-label="Move up" @click="move(section.id,-1)">↑</button><button type="button" aria-label="Move down" @click="move(section.id,1)">↓</button><button type="button" class="c3-chev" aria-label="Collapse or expand" @click="toggle(section.id)">⌃</button></div></header><div v-show="!collapsed[section.id]" class="c3-sec-b"><slot :name="section.id" /></div></section></div></template>
