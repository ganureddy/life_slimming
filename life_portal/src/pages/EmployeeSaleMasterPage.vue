<script setup>
import { onMounted, onBeforeUnmount, reactive, ref } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { session } from '../lib/session';
import { createDomPageRuntime } from '../lib/dom-page-runtime';
import { mountEmployeeSaleMaster } from '../controllers/employee-sale-master';
const root = ref(null), status = reactive({ reads:0, writes:0, error:'', notice:'' });
let runtime;
onMounted(() => { runtime=createDomPageRuntime({root:root.value,session,status}); mountEmployeeSaleMaster(runtime); });
onBeforeRouteLeave(() => !status.writes);
onBeforeUnmount(() => runtime?.dispose());
</script>
<template>
<section class="employee-sale-master-page" :aria-busy="status.reads > 0 || status.writes > 0">
<p v-if="status.error" role="alert" class="native-source-error">{{status.error}}</p>
<div ref="root" class="native-page-body"><div v-pre>
<div class="esr" id="esr-root">

  <!-- ═════════ PAGE HEADER ═════════ -->
  <header class="esr-head">
    <div class="esr-head-main">
      <div class="esr-kicker">Sales &amp; Collection Analytics</div>
      <h1 class="esr-title">Sales Master Report</h1>
      <div class="esr-sub">Collections credited to referring &amp; incentive employees — by employee, branch, treatment category and payment mode</div>
    </div>
    <div class="esr-head-side">
      <div class="esr-meta">
        <span class="esr-meta-chip"><em>Source</em> REFERRAL REPORT – FIXED</span>
        <span class="esr-meta-chip"><em>Period</em> <b id="esr-meta-period">—</b></span>
        <span class="esr-meta-chip"><em>Loaded</em> <b id="esr-meta-loaded">—</b></span>
      </div>
      <div class="esr-head-actions">
        <button class="esr-btn esr-btn-ghost" id="esr-btn-export" type="button">⬇ Export Excel</button>
        <button class="esr-btn esr-btn-ghost" id="esr-btn-print" type="button">🖨 Print</button>
      </div>
    </div>
  </header>

  <!-- ═════════ FILTER PANEL ═════════ -->
  <section class="esr-filters" id="esr-filters">
    <div class="esr-fhead">
      <div class="esr-fhead-l">
        <button class="esr-collapse" id="esr-fcollapse" title="Show / hide filters" type="button">▾</button>
        <div>
          <div class="esr-ftitle">Report Filters</div>
          <div class="esr-fhint">Period loads data from the server. Every other filter applies instantly.</div>
        </div>
      </div>
      <div class="esr-fhead-r">
        <button class="esr-btn esr-btn-outline" id="esr-btn-reset" type="button">↺ Reset</button>
        <button class="esr-btn esr-btn-primary" id="esr-btn-load" type="button">▶ Load Data</button>
      </div>
    </div>

    <div class="esr-fbody" id="esr-fbody">
      <div class="esr-fgrid">

        <!-- 1. PERIOD -->
        <div class="esr-fgroup esr-g-period">
          <div class="esr-fg-hdr"><span class="esr-fg-ico">📅</span>Period <small>Payment date</small></div>
          <div class="esr-fg-body">
            <div class="esr-frow2">
              <label class="esr-field"><span class="esr-lbl">From</span><input class="esr-input" id="esr-f-from" type="date"/></label>
              <label class="esr-field"><span class="esr-lbl">To</span><input class="esr-input" id="esr-f-to" type="date"/></label>
            </div>
            <div class="esr-quick" id="esr-quick">
              <button class="esr-q" data-range="today" type="button">Today</button>
              <button class="esr-q" data-range="yesterday" type="button">Yesterday</button>
              <button class="esr-q on" data-range="cycle" type="button">This Cycle</button>
              <button class="esr-q" data-range="lastcycle" type="button">Last Cycle</button>
              <button class="esr-q" data-range="calmonth" type="button">Calendar Month</button>
              <button class="esr-q" data-range="fy" type="button">This FY</button>
            </div>
            <div class="esr-fnote">Cycle = 6th to 5th of next month</div>
          </div>
        </div>

        <!-- 2. PEOPLE & PLACE -->
        <div class="esr-fgroup">
          <div class="esr-fg-hdr"><span class="esr-fg-ico">👥</span>People &amp; Place</div>
          <div class="esr-fg-body">
            <label class="esr-field"><span class="esr-lbl">Branch</span>
              <select class="esr-input" id="esr-f-branch"><option value="">All Branches</option></select>
            </label>
            <div class="esr-field"><span class="esr-lbl">Employee</span><div class="esr-ms" data-all="All Employees" data-key="emp"></div></div>
            <div class="esr-frow2">
              <div class="esr-field"><span class="esr-lbl">Credit Role</span><div class="esr-ms" data-all="Both Roles" data-key="role"></div></div>
              <div class="esr-field"><span class="esr-lbl">Sharing Type</span><div class="esr-ms" data-all="All Types" data-key="sharing"></div></div>
            </div>
          </div>
        </div>

        <!-- 3. TREATMENT -->
        <div class="esr-fgroup esr-g-treat">
          <div class="esr-fg-hdr"><span class="esr-fg-ico">✦</span>Treatment</div>
          <div class="esr-fg-body">
            <div class="esr-field"><span class="esr-lbl">Main Category</span><div class="esr-ms" data-all="All Main Categories" data-key="category"></div></div>
            <div class="esr-field"><span class="esr-lbl">Therapy Group</span><div class="esr-ms" data-all="All Therapy Groups" data-key="group"></div></div>
            <div class="esr-field"><span class="esr-lbl">Therapy Type</span><div class="esr-ms" data-all="All Therapy Types" data-key="type"></div></div>
            <div class="esr-field">
              <span class="esr-lbl">Amount Basis <i class="esr-tip" title="Full Invoice: the whole collected amount of every invoice whose plan contains the selected treatment. Treatment Share: only the part of the collection that belongs to the selected treatment lines (split across the plan's therapy lines).">?</i></span>
              <div class="esr-seg" id="esr-basis">
                <button class="on" data-basis="full" type="button">Full Invoice</button>
                <button data-basis="share" type="button">Treatment Share</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 4. PAYMENT & AMOUNT -->
        <div class="esr-fgroup">
          <div class="esr-fg-hdr"><span class="esr-fg-ico">₹</span>Payment &amp; Amount</div>
          <div class="esr-fg-body">
            <div class="esr-frow2">
              <div class="esr-field"><span class="esr-lbl">Booking Type</span><div class="esr-ms" data-all="All Booking Types" data-key="booking"></div></div>
              <div class="esr-field"><span class="esr-lbl">Mode of Payment</span><div class="esr-ms" data-all="All Modes" data-key="mop"></div></div>
            </div>
            <div class="esr-frow2">
              <label class="esr-field"><span class="esr-lbl">Paid ex-GST from</span><input class="esr-input esr-amt" id="esr-f-paid-min" inputmode="decimal" placeholder="Min ₹" type="text"/></label>
              <label class="esr-field"><span class="esr-lbl">to</span><input class="esr-input esr-amt" id="esr-f-paid-max" inputmode="decimal" placeholder="Max ₹" type="text"/></label>
            </div>
            <div class="esr-frow2">
              <label class="esr-field"><span class="esr-lbl">Outstanding from</span><input class="esr-input esr-amt" id="esr-f-out-min" inputmode="decimal" placeholder="Min ₹" type="text"/></label>
              <label class="esr-field"><span class="esr-lbl">to</span><input class="esr-input esr-amt" id="esr-f-out-max" inputmode="decimal" placeholder="Max ₹" type="text"/></label>
            </div>
            <label class="esr-check"><input id="esr-f-onlyout" type="checkbox"/> Only invoices with outstanding</label>
          </div>
        </div>

      </div>
    </div>

    <div class="esr-chips" id="esr-chips"></div>
  </section>

  <div class="esr-status-wrap" id="esr-status"></div>

  <!-- ═════════ TABS ═════════ -->
  <nav class="esr-tabs" id="esr-tabs">
    <button class="esr-tab on" data-tab="overview" type="button">📊 Overview</button>
    <button class="esr-tab" data-tab="employee" type="button">👤 Employee Wise <b class="esr-tc" id="esr-tc-employee">0</b></button>
    <button class="esr-tab" data-tab="branch" type="button">🏢 Branch Wise <b class="esr-tc" id="esr-tc-branch">0</b></button>
    <button class="esr-tab" data-tab="treatment" type="button">✦ Treatment Category <b class="esr-tc" id="esr-tc-treatment">0</b></button>
    <button class="esr-tab" data-tab="txn" type="button">📋 Transaction Detail <b class="esr-tc" id="esr-tc-txn">0</b></button>
  </nav>

  <main class="esr-main">

    <!-- OVERVIEW -->
    <section class="esr-pane on" data-pane="overview">
      <div class="esr-basis-note" id="esr-basis-note"></div>
      <div class="esr-kpis" id="esr-kpis"></div>
      <div class="esr-grid2">
        <div class="esr-card"><div class="esr-card-hdr"><span>Top Employees</span><span class="esr-badge">Paid ex-GST</span></div><div class="esr-card-body" id="esr-ov-emp"></div></div>
        <div class="esr-card"><div class="esr-card-hdr"><span>Branches</span><span class="esr-badge">Paid ex-GST</span></div><div class="esr-card-body" id="esr-ov-branch"></div></div>
      </div>
      <div class="esr-grid2">
        <div class="esr-card"><div class="esr-card-hdr"><span>Main Category Mix</span><span class="esr-badge esr-badge-alt">Treatment share</span></div><div class="esr-card-body" id="esr-ov-cat"></div></div>
        <div class="esr-card"><div class="esr-card-hdr"><span>Mode of Payment Mix</span><span class="esr-badge">Invoices · Paid ex-GST</span></div><div class="esr-card-body" id="esr-ov-mop"></div></div>
      </div>
      <div class="esr-card">
        <div class="esr-card-hdr"><span>Booking Type Breakdown</span><span class="esr-hsub">Invoices &amp; amounts by booking type</span></div>
        <div class="esr-tblbox" data-tbl="booking"></div>
      </div>
    </section>

    <!-- EMPLOYEE -->
    <section class="esr-pane" data-pane="employee">
      <div class="esr-card">
        <div class="esr-card-hdr"><span>Employee Wise Summary</span><span class="esr-hsub">Click a row for invoice-level drill-down</span></div>
        <div class="esr-tblbox" data-tbl="employee"></div>
      </div>
    </section>

    <!-- BRANCH -->
    <section class="esr-pane" data-pane="branch">
      <div class="esr-kpis" id="esr-br-kpis"></div>
      <div class="esr-card">
        <div class="esr-card-hdr"><span>Branch Wise Summary</span><span class="esr-hsub">Click a row to see that branch's employees</span></div>
        <div class="esr-tblbox" data-tbl="branch"></div>
      </div>
      <div class="esr-card">
        <div class="esr-card-hdr"><span>Branch × Main Category</span><span class="esr-badge esr-badge-alt">Treatment share · ex-GST</span></div>
        <div class="esr-tblbox" data-tbl="matrix"></div>
      </div>
    </section>

    <!-- TREATMENT -->
    <section class="esr-pane" data-pane="treatment">
      <div class="esr-kpis" id="esr-tr-kpis"></div>
      <div class="esr-card">
        <div class="esr-card-hdr">
          <span>Main Category › Therapy Group › Therapy Type</span>
          <span class="esr-hdr-actions">
            <button class="esr-btn esr-btn-xs" id="esr-tr-expand" type="button">Expand all</button>
            <button class="esr-btn esr-btn-xs" id="esr-tr-collapse" type="button">Collapse all</button>
          </span>
        </div>
        <div class="esr-tree-note">Amounts are the collected ex-GST value split across the therapy lines of each plan. Invoice count = invoices whose plan contains that treatment.</div>
        <div class="esr-tblwrap"><table class="esr-table esr-tree"><thead><tr>
          <th>Treatment</th><th class="n">Invoices</th><th class="n">Clients</th><th class="n">Employees</th><th class="n">Treatment Share ex-GST</th><th class="n">Share %</th><th class="n">Full-Invoice ex-GST</th>
        </tr></thead><tbody id="esr-tree-body"></tbody></table></div>
      </div>
      <div class="esr-card esr-card-warn" id="esr-unmapped-card">
        <div class="esr-card-hdr"><span>Unmapped Therapy Types</span><span class="esr-hsub">No Main Category / Therapy Group in the Therapy Type master — fix these to complete category reporting</span></div>
        <div class="esr-tblbox" data-tbl="unmapped"></div>
      </div>
    </section>

    <!-- TRANSACTIONS -->
    <section class="esr-pane" data-pane="txn">
      <div class="esr-card">
        <div class="esr-card-hdr"><span>Transaction Detail</span><span class="esr-hsub">One row per invoice · click invoice no. to open in ERP</span></div>
        <div class="esr-tblbox" data-tbl="txn"></div>
      </div>
    </section>

  </main>

  <!-- ═════════ MODAL ═════════ -->
  <div aria-hidden="true" class="esr-modal" id="esr-modal">
    <div class="esr-modal-box">
      <div class="esr-modal-hdr">
        <div><div class="esr-modal-title" id="esr-modal-title"></div><div class="esr-modal-sub" id="esr-modal-sub"></div></div>
        <button class="esr-modal-x" id="esr-modal-x" type="button">×</button>
      </div>
      <div class="esr-modal-body" id="esr-modal-body"></div>
    </div>
  </div>

</div>
</div></div></section>
</template>
<style scoped src="../styles/employee-sale-master.css"></style>
