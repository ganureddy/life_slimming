import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { apiCredentials, apiUrl } from "../api/config";
import { request } from "../api/http";
import { session } from "../lib/session";
import { dateText } from "../lib/unjoined";

export function useSalesMaster() {
  const reportName = "REFERRAL REPORT \u2013 FIXED", pageSize = 20;
  const cols = [["invoice", "Invoice"], ["posting_date", "Posting Date"], ["branch", "Branch"], ["customer", "Customer"], ["booking_type", "Booking Type"], ["sales_people", "Sales Person"], ["mode_of_payment", "Mode of Payment"], ["paid_amount", "Paid w/ GST"], ["tax_amount", "GST Amt"], ["paid_amount_without_tax", "Paid w/o GST"], ["grand_total", "Grand Total"], ["outstanding_amount", "Outstanding"]];
  const presets = [["today", "Today"], ["yesterday", "Yesterday"], ["thismonth", "This Month"], ["lastmonth", "Last Month"], ["thisquarter", "This Quarter"], ["thisfy", "This Financial Year"]];
  const from = ref(""), to = ref(""), quick = ref("thismonth"), branch = ref(""), salesPerson = ref(""), bookingType = ref(""), modeOfPayment = ref(""), customer = ref(""), paidFrom = ref(""), paidTo = ref(""), outstandingOperator = ref(""), outstandingValue = ref(""), format = ref("xlsx");
  const permittedBranches = ref([]), allBranchAccess = ref(false), branchRestricted = ref(false), branchReady = ref(false), branchError = ref("");
  const rows = ref([]), filteredRows = ref([]), employees = ref([]), loading = ref(false), error = ref(""), notice = ref(""), page = ref(1), reportLoaded = ref(false);
  let controller, alive = true;
  const appliedState = ref(null), downloading = ref(false), totalSourceIndex = ref(null);
  const pageCount = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / pageSize)));
  const visibleRows = computed(() => filteredRows.value.slice((page.value - 1) * pageSize, page.value * pageSize));
  const money = (v) => "\u20B9" + Number(v || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const recordCount = computed(() => `${filteredRows.value.length.toLocaleString("en-IN")} records`);
  const canUseAll = () => session.user === "Administrator" || session.roles.includes("System Manager");
  function pad(v) {
    return String(v).padStart(2, "0");
  }
  function iso(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }
  function cycleRange(offset = 0) {
    const now = new Date();
    let month = now.getMonth() + (now.getDate() < 6 ? -1 : 0) + offset;
    const start = new Date(now.getFullYear(), month, 6);
    return { from: iso(start), to: iso(new Date(start.getFullYear(), start.getMonth() + 1, 5)) };
  }
  function dateRange(key) {
    const now = new Date(), today = iso(now);
    if (key === "today") return { from: today, to: today };
    if (key === "yesterday") {
      now.setDate(now.getDate() - 1);
      const y = iso(now);
      return { from: y, to: y };
    }
    if (key === "thismonth") return cycleRange();
    if (key === "lastmonth") return cycleRange(-1);
    if (key === "thisquarter") {
      const m = now.getMonth(), qStart = Math.floor(m / 3) * 3;
      return { from: iso(new Date(now.getFullYear(), qStart, 6)), to: today };
    }
    if (key === "thisfy") {
      const year = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
      return { from: `${year}-04-01`, to: `${year + 1}-03-31` };
    }
    return cycleRange();
  }
  function parseAmount(value) {
    if (value === null || value === void 0 || String(value).trim() === "") return null;
    const n = Number(String(value).replace(/[₹,\s]/g, ""));
    return Number.isFinite(n) ? n : null;
  }
  function round(value) {
    return Math.round((Number(value || 0) + Number.EPSILON) * 100) / 100;
  }
  function normalizeRow(row) {
    const paid = parseAmount(row.paid_amount) || 0;
    let without = parseAmount(row.paid_amount_without_gst);
    if (without === null) without = parseAmount(row.paid_amount_without_tax);
    if (without === null) without = parseAmount(row.amount_without_gst);
    let gst = parseAmount(row.gst_amount);
    if (gst === null) gst = parseAmount(row.tax_amount);
    if (without === null && paid > 0) without = paid / 1.05;
    if (gst === null && paid > 0) gst = paid - Number(without || 0);
    return { ...row, posting_date: row.invoice_date || row.posting_date || "", referring_employee: String(row.referring_employee || row.custom_referring_name || row.referring_name || "").trim(), incentive_employee: String(row.incentive_employee || row.custom_incentive_employee_name || row.incentive_employee_name || "").trim(), paid_amount: round(paid), tax_amount: round(gst), gst_amount: round(gst), paid_amount_without_tax: round(without), paid_amount_without_gst: round(without) };
  }
  function rowKey(row) {
    if (row.invoice) return `invoice|${String(row.branch || "").trim()}|${String(row.invoice).trim()}`;
    return JSON.stringify([row.branch, row.posting_date, row.customer, row.booking_type, row.referring_employee, row.incentive_employee, row.mode_of_payment, row.paid_amount, row.tax_amount, row.paid_amount_without_tax, row.grand_total, row.outstanding_amount]);
  }
  async function getBranches() {
    branchReady.value = false;
    branchError.value = "";
    try {
      const response = await request("frappe.client.get_list", { args: { doctype: "Branch", fields: ["name"], limit_page_length: 200, order_by: "name asc" }, csrfToken: session.csrf_token });
      const names = (response.message || []).map((row) => String(row.name || "").trim()).filter(Boolean);
      permittedBranches.value = [...new Set(names)];
      allBranchAccess.value = canUseAll();
      branchRestricted.value = !allBranchAccess.value;
      if (!allBranchAccess.value && !names.length) throw new Error("No permitted Branch was returned for this login.");
      if (!allBranchAccess.value && names.length === 1) branch.value = names[0];
      branchReady.value = true;
    } catch (e) {
      branchError.value = e.message;
      branchReady.value = false;
    }
  }
  async function runOneBranch(state, requestedBranch, signal) {
    const filters = { from_date: state.fromDate, to_date: state.toDate, branch: requestedBranch || "" };
    const params = new URLSearchParams({ report_name: reportName, filters: JSON.stringify(filters), ignore_prepared_report: "1", are_default_filters: "false" });
    let response;
    try {
      response = await fetch(apiUrl("/api/method/frappe.desk.query_report.run?" + params.toString()), { method: "GET", credentials: apiCredentials(), signal, headers: { Accept: "application/json" } });
    } catch (e) {
      if (e.name === "AbortError") throw e;
      throw new Error("Could not reach the report server. Check your connection and retry.");
    }
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.exc_type) {
      let message = body.message || body.exception || "Sales Master Data report failed.";
      try {
        const messages = JSON.parse(body._server_messages || "[]");
        if (messages[0]) message = JSON.parse(messages[0]).message || message;
      } catch {
      }
      throw new Error(String(message).replace(/<[^>]*>/g, "").split("\n").pop());
    }
    const result = Array.isArray(body.message?.result) ? body.message.result : [];
    totalSourceIndex.value = result.findIndex(row => row && typeof row === 'object' && !Array.isArray(row) && (row.is_total_row === true || row.is_total_row === 1 || row.invoice === 'Total'));
    return result.map((row, index) => {
      if (!row || typeof row !== 'object' || Array.isArray(row) || row.is_total_row === true || row.is_total_row === 1 || row.invoice === 'Total') return null;
      const copy = normalizeRow(row), normalizedRequested = String(requestedBranch || "").trim();
      copy.__sourceIndex = index;
      copy.__requestedBranch = normalizedRequested;
      if (normalizedRequested && String(copy.branch || "").trim() !== normalizedRequested) return null;
      return copy;
    }).filter(Boolean);
  }
  function validate() {
    if (!from.value || !to.value) {
      error.value = "Choose both report dates.";
      return false;
    }
    if (from.value > to.value) {
      error.value = "From Date cannot be after To Date.";
      return false;
    }
    const pFrom = parseAmount(paidFrom.value), pTo = parseAmount(paidTo.value), out = parseAmount(outstandingValue.value);
    if (paidFrom.value.trim() && pFrom === null) {
      error.value = "Enter a valid Paid Amount From value.";
      return false;
    }
    if (paidTo.value.trim() && pTo === null) {
      error.value = "Enter a valid Paid Amount To value.";
      return false;
    }
    if (pFrom !== null && pTo !== null && pFrom > pTo) {
      error.value = "Paid Amount From cannot exceed Paid Amount To.";
      return false;
    }
    if (outstandingOperator.value && out === null) {
      error.value = "Enter a valid Outstanding Amount.";
      return false;
    }
    if (branchRestricted.value && branch.value && !permittedBranches.value.includes(branch.value)) {
      error.value = "You do not have access to the selected branch.";
      return false;
    }
    if (branchRestricted.value && permittedBranches.value.length === 1 && !branch.value) branch.value = permittedBranches.value[0];
    return true;
  }
  function stateSnapshot() {
    return { fromDate: from.value, toDate: to.value, branch: branch.value, salesPerson: salesPerson.value, bookingType: bookingType.value, modeOfPayment: modeOfPayment.value, customer: customer.value.trim().toLowerCase(), paidFrom: parseAmount(paidFrom.value), paidTo: parseAmount(paidTo.value), outstandingOperator: outstandingOperator.value, outstandingValue: parseAmount(outstandingValue.value) };
  }
  function applyLocalFilters(source, state) {
    return source.filter((row) => {
      if (branchRestricted.value && permittedBranches.value.length && !permittedBranches.value.includes(String(row.branch || ""))) return false;
      if (state.branch && row.branch !== state.branch) return false;
      if (state.salesPerson && ![row.referring_employee, row.incentive_employee].some((name) => String(name || "").trim().toLowerCase() === state.salesPerson.toLowerCase())) return false;
      if (state.bookingType && row.booking_type !== state.bookingType) return false;
      if (state.modeOfPayment && !String(row.mode_of_payment || "").includes(state.modeOfPayment)) return false;
      if (state.customer && ![row.customer, row.invoice, row.mobile_no, row.customer_id, row.patient, row.patient_name, row.client_name].map(value => String(value || "")).join(" ").toLowerCase().includes(state.customer)) return false;
      const paid = parseAmount(row.paid_amount) || 0;
      if (state.paidFrom !== null && paid < state.paidFrom) return false;
      if (state.paidTo !== null && paid > state.paidTo) return false;
      const outstanding = parseAmount(row.outstanding_amount) || 0;
      if (state.outstandingOperator === ">" && !(outstanding > state.outstandingValue)) return false;
      if (state.outstandingOperator === ">=" && !(outstanding >= state.outstandingValue)) return false;
      if (state.outstandingOperator === "<" && !(outstanding < state.outstandingValue)) return false;
      if (state.outstandingOperator === "<=" && !(outstanding <= state.outstandingValue)) return false;
      return true;
    });
  }
  function updateEmployees() {
    const names = new Set();
    for (const row of rows.value) {
      if (row.referring_employee) names.add(row.referring_employee);
      if (row.incentive_employee) names.add(row.incentive_employee);
    }
    if (salesPerson.value && !names.has(salesPerson.value)) names.add(salesPerson.value);
    employees.value = [...names].sort((a, b) => a.localeCompare(b, void 0, { sensitivity: "base" }));
  }
  async function applyFilters() {
    if (loading.value || !branchReady.value || !validate()) return;
    controller?.abort();
    const ctrl = new AbortController();
    controller = ctrl;
    loading.value = true;
    error.value = "";
    notice.value = "";
    filteredRows.value = [];
    page.value = 1;
    const state = stateSnapshot();
    try {
      let branchesToLoad;
      if (branchRestricted.value && !state.branch && permittedBranches.value.length > 1) branchesToLoad = permittedBranches.value.slice();
      else branchesToLoad = [state.branch || ""];
      const groups = await Promise.all(branchesToLoad.map((name) => runOneBranch(state, name, ctrl.signal)));
      if (!alive || controller !== ctrl) return;
      const seen = new Set();
      rows.value = [];
      for (const group of groups) for (const row of group) {
        const key = rowKey(row);
        if (!seen.has(key)) {
          seen.add(key);
          rows.value.push(row);
        }
      }
      updateEmployees();
      filteredRows.value = applyLocalFilters(rows.value, state);
      reportLoaded.value = true; appliedState.value = state;
      notice.value = `Loaded ${filteredRows.value.length.toLocaleString("en-IN")} matching records.`;
    } catch (e) {
      if (alive && controller === ctrl && e.name !== "AbortError") {
        error.value = e.message;
        rows.value = [];
        filteredRows.value = [];
        employees.value = [];
        reportLoaded.value = false;
      }
    } finally {
      if (alive && controller === ctrl) loading.value = false;
    }
  }
  function setPreset(key) {
    quick.value = key;
    const range = dateRange(key);
    from.value = range.from;
    to.value = range.to;
    notice.value = "Date range changed. Click Apply Filters.";
  }
  function formatDate(value) { return value ? dateText(String(value).slice(0, 10)) : ''; }
  function salesPeople(row) {
    const ref2 = String(row.referring_employee || "").trim(), inc = String(row.incentive_employee || "").trim();
    return ref2 && inc ? `${ref2} / ${inc}` : ref2 || inc;
  }
  function rowValue(row, key) {
    if (key === "sales_people") return salesPeople(row);
    if (key === "posting_date") return formatDate(row.posting_date);
    if (["paid_amount", "tax_amount", "paid_amount_without_tax", "grand_total", "outstanding_amount"].includes(key)) return money(row[key]);
    return row[key] || "";
  }
  const totals = computed(() => Object.fromEntries(["paid_amount", "tax_amount", "paid_amount_without_tax", "grand_total", "outstanding_amount"].map((key) => [key, filteredRows.value.reduce((sum, row) => sum + (parseAmount(row[key]) || 0), 0)])));
  function csvCell(value) {
    const text = String(value ?? "");
    return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }
  function xmlCell(value) {
    return String(value ?? "").replace(/[<>&'\"]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", "'": "&apos;", '"': "&quot;" })[c]);
  }
  function exportRows() {
    if (!reportLoaded.value || !filteredRows.value.length) {
      error.value = "There are no filtered rows to download.";
      return;
    }
    const header = cols.map(([, label]) => label), numericKeys = new Set(["paid_amount", "tax_amount", "paid_amount_without_tax", "grand_total", "outstanding_amount"]), values = filteredRows.value.map((row) => cols.map(([key]) => key === "posting_date" ? formatDate(row.posting_date) : key === "sales_people" ? salesPeople(row) : numericKeys.has(key) ? parseAmount(row[key]) ?? 0 : row[key] ?? ""));
    const base = `Life_Sales_Master_All_Permitted_Branches_${appliedState.value.fromDate}_to_${appliedState.value.toDate}`;
    if (format.value === "csv") {
      const lines = [header, ...values].map((row) => row.map(csvCell).join(",")).join("\r\n");
      downloadBlob(base + ".csv", new Blob(["\uFEFF" + lines], { type: "text/csv;charset=utf-8" }));
    } else {
      const numeric = new Set(["Paid w/ GST", "GST Amt", "Paid w/o GST", "Grand Total", "Outstanding"]);
      const all = [header, ...values];
      const rowsXml = all.map((row, i) => `<Row>${row.map((v, j) => `<Cell><Data ss:Type="${i && numeric.has(header[j]) ? "Number" : "String"}">${xmlCell(v)}</Data></Cell>`).join("")}</Row>`).join("");
      const content = `<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="Sales Master"><Table>${rowsXml}</Table></Worksheet></Workbook>`;
      downloadBlob(base + ".xls", new Blob([content], { type: "application/vnd.ms-excel;charset=utf-8" }));
    }
    notice.value = `${format.value === "csv" ? "CSV" : "Excel"} download started for ${filteredRows.value.length.toLocaleString("en-IN")} filtered records.`;
  }
  function appliedLabels(state) {
    const labels = { 'From Date': state.fromDate, 'To Date': state.toDate };
    for (const [key, field] of [['Branch','branch'],['Sales Person','salesPerson'],['Booking Type','bookingType'],['Mode of Payment','modeOfPayment'],['Customer','customer'],['Paid Amount From','paidFrom'],['Paid Amount To','paidTo']]) if (state[field] !== '' && state[field] !== null) labels[key] = state[field];
    if (state.outstandingOperator) labels['Outstanding Amount Condition'] = state.outstandingOperator + ' ' + state.outstandingValue;
    return labels;
  }
  async function downloadReport() {
    if (loading.value || downloading.value || !branchReady.value || !validate()) return;
    downloading.value = true; error.value = '';
    try {
      if (!reportLoaded.value || JSON.stringify(stateSnapshot()) !== JSON.stringify(appliedState.value)) await applyFilters();
      if (!reportLoaded.value || !filteredRows.value.length) throw new Error(error.value || 'There are no filtered rows to download.');
      const state = appliedState.value;
      if (branchRestricted.value && !state.branch && permittedBranches.value.length > 1) { exportRows(); return; }
      const indices = filteredRows.value.map(row => row.__sourceIndex).filter(Number.isInteger);
      if (filteredRows.value.length === rows.value.length && totalSourceIndex.value >= 0) indices.push(totalSourceIndex.value);
      const args = { report_name: reportName, custom_columns: [], file_format_type: format.value === 'csv' ? 'CSV' : 'Excel', filters: { from_date: state.fromDate, to_date: state.toDate, branch: state.branch || '' }, applied_filters: appliedLabels(state), visible_idx: indices, include_filters: 1, include_indentation: 0, include_hidden_columns: 0, export_in_background: 0, csv_delimiter: ',', csv_quoting: 0 };
      controller?.abort(); controller = new AbortController();
      const response = await fetch(apiUrl('/api/method/frappe.desk.query_report.export_query'), { method: 'POST', credentials: apiCredentials(), signal: controller.signal, headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': session.csrf_token }, body: JSON.stringify(args) });
      if (!response.ok || /json|text\/html/.test(response.headers.get('Content-Type') || '')) throw new Error('Unable to download the report. Please retry.');
      const header = response.headers.get('Content-Disposition') || '';
      const encoded = header.match(/filename\*=UTF-8''([^;]+)/i), plain = header.match(/filename="?([^";]+)"?/i);
      let filename = 'Life_Sales_Master_' + state.fromDate + '_to_' + state.toDate + (format.value === 'csv' ? '.csv' : '.xlsx');
      try { if (encoded) filename = decodeURIComponent(encoded[1]); else if (plain) filename = plain[1]; } catch { /* Use the local fallback filename. */ }
      const blob = await response.blob(); if (!alive) return;
      downloadBlob(filename, blob); notice.value = (format.value === 'csv' ? 'CSV' : 'Excel') + ' download started for ' + filteredRows.value.length + ' filtered records.';
    } catch (failure) { if (alive && failure.name !== 'AbortError') error.value = failure.message; }
    finally { if (alive) downloading.value = false; }
  }
  function downloadBlob(filename, blob) {
    const url = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1e3);
  }
  function resetFilters() {
    const range = dateRange("thismonth");
    from.value = range.from;
    to.value = range.to;
    quick.value = "thismonth";
    branch.value = branchRestricted.value && permittedBranches.value.length === 1 ? permittedBranches.value[0] : "";
    salesPerson.value = "";
    bookingType.value = "";
    modeOfPayment.value = "";
    customer.value = "";
    paidFrom.value = "";
    paidTo.value = "";
    outstandingOperator.value = "";
    outstandingValue.value = "";
    applyFilters();
  }
  watch(outstandingOperator, value => { if (!value) outstandingValue.value = ''; });
  watch([from, to, branch, salesPerson, bookingType, modeOfPayment, customer, paidFrom, paidTo, outstandingOperator, outstandingValue], () => { if (reportLoaded.value && !loading.value) notice.value = 'Filter changed. Click Apply Filters.'; });
  onMounted(() => {
    const range = dateRange("thismonth");
    from.value = range.from;
    to.value = range.to;
    getBranches().then(() => {
      if (alive && branchReady.value) applyFilters();
    });
  });
  onBeforeUnmount(() => {
    alive = false;
    controller?.abort();
  });
  return { cols, presets, from, to, quick, branch, salesPerson, bookingType, modeOfPayment, customer, paidFrom, paidTo, outstandingOperator, outstandingValue, format, permittedBranches, allBranchAccess, branchRestricted, branchReady, branchError, rows, filteredRows, employees, loading, error, notice, page, reportLoaded, pageCount, visibleRows, money, recordCount, totals, rowValue, formatDate, getBranches, applyFilters, setPreset, resetFilters, downloadReport, downloading, appliedState };
}
