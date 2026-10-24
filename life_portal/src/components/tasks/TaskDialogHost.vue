<script setup>
import { nextTick, reactive, ref } from 'vue';
import { sanitizeRichText } from '../../lib/rich-text';
const opened = ref([]), users = ref([]);
let sequence = 0, disposed = false;
const inputNodes = new Map(), wrapperNodes = new Map();
const key = (dialog, field) => `${dialog.id}-${field.fieldname}`;
function hide(dialog, cancelled = false) {
  opened.value = opened.value.filter(item => item.id !== dialog.id);
  for (const field of dialog.fields) { inputNodes.delete(key(dialog, field)); wrapperNodes.delete(key(dialog, field)); }
  if (cancelled) dialog.options.secondary_action?.();
}
function create(options) {
  const dialog = reactive({ id: ++sequence, options, fields: (options.fields || []).map(field => ({ ...field })), values: {}, error: '' });
  for (const field of dialog.fields) if (field.fieldtype !== 'HTML') dialog.values[field.fieldname] = field.default ?? '';
  const api = {
    fields_dict: {},
    get_value: name => inputNodes.get(`${dialog.id}-${name}`)?.value ?? dialog.values[name],
    set_value: (name, value) => { dialog.values[name] = value; },
    hide: () => hide(dialog),
    show: async () => {
      if (disposed || opened.value.some(item => item.id === dialog.id)) return;
      opened.value.push(dialog); await nextTick();
      for (const field of dialog.fields) api.fields_dict[field.fieldname] = {
        $input: [inputNodes.get(key(dialog, field))],
        $wrapper: { 0: wrapperNodes.get(key(dialog, field)), html: html => { field.options = html; } },
      };
      inputNodes.get(key(dialog, dialog.fields.find(field => field.fieldtype !== 'HTML') || {}))?.focus();
    },
  };
  dialog.api = api;
  return api;
}
function submit(dialog) {
  dialog.error = '';
  const values = {};
  for (const field of dialog.fields) {
    if (field.fieldtype === 'HTML') continue;
    const value = dialog.api.get_value(field.fieldname);
    if (field.reqd && !String(value ?? '').trim()) { dialog.error = `${field.label} is required.`; return; }
    values[field.fieldname] = field.fieldtype === 'Int' && value !== '' ? Number(value) : value;
  }
  dialog.options.primary_action?.(values);
}
function confirm(message, yes, no) {
  const dialog = create({ title: 'Confirm', fields: [{ fieldtype: 'HTML', fieldname: 'message', options: message }],
    primary_action_label: 'Yes', secondary_action_label: 'No', secondary_action: no,
    primary_action: () => { dialog.hide(); yes?.(); } });
  dialog.show();
}
defineExpose({ create, confirm, setUsers: value => { users.value = value; }, dispose: () => { disposed = true; opened.value = []; inputNodes.clear(); wrapperNodes.clear(); } });
</script>
<template>
  <div v-for="dialog in opened" :key="dialog.id" class="task-dialog-overlay" @click.self="hide(dialog,true)" @keydown.esc.stop.prevent="hide(dialog,true)">
    <form class="task-field-dialog" role="dialog" aria-modal="true" :aria-labelledby="'task-dialog-title-'+dialog.id" @submit.prevent="submit(dialog)">
      <header><h2 :id="'task-dialog-title-'+dialog.id">{{ dialog.options.title }}</h2><button type="button" aria-label="Close dialog" @click="hide(dialog,true)">×</button></header>
      <div class="task-dialog-fields">
        <div v-for="field in dialog.fields" :key="field.fieldname" :ref="node=>node?wrapperNodes.set(key(dialog,field),node):wrapperNodes.delete(key(dialog,field))">
          <div v-if="field.fieldtype==='HTML'" v-html="sanitizeRichText(field.options || '')"></div>
          <label v-else :for="key(dialog,field)">{{ field.label }}<span v-if="field.reqd"> *</span></label>
          <textarea v-if="['Small Text','Text','Long Text'].includes(field.fieldtype)" :id="key(dialog,field)" :ref="node=>node?inputNodes.set(key(dialog,field),node):inputNodes.delete(key(dialog,field))" v-model="dialog.values[field.fieldname]" :required="!!field.reqd" rows="4"></textarea>
          <input v-else-if="field.fieldtype!=='HTML'" :id="key(dialog,field)" :ref="node=>node?inputNodes.set(key(dialog,field),node):inputNodes.delete(key(dialog,field))" v-model="dialog.values[field.fieldname]" :type="field.fieldtype==='Int'?'number':'text'" :step="field.fieldtype==='Int'?1:undefined" :required="!!field.reqd" :list="field.options==='User'?'task-dialog-users-'+dialog.id:undefined" @change="field.onchange?.()">
        </div>
        <datalist :id="'task-dialog-users-'+dialog.id"><option v-for="user in users" :key="user.name" :value="user.name">{{ user.full_name }}</option></datalist>
        <p v-if="dialog.error" role="alert">{{ dialog.error }}</p>
      </div>
      <footer><button type="button" @click="hide(dialog,true)">{{ dialog.options.secondary_action_label || 'Cancel' }}</button><button type="submit">{{ dialog.options.primary_action_label || 'Submit' }}</button></footer>
    </form>
  </div>
</template>
<style scoped>
.task-dialog-overlay{position:fixed;inset:0;z-index:2000;background:#0006;display:flex;align-items:flex-start;justify-content:center;overflow:auto;padding:50px 16px;color:#152418;font:14px Arial,sans-serif}.task-field-dialog{width:560px;max-width:100%;background:#fff;border:1px solid #d1d8dd;border-radius:8px;box-shadow:0 12px 40px #0003}.task-field-dialog header,.task-field-dialog footer{padding:16px 20px;display:flex;align-items:center;justify-content:space-between;gap:12px}.task-field-dialog header{border-bottom:1px solid #e2e8e3}.task-field-dialog h2{font-size:18px;margin:0}.task-dialog-fields{padding:20px;display:grid;gap:16px}.task-dialog-fields label{display:block;margin-bottom:7px;font-size:13px}.task-dialog-fields label span,.task-dialog-fields [role=alert]{color:#b42318}.task-dialog-fields input,.task-dialog-fields textarea{box-sizing:border-box;width:100%;padding:9px 10px;border:1px solid #cbd5ce;border-radius:6px;font:inherit}.task-field-dialog button{padding:8px 14px;border:1px solid #cbd5ce;border-radius:6px;background:#fff;cursor:pointer}.task-field-dialog footer{border-top:1px solid #e2e8e3;justify-content:flex-end}.task-field-dialog button[type=submit]{background:#1b5e20;color:#fff;border-color:#1b5e20}
</style>
