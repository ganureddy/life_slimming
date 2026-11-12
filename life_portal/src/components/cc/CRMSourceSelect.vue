<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
const props=defineProps({options:{type:Array,default:()=>[]},label:{type:String,default:'Lead sources'},disabled:Boolean});
const model=defineModel({type:Array,default:()=>[]});
const query=ref(''), root=ref(null);
function closeOutside(event){if(root.value&&!root.value.contains(event.target))root.value.querySelector('details').open=false;}
onMounted(()=>document.addEventListener('pointerdown',closeOutside));
onBeforeUnmount(()=>document.removeEventListener('pointerdown',closeOutside));
const choices=computed(()=>[...new Set([...props.options,...model.value])].filter(source=>String(source).toLowerCase().includes(query.value.trim().toLowerCase())));
function toggle(source){if(props.disabled)return;model.value=model.value.includes(source)?model.value.filter(value=>value!==source):[...model.value,source];}
</script>
<template>
  <div ref="root" class="crm-source-select">
    <details @keydown.esc="event=>event.currentTarget.open=false">
      <summary :aria-label="label" :aria-disabled="disabled" @click="event=>{if(disabled)event.preventDefault()}"><span>{{model.length?`${model.length} sources selected`:'Choose lead sources'}}</span><span aria-hidden="true">⌄</span></summary>
      <div class="crm-source-options">
        <input v-model="query" type="search" :aria-label="'Search '+label" placeholder="Search lead sources…" :disabled="disabled">
        <div class="crm-source-tools"><button type="button" :disabled="disabled" @click="model=[...new Set([...model,...choices])]">Select shown</button><button type="button" :disabled="disabled||!model.length" @click="model=[]">Clear</button></div>
        <div class="crm-source-list"><label v-for="source in choices" :key="source"><input type="checkbox" :disabled="disabled" :checked="model.includes(source)" @change="toggle(source)"><span>{{source}}</span></label><p v-if="!choices.length">No matching sources.</p></div>
      </div>
    </details>
    <div v-if="model.length" class="crm-selected-sources"><button v-for="source in model" :key="source" type="button" :disabled="disabled" :aria-label="'Remove '+source" @click="toggle(source)">{{source}} <span aria-hidden="true">×</span></button></div>
    <small v-else>Select one or more sources using the checkboxes.</small>
  </div>
</template>
