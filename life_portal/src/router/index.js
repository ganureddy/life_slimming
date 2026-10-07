import { ref } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import { session, loadSession } from "../lib/session";
import access from "../../../life_slimming/portal_pages/access.json";
const menu = access.menu;
import portalPages from "../data/portalPages.json";
import PortalSourcePage from "../pages/PortalSourcePage.vue";

// Keep the existing ERP screen active from the portal menu until Vue parity is approved.
const keepLegacyModule = (id) => Boolean(portalPages[id]);

export const routeLoading = ref(false);

const pageComponents = {
  control: () => import("../pages/ControlPage.vue"),
  clireg: () => import("../pages/ClientRegistrationPage.vue"),
  stores360: () => import("../pages/Stores360NativePage.vue"),
  stock: () => import("../pages/StockDashboardNativePage.vue"),
  billing: () => import("../pages/BillingPage.vue"),
  payables: () => import("../pages/PayablesNativePage.vue"),
  conversions: () => import("../pages/ConversionsPage.vue"),
  pricelist: () => import("../pages/PriceListNativePage.vue"),
  conv: () => import("../pages/BranchTargetPage.vue"),
  discountaudit: () => import("../pages/DiscountAuditPage.vue"),
  documents: () => import("../pages/FormsDocumentsPage.vue"),
  appt: () => import("../pages/AppointmentSchedulerPage.vue"),
  salemaster: () => import("../pages/SalesMasterDataPage.vue"),
  empsale: () => import("../pages/EmployeeSaleMasterPage.vue"),
  wlres: () => import("../pages/WeightLossReportPage.vue"),
  service: () => import("../pages/ServicePage.vue"),
  vendors: () => import("../pages/VendorsPage.vue"),
  ccvisit: () => import("../pages/CCVisitReportPage.vue"),
  leads: () => import("../pages/CCDashboardPage.vue"),
  pendbal: () => import("../pages/PendingBalancesPage.vue"),
  receivables: () => import("../pages/PendingBalancesPage.vue"),
  bexp: () => import("../pages/BranchExpenditurePage.vue"),
  approvals: () => import("../pages/ApprovalsPage.vue"),
  approvalsreport: () => import("../pages/ApprovalsPage.vue"),
};

export const routes = [
  {
    path: "/native/billing", name: "billing-native",
    component: () => import("../pages/BillingNativePage.vue"),
    meta: { title: "Billing preview", accessModule: "billing" },
  },
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
    path: "/native/cluster-dashboard", name: "clusterhome-native",
    component: () => import("../pages/ClusterDashboardPage.vue"),
    meta: { title: "Cluster Dashboard preview", accessModule: "clusterhome" },
  },
  {
    path: "/native/stores360", name: "stores360-native",
    component: () => import("../pages/Stores360NativePage.vue"),
    meta: { title: "Stores 360 preview", accessModule: "stores360" },
  },
  {
    path: "/stock-legacy", name: "stock-legacy",
    component: () => import("../pages/PortalSourcePage.vue"),
    meta: { title: "Stock dashboard legacy", accessModule: "stock" },
  },
  {
    path: "/native/pricelist", name: "pricelist-native",
    component: () => import("../pages/PriceListNativePage.vue"),
    meta: { title: "Price-List preview", accessModule: "pricelist" },
  },
  {
    path: "/native/branch-target", name: "conv-native",
    component: () => import("../pages/BranchTargetPage.vue"),
    meta: { title: "Target & Realisation preview", accessModule: "conv" },
  },
  {
    path: "/native/service", name: "service-native",
    component: () => import("../pages/ServicePage.vue"),
    meta: { title: "Service Vue migration preview", accessModule: "service" },
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
      component: keepLegacyModule(item.id)
        ? PortalSourcePage
        : item.id === "control"
          ? pageComponents.control
          : ["clireg", "stores360", "stock", "pricelist", "conv", "documents", "appt", "salemaster", "empsale", "wlres", "vendors", "pendbal", "receivables", "bexp", "ccvisit", "leads", "approvals", "approvalsreport", "service", "payables"].includes(item.id)
            ? pageComponents[item.id]
            : item.id === "discountaudit"
              ? pageComponents.discountaudit
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
    component: keepLegacyModule(id) ? PortalSourcePage : pageComponents[id] || PortalSourcePage,
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
