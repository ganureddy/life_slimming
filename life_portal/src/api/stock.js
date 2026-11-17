import { request } from './http';
import { session } from '../lib/session';

// All Stock tabs share this gateway. Join identical requests while one is
// already in flight so mounting a page plus its tab does not hit Frappe twice.
const inFlight = new Map();
let contextCache = null;
let contextCacheAt = 0;

export async function stockAction(action, payload = {}) {
  if (action === 'get_context' && contextCache && Date.now() - contextCacheAt < 60_000) {
    return contextCache;
  }
  const payloadJson = JSON.stringify(payload || {});
  const key = `${String(action || '').trim()}:${payloadJson}`;
  if (inFlight.has(key)) return inFlight.get(key);

  const task = request('life_stock_fast_requests', {
    args: { action, payload: payloadJson },
    csrfToken: session.csrf_token,
  }).then(response => {
    const result = response?.message;
    if (!result || result.ok === false) {
      throw new Error(result?.message || 'Stock service returned an invalid response.');
    }
    if (action === 'get_context') {
      contextCache = result;
      contextCacheAt = Date.now();
    }
    return result;
  }).finally(() => {
    inFlight.delete(key);
  });

  inFlight.set(key, task);
  return task;
}

export function createSectionLoader() {
  const loaded = new Set();
  const pending = new Map();
  return {
    load(key, task) {
      if (loaded.has(key)) return Promise.resolve();
      if (pending.has(key)) return pending.get(key);
      const current = Promise.resolve().then(task).then(result => {
        loaded.add(key);
        return result;
      }).finally(() => pending.delete(key));
      pending.set(key, current);
      return current;
    },
    // Keep in-flight calls: refresh joins them instead of creating a duplicate.
    clear() { loaded.clear(); },
  };
}
