<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
const props = defineProps({ modelValue: { type: String, default: '' }, options: { type: Array, default: () => [] }, emptyLabel: String, placeholder: String, disabled: Boolean, label: String, id: String });
const emit = defineEmits(['update:modelValue', 'change']);
const open = ref(false), query = ref(''), host = ref(null), input = ref(null);
const display = computed(() => props.options.find(option => option.value === props.modelValue)?.label || props.modelValue || props.emptyLabel || 'Select…');
const filtered = computed(() => props.options.filter(option => option.label.toLowerCase().includes(query.value.toLowerCase())));
async function toggle() { if (props.disabled) return; open.value = !open.value; if (open.value) { query.value = ''; await nextTick(); input.value?.focus(); } }
function select(value) { emit('update:modelValue', value); emit('change', value); open.value = false; }
function outside(event) { if (!host.value?.contains(event.target)) open.value = false; }
onMounted(() => document.addEventListener('pointerdown', outside));
onBeforeUnmount(() => document.removeEventListener('pointerdown', outside));
</script>
<template>
  <div :id="id" ref="host" class="rr-ss" :class="{'rr-ss-open':open}">
    <button class="rr-ss-display" type="button" :disabled="disabled" :tabindex="disabled ? -1 : 0" :aria-label="label" :aria-expanded="open" @click="toggle" @keydown.esc="open = false"><span class="rr-ss-val">{{ display }}</span><span class="rr-ss-arrow">▼</span></button>
    <div v-if="open" class="rr-ss-drop" style="display:block" @keydown.esc.stop="open = false">
      <input ref="input" v-model="query" class="rr-ss-search" type="text" :placeholder="placeholder" autocomplete="off" :aria-label="placeholder" @keydown.enter.prevent="filtered.length === 1 && select(filtered[0].value)">
      <div class="rr-ss-list"><button v-for="option in filtered" :key="option.value" type="button" class="rr-ss-opt" :class="{'rr-ss-sel':option.value === modelValue}" :data-val="option.value" @click="select(option.value)">{{ option.label }}</button></div>
    </div>
  </div>
</template>
<style scoped>
.rr-ss-display{width:100%;font:inherit;text-align:left}.rr-ss-display:disabled{opacity:.78;pointer-events:none}.rr-ss-opt{display:block;width:100%;font:inherit;text-align:left;border:0}.rr-ss-opt:not(:hover):not(.rr-ss-sel){background:transparent}
</style>
