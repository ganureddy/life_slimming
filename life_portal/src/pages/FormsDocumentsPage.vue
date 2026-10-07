<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { request } from '../api/http';
import { session } from '../lib/session';
import '../styles/forms-documents.css';

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
const state = reactive(Object.fromEntries(tabs.map(tab => [tab.key, { loaded: false, loading: false, error: '', count: 0, files: [] }])));
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
  target.loading = true; target.error = '';
  try {
    const response = await frappeCall(tab.reportView ? 'frappe.desk.reportview.get' : 'frappe.client.get_list', listArgs(tab), controller.signal);
    const items = tab.reportView ? reportRows(response) : (response || []);
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
        files.push({ id: `${doc.name || items[index]?.name}-${files.length}`, title: titleOf(doc, items[index] || {}), url: path, date: dateText(doc[tab.dateField] || doc.modified || items[index]?.modified), icon: tab.icon });
      }
      if (parentHasFile) parents.add(doc.name || items[index]?.name);
    });
    target.files = files; target.count = parents.size; target.loaded = true;
  } catch (error) {
    if (alive.value && controllers[key] === controller && error.name !== 'AbortError') target.error = error.message || 'Unable to load documents.';
  } finally { if (alive.value && controllers[key] === controller) target.loading = false; }
}
function selectTab(key) { activeTab.value = key; loadTab(key); }
function absoluteUrl(path) {
  try { return new URL(path, window.location.origin).href; }
  catch { return ''; }
}
function openDoc(doc) { selectedDoc.value = { title: doc.title, url: absoluteUrl(doc.url) }; }
function closeDoc() { selectedDoc.value = null; }
function openFile() { if (selectedDoc.value?.url) window.open(selectedDoc.value.url, '_blank', 'noopener,noreferrer'); }
function downloadFile() {
  if (!selectedDoc.value?.url) return;
  const url = selectedDoc.value.url, filename = decodeURIComponent(url.split(/[?#]/)[0].split('/').pop() || 'document');
  const link = document.createElement('a'); link.href = url; link.download = filename; link.rel = 'noopener'; document.body.appendChild(link); link.click(); link.remove();
}
function onKeydown(event) { if (event.key === 'Escape') closeDoc(); }
onMounted(() => { window.addEventListener('keydown', onKeydown); loadTab('forms'); });
onBeforeUnmount(() => { alive.value = false; Object.values(controllers).forEach(controller => controller?.abort()); window.removeEventListener('keydown', onKeydown); });
</script>

<template>
  <section class="forms-documents">
    <header class="fd-hero"><div><span class="fd-kicker">DOCUMENT MANAGEMENT</span><h1>Forms &amp; Documents</h1><p>Access company forms, Life Rise SOPs, circulars, diet documents, audit forms, service certificates and consent forms.</p></div><div class="fd-total"><small>ACTIVE TAB</small><strong>{{ currentState.loading ? 'Loading…' : `${currentState.count} ${currentState.count===1?'Document':'Documents'}` }}</strong></div></header>
    <nav class="fd-tabs" aria-label="Document categories" role="tablist"><button v-for="tab in tabs" :key="tab.key" role="tab" :aria-selected="activeTab===tab.key" :aria-controls="`fd-panel-${tab.key}`" :class="{active:activeTab===tab.key}" @click="selectTab(tab.key)"><span>{{ tab.icon }}</span>{{ tab.label }}<b>{{ state[tab.key].loaded ? state[tab.key].count : '…' }}</b></button></nav>
    <section :id="`fd-panel-${activeTab}`" class="fd-panel" role="tabpanel" :aria-label="currentTab.label">
      <div v-if="currentState.loading" class="fd-message" role="status"><i class="fd-spinner"></i>Loading {{ currentTab.label.toLowerCase() }}…</div>
      <div v-else-if="currentState.error" class="fd-message fd-error" role="alert">{{ currentState.error }} <button @click="loadTab(activeTab,true)">Retry</button></div>
      <div v-else-if="!currentState.files.length" class="fd-message">No documents attached.</div>
      <div v-else class="fd-grid"><button v-for="doc in currentState.files" :key="doc.id" class="fd-card" @click="openDoc(doc)"><span class="fd-icon">{{ doc.icon }}</span><span class="fd-card-copy"><strong>{{ doc.title }}</strong><small>{{ doc.date || 'Date unavailable' }}</small></span><span class="fd-arrow" aria-hidden="true">›</span></button></div>
    </section>
    <div v-if="selectedDoc" class="fd-backdrop" @click.self="closeDoc"><section class="fd-dialog" role="dialog" aria-modal="true" :aria-label="selectedDoc.title"><button class="fd-close" aria-label="Close document actions" @click="closeDoc">×</button><span class="fd-dialog-icon">📄</span><h2>{{ selectedDoc.title }}</h2><p>Choose what you want to do with this document.</p><div class="fd-dialog-actions"><button @click="openFile">↗ Open / Print</button><button @click="downloadFile">↓ Download</button></div></section></div>
  </section>
</template>
