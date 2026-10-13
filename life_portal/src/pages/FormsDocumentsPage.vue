<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { request } from '../api/http';
import { session } from '../lib/session';


const tabs = [
  { key: 'forms', label: 'Forms', icon: '📋', doctype: 'Forms And Documents', dateField: 'date', childTable: 'forms_and_documents', reportView: true },
  { key: 'sops', label: 'Life Rise SOPs', icon: '📘', doctype: 'Life Rise SOPs', dateField: 'posting_date', childTable: 'forms_and_document', filters: [['docstatus', '=', 1]] },
  { key: 'circular', label: 'Circular', icon: '🔔', doctype: 'Circular', dateField: 'posting_date', childTable: 'documents', filters: [['docstatus', '=', 1]] },
  { key: 'diet', label: 'Diet', icon: '🥗', doctype: 'Diet', dateField: 'posting_date', childTable: 'document', filters: [['docstatus', '=', 0]] },
  { key: 'audit', label: 'Audit', icon: '📝', doctype: 'Audit Forms', dateField: 'posting_date', childTable: 'document', filters: [['docstatus', '=', 0]] },
  { key: 'service', label: 'Certificates', icon: '📜', doctype: 'Service Certificates', dateField: 'date', childTable: 'forms_and_documents', filters: [['docstatus', '=', 1]] },
  { key: 'consent', label: 'Consent Form', icon: '📋', doctype: 'Consent Form', dateField: 'posting_date', childTable: 'forms_and_document', filters: [['docstatus', '=', 1]] },
];
const activeTab = ref('forms'), selectedDoc = ref(null), alive = ref(true);
const state = reactive(Object.fromEntries(tabs.map(tab => [tab.key, { loaded: false, loading: false, error: '', count: 0, files: [], emptyMessage: 'No documents attached.' }])));
const currentTab = computed(() => tabs.find(tab => tab.key === activeTab.value));
const currentState = computed(() => state[activeTab.value]);
const controllers = Object.fromEntries(tabs.map(tab => [tab.key, null]));

