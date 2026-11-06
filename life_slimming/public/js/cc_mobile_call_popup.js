/* Mobile call screen-pop for the embedded /life_portal/leads dashboard. */
(() => {
  if (window.__LIFE_CC_SCREENPOP_V18) return;
  window.__LIFE_CC_SCREENPOP_V18 = true;
  const preference = 'life_cc_pop_auto';
  let auto = true, lastId = '', hiddenId = '', controller, timer, stopped = false;
  let popup, title, name, phone, status, openButton, checkbox, current;
  try { auto = localStorage.getItem(preference) !== '0'; } catch { /* storage unavailable */ }

  function timestamp(value) {
    const text = String(value || '').replace(' ', 'T');
    return Date.parse(text + (/(Z|[+-]\d{2}:?\d{2})$/i.test(text) ? '' : '+05:30'));
  }
  async function openLead(id) {
    if (!id || openButton.disabled) return;
    openButton.disabled = true;
    try {
      if (typeof window.LIFE_CC_OPEN_LEAD !== 'function') throw Error('The dashboard is still loading. Try Open lead again.');
      await window.LIFE_CC_OPEN_LEAD(id);
    } catch (error) {
      status.textContent = error.message || 'Could not open the lead. Try again.';
    } finally { openButton.disabled = false; }
  }
  function createPopup() {
    const style = document.createElement('style');
    style.textContent = '#life-mobile-call{position:fixed;right:18px;bottom:18px;z-index:2147480000;width:330px;max-width:calc(100vw - 36px);box-sizing:border-box;padding:14px;background:#fff;border:2px solid #c9a54a;border-radius:14px;box-shadow:0 14px 40px #0a281e40;color:#174b30;font:14px/1.4 system-ui,sans-serif}#life-mobile-call[hidden]{display:none}#life-mobile-call header{display:flex;justify-content:space-between;gap:10px;margin-bottom:12px}#life-mobile-call p{margin:8px 0}#life-mobile-call label{display:flex;align-items:center;gap:8px;font-size:12px;margin-top:12px}#life-mobile-call button{cursor:pointer}';
    document.head.appendChild(style);
    popup = document.createElement('aside');
    popup.id = 'life-mobile-call';
    popup.setAttribute('aria-live', 'polite');
    popup.hidden = true;
    // Only static markup enters innerHTML. Server-provided values use textContent.
    popup.innerHTML = '<header><strong></strong><button type="button" aria-label="Hide mobile call">×</button></header><strong data-name></strong><p data-phone></p><p data-status></p><button type="button" data-open>Open lead</button><label><input type="checkbox"> Open the lead automatically when a call starts</label>';
    title = popup.querySelector('header strong');
    name = popup.querySelector('[data-name]');
    phone = popup.querySelector('[data-phone]');
    status = popup.querySelector('[data-status]');
    openButton = popup.querySelector('[data-open]');
    checkbox = popup.querySelector('input');
    checkbox.checked = auto;
    popup.querySelector('header button').onclick = () => { hiddenId = current?.id; popup.hidden = true; };
    openButton.onclick = () => openLead(current?.lead);
    checkbox.onchange = () => {
      auto = checkbox.checked;
      try { localStorage.setItem(preference, auto ? '1' : '0'); } catch { /* storage unavailable */ }
    };
    document.body.appendChild(popup);
  }
  async function tick() {
    if (stopped || document.hidden || controller) return;
    controller = new AbortController();
    const timeout = setTimeout(() => controller?.abort(), 10000);
    try {
      const response = await fetch('/api/method/life_cc_mobile_v18', {
        method: 'POST', credentials: 'same-origin', signal: controller.signal,
        lifePortalBackground: true,
        headers: { 'Content-Type': 'application/json', Accept: 'application/json',
          'X-Frappe-CSRF-Token': window.lifePortalModule?.csrf_token || window.frappe?.csrf_token || '' },
        body: JSON.stringify({ action: 'live' }),
      });
      if (!response.ok) throw Error('Mobile call sync failed');
      const result = await response.json();
      if (result.exc_type) throw Error('Mobile call sync failed');
      if (stopped) return;
      current = result.message?.call;
      const now = timestamp(result.message?.now) || Date.now();
      const recent = current?.live || now - timestamp(current?.ended_on || current?.started_on) < 45000;
      if (!current?.id || current.id === hiddenId || !recent) {
        if (popup) popup.hidden = true;
        return;
      }
      if (!popup) createPopup();
      popup.hidden = false;
      title.textContent = current.live ? '📱 ON CALL FROM LIFE APP' : '📱 CALL ENDED';
      name.textContent = current.lead_name || current.lead || 'Lead';
      phone.textContent = (current.lead || '') + ' · ••••' + (current.ph4 || '');
      status.textContent = current.live ? 'Talking' : current.disposition || 'Waiting for result…';
      if (current.live && current.id !== lastId) {
        lastId = current.id;
        if (auto) void openLead(current.lead);
      }
    } catch {
      // Clear stale call information on session/network failures; retry next tick.
      if (popup) popup.hidden = true;
    } finally { clearTimeout(timeout); controller = null; }
  }
  function start() {
    stopped = false;
    clearInterval(timer);
    timer = setInterval(tick, 3000);
    void tick();
  }
  window.addEventListener('pagehide', () => { stopped = true; clearInterval(timer); controller?.abort(); });
  window.addEventListener('pageshow', start);
  document.addEventListener('visibilitychange', tick);
  start();
})();
