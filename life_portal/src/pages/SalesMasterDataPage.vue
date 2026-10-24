<script setup>
import { computed } from 'vue';
import { useSalesMaster } from '../composables/useSalesMaster';
import SearchSelect from '../components/SearchSelect.vue';
const { mainCategory,therapyGroup,therapyType,therapyOptions, cols, presets, from, to, quick, branch, salesPerson, bookingType, modeOfPayment, customer, paidFrom, paidTo, outstandingOperator, outstandingValue, format, permittedBranches, allBranchAccess, branchRestricted, branchReady, branchError, rows, filteredRows, employees, loading, error, notice, page, reportLoaded, pageCount, visibleRows, money, recordCount, totals, rowValue, formatDate, getBranches, applyFilters, setPreset, resetFilters, downloadReport, downloading, appliedState } = useSalesMaster();
const branchOptions = computed(() => [...(allBranchAccess.value || permittedBranches.value.length > 1 ? [{value:'',label:'All Branches'}] : []), ...permittedBranches.value.map(name => ({value:name,label:name}))]);
const employeeOptions = computed(() => [{value:'',label:'All Employees'}, ...employees.value.map(name => ({value:name,label:name}))]);
const bookingTypeOptions = [{value:'',label:'All Booking Types'}, ...[{"value": "Call Center", "label": "Call Center"}, {"value": "DIRECT WALKIN", "label": "DIRECT WALKIN"}, {"value": "Existing Customer", "label": "Existing Customer"}, {"value": "InHouse", "label": "InHouse"}, {"value": "Reference", "label": "Reference"}, {"value": "Unjoined", "label": "Unjoined"}, {"value": "Walk In", "label": "Walk In"}]];
const modeOfPaymentOptions = [{value:'',label:'All Modes'}, ...[{"value": "Bajaj Card Charges", "label": "Bajaj Card Charges"}, {"value": "Carepay", "label": "Carepay"}, {"value": "Cash", "label": "Cash"}, {"value": "Credit Card", "label": "Credit Card"}, {"value": "Debit Card", "label": "Debit Card"}, {"value": "Fibe Finance", "label": "Fibe Finance"}, {"value": "Online Transfer(Bank)", "label": "Online Transfer(Bank)"}, {"value": "Razorpay Software Pvt Ltd -Link", "label": "Razorpay Software Pvt Ltd -Link"}, {"value": "Sai Roshini Card Charges", "label": "Sai Roshini Card Charges"}, {"value": "Savein Fintech Card Charges", "label": "Savein Fintech Card Charges"}, {"value": "ShopSE", "label": "ShopSE"}, {"value": "mobile payments", "label": "mobile payments"}]];
const numericKeys = new Set(['paid_amount','tax_amount','paid_amount_without_tax','grand_total','outstanding_amount']);
const pageNumbers = computed(() => { const start = Math.max(1,page.value - 2), end = Math.min(pageCount.value,page.value + 2); return Array.from({length:end-start+1},(_,index) => start+index); });
</script>

<template>
<div id="sales-master-root">
<div class="rr-wrap">
<div class="rr-hdr">
<div><div class="rr-title">Life Sales Master Data</div></div>
</div>
<div class="rr-body">
<div class="rr-grid2">
<div>
<label class="rr-lbl" for="rr_from">From Date</label>
<input @change="quick = ''" @keydown.enter.prevent="applyFilters" class="rr-input" id="rr_from" type="date" v-model="from"/>
</div>
<div>
<label class="rr-lbl" for="rr_to">To Date</label>
<input @change="quick = ''" @keydown.enter.prevent="applyFilters" class="rr-input" id="rr_to" type="date" v-model="to"/>
</div>
</div>
<div class="rr-qrow">
<button :class="{'rr-qbtn-on':quick === 'today'}" @click="setPreset('today')" class="rr-qbtn" data-q="today" type="button">Today</button>
<button :class="{'rr-qbtn-on':quick === 'yesterday'}" @click="setPreset('yesterday')" class="rr-qbtn" data-q="yesterday" type="button">Yesterday</button>
<button :class="{'rr-qbtn-on':quick === 'thismonth'}" @click="setPreset('thismonth')" class="rr-qbtn" data-q="thismonth" type="button">This Month</button>
<button :class="{'rr-qbtn-on':quick === 'lastmonth'}" @click="setPreset('lastmonth')" class="rr-qbtn" data-q="lastmonth" type="button">Last Month</button>
<button :class="{'rr-qbtn-on':quick === 'thisquarter'}" @click="setPreset('thisquarter')" class="rr-qbtn" data-q="thisquarter" type="button">This Quarter</button>
<button :class="{'rr-qbtn-on':quick === 'thisfy'}" @click="setPreset('thisfy')" class="rr-qbtn" data-q="thisfy" type="button">This Financial Year</button>
</div>
<div class="rr-grid3">
<div>
<label class="rr-lbl">Branch</label>
<SearchSelect :disabled="!branchReady || (branchRestricted &amp;&amp; permittedBranches.length === 1)" :options="branchOptions" empty-label="All Branches" id="rr_ss_branch" label="Branch" placeholder="Search branch..." v-model="branch"></SearchSelect>
<input :value="branch" id="rr_branch" type="hidden" value=""/>
</div>
<div>
<label class="rr-lbl">Sales Person / Employee</label>
<SearchSelect :options="employeeOptions" empty-label="All Employees" id="rr_ss_sp" label="Sales Person / Employee" placeholder="Search employee..." v-model="salesPerson"></SearchSelect>
<input :value="salesPerson" id="rr_sp" type="hidden" value=""/>
</div>
<div>
<label class="rr-lbl">Booking Type</label>
<SearchSelect :options="bookingTypeOptions" empty-label="All Booking Types" id="rr_ss_booking" label="Booking Type" placeholder="Search type..." v-model="bookingType"></SearchSelect>
<input :value="bookingType" id="rr_booking" type="hidden" value=""/>
</div>
</div>
<div class="rr-grid4">
<div>
<label class="rr-lbl">Mode of Payment</label>
<SearchSelect :options="modeOfPaymentOptions" empty-label="All Modes" id="rr_ss_mop" label="Mode of Payment" placeholder="Search mode..." v-model="modeOfPayment"></SearchSelect>
<input :value="modeOfPayment" id="rr_mop" type="hidden" value=""/>
</div>
<div>
<label class="rr-lbl" for="rr_customer">Customer Name / Mobile / ID</label>
<input @keydown.enter.prevent="applyFilters" autocomplete="off" class="rr-input" id="rr_customer" placeholder="Search..." type="text" v-model="customer"/>
</div>
<div>
<label class="rr-lbl" for="rr_amt_from">Paid Amount From, ex-GST (₹)</label>
<input @keydown.enter.prevent="applyFilters" autocomplete="off" class="rr-input" id="rr_amt_from" inputmode="decimal" placeholder="Min" type="text" v-model="paidFrom"/>
</div>
<div>
<label class="rr-lbl" for="rr_amt_to">Paid Amount To, ex-GST (₹)</label>
<input @keydown.enter.prevent="applyFilters" autocomplete="off" class="rr-input" id="rr_amt_to" inputmode="decimal" placeholder="Max" type="text" v-model="paidTo"/>
</div>
</div>
<div class="rr-outstanding-panel">
<div class="rr-outstanding-copy">
<div class="rr-section-title">Outstanding Amount Filter</div>
<div class="rr-section-help">
          This condition filters the <b>Outstanding</b> column only.
          It does not change or depend on Paid Amount From / To.
        </div>
