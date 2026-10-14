<script setup>
import { useWeightLoss } from '../composables/useWeightLoss';
import { kg, difference, differenceClass, sessionDifference, excelTable, monthLabel, previousMonth } from '../lib/weight-loss';
import { indiaDate, dateText } from '../lib/unjoined';
import ReportPagination from '../components/ReportPagination.vue';
import '../styles/weight-loss-parity.css';
const { month, branch, weightFilter, search, selectedClient, branches, clientOptions, searchVisible, searchError, loading, openLoading, error, openError, notice, page, openPage, detail, openModal, months, visibleRows, filteredOpenRows, pageCount, openPageCount, pagedRows, openPaged, totalLoss, avgLoss, sessionCount, refresh, refreshMonthly, searchChanged, selectClient, clearClient } = useWeightLoss();
function download(headers, rows, filename) {
  const url = URL.createObjectURL(new Blob([excelTable(headers, rows)], { type: 'application/vnd.ms-excel;charset=utf-8;' }));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function exportMain() {
  if (!visibleRows.value.length || loading.value) return;
  download(['Month', 'Client', 'Mobile', monthLabel(previousMonth(month.value)), monthLabel(month.value), 'Weight Difference', 'Sessions', 'Branch'], visibleRows.value.map(row => [row.month_label, row.patient, row.mobile, kg(row.previous_closing_weight), kg(row.current_closing_weight), difference(row.month_difference), row.completed_sessions + ' of ' + (row.total_sessions || '-'), row.branch]), 'Client_Weight_Loss_' + monthLabel(month.value).replace(/\s+/g, '_') + '.xls');
}
function exportOpen() {
  if (!filteredOpenRows.value.length || openLoading.value || openError.value) return;
  download(['Client Name', 'Mobile Number', 'Branch'], filteredOpenRows.value.map(row => [row.patient, row.mobile || '-', row.branch]), 'Open_Cards_' + (branch.value || 'All Branches').replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '') + '_' + indiaDate() + '.xls');
}
</script>

<template>
<div @click="searchVisible = false" @keydown.esc="detail = null; openModal = false; searchVisible = false" class="wl-dashboard">

<div class="wl-header">
<div>
<h2>Client Weight Loss Info</h2>
<p>Month-wise Slimming Progress Report</p>
</div>
<div class="wl-actions">
<button :disabled="loading || openLoading" @click="refresh" class="wl-btn secondary" id="refreshDashboard" type="button">
                Refresh
            </button>
<button :disabled="loading || !visibleRows.length" @click="exportMain" class="wl-btn primary" id="sendMailBtn" type="button">
                Export Excel
            </button>
</div>
</div>

<div class="wl-filter-panel">
<div class="wl-filters wl-filters-main">

<div class="wl-field">
<label for="monthFilter">Month</label>
<select @change="refreshMonthly" id="monthFilter" v-model="month"><option :key="item.key" :value="item.key" v-for="item in months">{{ item.label }}</option></select>
</div>

<div class="wl-field">
<label for="branchFilter">Branch</label>
<select id="branchFilter" v-model="branch"><option value="">All Branches</option><option :key="item" :value="item" v-for="item in branches">{{ item }}</option></select>
</div>

<div class="wl-field search">
<label for="clientSearch">Search Client</label>
<div class="wl-search-row">
<div class="wl-autocomplete-container">
<input @click.stop="searchVisible = true" @focus="searchVisible = true" @input="searchChanged" autocomplete="off" id="clientSearch" placeholder="Search Client" type="text" v-model="search"/>
<div class="wl-custom-dropdown" id="clientList" v-if="searchVisible"><p class="wl-dropdown-item" v-if="searchError">{{ searchError }}</p><p class="wl-dropdown-item" v-else-if="!clientOptions.length">No clients found</p><button :key="option.value" @click.stop="selectClient(option)" class="wl-dropdown-item" type="button" v-else="" v-for="option in clientOptions"><strong>{{ option.value }}</strong><br/><small>{{ option.description || option.value }}</small></button></div>
</div>
<button @click="clearClient" class="wl-btn secondary wl-clear-btn" id="clearClientSearch" type="button">
                        Clear
                    </button>
</div>
</div>

<div class="wl-field">
<label for="weightLossFilter">Weight Loss</label>
<select id="weightLossFilter" v-model="weightFilter">
<option value="">
                        All Clients
                    </option>
<option value="one_and_above">
                        Above 1 kg
                    </option>
<option value="two_and_above">
                        Above 2 kg
                    </option>
<option value="three_and_above">
                        Above 3 kg
                    </option>
<option value="gain">
                        Weight Gain
                    </option>
<option value="no_change">
                        No Change
                    </option>
