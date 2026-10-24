<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { request } from '../api/http';
import { apiUrl } from '../api/config';
import { session } from '../lib/session';
import '../styles/discount-audit.css';

const method = 'life_slimming.api.server_scripts.life_discount_invoice_report.run';
const pageSize = 20;
const from = ref(''), to = ref(''), branch = ref(''), status = ref(''), level = ref(''), search = ref('');
const branches = ref([]), rows = ref([]), page = ref(1), totalPages = ref(1), totalRows = ref(0);
const summary = ref({}), loading = ref(false), exporting = ref(false), error = ref(''), branchError = ref(''), notice = ref(''), modalRow = ref(null), activePreset = ref('month'), closeButton = ref(null);
let controller, branchController, exportController, noticeTimer, returnFocus, previousOverflow, mounted = true;
const money = value => '₹' + Number(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const dateText = value => value ? String(value).slice(0, 10).split('-').reverse().join('-') : '—';
const recordLabel = computed(() => `${totalRows.value.toLocaleString('en-IN')} record${totalRows.value === 1 ? '' : 's'}`);

function localIso(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
function businessRange(offset = 0) {
  const now = new Date();
  let month = now.getMonth() + (now.getDate() < 6 ? -1 : 0) + offset;
  const year = now.getFullYear() + Math.floor(month / 12);
  month = ((month % 12) + 12) % 12;
  const start = new Date(year, month, 6);
  return [localIso(start), localIso(new Date(start.getFullYear(), start.getMonth() + 1, 5))];
}
function setPreset(which) {
  activePreset.value = which;
  if (which === 'today' || which === 'yesterday') {
    const date = new Date();
    if (which === 'yesterday') date.setDate(date.getDate() - 1);
    from.value = to.value = localIso(date);
  } else [from.value, to.value] = businessRange(which === 'last' ? -1 : 0);
  runReport(1);
}
function validate() {
  if (!from.value || !to.value) { error.value = 'Choose both report dates.'; return false; }
  if (from.value > to.value) { error.value = 'From Date cannot be after To Date.'; return false; }
  return true;
}
async function callApi(args, signal) {
  const response = await request(method, { args, signal, csrfToken: session.csrf_token });
  const data = response.message;
  if (!data?.success) throw new Error(data?.message || 'Invalid response from the report.');
  return data;
}
function reportArgs(targetPage = page.value, extra = {}) {
  return { action: 'report', from_date: from.value, to_date: to.value, branch: branch.value, approval_status: status.value, approval_level: level.value, search: search.value.trim(), page: targetPage, page_length: pageSize, ...extra };
}
async function runReport(targetPage = 1) {
  if (exporting.value || !validate()) return;
  controller?.abort();
  const current = new AbortController(); controller = current;
  loading.value = true; error.value = '';
  try {
    const data = await callApi(reportArgs(targetPage), current.signal);
    if (!mounted || controller !== current) return;
    rows.value = data.data || [];
    summary.value = data.summary || {};
    page.value = Number(data.pagination?.page || targetPage);
    totalPages.value = Math.max(1, Number(data.pagination?.total_pages || 1));
    totalRows.value = Number(data.pagination?.total_rows || 0);
  } catch (failure) {
    if (mounted && controller === current && failure.name !== 'AbortError') {
      rows.value = []; summary.value = {}; totalRows.value = 0; page.value = 1; totalPages.value = 1;
      error.value = failure.message;
    }
  } finally { if (mounted && controller === current) loading.value = false; }
}
async function loadBranches() {
  try {
    branchController?.abort(); branchController = new AbortController(); branchError.value = '';
    const data = await callApi({ action: 'branches' }, branchController.signal);
    if (mounted) branches.value = data.branches || [];
  } catch (failure) { if (mounted && failure.name !== 'AbortError') branchError.value = failure.message; }
}
function resetFilters() {
  [from.value, to.value] = businessRange(); branch.value = ''; status.value = ''; level.value = ''; search.value = ''; activePreset.value = 'month'; runReport(1);
}
function xml(value) {
  return String(value ?? '').replace(/[<>&'\"]/g, ch => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '\"': '&quot;' }[ch]));
}
async function exportReport() {
  if (!validate() || loading.value || exporting.value) return;
  exporting.value = true; error.value = '';
  exportController = new AbortController();
  const exportFrom = from.value, exportTo = to.value;
  try {
    const data = await callApi(reportArgs(1, { page_length: 5000, export: 1 }), exportController.signal);
    if (!mounted) return;
    const exportRows = data.data || [];
    if (!exportRows.length) { error.value = 'No records available to export.'; return; }
    const headers = ['Sales Invoice ID','Invoice Date','Branch','Client Name','Masked Mobile','Referring Name','Before Bill Total (Incl. 5% GST)','Grand Total','Paid Amount','Discount Used','Discount %','L1-L4 Approval Details','Approval Breakup','Approval Status','Outstanding Amount','Payment Entries','Last Payment Date'];
    const keys = ['sales_invoice','invoice_date','branch','client_name','masked_mobile','referring_name','original_bill_total','grand_total','paid_amount','discount_used','discount_percentage','approved_by','approval_breakup','approval_status','outstanding_amount','payment_entries','last_payment_date'];
    const numeric = new Set(['original_bill_total','grand_total','paid_amount','discount_used','discount_percentage','outstanding_amount']);
    const body = [headers, ...exportRows.map(row => keys.map(key => row[key] ?? ''))].map((row, index) => `<Row>${row.map((value, col) => `<Cell><Data ss:Type="${index && numeric.has(keys[col]) ? 'Number' : 'String'}">${xml(value)}</Data></Cell>`).join('')}</Row>`).join('');
    const blob = new Blob([`<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="Discount Report"><Table>${body}</Table></Worksheet></Workbook>`], { type: 'application/vnd.ms-excel;charset=utf-8' });
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = `Discount_Invoice_Report_${exportFrom}_to_${exportTo}.xls`; link.click(); URL.revokeObjectURL(url);
    notice.value = `${exportRows.length} records exported successfully.`; clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => { notice.value = ''; }, 3000);
  } catch (failure) { if (mounted && failure.name !== 'AbortError') error.value = failure.message || 'Excel export failed.'; }
  finally { if (mounted) exporting.value = false; }
}
function invoiceUrl(row) { return apiUrl(`/app/sales-invoice/${encodeURIComponent(row.sales_invoice)}`); }
function statusClass(status) { return /approved/i.test(status) ? 'approved' : /pending/i.test(status) ? 'pending' : /rejected/i.test(status) ? 'rejected' : 'other'; }
function openDetails(row, event) { returnFocus = event.currentTarget; modalRow.value = row; }
function closeDetails() { modalRow.value = null; returnFocus?.focus(); }
watch(modalRow, async row => {
  if (row) { previousOverflow = document.body.style.overflow; document.body.style.overflow = 'hidden'; await nextTick(); closeButton.value?.focus(); }
  else document.body.style.overflow = previousOverflow ?? '';
});
function onKeydown(event) { if (event.key === 'Escape') closeDetails(); }
onMounted(() => {
  [from.value, to.value] = businessRange();
  window.addEventListener('keydown', onKeydown);
  loadBranches(); runReport(1);
});
onBeforeUnmount(() => { mounted = false; controller?.abort(); branchController?.abort(); exportController?.abort(); clearTimeout(noticeTimer); if (modalRow.value) document.body.style.overflow = previousOverflow ?? ''; window.removeEventListener('keydown', onKeydown); });
</script>

<template>
<div id="life-discount-report">
    <div class="ldr-shell">
      <div class="ldr-header">
        <div>
          <h1 class="ldr-title">Discount Invoice & Collection Report</h1>
          <p class="ldr-subtitle">Sales invoices, approved discounts, collections and outstanding balances</p>
        </div>
      </div>

      <section class="ldr-card ldr-filter-card">
        <div class="ldr-quick-filters">
          <button id="ldr-today" :class="{active:activePreset==='today'}" @click="setPreset('today')" class="ldr-quick-btn" :disabled="exporting">Today</button>
          <button id="ldr-yesterday" :class="{active:activePreset==='yesterday'}" @click="setPreset('yesterday')" class="ldr-quick-btn" :disabled="exporting">Yesterday</button>
          <button id="ldr-this-month" :class="{active:activePreset==='month'}" @click="setPreset('month')" class="ldr-quick-btn" :disabled="exporting">This Month (6th–5th)</button>
          <button id="ldr-last-month" :class="{active:activePreset==='last'}" @click="setPreset('last')" class="ldr-quick-btn" :disabled="exporting">Last Month (6th–5th)</button>
        </div>
        <div class="ldr-filters">
          <div class="ldr-field"><label>From Date *</label><input id="ldr-from" v-model="from" @change="activePreset=''" class="ldr-input" type="date"></div>
          <div class="ldr-field"><label>To Date *</label><input id="ldr-to" v-model="to" @change="activePreset=''" class="ldr-input" type="date"></div>
          <div class="ldr-field"><label>Branch</label><select id="ldr-branch" v-model="branch" class="ldr-input"><option value="">All Branches</option><option v-for="name in branches" :key="name" :value="name">{{ name }}</option></select></div>
          <div class="ldr-field"><label>Approval Status</label><select id="ldr-status" v-model="status" class="ldr-input"><option value="">All Statuses</option><option>Approved</option><option>Pending Approval</option><option>Rejected</option></select></div>
          <div class="ldr-field"><label>Approval Level</label><select id="ldr-level" v-model="level" class="ldr-input"><option value="">All Levels</option><option>L1</option><option>L2</option><option>L3</option><option>L4</option></select></div>
          <div class="ldr-field"><label>Search</label><input @keydown.enter.prevent="runReport(1)" id="ldr-search" v-model="search" class="ldr-input" type="search" placeholder="Invoice, client, mobile or referring name"></div>
          <div class="ldr-actions">
            <button id="ldr-reset" @click="resetFilters" :disabled="loading || exporting" class="ldr-btn ldr-btn-light">Reset</button>
            <button id="ldr-run" @click="runReport(1)" :disabled="loading || exporting" class="ldr-btn ldr-btn-primary">View Report</button>
            <button id="ldr-export" @click="exportReport" :disabled="loading || exporting" class="ldr-btn ldr-btn-export">Export Excel</button>
          </div>
        </div>
      <p v-if="error" role="alert" class="ldr-request-error">{{ error }} <button @click="runReport(page)">Retry</button></p><p v-if="branchError" role="alert" class="ldr-request-error">{{ branchError }} <button @click="loadBranches">Retry branches</button></p></section>

      <section class="ldr-summary">
        <div class="ldr-card ldr-stat invoice"><div class="ldr-stat-label">Invoices</div><div id="ldr-count" class="ldr-stat-value">{{ Number(summary.invoice_count||0).toLocaleString('en-IN') }}</div></div>
        <div class="ldr-card ldr-stat sales"><div class="ldr-stat-label">Before Bill Total (Incl. 5% GST)</div><div id="ldr-original" class="ldr-stat-value">{{ money(summary.total_original_bill) }}</div></div>
        <div class="ldr-card ldr-stat sales"><div class="ldr-stat-label">Grand Total</div><div id="ldr-grand" class="ldr-stat-value">{{ money(summary.total_grand_total) }}</div></div>
        <div class="ldr-card ldr-stat paid"><div class="ldr-stat-label">Paid Amount</div><div id="ldr-paid" class="ldr-stat-value">{{ money(summary.total_paid) }}</div></div>
        <div class="ldr-card ldr-stat discount"><div class="ldr-stat-label">Discount Used</div><div id="ldr-discount" class="ldr-stat-value">{{ money(summary.total_discount) }}</div></div>
        <div class="ldr-card ldr-stat outstanding"><div class="ldr-stat-label">Outstanding</div><div id="ldr-outstanding" class="ldr-stat-value">{{ money(summary.total_outstanding) }}</div></div>
      </section>

      <section class="ldr-card ldr-table-card">
        <div class="ldr-table-head"><strong>Invoice Details</strong><span id="ldr-result-count" class="ldr-result-count">{{ recordLabel }}</span></div>
        <div id="ldr-loader" class="ldr-loader" :class="{show:loading || exporting}" role="status"><div class="ldr-spinner"></div>Loading report…</div>
        <div id="ldr-table-wrap" class="ldr-table-wrap" v-show="!loading &amp;&amp; !exporting" tabindex="0" role="region" aria-label="Discount invoices">
          <table class="ldr-table">
            <thead><tr>
              <th>#</th><th>Invoice ID</th><th>Invoice Date</th><th>Branch</th><th>Client Name</th><th>Mobile</th><th>Referring Name</th><th style="text-align:right">Before Bill Total<br>(Incl. 5% GST)</th>
              <th style="text-align:right">Grand Total</th><th style="text-align:right">Paid Amount</th><th style="text-align:right">Discount Used</th>
              <th>Discount %</th><th>L1–L4 Approval Details</th><th>Status</th><th style="text-align:right">Outstanding</th><th>Payment Entries</th><th>Details</th>
            </tr></thead>
            <tbody id="ldr-body"><tr v-for="(row,index) in rows" :key="row.sales_invoice">
 <td class="ldr-muted">{{ (page-1)*20+index+1 }}</td><td><a class="ldr-link" target="_blank" rel="noopener" :href="invoiceUrl(row)">{{ row.sales_invoice }}</a></td><td>{{ dateText(row.invoice_date) }}</td><td>{{ row.branch || '—' }}</td><td><strong>{{ row.client_name || '—' }}</strong></td>
 <td :title="row.mobile_number || 'Mobile number unavailable'">{{ row.masked_mobile || '—' }}</td><td>{{ row.referring_name || '—' }}</td><td class="ldr-money">{{ money(row.original_bill_total) }}</td><td class="ldr-money">{{ money(row.grand_total) }}</td><td class="ldr-money">{{ money(row.paid_amount) }}</td><td class="ldr-money">{{ money(row.discount_used) }}</td><td>{{ Number(row.discount_percentage||0).toFixed(2) }}%</td>
 <td class="ldr-approver">{{ row.approved_by || '—' }}<br><span class="ldr-muted">{{ row.approval_breakup || '' }}</span></td><td><span class="ldr-badge" :class="statusClass(row.approval_status)">{{ row.approval_status || 'Not Set' }}</span></td><td class="ldr-money">{{ money(row.outstanding_amount) }}</td><td class="ldr-approver">{{ row.payment_entries || '—' }}</td><td><button class="ldr-view-btn" @click="openDetails(row,$event)">View Details</button></td>
 </tr><tr v-if="!rows.length"><td colspan="17"><div class="ldr-empty"><div class="ldr-empty-icon">⌕</div><strong>No records found</strong><br><span>Change the filters and try again.</span></div></td></tr></tbody>
          </table>
        </div>
        <div class="ldr-pagination">
          <span id="ldr-page-info" class="ldr-page-info">Page {{ page }} of {{ totalPages }} · {{ recordLabel }}</span>
          <div class="ldr-page-controls">
            <button id="ldr-first" :disabled="loading || exporting || page<=1" @click="runReport(1)" class="ldr-btn ldr-btn-light ldr-page-btn" title="First page">«</button>
            <button id="ldr-prev" :disabled="loading || exporting || page<=1" @click="runReport(page-1)" class="ldr-btn ldr-btn-light ldr-page-btn" title="Previous page">‹</button>
            <button id="ldr-next" :disabled="loading || exporting || page>=totalPages" @click="runReport(page+1)" class="ldr-btn ldr-btn-light ldr-page-btn" title="Next page">›</button>
            <button id="ldr-last" :disabled="loading || exporting || page>=totalPages" @click="runReport(totalPages)" class="ldr-btn ldr-btn-light ldr-page-btn" title="Last page">»</button>
          </div>
        </div>
      </section>
    </div>
    <div id="ldr-modal-backdrop" class="ldr-modal-backdrop show" v-if="modalRow" @click.self="closeDetails">
      <div class="ldr-modal" role="dialog" aria-modal="true" aria-labelledby="ldr-modal-title">
        <div class="ldr-modal-head">
          <div><h2 id="ldr-modal-title">{{ modalRow.sales_invoice || 'Invoice Details' }}</h2><p id="ldr-modal-subtitle">{{ dateText(modalRow.invoice_date) }} · {{ modalRow.branch || 'Branch not set' }}</p></div>
          <button id="ldr-modal-close" ref="closeButton" @click="closeDetails" class="ldr-modal-close" aria-label="Close">×</button>
        </div>
        <div id="ldr-modal-body" class="ldr-modal-body"><section class="ldr-modal-section"><h3 class="ldr-section-title">Client &amp; Invoice Information</h3><div class="ldr-detail-grid"><div class="ldr-detail"><div class="ldr-detail-label">Client Name</div><div class="ldr-detail-value">{{ modalRow.client_name || '—' }}</div></div><div class="ldr-detail"><div class="ldr-detail-label">Masked Mobile</div><div class="ldr-detail-value">{{ modalRow.masked_mobile || '—' }}</div></div><div class="ldr-detail"><div class="ldr-detail-label">Referring Name</div><div class="ldr-detail-value">{{ modalRow.referring_name || '—' }}</div></div><div class="ldr-detail"><div class="ldr-detail-label">Invoice Date</div><div class="ldr-detail-value">{{ dateText(modalRow.invoice_date) }}</div></div><div class="ldr-detail"><div class="ldr-detail-label">Branch</div><div class="ldr-detail-value">{{ modalRow.branch || '—' }}</div></div><div class="ldr-detail"><div class="ldr-detail-label">Approval Status</div><div class="ldr-detail-value"><span class="ldr-badge" :class="statusClass(modalRow.approval_status)">{{ modalRow.approval_status || 'Not Set' }}</span></div></div></div></section><section class="ldr-modal-section"><h3 class="ldr-section-title">Financial Summary</h3><div class="ldr-finance-grid"><div class="ldr-finance "><div class="ldr-detail-label">Before Bill Total (Incl. 5% GST)</div><div class="ldr-detail-value">{{ money(modalRow.original_bill_total) }}</div></div><div class="ldr-finance "><div class="ldr-detail-label">Grand Total</div><div class="ldr-detail-value">{{ money(modalRow.grand_total) }}</div></div><div class="ldr-finance "><div class="ldr-detail-label">Paid Amount</div><div class="ldr-detail-value">{{ money(modalRow.paid_amount) }}</div></div><div class="ldr-finance discount"><div class="ldr-detail-label">Discount Used</div><div class="ldr-detail-value">{{ money(modalRow.discount_used) }}</div></div><div class="ldr-finance outstanding"><div class="ldr-detail-label">Outstanding</div><div class="ldr-detail-value">{{ money(modalRow.outstanding_amount) }}</div></div></div></section><section class="ldr-modal-section"><h3 class="ldr-section-title">Discount Approval</h3><div class="ldr-detail-grid"><div class="ldr-detail"><div class="ldr-detail-label">Total Discount %</div><div class="ldr-detail-value">{{ Number(modalRow.discount_percentage||0).toFixed(2)+'%' }}</div></div><div class="ldr-detail"><div class="ldr-detail-label">L1–L4 Approval Details</div><div class="ldr-detail-value">{{ modalRow.approved_by || '—' }}</div></div><div class="ldr-detail"><div class="ldr-detail-label">Approved At</div><div class="ldr-detail-value">{{ modalRow.latest_approval_at || '—' }}</div></div></div><div class="ldr-modal-note" style="margin-top:10px"><strong>Approval breakup:</strong><br>{{ modalRow.approval_breakup || 'No breakup available' }}</div></section><section class="ldr-modal-section"><h3 class="ldr-section-title">Collection Details</h3><div class="ldr-detail-grid"><div class="ldr-detail"><div class="ldr-detail-label">Payment Entries</div><div class="ldr-detail-value">{{ modalRow.payment_entries || '—' }}</div></div><div class="ldr-detail"><div class="ldr-detail-label">Last Payment Date</div><div class="ldr-detail-value">{{ dateText(modalRow.last_payment_date) }}</div></div><div class="ldr-detail"><div class="ldr-detail-label">Balance Due</div><div class="ldr-detail-value">{{ money(modalRow.outstanding_amount) }}</div></div></div></section><div class="ldr-modal-actions"><button class="ldr-btn ldr-btn-light" @click="closeDetails">Close</button><a class="ldr-btn ldr-btn-primary" target="_blank" rel="noopener" :href="invoiceUrl(modalRow)">Open Sales Invoice</a></div></div>
      </div>
    </div>
    <div id="ldr-toasts" class="ldr-toast-wrap" role="status"><div v-if="notice" class="ldr-toast success">{{ notice }}</div></div>
</div>
</template>
