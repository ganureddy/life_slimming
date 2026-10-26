<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { billingList } from '../api/billing';
import { indiaStamp } from '../lib/cc';
import { priceListTabs, splitPackages } from '../lib/price-list';
import { legacyPageOffer } from '../lib/price-list';
import { sanitizeRichText } from '../lib/rich-text';
import { request } from '../api/http';
import { session } from '../lib/session';

const route = useRoute(), router = useRouter();
const validTabs = priceListTabs.map(([id]) => id);
const tab = ref(validTabs.includes(route.query.tab) ? route.query.tab : 'types');
const therapies = ref([]), packages = ref([]), rules = ref([]);
const loaded = reactive({ types: false, packages: false, liferise: false });
const loading = reactive({ types: false, packages: false, liferise: false });
const errors = reactive({ types: '', packages: '', liferise: '' });
const search = reactive({ types: '', packages: '', liferise: '' });
const pages = reactive({ types: 1, packages: 1, liferise: 1 });
const offerOnly = ref(false), offerWarning = ref('');
const detail = ref(null), detailName = ref(''), detailBusy = ref(false), detailError = ref('');
const controllers = { types: null, packages: null }; let detailController, alive = true;
const today = indiaStamp().slice(0, 10);
const allTherapies = computed(() => therapies.value.map(row => ({ ...row, offer: legacyPageOffer(row, rules.value, today) })));
const packageGroups = computed(() => splitPackages(packages.value));
const currentRows = computed(() => tab.value === 'types' ? allTherapies.value : packageGroups.value[tab.value]);
const filtered = computed(() => {
  const query = search[tab.value].toLowerCase();
  return currentRows.value.filter(row => {
    const matches = tab.value === 'types' ? [row.therapy_type, category(row.healthcare_service_unit)] : [row.plan_name, row.item_code];
    return matches.some(value => String(value || '').toLowerCase().includes(query)) && (tab.value !== 'types' || !offerOnly.value || !!row.offer);
  });
});
const pageCount = computed(() => Math.max(1, Math.ceil(filtered.value.length / 10)));
const visible = computed(() => filtered.value.slice((pages[tab.value] - 1) * 10, pages[tab.value] * 10));
const money = value => value === null || value === undefined || value === '' ? '-' : Number(value).toFixed(2);
const date = value => value ? String(value).slice(0, 10).split('-').reverse().join('/') : '—';
const category = value => String(value || '').replace(/\s*-\s*LSACPL\s*$/i, '').trim();

