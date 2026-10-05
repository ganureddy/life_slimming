/* Local compatibility adapter for the checked-in ERP Web Pages. */
(() => {
  "use strict";
  const config = window.lifePortalModule;
  const runtime = window.lifePortalConfig || {};
  const remoteOrigin = runtime.legacyOrigin || "https://portal.lifescc.com";
  const legacyPortalRoutes = {
    "/billing-v2": "billing",
    "/client-360-Bhuvan": "cliinfo",
    "/pending-balances-updates-Bhuvan": "pendbal",
    "/branch-visit-report": "ccvisit",
    "/cc-dashboard": "leads",
    "/all-approvals-dashboard": "approvals",
  };
  const apiBase = (runtime.apiBase || "").replace(/\/$/, "");
  const apiOrigin = new URL(apiBase || location.origin).origin;
  frappe.csrf_token = config.csrf_token;
  frappe.session = { ...(frappe.session || {}), user: config.user };
  frappe.user_roles = config.roles || [];
  // Embedded dashboards have no code snippets; do not initialize the legacy highlighter.
  if (frappe.highlight_code_blocks) {
    const highlightCode = frappe.highlight_code_blocks.bind(frappe);
    frappe.highlight_code_blocks = () => {
      if (document.querySelector("pre code")) highlightCode();
    };
  }
  const originalCall = frappe.call.bind(frappe);
  frappe.call = function (options, args, callback) {
    const opts =
      typeof options === "string"
        ? { method: options, args, callback }
        : { ...options };
    const mapped = config.methods[opts.method];
    if (mapped) {
      opts.method = mapped;
      opts.type = "POST";
    }
    if (!opts.url && opts.method)
      opts.url = apiBase + "/api/method/" + opts.method;
    if (apiBase) opts.xhrFields = { ...opts.xhrFields, withCredentials: true };
    return originalCall(opts);
  };

  const migratedMethods = new Set(Object.values(config.methods));
  function isMigrated(input) {
    const url = new URL(input, location.href);
    return (
      url.origin === apiOrigin &&
      migratedMethods.has(
        decodeURIComponent(url.pathname.replace(/^\/api\/method\//, "")),
      )
    );
  }

  function localUrl(input) {
    const url = new URL(input, location.href);
    if (
      url.origin !== location.origin &&
      url.origin !== remoteOrigin &&
      url.origin !== apiOrigin
    )
      return input;
    const prefix = "/api/method/";
    if (url.pathname.startsWith(prefix)) {
      const method = decodeURIComponent(url.pathname.slice(prefix.length));
      url.pathname = prefix + (config.methods[method] || method);
    }
    return (
      (url.pathname.startsWith("/api/") ? apiBase : "") +
      url.pathname +
      url.search +
      url.hash
    );
  }
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, options) => {
    if (input instanceof Request) {
      const mapped = new URL(localUrl(input.url), location.href).href;
      input = mapped === input.url ? input : new Request(mapped, input);
    } else input = localUrl(String(input));
    const headers = new Headers(
      options?.headers ||
        (input instanceof Request ? input.headers : undefined),
    );
    const url = new URL(
      input instanceof Request ? input.url : input,
      location.href,
    );
    if (url.origin === apiOrigin && url.pathname.startsWith("/api/"))
      headers.set("X-Frappe-CSRF-Token", config.csrf_token);
    const method =
      options?.method || (input instanceof Request ? input.method : "GET");
    return originalFetch(input, {
      ...options,
      ...(url.origin === apiOrigin && apiBase
        ? { credentials: "include" }
        : {}),
      headers,
      method:
        isMigrated(url.href) && method.toUpperCase() === "GET"
          ? "POST"
          : method,
    });
  };
  const originalOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, ...args) {
    const mapped = localUrl(String(url));
    const upgrade = method.toUpperCase() === "GET" && isMigrated(mapped);
    const result = originalOpen.call(
      this,
      upgrade ? "POST" : method,
      mapped,
      ...args,
    );
    if (apiBase && new URL(mapped, location.href).origin === apiOrigin)
      this.withCredentials = true;
    if (upgrade)
      this.setRequestHeader("X-Frappe-CSRF-Token", config.csrf_token);
    return result;
  };

  // Route known legacy and current portal links through the parent SPA.
  // Keep normal new-tab/download behavior and all record/filter parameters.
  document.addEventListener("click", (event) => {
    const anchor = event.target.closest?.("a[href]");
    if (!anchor || event.defaultPrevented || event.button !== 0 || anchor.hasAttribute('download')) return;
    if (anchor.getAttribute?.('href')?.startsWith('#')) return;
    const url = new URL(anchor.href, location.href);
    if (![location.origin, remoteOrigin].includes(url.origin)) return;
    const pathname = url.pathname.replace(/\/$/, '');
    let module = config.routes[pathname] || legacyPortalRoutes[pathname];
    if (pathname === '/life_portal_module') module = url.searchParams.get('module');
    if (['/life-home', '/life_portal'].includes(pathname)) {
      module = url.searchParams.get('view') || 'home';
      url.searchParams.delete('view');
    }
    // Frappe Desk routes are not portal pages. Leave them alone only when no
    // portal equivalent exists; known legacy portal URLs always stay in the SPA.
    if (!module && pathname.startsWith('/app/')) return;
    if (!module && !pathname.startsWith('/life_portal/')) return;
    url.searchParams.delete('module');
    url.searchParams.delete('embed');
    const target = (module ? '/life_portal/' + encodeURIComponent(module) : pathname) + url.search + url.hash;
    anchor.href = target;
    const self = !anchor.target || ['_self', '_top', '_parent'].includes(anchor.target);
    if (self) anchor.target = '_top';
    if (!self || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (window.parent === window) return;
    event.preventDefault();
    // A report embedded inside another module must address the outer workspace.
    if (window.parent !== window.top) window.top.location.assign(target);
    else window.parent.postMessage({ type: 'life-portal:navigate', path: target }, location.origin);
  });
})();
