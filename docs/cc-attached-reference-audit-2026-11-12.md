# Branch Visit Report audit against the supplied files

> Update: the subsequent [visual pass](cc-report-visual-check-2026-11-12.md) corrected report colors and spacing and restored the single-agent scorecard, three-month metric comparison and daily chart. The comparison below records the earlier audit state.

Checked on 12 November 2026. The supplied files are the reference, rather than
an assumption that the previous simplified Vue conversion was equivalent.

## Reference identity

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| HTML | 64,307 | `2be55891d8029d20f7ddf166ce8be31eb4db2967ec1a99c7f0210352d133318c` |
| JavaScript | 1,467,253 | `6d1dabe1e9bb479d827cb18b6e715493c76a2320e9884551fbc07124c61230b1` |
| CSS | 106,131 | `5ed8ac9d2d560b47150a607eb85c831b4298d5582a6d63890d7e68cd0bb2a225` |

## Tab/component comparison

| Tab | Current Vue implementation | Comparison result |
| --- | --- | --- |
| Branch Visits | CCBranchVisitsPage, CCBranchSummaryCards, CCVisitDetailsDialog | Schedule, filters, summary cards, V1/V2 history, branch bill details and PD forms are implemented. Restored missing PD forms/history in this audit. Complete legacy per-section layouts/graphs/printing are not certified as equivalent. |
| Agent Report | CCAgentPerformancePage, CCAgentPerformanceView, CCReportKpiRanking | Scope selection, snapshot, funnel, branch matrix, trend, source mix, registers and manual-input KPI ranking are present. Legacy individual scorecard and the complete retained three-month layout remain gaps. |
| Marketing | CCMarketingReportPage | KPI cohorts, agency/ad-set/category/campaign tables, master campaign metadata and drilldowns are present. Full legacy campaign graph/detail presentation and tab-local filter layout still differ. |
| Consultant / Manager | CCConsultantReportPage | Employee/manager modes, active mappings, Patient/plan fallback, historical averages, money summaries and client dialogs are present. Full legacy team/detail presentation and per-section sharing still need comparison with live records. |
| Cluster addon | CCClusterReportPage | Branch roll-up is present. Fixed the wrong Visited–Not Booked status comparison. This roll-up does not reproduce the complete legacy Area Manager/cluster ownership interface. |
| Agent 360 addon | CCActivityPage / CCAgent360Page | Activity table, ERP outcomes, history and timeline are present. Standalone sidebar entry shows only activity. Legacy visual timeline/heatmap presentation is not identical. |
| Lead Journey addon | CCJourneyPage / CCJourneyReport | Native core report renders funnel, agents, call mix, joined-client credit and move history. Complete visual parity is not certified. |

The ranking weights, low-volume conversion behavior and the fact that missing
manual KPI inputs remain unranked agree with `lifePremiumRanking` in the supplied JS.
Do not replace missing inputs with invented ERP targets.

## Live ERP Server Script checks (read-only)

| API method used by the reference | Live Server Script | Modified (as stored in ERP) | State |
| --- | --- | --- | --- |
| `life_cc_agent_marketing_data` | Branch visit report | 2026-10-13 14:29:46.409469 | Enabled |
| `life_cc_nofu_v1` | life_cc_nofu_v1 | 2026-11-06 14:36:39.666460 | Enabled |
| `life_cc_core` | life_cc_core | 2026-11-11 11:36:56.777265 | Enabled |
| `cc_walkin_details` | cc_walkin_details | 2026-09-13 11:53:14.048654 | Enabled |

Also inspected `life_cc_lead_report_v1` and `life_convox_history_read_v1`; both exist
and are enabled, but neither is an explicit method call in the supplied JavaScript.
They must not be counted as extra required page requests merely because their names exist.

The reference also reads Lead, Patient, Therapy Plan, Sales Invoice, Payment Entry,
Employee, Campaign, ConVox events, mobile call logs, User, Version and File through
Frappe generic client methods. The Vue implementation consolidates these reads in
native APIs and does not copy the legacy global frappe.call monkey-patch.

### Native API mapping

- Main data: `server_scripts.life_cc_agent_marketing_data.run`; calendar and bounded
  appointment views replace broad initial reads. Its original server business logic
  is retained with permission checks, consolidated cohort queries and native enrichments.
- No Follow-up: `server_scripts.life_cc_nofu_v1.run`; same live script logic with bounded paging.
- Journey: `cc_core.run`, action `report`; shared native ownership/payment rules apply.
- Activity/history: `cc_report_activity.run` and `cc_report_history.run`; lazy recording reads.
- Branch bills: `cc_report_bills.run`; bounded authorized Lead batches and per-Lead cache.
- PD forms/history: new `cc_report_walkin.run` checks report and Lead access, then reuses
  migrated `server_scripts.cc_walkin_details.run`. Optional metadata fields are checked
  before querying, avoiding another unknown-field failure.

No live Server Script was edited or installed, and no business mutation was executed.
This is a code/metadata comparison, not reconciliation of authenticated live ERP totals.

## Request findings and fixes

1. Re-entering the report forced fresh appointment and financial reads despite a
   valid session cache. Entry/back navigation now uses cache; explicit Apply bypasses it.
2. The calendar was destroyed when `applied` was cleared during refresh. Its new
   instance could reuse stale cached counts. Preserve it after first load, so Apply
   makes one explicit calendar refresh.
3. KeepAlive watchers require a visibility check. The browser regression primes
   Journey, Activity and Untouched, switches to Marketing and changes dates: hidden
   reports must start zero reads.
4. A report refresh has three **different** main payloads: appointment/history,
   calendar and shared financial/summary data. Three calls to one method with these
   distinct arguments are not duplicate requests. Visible booked rows may also need
   a bounded bill lookup; it is cached by Lead. PD forms are requested only on click.
5. Reopening the same PD form dialog reuses its result; the browser check expects
   zero startup PD reads and one read across two dialog opens.

## Validation and limits

- Frontend unit suite and focused Python report/history/attribution/access/visit tests.
- Mocked desktop/mobile browser assertions for separate routes/sidebar, cache reuse,
  distinct refresh payloads, lazy PD forms, no hidden-tab reads, and viewport containment.
- Production build and whitespace checks.

These checks demonstrate request behavior for the exercised flows. They do not
prove that every interaction is duplicate-free, that all legacy pixels match, or
that server latency is zero. Remaining visual/function gaps above are open work.
