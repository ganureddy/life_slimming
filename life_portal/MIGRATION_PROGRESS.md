# Legacy to Vue migration progress

Updated: 16 October 2026. Counts refer to the 44 mapped routes; shared source pages are counted once per route. Billing and new portal-only features are tracked separately.

## Current routing

- 12 mapped routes now use Vue-owned pages by default.
- 32 mapped routes still use their legacy pages.
- A component file or a passing build does not mean complete UI/functionality parity.

## Current step: Client Info (preview, incomplete)

`/life_portal/native/client-info` now uses application-owned Vue components, a cancellable data composable and pure numerical helpers. This preview has the client list, date/branch/status/payment/pending filters, masked contacts, pagination/CSV, invoice drawer/print links, and the seven read-only profile tabs: Overview, Billing, Plans, Sessions, Appointments, Followups and Medical. Original CSS and static profile style patches are owned by the application; this page does not load Web Page content or page-content JSON.

Appointments preserve the original status counts, date/time ordering and 16-card pagination. Followups preserve type counts, remarks, client responses, linked records and overdue/cancelled states. Medical preserves six collapsible/reorderable sections, plan health flags, history, weight trend, vitals and consultations. Clinical reads start on opening the Medical tab, cancel on leaving it, cache only successful complete results and show explicit permission failures with retry.

Profile details render before background plan-document/name/photo enrichment finishes. Plan reads have a four-request concurrency limit, payments cache within the selected profile, search is debounced, obsolete loads cancel and the network dashboard starts when visible. Failed collection reads display unavailable totals rather than zero. Report limits are detected explicitly. Branch-scoped lookup denials do not fall back to broader searches.

This is not a complete Client Info replacement. Seven tabs remain: Diet, Concerns, Documents, Stock, Conversions, Remarks and Messages. Photo upload/camera, referral and branch-transfer/conversion history, New Bill integration, all write actions and exact desktop/mobile parity remain to be completed. The appointment link opens the scheduler; automatic patient prefilling is not implemented. The overview's referral section is also pending. The main `/life_portal/cliinfo` stays legacy; routing counts remain 12 Vue-owned / 32 legacy.

Mocked desktop/mobile checks cover list counts/pagination/masking, invoice drawer visibility, seven tabs, appointment status filters/time ordering/pagination, followup type filters/overdue states, lazy medical read/cache/error recovery, nonblocking plan enrichment, cached payments, permission recovery, branch lookup and unavailable collection totals. They do not certify the remaining workflows or live-data/pixel parity.

## Latest completed step: Appointments

`/life_portal/appt` now renders the original room/time scheduler in reactive Vue; `/life_portal/native/appointments` previews the same component. It preserves the 25 half-hour slots, branch/date controls, four summary cards, booking details, validated client/category search, pending therapy concerns, creation, all booking statuses, rescheduling and grey history references on the original date.

The prior Vue preview omitted move history and counted cancelled bookings as occupied slots. It also quoted report sort direction as part of the SQL field name. These are repaired. Rescheduling saves the new appointment as Scheduled and appends the original from/to history with the current user, matching the legacy workflow. Both booking and rescheduling check the room/time immediately before submitting. Changing client/category invalidates the old selection before async validation returns. Status changes cannot leave Update disabled after a cancelled slot-list request.

Loading changes: board records, rooms and move history load independently in parallel; room/time indexing avoids repeated full-list scans during grid rendering; therapy-plan detail requests use at most four concurrent reads; searches are debounced and superseded reads cancel. Only explicit user actions submit writes, with duplicate-submit protection and no automatic retry. CSS is scoped to this page so its generic modal selectors cannot change other portal pages.

Desktop/mobile fixture checks cover original-style rules, grid counts, excluded branches, cancelled-slot reuse, history navigation, pending concerns, create payloads/double-clicks, conflict rejection, reschedule history, cancellation, past-time restrictions, error/retry, modal containment, pending-request cancellation and navigation cleanup. No real ERP records were modified. Deployed pixel matching and live multi-user concurrency have not been certified.

Client Info was reviewed: it has 14 detail sections plus photo capture, referral/conversion history and messaging. Its main route stays legacy until these are preserved; it is not counted as converted.

