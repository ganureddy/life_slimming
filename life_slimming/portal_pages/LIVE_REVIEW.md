# Live frontend page review — 2026-10-04

Compared the portal module mappings with published ERP Web Pages. Imported seven sources. Existing local Convox, appointment, and approvals loading fixes are retained. The `cc-new-dash` source was not changed by this refresh.

| Module | Live page | Source modified | Result |
|---|---|---|---|
| stores360 | stores-360-testing-2 | 2026-09-30 12:03:15.847391 | Updated |
| tasks | task-management | 2026-08-17 17:25:34.069904 | Current; preserved |
| conv | branch-home-target | 2026-08-18 19:42:50.920730 | Current; preserved |
| empsale | employee-sale-master-data | 2026-09-04 18:48:09.850544 | Current; preserved |
| salemaster | sales-master-data | 2026-08-18 17:44:48.747400 | Current; preserved |
| audit | audit | 2026-08-18 14:40:04.103719 | Current; preserved |
| bexp | branch-expenditure-entry | 2026-09-26 19:24:56.495013 | Current; preserved |
| leads | cc-new-dashboard-bhuvan-oct2 | 2026-10-03 20:26:30.330893 | Updated |
| ccvisit | call-center-new-report-bhuvan | 2026-10-03 20:32:21.018321 | Updated |
| clireg | new-client-registration | 2026-08-18 14:09:50.126561 | Current; preserved |
| cliinfo | client-info | 2026-09-27 18:27:57.847460 | Current; preserved |
| wlres | client-weight-loss-info | 2026-08-18 17:13:36.399207 | Current; preserved |
| discountaudit | life-audit-report | 2026-09-28 14:58:06.576708 | Current; preserved |
| appt | appointment-shedular | 2026-08-14 13:58:57.003983 | Current; preserved |
| accounts | accounts-command-center | 2026-08-20 23:57:51.482100 | Current; preserved |
| pendbal | pending-balances-updates | 2026-09-18 00:15:57.994469 | Current; preserved |
| payables | payables-planner | 2026-08-18 19:30:14.767258 | Current; preserved |
| receivables | pending-balances-updates | 2026-09-18 00:15:57.994469 | Current; preserved |
| assets | asset-master | 2026-09-28 14:59:18.451262 | Current; preserved |
| pricelist | price-list | 2026-09-26 19:25:18.697344 | Current; preserved |
| stock | stock-dashboard | 2026-10-03 13:57:07.718180 | Updated |
| approvals | approvals-report | 2026-10-03 13:30:07.502255 | Updated |
| documents | v | 2026-09-26 19:47:59.831357 | Current; preserved |
| employees | hrms-dashboard---copy | 2026-09-13 15:54:09.292441 | Current; preserved |
| attend | hrms-dashboard---copy | 2026-09-13 15:54:09.292441 | Current; preserved |
| payroll | hrms-dashboard---copy | 2026-09-13 15:54:09.292441 | Current; preserved |
| repmaster | life-master-report | 2026-08-12 15:48:08.178415 | Current; preserved |
| approvalsreport | approvals-report | 2026-10-03 13:30:07.502255 | Updated |
| execdash | coo-dashboard | 2026-08-16 10:57:42.630222 | Current; preserved |
| mis | md-dashboard | 2026-09-26 19:25:40.788081 | Current; preserved |
| clusterhome | cluster-head-dashboard | 2026-08-27 12:45:10.817449 | Current; preserved |
| control | contols-command | 2026-08-01 13:15:17.290029 | Current; preserved |
| hrpol | knowledge-centre | 2026-09-26 19:26:44.171691 | Current; preserved |
| knowledge | knowledge-centre | 2026-09-26 19:26:44.171691 | Current; preserved |
| riseprog | glp-programme | 2026-09-01 12:13:05.827427 | Current; preserved |
| service | operations-service-module | 2026-09-29 18:07:42.673251 | Current; preserved |
| followup | followup-master | 2026-09-28 14:55:37.397921 | Current; preserved |
| p2p | package-conversion-for-p2p | 2026-10-03 13:20:43.795084 | Updated |
| c2c | package-conversion-c2c | 2026-09-26 19:37:52.493427 | Current; preserved |
| b2b | b2b-testing | 2026-10-02 11:17:27.377758 | Updated |
| bdash | branch-command-center | 2026-09-27 17:22:12.272446 | Current; preserved |
| enrollment-register | enrollment-register-testing | 2026-09-28 11:03:40.233081 | Current; preserved |

Other published test, backup, and standalone ERP pages are not frontend module mappings and were not substituted for existing modules. Live ERP records were read only; this refresh updates the repository frontend sources.
