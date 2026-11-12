<script setup>
import { computed } from 'vue';
import CCChipPicker from './CCChipPicker.vue';
const props=defineProps({agents:{type:Array,default:()=>[]}});
const settings=defineModel({type:Object,required:true});
defineEmits(['save']);
const seniors=computed(()=>[...props.agents.map(agent=>({value:agent.agent,label:agent.name||agent.agent})),...(settings.value.seniors||[]).filter(id=>!props.agents.some(agent=>agent.agent===id)).map(id=>({value:id,label:id}))]);
</script>
<template>
<section class="lcx-step distribution-settings"><h4><i>⚙</i>Settings <small>Workload limits · senior closers · dormant pool</small></h4><form class="bd" @submit.prevent="$emit('save')"><div class="lcx-grid"><div class="lcx-pk"><div class="lcx-pk-h"><b>Workload limit</b></div><label class="lcx-opt"><input v-model="settings.cap_on" type="checkbox" :true-value="1" :false-value="0"><b>Active</b></label><label class="lcx-opt">Max overdue follow-ups<input v-model.number="settings.cap_overdue" type="number" min="1" required></label><label class="lcx-opt">Missed in last<input v-model.number="settings.overdue_days" type="number" min="1" required>days</label><label class="lcx-opt">Max open leads<input v-model.number="settings.cap_open" type="number" min="1" required></label><label class="lcx-opt">Open lead window<input v-model.number="settings.open_days" type="number" min="1" required>days</label></div><CCChipPicker v-model="settings.seniors" label="Senior closers" :options="seniors"/><div class="lcx-pk"><div class="lcx-pk-h"><b>Dormant pool</b></div><label class="lcx-opt">No activity for<input v-model.number="settings.dormant_days" type="number" min="7" required>days</label></div></div><div class="distribution-actions"><button type="submit" class="btn btn-g">Save &amp; Apply settings</button></div></form></section>
</template>
