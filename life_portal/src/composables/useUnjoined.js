import { computed, onBeforeUnmount, reactive, ref, watch, toRaw } from 'vue';
import data from '../data/unjoined.json';
import { request } from '../api/http';
import { session as portalSession } from '../lib/session';
import { FORM_DOCTYPE, sectionFilters, sectionSearch, indiaDate, displayValue, phoneField, followDocument } from '../lib/unjoined';

export function useUnjoined() {
  const sections = data.sections;
  const filters = reactive({ from: '', to: '', branch: '', basis: 'business', followStatus: '', search: '' });
  const applied = ref(null), branches = ref([]), manager = ref(false), busy = ref(false), loaded = ref(false), notice = ref('');
  const records = reactive(Object.fromEntries(sections.map(section => [section.key, { rows: [], count: 0, page: 0, error: '' }])));
  const followups = reactive(new Map());
  const detail = reactive({ open: false, busy: false, tab: 'record', parts: [], warning: '', error: '', context: null });
  const draft = reactive({}), dirty = ref(false), saving = ref(false), saveNotice = ref(''), photo = ref(null), legacyChoice = ref('');
  let generation = 0, detailGeneration = 0, disposed = false;
  const controllers = new Set();
  const canOutput = computed(() => loaded.value && !busy.value);
  const cachedKey = (section, name) => section.dt + '\n' + name;
  async function api(method, args) {
    const controller = new AbortController();
    controllers.add(controller);
    try {
      const result = await request(method, { args, csrfToken: portalSession.csrf_token, signal: controller.signal });
      if (result.exc) throw new Error('ERP request failed.');
      return result.message;
    } finally { controllers.delete(controller); }
  }
  watch(filters, () => { loaded.value = false; notice.value = 'Filters changed. Click Apply to refresh data.'; });
  const show = (field, value) => displayValue(field, value, manager.value);
  const abortReads = () => { for (const controller of controllers) controller.abort(); };

  async function readPage(section, token = generation) {
    const state = records[section.key], criteria = applied.value;
    const args = { doctype: section.dt, filters: sectionFilters(section, criteria), or_filters: sectionSearch(section, criteria) };
    try {
      const [rows, counts] = await Promise.all([
        api('frappe.client.get_list', { ...args, fields: section.fields, limit_start: state.page * 20, limit_page_length: 20, order_by: 'creation desc, name desc' }),
        api('frappe.client.get_list', { ...args, fields: ['count(name) as total'], limit_page_length: 1 }),
      ]);
      if (disposed || token !== generation) return;
      state.rows = rows || []; state.count = Number(counts?.[0]?.total) || 0; state.error = '';
      if (section.dt !== FORM_DOCTYPE && state.rows.length) {
        try {
          const forms = await api('frappe.client.get_list', { doctype: FORM_DOCTYPE, filters: { custom_source_doctype: section.dt, custom_source_document: ['in', rows.map(row => row.name)] }, fields: ['name', 'custom_source_document', 'custom_client_photo_attach', 'status'], limit_page_length: 100 });
          if (!disposed && token === generation) for (const form of forms || []) followups.set(cachedKey(section, form.custom_source_document), form);
        } catch (error) { if (error.name === 'AbortError') throw error; }
      }
    } catch (error) {
      if (disposed || token !== generation || error.name === 'AbortError') return;
      state.rows = []; state.count = 0; state.error = error.message;
    }
  }

  async function load() {
    if (busy.value) return;
    if (filters.from && filters.to && filters.from > filters.to) { notice.value = 'From date must be before To date.'; return; }
    const token = ++generation;
    busy.value = true; loaded.value = false; notice.value = 'Loading permitted ERP records…';
    applied.value = { ...filters }; followups.clear();
    for (const state of Object.values(records)) state.page = 0;
    try {
      await Promise.all(sections.map(section => readPage(section, token)));
      if (disposed || token !== generation) return;
      loaded.value = true;
      notice.value = 'Loaded ' + new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: true }) + '. Counts are section-wise; the same person may have a Client and Lead record. ' + (Object.values(records).some(state => state.error) ? 'Some sections could not be read; see their errors.' : '');
    } finally { if (!disposed && token === generation) busy.value = false; }
  }

  async function paginate(section, direction) {
    if (busy.value || !loaded.value) return;
    const state = records[section.key], next = state.page + direction;
    if (next < 0 || next * 20 >= state.count) return;
    state.page = next; busy.value = true;
    try { await readPage(section); } finally { if (!disposed) busy.value = false; }
  }

  async function initialize() {
    // Roles originate from the authenticated bootstrap; failures keep numbers masked.
    manager.value = Array.isArray(portalSession.roles) && portalSession.roles.includes('System Manager');
    // The branch selector is independent of the record filters. Start records
    // immediately so a slow master list cannot delay the primary table.
    const initialLoad = load();
    try {
      const rows = await api('frappe.client.get_list', { doctype: 'Branch', fields: ['name'], limit_page_length: 1000, order_by: 'name asc' });
      if (disposed) return;
      branches.value = (rows || []).filter(branch => branch.name !== 'Testing Branch').map(branch => branch.name);
    } catch (error) { if (disposed) return; notice.value = 'Branch list unavailable: ' + error.message; }
    await initialLoad;
  }

  function resetDraft(context) {
    const original = context.form || context.defaults;
    for (const key of Object.keys(draft)) delete draft[key];
    for (const field of data.followFields) draft[field.fieldname] = show(field.fieldname, original[field.fieldname] ?? '');
    dirty.value = false; photo.value = null;
    saveNotice.value = context.lookupError ? 'Record lookup failed; saving is blocked until reloaded.' : context.form ? 'Ready to edit' : 'Not saved yet';
  }

  async function findFollowup(section, source) {
    const context = { section, source, form: null, defaults: {
      client_name: source[section.name] || source.name, branch: source[section.branch] || source.branch_name || '', contact_number: source[section.mobile] || source.mobile || source.phone || '',
      treatment: source[section.category] || '', visited_date: ['clients', 'leads'].includes(section.key) ? String(source[section.date] || '').slice(0, 10) : '', status: '', remarks: '', follow_up: '', calling_date: indiaDate(),
    }, legacy: [], lookupError: '' };
    if (section.dt === FORM_DOCTYPE) { context.form = source; return context; }
    try {
      const matches = await api('frappe.client.get_list', { doctype: FORM_DOCTYPE, filters: { custom_source_doctype: section.dt, custom_source_document: source.name }, fields: ['name'], limit_page_length: 2 });
      if (matches.length > 1) throw new Error('Multiple follow-up records link to this source. Resolve them in ERP before editing.');
      if (matches.length) context.form = await api('frappe.client.get', { doctype: FORM_DOCTYPE, name: matches[0].name });
      else if (context.defaults.contact_number && context.defaults.branch) context.legacy = (await api('frappe.client.get_list', { doctype: FORM_DOCTYPE, filters: { contact_number: context.defaults.contact_number, branch: context.defaults.branch }, fields: ['name', 'client_name', 'custom_source_doctype', 'custom_source_document'], limit_page_length: 100 })).filter(row => !row.custom_source_document);
    } catch (error) { context.lookupError = 'Follow-up record lookup failed: ' + error.message; }
    return context;
  }

  async function attachments(doctype, doc) {
    const direct = (data.meta[doctype] || []).filter(field => /Attach/.test(field.fieldtype) && doc[field.fieldname]).map(field => ({ file_name: field.label || field.fieldname, file_url: doc[field.fieldname] }));
    let rows = [], error = '';
    try { rows = await api('frappe.client.get_list', { doctype: 'File', filters: { attached_to_doctype: doctype, attached_to_name: doc.name }, fields: ['name', 'file_name', 'file_url'], limit_page_length: 1000 }); }
    catch (failure) { error = 'Attachments could not be listed: ' + failure.message; }
    const seen = new Set();
    return { files: [...direct, ...(rows || [])].filter(file => { if (seen.has(file.file_url)) return false; seen.add(file.file_url); return true; }), attachmentError: error };
  }

  async function openDetail(section, name, tab = 'record') {
    if (saving.value || (dirty.value && !window.confirm('Discard unsaved follow-up changes?'))) return;
    const token = ++detailGeneration;
    Object.assign(detail, { open: true, busy: true, tab, parts: [], warning: '', error: '', context: null });
    dirty.value = false; legacyChoice.value = '';
    try {
      const source = await api('frappe.client.get', { doctype: section.dt, name });
      const context = await findFollowup(section, source);
      if (disposed || token !== detailGeneration) return;
      detail.context = context; resetDraft(context);
      const parts = [{ doctype: section.dt, doc: source }], warning = [];
      async function linkedPatient(id) {
        try { parts.push({ doctype: 'Patient', doc: await api('frappe.client.get', { doctype: 'Patient', name: id }) }); }
        catch (error) { warning.push('Linked client could not be read: ' + error.message); }
      }
      if (section.dt === 'Patient Appointment' && source.patient) await linkedPatient(source.patient);
      if (section.dt === 'Lead') {
        try {
          const patients = await api('frappe.client.get_list', { doctype: 'Patient', filters: { custom_lead: name }, fields: ['name'], limit_page_length: 100 });
          for (const patient of patients) await linkedPatient(patient.name);
        } catch (error) { warning.push('Linked clients could not be read: ' + error.message); }
      }
      if (section.dt === FORM_DOCTYPE && source.custom_linked_client) await linkedPatient(source.custom_linked_client);
      if (section.dt !== FORM_DOCTYPE && context.form) parts.push({ doctype: FORM_DOCTYPE, doc: context.form });
      const prepared = await Promise.all(parts.map(async part => ({ ...part, ...await attachments(part.doctype, part.doc) })));
      if (!disposed && token === detailGeneration) { detail.parts = prepared; detail.warning = warning.join(' '); }
    } catch (error) { if (!disposed && token === detailGeneration && error.name !== 'AbortError') detail.error = error.message; }
    finally { if (!disposed && token === detailGeneration) detail.busy = false; }
  }

  function closeDetail() {
    if (saving.value || (dirty.value && !window.confirm('Discard unsaved follow-up changes?'))) return false;
    detailGeneration++; detail.open = false; detail.context = null; dirty.value = false; return true;
  }

  async function chooseLegacy(name) {
    if (saving.value || !detail.context || !name) return;
    if (dirty.value && !window.confirm('Discard unsaved changes and load this existing form?')) { legacyChoice.value = ''; return; }
    const token = detailGeneration, context = detail.context;
    try {
      const form = await api('frappe.client.get', { doctype: FORM_DOCTYPE, name });
      if (!disposed && token === detailGeneration) { context.form = form; resetDraft(context); }
    } catch (error) { if (!disposed && token === detailGeneration) saveNotice.value = error.message; }
  }

  async function save() {
    const context = detail.context;
    if (saving.value || !context || context.lookupError) return;
    const values = Object.fromEntries(data.followFields.map(field => [field.fieldname, String(draft[field.fieldname] ?? '').trim()]));
    const original = context.form || context.defaults;
    if (!manager.value) for (const field of Object.keys(values)) {
      if (phoneField(field) || values[field] === show(field, original[field] ?? '')) values[field] = original[field] ?? '';
    }
    if (values.status === 'Follow Up Scheduled' && !values.next_follow_up_scheduled_date) { saveNotice.value = 'Choose the next follow-up date.'; return; }
    const file = photo.value;
    if (file && (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024)) { saveNotice.value = 'Choose a JPEG, PNG or WebP image below 10 MB.'; return; }
    saving.value = true; saveNotice.value = 'Saving…'; let recordSaved = false;
    try {
      const doc = await followDocument({ ...context, form: context.form ? toRaw(context.form) : null }, values);
      context.form = await api(context.form ? 'frappe.client.save' : 'frappe.client.insert', { doc });
      recordSaved = true;
      if (file) {
        if (!portalSession.csrf_token) throw new Error('Photo upload requires a refreshed signed-in session.');
        const form = new FormData();
        form.append('file', file); form.append('is_private', '1'); form.append('doctype', FORM_DOCTYPE); form.append('docname', context.form.name); form.append('fieldname', 'custom_client_photo_attach');
        const result = await request('upload_file', {formData:form,csrfToken:portalSession.csrf_token});
        if (!result.message?.file_url) throw new Error('Photo upload failed.');
        const latest = await api('frappe.client.get', { doctype: FORM_DOCTYPE, name: context.form.name });
        latest.custom_client_photo_attach = result.message.file_url;
        context.form = await api('frappe.client.save', { doc: latest });
      }
      if (disposed) return;
      followups.set(cachedKey(context.section, context.source.name), context.form);
      resetDraft(context); saveNotice.value = 'Saved successfully · ' + show('name', context.form.name);
      await load();
      followups.set(cachedKey(context.section, context.source.name), context.form);
      const part = { doctype: FORM_DOCTYPE, doc: context.form, ...await attachments(FORM_DOCTYPE, context.form) };
      if (!disposed && detail.context === context) detail.parts = [...detail.parts.filter(item => item.doctype !== FORM_DOCTYPE), part];
    } catch (error) {
      if (!disposed) { dirty.value = recordSaved ? !!file : true; saveNotice.value = (recordSaved ? 'Follow-up saved. Photo could not be completed: ' : 'Not saved: ') + error.message; }
    } finally { if (!disposed) saving.value = false; }
  }

  async function allRows(section) {
    const rows = [], criteria = applied.value;
    for (let start = 0; ; start += 500) {
      notice.value = 'Preparing ' + section.title + ' · ' + rows.length + ' records…';
      const batch = await api('frappe.client.get_list', { doctype: section.dt, fields: section.fields, filters: sectionFilters(section, criteria), or_filters: sectionSearch(section, criteria), limit_start: start, limit_page_length: 500, order_by: 'creation desc, name desc' });
      if (disposed) throw new DOMException('Page closed', 'AbortError');
      rows.push(...batch); if (batch.length < 500) return rows;
    }
  }

  onBeforeUnmount(() => { disposed = true; generation++; detailGeneration++; abortReads(); });
  return { sections, filters, applied, branches, manager, busy, loaded, notice, records, followups, detail, draft, dirty, saving, saveNotice, photo, legacyChoice, canOutput, show, cachedKey, initialize, load, paginate, openDetail, closeDetail, chooseLegacy, save, allRows };
}
