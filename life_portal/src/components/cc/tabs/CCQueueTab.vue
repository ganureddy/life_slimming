<script setup>
import { computed, inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';
import CCJourneyChips from '../CCJourneyChips.vue';
import CCMaskedPhone from '../CCMaskedPhone.vue';
import CCPager from '../CCPager.vue';

const { journeyFlags, rows, total, page, searching, scoped, queueOwner, queueFlag, queueFlags, journeys, journeyError, matrixFilter, queueStatus, queueCategory, queueSubStatus, queueSearch, loading, error, applied, viewLead, callOutcomes, treatmentCategories, queuePageRows, pages, visibleLeads, load, openDetail, assignOwners } = toRefs(inject(ccDashboardKey));
const mainFlags = computed(() => journeyFlags.value.filter(([value]) => ['Interested', 'Appointment Booked', 'Appointment Missed', 'Visited', 'Visited & Booked', 'Visited - Not Booked'].includes(value)));
const flagLabel = computed(() => queueFlags.value.length ? `${queueFlags.value.length} main status${queueFlags.value.length === 1 ? '' : 'es'} selected` : 'All main statuses');
function clearFilters() { queueFlag.value=''; queueFlags.value=[]; matrixFilter.value=null; queueOwner.value=''; queueStatus.value=''; queueSubStatus.value=''; queueCategory.value=''; queueSearch.value=''; }
</script>

<template>
  <p v-if="journeyError" role="alert" class="cc-error">{{journeyError}}</p>
  <div class="cc-queue-toolbar"><span class="cc-status-line">{{ loading ? 'Loading leads…' : searching ? rows.length + ' matches on this page' : total + ' matching leads' }} · {{ applied }}<span v-if="scoped"> · Your assigned leads</span></span><span class="cc-quick-links"><button @click="load(page)">↻ Refresh</button></span></div>
  <div id="cc-ml-filterbar" class="cc-queue-filters">
    <select class="cc-main-status-select" v-model="queueFlag" aria-label="Main status"><option value="">🚩 All main statuses</option><option v-for="[value,label] in mainFlags" :key="value" :value="value">{{label}}</option></select>
    <select id="cc-ml-owner" v-model="queueOwner" aria-label="Filter by agent"><option value="">All Agents</option><option v-for="owner in assignOwners" :key="owner.id" :value="owner.id">{{owner.name}}</option></select>
    <select id="cc-ml-status" v-model="queueStatus" aria-label="Lead status"><option value="">All Status</option><option>UNTOUCHED</option><option>FOLLOW-UP</option><option>SUCCESS</option><option>LOST</option><option>INVALID</option></select>
    <select v-model="queueSubStatus" aria-label="Call result"><option value="">All Call Results</option><option value="NOT_RESPONDING">No Response / Not Reachable / Disconnected</option><option v-for="result in callOutcomes" :key="result">{{result}}</option></select>
    <select v-model="queueCategory" aria-label="Treatment category"><option value="">All Categories</option><option v-for="category in treatmentCategories" :key="category">{{category}}</option></select>
    <button class="btn btn-gy btn-sm" @click="clearFilters">Clear</button>
  </div>
  <section class="card"><header class="card-hdr">📋 My Lead Queue <span class="badge">{{visibleLeads.length}}</span></header><div id="my-leads-list" class="card-body"><p class="cc-status-line">{{searching?'Search page '+page+' · '+visibleLeads.length+' matches on this page':'Showing '+(visibleLeads.length?(page-1)*10+1:0)+'–'+Math.min(page*10,visibleLeads.length)+' of '+visibleLeads.length+' leads'}}</p><article v-for="row in queuePageRows" :key="row.name" class="queue-item wf-qrow"><div class="wf-q-main"><div class="wf-q-l1"><strong class="wf-q-name">{{row.lead_name||row.name}}</strong><span class="wf-f ag">👤 {{row.lead_owner_name||row.lead_owner||'Unassigned'}}</span><span class="wf-f st">Last status: {{row.custom_cc_sub_status||row.custom_appointment_status||row.custom_cc_stage||row.status||'New'}}</span><small>{{row.name}}</small></div><CCJourneyChips :summary="journeys[row.name]"/><div class="wf-q-l2">📞 <CCMaskedPhone :number="row.mobile_no"/> · 📍 {{row.city||'—'}} · 📡 {{row.source||'—'}} · 🗓 {{String(row.creation||'').slice(0,10)}} · 📞×{{row.custom_call_count||0}}</div><div class="wf-q-l1"><span v-if="row.custom_treatment_interests" class="wf-f">{{row.custom_treatment_interests}}</span><span v-if="row.branch||row.lead_assign_to_branch" class="wf-f br">🏥 {{row.branch||row.lead_assign_to_branch}}</span><span v-if="row.custom_next_followup_date" class="wf-f fu">📅 {{row.custom_next_followup_date}}</span><span v-if="row.custom_appointment_date_and_time" class="wf-f ap">📅 Appt: {{row.custom_appointment_date_and_time}}</span></div><p v-if="row.custom_conclusion_remark" class="wf-q-l2">💬 {{row.custom_conclusion_remark}}</p></div><div class="wf-q-side"><button class="wf-q-btn" @click="openDetail(row)">📞 Call &amp; Update</button><button class="btn btn-gy btn-sm" @click="viewLead(row)">👁 View</button></div></article><p v-if="!loading&&!error&&!visibleLeads.length" class="cc-empty-state">No leads match the selected filter.</p></div></section>
  <CCPager :page="page" :pages="pages" :busy="loading" @change="searching?load($event):page=$event" />
</template>
