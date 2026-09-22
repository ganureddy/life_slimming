/* Local compatibility adapter for the checked-in ERP Web Pages. */
(() => {
  "use strict";
  const config = window.lifePortalModule;
  const runtime = window.lifePortalConfig || {};
  const remoteOrigin = runtime.legacyOrigin || "https://portal.lifescc.com";
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

  // Preserve navigation between exported forms without leaving the local site.
  document.addEventListener("click", (event) => {
    const anchor = event.target.closest?.("a[href]");
    if (!anchor || event.defaultPrevented || event.button !== 0) return;
    const url = new URL(anchor.href, location.href);
    if (![location.origin, remoteOrigin].includes(url.origin)) return;
    const module = config.routes[url.pathname];
    if (!module) return;
    url.searchParams.set("module", module);
    anchor.href =
      "/life_portal_module?" + url.searchParams.toString() + url.hash;
  });
})();