</div>
<div class="rr-outstanding-fields">
<div>
<label class="rr-lbl" for="rr_out_operator">Outstanding Condition</label>
<select class="rr-input rr-select" id="rr_out_operator" v-model="outstandingOperator">
<option value="">No Outstanding Condition</option>
<option value="&gt;">Greater Than (&gt;)</option>
<option value="&gt;=">Greater Than or Equal (&gt;=)</option>
<option value="&lt;">Less Than (&lt;)</option>
<option value="&lt;=">Less Than or Equal (&lt;=)</option>
</select>
</div>
<div>
<label class="rr-lbl" for="rr_out_value">Outstanding Amount (₹)</label>
<input :disabled="!outstandingOperator" @keydown.enter.prevent="applyFilters" autocomplete="off" class="rr-input" id="rr_out_value" inputmode="decimal" placeholder="Enter outstanding amount" type="text" v-model="outstandingValue"/>
</div>
</div>
</div>
<div class="rr-grid2">
<div><label class="rr-lbl">Main Category</label><SearchSelect v-model="mainCategory" :options="[{value:'',label:'All Main Categories'},...therapyOptions.mainCategory.map(value=>({value,label:value}))]" label="Main Category" id="rr_ss_main_category" /></div>
<div><label class="rr-lbl">Therapy Group</label><SearchSelect v-model="therapyGroup" :options="[{value:'',label:'All Therapy Groups'},...therapyOptions.therapyGroup.map(value=>({value,label:value}))]" label="Therapy Group" id="rr_ss_therapy_group" /></div>
<div><label class="rr-lbl">Therapy Type</label><SearchSelect v-model="therapyType" :options="[{value:'',label:'All Therapy Types'},...therapyOptions.therapyType.map(value=>({value,label:value}))]" label="Therapy Type" id="rr_ss_therapy_type" /></div>
</div>
<div class="rr-apply-row">
<div class="rr-apply-note">Change the required filters, then click Apply Filters.</div>
<button :disabled="loading || downloading || !branchReady" @click="applyFilters" class="rr-btn rr-btn-apply" id="rr_apply_btn" type="button">{{ loading ? 'Applying...' : 'Apply Filters' }}</button>
</div>
</div>
<div class="rr-footer">
<div class="rr-colcount">
      Preview includes <b>12 visible columns</b>: invoice date, branch, customer,
      booking type, employee, therapy categories/groups/types, payment mode,
      paid amount without GST and outstanding.
    </div>
<div class="rr-export-group">
<span class="rr-export-label">Download Format</span>
<div aria-label="Download format" class="rr-fmtrow" role="group">
<button :aria-pressed="format === 'xlsx'" :class="{'rr-fchip-on':format === 'xlsx'}" @click="format = 'xlsx'" class="rr-fchip" data-f="xlsx" type="button">Excel</button>
<button :aria-pressed="format === 'csv'" :class="{'rr-fchip-on':format === 'csv'}" @click="format = 'csv'" class="rr-fchip" data-f="csv" type="button">CSV</button>
</div>
<button :disabled="loading || downloading || !branchReady" @click="downloadReport" class="rr-btn rr-btn-gold" id="rr_dl_btn" type="button">{{ downloading ? 'Preparing...' : 'Generate &amp; Download' }}</button>
</div>
</div>
<div :style="{color:error || branchError ? '#c0392b' : '#0d2b4e'}" class="rr-msg" id="rr_msg" role="status" style="display:block" v-if="error || branchError || notice || loading">{{ error || branchError || (loading ? 'Loading data…' : notice) }}</div>
<div class="rr-tbl-wrap" id="rr_tbl_wrap" v-if="reportLoaded &amp;&amp; !loading"><table class="rr-table"><thead><tr><th :class="{'rr-num':numericKeys.has(key)}" :key="key" v-for="[key,label] in cols">{{ label }}</th></tr></thead><tbody><tr :class="index % 2 ? 'rr-row-odd' : 'rr-row-even'" :key="row.branch + '::' + row.invoice + '::' + index" v-for="(row,index) in visibleRows"><td :class="key === 'sales_people' ? 'rr-sales-person-td' : numericKeys.has(key) ? 'rr-num' : ''" :key="key" v-for="[key] in cols"><div class="rr-sales-person-cell" v-if="key === 'sales_people'"><div class="rr-sales-person-primary" v-if="row.referring_employee">{{ row.referring_employee }}{{ row.incentive_employee ? ' /' : '' }}</div><div :class="row.referring_employee ? 'rr-sales-person-secondary' : 'rr-sales-person-primary'" v-if="row.incentive_employee">{{ row.incentive_employee }}</div></div><template v-else="">{{ rowValue(row,key) }}</template></td></tr><tr v-if="!visibleRows.length"><td class="rr-nodata" colspan="12">No records match the selected filters.</td></tr></tbody><tfoot><tr><td :class="{'rr-num':numericKeys.has(key)}" :key="key" v-for="[key] in cols">{{ key === 'invoice' ? 'TOTAL (' + filteredRows.length + ' rows)' : numericKeys.has(key) ? money(totals[key]) : '' }}</td></tr></tfoot></table>
<div class="rr-pgbar"><button :disabled="page === 1" @click="page = 1" class="rr-pgbtn" id="rr_pg_first">« First</button><button :disabled="page === 1" @click="page--" class="rr-pgbtn" id="rr_pg_prev">‹ Prev</button><button :class="{'rr-pgnum-on':page === value}" :key="value" @click="page = value" class="rr-pgbtn rr-pgnum" v-for="value in pageNumbers">{{ value }}</button><span v-if="pageNumbers[pageNumbers.length - 1] < pageCount" class="rr-pgdots">…</span><button :disabled="page === pageCount" @click="page++" class="rr-pgbtn" id="rr_pg_next">Next ›</button><button :disabled="page === pageCount" @click="page = pageCount" class="rr-pgbtn" id="rr_pg_last">Last »</button><span class="rr-pginfo">Page <b>{{ page }}</b> of <b>{{ pageCount }}</b> | {{ filteredRows.length }} records<template v-if="appliedState?.branch"> | Branch: <b>{{ appliedState.branch }}</b></template></span></div></div>
</div>
</div>
</template>
<style>
/* ERPNext Web Page > Style */
/* ============================================================
   SALES MASTER DATA — LIFE GREEN THEME
   ============================================================ */
