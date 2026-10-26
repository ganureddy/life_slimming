# Vue parity audit — 26 October 2026

## Verdict and scope

No Vue replacement is certified here as identical in every pixel and every business workflow. This audit compares checked-in legacy sources, current Vue sources, original-style contracts, regression tests and mocked desktop/mobile browser workflows. It does not compare against a newly downloaded production source or submit real ERP transactions.

The current router has `nativeModules = new Set([])`. Mapped main module routes use `PortalSourcePage`; explicit `/native/...` routes expose Vue previews. Earlier documents calling twelve pages “default Vue modules” are stale for this checkout. An original-looking main route therefore does not prove that its Vue preview matches.

## Closest matches: original CSS and selected behavior covered

These nine replacements have passing original-CSS contracts and regression coverage. No new omission was established for them in this audit, but untested workflows and exact screenshot parity remain open.

| Page | Covered behavior / final comparison needed |
| --- | --- |
| Appointments | Original grid and slots; booking, pending concerns, status, reschedule/history, conflicts and dates. Finish complete role/data and visual comparison. |
| Client Registration | Form, validation, duplicate mobile, linked IDs, uploads and Billing navigation. Finish complete role/data and visual comparison. |
| Discount Audit | Filters, periods, totals, paging, invoice dialog and Excel. Finish complete role/data and visual comparison. |
| Unjoined Clients | Cohort/date filters, masking, details, follow-up, attachments and exports. Finish complete role/data and visual comparison. |
| Conversions & Targets | Sales cycles, targets and daily tracker. Finish complete role/data and visual comparison. |
| Price List | Tabs, package details, therapy search and pricing-rule precedence. Finish complete role/data and visual comparison. |
| Forms & Documents | Seven tabs, counts, attachments, viewer and retry. Finish complete role/data and visual comparison. |
| Sales Master | Permitted branches, same-line therapy filters, ex-GST amounts, totals and filtered exports. Finish complete role/data and visual comparison. |
| Weight Loss Results | Monthly/lifetime values, new joiners, masking and export. Finish complete role/data and visual comparison. |

## Confirmed differences requiring changes

### Employee Sale Master

Compared `life_slimming/portal_pages/employee-sale-master-data.json` with `EmployeeSaleMasterPage.vue`, `NativeTable.vue`, `NativeDialog.vue` and `TreatmentTree.vue`.

- The original Branch tab has Active Branches, Paid ex-GST, Top Branch and Current Outstanding KPI cards. The Vue branch template omits them.
- The original Treatment tab has Main Categories, Treatment Share ex-GST, Leading Category and Unmapped Treatments KPI cards. The Vue treatment template omits them.
- Original Branch × Main Category is a pivot matrix with category columns and a total column. Vue renders branch/category/share records in a flat table.
- Original treatment hierarchy is a seven-column table. Vue renders wrapping flex rows. Separate Expand all / Collapse all controls become one toggle.
- Tree expansion is not equivalent: `expanded || opened.has(node.k)` prevents an individual collapse while global expansion is enabled, and switching global expansion off does not clear locally opened nodes.
- Original modal structure (`esr-modal`, header/subtitle/body) is replaced by a shared native dialog. Table styling, pagination and overview bar rendering also use new markup/styles. Keeping the old CSS does not preserve the original DOM or computed appearance.

Allocation, identity, filtering and treatment-share regression tests pass; those passes do not remove the UI gaps above.

### My Tasks

- Original source has a dedicated drawer and modal; Vue uses a shared `NativeDialog` for the task/ticket details and shared tables/multiselects.
- This is a confirmed UI structure difference. Restore/compare original drawer, dashboard, table and form behavior before claiming identical UI.
- Metadata persistence, group member state, task/ticket creation, review and queue branches have regression coverage. Exhaustive role/configuration/report/deadline combinations are not certified by that coverage.

### Cluster Dashboard

- Vue supplies its own header, KPI/cards, race progress lanes and shared `NativePanel` / `NativeTable` presentation, with additional scoped CSS. This requires rendered comparison against the original dashboard; retained legacy CSS is insufficient.
- Finance/race and other data calculations have fixture coverage. Original race presentation, rankings, all branch detail states and every source-error combination still need full comparison.

### Client Info

- Original has 14 profile tabs; Vue has seven.
- Missing tabs: Diet, Concerns, Documents, Stock, Conversions, Remarks and Messages.
- Original tab count/status badges are absent from the Vue tab template.
- Vue photo menu only offers viewing; complete photo/write/upload actions, referrals/transfers/conversions and messaging parity remain migration work.
- Main route remains legacy; Vue explicitly identifies itself as incomplete.

## Other partial implementations

The existing `NATIVE_PARITY.md` records the following unresolved comparisons. They remain open; this audit does not relabel those previously recorded gaps as newly reproduced bugs.

