import { reactive, computed } from "vue";
import { call } from "./api";
import access from "../../../life_slimming/portal_pages/access.json";
const menu = access.menu;

export const session = reactive({
  loading: true,
  error: "",
  status: null,
  user: "",
  session_id: "",
  full_name: "",
  roles: [],
  portal_role: "",
  csrf_token: "",
  access_config: null,
});
export const labels = access.labels;
export const groupRoles = access.group_roles;
export const roleKey = computed(() => {
  if (
    session.user === "Administrator" ||
    session.roles.includes("System Manager")
  )
    return "IT";
  return (
    Object.keys(labels).find(
      (key) =>
        key === session.portal_role || labels[key] === session.portal_role,
    ) || ""
  );
});
export const roleLabel = computed(() => labels[roleKey.value] || "Portal user");
export const initials = computed(() =>
  session.full_name
    .split(/\s+/)
    .map((word) => word[0])
    .join("")
    .slice(0, 2)
    .toUpperCase(),
);
export function canSee(item, group) {
  if (!session.user || session.error) return false;
  if (item.id === "home") return true;
  const key = roleKey.value;
  const cfg = session.access_config?.[key];
  if (cfg && typeof cfg === "object" && !Array.isArray(cfg)) {
    if (Array.isArray(cfg.show) && cfg.show.includes(item.id)) return true;
    if (Array.isArray(cfg.hide) && cfg.hide.includes(item.id)) return false;
    return (
      cfg.groups === "ALL" ||
      (Array.isArray(cfg.groups) && cfg.groups.includes(group))
    );
  }
  return ["IT", "MD"].includes(key) || (groupRoles[key] || []).includes(group);
}
export const visibleMenu = computed(() =>
  menu
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => canSee(item, group.label)),
    }))
    .filter((group) => group.items.length),
);
export function canAccessModule(module) {
  const parent = access.children[module]?.parent || module;
  return visibleMenu.value.some(group => group.items.some(item => item.id === parent));
}
export async function loadSession() {
  session.loading = true;
  session.error = "";
  session.status = null;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    Object.assign(session, await call("life_slimming.api.portal.bootstrap", undefined, { signal: controller.signal }));
  } catch (error) {
    session.user = "";
    session.error = error.name === "AbortError" ? "Loading took too long. Please check your connection and try again." : error.message;
    session.status = error.status;
  } finally {
    clearTimeout(timeout);
    session.loading = false;
  }
}
export function loginUrl() {
  return (
    "/life_portal/login?redirect-to=" +
    encodeURIComponent(window.location.pathname + window.location.search)
  );
}
