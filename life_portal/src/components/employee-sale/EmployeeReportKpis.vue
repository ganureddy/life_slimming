<script setup>defineProps({items:Array});</script>
<template><div class="esr-kpis"><div v-for="[label,value,note,tone] in items" :key="label" class="esr-kpi" :class="tone"><div class="l">{{label}}</div><div class="v">{{value}}</div><div v-if="note" class="s">{{note}}</div></div></div></template>