async function listAll(doctype, filters, fields, signal) {
  const rows = [];
  for (let start = 0; ; start += 100) {
    const batch = await billingList(doctype, filters, fields, { start, limit: 100, order: doctype === 'Therapy Type' ? 'therapy_type asc' : 'plan_name asc', signal });
    rows.push(...batch);
    if (batch.length < 100) return rows;
  }
}
async function nativeCall(method, args, signal) { return (await request(method, { args, csrfToken: session.csrf_token, signal })).message; }
async function loadTypes() {
  controllers.types?.abort(); const current = new AbortController(); controllers.types = current; const signal = current.signal;
  loading.types = true; errors.types = ''; offerWarning.value = ''; rules.value = [];
  try {
    const rows = await listAll('Therapy Type', [['is_billable', '=', 1], ['disabled', '=', 0], ['custom_show_in_billing', '=', 1]], ['therapy_type', 'healthcare_service_unit', 'item_code', 'rate', 'minimum_price', 'maximum_price', 'custom_show_in_billing'], signal);
    if (!alive || signal.aborted) return;
    therapies.value = rows.filter(row => Number(row.rate) > 0 && Number(row.custom_show_in_billing) === 1); loaded.types = true; loading.types = false;
    try {
      const names = [];
      for (let start = 0; ; start += 1000) {
        const batch = await nativeCall('frappe.client.get_list', { doctype: 'Pricing Rule', filters: { disable: 0, selling: 1, apply_on: 'Item Code' }, fields: ['name'], limit_start: start, limit_page_length: 1000, order_by: 'modified desc, name desc' }, signal);
        names.push(...batch); if (batch.length < 1000) break;
      }
      let next = 0; const offers = [];
      const priorities = new Map(names.map((row,index)=>[row.name,index]));
      async function readRule() {
        while (next < names.length && !signal.aborted) {
          const name = names[next++].name;
          try {
            const doc = await nativeCall('frappe.client.get', { doctype: 'Pricing Rule', name }, signal);
            if (doc?.items && !Number(doc.disable) && Number(doc.selling) && (!doc.valid_from || today >= doc.valid_from) && (!doc.valid_upto || today <= doc.valid_upto)) for (const item of doc.items) if (item.item_code) offers.push({ ...doc, item_code: item.item_code });
            if (alive && !signal.aborted) rules.value = [...offers].sort((a,b)=>priorities.get(a.name)-priorities.get(b.name));
          } catch (error) { if (signal.aborted) throw error; offerWarning.value = 'Some current offers could not be loaded.'; }
        }
      }
      await Promise.all(Array.from({ length: Math.min(5, names.length) }, readRule));
      if (alive && !signal.aborted) rules.value = [...offers].sort((a,b)=>priorities.get(a.name)-priorities.get(b.name));
    } catch (error) { if (alive && !signal.aborted) offerWarning.value = 'Current offers could not be loaded: ' + error.message; }
  } catch (error) { if (alive && !signal.aborted) errors.types = error.message; }
  finally { if (alive && controllers.types === current) loading.types = false; }
}
async function loadPackages() {
  controllers.packages?.abort(); const current = new AbortController(); controllers.packages = current; const signal = current.signal;
  loading.packages = true; loading.liferise = true; errors.packages = ''; errors.liferise = '';
  try {
    packages.value = await listAll('Therapy Plan Template', [['is_active', '=', 1]], ['name', 'plan_name', 'item_code', 'item_group', 'gst_hsn_code', 'description', 'total_sessions', 'total_amount', 'offer_price', 'custom_including_gst', 'is_active', 'offer_valid_from', 'offer_valid_to'], signal);
    if (!alive || signal.aborted) return; loaded.packages = true; loaded.liferise = true;
  } catch (error) { if (!signal.aborted) { errors.packages = error.message; errors.liferise = error.message; } }
  finally { if (controllers.packages === current) { loading.packages = false; loading.liferise = false; } }
}
function ensureLoaded() { if (tab.value === 'types' && !loaded.types && !loading.types) loadTypes(); else if (tab.value !== 'types' && !loaded.packages && !loading.packages) loadPackages(); }
function selectTab(id) { tab.value = id; router.replace({ query: { ...route.query, tab: id } }); ensureLoaded(); }
async function openDetail(name) {
  detailController?.abort(); detailController = new AbortController(); const signal = detailController.signal;
  detailName.value = name; detail.value = null; detailBusy.value = true; detailError.value = '';
  try { const doc = await nativeCall('frappe.client.get', { doctype: 'Therapy Plan Template', name }, signal); if (!doc) throw new Error('Not found'); if (alive && !signal.aborted) detail.value = doc; }
  catch (error) { if (alive && !signal.aborted) detailError.value = error.message; }
  finally { if (alive && !signal.aborted) detailBusy.value = false; }
}
function closeDetail() { detailController?.abort(); detailName.value = ''; detail.value = null; detailBusy.value = false; }
function onKeydown(event) { if (event.key === 'Escape' && detailName.value) closeDetail(); }
watch(() => route.query.tab, value => { const next = validTabs.includes(value) ? value : 'types'; if (next !== tab.value) { tab.value = next; ensureLoaded(); } });
for (const id of validTabs) watch(() => search[id], () => { pages[id] = 1; });
watch(offerOnly, () => { pages.types = 1; });
onMounted(() => { ensureLoaded(); window.addEventListener('keydown', onKeydown); });
onBeforeUnmount(() => { alive = false; controllers.types?.abort(); controllers.packages?.abort(); detailController?.abort(); window.removeEventListener('keydown', onKeydown); });
</script>
<template>
  <section class="tt-block price-list-native">
    <div class="tt-tabs price-tabs"><button v-for="[id,label] in priceListTabs" :key="id" type="button" class="tt-tab-btn" :class="{active:tab === id}" :aria-current="tab === id ? 'page' : undefined" @click="selectTab(id)">{{ id === 'types' ? '💊' : id === 'packages' ? '📦' : '🌟' }} {{ label }}</button></div>
    <div class="tt-panel price-panel" :data-panel="tab">
      <div class="tt-header"><h3>{{ tab === 'types' ? '💊 Billable Therapy Types' : tab === 'packages' ? '📦 Therapy Plan Templates' : '🌟 LIFErise Packages' }} <span class="tt-badge" :class="{'pkg-badge':tab === 'packages', 'lr-badge':tab === 'liferise'}">{{ tab === 'types' ? 'In Plan Templates' : tab === 'packages' ? 'Packages' : 'LIFErise' }}</span></h3><div class="tt-filter-row price-filters"><input v-model="search[tab]" type="text" autocomplete="off" :class="tab === 'types' ? 'tt-search' : tab === 'packages' ? 'pkg-search' : 'lr-search'" :placeholder="tab === 'types' ? '🔍 Search therapy type...' : tab === 'packages' ? '🔍 Search package / item code...' : '🔍 Search LIFErise package...'"><button v-if="tab === 'types'" class="tt-offer-filter-btn" :class="{active:offerOnly}" :data-active="offerOnly ? 1 : 0" :aria-pressed="offerOnly" @click="offerOnly = !offerOnly">{{ offerOnly ? '✅ Offer Applied Only' : '🏷️ Offer Applied' }}</button></div></div>
      <p v-if="errors[tab]" class="tt-loading" role="alert">{{ errors[tab] }} <button @click="tab === 'types' ? loadTypes() : loadPackages()">Retry</button></p><p v-if="offerWarning && tab === 'types'" role="status">{{ offerWarning }} <button @click="loadTypes">Retry offers</button></p>
      <div class="tt-table-wrap price-table-wrap"><table class="tt-table"><thead><tr v-if="tab === 'types'"><th>Therapy Type</th><th>Rate</th><th>Min Price</th><th>Max Price</th><th>Offer Applied</th></tr><tr v-else><th>Plan Name</th><th>Item Code</th><th>Sessions</th><th>Total Amount</th><th>Offer Price</th><th>Incl. GST</th><th>Status</th><th></th></tr></thead><tbody :class="tab === 'types' ? 'tt-tbody' : tab === 'packages' ? 'pkg-tbody' : 'lr-tbody'">
        <tr v-if="loading[tab]"><td :colspan="tab === 'types' ? 5 : 8" class="tt-loading">{{ tab === 'types' ? 'Loading therapy types and current offers…' : 'Loading...' }}</td></tr>
        <template v-else-if="tab === 'types'"><tr v-for="(row,index) in visible" :key="row.therapy_type + '::' + index" :class="index % 2 ? 'tt-row-odd' : 'tt-row-even'"><td class="tt-name"><div class="tt-name-main">{{ row.therapy_type }}</div><div v-if="category(row.healthcare_service_unit)" class="tt-name-category">{{ category(row.healthcare_service_unit) }}</div></td><td><span class="tt-pill tt-pill-rate">{{ money(row.rate) }}</span></td><td><span class="tt-pill tt-pill-min">{{ money(row.minimum_price) }}</span></td><td><span class="tt-pill tt-pill-max">{{ money(row.maximum_price) }}</span></td><td><span class="tt-pill" :class="row.offer ? 'tt-pill-offer-yes' : 'tt-pill-offer-no'">{{ row.offer ? '✅ ' + money(row.offer.rate) : '— No' }}</span></td></tr></template>
        <template v-else><tr v-for="(row,index) in visible" :key="row.name" :class="index % 2 ? 'tt-row-odd' : 'tt-row-even'"><td class="tt-name">{{ row.plan_name }}</td><td>{{ row.item_code || '-' }}</td><td><span class="tt-pill tt-pill-rate">{{ row.total_sessions ?? '-' }}</span></td><td><span class="tt-pill tt-pill-max">{{ money(row.total_amount) }}</span></td><td><span class="tt-pill tt-pill-min">{{ money(row.offer_price) }}</span></td><td>{{ money(row.custom_including_gst) }}</td><td><span class="tt-pill" :class="row.is_active ? 'pkg-pill-active' : 'pkg-pill-inactive'">{{ row.is_active ? 'Active' : 'Inactive' }}</span></td><td><button class="pkg-view-btn" @click="openDetail(row.name)">View</button></td></tr></template>
        <tr v-if="!loading[tab] && !visible.length"><td :colspan="tab === 'types' ? 5 : 8" class="tt-loading">No results found</td></tr>
      </tbody></table></div>
      <div class="tt-pagination price-pagination"><button type="button" class="tt-prev" :disabled="pages[tab] <= 1 || loading[tab]" @click="pages[tab]--">« Prev</button><span class="tt-page-info">Page {{ pages[tab] }} of {{ pageCount }} ({{ filtered.length }} {{ tab === 'types' ? 'items' : 'packages' }})</span><button type="button" class="tt-next" :disabled="pages[tab] >= pageCount || loading[tab]" @click="pages[tab]++">Next »</button></div>
    </div>
    <div v-if="detailName" class="pkg-modal-overlay price-overlay" @click.self="closeDetail"><div class="pkg-modal price-dialog" role="dialog" aria-modal="true" aria-labelledby="tt-package-modal-title"><div class="pkg-modal-head"><h4 id="tt-package-modal-title" class="pkg-modal-title">{{ detailName }}</h4><button type="button" class="pkg-modal-close" aria-label="Close package details" @click="closeDetail">×</button></div><div class="pkg-modal-body"><div v-if="detailBusy" class="tt-loading" role="status">Loading details...</div><p v-if="detailError" class="tt-loading" role="alert">{{ detailError }} <button @click="openDetail(detailName)">Retry</button></p><template v-if="detail"><div class="pkg-detail-grid"><div v-for="[label,value] in [['Item Code',detail.item_code || '-'],['Item Group',detail.item_group || '-'],['HSN/SAC',detail.gst_hsn_code || '-'],['Status',detail.is_active ? 'Active' : 'Inactive'],['Total Sessions',detail.total_sessions ?? '-'],['Total Amount',money(detail.total_amount)],['Offer Price',money(detail.offer_price)],['Incl. GST',money(detail.custom_including_gst)],['Offer Valid From',date(detail.offer_valid_from)],['Offer Valid To',date(detail.offer_valid_to)]]" :key="label"><span class="pkg-detail-label">{{ label }}</span><div>{{ value }}</div></div></div><div v-if="detail.description" class="pkg-desc"><span class="pkg-detail-label">Description</span><div v-html="sanitizeRichText(detail.description)"></div></div><span class="pkg-detail-label" style="margin-top:14px;display:block">Included Therapy Types</span><table class="tt-table" style="margin-top:6px"><thead><tr><th>Therapy Type</th><th>Sessions</th><th>Rate</th><th>Amount</th></tr></thead><tbody><tr v-for="(row,index) in detail.therapy_types || []" :key="row.name || index" :class="index % 2 ? 'tt-row-odd' : 'tt-row-even'"><td>{{ row.therapy_type }}</td><td>{{ row.no_of_sessions ?? '-' }}</td><td>{{ money(row.rate) }}</td><td>{{ money(row.amount) }}</td></tr><tr v-if="!detail.therapy_types?.length"><td colspan="4" class="tt-loading">No therapy types</td></tr></tbody></table></template></div></div></div>
  </section>
