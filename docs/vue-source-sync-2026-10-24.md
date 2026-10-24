# Vue pages aligned with ERP sources — 24 October 2026

Compared all twelve default Vue modules against the production sources refreshed from ERP. Six changed sources required Vue updates. CC legacy sources and their routing remain unchanged.

| Active Vue page | Imported behavior |
|---|---|
| Appointments | Links may preselect a permitted branch; opening an empty slot validates and prefills the linked Patient and loads their pending therapies. Existing create/reschedule/status safeguards remain. |
| Employee Sale Master | Current dashboard layout, multiple employee/role/payment/booking/treatment filters, full-invoice versus treatment-share allocation, overview/employee/branch/treatment/transaction views, drilldowns and exports. |
| Sales Master | `Sales Master Billing` report; main-category, therapy-group and therapy-type filters on the same therapy detail; invoice-date bounds; ex-GST amount filtering; new visible columns and client-side export of filtered rows for all roles. |
| Price List | Enabled, billable therapies shown in Billing with positive rates; background enabled selling item rules, current dates, five concurrent rule reads, progressive offer rendering, and first applicable rule in query order. |
| My Tasks | Current tasks/tickets dashboard, group tasks, priority/queue operations, reporting/review actions, ticket resolver workflow, phone-display policy and persisted role/control-panel configuration. |
| Cluster Dashboard | Current cluster operations layout and permitted branch selection; branch finance/attendance/stock/recovery/approval/execution sources and sales-race display policy. Unavailable sources remain visibly unavailable. |

Unjoined Clients, Weight Loss Results, Conversions & Targets, Forms & Documents, New Client Registration and Discount Audit had no newer reference changes to transfer in this refresh.

## Architecture and scope

Components own checked-in templates, scoped styles and ES modules. They do not load page-content JSON, inject executable page scripts or mount legacy iframes at runtime. Tasks, Cluster Dashboard and Employee Sale Master retain DOM-based business controllers inside Vue-owned components; this update is **not** a claim that their internals have all been rewritten as reactive Vue components. The previous Employee Sale composable remains in the tree but is no longer the active implementation.

The isolated controller runtime maps API methods to configured ERP endpoints, preserves CSRF/credentials only for the ERP origin, suppresses stale callbacks, cancels requests and removes timers/listeners/observers on unmount. In-progress writes block SPA navigation. Parent portal chrome and global Frappe state are not overwritten.

## Verification

- Full frontend unit run: 36 test files passed, including source styles, sales filters/exports, pricing rules and runtime isolation/cancellation.
- Mocked Chrome desktop/mobile checks passed for current Tasks, Employee Sale and Cluster layouts, and SPA navigation cleanup.
- Mocked Chrome Price List workflows passed, including offers and sanitized package descriptions.
- Mocked Chrome Appointments workflows passed, including new branch/patient prefilling, create/reschedule/cancel/history/conflict/error behavior.
- Production portal build passed.
- CC source checksums remained unchanged.

No live ERP transactions or configuration writes were executed. The refreshed dashboard write actions and every production-data combination have not been certified by these fixture checks.
