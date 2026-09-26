// The runtime setting is shared with the embedded ERP modules.
export function apiUrl(path) {
  return window.lifePortalNetwork.url(path);
}
export function apiCredentials() {
  return window.lifePortalNetwork.credentials();
}
