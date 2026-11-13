import { ref } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import { session, loadSession, canAccessTab } from "../lib/session";
import access from "../../../life_slimming/portal_pages/access.json";
const menu = access.menu;
import { reportTabs, reportAliases, reportRoute } from '../lib/cc-report-navigation';
import { ccTabs, ccPagePath, ccRoute } from '../lib/cc-navigation';
import portalPages from "../data/portalPages.json";
import PortalSourcePage from "../pages/PortalSourcePage.vue";

// The CC Dashboard uses native Vue tabs; other mapped modules retain their legacy pages.
const nativeModules = new Set(["leads", "ccvisit"]);
const keepLegacyModule = (id) => Boolean(portalPages[id]) && !nativeModules.has(id);

const ccPages = {
  dashboard: () => import('../components/cc/tabs/CCDashboardTab.vue'),
  testing: () => import('../components/cc/tabs/CCTestingTab.vue'),
  queue: () => import('../components/cc/tabs/CCQueueTab.vue'),
  followup: () => import('../components/cc/tabs/CCFollowupTab.vue'),
  create: () => import('../components/cc/tabs/CCCreateLeadTab.vue'),
  assign: () => import('../components/cc/tabs/CCAssignTab.vue'),
  duplicates: () => import('../components/cc/tabs/CCDuplicatesTab.vue'),
  worksheet: () => import('../components/cc/tabs/CCWorksheetTab.vue'),
  distribution: () => import('../components/cc/tabs/CCDistributionTab.vue'),
  tl: () => import('../components/cc/tabs/CCTlTab.vue'),
  reports: () => import('../components/cc/tabs/CCReportsTab.vue'),
  scripts: () => import('../components/cc/tabs/CCScriptsTab.vue'),
  faq: () => import('../components/cc/tabs/CCFaqTab.vue'),
  treatments: () => import('../components/cc/tabs/CCTreatmentsTab.vue'),
  objections: () => import('../components/cc/tabs/CCObjectionsTab.vue'),
  branches: () => import('../components/cc/tabs/CCBranchesTab.vue'),
  doctors: () => import('../components/cc/tabs/CCDoctorsTab.vue'),
};

export const routeLoading = ref(false);

