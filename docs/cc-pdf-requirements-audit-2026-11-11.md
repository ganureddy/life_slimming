# CC Dashboard and CC Visit Report: PDF audit

Source checklist: `/home/life/Downloads/Temp file.pdf`, supplied by the user.
Audit date: 11 November 2026, India time.

**Result: the native pages do not yet implement every CC requirement in the PDF.**
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
| Failed calls preserve appointment/visit/business results | Existing booked-outcome unit test passes. A paid lead with no appointment status can still become FOLLOW-UP / Not Response; see reproduction below. | Partial / defect |
| A fresh lead becomes FOLLOW-UP with the failure reason | The attempt branch implements this when previous sub-status is blank/Lead/failed and no appointment lock applies. | Present |
| Joined Client requires booked + any paid bill | `milestone_of` returns Joined Client whenever paid money exists, even without booked evidence. | Mismatch |
| Joined clients receive feedback calls only | The next-action label says Feedback call only. This alone is not proof of a hard restriction on every save/booking path. | Partial / integration not verified |
| Joined clients never move | Manual distribution rechecks the Joined milestone. Scheduler payment matching only uses Patient.custom_lead, and does not include verified alternate-number Track matches. | Partial / protection gap |
| Add another number, match branch client, TL verify | Native journey UI and add_number/match/match_verify actions exist. Actual matching against live branch records was not exercised. | Present / integration not verified |
| 100% credit to the agent who booked the converting visit | Credit selection exists, but compares booking date with bill posting date, without payment timestamp ordering. Same-day correctness is not guaranteed. | Partial / defect |
| Present status, last call, unreachable streak, next action | Displayed in the journey component; browser checks pass. | Tested |
| Different milestone colours | Native journey chips use the same p-green class for all milestone labels. Other legacy workflow stamps have colours, but the new milestone strip lacks the PDF palette. | Partial |
| Received time and visit as branch code–consultant | Core header API returns received_first/received_this/visit. The native journey template does not render these values. | Missing UI wiring |
| Short names instead of emails | Journey owner is shortened by the API; the main worksheet banner still displays raw lead_owner. | Partial |
| Full timeline | Timeline opens and renders. It is bounded, and combines activity/follow-up/mobile logs; ConVox details are provided through separate history views. | Tested basic flow / bounded coverage |
| Compact dashboard title, golden age circle, 45-degree call-button divider | Existing banner still uses its earlier age text/stamp layout. The PDF's specific title layout has not been reproduced. | Missing / not matched |
| Remove CC-Reports button | `cc-reports-link` is still rendered in CCDashboardPage.vue. | Missing change |
| Flag/status filters actually filter and show counts | Computed flag/status filters exist; desktop/mobile queue tests pass. | Tested |
| No-show recovery and post-consult closing queues | Recovery tiles exist and open filtered queue views. | Tested basic flow |
| Red/teal/orange recovery warnings on the lead | Specific warning banners are not rendered in the native lead worksheet/journey. | Missing |
| Menu hides after 10 seconds, Pin, clickable MENU tab | Native menu has a burger and collapses when entering follow-up; there is no ten-second idle timer, Pin, or MENU edge-tab control. | Missing |
| Resizable side panel | Pointer/keyboard resizing and saved width exist. | Present; browser layout checked, drag persistence not separately exercised |
| Collapsible TL sections | TL sections are ordinary section/header elements; no collapse control/state is wired. | Missing |

## 2. Lead Distribution

| PDF requirement | Finding | Status |
| --- | --- | --- |
| Filter → checklist → receiving agents/method | All controls exist in one view. There is no explicit three-step progression. | Partial |
| Preview, move and undo | Mocked desktop/mobile request/response flows pass. Actual live ownership changes were not performed. | Tested UI; real mutation not verified |
| Export list to Excel | Preview export currently uses CSV, which Excel can open; it is not an .xlsx workbook. | Partial |
| Dormant-only (90+ days) | Dormant filter uses configurable dormant_days, default 90. It tests last modification age. | Present |
| New lead, overdue follow-up, hot overdue, visited-not-booked, absent agent triggers | Five trigger types are supported in native UI/scheduler code. Only three rule records were found live. | Present; only three configured |
| Absent Auto/Manual | Both modes exist. | Present |
| Seven ranking methods | Conversion, bookings, walk-ins, lowest load, round robin, fewest leads, fewest follow-ups are implemented. Ranking UI test passes. | Tested basic ranking flow |
| Green What is applied summary + Accept & Apply | UI has direct Save rule and overlap resolution; no required preview/accept step. | Missing |
| Rules default to Test mode | newRule uses test_mode=1; browser assertion passes. All three live rule records are also in Test mode. | Tested / live configuration confirmed |
| Workload switch and default limits | Defaults are 150 overdue/30 days and 1000 open/60 days; UI exposes the switch/windows. | Present |
| Warning before assigning over capacity | Agents table displays over-limit status; manual dist_move does not enforce or request acknowledgment of those caps. Scheduler code does apply caps. | Partial |
| Configure senior closers and dormant days in Settings | Dormant days is editable. Server accepts seniors, but the native settings form does not expose the seniors list. Identity mapping for the three named seniors was not verified. | Partial |
| Bulk Excel/CSV file, duplicate skip, assignment modes | Parsing, file selection, default duplicate skip and Auto/one/split/rank/file modes exist. Parser tests pass. Actual live bulk creation was not performed. | Tested parsing; mutation not verified |
| Downloadable Excel template | No download/template control found. | Missing |
| Paste rows | No paste-input control found. | Missing |
| Row-by-row preflight | Preview shows the first 30 rows; detailed validation/result messages largely come after submission. Not a complete pre-submit row audit. | Partial |
| TL/Admin/Surya/Bhuvan/MD may move leads | Native access uses configured allowed users plus Call Center Export/System Manager. No live Permissions rule was returned; named-user requirements are not explicitly configured by the native defaults. | Mismatch / named access unverified |
| Only Bhuvan and Naren may edit permission list | Native EDITORS includes Administrator and every System Manager. | Mismatch |

## 3. CC Visit Report

| PDF requirement | Finding | Status |
| --- | --- | --- |
| Lead Journey tab | Native tab, report request and rendering pass browser checks. | Tested |
| Agent 360 ordinary agents see only own data | Activity and history APIs enforce ERP-user/ConVox mapping; negative access tests pass. Manager browser tests use mocks. Real agent-account integration remains unverified. | Tested access logic |
| Select report sections to send | Share preview supports visits/groups/rolling comparisons and copy. It does not provide the PDF's complete Agent 360/business/paid-bill section selection. No message was sent. | Partial |
| Paid bills show correctly | Invoice and paid totals are rendered; attribution/sum tests pass with fixtures. No reconciliation against actual ERP invoices/payments was performed. | Present / real totals not verified |
| Compact Untouched report | Untouched counts exist in the core funnel, but no dedicated compact Untouched drilldown/report is exposed in the native report. | Partial / missing dedicated view |
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

## Reproduced logic gaps (mock records; no production writes)

The audit executed actual core functions with synthetic records and reused the isolated
JourneyTests fixtures. The results were:

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
- Additional diagnostic probes above found uncovered business-rule gaps despite the passing suites.

No application behaviour or live configuration was changed during this audit.
