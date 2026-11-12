<script setup>
import { ref,watch,onBeforeUnmount } from 'vue';
import {useRoute} from 'vue-router';
import {watchVisibleReport} from '../../lib/cc-visible-report';
import { request } from '../../api/http';
import { session } from '../../lib/session';
const route=useRoute();
const props=defineProps({from:String,to:String});const emit=defineEmits(['open','loaded']);
const rows=ref([]),total=ref(0),page=ref(0),busy=ref(false),error=ref('');const loaded=ref(false);let controller,generation=0;
async function load(){const token=++generation;controller?.abort();controller=new AbortController();rows.value=[];error.value='';busy.value=true;try{const body=await request('life_slimming.api.cc_untouched.run',{args:{from_date:props.from,to_date:props.to,start:page.value*50},csrfToken:session.csrf_token,signal:controller.signal});if(token!==generation)return;rows.value=body.message.rows;total.value=body.message.total;loaded.value=true;emit('loaded',body.message);}catch(e){if(token===generation&&e.name!=='AbortError')error.value=e.message;}finally{if(token===generation)busy.value=false;}}
watch(()=>[props.from,props.to],()=>{page.value=0;});
watchVisibleReport(()=>[props.from,props.to,page.value],()=>route.meta.reportTab==='agents'&&route.meta.agentSubtab==='untouched',load,()=>!error.value&&loaded.value);onBeforeUnmount(()=>{generation++;controller?.abort();});
</script>
<template><section class="cc-card"><h2>Untouched leads · {{total}}</h2><p v-if="error" class="cc-error" role="alert">{{error}}</p><p v-if="busy" role="status">Loading untouched leads…</p><div class="cc-table"><table><thead><tr><th>Client</th><th>Lead</th><th>Phone</th><th>Agent</th><th>Received</th></tr></thead><tbody><tr v-for="row in rows" :key="row.name"><td>{{row.lead_name}}</td><td><button @click="emit('open',row.name)">{{row.name}}</button></td><td>{{row.phone}}</td><td>{{row.agent_name}}</td><td>{{row.creation}}</td></tr><tr v-if="!rows.length&&!busy"><td colspan="5">No untouched leads in this range.</td></tr></tbody></table></div><button :disabled="busy||!page" @click="page--">Previous</button><span> {{page+1}} / {{Math.max(1,Math.ceil(total/50))}} </span><button :disabled="busy||(page+1)*50>=total" @click="page++">Next</button></section></template>