async function frappeCall(method, args, signal) {
  const response = await request(method, { args, signal, csrfToken: session.csrf_token });
  return response.message;
}
function reportRows(message) {
  const keys = message?.keys || [], values = message?.values || [];
  return values.map(valuesRow => Object.fromEntries(keys.map((key, index) => [key, valuesRow[index]])));
}
function listArgs(tab) {
  if (tab.reportView) return {
    doctype: tab.doctype,
    fields: [`\`tab${tab.doctype}\`.\`name\``, `\`tab${tab.doctype}\`.\`modified\``, `\`tab${tab.doctype}\`.\`docstatus\``],
    filters: tab.filters || [], order_by: `\`tab${tab.doctype}\`.\`modified\` desc`,
    start: 0, page_length: 200, view: 'List', group_by: null, with_comment_count: 0,
  };
  return { doctype: tab.doctype, fields: ['name', 'modified', 'docstatus'], filters: tab.filters || [], order_by: 'modified desc', limit_start: 0, limit_page_length: 200 };
}
function childRows(doc, preferred) {
  for (const field of [preferred, 'forms_and_documents', 'forms_and_document', 'documents', 'document']) {
    if (Array.isArray(doc?.[field])) return doc[field];
  }
  return [];
}
function fileUrl(row) {
  for (const value of [row?.files, row?.file, row?.file_url, row?.attachment, row?.attach, row?.document, row?.document_file, row?.attach_file]) {
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return '';
}
function titleOf(doc, item) {
  for (const field of ['name1', 'title', 'document_name', 'subject', 'description', 'name']) if (doc?.[field]) return String(doc[field]);
  return item.name || 'Untitled Document';
}
function dateText(value) {
  if (!value) return '';
  const raw = String(value), parts = raw.split(/[ T]/)[0].split('-');
  if (parts.length !== 3) return raw;
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${parts[2]}-${months[Number(parts[1]) - 1] || parts[1]}-${parts[0]}`;
}
async function fullDocsInBatches(items, tab, signal) {
  const documents = [];
  for (let start = 0; start < items.length; start += 8) {
    const batch = await Promise.all(items.slice(start, start + 8).map(async item => {
      try { return await frappeCall('frappe.client.get', { doctype: tab.doctype, name: item.name }, signal); }
      catch (error) { if (error.name === 'AbortError') throw error; return null; }
    }));
    documents.push(...batch);
  }
  return documents;
}
async function loadTab(key, retry = false) {
  const tab = tabs.find(item => item.key === key), target = state[key];
  if (!tab || target.loading || (target.loaded && !retry)) return;
  controllers[key]?.abort();
  const controller = new AbortController(); controllers[key] = controller;
  target.loading = true; target.error = ''; target.count = 0; target.files = [];
  try {
    const response = await frappeCall(tab.reportView ? 'frappe.desk.reportview.get' : 'frappe.client.get_list', listArgs(tab), controller.signal);
    const items = tab.reportView ? reportRows(response) : (response || []);
    target.emptyMessage = items.length ? 'No documents attached.' : 'No documents found.';
    const docs = await fullDocsInBatches(items, tab, controller.signal);
    if (!alive.value || controllers[key] !== controller) return;
    const files = [], parents = new Set();
    docs.forEach((doc, index) => {
      if (!doc) return;
      let parentHasFile = false;
      for (const row of childRows(doc, tab.childTable)) {
        const path = fileUrl(row);
        if (!path) continue;
        parentHasFile = true;
        files.push({ id: `${doc.name || items[index]?.name}-${files.length}`, title: titleOf(doc, items[index] || {}), url: path, date: dateText(doc[tab.dateField] || doc.modified || items[index]?.modified), icon: tab.key === 'forms' ? '📄' : tab.icon });
      }
      if (parentHasFile) parents.add(doc.name || items[index]?.name);
    });
    target.files = files; target.count = parents.size; target.loaded = true;
  } catch (error) {
    if (alive.value && controllers[key] === controller && error.name !== 'AbortError') { target.error = error.message || 'Unable to load documents.'; target.loaded = true; }
  } finally { if (alive.value && controllers[key] === controller) target.loading = false; }
}
function selectTab(key) { activeTab.value = key; loadTab(key); }
function absoluteUrl(path) {
  if (!String(path || '').trim()) return '';
  try { const url = new URL(String(path).trim(), window.location.origin); return ['http:', 'https:'].includes(url.protocol) ? url.href : ''; }
  catch { return ''; }
}
function openDoc(doc) { selectedDoc.value = { title: doc.title, url: absoluteUrl(doc.url) }; }
function closeDoc() { selectedDoc.value = null; }
function openFile() { if (selectedDoc.value?.url) window.open(selectedDoc.value.url, '_blank', 'noopener,noreferrer'); }
function downloadFile() {
  if (!selectedDoc.value?.url) return;
  const url = selectedDoc.value.url;
  let filename = 'document';
  try { filename = decodeURIComponent(url.split(/[?#]/)[0].split('/').pop() || 'document'); } catch { /* Preserve the source's fallback filename. */ }
  const link = document.createElement('a'); link.href = url; link.download = filename; link.rel = 'noopener'; document.body.appendChild(link); link.click(); link.remove();
}
function onKeydown(event) { if (event.key === 'Escape') closeDoc(); }
onMounted(() => { window.addEventListener('keydown', onKeydown); Promise.allSettled(tabs.map(tab => loadTab(tab.key))); });
onBeforeUnmount(() => { alive.value = false; Object.values(controllers).forEach(controller => controller?.abort()); window.removeEventListener('keydown', onKeydown); });
</script>

<template>
  <section id="fad-app" class="forms-documents">
    <div class="fad-shell">
      <div class="fad-hero"><div class="fad-hero-left"><div class="fad-kicker">DOCUMENT MANAGEMENT</div><h1 class="fad-hero-title">Forms &amp; Documents</h1><div class="fad-hero-description">Access company forms, Life Rise SOPs, circulars, diet documents, audit forms, service certificates and consent forms.</div></div><div class="fad-hero-right"><div class="fad-total-box"><div class="fad-total-label">ACTIVE TAB</div><div id="fad-count-badge" class="fad-total-value">{{ currentState.count }} {{ currentState.count === 1 ? 'Document' : 'Documents' }}</div></div></div></div>
      <div class="fad-tabs-wrap"><nav class="fad-tabs" aria-label="Document categories" role="tablist"><button v-for="tab in tabs" :key="tab.key" type="button" class="fad-tab" :class="{'fad-tab-active':activeTab === tab.key}" :data-tab="tab.key" :data-count="state[tab.key].count" role="tab" :aria-selected="activeTab === tab.key" :aria-controls="'fad-panel-' + tab.key" @click="selectTab(tab.key)"><span class="fad-tab-icon">{{ tab.icon }}</span><span>{{ tab.label }}</span><span :id="'fad-pill-' + tab.key" class="fad-tab-pill">{{ state[tab.key].count }}</span></button></nav></div>
      <div class="fad-content"><section v-for="tab in tabs" :id="'fad-panel-' + tab.key" :key="tab.key" class="fad-panel" :class="{'fad-panel-active':activeTab === tab.key}" role="tabpanel" :aria-label="tab.label"><div :id="'fad-' + tab.key + '-grid'" class="fad-grid">
        <div v-if="state[tab.key].loading" class="fad-loading" role="status">Loading {{ tab.key === 'sops' ? 'SOPs' : tab.label.toLowerCase() }}...</div>
        <div v-else-if="state[tab.key].error" class="fad-error" role="alert">Unable to load documents. <button type="button" @click="loadTab(tab.key,true)">Retry</button></div>
        <div v-else-if="!state[tab.key].files.length" class="fad-empty">{{ state[tab.key].emptyMessage }}</div>
        <button v-for="doc in state[tab.key].loading ? [] : state[tab.key].files" :key="doc.id" type="button" class="fad-card" @click="openDoc(doc)"><div class="fad-card-icon">{{ doc.icon }}</div><div class="fad-card-body"><div class="fad-card-title">{{ doc.title }}</div><div class="fad-card-sub">{{ doc.date }}</div></div><div class="fad-card-arrow" aria-hidden="true">›</div></button>
      </div></section></div>
    </div>
    <div v-if="selectedDoc" id="fad-modal-overlay" class="fad-modal-overlay fad-modal-show" @click.self="closeDoc"><section class="fad-modal" role="dialog" aria-modal="true" :aria-label="selectedDoc.title"><button id="fad-modal-close" type="button" class="fad-modal-close" aria-label="Close document actions" @click="closeDoc">×</button><div class="fad-modal-icon">📄</div><div id="fad-modal-title" class="fad-modal-title">{{ selectedDoc.title }}</div><div class="fad-modal-sub">Choose what you want to do with this document.</div><div class="fad-modal-actions"><button id="fad-open-document" type="button" class="fad-action fad-action-open" :disabled="!selectedDoc.url" @click="openFile">↗ Open / Print</button><button id="fad-download-document" type="button" class="fad-action fad-action-download" :disabled="!selectedDoc.url" @click="downloadFile">↓ Download</button></div></section></div>
  </section>
</template>

<style scoped>
#fad-app {

    --fad-dark-green: #005638;
    --fad-dark-green-2: #064a32;

    --fad-green: #087648;
    --fad-green-hover: #0a8652;

    --fad-green-light: #e7f4ec;
    --fad-green-light-2: #d6ebdf;

    --fad-gold: #b98508;
    --fad-gold-dark: #976e05;

    --fad-bg: #f3f0e8;
    --fad-bg-soft: #f8f6f1;

    --fad-white: #ffffff;

    --fad-text: #163a2d;
    --fad-muted: #6e8177;

    --fad-border: #d9d2c4;

    --fad-shadow:
        0 3px 12px
        rgba(26, 65, 47, 0.08);

    width: 100%;
    min-height: 100vh;

    margin: 0;
    padding: 0;

    background:
        linear-gradient(
            180deg,
            #f7f5ef 0%,
            #efede6 100%
        );

    color: var(--fad-text);

    font-family:
        "DM Sans",
        "Inter",
        "Segoe UI",
        Arial,
        sans-serif;
}


/* universal sizing */
#fad-app *,
#fad-app *::before,
#fad-app *::after {
    box-sizing: border-box;
}


/* =========================================================
   MAIN SHELL
========================================================= */

#fad-app .fad-shell {
    width: 100%;
    min-height: 100vh;

    margin: 0;

    padding:
        16px
        18px
        32px;

    background:
        linear-gradient(
            180deg,
            #f6f4ee 0%,
            #efede6 100%
        );
}


/* =========================================================
   HERO / PAGE TITLE CARD
========================================================= */

#fad-app .fad-hero {

    width: 100%;

    display: flex;
    align-items: center;
    justify-content: space-between;

    gap: 20px;

    padding:
        20px
        22px;

    margin:
        0
        0
        15px;

    background: #ffffff;

    border:
        1px solid
        var(--fad-border);

    border-left:
        5px solid
        var(--fad-green);

    border-radius: 15px;

    box-shadow:
        var(--fad-shadow);
}


#fad-app .fad-hero-left {
    flex: 1;
    min-width: 0;
}


#fad-app .fad-hero-right {
    flex: 0 0 auto;
}


/* DOCUMENT MANAGEMENT */
#fad-app .fad-kicker {

    margin-bottom: 7px;

    color: var(--fad-gold);

    font-size: 11px;

    font-weight: 900;

    letter-spacing: 3px;

    text-transform: uppercase;
}


/* Forms & Documents */
#fad-app .fad-hero-title {

    margin:
        0
        0
        6px;

    padding: 0;

    color: #003d2a;

    font-size: 30px;

    line-height: 1.08;

    font-weight: 900;

    letter-spacing: -0.7px;
}


#fad-app .fad-hero-description {

    max-width: 980px;

    color: var(--fad-muted);

    font-size: 13px;

    line-height: 1.55;
}


/* =========================================================
   ACTIVE TAB COUNT
========================================================= */

#fad-app .fad-total-box {

    min-width: 170px;

    padding:
        13px
        17px;

    text-align: center;

    background:
        linear-gradient(
            180deg,
            #fffdf7 0%,
            #f7f2e5 100%
        );

    border:
        1px solid
        #dbd1bd;

    border-radius: 11px;
}


#fad-app .fad-total-label {

    color: #7c725e;

    font-size: 9px;

    font-weight: 900;

    letter-spacing: 1.5px;

    text-transform: uppercase;
}


#fad-app .fad-total-value {

    margin-top: 5px;

    color: var(--fad-dark-green);

    font-size: 15px;

    font-weight: 900;
}


/* =========================================================
   TABS WRAPPER
========================================================= */

#fad-app .fad-tabs-wrap {

    width: 100%;

    margin-bottom: 15px;

    padding: 7px;

    background: #ffffff;

    border:
        1px solid
        var(--fad-border);

    border-radius: 13px;

    box-shadow:
        var(--fad-shadow);
}


/* =========================================================
   TABS
========================================================= */

#fad-app .fad-tabs {

    display: flex;
    align-items: center;

    gap: 7px;

    width: 100%;

    overflow-x: auto;
    overflow-y: hidden;

    scrollbar-width: thin;

    -webkit-overflow-scrolling:
        touch;
}


#fad-app .fad-tab {

    appearance: none;
    -webkit-appearance: none;

    flex:
        0
        0
        auto;

    min-height: 40px;

    display: inline-flex;
    align-items: center;
    justify-content: center;

    gap: 7px;

    padding:
        9px
        14px;

    border:
        1px solid
        transparent;

    outline: none;

    border-radius: 9px;

    background:
        transparent;

    color: #51695c;

    font-family: inherit;

    font-size: 12px;

    font-weight: 800;

    line-height: 1;

    white-space: nowrap;

    cursor: pointer;

    transition:
        background 0.18s ease,
        color 0.18s ease,
        border-color 0.18s ease,
        box-shadow 0.18s ease,
        transform 0.18s ease;
}


#fad-app .fad-tab:hover {

    color:
        var(--fad-green);

    background:
        #edf7f1;

    border-color:
        #d4e8dc;
}


#fad-app .fad-tab:focus {
    outline: none;
}


/* ACTIVE TAB */
#fad-app .fad-tab.fad-tab-active {

    color: #ffffff;

    background:
        linear-gradient(
            135deg,
            #087648 0%,
            #005638 100%
        );

    border-color:
        transparent;

    box-shadow:
        0 4px 10px
        rgba(0, 85, 52, 0.2);
}


/* tab emoji */
#fad-app .fad-tab-icon {

    display: inline-flex;

    align-items: center;
    justify-content: center;

    font-size: 14px;

    line-height: 1;
}


/* count */
#fad-app .fad-tab-pill {

    min-width: 23px;

    padding:
        2px
        7px;

    text-align: center;

    border-radius: 999px;

    background:
        rgba(
            255,
            255,
            255,
            0.18
        );

    color: inherit;

    font-size: 10px;

    font-weight: 900;

    line-height: 1.3;
}


/* inactive count */
#fad-app
.fad-tab:not(.fad-tab-active)
.fad-tab-pill {

    color:
        var(--fad-green);

    background:
        #e5f2ea;
}


/* =========================================================
   CONTENT
========================================================= */

#fad-app .fad-content {

    width: 100%;

    margin: 0;

    padding: 0;
}


/* =========================================================
   PANELS
========================================================= */

#fad-app .fad-panel {

    display: none;

    width: 100%;
}


#fad-app .fad-panel.fad-panel-active {

    display: block;
}


/* =========================================================
   DOCUMENT GRID
========================================================= */

#fad-app .fad-grid {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fill,
            minmax(
                270px,
                1fr
            )
        );

    gap: 13px;

    width: 100%;
}


/* =========================================================
   DOCUMENT CARD
========================================================= */

#fad-app .fad-card {

    position: relative;

    min-width: 0;

    display: flex;
    align-items: center;

    gap: 13px;

    padding:
        15px
        15px;

    background:
        #ffffff;

    border:
        1px solid
        var(--fad-border);

    border-left:
        4px solid
        var(--fad-green);

    border-radius:
        12px;

    cursor: pointer;

    box-shadow:
        var(--fad-shadow);

    transition:
        transform 0.18s ease,
        box-shadow 0.18s ease,
        border-color 0.18s ease;
}


#fad-app .fad-card:hover {

    transform:
        translateY(-2px);

    border-color:
        #b8cbbf;

    border-left-color:
        var(--fad-green-hover);

    box-shadow:
        0 8px 22px
        rgba(
            16,
            77,
            49,
            0.12
        );
}


/* =========================================================
   CARD ICON
========================================================= */

#fad-app .fad-card-icon {

    width: 46px;
    height: 46px;

    flex:
        0
        0
        46px;

    display: flex;

    align-items: center;
    justify-content: center;

    background:
        linear-gradient(
            135deg,
            #e8f5ed 0%,
            #d5ecdd 100%
        );

    border:
        1px solid
        #d8eadf;

    border-radius:
        10px;

    font-size:
        22px;

    line-height:
        1;
}


/* =========================================================
   CARD CONTENT
========================================================= */

#fad-app .fad-card-body {

    flex: 1;

    min-width: 0;
}


#fad-app .fad-card-title {

    overflow: hidden;

    color:
        #18392c;

    font-size:
        13px;

    font-weight:
        900;

    line-height:
        1.35;

    white-space:
        nowrap;

    text-overflow:
        ellipsis;
}


#fad-app .fad-card-sub {

    margin-top:
        4px;

    overflow: hidden;

    color:
        #809087;

    font-size:
        11px;

    font-weight:
        600;

    line-height:
        1.35;

    white-space:
        nowrap;

    text-overflow:
        ellipsis;
}


/* =========================================================
   CARD ARROW
========================================================= */

#fad-app .fad-card-arrow {

    flex:
        0
        0
        auto;

    color:
        #afbeb5;

    font-size:
        22px;

    font-weight:
        300;

    line-height:
        1;

    transition:
        color 0.18s ease,
        transform 0.18s ease;
}


#fad-app .fad-card:hover
.fad-card-arrow {

    color:
        var(--fad-green);

    transform:
        translateX(3px);
}


/* =========================================================
   DOCUMENT TITLE TOOLTIP
========================================================= */

#fad-app .fad-card::after {

    content:
        attr(data-title);

    position:
        absolute;

    left:
        14px;

    bottom:
        calc(
            100% + 8px
        );

    z-index:
        9999;

    width:
        max-content;

    max-width:
        330px;

    padding:
        8px
        10px;

    background:
        #17392b;

    color:
        #ffffff;

    border-radius:
        8px;

    box-shadow:
        0 8px 22px
        rgba(
            0,
            0,
            0,
            0.2
        );

    font-size:
        11px;

    font-weight:
        600;

    line-height:
        1.4;

    white-space:
        normal;

    opacity:
        0;

    visibility:
        hidden;

    pointer-events:
        none;

    transform:
        translateY(4px);

    transition:
        opacity 0.15s ease,
        visibility 0.15s ease,
        transform 0.15s ease;
}


#fad-app .fad-card:hover::after {

    opacity: 1;

    visibility:
        visible;

    transform:
        translateY(0);
}


/* =========================================================
   LOADING / EMPTY / ERROR
========================================================= */

#fad-app .fad-loading,
#fad-app .fad-empty,
#fad-app .fad-error {

    grid-column:
        1 / -1;

    width: 100%;

    padding:
        38px
        20px;

    text-align:
        center;

    border:
        1px solid
        var(--fad-border);

    border-radius:
        12px;

    background:
        #ffffff;

    box-shadow:
        var(--fad-shadow);

    font-size:
        13px;

    font-weight:
        600;
}


#fad-app .fad-loading {

    color:
        #778a7f;
}


#fad-app .fad-empty {

    color:
        #778a7f;
}


#fad-app .fad-error {

    color:
        #b72c2c;

    background:
        #fff6f6;

    border-color:
        #efcccc;
}


/* =========================================================
   MODAL OVERLAY
========================================================= */

#fad-app .fad-modal-overlay {

    position:
        fixed;

    inset:
        0;

    z-index:
        9999999;

    display:
        none;

    align-items:
        center;

    justify-content:
        center;

    padding:
        20px;

    background:
        rgba(
            8,
            38,
            26,
            0.55
        );

    backdrop-filter:
        blur(3px);

    -webkit-backdrop-filter:
        blur(3px);
}


#fad-app
.fad-modal-overlay.fad-modal-show {

    display:
        flex;
}


/* =========================================================
   MODAL
========================================================= */

#fad-app .fad-modal {

    position:
        relative;

    width:
        100%;

    max-width:
        460px;

    padding:
        30px
        24px
        24px;

    background:
        #ffffff;

    border:
        1px solid
        #d6cec0;

    border-radius:
        16px;

    text-align:
        center;

    box-shadow:
        0 25px 70px
        rgba(
            0,
            0,
            0,
            0.28
        );

    animation:
        fadModalIn
        0.18s
        ease-out;
}


@keyframes fadModalIn {

    from {

        opacity:
            0;

        transform:
            translateY(10px)
            scale(0.98);
    }

    to {

        opacity:
            1;

        transform:
            translateY(0)
            scale(1);
    }

}


/* =========================================================
   MODAL CLOSE
========================================================= */

#fad-app .fad-modal-close {

    position:
        absolute;

    top:
        11px;

    right:
        12px;

    width:
        34px;

    height:
        34px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    padding:
        0;

    border:
        0;

    border-radius:
        50%;

    outline:
        none;

    background:
        #edf2ee;

    color:
        #52655b;

    font-family:
        inherit;

    font-size:
        23px;

    font-weight:
        400;

    line-height:
        1;

    cursor:
        pointer;
}


#fad-app .fad-modal-close:hover {

    color:
        #17382b;

    background:
        #dfe8e2;
}


/* =========================================================
   MODAL DOCUMENT ICON
========================================================= */

#fad-app .fad-modal-icon {

    width:
        68px;

    height:
        68px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    margin:
        0
        auto
        16px;

    background:
        linear-gradient(
            135deg,
            #e7f4ec 0%,
            #d4eadc 100%
        );

    border:
        1px solid
        #cee4d6;

    border-radius:
        50%;

    font-size:
        31px;
}


/* =========================================================
   MODAL TITLE
========================================================= */

#fad-app .fad-modal-title {

    color:
        #16382c;

    font-size:
        18px;

    font-weight:
        900;

    line-height:
        1.35;

    word-break:
        break-word;
}


#fad-app .fad-modal-sub {

    margin-top:
        7px;

    color:
        #73857b;

    font-size:
        12px;

    line-height:
        1.5;
}


/* =========================================================
   MODAL BUTTONS
========================================================= */

#fad-app .fad-modal-actions {

    display:
        flex;

    align-items:
        stretch;

    gap:
        11px;

    margin-top:
        23px;
}


#fad-app .fad-action {

    flex:
        1;

    min-height:
        43px;

    display:
        inline-flex;

    align-items:
        center;

    justify-content:
        center;

    gap:
        7px;

    padding:
        11px
        16px;

    border:
        0;

    border-radius:
        10px;

    outline:
        none;

    color:
        #ffffff;

    font-family:
        inherit;

    font-size:
        12px;

    font-weight:
        900;

    line-height:
        1.2;

    cursor:
        pointer;

    transition:
        transform 0.15s ease,
        box-shadow 0.15s ease,
        filter 0.15s ease;
}


#fad-app .fad-action:hover {

    transform:
        translateY(-1px);

    filter:
        brightness(1.03);
}


#fad-app .fad-action:active {

    transform:
        translateY(0);
}


/* Open button */
#fad-app .fad-action-open {

    background:
        linear-gradient(
            135deg,
            #087648 0%,
            #005638 100%
        );

    box-shadow:
        0 4px 10px
        rgba(
            0,
            85,
            52,
            0.18
        );
}


/* Download button */
#fad-app .fad-action-download {

    background:
        linear-gradient(
            135deg,
            #bf8c12 0%,
            #9c7003 100%
        );

    box-shadow:
        0 4px 10px
        rgba(
            156,
            112,
            3,
            0.18
        );
}


/* =========================================================
   SCROLLBAR
========================================================= */

#fad-app .fad-tabs::-webkit-scrollbar {

    height:
        5px;
}


#fad-app .fad-tabs::-webkit-scrollbar-track {

    background:
        transparent;
}


#fad-app .fad-tabs::-webkit-scrollbar-thumb {

    background:
        #c5d3ca;

    border-radius:
        999px;
}


/* =========================================================
   TABLET
========================================================= */

@media (
    max-width:
    900px
) {

    #fad-app .fad-shell {

        padding:
            14px
            14px
            28px;
    }


    #fad-app .fad-hero {

        align-items:
            flex-start;

        padding:
            18px;
    }


    #fad-app .fad-hero-title {

        font-size:
            26px;
    }


    #fad-app .fad-grid {

        grid-template-columns:
            repeat(
                auto-fill,
                minmax(
                    230px,
                    1fr
                )
            );
    }

}


/* =========================================================
   MOBILE
========================================================= */

@media (
    max-width:
    650px
) {

    #fad-app .fad-shell {

        padding:
            12px
            12px
            24px;
    }


    #fad-app .fad-hero {

        flex-direction:
            column;

        align-items:
            stretch;

        gap:
            15px;

        padding:
            17px;

        border-left-width:
            4px;
    }


    #fad-app .fad-hero-title {

        font-size:
            23px;

        letter-spacing:
            -0.3px;
    }


    #fad-app .fad-hero-description {

        font-size:
            12px;
    }


    #fad-app .fad-total-box {

        width:
            100%;

        min-width:
            0;
    }


    #fad-app .fad-tabs-wrap {

        padding:
            6px;
    }


    #fad-app .fad-tab {

        min-height:
            38px;

        padding:
            8px
            11px;

        font-size:
            11px;
    }


    #fad-app .fad-grid {

        grid-template-columns:
            1fr;

        gap:
            10px;
    }


    #fad-app .fad-card {

        padding:
            13px;

        gap:
            11px;
    }


    #fad-app .fad-card-icon {

        width:
            42px;

        height:
            42px;

        flex-basis:
            42px;

        font-size:
            20px;
    }


    #fad-app .fad-modal {

        padding:
            28px
            17px
            18px;
    }


    #fad-app .fad-modal-actions {

        flex-direction:
            column;
    }

}


/* =========================================================
   VERY SMALL DEVICES
========================================================= */

@media (
    max-width:
    380px
) {

    #fad-app .fad-hero-title {

        font-size:
            21px;
    }


    #fad-app .fad-kicker {

        font-size:
            9px;

        letter-spacing:
            2px;
    }


    #fad-app .fad-card-title {

        font-size:
            12px;
    }

}
.fad-card{font:inherit;text-align:left}
</style>
