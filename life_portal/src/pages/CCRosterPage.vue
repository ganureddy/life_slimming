<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { request } from '../api/http';
import { session, canAccessModule } from '../lib/session';
import { movePeriod, summarize, cellLabel } from '../lib/cc-roster';

const view = ref('week'), anchor = ref(''), query = ref(''), department = ref('');
const data = ref(null), loading = ref(false), error = ref(''), success = ref('');
const editor = ref(null), dialog = ref(null), saving = ref(false), saveError = ref('');
let controller, generation = 0, active = true;
const allowed = computed(() => canAccessModule('leads'));
const employees = computed(() => (data.value?.employees || []).filter(e =>
  (!department.value || e.department === department.value) &&
  [e.employee_name, e.name, e.designation].some(v => String(v || '').toLowerCase().includes(query.value.trim().toLowerCase()))));
const departments = computed(() => [...new Set((data.value?.employees || []).map(e => e.department).filter(Boolean))].sort());
const summaries = computed(() => Object.fromEntries(employees.value.map(e => [e.name, summarize(data.value.cells[e.name])])));
const totals = computed(() => Object.values(summaries.value).reduce((sum, row) => {
  for (const key of ['planned', 'weekOff', 'unplanned', 'conflicts']) sum[key] += row[key];
  return sum;
}, { planned: 0, weekOff: 0, unplanned: 0, conflicts: 0 }));
const format = (day, options = {}) => new Date(day + 'T12:00:00Z').toLocaleDateString('en-IN', {timeZone: 'UTC', ...options});
const periodLabel = computed(() => !data.value ? '' : view.value === 'month'
  ? format(data.value.start, {month: 'long', year: 'numeric'})
  : format(data.value.start, {day: 'numeric', month: 'short'}) + ' – ' + format(data.value.end, {day: 'numeric', month: 'short', year: 'numeric'}));
const cell = (employee, day) => data.value.cells[employee][day];
const editable = value => data.value.can_edit && value.shifts.length <= 1 && (!value.shifts.length || value.shifts[0].single_day);
async function api(method, args, signal) {
  return (await request('life_slimming.api.cc_roster.' + method, {args, signal, csrfToken: session.csrf_token})).message;
}
async function load() {
  const gen = ++generation;
  controller?.abort(); controller = new AbortController();
  error.value = ''; loading.value = true; data.value = null;
  try {
    const result = await api('calendar_view', {anchor: anchor.value || undefined, view: view.value}, controller.signal);
    if (active && gen === generation) { data.value = result; if (!anchor.value) anchor.value = result.today; }
  } catch (cause) { if (active && gen === generation && cause.name !== 'AbortError') error.value = cause.message; }
  finally { if (active && gen === generation) loading.value = false; }
}
function navigate(direction) { if (!data.value) return; anchor.value = movePeriod(data.value.start, view.value, direction); load(); }
function today() { if (!data.value) return; anchor.value = data.value.today; load(); }
async function edit(employee, day) {
  const value = cell(employee.name, day); if (!editable(value) || saving.value) return;
  editor.value = {employee, day, previous: value.shifts[0] || null, shift: value.shifts[0]?.shift_type || ''};
  saveError.value = ''; await nextTick(); dialog.value?.showModal();
}
function close() { if (saving.value) return; dialog.value?.close(); editor.value = null; }
async function save() {
  if (!editor.value || saving.value) return;
  saving.value = true; saveError.value = ''; success.value = '';
  const entry = editor.value;
  try {
    await api('save_shift', {employee: entry.employee.name, day: entry.day, shift_type: entry.shift,
      assignment: entry.previous?.name || '', expected_modified: entry.previous?.modified || ''});
    if (!active) return;
    success.value = entry.employee.employee_name + ' · ' + format(entry.day, {day: 'numeric', month: 'short'}) + ' saved.';
    dialog.value?.close(); editor.value = null; await load();
  } catch (cause) { if (active) saveError.value = cause.message + ' Refresh the roster before retrying if the result is uncertain.'; }
  finally { saving.value = false; }
}
watch(view, () => { success.value = ''; load(); });
onMounted(() => { if (allowed.value) load(); });
onBeforeRouteLeave(() => !saving.value);
onBeforeUnmount(() => { active = false; generation++; controller?.abort(); });
</script>