const pageComponents = {
  tasks: () => import("../pages/TaskManagerPage.vue"),
  unjoined: () => import("../pages/UnjoinedClientsPage.vue"),
  clusterhome: () => import("../pages/ClusterDashboardPage.vue"),
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

const reportPages={
 visits:()=>import('../components/cc/reports/CCBranchVisitsPage.vue'),
 agents:()=>import('../components/cc/reports/CCAgentPerformancePage.vue'),
 marketing:()=>import('../components/cc/reports/CCMarketingReportPage.vue'),
 consultants:()=>import('../components/cc/reports/CCConsultantReportPage.vue'),
 cluster:()=>import('../components/cc/reports/CCClusterReportPage.vue'),
 agent360:()=>import('../components/cc/reports/CCActivityPage.vue'),
 journey:()=>import('../components/cc/reports/CCJourneyPage.vue'),
};
export const routes = [
  {path:'/control/access',name:'control-access',component:()=>import('../pages/ControlPage.vue'),meta:{title:'Role & tab access',accessModule:'control'}},
  {path:'/agent-360',name:'agent-360',component:()=>import('../pages/CCAgent360Page.vue'),meta:{title:'Agent 360',accessModule:'ccvisit',standaloneAgent360:true}},
  { path:'/ccvisit', component:pageComponents.ccvisit, meta:{title:'Branch Visit Report',accessModule:'ccvisit'}, children:[
    ...reportTabs.map(tab=>({path:tab.path,name:tab.name,component:reportPages[tab.key],meta:{reportTab:tab.key,title:tab.label,accessModule:'ccvisit'}})),
    ...[['convox','convox'],['no-follow-up','nofollowup'],['untouched','untouched']].map(([path,sub])=>({path:'agents/'+path,name:'ccvisit-agents-'+sub,component:reportPages.agents,meta:{reportTab:'agents',agentSubtab:sub,title:'Agent Report',accessModule:'ccvisit'}})),
  ]},

  { path: "/cc-invoices", name: "cc-invoices", component: () => import("../pages/CCInvoicesPage.vue"), meta: { title: "Invoices / Bills", accessModule: "leads" } },
  { path: "/native/receivables", name: "receivables-native", component: () => import("../pages/PendingBalancesPage.vue"), meta: { title: "Receivables Vue preview", accessModule: "receivables" } },
  { path: "/native/pending-balances", name: "pendbal-native", component: () => import("../pages/PendingBalancesPage.vue"), meta: { title: "Pending Balances Vue preview", accessModule: "pendbal" } },
  { path: "/native/branch-expenditure", name: "bexp-native", component: () => import("../pages/BranchExpenditurePage.vue"), meta: { title: "Branch Expenditure Vue preview", accessModule: "bexp" } },
  { path: "/native/client-info", name: "cliinfo-native", component: () => import("../pages/ClientInfoPage.vue"), meta: { title: "Client Info Vue preview", accessModule: "cliinfo" } },
  { path: "/native/appointments", name: "appt-native", component: () => import("../pages/AppointmentSchedulerPage.vue"), meta: { title: "Client Appointment Scheduler", accessModule: "appt" } },
  { path: "/native/employee-sales", name: "empsale-native", component: () => import("../pages/EmployeeSaleMasterPage.vue"), meta: { title: "Employee Sale Master", accessModule: "empsale" } },
  { path: "/native/discount-audit", name: "discountaudit-native", component: () => import("../pages/DiscountAuditPage.vue"), meta: { title: "Discount Invoice & Collection Report", accessModule: "discountaudit" } },
  {
    path: "/native/client-registration", name: "clireg-native",
    component: () => import("../pages/ClientRegistrationPage.vue"),
    meta: { title: "New Client Registration", accessModule: "clireg" },
  },
  {
    path: "/native/tasks", name: "tasks-native",
    component: () => import("../pages/TaskManagerPage.vue"),
    meta: { title: "Task Manager & Ticket System preview", accessModule: "tasks" },
  },
  {
    path: "/native/sales-master", name: "salemaster-native",
    component: () => import("../pages/SalesMasterDataPage.vue"),
    meta: { title: "Sales Master Data", accessModule: "salemaster" },
  },
  {
    path: "/native/documents", name: "documents-native",
    component: () => import("../pages/FormsDocumentsPage.vue"),
    meta: { title: "Forms & Documents", accessModule: "documents" },
  },
  {
    path: "/native/weight-loss", name: "wlres-native",
    component: () => import("../pages/WeightLossReportPage.vue"),
    meta: { title: "Client Weight Loss Info", accessModule: "wlres" },
  },
  {
    path: "/native/unjoined", name: "unjoined-native",
    component: () => import("../pages/UnjoinedClientsPage.vue"),
    meta: { title: "Unjoined Clients", accessModule: "unjoined" },
  },
  {
    path: "/native/cc-live-tv", name: "cc-live-tv",
    component: () => import("../components/cc/CCLiveTV.vue"),
    meta: { title: "CC Live TV", accessModule: "leads" },
  },
  {
    path: "/native/billing", name: "billing-native",
    component: () => import("../pages/BillingNativePage.vue"),
    meta: { title: "Billing preview", accessModule: "billing" },
  },
  {
    path: "/native/cc-dashboard", name: "leads-native",
    redirect: to => ({ name: "leads", query: to.query }),
  },
  {
    path: "/native/cc-visit-report", name: "ccvisit-native",
    redirect: to => reportRoute(reportAliases[String(to.query.tab||to.hash.slice(1))]||'visits',to.query),
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
    redirect: to => ccRoute("followup", { lead: to.params.leadId, history: "convox" }),
  },
  {
    path: "/convox-history", name: "convox-history-index",
    redirect: { name: "leads" },
  },
  {
    path: "/cc-roster", name: "cc-roster",
    component: () => import("../pages/CCRosterPage.vue"),
    meta: { title: "CC ROASTER", accessModule: "leads" },
  },
  {
    path: "/cc-appointments", name: "cc-appointments",
    component: () => import("../pages/CCAppointmentsPage.vue"),
    meta: { title: "CC Appointments", accessModule: "leads" },
  },
  {
    path: '/leads', component: pageComponents.leads,
    meta: { title: 'CC Dashboard', accessModule: 'leads' },
    children: ccTabs.map(tab => ({
      path: ccPagePath(tab.view) + (tab.view === 'followup' ? '/:leadId?' : ''),
      name: tab.view === 'dashboard' ? 'leads' : 'cc-leads-' + tab.view,
      component: ccPages[tab.view],
      meta: { title: tab.label, accessModule: 'leads', ccView: tab.view },
    })),
  },
  ...menu
    .flatMap((group) => group.items)
    .filter((item) => !["home", "leads", "ccvisit"].includes(item.id))
    .map((item) => ({
      path: "/" + item.id,
      name: item.id,
      component: keepLegacyModule(item.id)
        ? PortalSourcePage
        : nativeModules.has(item.id)
          ? pageComponents[item.id]
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
        title: item.id === "ccvisit" ? "Agent 360" : item.label,
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
  if(to.meta.accessModule==='ccvisit'&&(to.query.tab||to.hash)){const tab=reportAliases[String(to.query.tab||to.hash.slice(1))];if(tab)return {...reportRoute(tab,to.query),replace:true};}
  // Retain shared links to retired dashboard tabs without loading duplicate views.
  if (['leads', 'leads-native'].includes(to.name) && ['appointments', 'agent360', 'attendance'].includes(to.query.view)) {
    const { view, ...query } = to.query;
    return { name: view === 'appointments' ? 'cc-appointments' : view === 'agent360' ? 'ccvisit' : 'leads', query, replace: true };
  }
  if (to.meta.accessModule === 'leads' && to.query.view && ccTabs.some(tab => tab.view === to.query.view)) {
    return { ...ccRoute(to.query.view, to.query), replace: true };
  }
  if (to.name === 'cc-leads-followup' && to.query.lead && !to.params.leadId) return { ...ccRoute('followup', to.query), replace: true };
  // Check guest entry before rendering the workspace, including Vite.
  if (!to.meta.public && !from.name) {
    try {
      await loadSession();
      if (!session.user) return { name: "login", query: { "redirect-to": "/life_portal" + to.fullPath }, replace: true };
    } catch {
      return { name: "login", query: { "redirect-to": "/life_portal" + to.fullPath }, replace: true };
    }
  }
  const accessTab=to.meta.ccView||(to.meta.standaloneAgent360?'standalone':to.meta.agentSubtab||to.meta.reportTab)||({'cc-invoices':'invoices','cc-roster':'roster','cc-appointments':'appointments','cc-live-tv':'live-tv'})[to.name];
  const tabModule=to.meta.reportTab||to.meta.standaloneAgent360?'ccvisit':accessTab?'leads':null;
  if(tabModule&&accessTab&&!canAccessTab(tabModule,accessTab)){
    if(tabModule==='ccvisit'){const first=reportTabs.find(tab=>canAccessTab('ccvisit',tab.key));if(first)return {...reportRoute(first.key,to.query),replace:true};if(canAccessTab('ccvisit','standalone'))return {name:'agent-360',query:to.query,replace:true};}
    else {const first=ccTabs.find(tab=>canAccessTab('leads',tab.view)&&(!tab.manager||['System Manager','Call Center Export','Sales Manager'].some(role=>session.roles.includes(role))));if(first)return {...ccRoute(first.view,to.query),replace:true};}
    return {name:'home',replace:true};
  }
  const ccTab=ccTabs.find(tab=>tab.view===to.meta.ccView);
  if(ccTab?.manager&&!['System Manager','Call Center Export','Sales Manager'].some(role=>session.roles.includes(role)))return ccRoute('dashboard');
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
