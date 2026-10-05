import { ref } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import { session, loadSession } from "../lib/session";
import access from "../../../life_slimming/portal_pages/access.json";
const menu = access.menu;
import portalPages from "../data/portalPages.json";

export const routeLoading = ref(false);

const pageComponents = {
  control: () => import("../pages/ControlPage.vue"),
  billing: () => import("../pages/BillingPage.vue"),
  conversions: () => import("../pages/ConversionsPage.vue"),
};

export const routes = [
  {
    path: "/native/cc-dashboard", name: "leads-native",
    component: () => import("../pages/CCDashboardPage.vue"),
    meta: { title: "CC Dashboard preview", accessModule: "leads" },
  },
  {
    path: "/native/cc-visit-report", name: "ccvisit-native",
    component: () => import("../pages/CCVisitReportPage.vue"),
    meta: { title: "CC Visit Report preview", accessModule: "ccvisit" },
  },
  {
    path: "/login",
    name: "login",
    component: () => import("../pages/LoginPage.vue"),
    meta: { title: "Sign in", public: true },
  },
  {
    path: "/",
    name: "home",
    component: () => import("../pages/HomePage.vue"),
    meta: { title: "Home" },
  },
  {
    path: "/leads/:leadId/convox", name: "convox-history",
    component: () => import("../pages/ConvoxHistoryPage.vue"),
    meta: { title: "ConVox call details", accessModule: "leads" },
  },
  {
    path: "/convox-history", name: "convox-history-index",
    component: () => import("../pages/ConvoxHistoryPage.vue"),
    meta: { title: "ConVox history", accessModule: "leads" },
  },
  {
    path: "/cc-appointments", name: "cc-appointments",
    component: () => import("../pages/CCAppointmentsPage.vue"),
    meta: { title: "CC Appointments", accessModule: "leads" },
  },
  ...menu
    .flatMap((group) => group.items)
    .filter((item) => item.id !== "home")
    .map((item) => ({
      path: "/" + item.id,
      name: item.id,
      component: item.id === "control"
        ? pageComponents.control
        : portalPages[item.id]
        ? () => import("../pages/PortalSourcePage.vue")
        : ["billing", "conversions"].includes(item.id)
          ? pageComponents[item.id]
          : () => import("../pages/ModulePage.vue"),
      meta: {
        title: item.label,
        description: item.description,
        icon: item.icon,
      },
    })),
  ...Object.entries(access.children).map(([id, entry]) => ({
    path: "/" + id, name: id,
    component: () => import("../pages/PortalSourcePage.vue"),
    meta: { title: entry.title },
  })),
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("../pages/NotFoundPage.vue"),
    meta: { title: "Page not found" },
  },
];
const router = createRouter({
  history: createWebHistory("/life_portal/"),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});
router.beforeEach(async (to, from) => {
  routeLoading.value = true;
  // Check guest entry before rendering the workspace, including Vite.
  if (!to.meta.public && !from.name) {
    try {
      await loadSession();
      if (!session.user) return { name: "login", query: { "redirect-to": "/life_portal" + to.fullPath }, replace: true };
    } catch {
      return { name: "login", query: { "redirect-to": "/life_portal" + to.fullPath }, replace: true };
    }
  }
  // Accept old portal links without taking over the live /life-home route.
  if (
    to.path === "/" &&
    typeof to.query.view === "string" &&
    router.hasRoute(to.query.view)
  ) {
    const { view, ...query } = to.query;
    return { name: view, query, replace: true };
  }
});
router.onError(() => { routeLoading.value = false; });
router.afterEach((to) => {
  routeLoading.value = false;
  document.title = to.meta.title + " · LIFE Portal";
});
export default router;
