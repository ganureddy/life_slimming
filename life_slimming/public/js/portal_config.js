/* Shared by the Vue portal and embedded modules. Change apiBase in this file
 * to move all portal API requests. Empty means the current site's origin.
 * A separate origin must allow credentialed CORS and Frappe session cookies.
 */
window.lifePortalConfig = Object.freeze({
  apiBase: "",
  legacyOrigin: "https://portal.lifescc.com",
});
window.lifePortalNetwork = Object.freeze({
  url(path) {
    return window.lifePortalConfig.apiBase.replace(/\/$/, "") + path;
  },
  credentials() {
    return window.lifePortalConfig.apiBase ? "include" : "same-origin";
  },
});
