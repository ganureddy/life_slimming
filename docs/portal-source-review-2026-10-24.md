# ERP legacy source refresh — 24 October 2026

Read the complete connected ERP Web Page inventory (132 records) and refreshed 18 production sources already represented in this repository. ERP records were read only. Test/mobile variants and backups were not substituted for production pages. Native Vue implementations were not changed.

## Imported sources

| Local source | ERP Web Page | ERP modified |
|---|---|---|
| appointment-shedular | appointment-shedular | 2026-10-21 03:15:36.579857 |
| approvals-report | approvals-report | 2026-10-23 00:30:09.456859 |
| billing-v2 | billing-v2 | 2026-10-24 12:26:37.149436 |
| branch-command-center | branch-command-center | 2026-10-23 18:40:55.584290 |
| branch-expenditure-entry | branch-expenditure-entry | 2026-10-24 16:14:16.959089 |
| client-info | client-info-live | 2026-10-24 17:02:56.013715 |
| cluster-head-dashboard | cluster-head-dashboard | 2026-10-23 18:31:37.395618 |
| employee-sale-master-data | employee-sale-master-data | 2026-10-24 16:24:34.872232 |
| enrollment-register-testing | enrollment-register-bhuvan | 2026-10-24 16:33:15.967483 |
| followup-master | followup-master | 2026-10-24 16:33:16.156792 |
| hrms-dashboard---copy | hrms-dashboard-copy | 2026-10-15 14:19:24.773126 |
| operations-service-module | operations-service-module | 2026-10-22 11:51:43.327578 |
| package-conversion-c2c | package-conversion-c2c | 2026-10-20 12:48:18.262540 |
| package-conversion-for-p2p | package-conversion-for-p2p | 2026-10-24 16:11:28.811429 |
| price-list | price-list | 2026-10-15 11:55:53.801642 |
| sales-master-data | sales-master-data | 2026-10-24 11:36:39.336128 |
| stock-dashboard | stock-dashboard | 2026-10-16 15:51:47.242574 |
| task-management | task-management | 2026-10-23 18:31:49.975347 |

## Preserved integration behavior

- CC legacy dashboards, CC reports, and their manifest mappings were excluded. Their source checksums are unchanged.
- Backend/frontend manifests match. Enrollment Register follows the live Home destination `client-info-Enrollment`; the previous route remains an alias.
- Repository source identities remain stable so existing chrome adapters continue to apply, including renamed Client Info and HRMS documents.
- Retained Approvals parallel count requests, Branch Command Center viewport-deferred panels and primary-ready notification, and Price List primary-ready notification.
- Removed executable console calls/debugger statements from imported JavaScript and embedded scripts.
- The live Branch/Cluster layouts use the existing ERP API `life_branch_shared_layout`; Client Info statistics use `life_client360_dashboard_summary_v1`. Both Server Scripts were confirmed enabled in the connected ERP. Their backend implementations were not changed by this source refresh.

## Verification

- All 64 imported standalone/embedded JavaScript blocks parsed successfully.
- 14 backend page, workspace and source-cache tests passed.
- Frontend page-performance, portal-bridge, workspace-loading and API-configuration suites passed.
- Production portal build passed; generated HTML/assets refreshed.
- Signed-in browser business workflows were not exercised.

Local source refresh only; no ERP Web Page was overwritten.
