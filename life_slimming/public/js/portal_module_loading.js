/* Forward ERP request activity to the one loader in the parent workspace. */
(() => {
  'use strict';
  if (window.parent === window) return;
  let pending = 0;
  let ready = false;
  let timer;
  const config = window.lifePortalModule;
  function report() {
    clearTimeout(timer);
    timer = setTimeout(() => window.parent.postMessage({
      type: 'life-portal:loading', module: config.module, busy: !ready || pending > 0,
    }, location.origin), pending ? 0 : 120);
  }
  function begin() {
    pending++;
    report();
    let finished = false;
    return () => {
      if (finished) return;
      finished = true;
      pending--;
      report();
    };
  }
  function isApi(input) {
    const url = new URL(input, location.href);
    const apiOrigin = new URL(window.lifePortalConfig?.apiBase || location.origin).origin;
    return [location.origin, apiOrigin].includes(url.origin) && url.pathname.startsWith('/api/');
  }
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input, options) => {
    const done = isApi(input instanceof Request ? input.url : String(input)) ? begin() : () => {};
    try { return await originalFetch(input, options); }
    finally { done(); }
  };
  const open = XMLHttpRequest.prototype.open;
  const send = XMLHttpRequest.prototype.send;
  const apiRequests = new WeakMap();
  XMLHttpRequest.prototype.open = function (method, url, ...args) {
    const result = open.call(this, method, url, ...args);
    apiRequests.set(this, isApi(String(url)));
    return result;
  };
  XMLHttpRequest.prototype.send = function (...args) {
    if (!apiRequests.get(this)) return send.apply(this, args);
    const done = begin();
    this.addEventListener('loadend', done, { once: true });
    try { return send.apply(this, args); }
    catch (error) { done(); throw error; }
  };
  window.addEventListener('load', () => { ready = true; report(); }, { once: true });
  report();
})();
