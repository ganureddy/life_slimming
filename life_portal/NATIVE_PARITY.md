# Native Vue parity and loading audit

Reference date: 16 October 2026. Requirement: preserve each legacy page's UI,
controls, filters, data semantics, permissions, exports, dialogs and actions.
Performance work must preserve those behaviors.

See [MIGRATION_PROGRESS.md](MIGRATION_PROGRESS.md) for the current page-by-page queue and the scope of the Task Manager conversion.

## Current evidence

The twelve default Vue modules retain their original page CSS. The source parity
suite compares the checked-in legacy rules directly to the native styles;
Frappe website wrappers are excluded because PortalLayout owns that chrome.
Desktop/mobile workflow fixtures cover these modules. This is evidence about
styles and tested workflows, not a claim that every possible business action or
pixel has been verified with live data.

| Module | Legacy reference | Vue component | Verification |
| --- | --- | --- | --- |
| Appointments | appointment-shedular | AppointmentSchedulerPage | Original scoped styles/grid, slots/counts/history, pending concerns, booking, duplicate-submit and collision checks, all status choices, rescheduling history, retries, navigation cleanup, desktop/mobile |
| Client Registration | new-client-registration | ClientRegistrationPage | Original form/styles, validation, linked IDs, risk flags, duplicate mobile checks, PD upload, Patient insert, Billing redirect, desktop/mobile |
| Discount Audit | life-audit-report | DiscountAuditPage | Original styles, filters, totals, paging, invoice dialog, business dates, Excel export, desktop/mobile |
| Employee Sale Master | employee-sale-master-data | EmployeeSaleMasterPage | Original styles and four views, identity/share rules, searchable selectors, amount/date filters, summaries, both Excel exports, restricted branch requests, desktop/mobile |
| My Tasks / Ticket System | task-management | TaskManagerPage | Original markup/styles; task/ticket creation, uploads, completion, cancellation/reopening, reassignment, queue history, permission/error/retry and cleanup |
| Unjoined Clients | unjoined-data | UnjoinedClientsPage | Original styles; filter cohorts, masking, pagination, details, follow-up insert/save, uploads, exports |
| Cluster Dashboard | cluster-head-dashboard | ClusterDashboardPage | Original styles; cluster/date filters, totals, permission/error/empty states |
| Conversions & Targets | branch-home-target | BranchTargetPage | Original styles; cycles, targets, tracker, desktop/mobile |
| Price List | price-list | PriceListNativePage | Original styles; tabs, offers, package details, search, pagination |
| Forms & Documents | v | FormsDocumentsPage | Original styles; seven tabs, counts, attachments, viewer, errors/retry |
| Sales Master | sales-master-data | SalesMasterDataPage | Original styles; filters, permitted branches, report totals, pagination, export |
| Weight Loss | client-weight-loss-info | WeightLossReportPage | Original styles; monthly/lifetime calculations, cards, masking, exports, independent errors |

## Converted previews and other components

These are included in the scope. A source-based audit found substantial differences
in several native previews. They are not certified as exact replacements.
Main routes that still use PortalSourcePage continue to show the original page.

| Component | Reference | State / remaining comparison |
| --- | --- | --- |
| ClientInfoPage | client-info | Preview only: list, invoice drawer and seven read-only tabs checked on desktop/mobile; appointment paging/statuses, followup filters and lazy medical retry/cache covered; seven tabs, referrals/transfers/conversions, uploads, messaging and write actions remain. Main route stays legacy |
| BillingPage | billingV2LiveSource | Original UI/runtime retained in Vue; review lifecycle and loading independently |
| BillingNativePage | billingV2LiveSource | Mocked billing/approval/payment/registration workflows pass; layout still differs |
| CCDashboardPage | cc-new-dashboard-bhuvan-oct2 | Cohorts, tiles, search, directory, pagination/error fixtures pass; complete import/assignment/report/dialog parity remains |
| CCVisitReportPage | branch-visit-report | Native report layout and controls differ; all four report views need comparison |
| Stores360NativePage | stores-360 | Report navigation, filter layout and controls differ; API mapping and inventory calculation performance repaired |
| StockDashboardNativePage | stock-dashboard | Compare all requests, item editing, receipt, release, attachment and approval dialogs; API/upload mapping repaired |
| ServicePage | operations-service-module | Appointment/session/execution navigation and layout differ; duplicate requests, search load and initial metadata blocking repaired |
| PayablesNativePage | payables-planner | Native layout differs; ledger, payment, forecast and approval parity remains; API mapping repaired |
| PendingBalancesPage | pending-balances-updates | Native layout differs; client/branch/employee reports, aging filters and drilldowns remain |
| BranchExpenditurePage | branch-expenditure-entry | Native layout differs; all selectors, attachments, drafts, approval and export behavior remain |
| ApprovalsPage | approvals-report | Original report retained in an iframe; not a completed native conversion |
| ControlPage | life-home portal access control | Distinct access-control function; contols-command is not its correct parity reference |
| ConversionsPage | portal conversion cards | Preserve existing three conversion links and their original target pages |
| VendorsPage | no mapped legacy reference | Separate native feature; no original page available in the manifest |

CCAppointmentsPage, ConvoxHistoryPage and live TV are separate features rather
than replacements for a mapped legacy page. Their existing suites remain relevant
but do not certify legacy parity.

## Loading changes

- Unjoined reads start alongside the independent branch list.
- Documents prioritizes the visible tab and warms other tabs through one queue.
- Native API requests have a 45-second deadline, including response body loading.
  Navigation aborts retain AbortError; timeouts become a visible TimeoutError.
  No request is automatically retried.
- Known API IDs resolve through endpoints.json. Ambiguous aliases are not guessed.
- Stock uploads and Stores purchase-order/workflow actions use the shared client.
- Stores indexes movements once and reuses them across filter changes. A fixture
  with 1,000 items and 10,000 movements verifies one movement pass and correct
  reactive inventory/forecast totals.
- Weight Loss derives previous-month rows from the already-loaded lifetime
  history rather than fetching those same sessions again.
- Service starts its appointment report while metadata is pending, debounces
  report search and lets its watcher perform one request per tab change.

## Run checks

From life_portal:

```sh
npm test
npm run build
npm run dev -- --port 5178
```

With an isolated Chrome exposing DevTools on port 9230:

```sh
npm run test:native:browser
```

Set PORTAL_BROWSER_URL and PORTAL_PREVIEW_URL to use other ports. Browser suites
intercept ERP APIs and do not change real business records. The runner is
sequential and gives each suite a 60-second deadline.

## Completion criteria

A converted page is complete only after its original desktop/mobile layout,
all controls and workflows, permissions and data calculations have been checked.
Do not promote a partial native preview solely because it builds or its basic
smoke test passes. Live latency and untested workflows remain unverified here.
