<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';
import { session } from '../../../lib/session';
import { maskPhone } from '../../../lib/cc';
const { createForm, createBusy, createError, createDuplicate, createMastersLoading, createSources, createBranches, createCategories, createOwners, canEditLeadOwner, tlConfigError, createLead, openDetail, showView } = toRefs(inject(ccDashboardKey));
</script>

<template>
  <section class="crm-create-screen" aria-labelledby="create-title">
    <header class="crm-page-heading"><div><span class="crm-eyebrow">CONTACTS &amp; ENQUIRIES</span><h1 id="create-title">Create a lead</h1><p>Add contact and enquiry details to start the follow-up journey.</p></div><button type="button" class="btn btn-gy" :disabled="createBusy" @click="showView('queue')">Back to lead queue</button></header>
    <form class="crm-create-form" @submit.prevent="createLead">
      <p v-if="createMastersLoading" class="crm-inline-notice" role="status">Loading enquiry options…</p>
      <section class="crm-form-section"><header><span class="crm-section-number">1</span><div><h2>Contact details</h2><p>The mobile number is checked for an existing lead.</p></div></header><div class="crm-field-grid">
        <label>Full name <span class="req">*</span><input v-model="createForm.first_name" name="first_name" autocomplete="name" placeholder="Client’s full name" required></label>
        <label>Mobile number <span class="req">*</span><input v-model="createForm.mobile_no" name="mobile_no" type="tel" inputmode="numeric" maxlength="10" pattern="[6-9][0-9]{9}" autocomplete="tel-national" placeholder="10-digit mobile number" required></label>
        <label>Alternate number<input v-model="createForm.phone" type="tel" inputmode="numeric" maxlength="10" placeholder="Optional alternate number"></label>
        <label>Email address<input v-model="createForm.email_id" type="email" autocomplete="email" placeholder="name@example.com"></label>
        <label>Age<input v-model="createForm.age" type="number" min="1" max="120" placeholder="Age in years"></label>
        <label>Gender<select v-model="createForm.gender"><option value="">Select gender</option><option>Male</option><option>Female</option><option>Other</option></select></label>
      </div></section>
      <section class="crm-form-section"><header><span class="crm-section-number">2</span><div><h2>Enquiry details</h2><p>Choose the source, branch, and treatment interest.</p></div></header><div class="crm-field-grid">
        <label>Lead source <span class="req">*</span><select v-model="createForm.source" name="source" :disabled="createMastersLoading" required><option value="">Select lead source</option><option v-for="source in createSources" :key="source">{{source}}</option></select></label>
        <label>Preferred branch <span class="req">*</span><select v-model="createForm.branch" name="branch" :disabled="createMastersLoading" required><option value="">Select branch</option><option v-for="branch in createBranches" :key="branch">{{branch}}</option></select></label>
        <label>Client area<input v-model="createForm.city" placeholder="Area or locality"></label>
        <label>Treatment category<select v-model="createForm.category"><option value="">Select category</option><option v-for="category in createCategories" :key="category">{{category}}</option></select></label>
        <label>Enquired for<input v-model="createForm.enquired_for" placeholder="Treatment or concern"></label>
        <label>Assigned agent<select v-if="canEditLeadOwner" v-model="createForm.lead_owner" :disabled="createMastersLoading"><option value="">Auto-assign to an eligible agent</option><option v-for="owner in createOwners" :key="owner.id" :value="owner.id">{{owner.name}}</option></select><input v-else :value="session.full_name||session.user" disabled></label>
        <label class="crm-field-wide">Enquiry notes<textarea v-model="createForm.custom_remarks" rows="4" placeholder="Add the client’s concern or anything useful for the first call."></textarea></label>
      </div></section>
      <p v-if="tlConfigError&&canEditLeadOwner" class="crm-inline-notice" role="status">{{tlConfigError}}</p>
      <div v-if="createDuplicate" class="crm-duplicate-notice" role="alert"><div><strong>This mobile number already has a lead</strong><p>{{createDuplicate.lead_name||createDuplicate.name}} · {{maskPhone(createDuplicate.mobile_no)}}</p></div><button type="button" class="btn btn-g" @click="openDetail(createDuplicate)">Open existing lead</button></div>
      <p v-if="createError" class="cc-error" role="alert">{{createError}}</p>
      <footer class="crm-form-footer"><p>Fields marked <span class="req">*</span> are required. New leads start in the lead queue.</p><div><button type="button" class="btn btn-gy" :disabled="createBusy" @click="showView('queue')">Cancel</button><button type="submit" class="btn btn-g" :disabled="createBusy||createMastersLoading">{{createBusy?'Creating lead…':'Create lead'}}</button></div></footer>
    </form>
  </section>
</template>
