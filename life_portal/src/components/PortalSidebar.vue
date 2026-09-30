<script setup>
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { visibleMenu, roleLabel } from "../lib/session";
const props = defineProps({ collapsed: Boolean });
defineEmits(["toggle", "close"]);
const route = useRoute();
const search = ref("");
const closed = ref(new Set());
const groups = computed(() =>
  visibleMenu.value
    .map((group) => ({
      ...group,
      items: group.items.flatMap(item => item.id === 'leads'
        ? [item, { id: 'cc-appointments', label: 'Create Appointment', description: 'Branch and staff calendar', icon: '▦' }, { id: 'convox-history-index', label: 'ConVox History', description: 'Call details and recordings', icon: '☎' }]
        : [item]).filter((item) =>
        (group.label + " " + item.label + " " + item.description)
          .toLowerCase()
          .includes(search.value.toLowerCase()),
      ),
    }))
    .filter((group) => group.items.length),
);
function toggle(label) {
  const next = new Set(closed.value);
  next.has(label) ? next.delete(label) : next.add(label);
  closed.value = next;
}
</script>

<template>
  <aside class="sidebar" aria-label="Workspace menu">
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
            active: group.items.some((item) => item.id === route.name),
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
              :to="{ name: item.id }"
              class="nav-item"
              :title="item.label"
              :aria-label="item.label"
              active-class="selected"
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
      {{ collapsed ? "›" : "‹" }}
    </button>
  </aside>
</template>
