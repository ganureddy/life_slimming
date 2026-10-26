<script setup>
import {computed} from 'vue';
const props=defineProps({items:Array,calc:Object,tone:String});const max=computed(()=>Math.max(1,...props.items.map(i=>i.value)));
</script>
<template><div v-if="!items.length" class="esr-empty">No data</div><div v-for="i in items" :key="i.label" class="esr-bar" :class="tone"><div class="esr-bar-l" :title="i.label">{{i.label}} <small v-if="i.sub">{{i.sub}}</small></div><div class="esr-bar-t"><div class="esr-bar-f" :style="{width:Math.max(1,Math.round(i.value/max*100))+'%'}"></div></div><div class="esr-bar-v">{{calc.fmt(i.value)}}<small v-if="i.note">{{i.note}}</small></div></div></template>
