# Reactive Vue conversion — 25 October 2026

The remaining three controller-backed routes now render with Vue templates, reactive composables and shared table, multiselect, dialog and panel components. The old task, employee and cluster DOM controllers and their runtime have been deleted. CC legacy pages were not changed.

- My Tasks: task and ticket forms, configuration, scope and permissions, member-specific group completion, review actions, queue ordering, uploads, CSV/workbook exports and masked contacts. Persistence retains fresh document reads and metadata merging. Read requests cancel on navigation; writes have duplicate-submit guards.
- Employee Sale Master: employee identity and credit allocation, treatment weighting, cascading filters, totals, tree and transaction views, drills and workbook export. Restricted branch requests retain explicit branch filters. Computation does not mutate source invoices.
- Cluster Dashboard: permitted clusters, finance, attendance, walk-ins, appointments, executions, recoveries, approvals and media. Sales Race is rendered in Vue, including payment allocations, targets and employee rankings. Sections support collapse, ordering and zoom; failures are displayed separately.

## Verification

Unit and regression suites cover allocation conservation, treatment shares, task metadata, visibility, group review, queue errors, individual/group assignment, ticket creation/resolution, read cancellation and permission failures. The full portal production build passes.

The browser fixture checks all three routes at 1440px and 390px: employee totals/tree/drilldown, task start with persisted metadata, cluster collections and daily target calculations, no iframe, no horizontal overflow and no runtime exceptions. ERP API calls are intercepted. No live ERP transactions or messages were submitted. Exact live-data and pixel parity across every workflow remains unverified.
