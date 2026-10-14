export const FORM_DOCTYPE = 'Unjoined Client Form';
export const tabKeys = ['clients', 'leads', 'pending', 'forms'];
export const followStatuses = ['Call Connected', 'Follow Up Scheduled', 'No Response', 'Switch Off', 'Invalid Number', 'Dropped / Discontinued'];

export function indiaDate(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' }).format(now);
}

export function phoneField(field) {
  return /mobile|phone|whatsapp|telephone|contact.*(number|no)/i.test(field);
}

export function maskPhone(value, manager = false) {
  const text = String(value ?? '');
  if (!text || manager) return text;
  const digits = text.replace(/\D/g, '');
  if (!digits) return text;
  return digits.length > 6 ? digits.slice(0, 3) + '*'.repeat(digits.length - 6) + digits.slice(-3) : '*'.repeat(digits.length);
}

export function maskText(value, manager = false) {
  const text = String(value ?? '');
  if (manager) return text;
  return text.replace(/\+?\d[\d ()-]{5,}\d/g, part => {
    const digits = part.replace(/\D/g, '');
    return digits.length >= 7 && digits.length <= 15 && !/^\d{4}-\d{2}-\d{2}/.test(part) ? maskPhone(part) : part;
  });
}

export function displayValue(field, value, manager = false) {
  if (Array.isArray(value)) return JSON.stringify(value.map(row => sanitize(row, manager)));
  if (value && typeof value === 'object') return JSON.stringify(sanitize(value, manager));
  return phoneField(field) ? maskPhone(value, manager) : maskText(value, manager);
}

function sanitize(value, manager) {
  if (Array.isArray(value)) return value.map(row => sanitize(row, manager));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, typeof item === 'object' ? sanitize(item, manager) : displayValue(key, item, manager)]));
  return maskText(value, manager);
}

export function sectionFilters(section, filters) {
  const result = section.base.map(row => [...row]);
  result.push([section.branch, filters.branch ? '=' : '!=', filters.branch || 'Testing Branch']);
  if (section.key === 'forms' && filters.followStatus) result.push(['status', '=', filters.followStatus]);
  const field = filters.basis === 'created' ? 'creation' : section.date;
  if (filters.from) result.push([field, '>=', filters.from]);
  if (filters.to) {
    const end = new Date(filters.to + 'T00:00:00Z');
    end.setUTCDate(end.getUTCDate() + 1);
    result.push([field, '<', end.toISOString().slice(0, 10)]);
  }
  return result;
}

export function sectionSearch(section, filters) {
  const term = filters.search.trim();
  return term ? ['name', section.name, section.mobile].map(field => [field, 'like', '%' + term + '%']) : [];
}

export function dateText(value) {
  if (!value) return '—';
  const text = String(value), match = text.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return text;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  let result = match[3] + '-' + months[+match[2] - 1] + '-' + match[1].slice(2);
  const time = text.match(/[ T](\d{2}):(\d{2})/);
  if (time) result += ' ' + (+time[1] % 12 || 12) + ':' + time[2] + ' ' + (+time[1] >= 12 ? 'pm' : 'am');
  return result;
}

export function sameOriginFile(value, origin) {
  if (!value) return '';
  try {
    const url = new URL(value, origin);
    return url.origin === origin && ['http:', 'https:'].includes(url.protocol) ? url.href : '';
  } catch { return ''; }
}

export function childColumns(rows) {
  const hidden = ['doctype', 'owner', 'modified_by', 'creation', 'modified', 'docstatus', 'parent', 'parentfield', 'parenttype', 'name', 'idx'];
  return [...new Set(rows.flatMap(row => Object.keys(row)))].filter(key => !hidden.includes(key));
}

export function visibleFields(meta, doc) {
  return meta.filter(field => !/Section Break|Column Break|Tab Break|HTML|Button|Heading|Password/.test(field.fieldtype) && !(field.permlevel > 0) && doc[field.fieldname] !== undefined && doc[field.fieldname] !== null && doc[field.fieldname] !== '');
}

export async function sourceKey(doctype, name) {
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(doctype + '\n' + name));
  return Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('');
}

export async function followDocument(context, values) {
  const doc = context.form ? JSON.parse(JSON.stringify(context.form)) : { doctype: FORM_DOCTYPE };
  Object.assign(doc, values);
  if (context.section.dt === FORM_DOCTYPE) return doc;
  const { section, source } = context;
  if (doc.custom_source_document && (doc.custom_source_doctype !== section.dt || doc.custom_source_document !== source.name)) throw new Error('This form is linked to a different source.');
  const key = await sourceKey(section.dt, source.name);
  Object.assign(doc, { custom_source_doctype: section.dt, custom_source_document: source.name, custom_source_key: key });
  if (!context.form) doc.client_full_name = String(values.client_name).slice(0, 65) + ' · UJ-' + key.slice(0, 16);
  if (section.dt === 'Patient') doc.custom_linked_client = source.name;
  if (section.dt === 'Lead') doc.custom_linked_lead = source.name;
  if (section.dt === 'Patient Appointment' && source.patient) doc.custom_linked_client = source.patient;
  return doc;
}