</template>

<style>
/*
ERPNext Web Page CSS
LIFE green + white theme, adapted from your reference dashboard.
*/

.navbar { display: none; }
.web-footer { display: none; }

.tt-block,
.tt-block * {
  box-sizing: border-box;
}

.tt-block {
  width: 100%;
  margin: 0 auto;
  padding: 18px;
  color: #152418;
  font-family: "Inter", "Segoe UI", Arial, system-ui, sans-serif;
  font-size: 12px;
  line-height: 1.45;
  background: #F3FAF4;
  border: 1px solid #DCE9DE;
  border-radius: 14px;
  box-shadow:
    0 1px 2px rgba(15, 61, 30, 0.06),
    0 8px 26px rgba(15, 61, 30, 0.09);
}

/* ============================================================
   TABS
   ============================================================ */

.tt-tabs {
  display: flex;
  gap: 6px;
  margin: -18px -18px 18px;
  padding: 10px 16px 0;
  overflow-x: auto;
  background: #FFFFFF;
  border-bottom: 1px solid #DCE9DE;
  border-radius: 14px 14px 0 0;
}

.tt-tab-btn {
  min-height: 40px;
  padding: 0 15px;
  color: #5F6F63;
  font-family: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  background: transparent;
  border: 1px solid transparent;
  border-bottom: 3px solid transparent;
  border-radius: 9px 9px 0 0;
  transition:
    color 0.15s ease,
    background 0.15s ease,
    border-color 0.15s ease;
}

