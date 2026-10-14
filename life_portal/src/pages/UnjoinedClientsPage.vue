<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { useUnjoined } from '../composables/useUnjoined';
import data from '../data/unjoined.json';
import { tabKeys, followStatuses, indiaDate, dateText, maskText, maskPhone } from '../lib/unjoined';
import { workbook } from '../lib/xlsx';
import ClientPhoto from '../components/unjoined/ClientPhoto.vue';
import RecordDetails from '../components/unjoined/RecordDetails.vue';
import FollowupEditor from '../components/unjoined/FollowupEditor.vue';
import '../styles/unjoined.css';

const { sections, filters, applied, branches, manager, busy, loaded, notice, records, followups, detail, draft, dirty, saving, saveNotice, photo, legacyChoice, canOutput, show, cachedKey, initialize, load, paginate, openDetail, closeDetail, chooseLegacy, save, allRows } = useUnjoined();
const activeTab = ref('clients'), dialog = ref(null), detailPrint = ref(null), reportPrint = ref(null), printBatches = ref([]);
const tabButtons = new Map();
const tabs = computed(() => tabKeys.map(key => ({ key, section: sections.find(section => section.key === key) })));
const visibleSections = computed(() => sections.filter(section => (section.key === 'appointments' ? 'pending' : section.key) === activeTab.value));
const followBranches = computed(() => branches.value);
const displayDate = section => (applied.value?.basis || filters.basis) === 'created' ? 'creation' : section.date;
const dateLabel = section => (applied.value?.basis || filters.basis) === 'created' ? 'Record created' : section.dateLabel;
const photoFor = (section, row) => row.custom_client_photo_attach || row.image || followups.get(cachedKey(section, row.name))?.custom_client_photo_attach;
function statusFor(section, row) {
  let result = row[section.status] || '—';
  if (['pending', 'appointments'].includes(section.key)) {
    const date = String(row[section.date] || '').slice(0, 10), today = indiaDate();
    result += ' · ' + (!date ? 'Date missing' : date < today ? 'Overdue' : date === today ? 'Today' : 'Upcoming');
  }
  return result;
}
function cardCount(key) {
  if (records[key].error || (key === 'pending' && records.appointments.error)) return '—';
  return records[key].count + (key === 'pending' ? records.appointments.count : 0);
}
function tabKeydown(event, key) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const index = tabKeys.indexOf(key), next = event.key === 'Home' ? 0 : event.key === 'End' ? tabKeys.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabKeys.length) % tabKeys.length;
  activeTab.value = tabKeys[next]; nextTick(() => tabButtons.get(activeTab.value)?.focus());
}
async function reset() {
  Object.assign(filters, { from: '', to: '', branch: '', search: '', followStatus: '' });
  await nextTick(); await load();
}
watch(() => detail.open, async open => {
  await nextTick();
  if (open && !dialog.value?.open) dialog.value?.showModal();
  if (!open && dialog.value?.open) dialog.value.close();
});
function cancelDialog(event) { if (!closeDetail()) event.preventDefault(); }
function markDirty() { dirty.value = true; saveNotice.value = 'Unsaved changes'; }
function setField(field, value) { draft[field] = value; }
async function legacySelected(value) { legacyChoice.value = value; await chooseLegacy(value); }

