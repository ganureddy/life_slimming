<script setup>
import { onMounted, onBeforeUnmount, reactive, ref } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { session } from '../lib/session';
import { createDomPageRuntime } from '../lib/dom-page-runtime';
import { mountClusterDashboard } from '../controllers/cluster-dashboard';
const root = ref(null), status = reactive({ reads:0, writes:0, error:'', notice:'' });
let runtime;
onMounted(() => { runtime=createDomPageRuntime({root:root.value,session,status}); mountClusterDashboard(runtime); });
onBeforeRouteLeave(() => !status.writes);
onBeforeUnmount(() => runtime?.dispose());
</script>
<template>
<section class="cluster-dashboard-page" :aria-busy="status.reads > 0 || status.writes > 0">
<p v-if="status.error" role="alert" class="native-source-error">{{status.error}}</p>
<div ref="root" class="native-page-body"><div v-pre>
<div id="clusterApp"><header class="cl-header"><div class="cl-brand"><a aria-label="LIFE home" href="/life-home">L</a><div><small>LIFE · CLUSTER OPERATIONS</small><h1>Cluster Command Center</h1><span class="cl-grand" id="cl-grand">All clusters · cycle net —</span></div></div><div class="cl-controls"><label>CLUSTER<select aria-label="Cluster" disabled="" id="cl-select"><option>Checking access…</option></select></label><span class="cl-profile" id="cl-profile"></span><button id="cl-refresh">↻ Refresh</button></div></header><nav aria-label="Cluster dashboard views" class="cl-tabs"><button data-jump="cl-overview">Overview</button><button data-jump="cl-conversions">Conversions</button><button data-jump="cl-comparison">Branch comparison</button><button data-jump="bcc-race">Sales Race</button><button data-jump="cl-att-panel">Absent Staff</button><button data-jump="cl-dues-panel">Dues &amp; Recovery</button><button data-jump="cl-ap-panel">HO-CC Appointments</button><button data-jump="cl-exec-panel">Appointments &amp; Executions</button><button data-jump="cl-stock-panel">Approvals</button><button data-jump="cl-media-panel">Media / Source Mix</button><span id="cl-period"></span></nav><div class="cl-score"><div>Today <b id="cl-today">—</b></div><div>Invoices <b id="cl-bills">—</b></div><div>Cycle net <b id="cl-month">—</b></div><div>Staff <b id="cl-att">—</b></div><div class="cl-score-ticker"><span id="cl-ticker">Loading cluster performance…</span></div></div><main><div id="cl-status" role="status">Checking your available branches…</div><section id="cl-overview"><div class="cl-intro"><div><small>YOUR CLUSTER AT A GLANCE</small><h2 id="cl-heading">Branch performance</h2><p id="cl-subtitle">Collections after GST · completed paid bills · today’s attendance</p></div><div class="cl-legend"><i></i> Live records <span>·</span> Auto-refresh 5 min</div></div><div class="cl-cards" id="cl-cards"></div><section class="cl-panel" id="cl-conversions"><div class="cl-panel-title"><div><h2>Branch walk-in conversions</h2><p>Current sales cycle · booked ÷ visited clients</p></div></div><div class="cl-conversions" id="cl-conversion-cards"></div></section><section aria-labelledby="bcc-title-race" class="bcc-panel bcc-gold" data-bcc-panel="race" id="bcc-race" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-race">Sales Race Board</h2><p id="lsrbSub">Live cluster &amp; branch ranking · cluster rank: target achieved % · branch rank: net collections · part-payments included</p></div>
    <div class="bcc-race-actions">
      <div class="lsrb-ctl" id="lsrbCtl"><span class="lc-live" id="lsrbLive"><i></i>LIVE</span>
        <div class="lc-seg" id="lsrbSeg"><button data-p="today" type="button">Today</button><button class="on" data-p="mtd" type="button">This Month</button></div>
        <button class="lc-btn" id="lsrbRefresh" title="Refresh now" type="button">↻</button></div>
      <div class="bcc-panel-actions" data-bcc-controls=""></div>
    </div></header>
  <div class="bcc-panel-body" id="bcc-body-race">
<section aria-label="Sales Race Board" class="lsrb" id="lsrb">



  <div class="lsrb-body">
    <div class="lsrb-card race-card">
      <div class="lsrb-card-h">🏎️ Cluster Race <span>who leads the network</span></div>
      <div class="lanes" id="lsrbLanes"></div>
      <div class="champs"><div class="ch-h">Race Leaders</div>
        <div class="ch-grid"><div class="champ" id="lsrbChC"></div><div class="champ" id="lsrbChB"></div></div></div>
    </div>
    <div class="lsrb-card">
      <div class="lsrb-card-h">🏆 Branch Leaderboard <span>(top sales employee) · live positions</span></div>
      <div class="board-hd"><span>#</span><span>Br</span><span>Branch (Top Employee)</span><span>Collected net</span><span>Bills</span><span>New</span><span>In-H</span><span>Move</span></div>
      <div class="board" id="lsrbBoard"></div>
    </div>
  </div>

  <div class="lsrb-status" id="lsrbStatus">Loading live bills…</div>

  <svg aria-hidden="true" height="0" style="position:absolute" width="0"><defs><linearGradient id="lsrbGold" x1="0" x2="1" y1="0" y2="1">
    <stop offset="0" stop-color="#FFF1B8"></stop><stop offset=".45" stop-color="#F5B400"></stop><stop offset=".7" stop-color="#FFE38A"></stop><stop offset="1" stop-color="#B37A00"></stop></linearGradient></defs></svg>


