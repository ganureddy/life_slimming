# CC Dashboard and CC Visit Report: PDF audit

Source checklist: `/home/life/Downloads/Temp file.pdf`, supplied by the user.
Audit date: 11 November 2026, India time.

**Follow-up source review: the prior audit marked several implemented native features as missing.**
The Vue dashboard/distribution/report source was rechecked on 11 November 2026. `cc-new-dash` is a
separate ERP Web Page with its own lead UI and still lacks parity with the newer CC dashboard.
The document was used as a checklist, not as authorization to alter permissions,
activate redistribution, distribute an APK, or change live business records.

## What the verification means

- **Tested:** local tests or desktop/mobile browser checks using mocked ERP requests passed.
- **Present:** implementation found, but a full real-data integration has not been verified.
- **Partial / mismatch:** some implementation exists but differs from the PDF.
- **Missing:** no corresponding native UI/control was found.
- Live ERP checks were read-only configuration checks. No live calls, lead moves, bill changes,
  matching confirmations, permission edits, or rule activations were performed.
- PDF sections 4–6 (Branch Command Center, mobile app, APK) are outside this CC-page audit.
  `life_pw` was checked for existence/enabled status only.

## 1. CC Dashboard

| PDF requirement | Finding | Status |
| --- | --- | --- |
| Failed calls preserve appointment/visit/business results | Core attempt path leaves business fields unchanged when `has_business_result` detects paid/bill/booked/business evidence; a paid-lead regression fixture covers this path. | Implemented in source; live integration unverified |
| A fresh lead becomes FOLLOW-UP with the failure reason | The attempt branch implements this when previous sub-status is blank/Lead/failed and no appointment lock applies. | Present |
| Joined Client requires booked + any paid bill | `milestone_of` requires `booked(l, c)` together with paid evidence. | Implemented in source; live integration unverified |
| Joined clients receive feedback calls only | Core `save_connected` rejects changes to business outcome, appointment and owner for Joined Client; legacy worksheet UI still needs parity verification. | Native source protected; legacy/live integration unverified |
| Joined clients never move | Distribution filters protected milestones before moving; payment evidence includes verified alternate-number matches via LIFE CC Lead Track. | Implemented in source; live integration unverified |
| Add another number, match branch client, TL verify | Native journey UI and add_number/match/match_verify actions exist. Actual matching against live branch records was not exercised. | Present / integration not verified |
| 100% credit to the agent who booked the converting visit | Credit uses appointment activity and payment/invoice submission timestamps; where exact payment time is unavailable, evidence is marked provisional. | Implemented with provisional fallback; ERP reconciliation outstanding |
| Present status, last call, unreachable streak, next action | Displayed in the journey component; browser checks pass. | Tested |
| Different milestone colours | `CCJourneyChips.vue` maps milestones to distinct colour classes. | Present in native source |
| Received time and visit as branch code–consultant | `CCLeadJourney.vue` renders received dates and branch code, consultant and date. | Present in native source |
| Short names instead of emails | Journey owner is shortened by the API; the main worksheet banner still displays raw lead_owner. | Partial |
| Full timeline | Timeline opens and renders. It is bounded, and combines activity/follow-up/mobile logs; ConVox details are provided through separate history views. | Tested basic flow / bounded coverage |
| Compact dashboard title, golden age circle, 45-degree call-button divider | Existing banner still uses its earlier age text/stamp layout. The PDF's specific title layout has not been reproduced. | Missing / not matched |
| Remove CC-Reports button | Vue page has no rendered reports shortcut (browser assertion checks null). The separate live `cc-new-dash` record still has it. | Missing on live Web Page |
| Flag/status filters actually filter and show counts | Computed flag/status filters exist; desktop/mobile queue tests pass. | Tested |
| No-show recovery and post-consult closing queues | Recovery tiles exist and open filtered queue views. | Tested basic flow |
| Red/teal/orange recovery warnings on the lead | `CCLeadWorksheet.vue` renders no-show, post-consult and unreachable warnings with red/teal/orange classes. | Present in native source |
| Menu hides after 10 seconds, Pin, clickable MENU tab | Vue dashboard and both CC Web Page scripts contain the timer, pin and edge menu. The legacy source has been aligned to the live V26-4 add-on. | Present in source; fresh browser verification pending |
| Resizable side panel | Pointer/keyboard resizing and saved width exist. | Present; browser layout checked, drag persistence not separately exercised |
| Collapsible TL sections | Vue dashboard has a Collapse / Expand TL sections control. | Present in native source |

