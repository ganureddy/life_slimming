/* Shared notification renderer for the portal and its CC dashboard iframe. */
(() => {
  if (window.lifeToast) return;
  function messageText(value) {
    if (value == null) return '';
    if (Array.isArray(value)) return value.map(messageText).filter(Boolean).join('\n');
    if (typeof value === 'object') {
      return messageText(value._server_messages || value.responseJSON || value.message ||
        (value.status === 0 ? 'Cannot reach the server. Check your connection and try again.' : 'The request failed. Please try again.'));
    }
    const text = String(value);
    if (/^[\[{]/.test(text.trim())) {
      try { return messageText(JSON.parse(text)); } catch { /* ordinary text */ }
    }
    const doc = new DOMParser().parseFromString(text.replace(/<br\s*\/?\s*>/gi, '\n'), 'text/html');
    doc.querySelectorAll('script,style').forEach(node => node.remove());
    return doc.body.textContent.trim();
  }
  window.lifeMessageText = messageText;
  window.lifeToast = (value, indicator = 'blue', seconds = 10) => {
    const message = messageText(value);
    if (!message) return;
    try {
      if (window.parent !== window && window.parent.location.origin === location.origin && window.parent.lifeToast) {
        return window.parent.lifeToast(message, indicator, seconds);
      }
    } catch { /* standalone rendering */ }
    const duration = 10000;
    let host = document.getElementById('life-toast-host');
    if (!host) {
      const style = document.createElement('style');
      style.textContent = `#life-toast-host{position:fixed;top:90px;right:20px;z-index:2147483000;width:min(460px,calc(100vw - 24px));max-height:calc(100dvh - 110px);overflow:auto;display:grid;gap:10px;pointer-events:none;font:14px/1.5 Arial,sans-serif}#life-toast-host .life-toast{position:relative;inset:auto;pointer-events:auto;display:grid;grid-template-columns:1fr auto;gap:12px;background:#fff;color:#173e31;border:1px solid #a6c6b6;border-left:6px solid #286e53;border-radius:10px;padding:14px 16px;box-shadow:0 6px 24px #0003;white-space:pre-wrap;overflow-wrap:anywhere}#life-toast-host .life-toast-error{border-color:#be463c;color:#802720;background:#fff5f3}#life-toast-host .life-toast-warning{border-color:#a67915;color:#694c0a;background:#fffbeb}#life-toast-host strong{display:block;margin-bottom:4px}#life-toast-host button{align-self:start;border:0;background:transparent;color:inherit;padding:2px 6px;font:22px Arial;cursor:pointer}@media(max-width:600px){#life-toast-host{top:76px;right:12px;max-height:calc(100dvh - 92px)}}`;
      document.head.appendChild(style);
      host = document.createElement('div'); host.id = 'life-toast-host';
      host.setAttribute('aria-label', 'Notifications');
      document.body.appendChild(host);
    }
    const kind = ['red', 'error'].includes(indicator) ? 'error' : ['gold', 'orange', 'yellow', 'warning'].includes(indicator) ? 'warning' : ['green', 'teal', 'alert-green', 'success'].includes(indicator) ? 'success' : 'info';
    const existing = [...host.children].find(node => node.dataset.message === message && node.dataset.kind === kind);
    if (existing) { existing.restart(); return existing; }
    const toast = document.createElement('div'); toast.className = 'life-toast life-toast-' + kind;
    toast.dataset.message = message; toast.dataset.kind = kind;
    toast.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    const content = document.createElement('div'), title = document.createElement('strong'), body = document.createElement('span');
    title.textContent = { error: 'Unable to complete action', warning: 'Please check', success: 'Update', info: 'Information' }[kind];
    body.textContent = message; content.append(title, body);
    const close = document.createElement('button'); close.type = 'button'; close.textContent = '×'; close.setAttribute('aria-label', 'Dismiss notification');
    let timer;
    close.addEventListener('click', () => { clearTimeout(timer); toast.remove(); });
    toast.restart = () => { clearTimeout(timer); timer = setTimeout(() => toast.remove(), duration); };
    toast.addEventListener('mouseenter', () => clearTimeout(timer));
    toast.addEventListener('mouseleave', toast.restart);
    toast.addEventListener('focusin', () => clearTimeout(timer));
    toast.addEventListener('focusout', toast.restart);
    toast.append(content, close); host.appendChild(toast); toast.restart();
    return toast;
  };
  // Only replace notification dialogs in the CC iframe. Forms/confirmations retain their controls.
  if (window.lifePortalModule?.module === 'leads') {
    window.alert = value => window.lifeToast(value, 'red');
    if (window.frappe) {
      frappe.show_alert = (value, seconds) => window.lifeToast(value, value?.indicator || 'blue', seconds);
      frappe.msgprint = (value, title, indicator) => window.lifeToast(value, value?.indicator || indicator || 'red');
    }
    window.addEventListener('unhandledrejection', event => {
      window.lifeToast(event.reason || 'The action failed. Please try again.', 'red');
    });
  }
})();
