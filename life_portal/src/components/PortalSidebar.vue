<script setup>
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { visibleMenu, roleLabel, session, canAccessTab } from "../lib/session";
import {reportTabs} from '../lib/cc-report-navigation';
import { ccPermissions } from "../lib/cc-permissions";
import { ccTabs, ccRoute, ccViewOfRoute, isCcRoute } from "../lib/cc-navigation";
const canMoveLeads = ref(false);
let permissionGeneration = 0;
watch(() => visibleMenu.value.some(group => group.items.some(item => item.id === 'leads')) ? session.user : '', async user => {
  const token = ++permissionGeneration;canMoveLeads.value = false;
  if (!user) return;
  try { const result = await ccPermissions();if (token === permissionGeneration) canMoveLeads.value = !!result.can_move; } catch {}
}, { immediate: true });
const canManageLeads = computed(() => ["System Manager", "Call Center Export", "Sales Manager"].some(role => session.roles.includes(role)));
function itemTarget(item) { return item.to || { name: item.id==='control'?'control-access':item.id }; }
function isSelected(item) {
  if (item.ccView) return isCcRoute(route) && ccViewOfRoute(route) === item.ccView;
  if(item.id==='agent-360')return Boolean(route.meta.standaloneAgent360);
  if(item.id==='control'&&route.meta.accessModule==='control')return true;
  return route.name === item.id || (item.id === 'ccvisit' && route.meta.accessModule === 'ccvisit' && !route.meta.standaloneAgent360);
}
const props = defineProps({ collapsed: Boolean });
defineEmits(["toggle", "close"]);
const route = useRoute();
const search = ref("");
const closed = ref(new Set());
const ccMenuItems = computed(() => {
  const range = isCcRoute(route)
    ? Object.fromEntries(['from', 'to', 'mode'].filter(key => route.query[key]).map(key => [key, route.query[key]]))
    : {};
  const tabs = ccTabs
    .filter(tab => canAccessTab('leads',tab.view) && (!tab.manager || canManageLeads.value) && (!tab.mover || canMoveLeads.value))
    .map(tab => ({
      id: 'cc-tab-' + tab.view, ccView: tab.view,
      label: tab.label, icon: tab.icon, description: '',
      to: ccRoute(tab.view, range),
    }));
  return [...tabs,
    { id: 'cc-invoices', label: 'Invoices / Bills', description: 'View invoices and bills', icon: '▤' },
    { id: 'cc-roster', label: 'CC ROASTER', description: 'CC employee weekly and monthly roster', icon: '▦' },
    { id: 'cc-appointments', label: 'CC Appointments', description: 'Branch and staff calendar', icon: '▦' },
  ].filter(item=>!['cc-invoices','cc-roster','cc-appointments','cc-live-tv'].includes(item.id)||canAccessTab('leads',({'cc-invoices':'invoices','cc-roster':'roster','cc-appointments':'appointments','cc-live-tv':'live-tv'})[item.id]));
});
const groups = computed(() =>
  visibleMenu.value
    .map(group => ({
      ...group,
      items: group.items.flatMap(item => item.id === 'leads' ? ccMenuItems.value : item.id === 'ccvisit' ? [{...item,label:'Branch Visit Report'}, {id:'agent-360',label:'Agent 360',description:'ConVox, mobile calls and ERP activity',icon:'🔗'}] : [item])
        .filter(item=>item.id!=='agent-360'||canAccessTab('ccvisit','standalone'))
        .filter(item=>item.id!=='ccvisit'||reportTabs.some(tab=>canAccessTab('ccvisit',tab.key)))
        .filter(item => (group.label + ' ' + item.label + ' ' + item.description)
          .toLowerCase().includes(search.value.toLowerCase())),
    }))
    .filter(group => group.items.length),
);
function toggle(label) {
  const next = new Set(closed.value);
  next.has(label) ? next.delete(label) : next.add(label);
  closed.value = next;
}
</script>

<template>
  <aside
    class="sidebar"
    aria-label="Workspace menu"
  >
    <div class="sidebar-card">
      <div class="sidebar-heading">
        <span>WORKSPACE</span><span class="sidebar-edition">LIFE</span>
      </div>
      <div class="menu-search">
        <span aria-hidden="true">⌕</span
        ><input
          v-model="search"
          aria-label="Filter menu"
          placeholder="Find a module…"
        /><button
          class="mobile-toggle"
          aria-label="Close navigation"
          @click="$emit('close')"
        >
          ×
        </button>
      </div>
      <nav aria-label="Portal navigation">
        <section
          v-for="group in groups"
          :key="group.label"
          class="nav-group"
          :class="{
            active: group.items.some(isSelected),
          }"
        >
          <button
            class="group-heading"
            :aria-expanded="
              Boolean(props.collapsed || search || !closed.has(group.label))
            "
            @click="toggle(group.label)"
          >
            <span>{{ group.label }}</span
            ><span>{{ closed.has(group.label) ? "›" : "⌄" }}</span>
          </button>
          <div v-show="props.collapsed || search || !closed.has(group.label)">
            <RouterLink
              v-for="item in group.items"
              :key="item.id"
              :to="itemTarget(item)"
              class="nav-item"
              :title="item.label"
              :aria-label="item.label"
              active-class=""
              :class="{ selected: isSelected(item) }"
              :aria-current="isSelected(item) ? 'page' : undefined"
            >
              <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span
              ><span class="nav-label">{{ item.label }}</span>
            </RouterLink>
          </div>
        </section>
        <p v-if="!groups.length" class="muted empty-menu">
          No matching menu items.
        </p>
      </nav>
      <footer class="sidebar-footer">
        <span>{{ roleLabel }}</span
        ><small>LIFE ERP · Enterprise Portal</small>
      </footer>
    </div>
    <button
      class="collapse-button"
      :aria-label="collapsed ? 'Expand menu' : 'Collapse menu'"
      :aria-expanded="!collapsed"
      @click="$emit('toggle')"
    >
      <span class="collapse-icon" aria-hidden="true">{{ collapsed ? "›" : "‹" }}</span>
      <span class="collapse-hint" aria-hidden="true">{{ collapsed ? "Expand" : "Collapse" }}</span>
    </button>
  </aside>
</template>