## Earlier completed steps: Employee Sale Master, Client Registration and Discount Audit

`/life_portal/empsale` now owns the original four-view Employee Sale Master dashboard in reactive Vue: original CSS and table columns, searchable branch/booking/employee/payment-mode controls, date/amount filters, reset, six overview totals, ranked bars, employee/branch summaries, transaction detail and both Excel exports. Normalization, share allocation and employee identity grouping are ordinary pure ES-module functions. Repeated employee IDs and unambiguous name aliases follow the original rules. Restricted All Branches requests explicitly name permitted branches, filter returned rows by that branch and run at most three reports concurrently. Metadata and requests cancel on navigation; amounts validate before reports. Only the active dashboard view mounts its tables, while all views reuse the loaded report data. Mocked desktop/mobile checks cover these workflows, numeric exports and permission recovery.

`/life_portal/clireg` now owns its original seven-section form, risk table, preview card and today's registrations in reactive Vue. Validation, branch/practitioner typeahead, selected document IDs, risk-to-Patient mappings, duplicate-mobile blocking, confirmed registration and Billing redirect are preserved. PD uploads now populate the Patient's PD form child table; the original file picker only displayed a filename and never uploaded it. Searches are debounced, cancelled when superseded, and cleaned up on navigation. The form renders immediately while today's records load separately. Tested on desktop/mobile using intercepted APIs, including upload payloads, duplicate-click protection, reset and permission recovery.

`/life_portal/discountaudit` now owns the original report markup and CSS in Vue. Preserved controls include 6th-to-5th date presets, branch/status/level/search filters, six totals, all 17 table columns, pagination, invoice details and numeric Excel export. Report loading starts independently of the branch list; reads cancel on navigation and errors have visible retry controls. Desktop/mobile workflow fixtures cover these actions and permission recovery. Neither page loads legacy Web Pages or page-content JSON at runtime.

These checks do not certify every live-data scenario or a pixel-for-pixel comparison with a deployed legacy page. Source rules are compared against the checked-in reference; no real business records were modified.

## Earlier step: My Tasks / Ticket System

`/life_portal/tasks` now uses `TaskManagerPage.vue`; `/life_portal/native/tasks` renders the same component.

The Vue component owns the original template, page CSS, dialogs and lifecycle. The reviewed task/ticket business controller is retained as a static ES module. Its dynamic table/form rendering remains imperative; this is not a claim that every legacy function has been rewritten as reactive Vue state. No iframe, eval, global Frappe installation or runtime script injection is used.

Validated with mocked ERP APIs: desktop/mobile, visible records while users load, bootstrap identity, task/ticket creation, attachment upload, task completion, cancellation/reopening, reassignment and queue history, ticket resolution, restricted reports, permission error/retry, and cleanup on navigation. Task behavior has standalone workflow and dependency tests. Live transactions and exact Frappe-dialog pixel matching have not been certified.

Legacy workflow and lifecycle bugs are corrected: cancelled-task Reopen no longer invokes the completed-task handler; queue saving accepts task records as well as names during reassignment; employee search also filters the normal report; queue dialogs remove their Escape handlers when closed.

Task markup, styles and controller are maintained directly in the Vue source tree. The task JSON generator and JSON-based tests have been removed; this page no longer requires the legacy task Web Page or its JSON snapshot. The retained imperative controller still needs a reactive Vue rewrite to meet the fully component-based requirement.

## Required final architecture

All portal pages must own their templates, state, dialogs and actions in Vue components/composables, without loading or generating page content from legacy Web Pages or JSON snapshots. Existing legacy routes remain migration work; they do not meet this requirement yet. Ordinary API records and configuration are separate from legacy page content.

## Page-by-page queue

Rows marked **Vue baseline checked** have source-style contracts and selected workflow tests. Remaining pages require their original controls, dialogs and workflows to be checked before switching their main route.

