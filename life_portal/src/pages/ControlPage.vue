<script setup>
import { computed, ref, watch } from "vue";
import menu from "../data/menu.json";
import { session, roleKey, labels, groupRoles } from "../lib/session";
import { call } from "../lib/api";
const allowed = computed(() => ["IT", "MD"].includes(roleKey.value));
const selectedRole = ref("IT");
const selectedGroups = ref([]);
const selectedItems = ref([]);
const saving = ref(false);
const error = ref("");
const notice = ref("");
const total = menu.flatMap(group => group.items).length;
function roleConfig(role) {
  return session.access_config?.[role] || {
    groups: ["IT", "MD"].includes(role) ? "ALL" : groupRoles[role] || [],
    show: [], hide: [],
  };
}
function loadRole() {
  const cfg = roleConfig(selectedRole.value);
  selectedGroups.value = menu.filter(g => cfg.groups === "ALL" || cfg.groups?.includes(g.label)).map(g => g.label);
  selectedItems.value = menu.flatMap(g => g.items.filter(item =>
    cfg.show?.includes(item.id) || (!cfg.hide?.includes(item.id) && selectedGroups.value.includes(g.label))
  ).map(item => item.id));
  error.value = "";
  notice.value = "";
}
watch(selectedRole, loadRole, { immediate: true });
function toggleGroup(group, checked) {
  selectedGroups.value = selectedGroups.value.filter(name => name !== group.label);
  const ids = group.items.map(item => item.id);
  selectedItems.value = selectedItems.value.filter(id => !ids.includes(id));
  if (checked) {
    selectedGroups.value.push(group.label);
    selectedItems.value.push(...ids);
  }
}
function selectAll(checked) {
  selectedGroups.value = checked ? menu.map(g => g.label) : [];
  selectedItems.value = checked ? menu.flatMap(g => g.items.map(i => i.id)) : [];
}
async function save() {
  if (saving.value || !allowed.value) return;
  saving.value = true; error.value = ""; notice.value = "";
  const role = selectedRole.value;
  const config = Object.fromEntries(Object.keys(labels).map(key => [key, roleConfig(key)]));
  Object.assign(config, session.access_config || {});
  config[role] = {
    groups: selectedGroups.value.length === menu.length ? "ALL" : [...selectedGroups.value],
    show: menu.flatMap(g => g.items.filter(i => !selectedGroups.value.includes(g.label) && selectedItems.value.includes(i.id)).map(i => i.id)),
    hide: menu.flatMap(g => g.items.filter(i => selectedGroups.value.includes(g.label) && !selectedItems.value.includes(i.id)).map(i => i.id)),
  };
  try {
    await call("frappe.client.set_value", {
      doctype: "Portal Access Settings", name: "Portal Access Settings",
      fieldname: { access_config: JSON.stringify(config), last_updated_by_portal: session.user },
    }, { csrfToken: session.csrf_token });
    session.access_config = config;
    notice.value = `Saved access for ${labels[role]}. Users see changes on next login.`;
  } catch (err) { error.value = err.message; }
  finally { saving.value = false; }
}
</script>

<template>
  <section v-if="!allowed" class="panel">
    <h1>Restricted area</h1>
    <p>Portal Access Control can only be opened by an IT Admin or MD.</p>
  </section>
  <section v-else class="access-panel">
    <header class="access-hero">
      <span aria-hidden="true">🔐</span>
      <div><h1>Portal Access Control</h1><p>Choose a role, then tick the groups and individual tabs it can see.</p></div>
    </header>
    <fieldset :disabled="saving">
      <div class="access-toolbar panel">
        <label for="access-role">Role
          <select id="access-role" v-model="selectedRole"><option v-for="(label, key) in labels" :key="key" :value="key">{{ label }}</option></select>
        </label>
        <div class="actions">
          <button type="button" @click="selectAll(true)">✓ Grant all</button>
          <button type="button" @click="selectAll(false)">Revoke all</button>
          <button type="button" class="primary" @click="save">{{ saving ? 'Saving…' : 'Save changes' }}</button>
        </div>
      </div>
      <p class="muted"><b>{{ labels[selectedRole] }}</b> currently sees <b>{{ selectedItems.length }}</b> of {{ total }} tabs.</p>
      <p v-if="error" role="alert" class="access-error">{{ error }}</p>
      <p v-if="notice" role="status" class="access-notice">{{ notice }}</p>
      <div class="access-matrix">
        <section v-for="group in menu" :key="group.label" class="access-group">
          <header>
            <label><input type="checkbox" :checked="selectedGroups.includes(group.label)" @change="toggleGroup(group, $event.target.checked)"> {{ group.label }}</label>
            <span>{{ group.items.filter(i => selectedItems.includes(i.id)).length }}/{{ group.items.length }}</span>
          </header>
          <label v-for="item in group.items" :key="item.id" class="access-item" :class="{ enabled: selectedItems.includes(item.id) }">
            <input v-model="selectedItems" type="checkbox" :value="item.id">
            <span aria-hidden="true">{{ item.icon }}</span><span>{{ item.label }}</span>
          </label>
        </section>
      </div>
    </fieldset>
  </section>
</template>

<style scoped>
.access-panel{max-width:1180px}.access-hero{display:flex;align-items:center;gap:18px;padding:24px;background:#164c3f;border-radius:16px;color:white;margin-bottom:20px}.access-hero>span{font-size:30px}.access-hero h1{font-size:24px}.access-hero p{margin:0;color:#d5e6da;font-size:13px}fieldset{border:0;padding:0;margin:0;min-width:0}.access-toolbar{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:18px}.access-toolbar label{display:grid;gap:6px;font-size:12px;font-weight:600}select{min-width:190px;padding:10px;border:1px solid var(--line);border-radius:8px;background:white;color:inherit}.access-matrix{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;align-items:start}.access-group{border:1px solid var(--line);border-radius:12px;background:white;overflow:hidden}.access-group header{display:flex;justify-content:space-between;gap:8px;padding:14px;background:#eaf3e8;font-size:11px;font-weight:600}.access-group header label{display:flex;align-items:center;gap:8px}.access-group header>span{white-space:nowrap}.access-item{display:flex;align-items:center;gap:10px;padding:12px 14px;border-top:1px solid #edf2eb;font-size:12px;color:#6b8070}.access-item.enabled{color:#183d26;background:#f8fbf6}input{accent-color:#236d38;width:16px;height:16px;flex-shrink:0}.access-error{color:#9a4233}.access-notice{color:#236d38}@media(max-width:1000px){.access-matrix{grid-template-columns:repeat(2,minmax(0,1fr))}.access-toolbar{align-items:flex-start;flex-direction:column}}@media(max-width:600px){.access-matrix{grid-template-columns:1fr}.access-hero{padding:18px}.access-hero h1{font-size:20px}.actions{flex-wrap:wrap}}
</style>
