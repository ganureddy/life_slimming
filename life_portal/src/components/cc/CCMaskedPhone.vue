<script setup>
import { ref } from 'vue';
import { maskPhone } from '../../lib/cc';

const props = defineProps({ number: { type: [String, Number], default: '' } });
const revealed = ref(false);
const copied = ref(false);

async function copy() {
  const value = String(props.number || '').replace(/\D/g, '').slice(-10);
  if (!value) return;
  try { await navigator.clipboard.writeText(value); copied.value = true; setTimeout(() => { copied.value = false; }, 1500); } catch {}
}
</script>

<template>
  <button
    type="button"
    class="cc-masked-phone"
    :title="number ? 'Hover to reveal · click to copy' : ''"
    @mouseenter="revealed = true"
    @mouseleave="revealed = false"
    @focus="revealed = true"
    @blur="revealed = false"
    @click.stop="copy"
  >{{ revealed ? number : maskPhone(number) }}<small v-if="copied"> Copied</small></button>
</template>
