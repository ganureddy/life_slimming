import { request } from './http';
import { apiUrl, apiCredentials } from './config';
import endpoints from './endpoints.json';
import { session } from '../lib/session';

// Native Billing uses its own adapter; the exported page bridge is untouched.
export async function billingCall(method, args = {}, signal) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) abort();
  signal?.addEventListener('abort', abort, { once: true });
  const timeout = setTimeout(abort, 45000);
  try {
    const body = await request(endpoints[method] || method, { args, signal: controller.signal, csrfToken: session.csrf_token });
    const result = body.message;
    if (result == null || result.error || result.ok === false) throw new Error(result?.error || result?.message || 'Billing returned no result. Please retry.');
    return result;
  } catch (error) {
    if (error.name === 'AbortError' && !signal?.aborted) throw new Error('Billing request timed out. Check the invoice before retrying a transaction.');
    throw error;
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener('abort', abort);
  }
}
export const getBillingDoc = (doctype, name) => billingCall('frappe.client.get', { doctype, name });
export const setBillingValue = (doctype, name, fieldname, value) => billingCall('frappe.client.set_value', { doctype, name, fieldname, value });
export async function billingList(doctype, filters, fields, { start = 0, limit = 40, order = 'creation desc', signal, orFilters } = {}) {
  return billingCall('frappe.client.get_list', { doctype, filters, fields, limit_start: start, limit_page_length: limit, order_by: order, ...(orFilters?.length ? { or_filters: orFilters } : {}) }, signal);
}
export async function uploadBillingFile(file, doctype) {
  const form = new FormData();
  form.append('file', file); form.append('is_private', '1');
  if (!file || file.size > 10 * 1024 * 1024) throw new Error('Choose a file no larger than 10 MB.');
  form.append('folder', 'Home/Attachments');
  const response = await fetch(apiUrl('/api/method/upload_file'), { method: 'POST', credentials: apiCredentials(), headers: { 'X-Frappe-CSRF-Token': session.csrf_token || '' }, body: form });
  const body = await response.json();
  if (!response.ok || !body.message?.file_url) throw new Error('File upload failed. Please retry.');
  return body.message.file_url;
}
export function invoicePdfUrl(name, printFormat = 'Consultaion Patient Sales Invoice') {
  return apiUrl('/api/method/frappe.utils.print_format.download_pdf?' + new URLSearchParams({ doctype: 'Sales Invoice', name, format: printFormat, no_letterhead: '0' }));
}
export function invoicePrintViewUrl(name, printFormat = 'Consultaion Patient Sales Invoice') {
  return apiUrl('/printview?' + new URLSearchParams({ doctype: 'Sales Invoice', name, format: printFormat, no_letterhead: '0', trigger_print: '0' }));
}

export async function refreshBillingOffers(fallback, today) {
  // Read child item mappings from their permitted parent Pricing Rule docs.
  const rules = await billingList('Pricing Rule', [['disable', '=', 0], ['selling', '=', 1], ['apply_on', '=', 'Item Code']], ['name', 'valid_from', 'valid_upto'], { limit: 501, order: 'priority desc, modified desc' });
  if (rules.length > 500) throw new Error('Pricing rule refresh is incomplete; retaining bootstrap offers.');
  const active = rules.filter(r => (!r.valid_from || String(r.valid_from).slice(0,10) <= today) && (!r.valid_upto || String(r.valid_upto).slice(0,10) >= today));
  const documents = [];
  // Keep concurrency bounded while resolving every item in multi-item rules.
  for (let i = 0; i < active.length; i += 8) documents.push(...await Promise.all(active.slice(i,i+8).map(r=>getBillingDoc('Pricing Rule',r.name))));
  return documents.flatMap(rule=>(rule.items || []).map(item=>({ ...rule, item_code:item.item_code, uom:item.uom, apply_on:'Item Code' })));
}
