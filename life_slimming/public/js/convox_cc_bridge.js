/* Only same-origin portal parent messages are accepted. No ConVox credentials here. */
(() => {
  if (window.parent === window) return;
  const origin = window.location.origin;
  let lead = '';
  const requests = new Map();
  function send(type) {
    window.parent.postMessage({ type, ...(lead ? { lead_id: lead } : {}) }, origin);
  }
  window.lifeConvoxSelectLead = (id) => {
    if (typeof id !== 'string' || !id || id.length > 140) return;
    lead = id;
    send('life-convox-select');
  };
  window.lifeConvoxOpenPhone = () => send('life-convox-open');
  window.lifeConvoxStartCall = (id) => {
    if (typeof id !== 'string' || !id || id.length > 140) {
      return Promise.resolve({ success: false, message: 'Select a lead before calling.' });
    }
    const request_id = crypto.randomUUID().replaceAll('-', '');
    return new Promise(resolve => {
      const timeout = setTimeout(() => {
        requests.delete(request_id);
        resolve({ success: false, status: 'UNKNOWN', message: 'Call outcome is unconfirmed. Check the ConVox phone before retrying.' });
      }, 35000);
      requests.set(request_id, { lead: id, resolve, timeout });
      window.parent.postMessage({ type: 'life-convox-call', lead_id: id, request_id }, origin);
    });
  };
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'hdr-btn';
  button.textContent = '☎ Phone';
  button.setAttribute('aria-label', 'Open ConVox phone');
  button.addEventListener('click', () => send('life-convox-open'));
  document.querySelector('.hdr-right')?.prepend(button);
  window.addEventListener('message', (event) => {
    if (event.origin !== origin || event.source !== window.parent) return;
    if (event.data?.type === 'life-convox-call-result') {
      const request = requests.get(event.data.request_id);
      if (!request || event.data.lead_id !== request.lead) return;
      clearTimeout(request.timeout);
      requests.delete(event.data.request_id);
      request.resolve({ success: event.data.success === true, status: event.data.status,
        refno: typeof event.data.refno === 'string' ? event.data.refno : '',
        message: typeof event.data.message === 'string' ? event.data.message : 'Check the ConVox phone for the call result.' });
      return;
    }
    if (event.data?.type !== 'life-convox-find') return;
    const mobile = event.data.mobile;
    if (typeof mobile !== 'string' || !/^[0-9]{10}$/.test(mobile)) return;
    const input = document.getElementById('global-search');
    if (input) {
      input.value = mobile;
      // Also make the search available on small screens for an incoming caller lookup.
      const wrap = input.closest('.hdr-center');
      if (wrap) { wrap.style.display = 'flex'; wrap.style.flexBasis = '100%'; }
      input.focus();
      window.globalSearch?.(mobile);
    }
  });
})();
