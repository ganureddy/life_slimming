import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { onBeforeRouteLeave, useRouter } from 'vue-router';
import { call } from '../lib/api';
import { session } from '../lib/session';
import { request } from '../api/http';
import { registrationAge, registrationDefaults, registrationMobile, registrationPatient, registrationRisks, registrationToday, validateRegistration } from '../lib/client-registration';

export function useClientRegistration() {
  const router = useRouter(), root = ref(null), fileInput = ref(null);
  const form = reactive(registrationDefaults()), errors = reactive({}), touched = reactive({});
  const links = reactive(Object.fromEntries(['fBranch', 'fRelBr', 'fEmp', 'fBM'].map(key => [key, { id: '', rows: [], open: false, busy: false, error: '', selected: -1 }])));
  const registrations = ref([]), loading = ref(false), loadError = ref(''), busy = ref(false), saveError = ref(''), saved = ref(null);
  const pdFile = ref(null), toastMessage = ref('');
  const timers = new Map(), searches = new Map();
  let active = true, listController, toastTimer;
  const csrf = () => session.csrf_token;
  const rpc = (method, args, signal) => call(method, args, { csrfToken: csrf(), signal });
  const age = computed(() => registrationAge(form.fDob));
  const ageText = computed(() => age.value === null ? '' : `${age.value} years`);
  const ageHint = computed(() => !form.fDob ? 'Age auto-calculates from DOB' : age.value === null ? '⚠ Check DOB — age out of range' : 'Age auto-calculated ✓');
  const risk = computed(() => registrationRisks.find(row => row[0] === form.fRisk));
  const initials = computed(() => form.fName.trim().split(/\s+/).filter(Boolean).map(word => word[0]).join('').slice(0, 2).toUpperCase() || '?');
  function toast(message) { toastMessage.value = message; clearTimeout(toastTimer); toastTimer = setTimeout(() => { toastMessage.value = ''; }, 2800); }
  function validate(key) {
    touched[key] = true;
    const result = validateRegistration(form, links);
    errors[key] = result[key] || '';
    if (['fPhone', 'fAlt'].includes(key) && !errors[key]) form[key] = registrationMobile(form[key]);
  }
  for (const key of Object.keys(form)) watch(() => form[key], () => {
    if (touched[key]) errors[key] = validateRegistration(form, links)[key] || '';
  });
  function closeLinks() { for (const link of Object.values(links)) link.open = false; }
  function searchLink(key) {
    const link = links[key], query = form[key].trim();
    link.id = ''; link.error = ''; link.rows = []; link.open = query.length >= 2; link.selected = -1; link.busy = false;
    clearTimeout(timers.get(key)); searches.get(key)?.abort();
    if (query.length < 2) return;
    timers.set(key, setTimeout(async () => {
      const controller = new AbortController(); searches.set(key, controller); link.busy = true;
      const practitioner = ['fEmp', 'fBM'].includes(key), field = practitioner ? 'practitioner_name' : 'name';
      try {
        const rows = await rpc('frappe.client.get_list', {
          doctype: practitioner ? 'Healthcare Practitioner' : 'Branch', fields: practitioner ? ['name', field] : ['name'],
          filters: [[field, 'like', `%${query}%`]], order_by: field + ' asc', limit_page_length: 12,
        }, controller.signal);
        if (active && !controller.signal.aborted && form[key].trim() === query) link.rows = (rows || []).map(row => ({ id: row.name, label: row[field] || row.name, sub: practitioner ? row.name : '' }));
      } catch (error) { if (active && !controller.signal.aborted) link.error = error.message; }
      finally { if (active && searches.get(key) === controller) link.busy = false; }
    }, 200));
  }
  function chooseLink(key, row) {
    searches.get(key)?.abort(); clearTimeout(timers.get(key));
    Object.assign(links[key], { id: row.id, open: false, busy: false }); form[key] = row.label; validate(key);
  }
  function linkKey(key, event) {
    const link = links[key];
    if (event.key === 'Escape') link.open = false;
    else if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault(); link.open = true;
      link.selected = Math.max(0, Math.min(link.rows.length - 1, link.selected + (event.key === 'ArrowDown' ? 1 : -1)));
    } else if (event.key === 'Enter' && link.open && link.rows[link.selected]) {
      event.preventDefault(); chooseLink(key, link.rows[link.selected]);
    }
  }
  async function loadRegistrations() {
    listController?.abort(); const controller = new AbortController(); listController = controller;
    loading.value = true; loadError.value = '';
    try {
      const rows = await rpc('frappe.client.get_list', { doctype: 'Patient', fields: ['name', 'patient_name', 'custom_final_decision', 'custom_health_flag'],
        filters: [['creation', '>=', registrationToday() + ' 00:00:00']], order_by: 'creation desc', limit_page_length: 20 }, controller.signal);
      if (active && !controller.signal.aborted) registrations.value = rows || [];
    } catch (error) { if (active && !controller.signal.aborted) loadError.value = error.message; }
    finally { if (active && listController === controller) loading.value = false; }
  }
  function resetForm() {
    if (busy.value) return;
    Object.assign(form, registrationDefaults());
    for (const key of Object.keys(errors)) delete errors[key];
    for (const key of Object.keys(touched)) delete touched[key];
    for (const [key, link] of Object.entries(links)) {
      clearTimeout(timers.get(key)); searches.get(key)?.abort();
      Object.assign(link, { id: '', rows: [], open: false, error: '', busy: false, selected: -1 });
    }
    pdFile.value = null; if (fileInput.value) fileInput.value.value = '';
    saveError.value = ''; saved.value = null; toast('Form cleared');
  }
  function pickFile(event) {
    const file = event.target.files?.[0];
    if (file && !(/\.pdf$/i.test(file.name) || file.type.startsWith('image/'))) {
      saveError.value = 'Choose a PDF or image for the PD form.'; event.target.value = ''; pdFile.value = null; return;
    }
    pdFile.value = file || null; saveError.value = '';
  }
  async function openBilling() { if (saved.value) await router.push({ name: 'billing', query: { mobile: saved.value.mobile } }); }
  async function saveClient() {
    if (busy.value || saved.value) return;
    const invalid = validateRegistration(form, links);
    for (const key of new Set([...Object.keys(errors), ...Object.keys(invalid)])) { errors[key] = invalid[key] || ''; touched[key] = true; }
    if (Object.keys(invalid).length) {
      toast('Please fix the highlighted fields.'); await nextTick();
      root.value?.querySelector('.has-err input,.has-err select,.has-err button')?.focus(); return;
    }
    busy.value = true; saveError.value = ''; closeLinks();
    // Freeze the submitted values so edits or delayed reads cannot change the transaction.
    const doc = registrationPatient({ ...form }, links), file = pdFile.value;
    try {
      const duplicate = await rpc('frappe.client.get_value', { doctype: 'Patient', filters: { mobile: doc.mobile }, fieldname: 'patient_name' });
      if (duplicate?.patient_name) {
        errors.fPhone = `Already registered to ${duplicate.patient_name}.`; touched.fPhone = true;
        toast('Duplicate mobile — registration blocked'); return;
      }
      if (file) {
        const body = new FormData(); body.append('file', file); body.append('is_private', '1');
        const upload = (await request('upload_file', { formData: body, csrfToken: csrf() })).message;
        if (!upload?.file_url) throw new Error('PD form upload returned no file. Registration was not submitted.');
        doc.custom_pd_form = [{ pd_form: upload.file_url }];
      }
      const patient = await rpc('frappe.client.insert', { doc });
      if (!patient?.name) throw new Error('No client ID was returned. Check today’s registrations before submitting again.');
      saved.value = { name: patient.name, mobile: doc.mobile }; toast(`${patient.name} registered ✓`);
      // Navigate only after a confirmed insert. No automatic mutation retry.
      await openBilling();
    } catch (error) { saveError.value = error.message || 'Registration failed. Check today’s registrations before trying again.'; }
    finally { busy.value = false; }
  }
  onMounted(loadRegistrations);
  onBeforeRouteLeave(() => !busy.value || !!saved.value);
  onBeforeUnmount(() => { active = false; listController?.abort(); searches.forEach(controller => controller.abort()); timers.forEach(clearTimeout); clearTimeout(toastTimer); });
  return { root, fileInput, form, errors, touched, links, registrations, loading, loadError, busy, saveError, saved, pdFile, toastMessage,
    ageText, ageHint, risk, initials, risks: registrationRisks, validate, closeLinks, searchLink, chooseLink, linkKey,
    loadRegistrations, resetForm, pickFile, saveClient, openBilling };
}