<template>
  <section class="cc-roster">
    <header class="roster-heading"><div><p class="eyebrow">CALL CENTRE · HO CC</p><h1>CC ROASTER</h1><p>Employee shifts, week offs and attendance for Ho CC.</p></div><span class="branch-tag">Ho CC</span></header>
    <p v-if="!allowed" role="alert">This module is not available for your account.</p>
    <template v-else>
      <div class="roster-toolbar panel">
        <div class="view-switch" aria-label="Roster period"><button v-for="mode in ['week','month']" :key="mode" :aria-pressed="view===mode" :disabled="saving" @click="view=mode">{{mode==='week'?'Week':'Month'}}</button></div>
        <label>Date<input v-model="anchor" type="date" :disabled="saving" @change="load"></label>
        <div class="period-nav"><button :disabled="!data||saving" aria-label="Previous period" @click="navigate(-1)">‹</button><button :disabled="!data||saving" @click="today">Today</button><button :disabled="!data||saving" aria-label="Next period" @click="navigate(1)">›</button></div>
        <label>Employee<input v-model="query" placeholder="Name, ID or designation"></label>
        <label>Department<select v-model="department"><option value="">All departments</option><option v-for="name in departments" :key="name">{{name}}</option></select></label>
        <button :disabled="loading||saving" @click="load">Refresh</button>
      </div>
      <p v-if="success" class="notice" role="status">{{success}}</p>
      <p v-if="error" class="roster-error" role="alert">{{error}} <button @click="load">Retry</button></p>
      <p v-if="loading" role="status" class="panel">Loading Ho CC roster…</p>
      <template v-if="data">
        <div class="roster-period"><h2>{{periodLabel}}</h2><span>{{employees.length}} employees · {{data.can_edit?'Select a shift cell to edit':'View only · Call Center Export or System Manager can edit'}}</span></div>
        <div class="roster-metrics"><article><strong>{{employees.length}}</strong><span>Employees</span></article><article><strong>{{totals.planned}}</strong><span>Planned work days</span></article><article><strong>{{totals.weekOff}}</strong><span>Week off days</span></article><article><strong>{{totals.unplanned}}</strong><span>Unplanned days</span></article></div>
        <p v-if="totals.conflicts" class="roster-error">{{totals.conflicts}} employee-days have overlapping shifts. Resolve them in HR before editing.</p>
        <div v-if="employees.length" class="roster-grid panel" tabindex="0" aria-label="Ho CC employee roster">
          <table :class="view"><caption class="sr-only">Ho CC {{view}} roster, {{periodLabel}}</caption><thead><tr><th scope="col">Employee</th><th v-for="day in data.days" :key="day" scope="col" :class="{today:day===data.today}"><span>{{format(day,{weekday:'short'})}}</span><strong>{{format(day,{day:'numeric',month:'short'})}}</strong></th></tr></thead>
            <tbody><tr v-for="employee in employees" :key="employee.name"><th scope="row"><strong>{{employee.employee_name}}</strong><small>{{employee.name}}</small><small>{{employee.designation||employee.department||'—'}}</small></th>
              <td v-for="day in data.days" :key="day" :class="{today:day===data.today,off:cell(employee.name,day).shifts[0]?.shift_type==='Week Off',conflict:cell(employee.name,day).shifts.length>1}">
                <button v-if="editable(cell(employee.name,day))" class="shift-cell" :aria-label="employee.employee_name+', '+day+', '+cellLabel(cell(employee.name,day))+', change shift'" @click="edit(employee,day)">{{cellLabel(cell(employee.name,day))}} <span aria-hidden="true">✎</span></button>
                <span v-else class="shift-label">{{cellLabel(cell(employee.name,day))}}</span>
                <small v-if="cell(employee.name,day).attendance" class="attendance">{{cell(employee.name,day).attendance}}</small><small v-else-if="cell(employee.name,day).leave" class="attendance">Approved leave</small><small v-else-if="day<=data.today" class="no-attendance">No attendance record</small>
                <small v-if="cell(employee.name,day).shifts.some(s=>!s.single_day)" class="no-attendance">Range assignment · edit in HR</small>
              </td></tr></tbody></table>
        </div>
        <p v-else class="panel">{{data.employees.length?'No employees match these filters.':'No active employees are assigned to Ho CC.'}}</p>
        <template v-if="view==='month'&&employees.length"><h2>Monthly summary</h2><p>Planned days come from shifts. Attendance totals include only submitted records.</p><div class="summary-table panel"><table><thead><tr><th>Employee</th><th>Planned work</th><th>Week off</th><th>Unplanned</th><th>Present / WFH</th><th>Absent</th><th>Leave days</th></tr></thead><tbody><tr v-for="employee in employees" :key="employee.name"><th scope="row">{{employee.employee_name}}</th><td>{{summaries[employee.name].planned}}</td><td>{{summaries[employee.name].weekOff}}</td><td>{{summaries[employee.name].unplanned}}</td><td>{{data.attendance_available?summaries[employee.name].present:'—'}}</td><td>{{data.attendance_available?summaries[employee.name].absent:'—'}}</td><td>{{summaries[employee.name].leave}}</td></tr></tbody></table></div></template>
      </template>
      <dialog v-if="editor" ref="dialog" class="roster-dialog" @cancel.prevent="close"><form @submit.prevent="save"><h2>Change shift</h2><p>{{editor.employee.employee_name}} · {{format(editor.day,{day:'numeric',month:'long',year:'numeric'})}}</p><label>Shift<select v-model="editor.shift" :disabled="saving"><option value="">Not planned</option><option v-for="shift in data?.shift_types||[]" :key="shift">{{shift}}</option></select></label><p v-if="editor.previous&&!editor.shift">Saving will cancel this day's current shift assignment.</p><p v-if="saveError" class="roster-error" role="alert">{{saveError}}</p><div class="dialog-actions"><button type="button" :disabled="saving" @click="close">Cancel</button><button type="submit" class="primary" :disabled="saving">{{saving?'Saving…':'Save shift'}}</button></div></form></dialog>
    </template>
  </section>
