# Legacy portal source review — 13 October 2026

Read the connected ERP Portal's complete Web Page inventory for modifications from 10 October 2026 00:00:00 through this review on 13 October (Asia/Kolkata). All 18 returned records were reviewed; the connector reported no additional results. Live ERP records were read only. Changes below update repository sources used by the legacy module frames in `/life_portal`, then rebuild `life_slimming/www/life_portal.html` and its assets.

## Production pages

| ERP Web Page | Live modified | Result |
|---|---|---|
| branch-visit-report | 2026-10-13 14:38:16.171296 | Imported updated report; `ccvisit` now follows the live Home mapping. Old `branch-visit-report-NEW-Bhuvan` links remain aliases. |
| unjoined-data | 2026-10-13 12:35:17.628630 | Imported and connected the existing Unjoined Clients menu entry. Includes its filters, follow-up register, detail forms, attachments, and export source. |
| life-portal-home | 2026-10-13 12:24:18.803477 | Reviewed routing/menu source. Connected Unjoined Clients and updated Stores 360 / CC Visit mappings. Kept the existing portal shell and customized lead dashboard mapping. |
| client-weight-loss-info | 2026-10-12 18:43:45.058975 | Imported HTML, CSS and JavaScript. Open Cards uses the January 2026 activity window and includes new slimming joiners. |
| branch-command-center | 2026-10-12 16:02:40.354073 | Already current. Retained local viewport-based loading and primary-ready event. |
| operations-service-module | 2026-10-11 12:11:24.371904 | Already current; differences are local removal of console calls. |
| stock-dashboard | 2026-10-11 01:27:24.689694 | Already current; differences are local removal of console calls. |
| stores-360 | 2026-10-10 07:11:16.228701 | Imported and mapped `stores360` to the live Home's production source. Old `stores-360-testing-2` links remain aliases. Existing Stores API and local receipt enhancements retained. |

Imported page JavaScript retains the portal's removal of console calls. Shared chrome handling hides duplicate branding for the new Stores and Unjoined sources while retaining their controls. Frontend/backend manifests match. Existing test sources remain in the repository for reference; active modules use the production mappings above.

## Other records in the four-day inventory

These published variants are not the Home's active destinations for their modules and were not substituted for production sources:

- stock-dashboard-testing-kavya — 2026-10-12 16:49:14.090774
- operations-service-module-bhuvan-11-oct — 2026-10-11 12:33:24.370826
- branch-command-center-bhuvan11oct26 — 2026-10-11 12:32:20.173063
- stock-ho-dashboard-test — 2026-10-11 12:05:49.249713
- stock-360-reports-bhuvan-t — 2026-10-11 00:19:13.001454
- billing-testing-kavya — 2026-10-10 18:13:34.043469

Unpublished backups excluded from active mappings:

- cc-visit-tab-backup-20261013143815873892
- cc-visit-v20261013-backup-20261013142945803345
- branch-command-center-before-stable-merge-20261012-160240-268943
- branch-command-center-backup-20261012-104153-698190

## Required APIs

The recent API Server Script inventory returned six records. The refreshed Visit Report requires `life_cc_agent_marketing_data`, whose production source changed on 13 October at 14:29:46.409469. Imported that body into its existing authenticated native endpoint and updated its catalogue source hash/revision. The new body uses bounded pagination, permission-aware reads, owner scoping, and an appointment view without financial joins.

Local adapters retained: the optional `custom_visit_status` field for native appointment consumers and the correct `len("lifescc")` offset for numeric agent logins. The live source's hardcoded `[6:]` offset misclassifies `lifescc13@gmail.com` when it owns no leads. Permission checks remain before detailed reads.

`life_stores_360_live_api` already matches the required live source revision, with local receipt/request enrichment retained. Unjoined Data uses existing permission-enforcing Frappe document APIs. The other recent script records were an inactive Visit backup, the billing-test cross-branch lookup, the two duplicate cryo batch sources, and Operations Session Dashboard; their existing migration decisions from the 12 October review remain unchanged.

## Validation and delivery

- 25 backend unit checks passed: source rendering, identical manifests, old-link aliases, API registration, owner scoping, permission denial, pagination and cross-cohort deduplication.
- Existing page performance, portal bridge and workspace loading JavaScript suites passed.
- JavaScript parsed for all 39 active legacy page sources.
- Production portal build passed and refreshed the HTML entry and local assets.
- `git diff --check` passed.

Business transactions and signed-in production browser workflows were not executed. Deploy Python, page JSON, HTML and generated assets together; refresh the running site's Python workers/cache using its normal deployment process. This review does not deploy or change live ERP records.
