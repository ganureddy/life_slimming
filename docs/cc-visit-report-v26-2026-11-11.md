# Native CC Visit Report V26 update

Reviewed ERP Web Page `cc-lead-reports-v26-4-bhuvan`, route
`branch-visit-report-CC-LEAD-REPORTS`, modified 10 November 2026.
The live `Branch visit report` Server Script matches the migrated backend's source revision.

The native page now provides:

- Six report tabs, deep links, compact header, print and selectable share previews.
- A sixth-to-fifth business-month daily appointment/visit/booking strip, with month navigation.
- Branch and agent grouping, sortable counts, masked paged drilldowns and complete-row CSV exports.
- Persistent card/summary visibility and text-size controls.
- Lazy three-business-month conversion comparisons.
- Agent 360 ConVox/mobile activity, dispositions, talk time, seven-day timelines,
  idle gaps and call/update/appointment mismatches.
- Existing owner-scoped no-follow-up API with day buckets, outcome filters and paging.
- Native Lead Journey reporting through the core added with the CC dashboard update.
- Marketing-source and invoice collection summaries. Consultant attribution is taken from
  the invoice's linked Therapy Plan, without inventing a fallback consultant.
- Today's appointment and staff attendance panels.
- A lightweight change marker every 90 seconds while visible; new data requires an explicit refresh.

All financial data and comparisons load on demand. Partial appointment results block visit
exports and share previews. Activity exports are blocked when their source limit is reached;
timelines are capped at 1,000 events per agent, and ranges above seven days omit timeline/idle checks.
Phone numbers remain masked in drilldowns and exports. Activity APIs enforce report-module
access and scope ordinary agents to their own ERP user and ConVox ID.

The activity API is native Python; no new Server Script installation is needed. Deploy the
backend and built portal assets. The preceding CC V26 schema migration is still required for
Lead Journey. Existing automatic redistribution rule settings are unchanged.

Validation: frontend unit suite; focused Python aggregation/access/attribution tests; production
build; mocked desktop/mobile browser suite covering tabs, drilldowns, masked details, lazy data,
share preview, today appointments, activity, no-follow-up, partial exports and errors/retry.

## Loading optimization

The appointment-only request now filters by appointment date before reading Lead records,
rather than querying a union of creation/posting/appointment cohorts. Native visit lists request
compact rows, bounded to 10,000 plus a partial-result sentinel; other appointment consumers
retain their detailed fields. Calendar requests use a single database grouping by day, branch,
agent and appointment outcome, with no client names or phone payload. Agent Performance uses
already-loaded appointment rows. Financial data is reused across report tabs until Apply/refresh
changes or refreshes the range. Calendar back-navigation reuses a short per-login memory cache;
explicit report refresh bypasses it. The change-marker request runs on its timer, not on initial paint.

Validated query shape, bounds and permission-aware reads with focused backend tests, and
verified in the desktop/mobile browser suite that Agent Performance makes no invoice request
and switching between financial tabs reuses one completed request. Live server latency was not
benchmarked; these checks verify the removal of avoidable work rather than a measured speedup.

## Live report refresh, 11 November 2026

Compared the current `branch-visit-report` (modified 11 November 2026 08:59:39)
with the prior V26 report. The HTML/CSS are unchanged; JavaScript adds Agent 360
call history, lazy recording playback and lead field-change history.

The native activity report now opens history from summary cards and per-agent
ConVox/CC counts. A modal provides channel tabs, search, 30-record pages, masked
phone numbers, direction, status, duration, disposition and recording controls.
Lead Updates shows the reportable changed fields and before/after values.

History and recording URLs are requested only on demand through
`life_slimming.api.cc_report_history`. Agent scope is checked on both endpoints;
a caller cannot fetch another agent's recording by guessing a call ID. Mobile
private-file URLs retain their original file route, while trusted PBX recording
URLs use the existing public HTTPS ConVox host. No live Server Script changes
or additional data migrations are required for this update.
