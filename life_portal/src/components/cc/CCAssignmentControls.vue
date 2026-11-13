<script setup>
import { computed, reactive, watch } from 'vue';
import { ccCall } from '../../api/cc';
import CRMSourceSelect from './CRMSourceSelect.vue';
import { activeCcAgents } from '../../lib/cc-agents';
const props=defineProps({config:Object});
const state=reactive({});
const agents=computed(()=>activeCcAgents(props.config?.agents||[]));
watch(()=>props.config,()=>{for(const key of Object.keys(state))delete state[key];});
function draft(agent){return state[agent.agent]||(state[agent.agent]={...agent,allowed_sources:[...(agent.allowed_sources||[])],busy:false,error:'',notice:''})}
async function save(agent){const row=draft(agent);row.busy=true;row.error='';row.notice='';try{const result=await ccCall('lead_assignment_configuration',{action:'save_agent',agent:agent.agent,auto_enabled:Number(row.auto_enabled),temporarily_stopped:Number(row.temporarily_stopped),use_conversion:Number(row.use_conversion),max_per_day:row.max_per_day,share_weight:row.share_weight,lead_sources:row.allowed_sources.join(', '),stop_reason:row.stop_reason,team_leader:row.team_leader||''});if(!result.saved)throw new Error('Assignment settings were not saved.');row.notice='Saved';}catch(error){row.error=error.message}finally{row.busy=false}}
</script>
<template>
<section v-if="config" class="assignment-editor">
  <div class="assignment-mode"><span>Mode: <b>{{config.settings?.assignment_mode}}</b></span><span>Hours: <b>{{config.settings?.start_time}} – {{config.settings?.end_time}}</b></span><span>Performance: <b>Last {{config.settings?.conversion_window_days}} days</b></span><span>Conversion Status: <b>{{config.settings?.conversion_statuses}}</b></span></div>
  <p class="assignment-rule"><b>Assignment rule:</b> Only an active Business Executive who is checked in, enabled, mapped to the Lead Source and below the daily limit is eligible. The lowest weighted assignment score receives the next lead.</p>
  <p v-if="!agents.length" class="crm-inline-notice">No active call-centre agents are configured.</p>
  <article v-for="agent in agents" :key="agent.agent" class="assignment-agent">
    <form @submit.prevent="save(agent)"><div class="assignment-fields">
      <div><small>AGENT &amp; ATTENDANCE</small><strong>{{agent.employee_name}}</strong><span>{{agent.agent}}</span><b class="assignment-attendance">{{agent.checked_in?'CHECKED IN':'NOT CHECKED IN'}}</b></div>
      <div class="assignment-sources"><small>ALLOWED LEAD SOURCES</small><CRMSourceSelect v-model="draft(agent).allowed_sources" :options="config.source_options||[]" :disabled="draft(agent).busy" :label="'Lead sources for '+agent.employee_name"/></div>
      <label><small>TODAY / DAILY LIMIT</small><div class="assignment-inline"><strong>{{agent.today_assigned||0}}</strong> / <input v-model.number="draft(agent).max_per_day" type="number" min="0" required></div><span>Assigned today / maximum</span></label>
      <div><small>CONVERSION PERFORMANCE</small><label class="assignment-inline"><input type="checkbox" v-model="draft(agent).use_conversion" :true-value="1" :false-value="0"> Use performance</label><label class="assignment-inline">Weight <input v-model.number="draft(agent).share_weight" type="number" min="0.01" step="0.01" required></label></div>
      <label><small>AUTO ASSIGNMENT</small><input class="assignment-switch" type="checkbox" v-model="draft(agent).auto_enabled" :true-value="1" :false-value="0"><span>Auto assign</span></label>
      <div><label><small>TEMPORARY STOP</small><input class="assignment-switch" type="checkbox" v-model="draft(agent).temporarily_stopped" :true-value="1" :false-value="0"></label><input v-if="draft(agent).temporarily_stopped" v-model="draft(agent).stop_reason" placeholder="Stop reason" aria-label="Stop reason"></div>
      <label v-if="config.is_manager"><small>TEAM LEADER</small><input v-model="draft(agent).team_leader" type="email" placeholder="Team leader user"></label>
    </div><footer><p v-if="draft(agent).error" role="alert">{{draft(agent).error}}</p><span v-if="draft(agent).notice" role="status">{{draft(agent).notice}}</span><button class="cc-primary" :disabled="draft(agent).busy">{{draft(agent).busy?'Saving…':'Save changes'}}</button></footer></form>
  </article>
</section>
</template>
