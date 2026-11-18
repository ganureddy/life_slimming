<script setup>
import { computed, ref, watch } from 'vue';

const props = defineProps({ open: Boolean, branches: { type: Array, default: () => [] }, selectedCode: { type: String, default: '' } });
const emit = defineEmits(['close', 'select']);
const code = ref('');
const selected = computed(() => props.branches.find(branch => branch.code === code.value));

watch(() => props.open, open => { if (open) code.value = props.selectedCode || props.branches[0]?.code || ''; }, { immediate: true });
function confirm() { if (selected.value) emit('select', selected.value); }
</script>

<template>
  <div v-if="open" class="stock-modal-backdrop" @click.self="emit('close')">
    <section class="stock-item-modal stock-toolbar-modal" role="dialog" aria-modal="true" aria-labelledby="stock-branch-view-title">
      <div class="stock-panel-head"><div><h2 id="stock-branch-view-title">🏬 Select Branch View</h2><p>Choose the branch whose stock dashboard you want to open.</p></div><button type="button" @click="emit('close')">× Close</button></div>
      <label class="stock-search">Branch<select v-model="code"><option v-for="branch in branches" :key="branch.code" :value="branch.code">{{ branch.name }}</option></select></label>
      <p v-if="selected" class="stock-note">{{ selected.warehouses.length }} authorized warehouse(s) will be used for this view.</p>
      <p v-else class="stock-error">No branch warehouses are available to this account.</p>
      <div class="stock-form-actions"><button type="button" @click="emit('close')">Cancel</button><button type="button" class="stock-primary" :disabled="!selected" @click="confirm">Open Branch View</button></div>
    </section>
  </div>
</template>
