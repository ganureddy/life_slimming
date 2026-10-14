# Native Vue rewrite coverage — 13 October 2026

The requested full migration is **not complete**. Seven of the 39 mapped legacy sources now use native Vue state, templates and event handlers and have passed mocked desktop/mobile workflow tests. The other 32 sources remain on their working legacy routes; existing Vue previews are not proof of complete parity. Billing and live Home are tracked separately because they are outside the legacy module manifest.

## Native routes implemented and tested

| Module | Source | Native component | Workflow verification |
|---|---|---|---|
| Unjoined Clients | unjoined-data | UnjoinedClientsPage.vue | Five cohorts/four tabs, filters, linked details/attachments, masking, follow-up insert/save, required dates, duplicate protection, photo upload, Excel export |
| Weight Loss | client-weight-loss-info | WeightLossReportPage.vue | Legacy markup/styles, monthly and lifetime weights, new joiners, attended older plans, completed/cancelled exclusion, multi-branch deduplication, client selection, Excel exports, errors/retry |
| Cluster Dashboard | cluster-head-dashboard | ClusterDashboardPage.vue | Legacy markup/styles, native mapped API with CSRF, date/cluster filters, totals, empty/denied states, retry |
| Target & Realisation | branch-home-target | BranchTargetPage.vue | Legacy KPI/accordion/chart/table layouts, elapsed days, cycle presets, branch changes and net-collection formula |
| Price List | price-list | PriceListNativePage.vue | Legacy tab/table/modal styling, therapy/category and package searches, offer precedence, regular/LIFErise split, package children and rich descriptions |

| Forms & Documents | v | FormsDocumentsPage.vue | Seven categories, permitted document reads, child-attachment field fallbacks, parent counts, concurrent tab loading, document actions, empty/denied states and retry |
| Sales Master Data | sales-master-data | SalesMasterDataPage.vue / useSalesMaster.js | Searchable selectors, date/amount/employee filters, permitted-branch merging, original report row indexes, GST normalization, pagination/totals, filter refresh before download, client-side restricted-branch exports and server XLSX/CSV exports |

## Remaining mapped sources

| Source | Portal modules | Existing Vue preview |
|---|---|---|
| stores-360 | stores360 | Stores360NativePage.vue |
| task-management | tasks | No native component |
| employee-sale-master-data | empsale | EmployeeSaleMasterPage.vue |
| audit | audit | No native component |
| branch-expenditure-entry | bexp | BranchExpenditurePage.vue |
| cc-new-dashboard-bhuvan-oct2 | leads | CCDashboardPage.vue |
| branch-visit-report | ccvisit | CCVisitReportPage.vue |
| new-client-registration | clireg | ClientRegistrationPage.vue |
| client-info | cliinfo | No native component |
| life-audit-report | discountaudit | DiscountAuditPage.vue |
| appointment-shedular | appt | AppointmentSchedulerPage.vue |
| accounts-command-center | accounts | No native component |
| pending-balances-updates | pendbal, receivables | PendingBalancesPage.vue |
| payables-planner | payables | PayablesNativePage.vue |
| asset-master | assets | No native component |
| stock-dashboard | stock | StockDashboardNativePage.vue |
| approvals-report | approvals, approvalsreport | ApprovalsPage.vue |
| hrms-dashboard---copy | employees, attend, payroll | No native component |
| life-master-report | repmaster | No native component |
| coo-dashboard | execdash | No native component |
| md-dashboard | mis | No native component |
| contols-command | control | ControlPage.vue |
| knowledge-centre | hrpol, knowledge | No native component |
| glp-programme | riseprog | No native component |
| operations-service-module | service | ServicePage.vue |
| followup-master | followup | No native component |
| package-conversion-for-p2p | p2p | No native component |
| package-conversion-c2c | c2c | No native component |
| b2b-testing | b2b | No native component |
| branch-command-center | bdash | No native component |
| enrollment-register-testing | enrollment-register | No native component |
| data-correction | data-correction | No native component |

## APIs and delivery

The existing catalogue contains 150 authenticated/native API modules (including two token-checked guest callback endpoints); their schema, permission and source-registration checks remain in place. The seven rewritten pages use existing native APIs and standard permission-checked Frappe document/report APIs. No production transactions were executed.

The Cluster page now calls the mapped Python endpoint with CSRF. Price List preserves the source page’s item-rule discount precedence and reads its supplemental Pricing Rule documents through Frappe permissions; native pricing helpers used by other consumers remain unchanged.

The coverage JSON lists every mapped source, source revision/hash, existing Vue preview, static controls, headings and identifiable API methods. Dynamic controls and API calls still require per-workflow review; these counts are an inventory, not a parity score.

Validation: native Vue production build, pure calculation/masking/linking/export tests, and desktop/mobile browser workflows with mocked APIs. Exact visual parity with signed-in production data has not been established. Deploy the HTML entry and generated assets together; the separate legacy refresh also includes Python/page-source changes.

Reproduction: start Vite and an isolated headless Chrome debugging session, set PORTAL_PREVIEW_URL and PORTAL_BROWSER_URL, then run the seven browser scripts in life_portal/tests. API responses and write operations are intercepted by the fixtures.

## Latest verification fixes

The Forms & Documents source loads all category counts at startup; the native implementation now does the same, with eight concurrent full-document reads per batch. Failure remains visible until the user chooses Retry.

Sales Master preserves `REFERRAL REPORT – FIXED`'s original result indexes for server export. Restricted users selecting all permitted branches receive merged and deduplicated client-side exports, so no blank-branch export request is sent. A changed draft filter refreshes report data before download.

Corrected the Weight Loss pagination component tags and tested report/open-card datasets with 14 clients and 23 cards. Browser fixtures use unique session IDs to avoid stale idle timestamps between runs. The runtime-config unit check selects the configuration script by URL, allowing the separate session keepalive script to coexist.