</section>
  </div>
</section>
<section class="cl-panel" id="cl-comparison"><div class="cl-panel-title"><div><h2>Branch comparison</h2><p>Live comparison across assigned cluster branches</p></div><div class="cl-compare-controls"><select aria-label="Branch comparison period" id="cl-compare-mode"><option value="today">Today</option><option value="yesterday">Yesterday</option><option value="range">Date range</option></select><input aria-label="Comparison start" id="cl-compare-from" type="date"/><input aria-label="Comparison end" id="cl-compare-to" type="date"/><button id="cl-compare-apply">Apply</button></div></div><div class="cl-table-wrap"><table><thead><tr><th>Branch</th><th>Cluster</th><th>Package net</th><th>Collected net</th><th>Pending dues</th><th># Inv</th><th>Fresh net | Recovery net</th><th>Target</th><th>Cycle net</th><th>Last month net</th><th>Rank</th></tr></thead><tbody id="cl-branches"><tr><td colspan="9">Loading…</td></tr></tbody></table></div></section><section class="cl-panel" id="cl-att-panel"><div class="cl-panel-title"><div><h2>Branch-wise Absent Staff</h2><p>Today’s absent names · calendar-month present / absent counts</p></div></div><div id="cl-absence"></div></section><section class="cl-panel" id="cl-dues-panel"><div class="cl-panel-title"><div><h2>Pending Dues &amp; Recovery</h2><p>Cluster totals · branch and employee recovery status</p></div></div><div class="cl-filters" id="cl-dues-tabs"><button class="on" data-dues="today">Today</button><button data-dues="month">This Month</button><button data-dues="all">Overall</button><div class="cl-due-range"><label>Start <input aria-label="Pending dues start date" id="cl-dues-from" type="date"/></label><label>End <input aria-label="Pending dues end date" id="cl-dues-to" type="date"/></label><span>Invoice dates</span></div></div><div id="cl-billing-dues"></div><details><summary>Recovery commitments &amp; employee follow-ups</summary><div id="cl-recovery"></div></details></section><section class="cl-panel" id="cl-ap-panel"><div class="cl-panel-title"><div><h2>Walk In Appointments By HO-CC</h2><p>Cluster appointments · client details · lead journey · current 6th–5th cycle</p></div></div><div class="cl-filters cl-ap-toolbar"><input aria-label="Search appointments" id="cl-ap-search" placeholder="Search client, owner or status"/><select aria-label="Appointment branch" id="cl-ap-branch"><option value="">All branches</option></select><select aria-label="Consultant" id="cl-ap-consultant"><option value="">All consultants</option></select><select aria-label="Visit or journey" id="cl-ap-journey"><option value="">All visits / journeys</option><option value="first">First visit</option><option value="repeat">Repeat visit</option><option value="visited">Visited</option><option value="pending">Not yet visited</option></select></div><div id="cl-ap-content"></div></section><section class="cl-panel" id="cl-exec-panel"><div class="cl-panel-title"><div><h2>Appointments &amp; Executions</h2><p>Today · service appointments, visits and session entries</p></div><a href="/operations-&amp;-service-module" target="_blank">Open Operations ↗</a></div><div class="cl-filters cl-ex-toolbar"><select aria-label="Execution branch" id="cl-ex-branch"><option value="">All branches</option></select><select aria-label="Execution employee" id="cl-ex-employee"><option value="">All employees</option></select><select aria-label="Execution service" id="cl-ex-service"><option value="">All services</option><option>Slimming</option><option>Skin</option><option>Hair</option><option>Life Rise</option><option>Unmapped service</option></select><span id="cl-ex-periods"></span></div><div id="cl-execution">Loading…</div></section><section class="cl-panel" id="cl-media-panel"><div class="cl-panel-title"><div><h2>Media / Source Mix</h2><p>Selected cluster · current sales cycle to today · collections</p></div></div><div id="cl-media"></div></section><section class="cl-panel" id="cl-stock-panel"><div class="cl-panel-title"><div><h2>Approvals</h2><p>Branch-wise pending approvals &amp; stock request progress</p></div></div><div id="cl-approvals"></div></section><p class="cl-footnote">Business uses submitted non-return invoice final payable, including partly paid bills, converted to net sales. Collections use the Billing collections report. Sales and collections are ex-GST (inclusive amount ÷ 1.05). Dues remain actual payable balances. Collectable balances follow invoice due dates; undated balances remain in Overall. Race ranks Billing report collections in the selected period. Employee attribution uses submitted Payment Entry allocations, split 50/50 where shared; Hi Ticket uses collected money on one invoice, with joint owners shown together. Attendance P uses punch records or recorded attendance; A is provisional until the day closes. Leave and weekly off are excluded. Unavailable sources show —.</p></section></main></div>
</div></div></section>
</template>
<style scoped src="../styles/cluster-dashboard.css"></style>