.tt-tab-btn:hover {
  color: #14501F;
  background: #F3FAF4;
}

.tt-tab-btn.active {
  color: #14501F;
  background: #E8F5E9;
  border-color: #DCE9DE;
  border-bottom-color: #2E7D32;
}

/* ============================================================
   PANEL / HEADER / FILTERS
   ============================================================ */

.tt-panel {
  padding: 16px;
  background: #FFFFFF;
  border: 1px solid #DCE9DE;
  border-radius: 14px;
  box-shadow:
    0 1px 2px rgba(15, 61, 30, 0.05),
    0 5px 16px rgba(15, 61, 30, 0.07);
}

.tt-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px dashed #CFE1D2;
}

.tt-header h3 {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
  color: #0F3D1E;
  font-size: 17px;
  font-weight: 900;
  line-height: 1.3;
}

.tt-badge {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 3px 10px;
  color: #FFFFFF;
  font-size: 9.5px;
  font-weight: 800;
  letter-spacing: 0.25px;
  background: #1B5E20;
  border: 1px solid #1B5E20;
  border-radius: 999px;
  box-shadow: 0 2px 6px rgba(27, 94, 32, 0.18);
}

.pkg-badge {
  background: #2E7D32;
  border-color: #2E7D32;
}

.lr-badge {
  color: #5D3A00;
  background: #FFF3CD;
  border-color: #F1D78A;
  box-shadow: none;
}