## 2. Lead Distribution

| PDF requirement | Finding | Status |
| --- | --- | --- |
| Filter → checklist → receiving agents/method | All controls exist in one view. There is no explicit three-step progression. | Partial |
| Preview, move and undo | Mocked desktop/mobile request/response flows pass. Actual live ownership changes were not performed. | Tested UI; real mutation not verified |
| Export list to Excel | Preview exports an `.xlsx` workbook. | Present in native source |
| Dormant-only (90+ days) | Dormant filter uses configurable dormant_days, default 90. It tests last modification age. | Present |
| New lead, overdue follow-up, hot overdue, visited-not-booked, absent agent triggers | Five trigger types are supported in native UI/scheduler code. Only three rule records were found live. | Present; only three configured |
| Absent Auto/Manual | Both modes exist. | Present |
| Seven ranking methods | Conversion, bookings, walk-ins, lowest load, round robin, fewest leads, fewest follow-ups are implemented. Ranking UI test passes. | Tested basic ranking flow |
| Green What is applied summary + Accept & Apply | Rule review shows the applied summary and explicit Accept & Apply step. | Present in native source |
| Rules default to Test mode | newRule uses test_mode=1; browser assertion passes. All three live rule records are also in Test mode. | Tested / live configuration confirmed |
| Workload switch and default limits | Defaults are 150 overdue/30 days and 1000 open/60 days; UI exposes the switch/windows. | Present |
| Warning before assigning over capacity | Manual move checks projected capacity and requires an explicit acknowledgement; scheduler also applies caps. | Present in native source |
| Configure senior closers and dormant days in Settings | Native settings form exposes dormant days and senior closers. Live identity mapping remains unverified. | Present in source; live identity mapping unverified |
| Bulk Excel/CSV file, duplicate skip, assignment modes | Parsing, file selection, default duplicate skip and Auto/one/split/rank/file modes exist. Parser tests pass. Actual live bulk creation was not performed. | Tested parsing; mutation not verified |
| Downloadable Excel template | Bulk upload provides an Excel template download. | Present in native source |
| Paste rows | Bulk upload accepts pasted CSV/Excel rows. | Present in native source |
| Row-by-row preflight | “Check every row” returns a row-by-row validation table before creation. | Present in native source |
| TL/Admin/Surya/Bhuvan/MD may move leads | Source includes the configured mover defaults and TL/MD role checks; live named-user configuration still needs confirmation. | Source policy present; live configuration unverified |
| Only Bhuvan and Naren may edit permission list | `PERMISSION_EDITORS` restricts permission-list edits to the two configured accounts; generic System Manager is denied. | Implemented in source; live integration unverified |

## 3. CC Visit Report

| PDF requirement | Finding | Status |
| --- | --- | --- |
| Lead Journey tab | Native tab, report request and rendering pass browser checks. | Tested |
| Agent 360 ordinary agents see only own data | Activity and history APIs enforce ERP-user/ConVox mapping; negative access tests pass. Manager browser tests use mocks. Real agent-account integration remains unverified. | Tested access logic |
| Select report sections to send | Share preview supports visits, groups, paid bills, activity/Agent 360, Untouched and rolling comparisons, plus copy/share. | Present in native source; no external message sent |
| Paid bills show correctly | Invoice and paid totals are rendered; attribution/sum tests pass with fixtures. No reconciliation against actual ERP invoices/payments was performed. | Present / real totals not verified |
| Compact Untouched report | Dedicated paginated Untouched report and share section are present. | Present in native source |
| Compact title and six menu buttons | Implemented; desktop/mobile containment and six-tab browser checks pass. Exact 30% height reduction was not measured against a visual baseline. | Tested functional layout |
| Hide/show branch cards | Reactive visibility control and per-user saved preferences exist. | Present |
| Business-month strip (6th–5th), daily appointments/visits/booked, previous/next | Implemented with grouped queries; range/leap-year tests and browser rendering pass. | Tested |
| Recent addition: call history, recordings, lead changes | Search/channel/paging/masking/unavailable-recording browser flows and owner-access backend tests pass. Real recording playback was not exercised. | Tested local flow; actual audio not verified |