#sales-master-root .rr-wrap,
#sales-master-root .rr-wrap * { box-sizing: border-box; }
#sales-master-root .rr-wrap {
  width: 100%; overflow: visible; color: #152418;
  font-family: "Inter","Segoe UI",Arial,system-ui,sans-serif;
  font-size: 12px; line-height: 1.45; background: #f3faf4;
  border: 1px solid #dce9de; border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15,61,30,.06), 0 8px 24px rgba(15,61,30,.08);
}


#sales-master-root .rr-hdr {
  padding: 15px 18px; color: #fff;
  background: linear-gradient(135deg,#0f3d1e 0%,#1b5e20 70%,#2e7d32 100%);
  border-radius: 11px 11px 0 0; box-shadow: 0 2px 12px rgba(15,61,30,.25);
}
#sales-master-root .rr-title { color:#fff; font-size:16px; font-weight:800; line-height:1.2; text-shadow:0 1px 2px rgba(0,0,0,.2); }
#sales-master-root .rr-sub { margin-top:4px; color:#ddf5e1; font-size:10.5px; font-weight:500; letter-spacing:.2px; }
#sales-master-root .rr-body { padding:18px; background:#f3faf4; }
#sales-master-root .rr-lbl { display:block; margin-bottom:5px; color:#5f6f63; font-size:9.5px; font-weight:800; letter-spacing:.85px; line-height:1.2; text-transform:uppercase; }
#sales-master-root .rr-input { width:100%; height:36px; padding:0 10px; color:#152418; font-family:inherit; font-size:11.5px; background:#fff; border:1.5px solid #dce9de; border-radius:8px; outline:none; transition:border-color .15s,box-shadow .15s,background .15s; }
#sales-master-root .rr-input::placeholder { color:#87968b; }
#sales-master-root .rr-input:hover:not(:disabled) { border-color:#a5d6a7; }
#sales-master-root .rr-input:focus { background:#fff; border-color:#43a047; box-shadow:0 0 0 3px rgba(67,160,71,.12); }
#sales-master-root .rr-input:disabled { color:#7f8d82; cursor:not-allowed; background:#eef4ef; border-color:#d7e4d9; }
#sales-master-root .rr-select { cursor:pointer; }
#sales-master-root .rr-grid2,#sales-master-root .rr-grid3,#sales-master-root .rr-grid4 { display:grid; gap:12px; margin-bottom:14px; }
#sales-master-root .rr-grid2 { grid-template-columns:repeat(2,minmax(0,1fr)); }
#sales-master-root .rr-grid3 { grid-template-columns:repeat(3,minmax(0,1fr)); }
#sales-master-root .rr-grid4 { grid-template-columns:minmax(180px,1.15fr) minmax(220px,1.35fr) minmax(145px,.8fr) minmax(145px,.8fr); }
#sales-master-root .rr-qrow { display:flex; flex-wrap:wrap; gap:7px; margin:3px 0 18px; }
#sales-master-root .rr-qbtn { min-height:30px; padding:0 13px; color:#14501f; font-family:inherit; font-size:10.5px; font-weight:800; cursor:pointer; background:#fff; border:1.5px solid #dce9de; border-radius:999px; transition:color .15s,background .15s,border-color .15s,transform .15s,box-shadow .15s; }
#sales-master-root .rr-qbtn:hover { color:#0f3d1e; background:#e8f5e9; border-color:#66bb6a; transform:translateY(-1px); }
#sales-master-root .rr-qbtn-on { color:#fff; background:linear-gradient(135deg,#2e7d32,#1b5e20); border-color:#1b5e20; box-shadow:0 3px 10px rgba(27,94,32,.3); }
#sales-master-root .rr-ss { position:relative; min-width:0; user-select:none; }
#sales-master-root .rr-ss-display { display:flex; align-items:center; justify-content:space-between; width:100%; height:36px; padding:0 10px; color:#152418; font-family:inherit; font-size:11.5px; cursor:pointer; background:#fff; border:1.5px solid #dce9de; border-radius:8px; transition:border-color .15s,box-shadow .15s,background .15s; }
#sales-master-root .rr-ss-display:hover { border-color:#a5d6a7; }
#sales-master-root .rr-ss-open .rr-ss-display { background:#fff; border-color:#43a047; box-shadow:0 0 0 3px rgba(67,160,71,.12); }
#sales-master-root .rr-ss-val { min-width:0; overflow:hidden; color:#152418; text-overflow:ellipsis; white-space:nowrap; }
#sales-master-root .rr-ss-arrow { flex:0 0 auto; margin-left:8px; color:#2e7d32; font-size:9px; }
#sales-master-root .rr-ss-drop { position:absolute; z-index:9999; top:39px; right:0; left:0; display:none; overflow:hidden; background:#fff; border:1.5px solid #43a047; border-radius:9px; box-shadow:0 10px 28px rgba(15,61,30,.18); }
#sales-master-root .rr-ss-search { width:100%; height:34px; padding:0 10px; color:#152418; font-family:inherit; font-size:11px; background:#f3faf4; border:0; border-bottom:1px solid #dce9de; outline:none; }
#sales-master-root .rr-ss-search::placeholder { color:#87968b; }
#sales-master-root .rr-ss-list { max-height:210px; overflow-y:auto; }
#sales-master-root .rr-ss-opt { padding:7px 10px; overflow:hidden; color:#152418; font-size:11px; cursor:pointer; text-overflow:ellipsis; white-space:nowrap; }
#sales-master-root .rr-ss-opt:hover { color:#14501f; background:#e8f5e9; }
#sales-master-root .rr-ss-sel,#sales-master-root .rr-ss-sel:hover { color:#fff !important; font-weight:800; background:linear-gradient(135deg,#2e7d32,#1b5e20); }
#sales-master-root .rr-outstanding-panel { display:grid; grid-template-columns:minmax(260px,1fr) minmax(400px,1.35fr); gap:18px; align-items:center; margin-top:2px; padding:14px; background:linear-gradient(135deg,#f2fbf3,#e8f5e9); border:1px solid #b9dfbe; border-radius:12px; box-shadow:0 1px 2px rgba(15,61,30,.05); }
#sales-master-root .rr-section-title { color:#0f3d1e; font-size:12.5px; font-weight:800; }
#sales-master-root .rr-section-help { margin-top:4px; color:#52665a; font-size:10.5px; line-height:1.5; }
#sales-master-root .rr-section-help b { color:#14501f; }
#sales-master-root .rr-outstanding-fields { display:grid; grid-template-columns:minmax(190px,1fr) minmax(190px,1fr); gap:10px; }
#sales-master-root .rr-apply-row { display:flex; align-items:center; justify-content:flex-end; gap:14px; margin-top:14px; padding:14px 0 2px; border-top:1px dashed #cfe1d2; }
#sales-master-root .rr-apply-note { margin-right:auto; color:#5f6f63; font-size:10.5px; }
#sales-master-root .rr-btn { height:36px; padding:0 17px; font-family:inherit; font-size:11px; font-weight:800; cursor:pointer; border-radius:9px; transition:background .15s,border-color .15s,transform .15s,box-shadow .15s,opacity .15s; }
#sales-master-root .rr-btn:hover:not(:disabled) { transform:translateY(-1px); }
#sales-master-root .rr-btn:disabled { opacity:.5; cursor:not-allowed; transform:none; }
#sales-master-root .rr-btn-apply { min-width:130px; color:#fff; background:linear-gradient(135deg,#2e7d32,#1b5e20); border:1.5px solid #1b5e20; box-shadow:0 3px 10px rgba(27,94,32,.28); }
#sales-master-root .rr-btn-apply:hover:not(:disabled) { background:linear-gradient(135deg,#388e3c,#14501f); box-shadow:0 5px 14px rgba(27,94,32,.34); }
#sales-master-root .rr-footer { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:14px 18px; background:#fff; border-top:1px solid #dce9de; }
#sales-master-root .rr-colcount { max-width:760px; color:#5f6f63; font-size:10.5px; line-height:1.5; }
#sales-master-root .rr-colcount b { color:#14501f; }
#sales-master-root .rr-export-group { display:flex; flex:0 0 auto; align-items:center; gap:8px; padding:8px 10px 8px 16px; background:#fafcfa; border:1px solid #dce9de; border-radius:11px; }
#sales-master-root .rr-export-label { margin-right:2px; color:#5f6f63; font-size:9.5px; font-weight:800; letter-spacing:.8px; text-transform:uppercase; }
#sales-master-root .rr-fmtrow { display:flex; gap:6px; }
#sales-master-root .rr-fchip { height:30px; padding:0 12px; color:#14501f; font-family:inherit; font-size:10px; font-weight:800; cursor:pointer; background:#fff; border:1.5px solid #a5d6a7; border-radius:999px; transition:color .15s,background .15s,border-color .15s,box-shadow .15s; }
#sales-master-root .rr-fchip:hover { background:#e8f5e9; border-color:#66bb6a; }
#sales-master-root .rr-fchip-on { color:#fff; background:linear-gradient(135deg,#43a047,#1b5e20); border-color:#1b5e20; box-shadow:0 2px 7px rgba(27,94,32,.24); }
#sales-master-root .rr-btn-gold { min-width:170px; color:#fff; background:linear-gradient(135deg,#2e7d32,#1b5e20); border:1.5px solid #1b5e20; box-shadow:0 3px 10px rgba(27,94,32,.28); }
#sales-master-root .rr-btn-gold:hover:not(:disabled) { background:linear-gradient(135deg,#388e3c,#14501f); box-shadow:0 5px 14px rgba(27,94,32,.34); }
#sales-master-root .rr-msg { display:none; padding:10px 18px; color:#14501f; font-size:11px; font-weight:600; background:#f3faf4; border-top:1px solid #dce9de; }
#sales-master-root .rr-tbl-wrap { width:100%; overflow-x:auto; background:#fff; border-radius:0 0 11px 11px; }
#sales-master-root .rr-table { width:100%; min-width:1120px; border-collapse:collapse; font-size:11px; }
#sales-master-root .rr-table thead tr { color:#fff; background:linear-gradient(135deg,#0f3d1e,#1b5e20); }
#sales-master-root .rr-table thead th { padding:9px; color:#fff; font-size:10px; font-weight:800; letter-spacing:.45px; text-align:left; text-transform:uppercase; white-space:nowrap; border-bottom:2px solid #43a047; }
#sales-master-root .rr-table tbody td { padding:8px 9px; color:#152418; white-space:nowrap; border-bottom:1px solid #eef4ef; }
#sales-master-root .rr-row-even { background:#f8fcf8; }
#sales-master-root .rr-row-odd { background:#fff; }
#sales-master-root .rr-table tbody tr:hover td { background:#f3faf4; }
#sales-master-root .rr-num { text-align:right !important; font-variant-numeric:tabular-nums; }
#sales-master-root .rr-table tfoot tr { color:#14501f; font-weight:800; background:linear-gradient(135deg,#e8f5e9,#f3faf4); border-top:2px solid #a5d6a7; }
#sales-master-root .rr-table tfoot td { padding:9px; font-size:11px; white-space:nowrap; }
#sales-master-root .rr-nodata { padding:30px !important; color:#5f6f63 !important; font-style:italic; text-align:center; }
#sales-master-root .rr-pgbar { display:flex; flex-wrap:wrap; align-items:center; gap:5px; padding:11px 13px; background:#fafcfa; border-top:1px solid #dce9de; border-radius:0 0 11px 11px; }
#sales-master-root .rr-pgbtn { min-width:32px; height:29px; padding:0 10px; color:#14501f; font-family:inherit; font-size:10.5px; font-weight:800; cursor:pointer; background:#fff; border:1.5px solid #cfe1d2; border-radius:7px; transition:color .15s,background .15s,border-color .15s; }
#sales-master-root .rr-pgbtn:hover:not(:disabled) { color:#fff; background:#2e7d32; border-color:#2e7d32; }
#sales-master-root .rr-pgbtn:disabled { opacity:.35; cursor:not-allowed; }
#sales-master-root .rr-pgnum-on { color:#fff; background:linear-gradient(135deg,#2e7d32,#1b5e20); border-color:#1b5e20; }
#sales-master-root .rr-pgdots { padding:0 2px; color:#87968b; font-size:12px; }
#sales-master-root .rr-pginfo { margin-left:7px; color:#5f6f63; font-size:10.5px; }
#sales-master-root .rr-pginfo b { color:#14501f; }
#sales-master-root .rr-ss-list::-webkit-scrollbar,#sales-master-root .rr-tbl-wrap::-webkit-scrollbar { width:9px; height:9px; }
#sales-master-root .rr-ss-list::-webkit-scrollbar-track,#sales-master-root .rr-tbl-wrap::-webkit-scrollbar-track { background:#eef4ef; }
#sales-master-root .rr-ss-list::-webkit-scrollbar-thumb,#sales-master-root .rr-tbl-wrap::-webkit-scrollbar-thumb { background:#a5d6a7; border-radius:999px; }
#sales-master-root .rr-ss-list::-webkit-scrollbar-thumb:hover,#sales-master-root .rr-tbl-wrap::-webkit-scrollbar-thumb:hover { background:#66bb6a; }
@media (max-width:1100px){ #sales-master-root .rr-grid4{grid-template-columns:repeat(2,minmax(0,1fr));} #sales-master-root .rr-outstanding-panel{grid-template-columns:1fr;} }
@media (max-width:820px){ #sales-master-root .rr-grid3{grid-template-columns:1fr;} #sales-master-root .rr-footer{align-items:flex-start;flex-direction:column;} #sales-master-root .rr-export-group{width:100%;padding:10px;border-left:1px solid #dce9de;} }
@media (max-width:620px){ #sales-master-root .rr-body{padding:14px;} #sales-master-root .rr-grid2,#sales-master-root .rr-grid4,#sales-master-root .rr-outstanding-fields{grid-template-columns:1fr;} #sales-master-root .rr-apply-row{align-items:stretch;flex-direction:column;} #sales-master-root .rr-apply-note{margin-right:0;} #sales-master-root .rr-btn-apply{width:100%;} #sales-master-root .rr-export-group{align-items:stretch;flex-wrap:wrap;} #sales-master-root .rr-export-label{width:100%;} #sales-master-root .rr-btn-gold{flex:1 1 100%;width:100%;} }

/* ============================================================
   SALES PERSON — REFERRING FIRST, INCENTIVE BELOW
   ============================================================ */
#sales-master-root .rr-sales-person-td {
  min-width: 170px;
  white-space: normal;
}

#sales-master-root .rr-sales-person-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 150px;
  line-height: 1.25;
}

#sales-master-root .rr-sales-person-primary {
  color: #152418;
  font-size: 10.8px;
  font-weight: 800;
  white-space: normal;
}

