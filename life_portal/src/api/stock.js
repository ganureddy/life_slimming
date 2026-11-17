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
  let generation = 0;
  return {
    load(key, task) {
      if (loaded.has(key)) return Promise.resolve();
      if (pending.has(key)) return pending.get(key);
      const started = generation;
      const current = Promise.resolve().then(task).then(result => {
        if (generation === started) loaded.add(key);
        return result;
      }).finally(() => {
        if (pending.get(key) === current) pending.delete(key);
      });
      pending.set(key, current);
      return current;
    },
    clear() {
      // Keep pending promises to join duplicate requests; prevent stale results
      // from marking a section loaded after refresh.
      generation += 1;
      loaded.clear();
    },
  };
}
