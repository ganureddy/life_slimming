# ERP Web Page comparison — 23 October 2026

Compared 37 manifest-mapped source pages against connected ERP Web Page records. Comparison is saved HTML/CSS/JavaScript, not live workflow certification.

The installer mounts the same portal application at 37 existing Web Page URLs, preserving routes and publication settings. It includes twelve native Vue modules and source-backed modules, plus billing-v2. Shared assets remain lazy loaded. Private JSON backups are created before changes. Version checks stop the entire operation if any target has been edited since the audit.

**Excluded:** all CC legacy/dashboard/report documents, cc-new-dash, unrelated test and backup documents, and contols-command (the portal Control module has a different purpose). No legacy CC document or source file is written.

**Important:** eleven live ERP source documents have edits newer than the checked-in portal snapshots. Mounting the portal intentionally displays the portal implementation; it does not merge those newer ERP changes. Their existing code is retained in private backups. Review the rows marked Newer ERP before running the installer.

| ERP Web Page | Portal modules | Changed source fields | Newer ERP | Rendering |
| --- | --- | --- | --- | --- |
| accounts-command-center | accounts | html | No | Portal source frame |
| appointment-shedular | appt | javascript | Yes | Native Vue |
| approvals-report | approvals, approvalsreport | html, javascript | Yes | Portal source frame |
| asset-master | assets | javascript | No | Portal source frame |
| audit | audit | html | No | Portal source frame |
| b2b-testing | b2b | Identical | No | Portal source frame |
| branch-command-center | bdash | html, css, javascript | Yes | Portal source frame |
| branch-expenditure-entry | bexp | javascript | No | Portal source frame |
| branch-home-target | conv | javascript | No | Native Vue |
| client-info | cliinfo | html, css, javascript | Yes | Portal source frame |
| client-weight-loss-info | wlres | javascript | No | Native Vue |
| cluster-head-dashboard | clusterhome | javascript | No | Native Vue |
| contols-command | control | Identical | No | Excluded: distinct Control function |
| coo-dashboard | execdash | javascript | No | Portal source frame |
| data-correction | data-correction | html, css, javascript | No | Portal source frame |
| employee-sale-master-data | empsale | javascript | No | Native Vue |
| enrollment-register-testing | enrollment-register | javascript | No | Portal source frame |
| followup-master | followup | css, javascript | Yes | Portal source frame |
| glp-programme | riseprog | javascript | No | Portal source frame |
| hrms-dashboard-copy | employees, attend, payroll | html, css | Yes | Portal source frame |
| knowledge-centre | hrpol, knowledge | Identical | No | Portal source frame |
| life-audit-report | discountaudit | html | No | Native Vue |
| life-master-report | repmaster | javascript | No | Portal source frame |
| md-dashboard | mis | html, javascript | No | Portal source frame |
| new-client-registration | clireg | html | No | Native Vue |
| operations-service-module | service | html, css, javascript | Yes | Portal source frame |
| package-conversion-c2c | c2c | javascript | Yes | Portal source frame |
| package-conversion-for-p2p | p2p | javascript | Yes | Portal source frame |
| payables-planner | payables | Identical | No | Portal source frame |
| pending-balances-updates | pendbal, receivables | javascript | No | Portal source frame |
| price-list | pricelist | javascript | Yes | Native Vue |
| sales-master-data | salemaster | javascript | No | Native Vue |
| stock-dashboard | stock | html, javascript | Yes | Portal source frame |
| stores-360 | stores360 | javascript | No | Portal source frame |
| task-management | tasks | javascript | No | Native Vue |
| unjoined-data | unjoined | javascript | No | Native Vue |
| v | documents | javascript | No | Native Vue |

Validation: isolated production build succeeded. Browser launch was blocked by the local sandbox socket restriction; no live visual or business-write workflows were exercised. The connected ERP tools support reading pages, not updating them; run the installer in System Console to apply it.
