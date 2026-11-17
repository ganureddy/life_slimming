<script setup>
defineProps({ nextOrders: { type: Number, default: 0 }, dense: Boolean });
const emit = defineEmits(['next-orders','buying-price','search-client','help','font','print-section','print-all']);
</script>
<template>
  <div class="stock-live-toolbar">
    <button @click="emit('next-orders')">🛒 Next Order List <b>{{ nextOrders }}</b></button>
    <button @click="emit('buying-price')">Check Buying Price</button>
    <button @click="emit('search-client')">⌕ Search Client</button>
    <button @click="emit('help')">💡 How to use</button>
    <button @click="emit('font','smaller')">A−</button><button @click="emit('font','normal')">A</button><button @click="emit('font','larger')">A+</button>
    <button @click="emit('print-section')">♧ Print section</button><button @click="emit('print-all')">♧ Print all rows</button>
  </div>
</template>