| Page | Work still needed |
| --- | --- |
| BillingNativePage | Match original layout and all billing/approval/payment/registration flows. |
| BillingPage | Uses `innerHTML` to retain the original billing app; not a complete reactive Vue conversion. |
| CC Dashboard | Complete import, assignment, report and dialog parity. |
| CC Visit Report | Match layout/controls and all four report views. |
| Stores 360 | Match report navigation, filters and controls. |
| Stock | Compare item edit, receipt/release, attachments and approvals. |
| Service | Match appointment/session/execution layout and navigation. |
| Payables | Match layout, ledger, payments, forecast and approval workflows. |
| Pending Balances / Receivables | Match layout, client/branch/employee views, aging and drilldowns. |
| Branch Expenditure | Match selectors, attachments, draft, approval and export workflows. |
| Approvals / Approvals Report | Current component contains an iframe; not a completed native conversion. |

Control has a separate access-control reference; Conversions is a link hub; Vendors has no mapped original. CC Appointments, ConVox and Live TV are separate features. Other legacy-only pages remain listed in `life_portal/MIGRATION_PROGRESS.md`.

## Validation in this audit

- Production Vite build passes; Billing bundle-size warning remains.
- Unit run: 35/37 test files pass. Direct reruns show all twelve original-CSS checks pass.
- Two failing assertions assume a nonempty `nativeModules` declaration: source-parity's regular expression fails to recognize `new Set([])`, and Client Info's regular expression returns null and is indexed. These are test-parser failures, not evidence of missing CSS or a Client Info runtime crash. Update those assertions to handle the current empty set.
- Unmodified browser runner: 12/15 suites pass. Passing suites cover the three reactive pages together, registration, discount audit, appointments, Client Info, unjoined, documents, weight loss, CC dashboard, Billing layout, Billing workflows and loading/performance.
- Branch Target and Price List initially fail because their desktop test opens the legacy main URL. In-memory test variants pointed at their explicit Vue preview URLs pass at desktop and mobile widths. No test files were edited.
- Sales Master's unmodified browser test fails because column 9 is now Therapy Type rather than the old GST column. The current column layout agrees with the checked-in original source. An in-memory rerun using the current column positions proceeds past those checks, then fails its old CSV filename expectation (`All_Permitted_Branches` versus current `All-Branches`). Its remaining browser workflow assertions are therefore not verified in this run. Refresh the fixture/assertions against the current original before claiming full browser coverage.
- Requests are intercepted with fixtures; passing browser checks does not certify every workflow, identical screenshots or live-data parity.

## Recommended order

1. Restore Employee Sales' confirmed missing summaries, pivot layout and tree behavior.
2. Finish Client Info's seven missing tabs and write actions.
3. Compare Tasks and Cluster side by side against original desktop/mobile layouts, including drawers, dialogs and role variants.
4. Finish the other partial pages one at a time, with an explicit control/action checklist.
5. Repair the two test-parser assertions and stale migration wording. Promote routes only after full parity review and the existing routing approval requirement is satisfied.

## Resumed implementation and verification

The earlier audit results above describe the starting state; they do not describe the current test results.

- Restored Employee Sales report summaries, pivot/tree controls and drilldowns; Client Info's missing sections and contact/photo/remark actions; Tasks' source-style reports/dialogs; and Cluster's source-style report/race components. These remain subject to the outstanding exact parity review.
- Completed the separately requested CC status change: Appointment Status comes from the backend field throughout the dashboard/TV and original page; the separate Visit Status controls and fallback logic are removed. Existing permissions and optimistic concurrency checks remain.
- Rebuilt Branch Expenditure using the original source layout and original `life_branch_expenditure_v2` action contract. Restored account/employee selection, private bills, saved drafts/history, export, journal viewing and date amendment. Requests persist their IDs before writes so retries retain the original identity. Backend summaries remain authoritative. This API alias is called by the original page but its implementation is absent from this checkout; live API compatibility has not been certified.
- Added Pending Balances' independent scheduled/confirmed due-date cards, branch and branch-specific employee summaries, and reconciliation. Restored source mobile masking/reveal and masked exports, normalized formatted rupee values, and preserved existing PARTIAL records without offering new PARTIAL selections. Pending Balances is still incomplete: source layout, client collection list/appointment enrichment, section controls and full save/navigation behavior require further work. Existing 1,500-row limit remains explicit; this is not an exhaustive all-invoice report.
- Added explicit Vue previews `/native/branch-expenditure` and `/native/pending-balances`. Main module routing remains on the original pages pending parity review and routing approval.

Verification after this batch:

- All 40 unit test files pass, including financial reconciliation, month boundary calculations, branch-specific grouping, masking and CSV formula handling.
- Production Vite build passes; the existing large Billing chunk warning remains.
- Branch Expenditure browser fixture passes at 1440px and 390px: missing-bill validation, private upload, duplicate save protection, saved-draft reopen, submission retry ID, journal balances/bill link, date amendment concurrency token, export and permission failures without fabricated summary values.
- Pending Balances report browser fixture passes at 1440px and 390px: date-card calculations, all four report sections, formatted amounts, masked phones/CSV and no viewport overflow.
- Expanded Client Info browser fixture passes at desktop/mobile for all 14 tabs and contact/photo/remark/message workflows.
- Browser requests and uploads are intercepted; no live financial or client records were modified by these tests.

Outstanding source dependency: Client Info's original Take Actions loads `client-info-Enrollment`, which is absent from this repository. Connected ERP retrieval returned a permission validation failure. The source/access request remains open; that embedded workflow cannot yet be reproduced or certified.