const printStyle = 'body{font:12px Arial;color:#152418}h1,h2{color:#1b5e20}table{border-collapse:collapse;width:100%;margin-bottom:24px}td,th{border:1px solid #dce9de;padding:5px;word-break:break-word;text-align:left}thead{display:table-header-group}tr{break-inside:avoid}h2{break-after:avoid}b{display:block}img{max-width:200px;max-height:200px}.uj-full-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.uj-wide{grid-column:1/-1}.uj-gallery{display:flex;flex-wrap:wrap;gap:12px}.uj-gallery a{display:grid}.uj-record-part{break-after:page}.uj-photo{width:120px;height:120px}';
async function printWindow(win, element, title, landscape = false) {
  win.document.open();
  win.document.write('<!doctype html><html><head><title>' + title + '</title><style>' + (landscape ? '@page{size:A4 landscape;margin:12mm}' : '') + printStyle + '</style></head><body>' + element.innerHTML + '</body></html>');
  win.document.close();
  await Promise.all(Array.from(win.document.images).map(image => image.complete ? Promise.resolve() : new Promise(resolve => { image.onload = resolve; image.onerror = resolve; setTimeout(resolve, 8000); })));
  if (!win.closed) { win.focus(); win.print(); }
}
async function printDetails() {
  if (detail.busy || detail.error) return;
  const win = window.open('', '_blank');
  if (!win) { notice.value = 'Allow popups for printing.'; return; }
  await printWindow(win, detailPrint.value, 'Full client details');
}
async function output(key, print = false) {
  if (!canOutput.value) return;
  const selected = key === 'all' ? sections : sections.filter(section => section.key === key);
  if (selected.some(section => records[section.key].error)) { notice.value = 'Resolve the section access errors before exporting.'; return; }
  const win = print ? window.open('', '_blank') : null;
  if (print && !win) { notice.value = 'Allow popups for printing.'; return; }
  if (win) win.document.body.textContent = 'Preparing all filtered records…';
  busy.value = true;
  try {
    const batches = [];
    for (const section of selected) batches.push({ section, rows: await allRows(section) });
    if (print) {
      printBatches.value = batches; await nextTick();
      await printWindow(win, reportPrint.value, 'Unjoined Data', true);
    } else {
      const sheets = batches.map(({ section, rows }) => ({ name: section.key, rows: [section.fields.map(field => data.meta[section.dt].find(meta => meta.fieldname === field)?.label || field), ...rows.map(row => section.fields.map(field => show(field, row[field] ?? '')))] }));
      const criteria = applied.value;
      sheets.push({ name: 'Filters', rows: [['From', criteria.from], ['To', criteria.to], ['Branch', criteria.branch || 'All permitted branches'], ['Date basis', criteria.basis], ['Search', maskText(criteria.search, manager.value)], ['Generated', new Date().toISOString()], ['Notes', 'Section counts may overlap. Export includes all filtered list records; full record and child tables are available through Full details & images.']] });
      const url = URL.createObjectURL(workbook(sheets)), link = document.createElement('a');
      link.href = url; link.download = 'LIFE_Unjoined_Data_' + indiaDate() + '.xlsx'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    }
    notice.value = 'Prepared ' + batches.reduce((count, batch) => count + batch.rows.length, 0) + ' filtered records.';
  } catch (error) { if (win) win.close(); notice.value = 'Export / print failed: ' + error.message; }
  finally { busy.value = false; printBatches.value = []; }
}
function beforeUnload(event) { if (dirty.value || saving.value) { event.preventDefault(); event.returnValue = ''; } }
onBeforeRouteLeave(() => !saving.value && (!dirty.value || window.confirm('Discard unsaved follow-up changes?')));
onMounted(() => { window.addEventListener('beforeunload', beforeUnload); initialize(); });
onBeforeUnmount(() => { window.removeEventListener('beforeunload', beforeUnload); dialog.value?.close(); });
</script>

