# Branch Visit Report visual pass — 12 November 2026

This pass addresses the report's unreadable inherited colors, inconsistent spacing,
and missing scorecard/comparison presentation. It does not change assignment rules
or claim that every historical ERP enrichment rule has been reconciled.

## Changes

- Added one report-scoped final theme for Branch Visits, Agent Report, Marketing,
  Consultant / Manager, Cluster, Activity, Journey and standalone Agent 360.
- Corrected legacy white text on pale Agent section headers, WebKit text-fill
  inheritance, gold calendar labels, helper text and scorecard badge labels.
- Read-only activity totals retain full opacity instead of fading as disabled controls.
- Unified Poppins, section/card spacing, form labels, table cell padding, dialogs,
  focus states, tab wrapping and mobile grids. Removed redundant heading rows.
- Restored the single-agent benchmark scorecard, team shares and per-metric ranks.
  The core-agent benchmark uses the reference's 10% lead/appointment threshold.
- Restored a three-business-month metric comparison using existing cached report
  reads, loaded only when requested, and added the daily trend chart.
- Print styles use dark text on white so removing background graphics does not
  turn header text white on white.

## Verification

`ccvisit-route.browser.cjs` now audits all seven report tabs at 1440px and 390px.
The browser reads computed text-fill colors and inherited solid/gradient surfaces;
normal text requires 4.5:1 contrast and large text 3:1 in the exercised states.
It also checks page overflow, the selected-agent scorecard, loaded three-month
comparison, history dialog and empty/error states. No contrast failures remained
in these checks. Screenshots were inspected for spacing and readable card/table layouts.

The same test retains the request assertions: no requests from hidden tabs,
shared completed responses on navigation, distinct appointment/calendar/financial
refresh payloads, lazy PD forms, and one read per requested comparison period.
Frontend unit tests cover the restored benchmark's cohort and outcome calculations.

Browser records are mocked. These are layout and request-behavior checks, not
live-data reconciliation or a certification of every possible color/image combination.
