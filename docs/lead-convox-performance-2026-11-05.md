# Lead and ConVox performance changes — 5 November 2026

Application changes prepared locally:

- ConVox failures retry after 15, 30 and then 60 seconds; successful polls restore 5-second updates. Authorization failures stop retries.
- Poll/history batches reuse agent and phone-search results within that request only. Trusted dial references still verify the current phone number before linking and avoid an unnecessary phone scan.
- ConVox loads as a separate chunk when an authorized user enters the workspace. Once mounted, the phone persists across workspace navigation and session refreshes.
- Opening a specific Lead uses an exact primary-key filter rather than the broad substring search. Normal search retains its existing behavior and access contract.
- `life_slimming.lead_performance.execute` runs after schema migration. It adds missing indexes for owner/date Lead cohorts, appointment/follow-up dates, sub-status, ConVox agent/time polling and lead summaries, and Lead Version history. It skips missing optional tables/fields and indexes already covered by the leftmost columns of an existing full-column index.

Validation:

- 130 Python tests passed, including index idempotency, existing index coverage, missing schemas, request-local lookup reuse, agent scope, ambiguity, callbacks and history.
- 45 JavaScript test files passed, including polling recovery, call lifecycle, caller matching and deferred phone loading.
- Isolated browser fixtures passed for Lead dashboard desktop/mobile behavior and ConVox history counts, paging and recording links. ERP responses were mocked; no live calls or business writes were made.
- Production-style build was checked in `/tmp`, without replacing the deployed portal bundle or Frappe entry page.

Deployment handoff (not executed): deploy the application changes, build the portal assets through the normal release workflow, and run the target site's normal `bench --site <site> migrate`. The migration hook creates indexes; large-table index creation belongs in the release's maintenance window. If ConVox schema is installed later, rerun migration to cover its new table/fields.

Production acceptance still required: confirm actual indexes, inspect query plans and timings during peak use, and validate real outgoing calls, incoming notifications and history with an authorized agent. Existing phone normalization searches use SQL expressions and general text searches use substring matching; ordinary indexes do not make these scans disappear. The changes reduce repeated work, but no production speedup or complete resolution is claimed without measurements. Server capacity, Redis and worker administration are outside this change.
