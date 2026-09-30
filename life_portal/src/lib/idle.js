export const WARNING_MS = 57 * 60 * 1000;
export const TIMEOUT_MS = 60 * 60 * 1000;

// Wall-clock deadlines survive throttled tabs, reloads and device sleep.
export function createIdleTimer({ now = Date.now, read, write, warning, expire }) {
  let last = now(), ended = false;
  function sync() {
    const saved = read();
    if (saved?.expired) return false;
    if (Number.isFinite(saved?.last) && saved.last <= now()) last = Math.max(last, saved.last);
    return true;
  }
  const saved = read();
  if (Number.isFinite(saved?.last) && saved.last <= now()) last = saved.last;
  else write({ last });
  function check() {
    if (ended) return false;
    if (!sync() || now() - last >= TIMEOUT_MS) {
      ended = true;
      write({ last, expired: true });
      expire();
      return false;
    }
    warning(now() - last >= WARNING_MS ? Math.ceil((TIMEOUT_MS - (now() - last)) / 1000) : 0);
    return true;
  }
  function activity() {
    if (!check()) return;
    last = now();
    write({ last });
    warning(0);
  }
  return { check, activity };
}
