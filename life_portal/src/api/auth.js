import { request } from "./http";

export const authApi = {
  context: () =>
    request("life_slimming.api.auth.login_context").then(
      (body) => body.message,
    ),
  login: (credentials, csrfToken) =>
    request("login", { args: credentials, csrfToken }),
  resetPassword: (user, csrfToken) =>
    request("frappe.core.doctype.user.user.reset_password", {
      args: { user },
      csrfToken,
    }),
};

// Portal redirects never leave this SPA, including protocol-relative or encoded URLs.
export function portalDestination(value) {
  if (
    typeof value !== "string" ||
    !value.startsWith("/life_portal") ||
    /[\\\u0000-\u0020]/.test(value)
  )
    return "/life_portal/";
  try {
    const parsed = new URL(value, window.location.origin);
    const path = decodeURIComponent(parsed.pathname);
    if (
      parsed.origin !== window.location.origin ||
      /[\\\u0000-\u0020]/.test(path)
    )
      return "/life_portal/";
    if (path !== "/life_portal" && !path.startsWith("/life_portal/"))
      return "/life_portal/";
    if (path.replace(/\/$/, "") === "/life_portal/login")
      return "/life_portal/";
    return parsed.pathname + parsed.search + parsed.hash;
  } catch {
    return "/life_portal/";
  }
}
export function passwordResetDestination(value) {
  if (typeof value !== "string" || /[\\\u0000-\u0020]/.test(value)) return null;
  try {
    const parsed = new URL(value, window.location.origin);
    return parsed.origin === window.location.origin &&
      parsed.pathname === "/update-password"
      ? parsed.pathname + parsed.search
      : null;
  } catch {
    return null;
  }
}
