<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { request } from '../api/http';
import endpoints from '../api/endpoints.json';
import { session } from '../lib/session';
import { indiaDate } from '../lib/unjoined';
const today = indiaDate();
const from = ref(today.slice(0, 8) + '01'), to = ref(today), cluster = ref(''), data = ref(null), loading = ref(false), error = ref('');
let controller, alive = true;
const money = value => '₹' + Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
async function load() {
  if (!from.value) from.value = today.slice(0, 8) + '01';
  if (!to.value) to.value = today;
  if (from.value > to.value) { error.value = 'Choose a valid date range.'; return; }
  controller?.abort(); const current = new AbortController(); controller = current;
  loading.value = true; error.value = '';
  try {
    const result = await request(endpoints.cluster_dashboard_api, { args: { from_date: from.value, to_date: to.value, ...(cluster.value ? { cluster: cluster.value } : {}) }, csrfToken: session.csrf_token, signal: current.signal });
    if (!alive || controller !== current) return;
    if (!result.message || !Array.isArray(result.message.rows)) throw new Error('The dashboard returned an invalid response.');
    data.value = result.message;
  } catch (failure) { if (alive && controller === current && failure.name !== 'AbortError') error.value = 'Failed to load data.'; }
  finally { if (alive && controller === current) loading.value = false; }
}
onMounted(load);
onBeforeUnmount(() => { alive = false; controller?.abort(); });
</script>

<template>
  <div class="cd">
    <div class="cd-top">
      <div><div id="cdTitle" class="cd-title">{{ data?.cluster || 'Cluster Dashboard' }}</div><div id="cdSub" class="cd-sub" role="status">{{ loading ? 'Loading…' : error || (data ? (data.from_date || '') + ' → ' + (data.to_date || '') + ' · ' + (data.branches?.length || 0) + ' branches' : 'Loading…') }}</div></div>
      <form class="cd-controls" @submit.prevent="load">
        <select v-if="data?.available_clusters?.length > 1" id="cdClusterSel" v-model="cluster" class="cd-select" aria-label="Cluster"><option value="">My Cluster</option><option value="ALL">All Branches</option><option v-for="name in data.available_clusters" :key="name">{{ name }}</option></select>
        <input id="cdFrom" v-model="from" class="cd-date" type="date" aria-label="From date"><input id="cdTo" v-model="to" class="cd-date" type="date" aria-label="To date"><button class="cd-btn" :disabled="loading">Apply</button>
      </form>
    </div>
    <div v-if="data" id="cdCards" class="cd-cards"><div class="cd-card"><div class="k">Sales</div><div class="v">{{ money(data.totals?.sales_amt) }}</div></div><div class="cd-card"><div class="k">Invoices</div><div class="v">{{ data.totals?.sales_count || 0 }}</div></div><div class="cd-card"><div class="k">Collections</div><div class="v">{{ money(data.totals?.collections) }}</div></div><div class="cd-card"><div class="k">Outstanding</div><div class="v">{{ money(data.totals?.outstanding) }}</div></div></div>
    <div class="cd-table-wrap"><table id="cdTable" class="cd-table"><thead><tr><th>Branch</th><th>Sales</th><th>Invoices</th><th>Collections</th><th>Outstanding</th></tr></thead><tbody id="cdTbody"><tr v-for="row in data?.rows || []" :key="row.branch"><td>{{ row.branch }}</td><td>{{ money(row.sales_amt) }}</td><td>{{ row.sales_count }}</td><td>{{ money(row.collections) }}</td><td>{{ money(row.outstanding) }}</td></tr><tr v-if="!data?.rows.length"><td colspan="5" class="cd-empty">{{ loading ? 'Loading…' : error || 'No branches configured for this cluster yet.' }}</td></tr></tbody></table></div>
  </div>
</template>

<style scoped>
.cd{
  font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
  color: #14311d;
}
.navbar{display:none;}
.web-footer{display:none;}
.cd-top{
  display:flex;
  flex-wrap:wrap;
  gap:14px;
  align-items:center;
  justify-content:space-between;
  margin-bottom:18px;
}

.cd-title{
  font-size:20px;
  font-weight:700;
}

.cd-sub{
  font-size:13px;
  color:#5c7a68;
  margin-top:2px;
}

.cd-controls{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  align-items:center;
}

.cd-select,
.cd-date{
  border:1px solid #d3e3d8;
  border-radius:10px;
  padding:7px 10px;
  font-size:13px;
  background:#fff;
}

.cd-btn{
  background:linear-gradient(135deg,#1b5e20,#2e7d32);
  color:#fff;
  border:none;
  border-radius:10px;
  padding:8px 16px;
  font-size:13px;
  font-weight:600;
  cursor:pointer;
}

.cd-btn:hover{
  filter:brightness(1.08);
}

.cd-cards{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:12px;
  margin-bottom:20px;
}

.cd-card{
  background:linear-gradient(165deg,rgba(255,255,255,.95),rgba(236,248,238,.85));
  border:1px solid rgba(27,94,32,.12);
  border-radius:14px;
  padding:14px 16px;
  box-shadow:0 6px 18px rgba(15,61,30,.08);
}

.cd-card .k{
  font-size:12px;
  color:#5c7a68;
  margin-bottom:6px;
}

.cd-card .v{
  font-size:20px;
  font-weight:700;
  color:#14311d;
}

.cd-table-wrap{
  overflow-x:auto;
  border-radius:14px;
  border:1px solid rgba(27,94,32,.12);
  background:#fff;
}

.cd-table{
  width:100%;
  border-collapse:collapse;
  font-size:13px;
  min-width:520px;
}

.cd-table th{
  text-align:left;
  padding:11px 14px;
  background:#eef6f0;
  color:#1b5e20;
  font-weight:700;
  position:sticky;
  top:0;
}

.cd-table td{
  padding:10px 14px;
  border-top:1px solid #eef2ee;
}

.cd-table tr:hover td{
  background:#f7fbf8;
}

.cd-empty{
  text-align:center;
  color:#8aa596;
  padding:26px !important;
}

/* ================= RESPONSIVE ================= */

@media(max-width:900px){
  .cd-cards{
    grid-template-columns:repeat(2,1fr);
  }
}

@media(max-width:640px){
  .cd{
    padding:10px;
  }

  .cd-top{
    flex-direction:column;
    align-items:stretch;
  }

  .cd-controls{
    flex-direction:column;
    align-items:stretch;
  }

  .cd-controls > *{
    width:100%;
  }

  .cd-cards{
    grid-template-columns:1fr 1fr;
    gap:8px;
  }

  .cd-card{
    padding:11px 12px;
  }

  .cd-card .v{
    font-size:17px;
  }

  .cd-table{
    min-width:0;
    font-size:12px;
  }

  .cd-table th,
  .cd-table td{
    padding:8px 8px;
  }
}
</style>