</template>

<style scoped>
.cc-roster{display:grid;gap:16px;padding:24px;max-width:100%;min-width:0;color:#173d30}.roster-heading,.roster-period{display:flex;align-items:center;justify-content:space-between;gap:16px}.roster-heading h1{margin:4px 0;font-size:28px}.roster-heading p,.roster-period span{color:#64776f;margin:4px 0}.eyebrow{font-size:11px;letter-spacing:1.5px;font-weight:700}.branch-tag{background:#e7f3eb;padding:8px 18px;border-radius:20px;font-weight:700;white-space:nowrap}.panel{background:#fff;border:1px solid #dde6df;border-radius:12px;padding:16px}.roster-toolbar{display:flex;gap:12px;align-items:end;flex-wrap:wrap}.roster-toolbar label,.roster-dialog label{display:grid;gap:5px;font-size:12px;font-weight:600}.roster-toolbar input,.roster-toolbar select,.roster-dialog select{min-height:38px;border:1px solid #cbd9d0;border-radius:7px;padding:7px 9px;background:white;color:inherit}.roster-toolbar button,.dialog-actions button{padding:9px 14px;min-height:38px;border:1px solid #cbd9d0;border-radius:7px;background:#fff;color:inherit;cursor:pointer}.view-switch,.period-nav{display:flex;gap:4px}.view-switch button[aria-pressed=true],.dialog-actions .primary{background:#17633f;color:white;border-color:#17633f}button:disabled{opacity:.5;cursor:wait}.roster-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.roster-metrics article{display:grid;gap:5px;padding:16px;background:#fff;border:1px solid #dde6df;border-radius:10px}.roster-metrics strong{font-size:26px}.roster-metrics span{font-size:12px;color:#64776f}.roster-period h2{margin:0;font-size:20px}.roster-grid,.summary-table{overflow:auto;padding:0;max-width:100%}table{border-collapse:separate;border-spacing:0;width:100%;font-size:12px}th,td{padding:12px;border-right:1px solid #e4ebe6;border-bottom:1px solid #e4ebe6;text-align:left;vertical-align:top}thead th{background:#f1f6f2;white-space:nowrap}thead th span,thead th strong,tbody th strong,tbody th small{display:block;line-height:1.6}tbody th small{color:#64776f;font-weight:400}.roster-grid th:first-child{position:sticky;left:0;min-width:180px;max-width:220px;background:#fff;z-index:1}.roster-grid thead th:first-child{background:#f1f6f2;z-index:2}.roster-grid td{min-width:130px}.roster-grid .month td{min-width:110px}.shift-cell{border:1px solid #d0e1d5;border-radius:6px;background:#f6fbf7;padding:8px;color:#185538;text-align:left;width:100%;cursor:pointer;font-size:12px}.shift-label{display:block;padding:8px 0}.attendance,.no-attendance{display:block;font-size:10px;line-height:1.5;margin-top:6px}.attendance{color:#26664a}.no-attendance{color:#7c8982}.today{box-shadow:inset 0 3px #c2a446}.off{background:#fffaf0}.conflict,.roster-error{color:#a83232;background:#fff2f0}.roster-error,.notice{padding:12px;border-radius:8px;margin:0}.notice{color:#18643d;background:#eaf6ee}.roster-dialog{border:1px solid #d6e2da;border-radius:14px;padding:24px;width:min(460px,90vw);color:inherit}.roster-dialog::backdrop{background:#122e2466}.roster-dialog form{display:grid;gap:16px}.roster-dialog h2,.roster-dialog p{margin:0}.dialog-actions{display:flex;justify-content:flex-end;gap:8px}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}@media(max-width:700px){.cc-roster{padding:12px}.roster-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.roster-period{align-items:start;flex-direction:column}.roster-toolbar label{flex:1;min-width:130px}.roster-heading h1{font-size:24px}.roster-grid th:first-child{min-width:145px}}
</style>
