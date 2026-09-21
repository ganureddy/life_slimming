import { createRouter, createWebHistory } from "vue-router";
import { authApi } from "../api/auth";
import menu from "../data/menu.json";
import portalPages from "../data/portalPages.json";

const pageComponents = {
  control: () => import("../pages/ControlPage.vue"),
  billing: () => import("../pages/BillingPage.vue"),
  bdash: () => import("../pages/BranchDashboardPage.vue"),
  conversions: () => import("../pages/ConversionsPage.vue"),
};

export const routes = [
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
        : ["billing", "bdash", "conversions"].includes(item.id)
          ? pageComponents[item.id]
          : () => import("../pages/ModulePage.vue"),
      meta: {
        title: item.label,
        description: item.description,
        icon: item.icon,
      },
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
  // Check guest entry before rendering the workspace, including Vite.
  if (!to.meta.public && !from.name) {
    try {
      const context = await authApi.context();
      if (!context.authenticated) return { name: "login", query: { "redirect-to": "/life_portal" + to.fullPath }, replace: true };
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
router.afterEach((to) => {
  document.title = to.meta.title + " · LIFE Portal";
});
export default router;
