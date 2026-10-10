# Billing Vue migration — 5 October 2026

Status: native Billing workflow implementation available locally; live acceptance
and production deployment pending. The user requested complete Billing work in
isolation without disturbing the existing page.

## Routes and isolation

- `/life_portal/native/billing` — native Vue Billing workspace, defaulting to Billing.
- `?view=recent|pending|collections|approvals` — individual native views.
- `?invoice=<invoice ID>` — open an invoice inside the native workspace.
- `/life_portal/billing` and the existing sidebar destination remain unchanged.

The native route retains the Billing module access gate. It does not import
`billingV2LiveSource.json`, run exported page scripts, install a global Frappe
bridge, or link/redirect to the existing Billing page. The existing Billing
component, exports, backend APIs and production assets were not modified.

The invoice print preview renders the server's existing print format in a
sandboxed, read-only frame. This is an invoice document preview, not an embedded
legacy Billing application. PDF download opens the existing ERP PDF endpoint;
WhatsApp and Razorpay open their respective services only when requested.

## Native implementation

| Area | Implemented behavior |
| --- | --- |
| Workspace | Billing, Recent bills, Pending dues, Collections and Approvals; branch defaults; Head Office all-branch selection; India dates |
| Dashboard | Today and business-month collections, submitted invoice count and outstanding aggregate |
| Clients | Name/mobile/client ID lookup, client summary, lifetime aggregates and latest invoice history |
| Registration | Lead lookup/autofill, required fields, branch/practitioner mapping, duplicate mobile check, WhatsApp OTP, PD-form upload and OTP flag persistence |
| Bill editor | Individual therapies, package-only filtering, templates, fixed LIFErise package rules, consultant and doctor, source/reference/incentive selection |
| Pricing | Bounded live parent Pricing Rule refresh with bootstrap fallback, per-quantity offers, rate reset/adjustment, coupons, min spend and discount cap |
| Complimentary items | Subtotal eligibility, reduced pending-balance slab, item quantity limits and cumulative value limit |
| Draft creation | Review before creation, server-calculated final invoice, draft reuse when approval creation fails; no automatic repeat after an uncertain creation result |
| Invoices | Line details, office remarks, cost justification, approval history, read-only print preview, today's PDF download, explicit submission confirmation |
| Discounts | L1/L2/L3 batch requests, L4 final amount including GST, used-level protection, cumulative percentage cap, approval/rejection and refreshed history before mutations |
| Collections | Multiple payment modes, outstanding/ref checks, fresh invoice balance before manual recording, separate online/manual paths |
| Razorpay | Checkout SDK, payment links, optional backend QR, WhatsApp link delivery/sharing, bounded polling and manual status check; online rows never reposted through manual collection |
| Loans | Minimum ₹25,000, Aadhaar/PAN/transaction ID, four uploads, camera/microphone declaration with 60% keyword verification, private video upload and video persistence |
| Receipts | Recorded Payment Entry IDs, paid/balance totals, editable receipt mobile, copy and WhatsApp receipt |
| Lists | Server pagination, server search across invoice/client/mobile, dates/status/minimum-due filters, recent date presets, pending ageing and explicitly page-specific totals |
| Stock receipts | Overdue receipt reminder only; Billing remains available |

## Verification

- All 13 frontend Node test files passed. Native domain tests cover monetary
  strings/zero values, package/coupon/GST totals, quantity/date offer eligibility,
  payment overcollection/reference/loan-proof guards, practitioner deduplication,
  mobile normalization, approval visibility and 6th–5th date boundaries.
- Headless Chrome workflows passed at 1440px and 390px: client search, draft
  payload, print-preview sandbox, approval, submission, overcollection blocking,
  manual receipt, OTP registration, PD upload and module navigation.
- Additional browser cases passed: settled Razorpay link produces a receipt
  without manual reposting, rejection updates, L4 request amount, and loan
  collection blocked until attachments and verified video exist.
- Collections browser regressions passed at both sizes: branch defaults,
  totals, date presets, loading/empty/error/retry behavior and viewport overflow.
- Isolated production compilation passed under `/tmp/billing-native-build`.
  The existing Frappe entry and deployed assets were not rewritten. Existing
  legacy Billing-size and ConVox import warnings remain.
