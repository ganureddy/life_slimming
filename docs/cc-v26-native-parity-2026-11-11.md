# Native CC V26 workflows

The portal CC page now includes V26 lead journey summaries, timelines, failed-call retries,
recovery filters, resizable disposition panel, Agent 360, attendance (page and drawer),
and the five-tab lead distribution panel. Existing calling and native booking remain integrated.

`life_slimming.api.cc_core.run` contains the migrated V26 core, with owner checks on summaries,
per-lead actions and reports. Connected worksheet saves and tracking updates share a transaction.
Failed calls preserve established business outcomes and upcoming appointments. Manager distribution
rechecks protected status when applying a preview. Excel and CSV uploads preview up to 500 rows.

## Installation

Deploy the app and built portal assets, then run the site's normal `bench --site SITE migrate`.
The after-migrate hook `life_slimming.api.cc_v26_setup.execute` installs missing journey tables
and matching fields without replacing existing data or enabling automatic rules.

The native five-minute scheduler defers to the existing enabled `life_cc_autoshuffle` Server
Script when present, preventing duplicate jobs. New rules default to test mode; existing rule
settings are preserved. Permissions are read from existing permission rules, with administrator
and Call Center Export / System Manager access. System Managers can edit distribution permissions.

The full ERP + ConVox + Mobile Agent 360 view opens the existing
`/branch-visit-report-CC-LEAD-REPORTS#a360` webpage only when requested. Native lead journey
reporting loads through the app API. The staff attendance view uses Ho CC staff for managers
and the signed-in employee for agents; the existing roster provides shift and leave context.

## Verification

- Portal production build.
- Node test suite, including CSV and recovery-flag cases.
- Python tests for ownership, manager access, stale attempts, booked-outcome preservation,
  connected saves, conflicts, and Excel parsing/limits.
- Mocked browser checks at desktop and mobile widths for dashboard regression and new workflows.