## 4. Back end and live configuration

- Native equivalents exist: `life_slimming.api.cc_core.run` and
  `life_slimming.cc_autoshuffle.run`. The frontend maps life_cc_core to the native API.
- LIFE CC Lead Track and LIFE CC Assign Rule schema/install code exists. Match fields are
  added to Track, not to Lead, by this V26 setup.
- Live ERP: life_cc_core, life_cc_autoshuffle and life_pw were all returned with disabled=0.
- Live autoshuffle cron is `*/5 * * * *`.
- Three live rules were returned: Absent agent, New lead not called, Follow-up overdue.
  Each has enabled=1, test_mode=1 and last_moved=0.
- Their recorded last_run values were on 9 November 2026. This read does not prove that
  the scheduler is currently executing on time; scheduler-health investigation is still needed.
- No Hot Lead Overdue, Visited Not Booked, Settings or Permissions rule record was returned.
- The native scheduler defers to the active ERP autoshuffle script to avoid duplicate execution.

## Historical diagnostic (superseded by current source fixes; mock records only)

The original audit probe ran before the source fixes below and is retained as historical context. Its paid-without-booking, same-day attribution and failed-call results are no longer the current source behavior. The current regression fixtures cover these paths. The old results were:

```json
{
  "paid_lead_without_booking_milestone": "Joined Client",
  "sale_credit_uses_day_not_payment_timestamp": {
    "L1": "BOOKER_LATER_SAME_DAY"
  },
  "failed_call_paid_lead": {
    "status": "Not Response",
    "stage": "FOLLOW-UP",
    "milestone": "Joined Client"
  }
}
```

The last case starts with an UNTOUCHED/Lead record, a fully paid linked invoice,
and appointment status Not Booked. A failed-call save changes its business status/stage
while the computed milestone remains Joined Client. The ordinary booked-lead protection
test passes, so that test alone does not cover the PDF's broader paid-result guarantee.

## Verification executed

- Frontend: 48 test files passed.
- Python: 38 focused tests passed (core, bulk parsing, activity/history access, fast visit
  loading, no-follow-up, lead update conflicts and index migration).
- Dashboard V26 browser suite: passed at desktop/mobile widths with mocked ERP calls.
- Visit Report V26 browser suite: passed at desktop/mobile widths with mocked ERP calls.
- Dashboard parity browser suite: passed at desktop/mobile widths with mocked ERP calls.
- Historical diagnostic probes found gaps that were subsequently addressed in source; live ERP reconciliation remains outstanding.

No live configuration was changed during the original audit. The legacy route source update is recorded below.


## `/life_portal/leads` legacy route follow-up

The screenshot route is served by `PortalSourcePage.vue` as an iframe from the manifest entry
`leads → cc-new-dashboard-bhuvan-oct2`; it is not served by `CCDashboardPage.vue`. The legacy
source has been updated to remove the CC-Reports shortcut and align with the current live V26-4
CC add-ons: Agent 360, protected failed-call saves, journey strip/timeline, milestone chips,
Lead Distribution, auto rules, agent/permission settings, bulk upload, queue filters, TL section
collapse, resizable panel, 10-second menu pin/edge control and the compact lead age/header UI.
The add-on's API calls use `life_slimming.api.cc_core.run` on the local portal.

| Live `cc-new-dash` addition | Legacy route before this review | Legacy route source now |
| --- | --- | --- |
| Agent 360 nav entry | Missing | Added; opens the existing CC report at Agent 360 |
| Failed-call protection and connected-save tracking | Missing V26-4 hook | Added through the local `cc_core` API |
| Milestone strip, timeline, queue chips | Earlier local prototype only | Replaced by the live V26-4 add-on |
| Lead Distribution, preview/move/undo, ranking | Earlier TL UI only | Added using native `dist_preview`, `dist_move`, `dist_undo`, and `rank` actions |
| Auto Rules, agents/permissions, bulk upload | Earlier TL UI only | Added using native rules, settings, agents and bulk actions |
| Queue flag/status filters with counts | Missing | Added |
| TL section collapse and resizable lead panel | Missing | Added |
| Compact age badge and call/header layout | Initializer existed but did not appear in the supplied screenshot | Added a guarded retry from the active lead banner |
| Mobile call screen-pop | Already loaded by `life_portal_module.html` | Kept as-is; not duplicated |

