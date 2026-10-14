import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { request } from '../api/http';
import { session } from '../lib/session';
import { indiaDate } from '../lib/unjoined';
import { SLIMMING, CARD_START, sessionFields, submitted, monthRange, previousMonth, monthLabel, monthRows, openCardRows, number } from '../lib/weight-loss';

export function useWeightLoss() {
  const month = ref(indiaDate().slice(0, 7)), branch = ref(''), weightFilter = ref(''), search = ref(''), selectedClient = ref(''), branches = ref([]), clientOptions = ref([]), searchError = ref(''), searchVisible = ref(false);
  const rows = ref([]), openRows = ref([]), loading = ref(false), openLoading = ref(false), error = ref(''), openError = ref(''), notice = ref(''), page = ref(1), openPage = ref(1), detail = ref(null), openModal = ref(false);
  let controller, openController, searchController, searchTimer, generation = 0, searchGeneration = 0, openGeneration = 0, disposed = false;
  const months = computed(() => {
    const result = [], end = indiaDate().slice(0, 7);
    for (let key = '2023-08'; key <= end;) {
      result.push({ key, label: monthLabel(key) });
      const [year, month] = key.split('-').map(Number);
      key = new Date(Date.UTC(year, month, 1)).toISOString().slice(0, 7);
    }
    return result.reverse();
  });
  const visibleRows = computed(() => rows.value.filter(row => {
    if (branch.value && row.branch !== branch.value) return false;
    if (selectedClient.value && row.patient !== selectedClient.value) return false;
    const amount = number(row.month_difference);
    return weightFilter.value === 'one_and_above' ? amount > 1 : weightFilter.value === 'two_and_above' ? amount > 2 : weightFilter.value === 'three_and_above' ? amount > 3 : weightFilter.value === 'gain' ? amount < 0 : weightFilter.value === 'no_change' ? amount === 0 : true;
  }));
  const filteredOpenRows = computed(() => openRows.value.filter(row => (!branch.value || row.open_branches.includes(branch.value)) && (!selectedClient.value || row.patient === selectedClient.value)));
  const pageCount = computed(() => Math.max(1, Math.ceil(visibleRows.value.length / 10))), openPageCount = computed(() => Math.max(1, Math.ceil(filteredOpenRows.value.length / 20)));
  const pagedRows = computed(() => visibleRows.value.slice((page.value - 1) * 10, page.value * 10)), openPaged = computed(() => filteredOpenRows.value.slice((openPage.value - 1) * 20, openPage.value * 20));
  const totalLoss = computed(() => visibleRows.value.reduce((sum, row) => sum + Math.max(0, number(row.month_difference)), 0));
  const avgLoss = computed(() => visibleRows.value.length ? totalLoss.value / visibleRows.value.length : 0);
  const sessionCount = computed(() => visibleRows.value.reduce((sum, row) => sum + row.completed_sessions, 0));
  watch([branch, weightFilter, selectedClient], () => { page.value = 1; openPage.value = 1; });

  async function api(method, args, signal) { return (await request(method, { args, signal, csrfToken: session.csrf_token })).message; }
  function toRows(message) {
    if (Array.isArray(message?.values) && Array.isArray(message?.keys)) return message.values.map(values => Object.fromEntries(message.keys.map((key, index) => [key, values[index]])));
    return Array.isArray(message) ? message : [];
  }
  async function readAll(doctype, fields, filters, signal, order = 'name asc') {
    const result = [];
    for (let start = 0; ; start += 5000) {
      const batch = toRows(await api('frappe.desk.reportview.get', { doctype, fields, filters, order_by: order, start, page_length: 5000 }, signal));
      if (disposed) throw new DOMException('Page closed', 'AbortError');
      result.push(...batch); if (batch.length < 5000) return result;
    }
  }
  async function patientChunks(doctype, fields, patients, filters, signal, order) {
    const result = [];
    for (let start = 0; start < patients.length; start += 500) result.push(...await readAll(doctype, fields, [[doctype, doctype === 'Patient' ? 'name' : 'patient', 'in', patients.slice(start, start + 500)], ...filters], signal, order));
    return result;
  }
  async function loadBranches() {
    try {
      const rows = await readAll('Branch', ['name', 'branch'], [], undefined, 'modified desc, name desc');
      if (!disposed) branches.value = [...new Set(rows.map(row => row.branch || row.name).filter(name => name && !['testing branch', 'head office'].includes(name.trim().toLowerCase())))].sort();
    } catch (failure) { if (!disposed) notice.value = 'Branch list unavailable: ' + failure.message; }
  }
  async function refreshMonthly() {
    if (!month.value || !/^\d{4}-\d{2}$/.test(month.value)) { error.value = 'Please select a valid month.'; return; }
    const token = ++generation, selectedMonth = month.value, selected = selectedClient.value;
    controller?.abort(); controller = new AbortController(); const signal = controller.signal;
    loading.value = true; error.value = ''; notice.value = ''; rows.value = []; detail.value = null; page.value = 1;
    try {
      const currentRange = monthRange(selectedMonth), previousRange = monthRange(previousMonth(selectedMonth)), base = [['Therapy Session', 'service_unit', '=', SLIMMING], ['Therapy Session', 'docstatus', '=', 1]];
      const current = submitted(await readAll('Therapy Session', sessionFields, [...base, ['Therapy Session', 'start_date', '>=', currentRange.start], ['Therapy Session', 'start_date', '<=', currentRange.end], ...(selected ? [['Therapy Session', 'patient', '=', selected]] : [])], signal, 'start_date asc, name asc'));
      const patients = [...new Set(current.map(row => String(row.patient || '').trim()).filter(Boolean))];
      const [previous, history, plans, patientRows] = patients.length ? await Promise.all([
        patientChunks('Therapy Session', sessionFields, patients, [...base, ['Therapy Session', 'start_date', '>=', previousRange.start], ['Therapy Session', 'start_date', '<=', previousRange.end]], signal, 'start_date asc, name asc'),
        patientChunks('Therapy Session', sessionFields, patients, [...base, ['Therapy Session', 'start_date', '<=', currentRange.end]], signal, 'start_date asc, name asc'),
        patientChunks('Therapy Plan', ['name', 'patient', 'branch', 'category', 'status', 'start_date', 'total_sessions', 'total_sessions_completed', 'modified'], patients, [['Therapy Plan', 'branch', '!=', '']], signal, 'modified desc, name desc'),
        patientChunks('Patient', ['name', 'mobile', 'phone'], patients, [], signal, 'name asc'),
      ]) : [[], [], [], []];
      if (disposed || token !== generation) return;
      rows.value = monthRows({ month: selectedMonth, current, previous, history, plans, patients: patientRows });
      notice.value = rows.value.length ? 'Loaded ' + rows.value.length.toLocaleString('en-IN') + ' clients for ' + monthLabel(selectedMonth) + '.' : 'No submitted slimming sessions found for selected month';
    } catch (failure) { if (!disposed && token === generation && failure.name !== 'AbortError') error.value = failure.message; }
    finally { if (!disposed && token === generation) loading.value = false; }
  }
  async function refreshOpenCards() {
    const token = ++openGeneration;
    openController?.abort(); openController = new AbortController(); const signal = openController.signal;
    openLoading.value = true; openError.value = '';
    try {
      const today = indiaDate();
      const [attendance, plans] = await Promise.all([
        readAll('Therapy Session', ['name', 'patient', 'therapy_plan', 'start_date', 'docstatus'], [['Therapy Session', 'service_unit', '=', SLIMMING], ['Therapy Session', 'docstatus', '=', 1], ['Therapy Session', 'start_date', '>=', CARD_START], ['Therapy Session', 'start_date', '<=', today]], signal, 'start_date desc, name desc'),
        readAll('Therapy Plan', ['name', 'patient', 'patient_name', 'branch', 'category', 'status', 'start_date', 'docstatus', 'total_sessions', 'total_sessions_completed'], [['Therapy Plan', 'category', '=', SLIMMING], ['Therapy Plan', 'docstatus', '!=', 2], ['Therapy Plan', 'status', 'in', ['Not Started', 'In Progress']], ['Therapy Plan', 'start_date', '<=', today]], signal, 'start_date desc, name desc'),
      ]);
      const names = [...new Set(plans.map(plan => String(plan.patient || '').trim()).filter(Boolean))];
      const patients = await patientChunks('Patient', ['name', 'mobile', 'phone', 'branch_name'], names, [], signal, 'name asc');
      if (!disposed && token === openGeneration) { openRows.value = openCardRows({ attendance, plans, patients, today }); openPage.value = 1; }
    } catch (failure) { if (!disposed && token === openGeneration && failure.name !== 'AbortError') { openError.value = failure.message; openRows.value = []; } }
    finally { if (!disposed && token === openGeneration) openLoading.value = false; }
  }
  async function refresh() { await Promise.all([refreshMonthly(), refreshOpenCards()]); }
  async function findClients() {
    const term = search.value.trim(), token = ++searchGeneration;
    searchController?.abort(); searchController = new AbortController(); searchError.value = '';
    if (term.length < 2) { clientOptions.value = []; searchVisible.value = false; return; }
    try {
      const matches = await api('frappe.desk.search.search_link', { txt: term, doctype: 'Patient', reference_doctype: 'Therapy Session', page_length: 10 }, searchController.signal);
      if (!disposed && token === searchGeneration) { clientOptions.value = Array.isArray(matches) ? matches : []; searchVisible.value = true; }
    } catch (failure) { if (!disposed && token === searchGeneration && failure.name !== 'AbortError') { clientOptions.value = []; searchError.value = 'Failed to search clients'; searchVisible.value = true; } }
  }
  function searchChanged() { clearTimeout(searchTimer); searchController?.abort(); searchGeneration++; searchTimer = setTimeout(findClients, 300); }
  async function selectClient(row) { selectedClient.value = row.value || row.name; search.value = selectedClient.value; searchVisible.value = false; await refreshMonthly(); }
  async function clearClient() { selectedClient.value = ''; search.value = ''; clientOptions.value = []; searchVisible.value = false; searchController?.abort(); searchGeneration++; await refreshMonthly(); }
  function closeOverlays(event) { if (event.key === 'Escape') { detail.value = null; openModal.value = false; searchVisible.value = false; } }
  onMounted(() => { loadBranches(); refresh(); window.addEventListener('keydown', closeOverlays); });
  onBeforeUnmount(() => { disposed = true; generation++; openGeneration++; searchGeneration++; controller?.abort(); openController?.abort(); searchController?.abort(); clearTimeout(searchTimer); window.removeEventListener('keydown', closeOverlays); });
  return { month, branch, weightFilter, search, selectedClient, branches, clientOptions, searchVisible, searchError, rows, openRows, loading, openLoading, error, openError, notice, page, openPage, detail, openModal, months, visibleRows, filteredOpenRows, pageCount, openPageCount, pagedRows, openPaged, totalLoss, avgLoss, sessionCount, refresh, refreshMonthly, searchChanged, selectClient, clearClient };
}