#sales-master-root .rr-sales-person-secondary {
  padding-top: 3px;
  color: #35633d;
  font-size: 10px;
  font-weight: 700;
  white-space: normal;
  border-top: 1px dashed #cfe1d2;
}

#sales-master-root .rr-table {
  min-width: 1360px;
}


</style>

<style scoped>
/* ERPNext Web Page > Style */
/* ============================================================
   SALES MASTER DATA — LIFE GREEN THEME
   ============================================================ */
#sales-master-root .rr-wrap,
#sales-master-root .rr-wrap * { box-sizing: border-box; }
#sales-master-root .rr-wrap {
  width: 100%; overflow: visible; color: #152418;
  font-family: "Inter","Segoe UI",Arial,system-ui,sans-serif;
  font-size: 12px; line-height: 1.45; background: #f3faf4;
  border: 1px solid #dce9de; border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15,61,30,.06), 0 8px 24px rgba(15,61,30,.08);
}
.navbar { display: none; }
.web-footer { display: none; }
#sales-master-root .rr-hdr {
  padding: 15px 18px; color: #fff;
  background: linear-gradient(135deg,#0f3d1e 0%,#1b5e20 70%,#2e7d32 100%);
  border-radius: 11px 11px 0 0; box-shadow: 0 2px 12px rgba(15,61,30,.25);
}
#sales-master-root .rr-title { color:#fff; font-size:16px; font-weight:800; line-height:1.2; text-shadow:0 1px 2px rgba(0,0,0,.2); }
#sales-master-root .rr-sub { margin-top:4px; color:#ddf5e1; font-size:10.5px; font-weight:500; letter-spacing:.2px; }
#sales-master-root .rr-body { padding:18px; background:#f3faf4; }
#sales-master-root .rr-lbl { display:block; margin-bottom:5px; color:#5f6f63; font-size:9.5px; font-weight:800; letter-spacing:.85px; line-height:1.2; text-transform:uppercase; }
#sales-master-root .rr-input { width:100%; height:36px; padding:0 10px; color:#152418; font-family:inherit; font-size:11.5px; background:#fff; border:1.5px solid #dce9de; border-radius:8px; outline:none; transition:border-color .15s,box-shadow .15s,background .15s; }
#sales-master-root .rr-input::placeholder { color:#87968b; }
#sales-master-root .rr-input:hover:not(:disabled) { border-color:#a5d6a7; }
#sales-master-root .rr-input:focus { background:#fff; border-color:#43a047; box-shadow:0 0 0 3px rgba(67,160,71,.12); }
#sales-master-root .rr-input:disabled { color:#7f8d82; cursor:not-allowed; background:#eef4ef; border-color:#d7e4d9; }
#sales-master-root .rr-select { cursor:pointer; }
#sales-master-root .rr-grid2,#sales-master-root .rr-grid3,#sales-master-root .rr-grid4 { display:grid; gap:12px; margin-bottom:14px; }
#sales-master-root .rr-grid2 { grid-template-columns:repeat(2,minmax(0,1fr)); }
#sales-master-root .rr-grid3 { grid-template-columns:repeat(3,minmax(0,1fr)); }
#sales-master-root .rr-grid4 { grid-template-columns:minmax(180px,1.15fr) minmax(220px,1.35fr) minmax(145px,.8fr) minmax(145px,.8fr); }
#sales-master-root .rr-qrow { display:flex; flex-wrap:wrap; gap:7px; margin:3px 0 18px; }
#sales-master-root .rr-qbtn { min-height:30px; padding:0 13px; color:#14501f; font-family:inherit; font-size:10.5px; font-weight:800; cursor:pointer; background:#fff; border:1.5px solid #dce9de; border-radius:999px; transition:color .15s,background .15s,border-color .15s,transform .15s,box-shadow .15s; }
#sales-master-root .rr-qbtn:hover { color:#0f3d1e; background:#e8f5e9; border-color:#66bb6a; transform:translateY(-1px); }
#sales-master-root .rr-qbtn-on { color:#fff; background:linear-gradient(135deg,#2e7d32,#1b5e20); border-color:#1b5e20; box-shadow:0 3px 10px rgba(27,94,32,.3); }
#sales-master-root .rr-ss { position:relative; min-width:0; user-select:none; }
#sales-master-root .rr-ss-display { display:flex; align-items:center; justify-content:space-between; width:100%; height:36px; padding:0 10px; color:#152418; font-family:inherit; font-size:11.5px; cursor:pointer; background:#fff; border:1.5px solid #dce9de; border-radius:8px; transition:border-color .15s,box-shadow .15s,background .15s; }
#sales-master-root .rr-ss-display:hover { border-color:#a5d6a7; }
#sales-master-root .rr-ss-open .rr-ss-display { background:#fff; border-color:#43a047; box-shadow:0 0 0 3px rgba(67,160,71,.12); }
#sales-master-root .rr-ss-val { min-width:0; overflow:hidden; color:#152418; text-overflow:ellipsis; white-space:nowrap; }
#sales-master-root .rr-ss-arrow { flex:0 0 auto; margin-left:8px; color:#2e7d32; font-size:9px; }
#sales-master-root .rr-ss-drop { position:absolute; z-index:9999; top:39px; right:0; left:0; display:none; overflow:hidden; background:#fff; border:1.5px solid #43a047; border-radius:9px; box-shadow:0 10px 28px rgba(15,61,30,.18); }
#sales-master-root .rr-ss-search { width:100%; height:34px; padding:0 10px; color:#152418; font-family:inherit; font-size:11px; background:#f3faf4; border:0; border-bottom:1px solid #dce9de; outline:none; }
#sales-master-root .rr-ss-search::placeholder { color:#87968b; }
#sales-master-root .rr-ss-list { max-height:210px; overflow-y:auto; }
#sales-master-root .rr-ss-opt { padding:7px 10px; overflow:hidden; color:#152418; font-size:11px; cursor:pointer; text-overflow:ellipsis; white-space:nowrap; }
#sales-master-root .rr-ss-opt:hover { color:#14501f; background:#e8f5e9; }
#sales-master-root .rr-ss-sel,#sales-master-root .rr-ss-sel:hover { color:#fff !important; font-weight:800; background:linear-gradient(135deg,#2e7d32,#1b5e20); }
#sales-master-root .rr-outstanding-panel { display:grid; grid-template-columns:minmax(260px,1fr) minmax(400px,1.35fr); gap:18px; align-items:center; margin-top:2px; padding:14px; background:linear-gradient(135deg,#f2fbf3,#e8f5e9); border:1px solid #b9dfbe; border-radius:12px; box-shadow:0 1px 2px rgba(15,61,30,.05); }
#sales-master-root .rr-section-title { color:#0f3d1e; font-size:12.5px; font-weight:800; }
#sales-master-root .rr-section-help { margin-top:4px; color:#52665a; font-size:10.5px; line-height:1.5; }
#sales-master-root .rr-section-help b { color:#14501f; }
#sales-master-root .rr-outstanding-fields { display:grid; grid-template-columns:minmax(190px,1fr) minmax(190px,1fr); gap:10px; }
#sales-master-root .rr-apply-row { display:flex; align-items:center; justify-content:flex-end; gap:14px; margin-top:14px; padding:14px 0 2px; border-top:1px dashed #cfe1d2; }
#sales-master-root .rr-apply-note { margin-right:auto; color:#5f6f63; font-size:10.5px; }
#sales-master-root .rr-btn { height:36px; padding:0 17px; font-family:inherit; font-size:11px; font-weight:800; cursor:pointer; border-radius:9px; transition:background .15s,border-color .15s,transform .15s,box-shadow .15s,opacity .15s; }
#sales-master-root .rr-btn:hover:not(:disabled) { transform:translateY(-1px); }
#sales-master-root .rr-btn:disabled { opacity:.5; cursor:not-allowed; transform:none; }
#sales-master-root .rr-btn-apply { min-width:130px; color:#fff; background:linear-gradient(135deg,#2e7d32,#1b5e20); border:1.5px solid #1b5e20; box-shadow:0 3px 10px rgba(27,94,32,.28); }
#sales-master-root .rr-btn-apply:hover:not(:disabled) { background:linear-gradient(135deg,#388e3c,#14501f); box-shadow:0 5px 14px rgba(27,94,32,.34); }
#sales-master-root .rr-footer { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:14px 18px; background:#fff; border-top:1px solid #dce9de; }
#sales-master-root .rr-colcount { max-width:760px; color:#5f6f63; font-size:10.5px; line-height:1.5; }
#sales-master-root .rr-colcount b { color:#14501f; }
#sales-master-root .rr-export-group { display:flex; flex:0 0 auto; align-items:center; gap:8px; padding:8px 10px 8px 16px; background:#fafcfa; border:1px solid #dce9de; border-radius:11px; }
#sales-master-root .rr-export-label { margin-right:2px; color:#5f6f63; font-size:9.5px; font-weight:800; letter-spacing:.8px; text-transform:uppercase; }
#sales-master-root .rr-fmtrow { display:flex; gap:6px; }
#sales-master-root .rr-fchip { height:30px; padding:0 12px; color:#14501f; font-family:inherit; font-size:10px; font-weight:800; cursor:pointer; background:#fff; border:1.5px solid #a5d6a7; border-radius:999px; transition:color .15s,background .15s,border-color .15s,box-shadow .15s; }
#sales-master-root .rr-fchip:hover { background:#e8f5e9; border-color:#66bb6a; }
#sales-master-root .rr-fchip-on { color:#fff; background:linear-gradient(135deg,#43a047,#1b5e20); border-color:#1b5e20; box-shadow:0 2px 7px rgba(27,94,32,.24); }
#sales-master-root .rr-btn-gold { min-width:170px; color:#fff; background:linear-gradient(135deg,#2e7d32,#1b5e20); border:1.5px solid #1b5e20; box-shadow:0 3px 10px rgba(27,94,32,.28); }
#sales-master-root .rr-btn-gold:hover:not(:disabled) { background:linear-gradient(135deg,#388e3c,#14501f); box-shadow:0 5px 14px rgba(27,94,32,.34); }
#sales-master-root .rr-msg { display:none; padding:10px 18px; color:#14501f; font-size:11px; font-weight:600; background:#f3faf4; border-top:1px solid #dce9de; }
#sales-master-root .rr-tbl-wrap { width:100%; overflow-x:auto; background:#fff; border-radius:0 0 11px 11px; }
#sales-master-root .rr-table { width:100%; min-width:1120px; border-collapse:collapse; font-size:11px; }
#sales-master-root .rr-table thead tr { color:#fff; background:linear-gradient(135deg,#0f3d1e,#1b5e20); }
#sales-master-root .rr-table thead th { padding:9px; color:#fff; font-size:10px; font-weight:800; letter-spacing:.45px; text-align:left; text-transform:uppercase; white-space:nowrap; border-bottom:2px solid #43a047; }
#sales-master-root .rr-table tbody td { padding:8px 9px; color:#152418; white-space:nowrap; border-bottom:1px solid #eef4ef; }
#sales-master-root .rr-row-even { background:#f8fcf8; }
#sales-master-root .rr-row-odd { background:#fff; }
#sales-master-root .rr-table tbody tr:hover td { background:#f3faf4; }
#sales-master-root .rr-num { text-align:right !important; font-variant-numeric:tabular-nums; }
#sales-master-root .rr-table tfoot tr { color:#14501f; font-weight:800; background:linear-gradient(135deg,#e8f5e9,#f3faf4); border-top:2px solid #a5d6a7; }
#sales-master-root .rr-table tfoot td { padding:9px; font-size:11px; white-space:nowrap; }
#sales-master-root .rr-nodata { padding:30px !important; color:#5f6f63 !important; font-style:italic; text-align:center; }
#sales-master-root .rr-pgbar { display:flex; flex-wrap:wrap; align-items:center; gap:5px; padding:11px 13px; background:#fafcfa; border-top:1px solid #dce9de; border-radius:0 0 11px 11px; }
#sales-master-root .rr-pgbtn { min-width:32px; height:29px; padding:0 10px; color:#14501f; font-family:inherit; font-size:10.5px; font-weight:800; cursor:pointer; background:#fff; border:1.5px solid #cfe1d2; border-radius:7px; transition:color .15s,background .15s,border-color .15s; }
#sales-master-root .rr-pgbtn:hover:not(:disabled) { color:#fff; background:#2e7d32; border-color:#2e7d32; }
#sales-master-root .rr-pgbtn:disabled { opacity:.35; cursor:not-allowed; }
#sales-master-root .rr-pgnum-on { color:#fff; background:linear-gradient(135deg,#2e7d32,#1b5e20); border-color:#1b5e20; }
#sales-master-root .rr-pgdots { padding:0 2px; color:#87968b; font-size:12px; }
#sales-master-root .rr-pginfo { margin-left:7px; color:#5f6f63; font-size:10.5px; }
#sales-master-root .rr-pginfo b { color:#14501f; }
#sales-master-root .rr-ss-list::-webkit-scrollbar,#sales-master-root .rr-tbl-wrap::-webkit-scrollbar { width:9px; height:9px; }
#sales-master-root .rr-ss-list::-webkit-scrollbar-track,#sales-master-root .rr-tbl-wrap::-webkit-scrollbar-track { background:#eef4ef; }
#sales-master-root .rr-ss-list::-webkit-scrollbar-thumb,#sales-master-root .rr-tbl-wrap::-webkit-scrollbar-thumb { background:#a5d6a7; border-radius:999px; }
#sales-master-root .rr-ss-list::-webkit-scrollbar-thumb:hover,#sales-master-root .rr-tbl-wrap::-webkit-scrollbar-thumb:hover { background:#66bb6a; }
@media (max-width:1100px){ #sales-master-root .rr-grid4{grid-template-columns:repeat(2,minmax(0,1fr));} #sales-master-root .rr-outstanding-panel{grid-template-columns:1fr;} }
@media (max-width:820px){ #sales-master-root .rr-grid3{grid-template-columns:1fr;} #sales-master-root .rr-footer{align-items:flex-start;flex-direction:column;} #sales-master-root .rr-export-group{width:100%;padding:10px;border-left:1px solid #dce9de;} }
@media (max-width:620px){ #sales-master-root .rr-body{padding:14px;} #sales-master-root .rr-grid2,#sales-master-root .rr-grid4,#sales-master-root .rr-outstanding-fields{grid-template-columns:1fr;} #sales-master-root .rr-apply-row{align-items:stretch;flex-direction:column;} #sales-master-root .rr-apply-note{margin-right:0;} #sales-master-root .rr-btn-apply{width:100%;} #sales-master-root .rr-export-group{align-items:stretch;flex-wrap:wrap;} #sales-master-root .rr-export-label{width:100%;} #sales-master-root .rr-btn-gold{flex:1 1 100%;width:100%;} }

/* ============================================================
   SALES PERSON — REFERRING FIRST, INCENTIVE BELOW
   ============================================================ */
#sales-master-root .rr-sales-person-td {
  min-width: 170px;
  white-space: normal;
}

#sales-master-root .rr-sales-person-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 150px;
  line-height: 1.25;
}

#sales-master-root .rr-sales-person-primary {
  color: #152418;
  font-size: 10.8px;
  font-weight: 800;
  white-space: normal;
}

