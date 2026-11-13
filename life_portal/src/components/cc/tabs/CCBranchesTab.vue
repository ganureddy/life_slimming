<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';

const { error, doctorLoading, doctorError, copyNotice, branches, copyText, loadDoctors, branchManager } = toRefs(inject(ccDashboardKey));
</script>

<template>
<section id="branches-area" class="card"><header class="card-hdr">🏥 Branch Directory — All Branches<button class="btn btn-gy btn-sm" :disabled="doctorLoading" @click="loadDoctors">↻ Refresh</button></header><div class="card-body"><p v-if="doctorLoading" role="status">Loading branch contacts…</p><p v-if="doctorError" class="cc-error" role="alert">{{doctorError}}</p><div class="cc-legacy-branch-grid"><article v-for="branch in branches" :key="branch.code" class="form-section"><div class="form-section-title">🏥 {{branch.name}} ({{branch.code}}) — {{branch.city}}</div><div class="cc-branch-details"><div>📍 {{branch.address}}</div><div>📞 {{branch.phone}}</div><div>🕐 {{branch.hours}}</div><div>👤 Center Manager: <strong>{{branchManager(branch.name)}}</strong></div><div>👥 ACM: <strong>{{branchManager(branch.name,true)}}</strong></div></div><div class="btn-row"><a class="btn btn-teal btn-sm" :href="branch.maps" target="_blank" rel="noopener">🗺️ Open Maps</a><button class="copy-btn" @click="copyText(`${branch.name} (${branch.city})\n${branch.address}\n${branch.phone}\n${branch.hours}\n${branch.maps}`)">📋 Copy Location + Map Link</button></div></article></div></div></section><p v-if="copyNotice" class="cc-success" role="status">{{copyNotice}}</p>
</template>
