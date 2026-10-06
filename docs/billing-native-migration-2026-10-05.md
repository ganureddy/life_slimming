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
