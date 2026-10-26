const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'src/lib/client-registration.js'), 'utf8');
const rules = vm.runInNewContext(source.replaceAll('export ', '') + '\n({ registrationAge,registrationDefaults,registrationPatient,registrationMobile,validateRegistration })', { Date });
const valid = () => Object.assign(rules.registrationDefaults(), { fName: 'priya kumar', fGender: 'Female', fDob: '1990-03-12', fPhone: '+91 9876543210', fArea: 'Miyapur', fWFor: 'Joined for Treatment', fRisk: 'High Risk', book: 'Booked', rel: 'No', fBranch: 'Clinic A', fEmp: 'Dr Priya' });
const links = () => ({ fBranch: { id: 'Clinic A' }, fEmp: { id: 'PRAC-001' }, fBM: { id: '' }, fRelBr: { id: '' } });
test('registration preserves Patient field mappings, risk flags, practitioner IDs and remarks', () => {
  const f = valid(); f.fDept = 'Laser'; f.fAlias = 'Pri'; f.fPDNo = 'PD-9';
  const doc = rules.registrationPatient(f, links());
  assert.equal(doc.mobile, '9876543210'); assert.equal(doc.first_name, 'Priya Kumar');
  assert.equal(doc.custom_employee_id, 'PRAC-001'); assert.equal(doc.custom_health_flag, 'Red Flag');
  assert.equal(doc.custom_severity_update, 'Serious'); assert.equal(doc.custom_treatment_category, 'Skin/Laser');
  assert.equal(doc.custom_client_visited_for_, 'Skin'); assert.equal(doc.custom_pd_form_number, 'PD-9');
  assert(doc.custom_remarks.includes('Alias: Pri')); assert(doc.custom_remarks.includes('PD Form: PD-9'));
  for (const [risk, flag, severity] of [['Normal','Green Flag','Controlled'], ['Controlled','Green Flag','Controlled'], ['Medical History','Orange Flag','Controlled'], ['Active Condition','Red Flag','Serious']]) {
    f.fRisk = risk; const patient = rules.registrationPatient(f, links());
    assert.equal(patient.custom_health_flag, flag); assert.equal(patient.custom_severity_update, severity);
  }
  f.book = 'Unbooked'; assert.equal(rules.registrationPatient(f, links()).custom_final_decision, 'Not-Booked');
});
test('registration validates required fields, calendar dates, relatives and selected links', () => {
  assert.equal(Object.keys(rules.validateRegistration(valid(), links())).length, 0);
  const f = valid(), l = links(); f.fDob = '2025-02-31'; f.rel = 'Yes'; f.fPhone = '1234567890'; l.fEmp.id = '';
  const errors = rules.validateRegistration(f, l);
  for (const key of ['fDob','rel','fPhone','fEmp']) assert(errors[key], key);
  assert.equal(rules.registrationAge('2100-01-01'), null);
  assert.equal(rules.registrationAge('1990-10-16', new Date(2026,9,15)), 35);
  assert.equal(rules.registrationMobile('919876543210'), '9876543210');
});
test('registration owns reactive template and styles without page JSON or dynamic legacy rendering', () => {
  for (const file of ['src/pages/ClientRegistrationPage.vue','src/composables/useClientRegistration.js','src/lib/client-registration.js']) {
    const text = fs.readFileSync(path.join(root, file), 'utf8');
    assert(!/portal_pages|PortalSourcePage|<iframe|v-html|innerHTML|\beval\s*\(|new Function\s*\(|window\.frappe/.test(text), file);
  }
  const page = fs.readFileSync(path.join(root, 'src/pages/ClientRegistrationPage.vue'), 'utf8');
  for (const field of ['fName','fAlias','fGender','fDob','fPhone','fAlt','fEmail','fArea','fAddr','fWDate','fWType','fConsult','fWFor','fDept','fBranch','fPDNo','fEmp','fBM','fRisk','fMed','fRelName','fRelBr']) assert(page.includes('v-model="form.' + field + '"'), field);
  assert(page.includes('<style scoped>')); assert(!page.includes(':root{'));
});
