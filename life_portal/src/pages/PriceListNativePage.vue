<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { billingCall, billingList, getBillingDoc } from '../api/billing';
import { indiaStamp } from '../lib/cc';
import { filterPriceRows, priceListOffer, priceListTabs, splitPackages } from '../lib/price-list';
import '../styles/price-list-native.css';

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
const allTherapies = computed(() => therapies.value.map(row => ({ ...row, offer: priceListOffer(row, rules.value, today) })));
const packageGroups = computed(() => splitPackages(packages.value));
const currentRows = computed(() => tab.value === 'types' ? allTherapies.value : packageGroups.value[tab.value]);
const filtered = computed(() => filterPriceRows(currentRows.value, search[tab.value], tab.value === 'types' && offerOnly.value));
const pageCount = computed(() => Math.max(1, Math.ceil(filtered.value.length / 10)));
const visible = computed(() => filtered.value.slice((pages[tab.value] - 1) * 10, pages[tab.value] * 10));
const money = value => value === null || value === undefined || value === '' ? '—' : new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value));
const date = value => value ? String(value).slice(0, 10).split('-').reverse().join('/') : '—';
const category = value => String(value || '').replace(/\s*-\s*LSACPL\s*$/i, '').trim();

async function listAll(doctype, filters, fields, signal) {
  const rows = [];
  for (let start = 0; start < 10000; start += 100) {
    const batch = await billingList(doctype, filters, fields, { start, limit: 100, order: doctype === 'Therapy Type' ? 'therapy_type asc' : 'plan_name asc', signal });
    rows.push(...batch);
    if (batch.length < 100) return rows;
  }
  throw new Error('Too many price records. Narrow the source data before loading this page.');
}
async function loadTypes() {
  controllers.types?.abort(); const current = new AbortController(); controllers.types = current; const signal = current.signal;
  loading.types = true; errors.types = ''; offerWarning.value = '';
  try {
    therapies.value = (await listAll('Therapy Type', [['is_billable', '=', 1]], ['therapy_type', 'healthcare_service_unit', 'item_code', 'rate', 'minimum_price', 'maximum_price'], signal)).filter(row => Number(row.rate) > 0);
    loaded.types = true;
    try { rules.value = (await billingCall('life_slimming.price_list_api.active_offers', {}, signal)).offers || []; }
    catch (error) { if (!signal.aborted) offerWarning.value = `Current offers could not be loaded: ${error.message}`; }
  } catch (error) { if (!signal.aborted) errors.types = error.message; }
  finally { if (controllers.types === current) loading.types = false; }
}
async function loadPackages() {
  controllers.packages?.abort(); const current = new AbortController(); controllers.packages = current; const signal = current.signal;
  loading.packages = true; loading.liferise = true; errors.packages = ''; errors.liferise = '';
  try {
    packages.value = await listAll('Therapy Plan Template', [['is_active', '=', 1]], ['name', 'plan_name', 'item_code', 'item_group', 'gst_hsn_code', 'description', 'total_sessions', 'total_amount', 'offer_price', 'custom_including_gst', 'is_active', 'offer_valid_from', 'offer_valid_to'], signal);
    loaded.packages = true; loaded.liferise = true;
  } catch (error) { if (!signal.aborted) { errors.packages = error.message; errors.liferise = error.message; } }
  finally { if (controllers.packages === current) { loading.packages = false; loading.liferise = false; } }
}
function ensureLoaded() { if (tab.value === 'types' && !loaded.types && !loading.types) loadTypes(); else if (tab.value !== 'types' && !loaded.packages && !loading.packages) loadPackages(); }
function selectTab(id) { tab.value = id; router.replace({ query: { ...route.query, tab: id } }); ensureLoaded(); }
async function openDetail(name) {
  detailController?.abort(); detailController = new AbortController(); const signal = detailController.signal;
  detailName.value = name; detail.value = null; detailBusy.value = true; detailError.value = '';
  try { const doc = await getBillingDoc('Therapy Plan Template', name); if (alive && !signal.aborted) detail.value = doc; }
  catch (error) { if (alive && !signal.aborted) detailError.value = error.message; }
  finally { if (alive && !signal.aborted) detailBusy.value = false; }
}
function closeDetail() { detailController?.abort(); detailName.value = ''; detail.value = null; detailBusy.value = false; }
function onKeydown(event) { if (event.key === 'Escape' && detailName.value) closeDetail(); }
watch(() => route.query.tab, value => { const next = validTabs.includes(value) ? value : 'types'; if (next !== tab.value) { tab.value = next; ensureLoaded(); } });
watch(() => [search[tab.value], offerOnly.value], () => { pages[tab.value] = 1; });
onMounted(() => { ensureLoaded(); window.addEventListener('keydown', onKeydown); });
onBeforeUnmount(() => { alive = false; controllers.types?.abort(); controllers.packages?.abort(); detailController?.abort(); window.removeEventListener('keydown', onKeydown); });
</script>

