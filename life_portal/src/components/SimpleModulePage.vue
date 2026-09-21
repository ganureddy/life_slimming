<script setup>
import { computed, ref } from "vue";
import demoRecords from "../data/demoRecords.json";

const props = defineProps({ title: String, description: String });
const query = ref("");
const branch = ref("All Branches");
const toast = ref("");

const page = computed(() => demoRecords[props.title] || {
  doctype: props.title,
  columns: ["Reference", "Status"],
  rows: [],
});
const branches = computed(() => {
  const index = page.value.columns.findIndex((x) => x.toLowerCase() === "branch");
  if (index < 0) return [];
  return [...new Set(page.value.rows.map((row) => row[index]).filter((x) => x && x !== "-"))].sort();
});
const rows = computed(() => {
  const branchIndex = page.value.columns.findIndex((x) => x.toLowerCase() === "branch");
  const needle = query.value.trim().toLowerCase();
  return page.value.rows.filter((row) => {
    const branchMatch = branch.value === "All Branches" || branchIndex < 0 || row[branchIndex] === branch.value;
    return branchMatch && (!needle || row.join(" ").toLowerCase().includes(needle));
  });
});
const statusIndex = computed(() => page.value.columns.findIndex((x) => /status|workflow/i.test(x)));
const pending = computed(() => statusIndex.value < 0 ? 0 : page.value.rows.filter((r) => /pending|unpaid|overdue|open|draft/i.test(String(r[statusIndex.value]))).length);
const completed = computed(() => Math.max(page.value.rows.length - pending.value, 0));
const updated = computed(() => new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date()));

function notify(message) {
  toast.value = message;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => (toast.value = ""), 2200);
}
function reset() { query.value = ""; branch.value = "All Branches"; }
</script>

<template>
  <section class="life-module">
    <header class="life-module-hero">
      <div>
        <p class="life-eyebrow">LIFE · ENTERPRISE PORTAL</p>
        <h1>{{ title }}</h1>
        <p>{{ description }}</p>
      </div>
      <div class="life-hero-actions">
        <span class="life-live"><i></i> LIVE ERP SNAPSHOT</span>
        <button class="life-gold" @click="notify('Live snapshot refreshed')">↻ Refresh</button>
      </div>
    </header>

    <nav class="life-module-tabs" aria-label="Page sections">
      <button class="active">Overview</button>
      <button>Records</button>
      <button>Reports</button>
    </nav>

    <section class="life-toolbar">
      <label class="life-search"><span>Search</span><input v-model="query" type="search" placeholder="Search live records…"></label>
      <label v-if="branches.length"><span>Branch</span><select v-model="branch"><option>All Branches</option><option v-for="item in branches" :key="item">{{ item }}</option></select></label>
      <button class="life-apply" @click="notify('Filters applied')">Apply</button>
      <button @click="reset">Reset</button>
    </section>

    <section class="life-kpis">
      <article><span>Total records</span><strong>{{ page.rows.length }}</strong><small>Exported from live ERP</small></article>
      <article><span>Visible records</span><strong>{{ rows.length }}</strong><small>Current filter result</small></article>
      <article><span>Pending</span><strong>{{ pending }}</strong><small>Needs attention</small></article>
      <article><span>Processed</span><strong>{{ completed }}</strong><small>Other statuses</small></article>
    </section>

    <section class="life-data-card">
      <div class="life-card-head">
        <div><p class="life-eyebrow">{{ page.doctype }}</p><h2>Live Demo Data</h2><p>{{ rows.length }} records · snapshot from live ERP</p></div>
        <div><button @click="notify('CSV export will be connected to the native API')">↓ CSV</button><button @click="print()">⎙ Print</button></div>
      </div>
      <div class="life-table-wrap">
        <table>
          <thead><tr><th v-for="column in page.columns" :key="column">{{ column }}</th></tr></thead>
          <tbody>
            <tr v-for="(row, ri) in rows" :key="ri"><td v-for="(cell, ci) in row" :key="ci"><span v-if="ci === statusIndex" class="life-status">{{ cell }}</span><template v-else>{{ cell }}</template></td></tr>
            <tr v-if="!rows.length"><td :colspan="page.columns.length" class="life-empty">No matching live records</td></tr>
          </tbody>
        </table>
      </div>
      <footer class="life-card-foot"><span>Last refreshed: {{ updated }}</span><span>Read-only demo snapshot</span></footer>
    </section>
    <div v-if="toast" class="life-toast">✓ {{ toast }}</div>
  </section>
</template>
