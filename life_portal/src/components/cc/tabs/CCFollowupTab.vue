<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';
import CCDataTable from '../CCDataTable.vue';
import CCPager from '../CCPager.vue';
import CCLeadWorksheet from '../CCLeadWorksheet.vue';
const { createSources, createOwners, enquiryDate, enquiryLabel, rows, page, query, searching, apply, showView, contactManager, loading, error, detail, detailLoading, detailError, followup, savingFollowup, actionError, actionNotice, leadDraft, selectedCategories, selectedInterests, startCall, openPhone, callClock, callRunning, columns, pages, load, openDetail, closeDetail, recoverJunk, saveFollowup } = toRefs(inject(ccDashboardKey));
</script>

<template>
  <template v-if="!detail">
    <section class="card crm-followup-search" aria-labelledby="followup-search-title">
      <header class="card-hdr"><span id="followup-search-title">📞 Lead Follow-Up Form</span><button type="button" class="btn btn-gy btn-sm" @click="showView('queue')">← Go to lead queue</button></header>
      <div class="card-body"><p>Find a client to open their follow-up form, or choose a lead from your queue.</p><form class="crm-lead-search-row" @submit.prevent="apply"><label class="crm-search-field"><span>Client name, mobile number or Lead ID</span><input v-model="query" type="search" placeholder="Search across permitted lead history" autocomplete="off" minlength="2" required></label><button class="btn btn-g" :disabled="loading">{{loading?'Searching…':'Find lead'}}</button></form></div>
    </section>
    <section v-if="searching" class="card crm-followup-results"><header class="card-hdr">Search results <span class="badge">{{rows.length}}</span></header><div class="card-body"><CCDataTable :columns="columns" :rows="rows" :busy="loading"><template #actions="{row}"><button class="btn btn-g btn-sm" @click="openDetail(row)">Open follow-up form</button></template></CCDataTable><CCPager :page="page" :pages="pages" :busy="loading" @change="load" /></div></section>
    <section v-else class="card crm-followup-empty"><div class="card-body"><span class="crm-empty-icon" aria-hidden="true">📋</span><h2>No lead selected</h2><p>Choose a lead from your queue to review their details, record the call outcome, and schedule the next action.</p><button class="btn btn-g" @click="showView('queue')">Open my lead queue →</button></div></section>
  </template>
  <template v-else>
    <p v-if="detailLoading" role="status">Loading lead…</p><p v-else-if="detailError" class="cc-error" role="alert">{{detailError}}</p>
    <button v-if="['Junk/Wrong Call','Not Enquired'].includes(detail.custom_cc_sub_status)" class="btn btn-gy btn-sm" @click="recoverJunk(detail)">Unlock junk lead</button>
    <p v-if="enquiryLabel(detail)" class="cc-note"><strong>{{enquiryLabel(detail)}}</strong> · Enquiry date: {{enquiryDate(detail)}} · Original lead: {{detail.name}} · Assigned to: {{detail.lead_owner||'Unassigned'}}</p>
    <CCLeadWorksheet v-if="!detailLoading&&!detailError" :lead="detail" :sources="createSources" :owners="createOwners" :call-clock="callClock" :call-running="callRunning" :manager="contactManager" :busy="savingFollowup" :error="actionError" :notice="actionNotice" v-model:draft="leadDraft" v-model:followup="followup" v-model:categories="selectedCategories" v-model:interests="selectedInterests" @lead-modified="detail.modified=$event" @save="saveFollowup" @back="closeDetail" @start-call="startCall" @stop-call="openPhone" />
  </template>
</template>
