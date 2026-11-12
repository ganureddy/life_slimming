# Branch Visit Report: live-to-Vue comparison

> Historical progress record. The current attachment-based comparison, API mapping, request findings and remaining gaps are in [cc-attached-reference-audit-2026-11-12.md](cc-attached-reference-audit-2026-11-12.md). Some gaps listed below have since been implemented.

Reference: ERP Web Page `branch-visit-report`, modified `2026-11-11 08:59:39.792561`.
Its original four main tabs are Branch Visits, Agent Report, Lead & Digital Marketing,
and Consultant / Manager. Later addons expose Agent 360 and Lead Journey.

## Routes and component ownership

| Report | Path under /life_portal | Component |
| --- | --- | --- |
| Branch Visits | /ccvisit | CCBranchVisitsPage.vue |
| Agent Report | /ccvisit/agents | CCAgentPerformancePage.vue / CCAgentPerformanceView.vue |
| Marketing | /ccvisit/marketing | CCMarketingReportPage.vue |
| Consultant / Manager | /ccvisit/consultants | CCConsultantReportPage.vue |
| ERP + ConVox + mobile activity | /ccvisit/activity | CCActivityPage.vue |
| Lead Journey | /ccvisit/journey | CCJourneyPage.vue |

ConVox, No Follow-up, and Untouched have child paths under `/ccvisit/agents`.
Old `?tab=` and hash aliases redirect to the corresponding paths. The persistent
CCVisitReportPage provides shared reactive data; child pages do not start another
copy of appointment/calendar/financial loading. Date query parameters survive tab navigation.

## Changes in this comparison

- Removed the second sidebar; retained the portal's main navigation.
- Copied legacy Agent and Marketing theme rules into report-scoped styles, with Poppins.
- Marketing: agency multiselect, category/branch/search, 13 KPIs, source/ad-set/category/
  campaign tables, conversion ratios, invoice/payment-date drilldowns, CSV and print.
  Classification functions use the live report's exact junk/connected/appointment predicates.
  Receipt, appointment and payment cohorts stay separate; payment events retain later collections.
- Agent: all/single/multiple agents, snapshot, performance table, conversion funnel,
  branch summary/matrix, daily trend, source/enquired-for mix, paged invoice/appointment registers.
- Consultant: employee/manager grouping, appointment outcomes, linked invoice amounts,
  patient/plan consultant attribution, active staff and branch manager precedence,
  unmapped appointment retention, client dialogs and export.
- Optional Lead classification fields are added only when installed.

## Remaining exact-parity gaps

This comparison does **not** certify every legacy addon or pixel as migrated.
The following still need implementation and comparison with authenticated live records:

- Branch visit-number history (V1/V2) and branch-bill payment reconciliation per appointment.
- Agent incentive/KPI ranking rules and the complete three-business-month performance matrix.
- Campaign master status/date metadata and legacy campaign-specific detail/graph views.
- Consultant phone-based Patient fallback when `custom_lead` is missing; full historical
  manager team consolidation and three-month appointment averages.
- Legacy per-section print/share behavior and complete record-level drilldowns for all metrics.

## Validation

- Unit suite, marketing date/cohort/attribution rules, route mapping and report-request deduplication.
- Mocked browser check at 1440px and 390px: native entry, no iframe, separate routes,
  two startup reads, shared financial response, no legacy client get_list, no page overflow.
- Mocked Python test for scoped consultant lookup, active mapping, manager priority and
  retention of unresolved appointments. Python compilation and production build.

Browser requests were mocked. These checks do not constitute reconciliation against live
ERP totals or a guarantee of identical results for every legacy enrichment edge case.

## Separate sidebar entries

- **Branch Visit Report** opens `/ccvisit` with all six report tabs.
- **Agent 360** opens `/agent-360` with only the activity tab, its date filters,
  call history and timeline. It does not instantiate the branch report parent,
  calendar, or financial loader. The two activity entry points share a one-minute,
  login-scoped request cache; explicit refresh bypasses completed cached data.
- The activity response now includes ERP appointments, walk-ins and bookings,
  including owners who have appointments but no call events in the period.
- Rechecking Marketing found the Appointments KPI drilling into raw received leads;
  it now uses the appointment cohort.

The remaining exact-parity gaps listed above still apply. This sidebar separation
is not a claim that every legacy feature has been completed.