</select>
</div>
</div>
</div><p class="wl-native-status" role="status" v-if="error || notice || openError">{{ error || openError || notice }}</p>

<div class="wl-kpis">

<div class="wl-card">
<span>Total Clients</span>
<h3 id="totalClients">{{ visibleRows.length.toLocaleString('en-IN') }}</h3>
<small class="wl-card-note">
                Clients in the selected month
            </small>
</div>
<div @click="openModal = true" @keydown.enter.prevent="openModal = true" @keydown.space.prevent="openModal = true" class="wl-card wl-open-cards-card" id="totalOpenCardsCard" role="button" tabindex="0" title="Click to view Open Cards">
<span>Total Open Cards</span>
<h3 id="totalOpenCards">{{ openLoading ? '...' : openError ? '-' : filteredOpenRows.length.toLocaleString('en-IN') }}</h3>
<small class="wl-card-note">
                From 01-Jan-2026 · New slimming joiners included · Completed plans excluded
                <br/>
                Click to view client list
            </small>
</div>

<div class="wl-card">
<span>Average Weight Loss</span>
<h3 id="avgLoss">{{ avgLoss.toFixed(1) + ' kg' }}</h3>
<small class="wl-card-note wl-total-loss-note">
                Total Weight Loss:
                <strong id="totalLossSummary">{{ totalLoss.toFixed(1) + ' kg' }}</strong>
</small>
</div>

<div class="wl-card">
<span>Total Sessions</span>
<h3 id="totalSessions">{{ sessionCount.toLocaleString('en-IN') }}</h3>
<small class="wl-card-note">
                Submitted slimming sessions
            </small>
</div>
</div>

<div class="wl-table-wrap">
<div class="wl-table-header">
<h3>Month-wise Client Weight Loss Report</h3>
<p class="wl-table-note">
                Select a month to view clients who took submitted
                slimming sessions in that month. Last Month Weight is
                taken from the previous month’s last submitted slimming
                session. Current Month Weight is taken from the selected
                month’s last submitted slimming session.
            </p>
</div>
<div class="wl-table-scroll">
<table class="wl-table">
<thead>
<tr>
<th>Month</th>
<th>Client</th>
<th>Last Month</th>
<th>Current Month</th>
<th>Weight Difference</th>
<th>Sessions</th>
<th>Branch</th>
</tr>
</thead>
<tbody id="weightTableBody"><tr :key="row.patient" @click="detail = row" @keydown.enter="detail = row" class="wl-clickable-row" tabindex="0" v-for="row in pagedRows"><td><b>{{ row.month_label }}</b></td><td>{{ row.patient }}</td><td>{{ kg(row.previous_closing_weight) }}<br/><small :class="{ 'wl-reference-warning': row.used_current_opening_as_reference }">{{ row.reference_source }}</small></td><td>{{ kg(row.current_closing_weight) }}</td><td :class="differenceClass(row.month_difference)">{{ difference(row.month_difference) }}</td><td>{{ row.completed_sessions }} of {{ row.total_sessions || '-' }}</td><td>{{ row.branch }}</td></tr><tr v-if="!pagedRows.length"><td class="wl-empty-row" colspan="7">{{ loading ? 'Loading month-wise weight loss data...' : 'No submitted slimming sessions found for selected month' }}</td></tr></tbody>
</table>
</div>

<div class="wl-pagination" id="mainPagination"><ReportPagination :total="pageCount" v-model="page"></ReportPagination></div>
</div>

<div @click.self="openModal = false" class="wl-modal-overlay" id="openCardsModalOverlay" v-if="openModal">
<div class="wl-modal wl-open-cards-modal">
<div class="wl-modal-header">
<div>
<h3>Open Cards Client List</h3>
<p id="openCardsModalSummary">{{ filteredOpenRows.length.toLocaleString('en-IN') + ' open cards' }}</p>
</div>
<button @click="openModal = false" aria-label="Close" class="wl-modal-close" id="openCardsModalClose" type="button">
                ×
            </button>
</div>
<div class="wl-modal-body">
<div class="wl-open-cards-toolbar">
<div class="wl-open-cards-filter-info">
                    The displayed Branch and selected Client filters
                    are applied to this list.
                </div>
<button :disabled="openLoading || !!openError || !filteredOpenRows.length" @click="exportOpen" class="wl-btn primary" id="exportOpenCardsBtn" type="button">
                    Export Excel
                </button>