- Business APIs, OTP, uploads, online settlement, camera and speech recognition
  were mocked. No test sent an actual message, created a live record, captured
  money or requested real camera access.

## Live acceptance before deployment/cutover

Confirm the agent/branch/manager/MD permission matrix, actual bootstrap and
Pricing Rule records, template and coupon amounts, approval chains, GST/ex-GST
and outstanding totals, posting-date/PDF rules and business-month boundaries.
Exercise real OTP, upload, print/PDF, Razorpay settlement and loan-video flows
in an appropriate test environment. Measure actual queries and payloads.

The reused collections SQL endpoint accepts a branch filter; frontend branch
restrictions alone are not proof of server-side branch authorization. Review
its authorization before treating this preview as production-ready. Concurrent
writes and external payment side effects continue to rely on the existing
backend transaction validation and idempotency.

No production caller switch, legacy record retirement or deployment was done.
Billing remains the migration priority; do not start the next page until its
live acceptance is complete.

## Read-only site acceptance, 5 October 2026

The local `mysite.local` site contains 23,269 Sales Invoices and 19,833 Patients;
its Razorpay API key is in live mode. No test tenant is available. We did not
send an OTP, create a payment link, settle a payment or create a client.

`bench --site mysite.local execute life_slimming.billing_acceptance.audit`
compared the collections report with independent ledger sums for 6 September
through 5 October 2026. Billed, collected and outstanding amounts matched.
A restricted user saw one permitted branch, and an explicit request for a
different branch was denied. The endpoint now applies Branch User Permissions
to its raw SQL; the previous report had no server branch check.
`billing_acceptance.otp_guard` confirmed a synthetic unverified mobile is
rejected before client creation, without sending an OTP or writing a record.

Client registration now requires a short-lived, user-and-mobile-bound OTP proof
in the server cache before creating a Patient. The verifier creates the proof
after a correct code, and successful creation consumes it. The browser no
longer sets the OTP flag after creation. These changes are local and still need
acceptance on a safe test site, including OTP delivery/expiry and Razorpay
settlement. Permission coverage for every role and branch is also pending.
The mocked desktop/mobile Billing browser workflow and isolated production
build passed after these changes.

## Billing UI restoration

Restored the tab toolbar, client search, daily/monthly KPI cards, client summary,
numbered editor sections, sticky invoice breakdown, grouped pending invoices,
and approval shortcuts. Registration, invoice details and invoice review open
in native dialogs. Layouts were checked at desktop and mobile widths.

Auto-adjust targets the grand total including GST and respects rate bounds.
Source selection follows existing customer/lead locks and backend source values.
Mocked browser checks cover these layouts and billing workflows; live acceptance
above remains required before replacing the existing Billing page.

## Follow-on page

The smallest exported page is Cluster Dashboard. A native Vue preview is now
available at `/life_portal/native/cluster-dashboard`, with the same date,
cluster, totals and branch table views as the exported page. The server's
`cluster_dashboard_api` currently has empty `CLUSTER_MAP` and `USER_CLUSTER`
configuration, so it returns all branches. Configure and enforce actual cluster
permissions in that API before making this page a production destination.

## Legacy comparison follow-up — 8 October 2026

Compared the native workspace with the exported Billing source in
`life_portal/src/data/billingV2LiveSource.json`, including its later JavaScript
patches. The main tab structure, business-month defaults, client summary,
therapy editor, approval actions, month-grouped dues and collections remain.

Restored the legacy existing-video declaration path: select a video, review it
with playback controls, explicitly confirm the client declaration, then upload
privately and pass the verified URL to the existing loan collection payload.
Recording and speech verification remain available. Object URLs are released
when cancelling, switching to recording, uploading successfully or unmounting.

Pending dues now accepts optional date bounds, as the legacy query does, with
All dates and This business month shortcuts. Branch restrictions and pagination
still apply. Failed list requests no longer also show a misleading empty state.
Client history is keyboard-scrollable. KPI accent borders, numerical table
alignment, action spacing and spacing between pending-month groups were polished.

Updated the workflow browser test for the current consultant/therapy search
controls, invoice generation labels and new-window View bill action. Added
assertions for clearing pending date bounds and requiring confirmation before
uploading an existing declaration. The mocked workflow passes at 1440px and
390px, and the collections browser suite and billing domain tests pass.
Desktop/mobile screenshots were inspected. An isolated production build to
`/tmp/billing-review-build` passes with existing chunk-size/import warnings.

