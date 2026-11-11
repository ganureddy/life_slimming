<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue';
import { dateRange } from '../../lib/cc';
import { request } from '../../api/http';
import { session } from '../../lib/session';
defineEmits(['open']);
const [today]=dateRange('today');
const from=ref(today),to=ref(today),rows=ref([]),busy=ref(false),error=ref(''),offset=ref(0),more=ref(false);
let generation=0;
async function load(start=0){
  const token=++generation;
  error.value='';rows.value=[];more.value=false;
  if(!from.value||!to.value||from.value>to.value){error.value='Choose a valid date range.';busy.value=false;return;}
  busy.value=true;
  try{
    const response=await request('life_slimming.api.cc_access.lead_updates',{args:{from_date:from.value,to_date:to.value,start},csrfToken:session.csrf_token});
    if(token!==generation)return;
    rows.value=response.message.rows;more.value=response.message.more;offset.value=start;
  }catch(e){if(token===generation)error.value=e.message||'Could not load lead updates.';}
  finally{if(token===generation)busy.value=false;}
}
onMounted(()=>load());
onBeforeUnmount(()=>generation++);
</script>
<template>
<section class="cc-card"><header>Latest lead updates</header>
<form class="cc-queue-filters" @submit.prevent="load()"><label>From <input v-model="from" type="date" required></label><label>To <input v-model="to" type="date" required></label><button :disabled="busy">Apply</button></form>
<p class="cc-note">Saved lead changes, newest first. Dates and times are in the site time zone.</p>
<p v-if="busy" role="status">Loading lead updates…</p><p v-if="error" role="alert">{{error}}</p>
<div class="tbl-wrap"><table class="cc-simple-table"><thead><tr><th>Updated on</th><th>Lead</th><th>Updated by</th><th>Assigned agent</th><th>Changes</th></tr></thead><tbody><tr v-for="row in rows" :key="row.name"><td>{{row.creation}}</td><td><button type="button" @click="$emit('open',row.lead)">{{row.lead_name||row.lead}}</button><div>{{row.lead}}</div></td><td>{{row.owner}}</td><td>{{row.lead_owner||'Unassigned'}}</td><td><div v-for="(change,index) in row.changes" :key="index"><strong>{{change.label}}:</strong> {{change.before??'—'}} → {{change.after??'—'}}</div><span v-if="!row.changes.length">Lead details updated</span></td></tr></tbody></table></div>
<p v-if="!busy&&!error&&!rows.length">No saved lead updates in this date range.</p>
<div class="cc-pager-row"><button :disabled="busy||!offset" @click="load(offset-50)">Previous</button><span>Page {{Math.floor(offset/50)+1}}</span><button :disabled="busy||!more" @click="load(offset+50)">Next</button></div>
</section>
</template>