</div>
<div class="wl-open-cards-table-wrap">
<table class="wl-open-cards-table">
<thead>
<tr>
<th>Client Name</th>
<th>Mobile Number</th>
<th>Branch</th>
</tr>
</thead>
<tbody id="openCardsTableBody"><tr :key="row.patient" v-for="row in openPaged"><td>{{ row.patient }}</td><td>{{ row.mobile || '-' }}</td><td>{{ row.branch }}</td></tr><tr v-if="!openPaged.length"><td class="wl-empty-row" colspan="3">{{ openError || 'No Open Cards found' }}</td></tr></tbody>
</table>
</div>
<div class="wl-pagination" id="openCardsPagination"><ReportPagination :total="openPageCount" v-model="openPage"></ReportPagination></div>
</div>
</div>
</div>

<div @click.self="detail = null" class="wl-modal-overlay" id="wlDetailsModalOverlay" v-if="detail">
<div class="wl-modal">

<div class="wl-modal-header">
<div>
<h3 id="modalClientName">{{ detail.patient + (detail.mobile ? ' — ' + detail.mobile : '') }}</h3>
<p id="modalMonthInfo">{{ detail.previous_month_label + ' vs ' + detail.month_label }}</p>
</div>
<button @click="detail = null" aria-label="Close" class="wl-modal-close" id="wlModalClose" type="button">
                    ×
                </button>
</div>

<div class="wl-modal-body">

<div class="wl-modal-section">
<h4>Overall Weight Summary</h4>
<div class="wl-summary-grid">
<div>
<span>Branch</span>
<b id="modalBranch">{{ detail.branch }}</b>
</div>
<div>
<span>First Slimming Session</span>
<b id="modalFirstSession">{{ dateText(detail.first_session_date) }}</b>
</div>
<div>
<span>Joined Weight</span>
<b id="modalJoinedWeight">{{ kg(detail.joined_weight) }}</b>
</div>
<div>
<span>Present Weight</span>
<b id="modalPresentWeight">{{ kg(detail.present_weight) }}</b>
</div>
<div>
<span>Total Change</span>
<b :class="differenceClass(detail.total_change)" id="modalTotalLoss">{{ difference(detail.total_change) }}</b>
</div>
<div>
<span>Total Sessions</span>
<b id="modalTotalSessionSummary">{{ detail.lifetime_sessions.length + ' / ' + (detail.total_sessions || '-') }}</b>
</div>
</div>
</div>

<div class="wl-modal-section">
<h4>Selected Month Comparison</h4>
<div class="wl-summary-grid">
<div>
<span>Previous Month Closing</span>
<b id="modalPrevClosing">{{ kg(detail.previous_closing_weight) + (detail.used_current_opening_as_reference ? ' (' + detail.reference_source + ')' : '') }}</b>
</div>
<div>
<span>Current Month Closing</span>
<b id="modalCurrentClosing">{{ kg(detail.current_closing_weight) }}</b>
</div>
<div>
<span>Month Difference</span>
<b :class="differenceClass(detail.month_difference)" id="modalMonthDifference">{{ difference(detail.month_difference) }}</b>
</div>
</div>
</div>

<div class="wl-modal-section">
<h4 id="previousMonthTitle">{{ detail.previous_month_label + ' Sessions' }}</h4>
<div class="wl-inner-table-wrap">
<table class="wl-inner-table">
<thead>
<tr>
<th>Date</th>
<th>Session</th>
<th>Opening Weight</th>
<th>Closing Weight</th>
<th>Difference</th>
</tr>
</thead>
<tbody id="previousMonthSessionsBody"><tr :key="row.name" v-for="row in detail.previous_sessions"><td>{{ dateText(row.start_date) }}</td><td>{{ row.name || '-' }}</td><td>{{ kg(row.before_weight) }}</td><td>{{ kg(row.after_weight) }}</td><td :class="differenceClass(sessionDifference(row))">{{ difference(sessionDifference(row)) }}</td></tr><tr v-if="!detail.previous_sessions.length"><td class="wl-empty-row" colspan="5">No sessions found</td></tr></tbody>
</table>
</div>
</div>

<div class="wl-modal-section">
<h4 id="currentMonthTitle">{{ detail.month_label + ' Sessions' }}</h4>
<div class="wl-inner-table-wrap">
<table class="wl-inner-table">
<thead>
<tr>
<th>Date</th>
<th>Session</th>
<th>Opening Weight</th>
<th>Closing Weight</th>
<th>Difference</th>
</tr>
</thead>
<tbody id="currentMonthSessionsBody"><tr :key="row.name" v-for="row in detail.current_sessions"><td>{{ dateText(row.start_date) }}</td><td>{{ row.name || '-' }}</td><td>{{ kg(row.before_weight) }}</td><td>{{ kg(row.after_weight) }}</td><td :class="differenceClass(sessionDifference(row))">{{ difference(sessionDifference(row)) }}</td></tr><tr v-if="!detail.current_sessions.length"><td class="wl-empty-row" colspan="5">No sessions found</td></tr></tbody>
</table>
</div>
</div>
</div>
</div>
</div>
</div>
</template>
