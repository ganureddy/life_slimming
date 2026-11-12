<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';

const { error, doctorRows, doctorLoading, doctorError, doctorBranches, loadDoctors } = toRefs(inject(ccDashboardKey));
</script>

<template>
<section id="doctors-area" class="card"><header class="card-hdr">👨‍⚕️ Doctor Directory <span class="badge">{{doctorRows.length}}</span><button class="btn btn-gy btn-sm" :disabled="doctorLoading" @click="loadDoctors">↻ Refresh</button></header><div class="card-body"><p v-if="doctorLoading" role="status">Loading doctor directory…</p><p v-if="doctorError" class="cc-error" role="alert">{{doctorError}}</p><section v-for="branch in doctorBranches" :key="branch" class="cc-doctor-branch"><div class="form-section-title">🏥 {{branch}} ({{doctorRows.filter(row=>(row.branch||'Head Office / Unassigned')===branch).length}})</div><div class="tbl-wrap"><table><thead><tr><th>Doctor</th><th>Designation</th><th>Contact</th><th>Emp ID</th></tr></thead><tbody><tr v-for="doctor in doctorRows.filter(row=>(row.branch||'Head Office / Unassigned')===branch)" :key="doctor.name"><td><strong>{{doctor.employee_name}}</strong></td><td><span class="pill" :class="({'Chief HT Surgeon':'p-red','HOD Hair transplant surgery':'p-red','Consultant Doctor':'p-gold',Doctor:'p-blue','Assistant Doctor':'p-teal',Dermatologist:'p-green'})[doctor.designation]||'p-gy'">{{doctor.designation}}</span></td><td>{{doctor.cell_number||'—'}}</td><td class="cc-employee-id">{{doctor.name}}</td></tr></tbody></table></div></section><p v-if="!doctorLoading&&!doctorRows.length" class="cc-empty-state">Doctor data not available for this login.</p></div></section>
</template>