.tt-filter-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.tt-search,
.pkg-search,
.lr-search {
  width: 250px;
  max-width: 100%;
  height: 36px;
  padding: 0 13px;
  color: #152418;
  font-family: inherit;
  font-size: 11.5px;
  background: #FFFFFF;
  border: 1.5px solid #CFE1D2;
  border-radius: 999px;
  outline: none;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    background 0.15s ease;
}

.tt-search::placeholder,
.pkg-search::placeholder,
.lr-search::placeholder {
  color: #87968B;
}

.tt-search:hover,
.pkg-search:hover,
.lr-search:hover {
  border-color: #A5D6A7;
}

.tt-search:focus,
.pkg-search:focus,
.lr-search:focus {
  background: #FFFFFF;
  border-color: #43A047;
  box-shadow: 0 0 0 3px rgba(67, 160, 71, 0.12);
}

.tt-offer-filter-btn {
  height: 36px;
  padding: 0 14px;
  color: #14501F;
  font-family: inherit;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  background: #FFFFFF;
  border: 1.5px solid #A5D6A7;
  border-radius: 999px;
  transition:
    color 0.15s ease,
    background 0.15s ease,
    border-color 0.15s ease,
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

.tt-offer-filter-btn:hover {
  color: #0F3D1E;
  background: #E8F5E9;
  border-color: #66BB6A;
  box-shadow: 0 0 0 3px rgba(67, 160, 71, 0.10);
  transform: translateY(-1px);
}

.tt-offer-filter-btn.active {
  color: #FFFFFF;
  background: #1B5E20;
  border-color: #1B5E20;
  box-shadow: 0 3px 9px rgba(27, 94, 32, 0.22);
}

/* ============================================================
   TABLE
   ============================================================ */

.tt-table-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid #DCE9DE;
  border-radius: 11px;
}

.tt-table {
  width: 100%;
  min-width: 760px;
  border-collapse: separate;
  border-spacing: 0;
  color: #152418;
  font-size: 11.5px;
  background: #FFFFFF;
}

.tt-table thead tr {
  color: #FFFFFF;
  text-align: left;
  background: #1B5E20;
}

.tt-table th {
  padding: 10px 12px;
  color: #FFFFFF;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.25px;
  white-space: nowrap;
  border-bottom: 1px solid #14501F;
}

.tt-table td {
  padding: 10px 12px;
  vertical-align: middle;
  border-bottom: 1px solid #EEF4EF;
}

.tt-table tbody tr:last-child td {
  border-bottom: 0;
}

.tt-row-even { background: #F8FCF8; }
.tt-row-odd  { background: #FFFFFF; }

.tt-table tbody tr:hover td {
  background: #EEF8EF;
}

.tt-name {
  color: #0F3D1E;
  font-weight: 800;
}

.tt-name-main {
  font-weight: 700;
  color: #152418;
  line-height: 1.35;
}

.tt-name-category {
  margin-top: 2px;
  font-size: 11px;
  font-weight: 500;
  color: #6f7f72;
  line-height: 1.25;
}

/* ============================================================
   PILLS / STATUS
   ============================================================ */

.tt-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 9px;
  font-size: 10.5px;
  font-weight: 800;
  white-space: nowrap;
  border-radius: 999px;
}

.tt-pill-rate {
  color: #14501F;
  background: #E8F5E9;
  border: 1px solid #C8E6C9;
}

.tt-pill-min {
  color: #7A5200;
  background: #FFF8E1;
  border: 1px solid #F3DE9B;
}

.tt-pill-max {
  color: #8F1D1D;
  background: #FDECEA;
  border: 1px solid #F2B8B5;
}

.tt-pill-offer-yes,
.pkg-pill-active {
  color: #14501F;
  background: #E8F5E9;
  border: 1px solid #C8E6C9;
}

.tt-pill-offer-no,
.pkg-pill-inactive {
  color: #637668;
  background: #EEF4EF;
  border: 1px solid #D7E4D9;
}

.tt-loading {
  padding: 22px !important;
  color: #5F6F63;
  font-weight: 600;
  text-align: center;
}

/* ============================================================
   PAGINATION / ACTIONS
   ============================================================ */

.tt-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
}

