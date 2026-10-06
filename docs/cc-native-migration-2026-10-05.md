# CC native Vue migration — 5 October 2026

Status: **first native read-path slices implemented; full module parity and production cutover pending**. Existing Web Pages, API Server Scripts, DocType Event scripts, Scheduler scripts and Permission Query scripts remain intact. No live business records were written, unpublished, disabled or deleted.

## Review routes

After building/deploying the frontend with its matching Python changes:

- `/life_portal/native/cc-dashboard` — Vue lead list with server pagination (40 rows), created/updated/posting/appointment/follow-up date modes, permitted-history search, on-demand lead details/status history, and links to the existing native appointment scheduler and ConVox history.
- `/life_portal/native/cc-visit-report` — Vue appointment schedule, date shortcuts (India timezone, sales cycle 6th–5th), branch/agent/status/search filters, date/branch sorting, 40-row rendered pagination, visit/booked/pending/overdue cards, and filtered CSV with masked phones and spreadsheet-formula protection. Financial events load only on request.

These are explicit preview routes. `/life_portal/leads` and `/life_portal/ccvisit`, sidebar callers and old public routes retain their current implementations. The previews use the same portal module access gates. Shared table, pager, API adapter, date/status/CSV helpers and styles can be reused by later modules.

## Latest live Visit Report revision

Read `Web Page: call-center-new-report-bhuvan` through the ERP connector. Its live `modified` value was `2026-10-05 02:06:25.928460`. HTML and CSS matched the local source; JavaScript differed. Updated the local page source and revision metadata with the live JavaScript, retaining the local `life-portal:primary-ready` loading hook. No database page was changed.

SHA-256 of the retrieved live JavaScript before retaining that hook:
`c6944244c2ba93800df3d3f387081fd6ae91bb0de0d31cc795e2de3d003d7bde`

The revision includes richer schedule cards, overdue/pending and low/high indicators, business-month/today funnel shortcuts, panel layout changes and styling refinements. The native schedule implements status precedence and pending/overdue calculations; full funnel, branch-average flags and remaining analytics are still parity work. Updating source revision metadata does not certify full Vue migration or retirement readiness. The earlier retirement CSV remains a historical audit snapshot.

## Backend changes

- `cc_get_leads.run`: opt-in `page_size` (bounded to 1–100) and `start` for date-range reads; stable ordering; total and has-more metadata. Non-paginated callers retain the 5,000-row contract and truncation warning. Existing role and owner restrictions and appointment enrichment remain.
- `life_cc_agent_marketing_data.run`: `view=appointments` returns essential schedule fields before the financial joins. It retains the report's owner scope. Returns total/truncated metadata at a 10,000-row cap; the preview prominently labels partial counts and blocks export until the date range is narrowed.
- Fixed an existing report scope bug: the seven-character `lifescc` prefix was sliced at index 6, so numeric agent accounts were not recognized. Regression tests now verify that `lifescc13@gmail.com` cannot select another owner via `agent_owner`.
- Financial events continue to use the existing Python report implementation. Their filters are explicitly separate from the schedule filters. No event, scheduler or permission scripts were migrated or removed.

## Validation performed

- All 12 frontend Node test files passed, including native date-boundary, status-precedence, pending/overdue and CSV tests.
- Five backend tests passed with mocked database calls: bounded pagination, legacy contract, owner scope, essential schedule query isolation, and guest rejection.
- Isolated production compilation passed. Native page chunks were approximately 6.1 KB (dashboard) and 8.7 KB (visit report), before gzip, excluding shared runtime/components. Existing billing-size and ConVox import warnings remain unrelated.
- Headless Chrome at 1440px and 390px passed: no iframe, no viewport overflow, one initial module-data call, pagination, lazy details and financial events, branch filtering, masked all-filtered-row CSV, failed-load/retry behavior, and blocked export for truncated data.
- Browser business APIs were mocked. This proves frontend request/render behavior, not live query latency or production functional parity. Production entry assets were not rebuilt/deployed during this verification; compilation output was isolated under `/tmp/cc-native-build`.

## Completion gates, in module order

1. **CC Dashboard first:** port lead creation, contact/owner editing, the complete status transition and follow-up workflow, worksheet, walk-in actions, notifications and phone integration. Preserve server validation, concurrency rules and save side effects. Compare role-specific behavior and counts to the current dashboard; then validate native booking/call flows end to end.
2. **CC Visit Report next:** port standard funnel, ranking/agent, marketing, walk-in and cluster sections, financial drilldowns, visit ordinals, branch staff/invoice annotations, low/high flags, and section print/PDF exports. Preserve latest live rules and branch scopes. Review the legacy financial query caps and detect partial datasets; measure live SQL/query timing before deciding pagination/aggregation optimizations.
3. **Production checks:** agent/manager/branch permission matrix, empty/error/large date ranges, exported totals/masking, cross-module navigation, actual network payloads, first useful render and live backend timing. Gate caller switches on complete parity and acceptable performance, not on a source timestamp or the mocked request count.
4. **Remaining modules:** establish usage order from real traffic/workflow evidence and migrate one at a time with the shared Vue pieces. Resolve missing API dependencies before moving callers. Keep every event, scheduler and permission script until tested equivalent backend behavior is deployed.
5. **Retirement per completed module:** switch callers and verify redirects, back up exact database records, disable/unpublish, observe and retest, then delete only the verified old records. Keep app source and native Python APIs. No bulk deletion.