#sales-master-root .rr-sales-person-secondary {
  padding-top: 3px;
  color: #35633d;
  font-size: 10px;
  font-weight: 700;
  white-space: normal;
  border-top: 1px dashed #cfe1d2;
}

#sales-master-root .rr-table {
  min-width: 1360px;
}


/* Compact two-row filter panel. */
#sales-master-root .rr-filter-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:12px;align-items:end;}
#sales-master-root .rr-filter-grid>div{min-width:0;}
#sales-master-root .rr-filter-second{margin-top:14px;padding-top:14px;border-top:1px solid #dce9de;}
#sales-master-root .rr-customer-field{grid-column:span 2;}
#sales-master-root .rr-filter-grid .rr-lbl{min-height:23px;letter-spacing:.45px;}
#sales-master-root .rr-filter-grid .rr-input{min-width:0;}
#sales-master-root .rr-filter-actions{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:14px 0 8px;padding-top:12px;border-top:1px dashed #cfe1d2;}
#sales-master-root .rr-filter-actions .rr-qrow{margin:0;}
#sales-master-root .rr-filter-grid .rr-ss-drop{min-width:240px;left:auto;right:0;}
@media(max-width:1000px){#sales-master-root .rr-filter-grid{grid-template-columns:repeat(3,minmax(0,1fr));}#sales-master-root .rr-customer-field{grid-column:span 1;}}
@media(max-width:620px){#sales-master-root .rr-filter-grid{grid-template-columns:repeat(2,minmax(0,1fr));}#sales-master-root .rr-filter-actions{align-items:stretch;flex-direction:column;}#sales-master-root .rr-filter-grid .rr-ss-drop{min-width:190px;}}

#sales-master-root .rr-customer-compact{grid-column:span 1;}
#sales-master-root .rr-table tbody td:nth-child(7),#sales-master-root .rr-table tbody td:nth-child(8),#sales-master-root .rr-table tbody td:nth-child(9){white-space:normal;min-width:150px;max-width:260px;overflow-wrap:anywhere;}

/* Compact filters: two field rows and one action row on desktop. */
#sales-master-root .rr-body{padding:10px 14px;}
#sales-master-root .rr-filter-grid{gap:8px;}
#sales-master-root .rr-filter-grid .rr-lbl{min-height:0;margin:0 0 3px;line-height:1.2;letter-spacing:.25px;}
#sales-master-root .rr-filter-second{margin-top:8px;padding-top:0;border-top:0;}
#sales-master-root .rr-input,#sales-master-root .rr-ss-display{height:32px;padding:0 8px;}
#sales-master-root .rr-ss-drop{top:35px;}
#sales-master-root .rr-filter-actions{gap:8px;margin:8px 0 0;padding-top:8px;}
#sales-master-root .rr-action-buttons{display:flex;align-items:center;gap:8px;flex-shrink:0;}
#sales-master-root .rr-export-group{padding:0;border:0;background:transparent;gap:6px;}
#sales-master-root .rr-export-label{display:none;}
#sales-master-root .rr-btn{height:32px;padding:0 12px;}
#sales-master-root .rr-btn-apply{min-width:105px;}
#sales-master-root .rr-btn-gold{min-width:145px;}
#sales-master-root .rr-qrow{gap:5px;}
#sales-master-root .rr-qbtn{padding:0 10px;min-height:28px;}
#sales-master-root .rr-msg{padding:7px 14px;}
@media(max-width:1100px){#sales-master-root .rr-filter-actions{flex-wrap:wrap;}}
@media(max-width:620px){#sales-master-root .rr-action-buttons{flex-wrap:wrap;}#sales-master-root .rr-export-group{width:100%;flex-wrap:nowrap;}#sales-master-root .rr-btn-gold{flex:1;min-width:0;}#sales-master-root .rr-export-group .rr-btn{width:auto;} }


</style>
