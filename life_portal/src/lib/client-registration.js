// Client Registration rules, owned by the Vue application.
export const registrationRisks = [
  ['Normal', 'No known medical condition', 'GREEN', '#2E7D32'],
  ['Controlled', 'Controlled BP, controlled diabetes, thyroid', 'YELLOW', '#F9A825'],
  ['Medical History', 'Previous surgery, past cardiac issue', 'ORANGE', '#EF6C00'],
  ['Active Condition', 'Current infection, uncontrolled BP, active illness', 'RED', '#C62828'],
  ['High Risk', 'Cardiac risk, pregnancy, severe uncontrolled condition', 'BLACK', '#212121'],
];
export function registrationToday(now = new Date()) {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}
export function registrationDefaults() {
  return Object.fromEntries(['fName','fAlias','fGender','fDob','fOcc','fPhone','fAlt','fEmail','fArea','fAddr','fConsult','fWFor','fBranch','fPDNo','fEmp','fBM','fRisk','fMed','fRelName','fRelBr','book','rel'].map(key => [key, '']).concat([
    ['fWDate', registrationToday()], ['fWType', 'Fresh Walk-in'], ['fDept', 'Slimming'],
  ]));
}
export function registrationMobile(raw) {
  const digits = String(raw || '').replace(/\D/g, '');
  return /^91\d{10}$/.test(digits) ? digits.slice(2) : digits;
}
export function registrationName(raw) {
  return String(raw || '').replace(/[^a-zA-Z\s.']/g, '').trim().replace(/\s+/g, ' ')
    .split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
}
export function registrationAge(value, now = new Date()) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return null;
  const [year, month, day] = value.split('-').map(Number), date = new Date(year, month - 1, day);
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day || date > now) return null;
  const age = now.getFullYear() - year - (now.getMonth() < month - 1 || (now.getMonth() === month - 1 && now.getDate() < day) ? 1 : 0);
  return age >= 0 && age <= 110 ? age : null;
}
export function validateRegistration(form, links, now = new Date()) {
  const errors = {};
  if (!form.fName.trim()) errors.fName = 'Client name is required.';
  else if (registrationName(form.fName).replace(/[^a-zA-Z]/g, '').length < 2) errors.fName = 'Name must contain at least 2 letters.';
  if (!form.fGender) errors.fGender = 'Please select gender.';
  if (!form.fDob) errors.fDob = 'Date of birth is required.';
  else if (registrationAge(form.fDob, now) === null) errors.fDob = 'Check DOB — age out of range or date in the future.';
  const mobile = registrationMobile(form.fPhone);
  if (!mobile) errors.fPhone = 'Mobile number is required.';
  else if (!/^\d{10}$/.test(mobile)) errors.fPhone = 'Must be exactly 10 digits (91 prefix is stripped).';
  else if (!/^[6-9]/.test(mobile)) errors.fPhone = 'Must start with 6, 7, 8, or 9.';
  if (form.fAlt && !/^[6-9]\d{9}$/.test(registrationMobile(form.fAlt))) errors.fAlt = 'If entered, must be a valid 10-digit number.';
  if (form.fEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.fEmail.trim())) errors.fEmail = 'Enter a valid email address.';
  if (!form.fArea.trim()) errors.fArea = 'Client area is required.';
  if (!form.fWDate) errors.fWDate = 'Walk-in date is required.';
  if (!form.fWFor) errors.fWFor = 'Please select walk-in reason.';
  if (!links.fBranch.id) errors.fBranch = 'Select a valid branch from the list.';
  if (!links.fEmp.id) errors.fEmp = 'Select a valid practitioner from the list.';
  for (const key of ['fBM', 'fRelBr']) if (form[key] && !links[key].id) errors[key] = 'Select a valid entry from the list.';
  if (!form.fRisk) errors.fRisk = 'Select a medical risk level.';
  if (!form.book) errors.book = 'Select Booked or Unbooked.';
  if (!form.rel) errors.rel = 'Please answer Yes or No.';
  else if (form.rel === 'Yes' && !form.fRelName.trim()) errors.rel = "Enter the relative's client name below.";
  return errors;
}
export function registrationPatient(form, links) {
  const red = ['Active Condition', 'High Risk'].includes(form.fRisk);
  const remarks = [['Alias', form.fAlias], ['Walk-in date', form.fWDate], ['Walk-in type', form.fWType],
    ['Walk-in for', form.fWFor], ['Consultant', form.fConsult], ['Branch manager', form.fBM],
    ['PD Form', form.fPDNo], ['Risk level', form.fRisk]]
    .filter(([, value]) => value).map(([label, value]) => `${label}: ${value}`);
  if (form.rel === 'Yes' && form.fRelName) remarks.push(`Relative in LIFE: ${form.fRelName} (${form.fRelBr || ''})`);
  return {
    doctype: 'Patient', first_name: registrationName(form.fName), sex: form.fGender, dob: form.fDob,
    mobile: registrationMobile(form.fPhone), phone: registrationMobile(form.fAlt), email: form.fEmail.trim(),
    occupation: registrationName(form.fOcc), custom_client_address: [form.fArea, form.fAddr].filter(Boolean).join(', '),
    custom_branch: links.fBranch.id, branch_name: links.fBranch.id, custom_employee_id: links.fEmp.id,
    custom_manager_name: links.fBM.id || '', custom_client_visited_for_: form.fDept === 'Laser' ? 'Skin' : form.fDept,
    custom_treatment_category: form.fDept === 'Slimming' ? 'Slimming/Cryo' : form.fDept === 'Hair' ? 'Hair / PRP / GFC' : 'Skin/Laser',
    custom_final_decision: form.book === 'Booked' ? 'Booked' : 'Not-Booked',
    custom_health_flag: red ? 'Red Flag' : form.fRisk === 'Medical History' ? 'Orange Flag' : 'Green Flag',
    custom_severity_update: red ? 'Serious' : 'Controlled', custom_medical_history: form.fRisk === 'Normal' ? 'Non-Medical' : 'Medical',
    medical_history: form.fMed || '', custom_remarks: remarks.join(' | '),
    ...(form.fPDNo ? { custom_pd_form_number: form.fPDNo } : {}),
  };
}
