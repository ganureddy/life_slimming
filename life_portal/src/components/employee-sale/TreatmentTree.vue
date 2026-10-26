<script setup>
import {computed,reactive} from 'vue';
const props=defineProps({nodes:Array,total:Number,calc:Object});
const opened=reactive(new Map());
const all=computed(()=>{const rows=[];function visit(nodes,level=0,parent='',visible=true){for(const n of nodes){const id=JSON.stringify([parent,n.k]),open=opened.has(id)?opened.get(id):level===0;rows.push({...n,id,parent,level,visible,open});visit(n.kids,level+1,id,visible&&open);}}visit(props.nodes);return rows;});
function expandAll(open){for(const n of all.value)opened.set(n.id,open);}
defineExpose({expandAll});
</script>
<template><tbody id="esr-tree-body"><tr v-for="n in all" :key="n.id" :class="['lv'+n.level,{hide:!n.visible}]" :data-id="n.id" :data-p="n.parent"><td><button v-if="n.kids.length" type="button" class="tg" :aria-expanded="n.open" :aria-label="(n.open?'Collapse ':'Expand ')+calc.lbl(n.k)" @click="opened.set(n.id,!n.open)">{{n.open?'−':'+'}}</button><span v-if="n.k==='__NONE__'" class="esr-pill p-amber">{{calc.lbl(n.k)}}</span><template v-else>{{n.k}}</template> <span v-if="n.level<2" class="esr-c-mute">({{n.kids.length}})</span></td><td class="n">{{n.invoices.toLocaleString('en-IN')}}</td><td class="n">{{n.clients}}</td><td class="n">{{n.employees}}</td><td class="n esr-c-main">{{calc.fmt(n.share)}}</td><td class="n"><span class="esr-share"><i :style="{width:Math.min(100,calc.pct(n.share,total)).toFixed(1)+'%'}"></i></span>{{calc.pct(n.share,total).toFixed(1)}}%</td><td class="n esr-c-mute">{{calc.fmt(n.full)}}</td></tr></tbody></template>
