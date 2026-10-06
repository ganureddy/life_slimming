<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { request } from '../api/http';
import { apiUrl } from '../api/config';
import { session } from '../lib/session';
import '../styles/discount-audit.css';

const method = 'life_slimming.api.server_scripts.life_discount_invoice_report.run';
const pageSize = 20;
const from = ref(''), to = ref(''), branch = ref(''), status = ref(''), level = ref(''), search = ref('');
const branches = ref([]), rows = ref([]), page = ref(1), totalPages = ref(1), totalRows = ref(0);
const summary = ref({}), loading = ref(false), error = ref(''), modalRow = ref(null), activePreset = ref('month');
let controller, mounted = true;
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
  if (!validate()) return;
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
    const data = await callApi({ action: 'branches' });
    if (mounted) branches.value = data.branches || [];
  } catch (failure) { if (mounted) error.value = failure.message; }
}
function resetFilters() {
  [from.value, to.value] = businessRange(); branch.value = ''; status.value = ''; level.value = ''; search.value = ''; activePreset.value = 'month'; runReport(1);
}
function xml(value) {
  return String(value ?? '').replace(/[<>&'\"]/g, ch => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '\"': '&quot;' }[ch]));
}
async function exportReport() {
  if (!validate() || loading.value) return;
  loading.value = true; error.value = '';
  try {
    const data = await callApi(reportArgs(1, { page_length: 5000, export: 1 }));
    const exportRows = data.data || [];
    if (!exportRows.length) { error.value = 'No records available to export.'; return; }
    const headers = ['Sales Invoice ID','Invoice Date','Branch','Client Name','Masked Mobile','Referring Name','Before Bill Total (Incl. 5% GST)','Grand Total','Paid Amount','Discount Used','Discount %','L1-L4 Approval Details','Approval Breakup','Approval Status','Outstanding Amount','Payment Entries','Last Payment Date'];
    const keys = ['sales_invoice','invoice_date','branch','client_name','masked_mobile','referring_name','original_bill_total','grand_total','paid_amount','discount_used','discount_percentage','approved_by','approval_breakup','approval_status','outstanding_amount','payment_entries','last_payment_date'];
    const numeric = new Set(['original_bill_total','grand_total','paid_amount','discount_used','discount_percentage','outstanding_amount']);
    const body = [headers, ...exportRows.map(row => keys.map(key => row[key] ?? ''))].map((row, index) => `<Row>${row.map((value, col) => `<Cell><Data ss:Type="${index && numeric.has(keys[col]) ? 'Number' : 'String'}">${xml(value)}</Data></Cell>`).join('')}</Row>`).join('');
    const blob = new Blob([`<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="Discount Report"><Table>${body}</Table></Worksheet></Workbook>`], { type: 'application/vnd.ms-excel;charset=utf-8' });
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = `Discount_Invoice_Report_${from.value}_to_${to.value}.xls`; link.click(); URL.revokeObjectURL(url);
  } catch (failure) { error.value = failure.message || 'Excel export failed.'; }
  finally { loading.value = false; }
}
function invoiceUrl(row) { return apiUrl(`/app/sales-invoice/${encodeURIComponent(row.sales_invoice)}`); }
function closeDetails() { modalRow.value = null; }
function onKeydown(event) { if (event.key === 'Escape') closeDetails(); }
onMounted(() => {
  [from.value, to.value] = businessRange();
  window.addEventListener('keydown', onKeydown);
  loadBranches().then(() => { if (mounted) runReport(1); });
});
onBeforeUnmount(() => { mounted = false; controller?.abort(); window.removeEventListener('keydown', onKeydown); });
</script>

<template>
  <section class="discount-audit">
    <header class="dar-header"><div><h1>Discount Invoice &amp; Collection Report</h1><p>Sales invoices, approved discounts, collections and outstanding balances</p></div></header>
    <section class="dar-card dar-filter-card" aria-label="Report filters">
      <div class="dar-quick-filters"><button v-for="[id,label] in [['today','Today'],['yesterday','Yesterday'],['month','This Month (6th–5th)'],['last','Last Month (6th–5th)']]" :key="id" :class="{active:activePreset===id}" @click="setPreset(id)">{{ label }}</button></div>
      <form class="dar-filters" @submit.prevent="runReport(1)">
        <label>From Date *<input v-model="from" type="date" required @change="activePreset=''" /></label>
        <label>To Date *<input v-model="to" type="date" required @change="activePreset=''" /></label>
        <label>Branch<select v-model="branch"><option value="">All Branches</option><option v-for="name in branches" :key="name" :value="name">{{ name }}</option></select></label>
        <label>Approval Status<select v-model="status"><option value="">All Statuses</option><option>Approved</option><option>Pending Approval</option><option>Rejected</option></select></label>
        <label>Approval Level<select v-model="level"><option value="">All Levels</option><option>L1</option><option>L2</option><option>L3</option><option>L4</option></select></label>
        <label>Search<input v-model="search" type="search" placeholder="Invoice, client, mobile or referring name" /></label>
        <div class="dar-actions"><button type="button" class="dar-btn light" @click="resetFilters">Reset</button><button class="dar-btn primary" :disabled="loading">{{ loading ? 'Loading…' : 'View Report' }}</button><button type="button" class="dar-btn export" :disabled="loading" @click="exportReport">Export Excel</button></div>
      </form>
      <p v-if="error" class="dar-error" role="alert">{{ error }} <button type="button" @click="runReport(page)">Retry</button></p>
    </section>
    <section class="dar-summary" aria-label="Report summary">
      <article v-for="[key,label,tone] in [['invoice_count','Invoices','invoice'],['total_original_bill','Before Bill Total (Incl. 5% GST)','sales'],['total_grand_total','Grand Total','sales'],['total_paid','Paid Amount','paid'],['total_discount','Discount Used','discount'],['total_outstanding','Outstanding','outstanding']]" :key="key" class="dar-card dar-stat" :class="tone"><span>{{ label }}</span><strong>{{ key==='invoice_count'?Number(summary[key]||0).toLocaleString('en-IN'):money(summary[key]) }}</strong></article>
    </section>
    <section class="dar-card dar-table-card">
      <header class="dar-table-head"><strong>Invoice Details</strong><span>{{ recordLabel }}</span></header>
      <p v-if="loading" class="dar-loading" role="status">Loading report…</p>
      <div v-else class="dar-table-wrap" tabindex="0" role="region" aria-label="Discount invoice report table"><table><thead><tr><th>#</th><th>Invoice ID</th><th>Invoice Date</th><th>Branch</th><th>Client Name</th><th>Mobile</th><th>Referring Name</th><th>Before Bill Total (Incl. 5% GST)</th><th>Grand Total</th><th>Paid Amount</th><th>Discount Used</th><th>Discount %</th><th>L1–L4 Approval Details</th><th>Status</th><th>Outstanding</th><th>Payment Entries</th><th>Details</th></tr></thead><tbody>
        <tr v-for="(row,index) in rows" :key="row.sales_invoice"><td>{{ (page-1)*20+index+1 }}</td><td><a :href="invoiceUrl(row)" target="_blank" rel="noopener">{{ row.sales_invoice }}</a></td><td>{{ dateText(row.invoice_date) }}</td><td>{{ row.branch || '—' }}</td><td><strong>{{ row.client_name || '—' }}</strong></td><td :title="row.mobile_number || 'Mobile number unavailable'">{{ row.masked_mobile || '—' }}</td><td>{{ row.referring_name || '—' }}</td><td class="money">{{ money(row.original_bill_total) }}</td><td class="money">{{ money(row.grand_total) }}</td><td class="money">{{ money(row.paid_amount) }}</td><td class="money">{{ money(row.discount_used) }}</td><td>{{ Number(row.discount_percentage||0).toFixed(2) }}%</td><td>{{ row.approved_by || '—' }}<small>{{ row.approval_breakup }}</small></td><td><span class="dar-badge" :class="/approved/i.test(row.approval_status)?'approved':/pending/i.test(row.approval_status)?'pending':/rejected/i.test(row.approval_status)?'rejected':'other'">{{ row.approval_status || 'Not Set' }}</span></td><td class="money">{{ money(row.outstanding_amount) }}</td><td>{{ row.payment_entries || '—' }}</td><td><button class="dar-view" @click="modalRow=row">View Details</button></td></tr>
        <tr v-if="!rows.length"><td colspan="17" class="dar-empty">⌕<strong>No records found</strong><span>Change the filters and try again.</span></td></tr>
      </tbody></table></div>
      <footer class="dar-pagination"><span>Page {{ page }} of {{ totalPages }} · {{ recordLabel }}</span><div><button aria-label="First page" :disabled="loading||page<=1" @click="runReport(1)">«</button><button aria-label="Previous page" :disabled="loading||page<=1" @click="runReport(page-1)">‹</button><button aria-label="Next page" :disabled="loading||page>=totalPages" @click="runReport(page+1)">›</button><button aria-label="Last page" :disabled="loading||page>=totalPages" @click="runReport(totalPages)">»</button></div></footer>
    </section>
    <div v-if="modalRow" class="dar-backdrop" @click.self="closeDetails"><section class="dar-modal" role="dialog" aria-modal="true" aria-label="Invoice details"><header><div><h2>{{ modalRow.sales_invoice }}</h2><p>{{ dateText(modalRow.invoice_date) }} · {{ modalRow.branch || 'Branch not set' }}</p></div><button aria-label="Close" @click="closeDetails">×</button></header><div class="dar-modal-body">
      <section><h3>Client &amp; Invoice Information</h3><div class="dar-detail-grid"><div><small>Client Name</small><strong>{{ modalRow.client_name || '—' }}</strong></div><div><small>Masked Mobile</small><strong>{{ modalRow.masked_mobile || '—' }}</strong></div><div><small>Referring Name</small><strong>{{ modalRow.referring_name || '—' }}</strong></div><div><small>Invoice Date</small><strong>{{ dateText(modalRow.invoice_date) }}</strong></div><div><small>Branch</small><strong>{{ modalRow.branch || '—' }}</strong></div><div><small>Approval Status</small><strong>{{ modalRow.approval_status || 'Not Set' }}</strong></div></div></section>
      <section><h3>Financial Summary</h3><div class="dar-finance-grid"><div><small>Before Bill Total (Incl. 5% GST)</small><strong>{{ money(modalRow.original_bill_total) }}</strong></div><div><small>Grand Total</small><strong>{{ money(modalRow.grand_total) }}</strong></div><div><small>Paid Amount</small><strong>{{ money(modalRow.paid_amount) }}</strong></div><div class="discount"><small>Discount Used</small><strong>{{ money(modalRow.discount_used) }}</strong></div><div class="outstanding"><small>Outstanding</small><strong>{{ money(modalRow.outstanding_amount) }}</strong></div></div></section>
      <section><h3>Discount Approval</h3><div class="dar-detail-grid"><div><small>Total Discount %</small><strong>{{ Number(modalRow.discount_percentage||0).toFixed(2) }}%</strong></div><div><small>L1–L4 Approval Details</small><strong>{{ modalRow.approved_by || '—' }}</strong></div><div><small>Approved At</small><strong>{{ modalRow.latest_approval_at || '—' }}</strong></div></div><p class="dar-note"><b>Approval breakup:</b><br>{{ modalRow.approval_breakup || 'No breakup available' }}</p></section>
      <section><h3>Collection Details</h3><div class="dar-detail-grid"><div><small>Payment Entries</small><strong>{{ modalRow.payment_entries || '—' }}</strong></div><div><small>Last Payment Date</small><strong>{{ dateText(modalRow.last_payment_date) }}</strong></div><div><small>Balance Due</small><strong>{{ money(modalRow.outstanding_amount) }}</strong></div></div></section>
      <footer><button class="dar-btn light" @click="closeDetails">Close</button><a class="dar-btn primary" :href="invoiceUrl(modalRow)" target="_blank" rel="noopener">Open Sales Invoice</a></footer>
    </div></section></div>
  </section>
</template>
