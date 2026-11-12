<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue';
import { ccCore } from '../../api/cc-core';
const props=defineProps({lead:Object});
const timelineMore=ref(false),timelineCapped=ref(false);
const summary=ref(null),header=ref(null),events=ref([]),matches=ref(null),number=ref(''),error=ref(''),busy=ref(false),expanded=ref(false),matching=ref(false);
const emit=defineEmits(['changed','summary','header']);let generation=0;
watch(()=>props.lead?.name,async()=>{const token=++generation;summary.value=null;header.value=null;events.value=[];matches.value=null;expanded.value=false;matching.value=false;error.value='';try{const data=await ccCore('header',{lead:props.lead.name});if(token!==generation)return;header.value=data;summary.value=data.summary;emit('header',data);emit('summary',data.summary);}catch(e){if(token===generation)error.value=e.message;}},{immediate:true});
onBeforeUnmount(()=>generation++);
async function action(kind,args={}){busy.value=true;error.value='';const token=generation;try{const data=await ccCore(kind,{lead:props.lead.name,...args});if(token!==generation)return;if(data.summary){summary.value=data.summary;emit('summary',data.summary);}if(kind==='timeline'){events.value=args.start?[...events.value,...(data.events||[])]:data.events||[];timelineMore.value=!!data.more;timelineCapped.value=!!data.capped;expanded.value=true;}if(kind==='match'){matches.value=data;matching.value=true;}if(kind==='add_number'){emit('changed',data.modified);number.value='';await action('match');}if(kind==='match_verify'){await action('match');}}catch(e){if(token===generation)error.value=e.message;}finally{busy.value=false;}}
const palette = {
  'Joined Client':['#166534','#dcfce7','🏆','JOINED CLIENT'],
  'Booked - Payment Pending':['#a16207','#fef9c3','💳','BOOKED · PAYMENT PENDING'],
  Visited:['#1d4ed8','#dbeafe','🏥','VISITED'],
  'Visited - Not Booked':['#0f766e','#ccfbf1','🚶','VISITED · NOT BOOKED'],
  'Appointment Booked':['#b45309','#ffedd5','📅','APPOINTMENT BOOKED'],
  'Appointment Missed':['#b91c1c','#fee2e2','⏰','APPOINTMENT MISSED'],
  Interested:['#6d28d9','#ede9fe','💬','INTERESTED'],
  Contacted:['#475569','#e2e8f0','📞','CONTACTED'],
  New:['#6b7280','#f3f4f6','⚪','NEW LEAD'],
};
const tone=computed(()=>{
  const value=summary.value||{};
  if (/^(DNC|LOST|INVALID)$/.test(value.protected||'')||/^(Do not contact|Closed)/.test(value.next_action||''))return ['#111827','#e5e7eb','⛔','CLOSED · '+(value.protected==='DNC'?'DO NOT CONTACT':value.protected||'LOST')];
  return palette[value.milestone]||palette.New;
});
const milestoneClass=computed(()=>'lcx-ms-'+String(summary.value?.milestone||'').replace(/[^A-Za-z]+/g,'-'));
function formatDate(value){if(!value)return '—';const raw=String(value).replace(' ','T');const date=new Date(/(?:Z|[+-]\d{2}:?\d{2})$/.test(raw)?raw:raw+'+05:30');return Number.isFinite(date.getTime())?new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',day:'numeric',month:'short',year:'numeric',hour:'numeric',minute:'2-digit'}).format(date):String(value);}
</script>
<template>
<div class="cc-journey" aria-label="Lead journey">
  <div v-if="summary" class="lcx-strip">
    <div v-if="summary.milestone==='Appointment Missed'" class="lcx-warnbar lcx-wb-r" role="status">🚨 APPOINTMENT NO-SHOW: booked for {{summary.branch_code||''}} {{formatDate(summary.appt_at)}} <small>— call now, re-book a new slot</small></div>
    <div v-else-if="summary.milestone==='Visited - Not Booked'" class="lcx-warnbar lcx-wb-t" role="status">🏥 VISITED – NOT BOOKED <small>— closing call: ask what stopped them, offer the plan</small></div>
    <div class="lcx-title" :style="{background:tone[1],borderColor:tone[0]}">
      <span class="lcx-tl-k">PRESENT STATUS</span><span class="lcx-tl-v" :style="{color:tone[0]}">{{tone[2]}} {{tone[3]}}</span>
      <span v-if="summary.booked||summary.missed||summary.visited" class="lcx-tl-s">Booked {{summary.booked||0}} · Missed {{summary.missed||0}} · Visited {{summary.visited||0}}</span>
      <span class="lcx-tl-n" :style="{background:tone[0]}">➡ {{summary.milestone==='Joined Client'?'Feedback calls only':summary.next_action||'Call now'}}<template v-if="summary.next_action_due&&summary.milestone!=='Joined Client'"> · {{formatDate(summary.next_action_due)}}</template></span>
    </div>
    <div class="lcx-box" :class="milestoneClass"><div class="lcx-k">🏅 Milestone</div><b>{{summary.milestone}}</b><small v-if="summary.paid">Joined {{formatDate(summary.joined_on)}} · paid ₹{{Number(summary.paid).toLocaleString('en-IN')}}</small><small>{{summary.booked||summary.missed||summary.visited?`Booked ${summary.booked||0} · Missed ${summary.missed||0} · Visited ${summary.visited||0}`:'No appointment history'}}</small><small v-if="summary.protected">🔒 {{summary.protected}} — not auto-moved</small></div>
    <div class="lcx-box" :class="summary.last_call_result&&summary.last_call_result!=='Connected'?'lcx-bad':summary.last_call_result?'lcx-ok':''"><div class="lcx-k">📞 Last call</div><b>{{summary.last_call_result||'No call yet'}}</b><small>{{formatDate(summary.last_call_at)}}<template v-if="summary.unreachable_streak"> · {{summary.unreachable_streak}} unreachable in a row</template></small></div>
    <div class="lcx-box lcx-ok"><div class="lcx-k">➡️ Next action</div><b>{{summary.next_action||'Call now'}}</b><small>{{summary.next_action_due?'Due '+formatDate(summary.next_action_due):'No due time'}}</small><button type="button" class="lcx-tlbtn" :disabled="busy" @click="action('timeline')">🕘 Full timeline</button></div>
  </div>
  <p v-if="error" role="alert" class="wf-review">{{error}}</p><p v-if="busy" role="status">Loading…</p>
  <div v-if="expanded" class="lcx-tl"><button type="button" class="lcx-tlbtn" @click="expanded=false">Close timeline</button><div v-for="(event,i) in events" :key="i"><small>{{formatDate(event.at)}} · {{event.by}}</small><b>{{event.kind}}</b> {{event.from}} → {{event.to}}</div><p v-if="!events.length">No activity recorded.</p><button v-if="timelineMore" type="button" class="lcx-tlbtn" :disabled="busy" @click="action('timeline',{start:events.length})">Load older history</button><p v-if="timelineCapped">This timeline reached its display limit.</p></div>
  <form v-if="summary?.milestone!=='Joined Client'" class="lcx-join" @submit.prevent="action('add_number',{number})"><b>🔎 Joined with another number?</b> <input v-model="number" class="lcx-num" aria-label="Additional contact number" placeholder="Add client's other mobile (10 digits)" inputmode="numeric" pattern="[0-9]{10}" maxlength="10" required><button class="lcx-tlbtn" :disabled="busy">＋ Add number</button> <button type="button" class="lcx-tlbtn" :disabled="busy" @click="action('match')">Check branch records</button>
    <div v-if="matching" class="lcx-mres"><article v-for="match in matches?.matches||[]" :key="match.patient" class="lcx-m"><strong>{{match.name}} · {{match.patient}}</strong><span>{{match.branch}} · ••••{{match.mobile_last4}} · Paid ₹{{match.paid}} · {{match.status}}</span><template v-if="matches.can_verify"><button type="button" class="lcx-tlbtn" :disabled="busy" @click="action('match_verify',{patient:match.patient,decision:'Verified'})">Verify same client</button><button type="button" class="lcx-tlbtn" :disabled="busy" @click="action('match_verify',{patient:match.patient,decision:'Rejected'})">Different client</button></template></article><p v-if="!matches?.matches?.length">No matching branch client found.</p></div>
  </form>
</div>
</template>
