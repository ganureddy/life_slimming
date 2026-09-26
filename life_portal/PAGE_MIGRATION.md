# Portal page migration — 2026-09-20

Vue frontend: `life_portal/`. Git branch: `naren_test` at `6d09de6` when work started; one commit ahead of the locally recorded `upstream/naren_test`. The bench root is a separate, empty `main` repository. Angular `frontend/` is unchanged.

Sources were read through ERP Portal from the live `life-portal-home` mapping. 35 checked-in Web Page sources provide 40 local mappings: 36 menu entries, client registration, and three conversion forms. Existing Billing and Branch Dashboard components are retained.

The source HTML/CSS/JavaScript is hosted in authenticated local Frappe frames at `/life_portal_module?module=<id>`, inside the Vue shell. This preserves the original page UI without leaking page CSS or timers across Vue navigation. Source files are not bundled into the public Vue assets. Each frame uses the local Frappe runtime, session and CSRF token. The adapter maps unambiguous legacy methods to the existing migrated Python endpoints and upgrades their GET requests to POST.

Accounts and Controls receive a narrow DOM-helper rename at render time because their global `$` conflicts with Frappe jQuery. Accounts also guards updates to a clock element absent from its source markup. Checked-in source exports remain unchanged. The source cluster link `cluster-dashboard` does not exist; `cluster-head-dashboard` is used. Conversions retains the original three-card layout, linking to local copies of the three forms.

## Branch selection

There is no single selected clinic branch shared by these pages. Their original branch selectors, default values, and permission queries are retained. Employee Sale Master automatically selects the sole permitted branch when one is returned. Other pages may start with All/ALL or require selection. API authorization remains the responsibility of the existing endpoints. The table records static branch controls; dynamically generated controls and backend branch restrictions require signed-in data verification.

| Vue menu | ERP source route | Static branch selects |
| --- | --- | --- |
| My Tasks | `task-management` | 1 |
| Approvals Pending | `approvals-report` | 1 |
| Stores 360 | `stores-360` | 1 |
| Conversions & Targets | `branch-home-target` | 1 |
| Employee Sale Master | `employee-sale-master-data` | 1 |
| Sale Master Data | `sales-master-data` | 0 |
| Audit Reports | `audit` | 2 |
| Forms And Documents | `Documents` | 0 |
| Branch Expenditures | `branch-expenditure-entry` | 2 |
| Leads | `cc-new-dash` | 3 |
| CC Visit Report | `branch-visit-report` | 4 |
| Client Info | `client-info` | 1 |
| Appointments | `appointment-shedular` | 2 |
| Service | `operations-&-service-module` | 8 |
| WL Results Report | `client-weight-loss-info` | 1 |
| Follow-ups | `followup-master` | 4 |
| Knowledge Center | `knowledge-centre` | 0 |
| Accounts Command Centre | `accounts-command-center` | 2 |
| Pending Balances | `pending-balances-updates` | 1 |
| Payables | `payables-planner` | 1 |
| Receivables | `pending-balances-updates` | 1 |
| Assets | `asset-master` | 6 |
| Stock | `stock-dashboard` | 14 |
| Price-List | `price-list` | 0 |
| Employees | `hrms-dashbaord` | 2 |
| Attendance | `hrms-dashbaord` | 2 |
| Payroll | `hrms-dashbaord` | 2 |
| HR Policies | `knowledge-centre` | 0 |
| Programs & Packages | `glp-programme` | 2 |
| Report Master | `life-master-report` | 0 |
| Discount Audit Report | `life-audit-report` | 1 |
| Approvals Report | `approvals-report` | 1 |
| Executive Dashboard | `coo-dashboard` | 2 |
| MD Dashboard | `md-dashboard` | 1 |
| Cluster Dashboard | `cluster-head-dashboard` | 0 |
| Control Panel | Native `ControlPage.vue`: Portal Access Control from `life-home` (role/group/tab permissions), not `contols-command` | — |

## Original unavailable entries

Campaigns, Unjoined Clients, Dietitian Feedback, GST India, Financial Reports, Buying / Purchase Orders, Vendors, Leaves, RISE Dashboard, Webinars, RISE Clients, Users & Roles, Masters, System Audit Log.

These 14 entries have no page mapping in the original portal and retain an explicit unavailable state instead of displaying generic snapshot tables.

## Validation and limits

- Production Vue build passes; the existing large Billing chunk warning remains.
- All 35 original JavaScript blocks parse. All 40 authenticated page contexts render using the local Frappe template runtime. Guest HTTP request returns 302 to portal login.
- Controller tests cover guest redirect, unknown/path traversal rejection, every source, manifest agreement, session/API configuration and jQuery-helper compatibility. JavaScript bridge tests cover callbacks/arguments, mapping, GET-to-POST conversion, query preservation and CSRF isolation.
- Browser smoke checks exercise all 36 menu frames, conversion links, unavailable-page state and mobile layout with business requests blocked. This checks UI composition, not successful business transactions. Stock, Price-List and the shared HR page surface rejected API promises when those requests are deliberately denied; successful data loading has not been claimed.
- Local schema report (`life_slimming/api/local_schema_report.json`) already lists missing DocTypes across 51 migrated APIs. No schemas or business records were imported. Individual API availability, permissions, external integrations and locally missing `/files` assets still need data-level verification.
- The ambiguous `create_po_from_indent360` legacy alias is deliberately not mapped: the API catalog contains two different implementations. Other non-migrated methods retain their original method names and may be unavailable locally.

Run: `npm run build:portal`, `../../env/bin/python -B -m unittest life_slimming.tests.test_portal_pages -v`, `node life_portal/tests/portal-bridge.test.cjs` from the app root.
