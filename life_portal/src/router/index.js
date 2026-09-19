import { createRouter, createWebHistory } from "vue-router";
import menu from "../data/menu.json";

const pageComponents = {
  tasks: () => import("../pages/TasksPage.vue"),
  approvals: () => import("../pages/ApprovalsPage.vue"),
  stores360: () => import("../pages/Stores360Page.vue"),
  bdash: () => import("../pages/BranchDashboardPage.vue"),
  conv: () => import("../pages/ConvPage.vue"),
  empsale: () => import("../pages/EmpsalePage.vue"),
  salemaster: () => import("../pages/SalemasterPage.vue"),
  audit: () => import("../pages/AuditPage.vue"),
  documents: () => import("../pages/DocumentsPage.vue"),
  bexp: () => import("../pages/BexpPage.vue"),
  leads: () => import("../pages/LeadsPage.vue"),
  ccvisit: () => import("../pages/CcvisitPage.vue"),
  campaign: () => import("../pages/CampaignPage.vue"),
  cliinfo: () => import("../pages/CliinfoPage.vue"),
  unjoined: () => import("../pages/UnjoinedPage.vue"),
  appt: () => import("../pages/ApptPage.vue"),
  conversions: () => import("../pages/ConversionsPage.vue"),
  service: () => import("../pages/ServicePage.vue"),
  wlres: () => import("../pages/WlresPage.vue"),
  dietfb: () => import("../pages/DietfbPage.vue"),
  followup: () => import("../pages/FollowupPage.vue"),
  knowledge: () => import("../pages/KnowledgePage.vue"),
  billing: () => import("../pages/BillingPage.vue"),
  accounts: () => import("../pages/AccountsPage.vue"),
  pendbal: () => import("../pages/PendbalPage.vue"),
  payables: () => import("../pages/PayablesPage.vue"),
  receivables: () => import("../pages/ReceivablesPage.vue"),
  gst: () => import("../pages/GstPage.vue"),
  assets: () => import("../pages/AssetsPage.vue"),
  finrep: () => import("../pages/FinrepPage.vue"),
  stock: () => import("../pages/StockPage.vue"),
  buying: () => import("../pages/BuyingPage.vue"),
  vendors: () => import("../pages/VendorsPage.vue"),
  pricelist: () => import("../pages/PricelistPage.vue"),
  employees: () => import("../pages/EmployeesPage.vue"),
  attend: () => import("../pages/AttendPage.vue"),
  payroll: () => import("../pages/PayrollPage.vue"),
  leaves: () => import("../pages/LeavesPage.vue"),
  hrpol: () => import("../pages/HrpolPage.vue"),
  risedash: () => import("../pages/RisedashPage.vue"),
  riseprog: () => import("../pages/RiseprogPage.vue"),
  risewb: () => import("../pages/RisewbPage.vue"),
  riseclients: () => import("../pages/RiseclientsPage.vue"),
  repmaster: () => import("../pages/RepmasterPage.vue"),
  discountaudit: () => import("../pages/DiscountauditPage.vue"),
  approvalsreport: () => import("../pages/ApprovalsreportPage.vue"),
  execdash: () => import("../pages/ExecdashPage.vue"),
  mis: () => import("../pages/MisPage.vue"),
  clusterhome: () => import("../pages/ClusterhomePage.vue"),
  control: () => import("../pages/ControlPage.vue"),
  users: () => import("../pages/UsersPage.vue"),
  masters: () => import("../pages/MastersPage.vue"),
  auditlog: () => import("../pages/AuditlogPage.vue"),
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
      component: pageComponents[item.id] || (() => import("../pages/ModulePage.vue")),
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
router.beforeEach((to) => {
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