| Page | Route | Current state |
| --- | --- | --- |
| Stores 360 | `stores360` | Legacy active; component/parity work remains |
| My Tasks | `tasks` | Vue baseline checked |
| Conversions & Targets | `conv` | Vue baseline checked |
| Employee Sale Master | `empsale` | Reactive Vue; original styles, allocations, filters, summaries and Excel workflows checked |
| Sale Master Data | `salemaster` | Vue baseline checked |
| Audit Reports | `audit` | Legacy active; dedicated component needed |
| Branch Expenditures | `bexp` | Legacy active; component/parity work remains |
| CC Dashboard | `leads` | Legacy active; component/parity work remains |
| CC Visit Report | `ccvisit` | Legacy active; component/parity work remains |
| Client Registration | `clireg` | Reactive Vue; source styles and desktop/mobile workflows checked |
| Client Info | `cliinfo` | Main route legacy; Vue preview has list/drawer and seven profile tabs; seven tabs and actions pending |
| WL Results Report | `wlres` | Vue baseline checked |
| Discount Audit Report | `discountaudit` | Reactive Vue; source styles and desktop/mobile workflows checked |
| Appointments | `appt` | Reactive Vue; original grid/styles, booking/status/reschedule/history and desktop/mobile workflows checked |
| Accounts Command Centre | `accounts` | Legacy active; dedicated component needed |
| Pending Balances | `pendbal` | Legacy active; component/parity work remains |
| Payables | `payables` | Legacy active; component/parity work remains |
| Receivables | `receivables` | Legacy active; component/parity work remains |
| Assets | `assets` | Legacy active; dedicated component needed |
| Price-List | `pricelist` | Vue baseline checked |
| Stock | `stock` | Legacy active; component/parity work remains |
| Approvals Pending | `approvals` | Legacy active; component/parity work remains |
| Forms And Documents | `documents` | Vue baseline checked |
| HRMS Dashboard | `employees` | Legacy active; dedicated component needed |
| Attendance | `attend` | Legacy active; dedicated component needed |
| Payroll | `payroll` | Legacy active; dedicated component needed |
| Report Master | `repmaster` | Legacy active; dedicated component needed |
| Approvals Report | `approvalsreport` | Legacy active; component/parity work remains |
| Executive Dashboard | `execdash` | Legacy active; dedicated component needed |
| MD Dashboard | `mis` | Legacy active; dedicated component needed |
| Cluster Dashboard | `clusterhome` | Vue baseline checked |
| Control Panel | `control` | Legacy active; component/parity work remains |
| HR Policies | `hrpol` | Legacy active; dedicated component needed |
| Knowledge Center | `knowledge` | Legacy active; dedicated component needed |
| Programs & Packages | `riseprog` | Legacy active; dedicated component needed |
| Service | `service` | Legacy active; component/parity work remains |
| Follow-ups | `followup` | Legacy active; dedicated component needed |
| Package Conversion | `p2p` | Legacy active; dedicated component needed |
| Client Package Transfer | `c2c` | Legacy active; dedicated component needed |
| Branch Transfer | `b2b` | Legacy active; dedicated component needed |
| Branch Dashboard | `bdash` | Legacy active; dedicated component needed |
| Enrollment Register | `enrollment-register` | Legacy active; dedicated component needed |
| Data Correction | `data-correction` | Legacy active; dedicated component needed |
| Unjoined Clients | `unjoined` | Vue baseline checked |

## Continue in this order

1. Client Info: finish the seven remaining tabs and pending actions in the existing Vue preview, then compare all 14 sections before promoting the main route.
2. Audit Reports and My Tasks follow-up: cover remaining report/queue/deadline branches.
3. Existing partial conversions: finish one page at a time against its original source.
4. Remaining legacy-only routes in the table.

Keep completed default modules under source-style and browser regression tests. Never label the entire migration complete while rows remain legacy or have unverified workflow gaps.

## Validation for this migration batch

- 34 Node test files pass, including original-style comparisons and registration/allocation/export rules.
- All 17 desktop/mobile browser suites pass, including the Client Info preview with seven tabs, appointment/followup controls, lazy medical retry/cache and the existing converted pages; no live ERP writes.
- Final Appointments verification also covers cleared dates, repeated history-card keys and mobile form-control containment after the last layout fixes.
- Production Vite build passes. The pre-existing Billing bundle size warning remains.
- The CC regression test waits and clicks controls atomically after switching views. Its options fixture now matches the appointment-status API contract. A malformed-response case also exposed and verifies the repair for a CC render crash: invalid status metadata keeps an array in view state, shows a recoverable field error and cancels on navigation.
