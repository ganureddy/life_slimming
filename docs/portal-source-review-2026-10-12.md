# Portal source review — 12 October 2026

Read-only ERP Portal inventory: 127 Web Pages and 380 Server Scripts. No live records were changed.

## Local page update

Branch Command Center now uses source revision `2026-10-12 16:02:40.354073`. Imported live HTML/CSS and JavaScript updates, preserving the local viewport-triggered roster/offers loading and primary-ready event. The live changes include bounded read requests, treating HTTP 401 as expired authentication without redirecting on every permission denial, and less frequent polling. Other mapped page revisions already match the live inventory.

## Server Script APIs

All 150 catalogue entries match the live modified timestamps and SHA-256 source hashes. This verifies source revision alignment, not production business behavior. No native API bodies were regenerated.

Duplicate enabled API methods (do not choose a replacement by name alone):

- `life_ops_submit_cryo_batch`: `Operations Service Module cryo multiple sessions executions`, `LIFE Submit Cryo Session Batch V1`
- `cc_update_lead`: `cc_update_lead`, `CC update lead Testing kavya`
- `create_po_from_indent360`: `Stores 360`, `create_po_from_indent360`

Enabled API records absent from the migration catalogue (25); presence here does not establish whether a separately implemented native API exists:

- `Enrollment resgister showing clients in other branch` — `life_family_cross_branch_lookup`
- `LIFE Submit Cryo Session Batch V1` — `life_ops_submit_cryo_batch`
- `LIFE CC Comparison Setup` — `life_cc_comparison_setup`
- `LIFE CC Comparison Reports` — `life_cc_comparison_reports`
- `LIFE CC Comparison Source` — `life_cc_comparison_source`
- `LIFE CC Rebuild Audit v1` — `life_cc_rebuild_audit_v1`
- `LIFE Billing Package TEST - lifescc.billing.collections_report` — `life_billing_pkgtest_lifescc_billing_collections_report`
- `LIFE Billing Package TEST - lifescc.billing.submit_invoice` — `life_billing_pkgtest_lifescc_billing_submit_invoice`
- `LIFE Billing Package TEST - lifescc.billing.lead_lookup` — `life_billing_pkgtest_lifescc_billing_lead_lookup`
- `LIFE Billing Package TEST - validate_coupon` — `life_billing_pkgtest_validate_coupon`
- `LIFE Billing Package TEST - create_discount_approval_request` — `life_billing_pkgtest_create_discount_approval_request`
- `LIFE Billing Package TEST - lifescc.billing.create_client` — `life_billing_pkgtest_lifescc_billing_create_client`
- `LIFE Billing Package TEST - lifescc.billing.collect_payment_v4` — `life_billing_pkgtest_lifescc_billing_collect_payment_v4`
- `LIFE Billing Package TEST - apply_invoice_discount_NET_FINAL_V2` — `life_billing_pkgtest_apply_invoice_discount_NET_FINAL_V2`
- `LIFE Billing Package TEST - create_multiple_discount_approval_requests_v2` — `life_billing_pkgtest_create_multiple_discount_approval_requests_v2`
- `LIFE Billing Package TEST - lifescc.billing.bootstrap` — `life_billing_pkgtest_lifescc_billing_bootstrap`
- `LIFE Billing Package TEST - lifescc.billing.create_plan_and_invoice_TEST` — `life_billing_pkgtest_lifescc_billing_create_plan_and_invoice_TEST`
- `LIFE Billing Package TEST - life_stock_fast_requests` — `life_billing_pkgtest_life_stock_fast_requests`
- `CC update lead Testing kavya` — `cc_update_lead`
- `cc_lead_contacts_form_test` — `cc_lead_contacts_form_test`
- `cc_update_lead_form_test` — `cc_update_lead_form_test`
- `ADVANCE BOOKING MATERIAL REQUEST` — `life_stock_submit_advance_request`
- `LIFE DCR TEST API` — `life_dcr_test_api`
- `life_glp_appointment_safe_update` — `life_glp_appointment_safe_update`
- `GLP Master Appointment Mark booked` — `life_glp_appointment_mark_done`

## Session policy

Verified enabled live users: `narendhar@lifescc.com` and `life@gmail.com`; no `narendhar@lifescc.cpm` record exists. User requested renewal while the app remains open. Shared server policy disables the portal idle timer for those accounts and enables authenticated heartbeats in Desk, website pages, and the portal. Frappe core expiry and explicit logout remain effective. No site-wide expiry setting was changed.

## Validation

JavaScript parsing, existing page performance tests, session policy and heartbeat tests, portal page/API regression tests, and production portal build are checked locally. Live browser/business workflows and deployment require the running target site.
