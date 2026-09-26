import { reactive, computed } from "vue";
import { call } from "./api";
import menu from "../data/menu.json";

export const session = reactive({
  loading: true,
  error: "",
  status: null,
  user: "",
  full_name: "",
  roles: [],
  portal_role: "",
  csrf_token: "",
  access_config: null,
});
export const labels = {
  IT: "IT Admin",
  MD: "MD",
  CEO: "CEO",
  COO: "COO",
  C00: "C00",
  CGO: "CGO",
  CH: "Cluster Head",
  BM: "Branch Manager",
  AC: "Accounts",
  CC: "Call Centre",
  DR: "Doctor",
  FO: "Front Office",
  HR: "HR",
  Therapist: "Therapist",
  Dietitian: "Dietitian",
  STORES: "Stores",
};
export const groupRoles = {
  CEO: [
    "MAIN",
    "BRANCH HOME",
    "CRM & CALL CENTRE",
    "CLIENTS & CLINICAL",
    "BILLING & ACCOUNTS",
    "REPORTS & MIS",
    "LIFE RISE",
  ],
  COO: [
    "MAIN",
    "BRANCH HOME",
    "CRM & CALL CENTRE",
    "CLIENTS & CLINICAL",
    "BILLING & ACCOUNTS",
    "STOCK & PURCHASE",
    "REPORTS & MIS",
    "LIFE RISE",
  ],
  CGO: [
    "MAIN",
    "BRANCH HOME",
    "CRM & CALL CENTRE",
    "CLIENTS & CLINICAL",
    "BILLING & ACCOUNTS",
    "REPORTS & MIS",
  ],
  CH: [
    "MAIN",
    "BRANCH HOME",
    "CRM & CALL CENTRE",
    "CLIENTS & CLINICAL",
    "REPORTS & MIS",
    "LIFE RISE",
  ],
  BM: [
    "MAIN",
    "BRANCH HOME",
    "CLIENTS & CLINICAL",
    "BILLING & ACCOUNTS",
    "STOCK & PURCHASE",
    "CRM & CALL CENTRE",
  ],
  AC: ["MAIN", "BILLING & ACCOUNTS", "STOCK & PURCHASE", "REPORTS & MIS"],
  CC: ["MAIN", "CRM & CALL CENTRE", "CLIENTS & CLINICAL"],
  DR: ["MAIN", "CLIENTS & CLINICAL"],
  Therapist: ["MAIN", "CLIENTS & CLINICAL", "BILLING & ACCOUNTS"],
  Dietitian: ["MAIN", "CLIENTS & CLINICAL", "BILLING & ACCOUNTS"],
  FO: ["MAIN", "CLIENTS & CLINICAL", "BILLING & ACCOUNTS", "CRM & CALL CENTRE"],
  HR: ["MAIN", "HR & PAYROLL", "REPORTS & MIS"],
  STORES: ["MAIN", "STOCK & PURCHASE"],
};
groupRoles.C00 = groupRoles.COO;
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
  if (cfg && typeof cfg === "object") {
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
export async function loadSession() {
  session.loading = true;
  session.error = "";
  session.status = null;
  try {
    Object.assign(session, await call("life_slimming.api.portal.bootstrap"));
  } catch (error) {
    session.user = "";
    session.error = error.message;
    session.status = error.status;
  } finally {
    session.loading = false;
  }
}
export function loginUrl() {
  return (
    "/life_portal/login?redirect-to=" +
    encodeURIComponent(window.location.pathname + window.location.search)
  );
}