The live route handler reads the checked-in JSON source dynamically. I fetched the Web Page DocType
read-only (modified 3 October 2026); that record still contains the shortcut, but `/life_portal/leads`
uses the manifest JSON source instead. I did not browser-verify the running route. Refresh `/life_portal/leads`
after clearing browser cache to see the checked-in source changes. Joined Client backend protection remains enforced by
`cc_update_lead`; the added warning is explanatory UI, not a substitute for the server guard.

The user's 11 November screenshot of `/life_portal/leads` confirms the prior Pin menu and shortcut
removal reached the page. A later screenshot shows the right-hand disposition panel but not the
second screenshot's Present Status / milestone / last call / next action strip or alternate-number
controls. The cause was the V26-4 strip's lead-ID lookup requiring a literal `Lead ID:` label, while
this banner displays the CRM ID without that prefix. The lookup now reads the active follow-up banner
directly. Static checks pass, but the strip and controls still need confirmation in a fresh browser
capture.

## Separate ERP Web Page: `/cc-new-dash`

On 11 November 2026 the connected ERP Portal read returned published Web Page `cc-new-dash`,
modified `2026-11-11 08:24:23.727425`. Its HTML still contains the CC-Reports header shortcut.
Its JavaScript includes the V18 mobile call screen-pop, V26-4 Agent 360 menu and the 9 November
V26-4 core add-on (journey strip/timeline, lead distribution, auto rules, permissions and bulk
upload), plus responsive menu, queue filters, TL collapse, resizable panel and age/header updates.
The corresponding Agent 360 and V26-4 add-ons have now been copied into the `/life_portal/leads`
source with their API call adapted to `life_slimming.api.cc_core.run`. The ERP Portal connector is
read-only for Web Page documents. The local bench's `mysite.local` copy is older (modified
17 September 2026), so no console write was made to it. Live `cc-new-dash` itself remains unchanged.
After these source updates, the legacy page JavaScript syntax check, five legacy status tests, five
dashboard-group tests and seven CC core unit tests passed. A fresh browser capture is still needed to
confirm the full visual update on `/life_portal/leads`.

## 11 November live Server Script follow-up

The ERP Portal connector returned `Server Script/life_cc_core` as an API script with method
`life_cc_core`, modified `2026-11-11 11:36:56`. Its UI actions (`summary`, `timeline`, `attempt`,
`connected`, `header`, distribution, agent configuration, matching and `add_number`) are present in
the local native API. The legacy page calls `life_slimming.api.cc_core.run` directly, and the
`life_cc_core` endpoint alias resolves to that same function.

I aligned the local summary's conversion-agent fallback with the updated Server Script: retain a
saved `LIFE CC Lead Track.converting_agent` first, then event-derived credit, then the appointment
agent when there is payment evidence. The local API keeps its app-specific module authorization,
owner checks and atomic connected-save protection. I did not replace those with the less restrictive
standalone Server Script implementation. API unit tests (7), legacy JavaScript syntax, and the two
legacy UI suites (5 each) pass. ERP Portal provides read-only document access here, so this updates
the local API implementation only; it does not deploy or execute the live Server Script.

## Browser errors reported after the API update

The pasted `/life_portal/leads` console log showed repeated `cc_core.run` 500s because the local
Lead table does not have the optional `custom_cc_appointment_agent` column. The legacy API now
filters optional Lead query fields against installed table columns for both summary and report
queries. The same log showed `octQuickForm` reading an undeclared `pipe`; it now resolves the
`#wf-pipeline` element before appending the enquiry details. API unit tests (7), legacy UI suites
(5 each), and JavaScript/Python syntax checks pass. The running page still needs the updated app
source before these fixes will be visible; no live server deployment was performed.
