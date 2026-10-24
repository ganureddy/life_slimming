import { request } from './http';
import { session } from '../lib/session';

// A scope belongs to one list/profile load. It never installs a Frappe runtime.
export function createClientInfoReader(signal) {
  const metadata = new Map();
  async function call(method, args, raw = false) {
    if (signal?.aborted) throw new DOMException('Request aborted', 'AbortError');
    const body = await request(method, { args, signal, csrfToken: session.csrf_token });
    if (body.exc) throw new Error('The client data request failed. Please retry.');
    return raw ? body : body.message;
  }
  async function list(doctype, filters, fields, limit = 500, order = 'creation desc') {
    let selected = [...fields];
    // Sites can omit optional custom fields. Retry only an identified bad field,
    // never a permission/network failure, and never a mutation.
    for (let attempt = 0; attempt <= fields.length; attempt++) {
      try {
        const rows = [];
        for (let start = 0; start < limit; start += 500) {
          const count = Math.min(500, limit - start);
          const page = await call('frappe.client.get_list', { doctype, filters, fields: selected, limit_start: start, limit_page_length: count, order_by: order });
          if (!Array.isArray(page)) throw new Error(`${doctype} returned an invalid record list.`);
          rows.push(...page);
          if (page.length < count) return rows;
        }
        const extra = await call('frappe.client.get_list', { doctype, filters, fields: ['name'], limit_start: limit, limit_page_length: 1, order_by: order });
        if (!Array.isArray(extra)) throw new Error(`${doctype} returned an invalid record list.`);
        if (extra.length) throw new Error(`${doctype} exceeds the supported report size. Select a shorter date range.`);
        return rows;
      } catch (error) {
        if (signal?.aborted || !['ValidationError', 'DataError', 'OperationalError'].includes(error.code)) throw error;
        const field = error.message.match(/(?:Unknown column '(?:[\w ]+\.)?|Field not permitted in query:?\s*|Invalid field:?\s*)`?(\w+)/i)?.[1];
        if (!field || !selected.includes(field) || selected.length <= 1) throw error;
        selected = selected.filter(value => value !== field);
      }
    }
    throw new Error(`${doctype} fields could not be read.`);
  }
  const doc = (doctype, name) => call('frappe.client.get', { doctype, name });
  async function chunks(ids, read, size = 100) {
    const rows = [];
    for (let start = 0; start < ids.length; start += size) rows.push(...await read(ids.slice(start, start + size)));
    return rows;
  }
  async function pool(items, read, concurrency = 4) {
    const results = new Array(items.length); let next = 0;
    await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, async () => {
      while (next < items.length && !signal?.aborted) { const index = next++; results[index] = await read(items[index], index); }
    }));
    if (signal?.aborted) throw new DOMException('Request aborted', 'AbortError');
    return results;
  }
  async function meta(doctype) {
    if (!metadata.has(doctype)) metadata.set(doctype, call('frappe.desk.form.load.getdoctype', { doctype }, true).then(body => body.docs?.find(row => row.name === doctype)?.fields || []));
    try { return await metadata.get(doctype); }
    catch (error) { metadata.delete(doctype); throw error; }
  }
  async function lookup(params) {
    // This read API authoritatively scopes matches/history to the user's branch.
    const query = new URLSearchParams(params);
    const body = await request('life_slimming.api.server_scripts.life_client360_branch_patient_lookup.run?' + query, { signal, httpMethod: 'GET' });
    const result = body.message;
    if (!result?.ok) throw new Error(result?.message || result?.error || 'Client lookup is unavailable for this account.');
    return result;
  }
  return { call, list, doc, chunks, pool, meta, lookup };
}