<template>
  <div id="unjoinedApp">
    <header class="uj-header"><div><small>LIFE · CLIENT &amp; LEAD REPORT</small><h1>Unjoined Data</h1><p>Track unjoined clients · record calls · schedule follow-ups</p></div><RouterLink :to="{ name: 'home' }">← Home</RouterLink></header>
    <div class="uj-body">
      <form class="uj-filters" @submit.prevent="load">
        <label>From Date<input id="ujFrom" v-model="filters.from" type="date" :disabled="busy"></label><label>To Date<input id="ujTo" v-model="filters.to" type="date" :disabled="busy"></label>
        <label>Branch<select id="ujBranch" v-model="filters.branch" :disabled="busy"><option value="">All permitted branches</option><option v-for="branch in branches" :key="branch">{{ branch }}</option></select></label>
        <label>Date Basis<select id="ujBasis" v-model="filters.basis" :disabled="busy"><option value="business">Section business date</option><option value="created">Record created date</option></select></label>
        <label>Follow-up Status<select id="ujFollowStatus" v-model="filters.followStatus" :disabled="busy"><option value="">All statuses (Register)</option><option v-for="status in followStatuses" :key="status">{{ status }}</option></select></label>
        <label class="uj-search">Search<input id="ujSearch" v-model="filters.search" placeholder="Name, client / lead ID, mobile" type="search" :disabled="busy"></label>
        <button id="ujApply" type="submit" :disabled="busy">Apply</button><button id="ujReset" type="button" :disabled="busy" @click="reset">Reset</button>
      </form>
      <p class="uj-help">Business date: Clients = Joining Date; Visited Leads = Status Updated Date; Booked appointments = Appointment Date. Blank business dates are excluded when a date range is applied. Clear dates for all records. Testing Branch is excluded. Follow-up Register uses Visited Date; its status filter applies to that tab.</p>
      <div class="uj-tools"><span id="ujMaskNote" class="uj-mask-note">{{ manager ? 'System Manager · full numbers in list, hover, details, print and Excel' : 'Contact numbers are masked on screen, hover, print and Excel' }}</span><button :disabled="!canOutput" @click="output('all')">Export All Sections · Excel</button><button :disabled="!canOutput" @click="output('all', true)">Print All / Save PDF</button></div>
      <p id="ujNotice" role="status" aria-live="polite">{{ notice }}</p>
      <div id="ujCards" role="tablist" aria-label="Unjoined Data tabs">
        <button v-for="tab in tabs" :key="tab.key" :ref="element => element ? tabButtons.set(tab.key, element) : tabButtons.delete(tab.key)" role="tab" :aria-controls="'uj-' + tab.key" :aria-selected="activeTab === tab.key" :tabindex="activeTab === tab.key ? 0 : -1" class="uj-card" :class="{ 'is-active': activeTab === tab.key }" @click="activeTab = tab.key" @keydown="tabKeydown($event, tab.key)"><small>{{ tab.key === 'pending' ? 'Booked / Not Visited' : tab.section.title.replace(/^\d\. /, '') }}</small><strong>{{ cardCount(tab.key) }}</strong></button>
      </div>
      <div id="ujSections">
        <section v-for="section in visibleSections" :id="'uj-' + section.key" :key="section.key" role="tabpanel">
          <div class="uj-section-head"><div><h2>{{ section.title }} <span class="uj-count">{{ records[section.key].count }}</span></h2><small>Date filter: <span class="uj-date-label">{{ dateLabel(section) }}</span></small></div><div><button :disabled="!canOutput" @click="output(section.key)">Export Excel</button><button :disabled="!canOutput" @click="output(section.key, true)">Print / Save PDF</button></div></div>
          <div class="uj-scroll"><table><thead><tr><th>#</th><th>Client / Lead</th><th>Mobile / Alternate</th><th>Branch</th><th>Category</th><th>Date</th><th>Status</th><th>Details / Images</th></tr></thead><tbody>
            <tr v-if="records[section.key].error"><td colspan="8" class="uj-error">{{ records[section.key].error }}</td></tr>
            <tr v-else-if="!records[section.key].rows.length"><td colspan="8">{{ busy ? 'Loading permitted ERP records…' : 'No matching records.' }}</td></tr>
            <tr v-for="(row, index) in records[section.key].rows" v-else :key="row.name">
              <td>{{ records[section.key].page * 20 + index + 1 }}</td>
              <td><div class="uj-person"><ClientPhoto :value="photoFor(section, row)" /><div><button class="uj-link" @click="openDetail(section, row.name)">{{ show(section.name, row[section.name] || row.name) }}</button><small>{{ show('name', row.name) }}</small><small v-if="followups.has(cachedKey(section, row.name))" class="uj-success">{{ followups.get(cachedKey(section, row.name)).status || 'Follow-up saved' }}</small></div></div></td>
              <td><span class="uj-mobile" :title="maskPhone(row[section.mobile], manager)">{{ maskPhone(row[section.mobile], manager) || '—' }}</span><small><span class="uj-mobile" :title="maskPhone(row.phone, manager)">{{ maskPhone(row.phone, manager) }}</span></small></td>
              <td>{{ show(section.branch, row[section.branch] || row.branch_name || '—') }}</td><td>{{ show(section.category, row[section.category] || '—') }}</td>
              <td>{{ dateText(row[displayDate(section)]) }}<small v-if="section.key === 'forms'">Next: {{ dateText(row.next_follow_up_scheduled_date) }}</small></td>
              <td><span class="uj-badge">{{ show(section.status, statusFor(section, row)) }}</span></td>
              <td><div class="uj-row-actions"><button class="uj-primary" @click="openDetail(section, row.name, 'follow')">{{ section.key === 'forms' ? 'Edit & Save' : 'Follow-up / Edit' }}</button><button @click="openDetail(section, row.name)">Details &amp; Images</button></div></td>
            </tr>
          </tbody></table></div>
          <div class="uj-paging"><button :disabled="busy || !loaded || !records[section.key].page" @click="paginate(section, -1)">Previous</button><span>{{ records[section.key].count ? records[section.key].page * 20 + 1 : 0 }}–{{ Math.min(records[section.key].page * 20 + records[section.key].rows.length, records[section.key].count) }} of {{ records[section.key].count }}</span><button :disabled="busy || !loaded || (records[section.key].page + 1) * 20 >= records[section.key].count" @click="paginate(section, 1)">Next</button></div>
        </section>
      </div>
    </div>
    <dialog id="ujDialog" ref="dialog" @cancel="cancelDialog">
      <div class="uj-dialog-head"><h2>Client Workspace</h2><div><button v-if="detail.tab === 'record'" id="ujPrintDetail" :disabled="detail.busy || !!detail.error" @click="printDetails">Print Details / Save PDF</button><button id="ujClose" aria-label="Close details" :disabled="saving" @click="closeDetail">✕ Close</button></div></div>
      <div class="uj-detail-tabs" role="tablist"><button v-for="tab in ['record', 'follow']" :key="tab" role="tab" :aria-controls="tab === 'record' ? 'ujDetails' : 'ujFollowPane'" :aria-selected="detail.tab === tab" :class="{ 'is-active': detail.tab === tab }" @click="detail.tab = tab">{{ tab === 'record' ? 'Details & Images' : 'Follow-up / Edit' }}</button></div>
      <div id="ujDetails" ref="detailPrint" role="tabpanel" :hidden="detail.tab !== 'record'"><p v-if="detail.busy">Loading full record and attached images…</p><p v-else-if="detail.error" class="uj-error">{{ detail.error }}</p><template v-else><p v-if="detail.warning" class="uj-error">{{ detail.warning }}</p><RecordDetails v-for="part in detail.parts" :key="part.doctype + ':' + part.doc.name" :part="part" :manager="manager" /></template></div>
      <div id="ujFollowPane" role="tabpanel" :hidden="detail.tab !== 'follow'"><p v-if="detail.error" class="uj-error">{{ detail.error }}</p><p v-else-if="!detail.context">Loading follow-up form…</p><FollowupEditor v-else :context="detail.context" :draft="draft" :branches="followBranches" :manager="manager" :saving="saving" :dirty="dirty" :notice="saveNotice" :legacy-choice="legacyChoice" @field="setField" @change="markDirty" @photo="photo = $event" @legacy="legacySelected" @save="save" /></div>
    </dialog>
    <div ref="reportPrint" hidden aria-hidden="true">
      <h1>LIFE · Unjoined Data</h1><p>{{ applied?.from || 'All dates' }} to {{ applied?.to || 'All dates' }} · {{ applied?.branch || 'All permitted branches' }} · {{ applied?.basis === 'created' ? 'Record created date' : 'Section business date' }} · {{ maskText(applied?.search, manager) }}</p>
      <template v-for="batch in printBatches" :key="batch.section.key"><h2>{{ batch.section.title }} ({{ batch.rows.length }})</h2><table><thead><tr><th>ID</th><th>Name</th><th>Mobile</th><th>Branch</th><th>Category</th><th>{{ dateLabel(batch.section) }}</th><th>Status</th></tr></thead><tbody><tr v-for="row in batch.rows" :key="row.name"><td v-for="field in ['name', batch.section.name, batch.section.mobile, batch.section.branch, batch.section.category, displayDate(batch.section), batch.section.status]" :key="field">{{ show(field, row[field]) }}</td></tr></tbody></table></template>
    </div>
  </div>
</template>

<style scoped>
.uj-edit-grid{margin:0;padding:0;border:0;min-width:0}
</style>
