<script setup>
import { computed, ref } from 'vue';
import data from '../../data/unjoined.json';
import { phoneField, maskText } from '../../lib/unjoined';
import ClientPhoto from './ClientPhoto.vue';
const props = defineProps({ context: Object, draft: Object, branches: Array, manager: Boolean, saving: Boolean, dirty: Boolean, notice: String, legacyChoice: String });
const emit = defineEmits(['change', 'field', 'photo', 'legacy', 'save']);
const form = ref(null);
const original = computed(() => props.context.form || props.context.defaults);
const branchOptions = computed(() => [...new Set([...props.branches, props.draft.branch].filter(Boolean))]);
const nextRequired = computed(() => props.draft.status === 'Follow Up Scheduled');
function changed(field, value) { emit('field', field, value); emit('change'); }
function submit() { if (form.value.reportValidity()) emit('save'); }
</script>

<template>
  <template v-if="context">
    <div class="uj-follow-hero">
      <ClientPhoto :value="original.custom_client_photo_attach || context.source.custom_client_photo_attach || context.source.image" large />
      <div><small>UNJOINED CLIENT FORM</small><h3>{{ maskText(original.client_name || context.source.name || 'Follow-up', manager) }}</h3><p>{{ context.form ? 'Editing saved follow-up record · ' + maskText(context.form.name, manager) : 'New follow-up record' }}</p></div>
    </div>
    <p class="uj-help">Save these fields to Unjoined Client Form.</p>
    <p v-if="context.lookupError" class="uj-error">{{ context.lookupError }}</p>
    <div v-if="context.legacy.length" class="uj-legacy">
      <b>Existing forms with the same phone and branch</b><p>Select a matching record to edit and link it, or leave “Create new”.</p>
      <select id="ujLegacySelect" :value="legacyChoice" :disabled="saving" @change="emit('legacy', $event.target.value)"><option value="">Create new follow-up</option><option v-for="row in context.legacy" :key="row.name" :value="row.name">{{ maskText(row.client_name, manager) }} · {{ maskText(row.name, manager) }}</option></select>
    </div>
    <form id="ujEditForm" ref="form" @submit.prevent="submit">
      <fieldset :disabled="saving" class="uj-edit-grid">
        <label v-for="field in data.followFields" :key="field.fieldname" :for="'ujEdit-' + field.fieldname" :class="{ 'uj-wide': /Text/.test(field.fieldtype), 'uj-required': field.fieldname === 'next_follow_up_scheduled_date' && nextRequired }">
          <span>{{ field.label }} <em v-if="field.reqd || (field.fieldname === 'next_follow_up_scheduled_date' && nextRequired)">*</em></span>
          <select v-if="field.fieldtype === 'Select'" :id="'ujEdit-' + field.fieldname" :value="draft[field.fieldname]" :required="!!field.reqd" @change="changed(field.fieldname, $event.target.value)"><option v-for="option in (field.options || '').split('\n')" :key="option" :value="option">{{ option || 'Select…' }}</option></select>
          <select v-else-if="field.fieldname === 'branch'" :id="'ujEdit-' + field.fieldname" :value="draft.branch" :required="!!field.reqd" @change="changed(field.fieldname, $event.target.value)"><option value="">Select branch…</option><option v-for="branch in branchOptions" :key="branch">{{ branch }}</option></select>
          <textarea v-else-if="/Text/.test(field.fieldtype)" :id="'ujEdit-' + field.fieldname" :value="draft[field.fieldname]" rows="3" :required="!!field.reqd" @input="changed(field.fieldname, $event.target.value)"></textarea>
          <input v-else :id="'ujEdit-' + field.fieldname" :value="draft[field.fieldname]" :type="field.fieldtype === 'Date' ? 'date' : field.fieldtype === 'Time' ? 'time' : 'text'" :inputmode="phoneField(field.fieldname) ? 'tel' : undefined" :readonly="!manager && phoneField(field.fieldname)" :aria-readonly="!manager && phoneField(field.fieldname) ? true : undefined" :required="!!field.reqd || (field.fieldname === 'next_follow_up_scheduled_date' && nextRequired)" @input="changed(field.fieldname, $event.target.value)">
        </label>
        <label class="uj-wide">Client Photo<input id="ujPhotoFile" type="file" accept="image/jpeg,image/png,image/webp" @change="emit('photo', $event.target.files[0] || null); emit('change')"><small>JPEG, PNG or WebP · up to 10 MB</small></label>
      </fieldset>
      <div class="uj-save-bar"><span id="ujSaveState" role="status" :class="{ 'uj-success': notice.startsWith('Saved successfully'), 'uj-error': notice.startsWith('Not saved') || notice.includes('could not') }">{{ notice }}</span><button id="ujSaveForm" type="submit" class="uj-primary" :disabled="saving || !!context.lookupError">{{ saving ? 'Saving…' : 'Save Follow-up' }}</button></div>
    </form>
  </template>
</template>