This is local verification; no deployment or live financial transactions were
performed. Live OTP, actual video playback/upload, Razorpay settlement and the
full role matrix still require acceptance. This comparison does not certify
complete parity for every legacy patch or live backend configuration.

## Full billing review — 9 October 2026

Reviewed the exported Billing JavaScript, including appended patches, against
all native Billing components and the local create-invoice/payment adapters.
This pass also fixes the legacy portal wrapper, not just the Vue preview.

| Area reviewed | Outcome |
| --- | --- |
| Header, tabs, branch scope and KPIs | Retained branch scope and business-month defaults; protected count refreshes from stale responses. Legacy date helpers now use India time, including `now_datetime` for loan uploads; date arithmetic is timezone-independent. |
| Client search and summary | Search requests cancel when typing, clearing, changing views or selecting a client. Client summary loads atomically. Existing-customer source locking queries paid history beyond the 40 displayed invoices. |
| Registration, lead lookup and OTP | Existing workflow retained; registration inputs lock during asynchronous operations so the verified mobile cannot change mid-request. |
| Therapy selection and templates | Editing a selected therapy clears its stored selection and pricing. Switching back to individual therapy clears package state. Preview now runs submission validation. |
| Consultant, source and doctor | Restored optional doctor selector and backend doctor payload. Doctors use strict physical-branch matching, including legacy spelling aliases; all-branch consultant flags do not bypass this rule. |
| Offers, coupon and fixed packages | Existing quantity/date offer logic retained. Fixed packages clear and hide discount requests like legacy. Both Vue totals and the legacy portal adapter ignore extra coupons/discounts for fixed packages, matching the create-invoice backend. |
| Complimentary sessions and remarks | Reviewed current slab, cumulative quantity/value limits and 400-word remarks guard; retained existing behavior. |
| Draft generation and preview | Retained draft reuse/uncertain-result protection. Added print styling that isolates the draft preview from portal navigation and buttons. |
| Invoice details | Restored server net/GST/discount breakdown, doctor/therapy-plan identifiers and expandable cost justification. Explicit zero cost/profit values remain zero. Grouped invoice actions and removed unnecessary dialog minimum height. |
| Approvals and submission | Further requests now enforce the same 0.5%–5% per-level range as the editor and legacy patch. Existing combined cap, L4 and fresh-history checks retained. |
| Manual and online collection | Reject negative/non-finite amounts. Refresh outstanding before initiating online payment and include other unsettled rows when checking the balance. Clear prior polling timers before a new poll. |
| Loans, uploads and receipts | Retained recorded and reviewed-upload declarations. Recording/upload work blocks closing or recording collection; file size feedback occurs before video preview. Existing receipt workflow retained. |
| Recent, pending and collections | Existing date presets, pagination, grouped dues and totals retained. Previous follow-up restored optional pending date bounds and all-date shortcut. |
| Legacy presentation | Improved visible keyboard focus, table row/action spacing and long KPI amount wrapping. No business data or backend records changed. |

Verification:

- All 15 frontend Node test files passed.
- Expanded native workflow browser checks passed at 1440px and 390px:
  cancelled searches, doctor branch filtering and payload, package restrictions,
  stale therapy selection, print styling, older paid-history source lock,
  approval percentage minimum, normal draft/approval/submission/payment flows,
  OTP/registration, recorded and reviewed-upload loan consent, and no overflow.
- Collections desktop/mobile browser checks passed.
- New legacy browser checks passed at both widths with mocked business APIs,
  including a frozen 20:00 UTC clock that must resolve to the following India
  date, timestamp availability, month-boundary arithmetic, fixed-package totals and no runtime errors.
- Native invoice/preview and legacy mobile screenshots were inspected.
- Isolated production build succeeds under `/tmp/billing-audit-oct9-build`.

The exported JSON remains a reference snapshot; the legacy portal adapter corrects
its fixed-package preview formula at load time. Both rendered pages now follow
the backend fixed-package behavior. Live role permissions, OTP delivery, provider
settlement, physical camera/speech and actual file persistence remain live
acceptance items. No deployment or financial transaction was performed.
