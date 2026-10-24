<script setup>
import ReportSearchSelect from '../components/employee-sale/ReportSearchSelect.vue';
import { useEmployeeSaleMaster } from '../composables/useEmployeeSaleMaster';
import '../styles/employee-sale-master.css';
const {from,to,branch,booking,employee,employeeId,mode,paidFrom,paidTo,outFrom,outTo,branchRestricted,permittedBranches,branchOptions,bookingOptions,modeOptions,employees,employeeLoading,employeeError,modeError,loadModes,searchEmployees,activeTab,quick,loading,error,notice,generatedAt,amountErrors,validateAmounts,money,compact,dateText,preset,generate,reset,employeeSearch,employeeModeSearch,employeeRows,branchRows,topEmployees,bookings,transactions,overviewTiles,branchTiles,topBooking,exportAll,exportEmployees}=useEmployeeSaleMaster();
</script>

<template>

<div class="ref-wrap">

  <div class="ref-header">
    <div class="ref-header-main">
      <div class="ref-header-kicker">Sales &amp; Collection Analytics</div>
      <div class="h1">
        Employee-wise <span class="ref-title-dot">•</span>
        Branch-wise <span class="ref-title-dot">•</span>
        Mode of Payment-wise Report Dashboard
      </div>
      <div class="sub">
        LIFE SLIMMING AND COSMETIC PVT. LTD.
        <span class="ref-sub-sep">|</span>
        All Branches
        <span class="ref-sub-sep">|</span>
        <span id="ref-ts">{{ generatedAt }}</span>
      </div>
    </div>

    <div class="right">
      <span class="ref-source-label">Source</span>
      REFERRAL REPORT – FIXED
    </div>
  </div>

  <div class="ref-gold-bar"></div>

  <div class="ref-nav">
    <button type="button" class="ref-mnav" data-tab="0" :class="{on:activeTab===0}" @click="activeTab=0">📊 Overview</button>
    <button type="button" class="ref-mnav" data-tab="1" :class="{on:activeTab===1}" @click="activeTab=1">👤 Employee Wise</button>
    <button type="button" class="ref-mnav" data-tab="2" :class="{on:activeTab===2}" @click="activeTab=2">🏢 Branch Wise</button>
    <button type="button" class="ref-mnav" data-tab="3" :class="{on:activeTab===3}" @click="activeTab=3">📋 Transaction Detail</button>
  </div>

  <div class="ref-content">


    <div class="ref-fbar">

      <div class="ref-fbar-title-row">
        <div>
          <div class="ref-filter-title">Report Filters</div>
          <div class="ref-filter-help">
            Select the required filters, then generate the dashboard.
          </div>
        </div>
      </div>

      <div class="ref-fbar-row ref-primary-filters">

        <div class="ref-field">
          <label class="ref-lbl">From Date</label>
          <input type="date" class="ref-input" id="ref-f-from" v-model="from" @change="quick=''">
        </div>

        <div class="ref-field">
          <label class="ref-lbl">To Date</label>
          <input type="date" class="ref-input" id="ref-f-to" v-model="to" @change="quick=''">
        </div>

        <div class="ref-field">
          <label class="ref-lbl">Branch</label>
          <ReportSearchSelect id="ref-f-branch" v-model="branch" :options="branchOptions" placeholder="All Branches" :disabled="branchRestricted &amp;&amp; permittedBranches.length===1" />
        </div>

        <div class="ref-field">
          <label class="ref-lbl">Booking Type</label>
          <ReportSearchSelect id="ref-f-booking" v-model="booking" :options="bookingOptions" placeholder="All Booking Types" />
        </div>

        <div class="ref-field">
          <label class="ref-lbl">Employee Name</label>
          <ReportSearchSelect id="ref-f-emp" v-model="employee" :options="employees" placeholder="Search employee name..." remote :busy="employeeLoading" :error="employeeError" @query="searchEmployees" @choose="employeeId=$event?.value || ''" />
        </div>

        <div class="ref-field">
          <label class="ref-lbl">Mode of Payment</label>
          <ReportSearchSelect id="ref-f-mop" v-model="mode" :options="modeOptions" placeholder="All Modes of Payment" />
        </div>
      </div>

      <div class="ref-fbar-row ref-secondary-filters">

        <div class="ref-field ref-amount-field">
          <label class="ref-lbl">Paid From (₹)</label>
          <input type="text" class="ref-input" id="ref-f-paid-from" v-model="paidFrom" inputmode="numeric" @input="paidFrom=String(paidFrom).replace(/\D/g,'').replace(/^0+(?=\d)/,'');validateAmounts()" :class="{'ref-invalid':amountErrors.paid}" placeholder="Min">
        </div>

        <div class="ref-field ref-amount-field">
          <label class="ref-lbl">Paid To (₹)</label>
          <input type="text" class="ref-input" id="ref-f-paid-to" v-model="paidTo" inputmode="numeric" @input="paidTo=String(paidTo).replace(/\D/g,'').replace(/^0+(?=\d)/,'');validateAmounts()" :class="{'ref-invalid':amountErrors.paid}" placeholder="Max">
        </div>

        <div class="ref-field ref-amount-field">
          <label class="ref-lbl">Outstanding From (₹)</label>
          <input type="text" class="ref-input" id="ref-f-out-from" v-model="outFrom" inputmode="numeric" @input="outFrom=String(outFrom).replace(/\D/g,'').replace(/^0+(?=\d)/,'');validateAmounts()" :class="{'ref-invalid':amountErrors.out}" placeholder="Min">
        </div>

        <div class="ref-field ref-amount-field">
          <label class="ref-lbl">Outstanding To (₹)</label>
          <input type="text" class="ref-input" id="ref-f-out-to" v-model="outTo" inputmode="numeric" @input="outTo=String(outTo).replace(/\D/g,'').replace(/^0+(?=\d)/,'');validateAmounts()" :class="{'ref-invalid':amountErrors.out}" placeholder="Max">
        </div>

        <div class="ref-reset-slot"><button type="button" id="ref-reset-filters-btn" class="ref-reset-btn" @click="reset">↺ Reset Filters</button></div>
        <div class="ref-date-shortcuts">
          <button type="button" class="ref-qbtn" data-range="today" :class="{on:quick==='today'}" @click="preset('today')">Today</button>
          <button type="button" class="ref-qbtn" data-range="yesterday" :class="{on:quick==='yesterday'}" @click="preset('yesterday')">Yesterday</button>
          <button type="button" class="ref-qbtn" data-range="month" :class="{on:quick==='month'}" @click="preset('month')">This Month</button>
          <button type="button" class="ref-qbtn" data-range="lastmonth" :class="{on:quick==='lastmonth'}" @click="preset('lastmonth')">Last Month</button>
          <button type="button" class="ref-qbtn" data-range="year" :class="{on:quick==='year'}" @click="preset('year')">This Financial Year</button>
        </div>

        <div class="ref-action-group">
          <button type="button" class="ref-apbtn" id="ref-generate-btn" :disabled="loading" @click="generate">
            {{ loading ? 'Loading…' : '▶ Generate Report' }}
          </button><button type="button" class="ref-export-btn" id="ref-global-excel-btn" :disabled="loading" @click="exportAll">⬇ Export All (Excel)</button>
        </div>
      </div>
      <div v-if="amountErrors.paid || amountErrors.out" class="ref-num-error">{{ amountErrors.paid || amountErrors.out }}</div>
    </div>

    <div id="ref-status"><p v-if="error" role="alert" class="ref-err">{{ error }} <button @click="generate">Retry</button></p><p v-else-if="loading" role="status" class="ref-status">⏳ Fetching report…</p><p v-else role="status" class="ref-status">{{ notice }}</p><p v-if="modeError" role="alert">{{ modeError }} <button @click="loadModes">Retry payment modes</button></p></div>


    <div class="ref-mode" id="ref-mode-0" :class="{on:activeTab===0}" v-if="activeTab===0">
      <div class="ref-tiles" id="ref-ov-tiles"><div v-for="tile in overviewTiles" :key="tile[0]" class="ref-tile" :class="tile[2]"><div class="tl">{{ tile[0] }}</div><div class="tv" :class="{'ref-amount-with-compact':tile[3]}">{{ tile[3]?money(tile[1]):Number(tile[1]).toLocaleString() }}<span v-if="tile[3] &amp;&amp; compact(tile[1])" class="ref-compact-amount">({{ compact(tile[1]) }})</span></div></div></div>

      <div class="ref-two-col">
        <div class="ref-card">
          <div class="ref-card-hdr">
            <span>Top Employees — Paid (ex-GST)</span>
            <span class="badge">Ranked</span>
          </div>
          <div class="ref-card-body" id="ref-ov-emp-bars"><div v-for="row in topEmployees" :key="row.name" class="ref-bar-row"><div class="ref-bar-lbl" :title="row.name">{{ row.name }}</div><div class="ref-bar-track"><div class="ref-bar-fill" :style="{width:Math.round(row.exTax/(topEmployees[0]?.exTax || 1)*100)+'%',background:'linear-gradient(90deg,#43A047,#1B5E20)'}"></div></div><div class="ref-bar-val">{{ money(row.exTax) }}</div></div><div v-if="!topEmployees.length" class="ref-loading">No data</div></div>
        </div>

        <div class="ref-card">
          <div class="ref-card-hdr">
            <span>Top Branches — Paid (ex-GST)</span>
            <span class="badge">Ranked</span>
          </div>
          <div class="ref-card-body" id="ref-ov-branch-bars"><div v-for="row in branchRows" :key="row.name" class="ref-bar-row"><div class="ref-bar-lbl" :title="row.name">{{ row.name }}</div><div class="ref-bar-track"><div class="ref-bar-fill" :style="{width:Math.round(row.exTax/(branchRows[0]?.exTax || 1)*100)+'%',background:'linear-gradient(90deg,#81C784,#2E7D32)'}"></div></div><div class="ref-bar-val">{{ money(row.exTax) }}</div></div><div v-if="!branchRows.length" class="ref-loading">No data</div></div>
        </div>
      </div>

      <div class="ref-card">
        <div class="ref-card-hdr">
          <span>Booking Type Breakdown</span>
          <span class="sub">Invoices &amp; Paid Amount by Type</span>
        </div>

        <div class="ref-tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Booking Type</th>
                <th>Invoice Count</th>
                <th class="rnum">Paid (ex-GST)</th>
                <th class="rnum">GST Amount</th>
                <th class="rnum">Paid (w/GST)</th>
                <th class="rnum">Outstanding</th>
              </tr>
            </thead>
            <tbody id="ref-ov-booking-body"><tr v-for="row in bookings" :key="row.name"><td><span class="rpill rp-go">{{ row.name }}</span></td><td class="rnum">{{ row.invoices.size }}</td><td class="rnum" style="color:#1B5E20;font-weight:800">{{ money(row.ex) }}</td><td class="rnum">{{ money(row.tax) }}</td><td class="rnum" style="color:#5F6F63">{{ money(row.paid) }}</td><td class="rnum" :style="{color:row.out>0?'#C62828':'#5F6F63'}">{{ money(row.out) }}</td></tr><tr v-if="!bookings.length"><td colspan="6" class="ref-loading">No data</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>


    <div class="ref-mode" id="ref-mode-1" :class="{on:activeTab===1}" v-if="activeTab===1">
      <div class="ref-card">
        <div class="ref-card-hdr">
          <span>Employee Wise Summary</span>
          <span class="sub">Ranked by Paid (ex-GST)</span>
        </div>

        <div class="ref-tbl-wrap">
          <div id="ref-emp-ctrl-row" class="ref-emp-controls"><input id="ref-emp-srch" v-model="employeeSearch" placeholder="🔍 Search employee name..."><input id="ref-emp-mop-srch" v-model="employeeModeSearch" placeholder="🔍 Search mode of payment..."><button id="ref-emp-xlsx" class="ref-export-btn" @click="exportEmployees">⬇ Export Employee Excel</button></div><table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Employee</th>
                <th>Branch</th>
                <th>Emp ID</th>
                <th class="rnum">Invoices</th>
                <th class="rnum">Paid (ex-GST)</th>
                <th class="rnum">GST Amt</th>
                <th class="rnum">Paid (w/GST)</th>
                <th class="rnum">Grand Total</th>
                <th class="rnum">Outstanding</th>
                <th>Top Booking</th>
                <th>Modes</th>
              </tr>
            </thead>
            <tbody id="ref-emp-body"><tr v-for="(row,index) in employeeRows" :key="row.empId+'|'+row.name"><td><span class="rrank" :class="index<3?'rrank-'+(index+1):'rrank-n'">{{ index+1 }}</span></td><td><strong>{{ row.name }}</strong></td><td><span class="rpill rp-n">{{ row.branch }}</span></td><td style="font-size:9px;color:#6B7C70">{{ row.empId }}</td><td class="rnum">{{ row.cnt }}</td><td class="rnum" style="color:#1B5E20;font-weight:800">{{ money(row.exTax) }}</td><td class="rnum" style="color:#5F6F63">{{ money(row.tax) }}</td><td class="rnum" style="color:#5F6F63">{{ money(row.paid) }}</td><td class="rnum">{{ money(row.gt) }}</td><td class="rnum" :style="{color:row.out>10000?'#C62828':row.out>0?'#E65100':'#5F6F63'}">{{ money(row.out) }}</td><td><span class="rpill rp-go">{{ topBooking(row) }}</span></td><td style="font-size:9px;max-width:140px;overflow:hidden;text-overflow:ellipsis">{{ row.modes.join(', ') }}</td></tr><tr v-if="!employeeRows.length"><td colspan="12" class="ref-loading">No data</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>


    <div class="ref-mode" id="ref-mode-2" :class="{on:activeTab===2}" v-if="activeTab===2">
      <div class="ref-tiles" id="ref-br-tiles"><div v-for="tile in branchTiles" :key="tile[0]" class="ref-tile" :class="tile[2]"><div class="tl">{{ tile[0] }}</div><div class="tv" :class="{'ref-amount-with-compact':tile[3]}">{{ tile[3]?money(tile[1]):Number(tile[1]).toLocaleString() }}<span v-if="tile[3] &amp;&amp; compact(tile[1])" class="ref-compact-amount">({{ compact(tile[1]) }})</span></div></div></div>

      <div class="ref-card">
        <div class="ref-card-hdr">
          <span>Branch Wise Summary</span>
          <span class="sub">Ranked by Paid (ex-GST)</span>
        </div>

        <div class="ref-tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Branch</th>
                <th class="rnum">Invoices</th>
                <th class="rnum">Paid (ex-GST)</th>
                <th class="rnum">GST Amt</th>
                <th class="rnum">Paid (w/GST)</th>
                <th class="rnum">Grand Total</th>
                <th class="rnum">Outstanding</th>
                <th class="rnum">Employees</th>
                <th>Top Booking</th>
              </tr>
            </thead>
            <tbody id="ref-br-body"><tr v-for="(row,index) in branchRows" :key="row.name"><td><span class="rrank" :class="index<3?'rrank-'+(index+1):'rrank-n'">{{ index+1 }}</span></td><td><strong>{{ row.name }}</strong></td><td class="rnum">{{ row.cnt }}</td><td class="rnum" style="color:#1B5E20;font-weight:800">{{ money(row.exTax) }}</td><td class="rnum" style="color:#5F6F63">{{ money(row.tax) }}</td><td class="rnum" style="color:#5F6F63">{{ money(row.paid) }}</td><td class="rnum">{{ money(row.gt) }}</td><td class="rnum" :style="{color:row.out>50000?'#C62828':row.out>0?'#E65100':'#5F6F63'}">{{ money(row.out) }}</td><td class="rnum">{{ row.emps.length }}</td><td><span class="rpill rp-go">{{ topBooking(row) }}</span></td></tr><tr v-if="!branchRows.length"><td colspan="10" class="ref-loading">No data</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>


    <div class="ref-mode" id="ref-mode-3" :class="{on:activeTab===3}" v-if="activeTab===3">
      <div class="ref-card">
        <div class="ref-card-hdr">
          <span>
            Transaction Detail
            <span class="badge">Full Detail</span>
          </span>
          <span class="sub" id="ref-txn-count">{{ transactions.length.toLocaleString() }} invoices</span>
        </div>

        <div class="ref-tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Date</th>
                <th>Branch</th>
                <th>Customer</th>
                <th>Booking Type</th>
                <th>Referring Employee</th>
                <th>Ref Emp ID</th>
                <th class="rnum">Ref Share (ex-GST)</th>
                <th>Incentive Employee</th>
                <th>Inc Emp ID</th>
                <th class="rnum">Inc Share (ex-GST)</th>
                <th>Mode of Payment</th>
                <th class="rnum">Paid (ex-GST)</th>
                <th class="rnum">GST</th>
                <th class="rnum">Paid (w/GST)</th>
                <th class="rnum">Grand Total</th>
                <th class="rnum">Outstanding</th>
              </tr>
            </thead>
            <tbody id="ref-txn-body"><tr v-for="row in transactions" :key="row.branch+'|'+row.invoice"><td style="font-size:9.5px;color:#14501F;font-weight:700">{{ row.invoice }}</td><td style="font-size:9.5px">{{ dateText(row.invoice_date) }}</td><td><span class="rpill rp-n">{{ row.branch }}</span></td><td>{{ row.customer }}</td><td><span class="rpill rp-go">{{ row.booking_type }}</span></td><td><strong>{{ row.referring_employee || '—' }}</strong></td><td style="font-size:9px;color:#6B7C70">{{ row.referring_employee_id || row.referring_practitioner_id }}</td><td class="rnum" style="color:#1565C0;font-weight:800">{{ money(row.referring_employee_share) }}</td><td><strong>{{ row.incentive_employee || '—' }}</strong></td><td style="font-size:9px;color:#6B7C70">{{ row.incentive_employee_id }}</td><td class="rnum" style="color:#E65100;font-weight:800">{{ money(row.incentive_employee_share) }}</td><td style="font-size:9.5px">{{ row.mode_of_payment }}</td><td class="rnum" style="color:#1B5E20;font-weight:800">{{ money(row.paid_amount_without_gst) }}</td><td class="rnum" style="color:#5F6F63">{{ money(row.gst_amount) }}</td><td class="rnum" style="color:#5F6F63">{{ money(row.paid_amount) }}</td><td class="rnum">{{ money(row.grand_total) }}</td><td class="rnum" :style="{color:row.outstanding_amount>0?'#C62828':'#5F6F63'}">{{ money(row.outstanding_amount) }}</td></tr><tr v-if="!transactions.length"><td colspan="17" class="ref-loading">No data</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

  </div>
</div>

</template>