.tt-pagination button,
.pkg-view-btn {
  min-height: 32px;
  padding: 0 14px;
  color: #FFFFFF;
  font-family: inherit;
  font-size: 10.5px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  background: #1B5E20;
  border: 1px solid #1B5E20;
  border-radius: 999px;
  box-shadow: 0 3px 9px rgba(27, 94, 32, 0.18);
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease,
    opacity 0.15s ease;
}

.tt-pagination button:hover:not(:disabled),
.pkg-view-btn:hover {
  background: #2E7D32;
  border-color: #2E7D32;
  box-shadow: 0 5px 12px rgba(27, 94, 32, 0.24);
  transform: translateY(-1px);
}

.tt-pagination button:disabled {
  opacity: 0.38;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.tt-page-info,
.pkg-page-info,
.lr-page-info {
  color: #5F6F63;
  font-size: 10.5px;
  font-weight: 700;
}

/* ============================================================
   PACKAGE DETAIL MODAL
   ============================================================ */

.pkg-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(15, 61, 30, 0.46);
  backdrop-filter: blur(2px);
}

.pkg-modal {
  width: min(680px, 96vw);
  max-height: 86vh;
  overflow-y: auto;
  background: #FFFFFF;
  border: 1px solid #CFE1D2;
  border-radius: 14px;
  box-shadow: 0 18px 55px rgba(15, 61, 30, 0.28);
}

.pkg-modal-head {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  color: #FFFFFF;
  background: #1B5E20;
  border-bottom: 1px solid #14501F;
  border-radius: 13px 13px 0 0;
}

.pkg-modal-title {
  margin: 0;
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 900;
}

.pkg-modal-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  padding: 0;
  color: #E8F5E9;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.10);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 50%;
}

.pkg-modal-close:hover {
  color: #FFFFFF;
  background: rgba(255, 255, 255, 0.18);
}

.pkg-modal-body {
  padding: 18px;
  overflow-x: auto;
  background: #FFFFFF;
}

.pkg-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
}

.pkg-detail-grid > div {
  min-width: 0;
  padding: 10px 11px;
  background: #F8FCF8;
  border: 1px solid #E2EEE4;
  border-radius: 9px;
}

.pkg-detail-grid > div div {
  margin-top: 3px;
  color: #152418;
  font-size: 11.5px;
  font-weight: 800;
  overflow-wrap: anywhere;
}

.pkg-detail-label {
  display: inline-block;
  color: #35633D;
  font-size: 8.5px;
  font-weight: 900;
  letter-spacing: 0.75px;
  text-transform: uppercase;
}

.pkg-desc {
  margin-top: 14px;
  padding: 11px 12px;
  color: #152418;
  background: #F8FCF8;
  border: 1px solid #E2EEE4;
  border-radius: 9px;
}

.pkg-desc > div {
  margin-top: 4px;
  color: #2D4332;
  font-size: 11.5px;
  font-weight: 500;
  line-height: 1.55;
}

.pkg-modal-body > .tt-table {
  min-width: 600px;
  margin-top: 6px;
}

/* ============================================================
   RESPONSIVE
   ============================================================ */

@media (max-width: 768px) {
  .tt-block {
    padding: 12px;
    border-radius: 10px;
  }

  .tt-tabs {
    margin: -12px -12px 14px;
    padding: 8px 10px 0;
    border-radius: 10px 10px 0 0;
  }

  .tt-panel {
    padding: 12px;
    border-radius: 10px;
  }

  .tt-header {
    align-items: stretch;
  }

  .tt-header h3 {
    width: 100%;
    font-size: 15px;
  }

  .tt-filter-row,
  .tt-search,
  .pkg-search,
  .lr-search {
    width: 100%;
  }

  .tt-offer-filter-btn {
    flex: 1 1 auto;
  }

  .pkg-detail-grid {
    grid-template-columns: 1fr;
  }

  .pkg-modal-overlay {
    padding: 10px;
  }

  .pkg-modal {
    width: 100%;
    max-height: 92vh;
  }
}

</style>
