<script setup>
defineProps({ active: { type: String, default: 'dashboard' } });
const emit = defineEmits(['select']);
const tabs = [['dashboard','▦ Dashboard'],['intelligence','📈 Stock Insights'],['requests','📥 Requests / App.'],['vendor-reports','🏷 Vendor Reports'],['procurement','📦 Purchase Ord'],['procurement-receipt','📥 Purchase Rec.'],['procurement-invoice','🧾 Purchase Inv.'],['reports','▤ Indent Reports'],['item-vendor','◎ Item / Vendor 360'],['stock-reports','▦ Stock Reports']];
</script>
<template><nav class="stock-live-tabs" aria-label="Stock dashboard sections"><button v-for="[key,label] in tabs" :key="key" :class="{active: active===key}" @click="emit('select',key)">{{ label }} <span>💡</span></button></nav></template>
