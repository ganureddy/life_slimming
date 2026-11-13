<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';
import CCMaskedPhone from '../CCMaskedPhone.vue';

const { maskPhone, from, to, error, duplicatePages, duplicateVisible, filters, openDuplicateLead, duplicateLoading, duplicateError, duplicateSearch, duplicatePage, duplicateFiltered, loadDuplicateLeads } = toRefs(inject(ccDashboardKey));
</script>

<template>
<section class="cc-card"><header>🧬 Duplicate Leads <span>({{from}} → {{to}})</span><button class="cc-outline" :disabled="duplicateLoading" @click="loadDuplicateLeads">{{duplicateLoading?'Loading…':'↻ Refresh'}}</button></header><p class="cc-note">Duplicate submissions in the selected date range. Find Original searches the lead by mobile number.</p><div class="cc-queue-filters"><input v-model="duplicateSearch" type="search" placeholder="Search name, phone or enquiry"><span>{{duplicateFiltered.length}} duplicate records</span></div><p v-if="duplicateLoading" role="status">Loading duplicate submissions…</p><p v-if="duplicateError" class="cc-error" role="alert">{{duplicateError}}</p><div class="tbl-wrap"><table class="cc-simple-table"><thead><tr><th>Name</th><th>Phone</th><th>Enquired For</th><th>Created</th><th>Action</th></tr></thead><tbody><tr v-for="row in duplicateVisible" :key="row.name"><td>{{row.name1||'—'}}</td><td>{{maskPhone(row.phone)}}</td><td>{{row.enquired_for||'—'}}</td><td>{{String(row.creation||'').slice(0,16)}}</td><td><button class="cc-primary" @click="openDuplicateLead(row)">Find Original</button></td></tr><tr v-if="!duplicateLoading&&!duplicateError&&!duplicateVisible.length"><td colspan="5">No duplicate leads in this date range.</td></tr></tbody></table></div><div class="cc-pager-row"><button :disabled="duplicatePage<=1" @click="duplicatePage--">Previous</button><span>Page {{duplicatePage}} of {{duplicatePages}}</span><button :disabled="duplicatePage>=duplicatePages" @click="duplicatePage++">Next</button></div></section>
</template>
