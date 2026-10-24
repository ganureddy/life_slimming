import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { request } from '../api/http';
import { session } from '../lib/session';
import { appointmentSlots, appointmentStatuses, appointmentToday, appointmentTime, appointmentERPTime,
  appointmentInFuture, appointmentOccupiesSlot, appointmentRoomLabel, appointmentStatusClass,
  appointmentReportArgs, appointmentReportRows, appointmentIndex, appointmentSummary,
  pendingAppointmentTherapies, rescheduledAppointment } from '../lib/appointment-scheduler';

export function useAppointmentScheduler() {
  const root = ref(null), branch = ref(''), date = ref(appointmentToday()), branches = ref([]), rooms = ref([]), appointments = ref([]);
  const loading = ref(false), branchLoading = ref(false), error = ref(''), historyError = ref(''), notice = ref(''), saving = ref(false);
  const createOpen = ref(false), createError = ref(''), activeSlot = ref(null);
  const patientText = ref(''), patientInfo = ref(null), clientDetails = ref(''), patientSuggestions = ref([]), clientSearchLoading = ref(false), patientOpen = ref(false);
  const categoryText = ref(''), selectedCategory = ref(''), categorySuggestions = ref([]), categorySearchLoading = ref(false), categoryOpen = ref(false);
  const concernText = ref(''), selectedConcern = ref(''), concernOpen = ref(false), therapyPlans = ref([]), plansLoading = ref(false), plansError = ref('');
  const detailOpen = ref(false), detailLoading = ref(false), detailsError = ref(''), appointmentDoc = ref(null), detailName = ref('');
  const status = ref('Scheduled'), rescheduleDate = ref(''), rescheduleSlot = ref(''), availableSlots = ref([]), slotsLoading = ref(false);
  const controllers = new Map(), searchTimers = new Map();
  let alive = true, focusBeforeModal, previousOverflow;
  const isExcluded = name => ['testing branch', 'head office'].includes(String(name || '').trim().toLowerCase());
  const newRead = key => { controllers.get(key)?.abort(); const controller = new AbortController(); controllers.set(key, controller); return controller; };
  const current = (key, controller) => alive && controllers.get(key) === controller && !controller.signal.aborted;
  const call = async (method, args, signal) => {
    const result = await request(method, { args, signal, csrfToken: session.csrf_token });
    if (result.exc) throw new Error('The server could not complete the appointment request. Please retry.');
    return result;
  };
  const report = async (doctype, fields, filters, order, signal, length) => appointmentReportRows(
    await call('frappe.desk.reportview.get', appointmentReportArgs(doctype, fields, filters, order, length), signal));
  const index = computed(() => appointmentIndex(appointments.value));
  const summary = computed(() => appointmentSummary(appointments.value, rooms.value));
  const cellRows = (room, slot) => index.value.get(`${room}||${slot}`) || [];
  const roomLabel = (room, target = branch.value) => appointmentRoomLabel(room, target);
  const canAdd = (room, slot) => !loading.value && appointmentInFuture(date.value, slot) && !cellRows(room, slot).some(appointmentOccupiesSlot);
  const readyToCreate = computed(() => !!patientInfo.value?.name && !!activeSlot.value?.room && !!selectedCategory.value && !!selectedConcern.value && !!activeSlot.value?.slot && !saving.value && !plansLoading.value);
  const filteredPlans = computed(() => therapyPlans.value.filter(plan => {
    const unit = plan.unit.toLowerCase().trim(), category = selectedCategory.value.toLowerCase().trim(), query = concernText.value.toLowerCase().trim();
    return (!category || unit === category || unit.includes(category) || category.includes(unit)) && (!query || `${plan.therapy} ${plan.unit} ${plan.plan}`.toLowerCase().includes(query));
  }));
  async function loadBranches() {
    const controller = newRead('branches'); branchLoading.value = true; error.value = '';
    try {
      const rows = await report('Branch', ['name', 'branch'], [], 'modified desc', controller.signal, 100);
      if (!current('branches', controller)) return;
      branches.value = [...new Set(rows.map(row => row.branch || row.name).filter(name => name && !isExcluded(name)))];
      if (!branches.value.includes(branch.value)) branch.value = branches.value[0] || '';
      if (!branch.value) throw new Error('No branches found.');
      await loadBoard();
    } catch (cause) { if (current('branches', controller)) error.value = cause.message; }
    finally { if (current('branches', controller)) branchLoading.value = false; }
  }
  async function loadBoard() {
    if (saving.value) return;
    if (!branch.value || !date.value) {
      controllers.get('board')?.abort(); loading.value = false; appointments.value = []; rooms.value = [];
      error.value = 'Please select branch and date.'; historyError.value = ''; return;
    }
    const controller = newRead('board'), selectedBranch = branch.value, selectedDate = date.value;
    loading.value = true; error.value = ''; historyError.value = '';
    try {
      const filters = [['Patient Appointment', 'appointment_date', 'Between', [selectedDate, selectedDate]], ['Patient Appointment', 'branch', '=', selectedBranch]];
      const [rows, roomRows, ghosts] = await Promise.all([
        report('Patient Appointment', ['name', 'status', 'service_room', 'branch', 'appointment_date', 'patient_name', 'appointment_time', 'call_back_status'], filters, 'appointment_time asc', controller.signal),
        report('Service Room', ['name'], [], 'idx asc', controller.signal),
        call('life_appointment_move_history', { branch: selectedBranch, date: selectedDate }, controller.signal).then(body => {
          if (!Array.isArray(body.message?.rows)) throw new Error('Invalid reschedule history response.');
          return body.message.rows;
        }).catch(cause => { if (current('board', controller)) historyError.value = cause.message; return []; }),
      ]);
      if (!current('board', controller)) return;
      const normalize = row => ({ ...row, patient: row.patient_name || row.patient || '-', service_room: row.service_room || 'No Room', appointment_time: appointmentTime(row.appointment_time), life_target_time: appointmentTime(row.life_target_time) });
      const real = rows.map(normalize), history = ghosts.map(normalize).filter(ghost => !real.some(row => row.name === ghost.name && row.service_room === ghost.service_room && row.appointment_time === ghost.appointment_time));
      appointments.value = [...real, ...history];
      rooms.value = [...new Set(roomRows.map(row => row.name).filter(name => name && String(name).toLowerCase().includes(selectedBranch.toLowerCase())))].sort((a, b) => roomLabel(a, selectedBranch).localeCompare(roomLabel(b, selectedBranch), undefined, { numeric: true, sensitivity: 'base' }));
    } catch (cause) {
      if (current('board', controller)) { error.value = cause.message; appointments.value = []; rooms.value = []; controller.abort(); }
    } finally { if (alive && controllers.get('board') === controller) loading.value = false; }
  }
  function retryBoard() { if (branches.value.length) loadBoard(); else loadBranches(); }
  function stopCreateReads() {
    for (const key of ['patient-search', 'category-search', 'patient-validate', 'category-validate', 'plans']) controllers.get(key)?.abort();
    searchTimers.forEach(clearTimeout); searchTimers.clear();
  }
  function openCreate(room, slot, event) {
    if (saving.value || !canAdd(room, slot)) return;
    stopCreateReads(); focusBeforeModal = event?.currentTarget;
    activeSlot.value = { room, slot, branch: branch.value, date: date.value };
    patientText.value = ''; patientInfo.value = null; clientDetails.value = ''; patientSuggestions.value = [];
    categoryText.value = ''; selectedCategory.value = ''; categorySuggestions.value = []; concernText.value = ''; selectedConcern.value = '';
    therapyPlans.value = []; plansLoading.value = false; plansError.value = ''; createError.value = '';
    patientOpen.value = categoryOpen.value = concernOpen.value = false; clientSearchLoading.value = categorySearchLoading.value = false;
    createOpen.value = true;
  }
  function closeCreate() {
    if (saving.value) return;
    stopCreateReads(); createOpen.value = false; focusBeforeModal?.focus();
  }
  function queueSearch(which, edited = false) {
    const patient = which === 'patient', text = patient ? patientText.value : categoryText.value;
    if (edited) {
      if (patient) { patientInfo.value = null; clientDetails.value = ''; therapyPlans.value = []; controllers.get('plans')?.abort(); controllers.get('patient-validate')?.abort(); }
      else { selectedCategory.value = ''; controllers.get('category-validate')?.abort(); }
      selectedConcern.value = ''; concernText.value = '';
    }
    clearTimeout(searchTimers.get(which)); controllers.get(which + '-search')?.abort();
    const busy = patient ? clientSearchLoading : categorySearchLoading, open = patient ? patientOpen : categoryOpen;
    busy.value = true; open.value = true; createError.value = '';
    searchTimers.set(which, setTimeout(async () => {
      const controller = newRead(which + '-search');
      try {
        const args = { txt: text.trim(), doctype: patient ? 'Patient' : 'Healthcare Service Unit', reference_doctype: 'Patient Appointment', page_length: 20 };
        if (patient) { args.ignore_user_permissions = 1; args.filters = JSON.stringify({ status: 'Active' }); }
        const response = await call('frappe.desk.search.search_link', args, controller.signal);
        if (!current(which + '-search', controller) || !createOpen.value) return;
        if (!Array.isArray(response.message)) throw new Error('Search returned an invalid response. Please retry.');
        (patient ? patientSuggestions : categorySuggestions).value = response.message;
      } catch (cause) { if (current(which + '-search', controller)) createError.value = cause.message; }
      finally { if (current(which + '-search', controller)) busy.value = false; }
    }, 220));
  }
  async function selectPatient(option) {
    const controller = newRead('patient-validate'); patientOpen.value = false; createError.value = '';
    controllers.get('plans')?.abort(); patientInfo.value = null; clientDetails.value = ''; patientText.value = option.value; therapyPlans.value = [];
    selectedCategory.value = categoryText.value = concernText.value = selectedConcern.value = '';
    controllers.get('patient-search')?.abort(); clearTimeout(searchTimers.get('patient'));
    try {
      const response = await call('frappe.client.validate_link', { doctype: 'Patient', docname: option.value, fields: JSON.stringify(['patient_name', 'inpatient_record', 'sex', 'mobile']) }, controller.signal);
      if (!current('patient-validate', controller) || !createOpen.value) return;
      if (!response.message) throw new Error('Unable to validate this client.');
      patientInfo.value = { ...response.message, name: response.message.name || option.value };
      patientText.value = patientInfo.value.patient_name || patientInfo.value.name;
      clientDetails.value = [patientText.value, patientInfo.value.sex, patientInfo.value.mobile].filter(Boolean).join(' | ');
      selectedCategory.value = categoryText.value = concernText.value = selectedConcern.value = '';
      await loadTherapyPlans();
    } catch (cause) { if (current('patient-validate', controller)) createError.value = cause.message; }
  }
  async function loadTherapyPlans() {
    if (!patientInfo.value?.name) return;
    const patient = patientInfo.value.name, controller = newRead('plans');
    therapyPlans.value = []; plansLoading.value = true; plansError.value = '';
    try {
      const plans = await report('Therapy Plan', ['name', 'patient', 'start_date', 'modified'], [['Therapy Plan', 'patient', '=', patient]], 'modified desc', controller.signal, 100);
      const groups = new Array(plans.length); let next = 0;
      await Promise.all(Array.from({ length: Math.min(plans.length, 4) }, async () => {
        while (next < plans.length && !controller.signal.aborted) {
          const index = next++, plan = plans[index];
          const body = await call('frappe.client.get', { doctype: 'Therapy Plan', name: plan.name }, controller.signal);
          if (!body.message) throw new Error('A therapy plan could not be loaded.');
          groups[index] = pendingAppointmentTherapies(body.message, plan);
        }
      }));
      if (!current('plans', controller) || patientInfo.value?.name !== patient) return;
      const seen = new Set();
      therapyPlans.value = groups.flat().filter(row => { const key = `${row.plan}||${row.therapy}||${row.unit}`; if (seen.has(key)) return false; seen.add(key); return true; });
    } catch (cause) { if (current('plans', controller)) { plansError.value = cause.message; controller.abort(); } }
    finally { if (alive && controllers.get('plans') === controller) plansLoading.value = false; }
  }
  async function selectCategory(option) {
    const controller = newRead('category-validate'); categoryOpen.value = false; createError.value = '';
    selectedCategory.value = selectedConcern.value = concernText.value = ''; categoryText.value = option.value;
    controllers.get('category-search')?.abort(); clearTimeout(searchTimers.get('category'));
    try {
      const response = await call('frappe.client.validate_link', { doctype: 'Healthcare Service Unit', docname: option.value, fields: '[]' }, controller.signal);
      if (!current('category-validate', controller) || !createOpen.value) return;
      if (!response.message) throw new Error('Unable to validate this category.');
      selectedCategory.value = response.message.name || option.value; categoryText.value = selectedCategory.value;
      selectedConcern.value = concernText.value = '';
    } catch (cause) { if (current('category-validate', controller)) createError.value = cause.message; }
  }
  function selectConcern(plan) {
    if (saving.value) return;
    selectedCategory.value = categoryText.value = plan.unit || '';
    selectedConcern.value = concernText.value = plan.therapy; concernOpen.value = false;
  }
  async function verifySlot(target, exclude = '') {
    const response = await call('frappe.client.get_list', { doctype: 'Patient Appointment', fields: ['name', 'appointment_time', 'service_room', 'status', 'call_back_status'],
      filters: { branch: target.branch, appointment_date: target.date, service_room: target.room, docstatus: ['<', 2] }, limit_page_length: 1000 });
    if (!Array.isArray(response.message)) throw new Error('Could not verify the slot. Please retry.');
    if (response.message.some(row => row.name !== exclude && appointmentOccupiesSlot(row) && appointmentTime(row.appointment_time) === target.slot)) throw new Error('That room/time is already booked. Choose another slot.');
  }
  async function createAppointment() {
    if (!readyToCreate.value) return;
    const target = { ...activeSlot.value }, patient = { ...patientInfo.value };
    if (!appointmentInFuture(target.date, target.slot)) { createError.value = 'Select a future date/time and available slot.'; return; }
    saving.value = true; createError.value = '';
    const doc = { docstatus: 0, doctype: 'Patient Appointment', name: `new-patient-appointment-${Date.now()}`, __islocal: 1, __unsaved: 1,
      naming_series: 'HLC-APP-.YYYY.-', status: '', call_back_status: 'Scheduled', appointment_for: 'Practitioner', company: 'Life Slimming And Cosmetic Pvt Ltd',
      add_video_conferencing: 0, invoiced: 0, appointment_based_on_check_in: 0, reminded: 0, appointment_type: 'Session', department: '',
      service_unit: selectedCategory.value, patient: patient.name, patient_name: patient.patient_name || patient.name, inpatient_record: patient.inpatient_record || null,
      patient_sex: patient.sex || '', custom_client_mobile_no: patient.mobile || '', duration: null, service_room: target.room, concern: selectedConcern.value,
      appointment_date: target.date, appointment_time: appointmentERPTime(target.slot), branch: target.branch };
    let confirmed = false;
    try {
      await verifySlot(target);
      if (!alive) return;
      const response = await call('frappe.desk.form.save.savedocs', { doc: JSON.stringify(doc), action: 'Save' });
      const saved = response.docs?.[0] || response.message?.docs?.[0];
      if (!saved?.name) throw new Error('Appointment was not confirmed as saved. Refresh the board before retrying.');
      confirmed = true; createOpen.value = false; stopCreateReads(); notice.value = 'Appointment created successfully.';
      branch.value = target.branch; date.value = target.date;
    } catch (cause) { createError.value = cause.message || 'Appointment was not confirmed as saved. Refresh the board before retrying.'; }
    finally { saving.value = false; }
    if (confirmed && alive) { await loadBoard(); focusBeforeModal?.focus(); }
  }
  async function openDetails(name, event) {
    if (saving.value) return;
    focusBeforeModal = event?.currentTarget || focusBeforeModal;
    controllers.get('reschedule')?.abort(); slotsLoading.value = false;
    const controller = newRead('detail'); detailName.value = name; detailOpen.value = true; detailLoading.value = true; detailsError.value = '';
    appointmentDoc.value = null; status.value = 'Scheduled'; rescheduleSlot.value = ''; availableSlots.value = [];
    try {
      const response = await call('frappe.client.get', { doctype: 'Patient Appointment', name }, controller.signal);
      if (!current('detail', controller) || !detailOpen.value) return;
      if (!response.message?.name) throw new Error('Unable to load appointment details.');
      appointmentDoc.value = response.message; status.value = response.message.call_back_status || 'Scheduled';
      rescheduleDate.value = response.message.appointment_date >= appointmentToday() ? response.message.appointment_date : appointmentToday();
    } catch (cause) { if (current('detail', controller)) detailsError.value = cause.message; }
    finally { if (current('detail', controller)) detailLoading.value = false; }
  }
  function closeDetails() {
    if (saving.value) return;
    controllers.get('detail')?.abort(); controllers.get('reschedule')?.abort(); detailOpen.value = false; appointmentDoc.value = null; focusBeforeModal?.focus();
  }
  async function loadAvailableSlots() {
    if (!appointmentDoc.value || !rescheduleDate.value || status.value !== 'Re-Scheduled') return;
    const controller = newRead('reschedule'), doc = appointmentDoc.value, selectedDate = rescheduleDate.value;
    rescheduleSlot.value = ''; availableSlots.value = []; slotsLoading.value = true; detailsError.value = '';
    try {
      const filters = [['Patient Appointment', 'appointment_date', 'Between', [selectedDate, selectedDate]], ['Patient Appointment', 'branch', '=', doc.branch],
        ['Patient Appointment', 'call_back_status', 'not in', ['Re-Scheduled', 'Cancel', 'Cancelled']], ['Patient Appointment', 'docstatus', '<', 2]];
      const rows = await report('Patient Appointment', ['name', 'appointment_time', 'service_room', 'status', 'call_back_status'], filters, 'appointment_time asc', controller.signal);
      if (!current('reschedule', controller) || !detailOpen.value) return;
      const booked = new Set(rows.filter(row => row.name !== doc.name && row.service_room === doc.service_room && appointmentOccupiesSlot(row)).map(row => appointmentTime(row.appointment_time)));
      availableSlots.value = appointmentSlots.filter(slot => !booked.has(slot) && appointmentInFuture(selectedDate, slot));
    } catch (cause) { if (current('reschedule', controller)) detailsError.value = cause.message; }
    finally { if (current('reschedule', controller)) slotsLoading.value = false; }
  }
  watch(status, value => {
    if (value === 'Re-Scheduled') loadAvailableSlots();
    else { controllers.get('reschedule')?.abort(); slotsLoading.value = false; rescheduleSlot.value = ''; availableSlots.value = []; }
  });
  async function saveAppointmentStatus() {
    if (saving.value || !appointmentDoc.value || !appointmentStatuses.includes(status.value)) return;
    const source = appointmentDoc.value, selectedStatus = status.value;
    const target = { branch: source.branch, room: source.service_room, date: rescheduleDate.value, slot: rescheduleSlot.value };
    if (selectedStatus === 'Re-Scheduled' && (!availableSlots.value.includes(target.slot) || !appointmentInFuture(target.date, target.slot))) { detailsError.value = 'Select a future date/time and available slot.'; return; }
    saving.value = true; detailsError.value = ''; let confirmed = false;
    try {
      const doc = selectedStatus === 'Re-Scheduled' ? rescheduledAppointment(source, target.date, target.slot, session.user) : { ...source, __unsaved: 1, call_back_status: selectedStatus };
      if (selectedStatus === 'Re-Scheduled') await verifySlot(target, source.name);
      if (!alive) return;
      const response = await call('frappe.desk.form.save.savedocs', { doc: JSON.stringify(doc), action: 'Save' });
      const saved = response.docs?.[0] || response.message?.docs?.[0];
      if (!saved?.name) throw new Error('Appointment was not confirmed as updated. Reload its details before retrying.');
      confirmed = true; detailOpen.value = false; appointmentDoc.value = null;
      notice.value = selectedStatus === 'Re-Scheduled' ? 'Appointment rescheduled; grey reference saved on original date.' : 'Appointment status updated.';
      if (selectedStatus === 'Re-Scheduled') { date.value = target.date; branch.value = target.branch; }
    } catch (cause) { detailsError.value = cause.message || 'Appointment was not confirmed as updated. Reload its details before retrying.'; }
    finally { saving.value = false; }
    if (confirmed && alive) { await loadBoard(); focusBeforeModal?.focus(); }
  }
  function clickAppointment(row, event) {
    if (row.life_ghost) { date.value = row.life_target_date; loadBoard(); }
    else openDetails(row.name, event);
  }
  const anyModal = computed(() => createOpen.value || detailOpen.value);
  watch(anyModal, async open => {
    if (open) { previousOverflow = document.body.style.overflow; document.body.style.overflow = 'hidden'; await nextTick(); root.value?.querySelector('.pa-modal input,.appt-detail-modal .detail-modal-close')?.focus(); }
    else document.body.style.overflow = previousOverflow ?? '';
  });
  function onKey(event) { if (event.key === 'Escape') { closeCreate(); closeDetails(); } }
  function closeSuggestions(which) { if (which === 'patient') patientOpen.value = false; else if (which === 'category') categoryOpen.value = false; else concernOpen.value = false; }
  onBeforeRouteLeave(() => !saving.value);
  onMounted(() => { loadBranches(); window.addEventListener('keydown', onKey); });
  onBeforeUnmount(() => { alive = false; controllers.forEach(controller => controller.abort()); searchTimers.forEach(clearTimeout); window.removeEventListener('keydown', onKey); if (anyModal.value) document.body.style.overflow = previousOverflow ?? ''; });
  return { root, branch, date, branches, rooms, loading, branchLoading, error, historyError, notice, saving, createOpen, createError, activeSlot,
    patientText, patientInfo, clientDetails, patientSuggestions, clientSearchLoading, patientOpen, categoryText, selectedCategory, categorySuggestions, categorySearchLoading, categoryOpen,
    concernText, selectedConcern, concernOpen, therapyPlans, plansLoading, plansError, detailOpen, detailLoading, detailsError, appointmentDoc, detailName,
    status, rescheduleDate, rescheduleSlot, availableSlots, slotsLoading, summary, cellRows, roomLabel, canAdd, readyToCreate, filteredPlans,
    slots: appointmentSlots, statuses: appointmentStatuses, today: appointmentToday, timeLabel: appointmentTime, statusClass: appointmentStatusClass,
    loadBoard, retryBoard, openCreate, closeCreate, queueSearch, selectPatient, loadTherapyPlans, selectCategory, selectConcern, createAppointment,
    openDetails, closeDetails, loadAvailableSlots, saveAppointmentStatus, clickAppointment, closeSuggestions };
}
