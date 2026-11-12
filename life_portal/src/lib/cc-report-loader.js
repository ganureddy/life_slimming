export function createReportLoader(fetchReport, identity, ttl = 15 * 60 * 1000) {
  const cache = new Map(), pending = new Map();
  let login;
  return async function load(args, signal, refresh = false) {
    if (signal?.aborted) throw new DOMException('Request aborted', 'AbortError');
    const current = JSON.stringify(identity());
    if (current !== login) { cache.clear(); pending.clear(); login = current; }
    const key = JSON.stringify([current, Object.entries(args).sort(([a], [b]) => a.localeCompare(b))]);
    const saved = cache.get(key);
    if (!refresh && saved && Date.now() - saved.at < ttl) return saved.data;
    if (!pending.has(key)) {
      const promise = Promise.resolve().then(() => fetchReport(args)).then(data => {
        if (login === current) {
          cache.set(key, { at: Date.now(), data });
          if (cache.size > 24) cache.delete(cache.keys().next().value);
        }
        return data;
      }).finally(() => { if (pending.get(key) === promise) pending.delete(key); });
      pending.set(key, promise);
    }
    // Cancelling one tab must not cancel a shared request needed by another tab.
    const promise = pending.get(key);
    if (!signal) return promise;
    return new Promise((resolve, reject) => {
      const abort = () => reject(new DOMException('Request aborted', 'AbortError'));
      signal.addEventListener('abort', abort, { once: true });
      promise.then(value => { if (!signal.aborted) resolve(value); }, reject)
        .finally(() => signal.removeEventListener('abort', abort));
    });
  };
}
