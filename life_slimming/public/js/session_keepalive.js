/* Keep selected users' existing sessions alive while a LIFE page is open. */
(function () {
  if (window.__lifeSessionKeepalive) return;
  // The parent portal already owns the heartbeat for embedded legacy modules.
  try { if (window.parent !== window && window.parent.__lifeSessionKeepalive) return; } catch (_) {}
  window.__lifeSessionKeepalive = true;
  let timer, stopped = false, pending = false, restartRequested = false;
  async function ping() {
    if (stopped || pending) return;
    clearTimeout(timer);
    pending = true;
    let seconds = 60;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch('/api/method/life_slimming.session_policy.heartbeat', {
        credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
      });
      if (response.status === 401 || response.status === 403) { stopped = true; return; }
      if (!response.ok) return;
      const policy = (await response.json()).message;
      if (!policy || policy.idle_logout_exempt !== true) { stopped = true; return; }
      seconds = Math.max(1, Math.min(60, Number(policy.heartbeat_seconds) || 60));
    } catch (_) { /* Retry after temporary network errors; never sign in automatically. */ }
    finally {
      clearTimeout(timeout);
      pending = false;
      if (restartRequested) {
        restartRequested = false;
        stopped = false;
        seconds = 0;
      }
      if (!stopped) timer = setTimeout(ping, seconds * 1000);
    }
  }
  window.addEventListener('online', ping);
  // SPA login does not reload this script after the initial guest request.
  window.addEventListener('life-portal:session-loaded', () => {
    if (pending) { restartRequested = true; return; }
    stopped = false;
    ping();
  });
  window.addEventListener('focus', ping);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) ping(); });
  ping();
})();
