<script setup>
defineEmits(['home-store','branch-store','operations']);
</script>
<template>
  <section class="stock-operations-strip"><div><small>LIFE · INVENTORY OPERATIONS</small><h2>The right stock. In the right place.</h2><p>11 branches · HO Main Store · HO operations</p></div><div class="stock-operation-links"><button @click="$emit('home-store')">HO Main Store</button><span>→</span><button @click="$emit('branch-store')">Branch Store</button><span>→</span><button @click="$emit('operations')">Operations</button>💡</div></section>
</template>