<template>
  <section class="price-list-native">
    <header class="price-head"><div><span class="price-eyebrow">STOCK &amp; PURCHASE</span><h1>Price-List</h1><p>Billable therapies, packages and current offers</p></div><button class="price-refresh" :disabled="loading[tab]" @click="tab==='types'?loadTypes():loadPackages()">Refresh</button></header>
    <nav class="price-tabs" aria-label="Price-List views"><button v-for="[id,label] in priceListTabs" :key="id" :aria-current="tab===id?'page':undefined" @click="selectTab(id)">{{ label }}</button></nav>
    <section class="price-panel">
      <header class="price-panel-head"><div><h2>{{ tab==='types'?'Billable Therapy Types':tab==='packages'?'Therapy Plan Templates':'LIFErise Packages' }}</h2><p>{{ filtered.length }} {{ tab==='types'?'therapies':'packages' }}</p></div><div class="price-filters"><label>Search<input v-model="search[tab]" type="search" :placeholder="tab==='types'?'Therapy or category':'Package or item code'"></label><button v-if="tab==='types'" :aria-pressed="offerOnly" @click="offerOnly=!offerOnly">{{ offerOnly?'Offers only ✓':'Offers only' }}</button></div></header>
      <p v-if="errors[tab]" class="price-error" role="alert">{{ errors[tab] }} <button @click="ensureLoaded">Retry</button></p>
      <p v-if="offerWarning && tab==='types'" class="price-warning" role="status">{{ offerWarning }} <button @click="loadTypes">Retry offers</button></p>
      <p v-if="loading[tab]" role="status">Loading {{ tab==='types'?'therapies and offers':'packages' }}…</p>
      <div v-else class="price-table-wrap" tabindex="0" role="region" aria-label="Price list"><table><thead><tr v-if="tab==='types'"><th>Therapy Type</th><th>Rate</th><th>Min Price</th><th>Max Price</th><th>Offer Applied</th></tr><tr v-else><th>Plan Name</th><th>Item Code</th><th>Sessions</th><th>Total Amount</th><th>Offer Price</th><th>Incl. GST</th><th>Status</th><th>Details</th></tr></thead><tbody><template v-if="tab==='types'"><tr v-for="row in visible" :key="row.item_code || row.therapy_type"><td><strong>{{ row.therapy_type }}</strong><small v-if="category(row.healthcare_service_unit)">{{ category(row.healthcare_service_unit) }}</small></td><td>{{ money(row.rate) }}</td><td>{{ money(row.minimum_price) }}</td><td>{{ money(row.maximum_price) }}</td><td><span v-if="row.offer" class="price-pill price-offer" :title="row.offer.name">{{ money(row.offer.rate) }}</span><span v-else>— No</span></td></tr></template><template v-else><tr v-for="row in visible" :key="row.name"><td><strong>{{ row.plan_name }}</strong></td><td>{{ row.item_code || '—' }}</td><td>{{ row.total_sessions ?? '—' }}</td><td>{{ money(row.total_amount) }}</td><td>{{ money(row.offer_price) }}</td><td>{{ money(row.custom_including_gst) }}</td><td><span class="price-pill">{{ row.is_active?'Active':'Inactive' }}</span></td><td><button @click="openDetail(row.name)">View</button></td></tr></template><tr v-if="!visible.length"><td :colspan="tab==='types'?5:8">{{ errors[tab]?'Could not load records.':'No results found.' }}</td></tr></tbody></table></div>
      <footer class="price-pagination"><button :disabled="pages[tab]<=1 || loading[tab]" @click="pages[tab]--">‹ Prev</button><span>Page {{ pages[tab] }} of {{ pageCount }}</span><button :disabled="pages[tab]>=pageCount || loading[tab]" @click="pages[tab]++">Next ›</button></footer>
    </section>
    <div v-if="detailName" class="price-overlay" @click.self="closeDetail"><section class="price-dialog" role="dialog" aria-modal="true" :aria-label="'Package details: '+detailName"><header><h2>{{ detail?.plan_name || detailName }}</h2><button aria-label="Close details" @click="closeDetail">×</button></header><p v-if="detailBusy" role="status">Loading package details…</p><p v-if="detailError" role="alert">{{ detailError }} <button @click="openDetail(detailName)">Retry</button></p><template v-if="detail"><div class="price-detail-grid"><div><span>Item Code</span><strong>{{ detail.item_code || '—' }}</strong></div><div><span>Item Group</span><strong>{{ detail.item_group || '—' }}</strong></div><div><span>HSN/SAC</span><strong>{{ detail.gst_hsn_code || '—' }}</strong></div><div><span>Status</span><strong>{{ detail.is_active?'Active':'Inactive' }}</strong></div><div><span>Total Sessions</span><strong>{{ detail.total_sessions ?? '—' }}</strong></div><div><span>Total Amount</span><strong>{{ money(detail.total_amount) }}</strong></div><div><span>Offer Price</span><strong>{{ money(detail.offer_price) }}</strong></div><div><span>Incl. GST</span><strong>{{ money(detail.custom_including_gst) }}</strong></div><div><span>Offer Valid From</span><strong>{{ date(detail.offer_valid_from) }}</strong></div><div><span>Offer Valid To</span><strong>{{ date(detail.offer_valid_to) }}</strong></div></div><div v-if="detail.description" class="price-description"><strong>Description</strong><p>{{ detail.description }}</p></div><h3>Included Therapy Types</h3><div class="price-table-wrap"><table><thead><tr><th>Therapy Type</th><th>Sessions</th><th>Rate</th><th>Amount</th></tr></thead><tbody><tr v-for="(line,index) in detail.therapy_types || []" :key="line.name || index"><td>{{ line.therapy_type }}</td><td>{{ line.no_of_sessions ?? '—' }}</td><td>{{ money(line.rate) }}</td><td>{{ money(line.amount) }}</td></tr><tr v-if="!detail.therapy_types?.length"><td colspan="4">No therapy types</td></tr></tbody></table></div></template></section></div>
  </section>
</template>
