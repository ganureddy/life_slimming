import { request } from './http';
import { session } from '../lib/session';

// Deduplicate identical concurrent requests. Do not cache business data here:
// approvals, receipts and stock balances must always be refreshable.
const inFlight = new Map();
const CONTEXT_TTL_MS = 60_000;
let contextCache = null;
let contextCacheAt = 0;
let contextUser = '';

export function invalidateStockContext() {
  contextCache = null;
  contextCacheAt = 0;
  contextUser = '';
}

export async function stockAction(action, payload = {}) {
  const actionName = String(action || '').trim();
  const user = String(session.user || session.user_id || '');
  if (actionName === 'get_context' && contextCache &&
      contextUser === user && Date.now() - contextCacheAt < CONTEXT_TTL_MS) {
    return contextCache;
  }

  const payloadJson = JSON.stringify(payload || {});
  const key = `${user}:${actionName}:${payloadJson}`;
  if (inFlight.has(key)) return inFlight.get(key);

  const task = request('life_stock_fast_requests', {
    args: { action: actionName, payload: payloadJson },
    csrfToken: session.csrf_token,
  }).then(response => {
    const result = response?.message;
    if (!result || result.ok === false) {
      throw new Error(result?.message || 'Stock service returned an invalid response.');
    }
    if (actionName === 'get_context') {
      contextCache = result;
      contextCacheAt = Date.now();
      contextUser = user;
    }
    return result;
  }).finally(() => {
    if (inFlight.get(key) === task) inFlight.delete(key);
  });

  inFlight.set(key, task);
  return task;
}

// Each dashboard section is loaded once until a deliberate refresh.
// In-flight work is joined rather than repeated. The generation counter stops
// old work from marking a newly refreshed section as already loaded.
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
        if (started === generation) loaded.add(key);
        return result;
      }).finally(() => {
        if (pending.get(key) === current) pending.delete(key);
      });
      pending.set(key, current);
      return current;
    },
    clear() {
      generation += 1;
      loaded.clear();
      // Keep pending requests so refresh joins them, rather than duplicating
      // their API calls. Their completion will not mark the new generation loaded.
    },
  };
}