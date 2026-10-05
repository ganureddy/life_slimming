# Portal retirement audit — 5 October 2026

**Approved for immediate deletion: none.** This is a named retirement-candidate inventory, not a deletion instruction. No live records were changed.

Live ERP inventory: 122 Web Pages and 371 Server Scripts, retrieved read-only with no further pages reported. Compared with 38 unique legacy routes in the local module manifest and 145 API catalogue entries.

- 37 Web Page records have matching migration timestamps and mapped app sources.
- 140 enabled API scripts have named local replacements and no metadata/alias/callback blocker found in this audit.
- 22 enabled API scripts are absent from the migration catalogue.
- 97 enabled non-API scripts must stay: 86 DocType Event, 9 Scheduler Event and 2 Permission Query scripts.
- 107 Server Scripts are already disabled; these need separate archival review.

Matching timestamps indicate migration inventory alignment, not proof of identical behavior, successful production deployment or absence of other callers. Local customizations intentionally differ from original source. Live traffic, external integration settings, all Client Scripts and current business workflows were not fully audited.

## Web Page candidates — only after redirect and workflow verification

Names below are **database Web Page record names**, not filenames. Keep the app source files. Back up the records, switch users/links to the replacement routes, configure old-route redirects, then unpublish and verify before deleting.

| Exact record name | Old route / API | Replacement |
|---|---|---|
| accounts-command-center | accounts-command-center | /life_portal/accounts |
| appointment-shedular | appointment-shedular | /life_portal/appt |
| approvals-report | approvals-report | /life_portal/approvals; /life_portal/approvalsreport |
| asset-master | asset-master | /life_portal/assets |
| audit | audit | /life_portal/audit |
| b2b-testing | b2b-testing | /life_portal/b2b |
| branch-command-center | branch-command-center | /life_portal/bdash |
| branch-expenditure-entry | branch-expenditure-entry | /life_portal/bexp |
| branch-home-target | branch-home-target | /life_portal/conv |
| cc-new-dashboard-bhuvan-oct2 | CC-New-Dashboard-Bhuvan-oct2 | /life_portal/leads |
| client-info | client-info | /life_portal/cliinfo |
| client-weight-loss-info | client-weight-loss-info | /life_portal/wlres |
| cluster-head-dashboard | cluster-head-dashboard | /life_portal/clusterhome |
| contols-command | contols-command | /life_portal/control |
| coo-dashboard | coo-dashboard | /life_portal/execdash |
| data-correction | data-correction | /life_portal/data-correction |
| employee-sale-master-data | employee-sale-master-data | /life_portal/empsale |
| enrollment-register-testing | enrollment-register-testing | /life_portal/enrollment-register |
| followup-master | followup-master | /life_portal/followup |
| glp-programme | glp-programme | /life_portal/riseprog |
| hrms-dashboard-copy | hrms-dashboard---copy | /life_portal/employees; /life_portal/attend; /life_portal/payroll |
| knowledge-centre | knowledge-centre | /life_portal/hrpol; /life_portal/knowledge |
| life-audit-report | life-audit-report | /life_portal/discountaudit |
| life-master-report | life-master-report | /life_portal/repmaster |
| md-dashboard | md-dashboard | /life_portal/mis |
| new-client-registration | new-client-registration | /life_portal/clireg |
| operations-service-module | operations-&-service-module | /life_portal/service |
| package-conversion-c2c | package-conversion-C2C | /life_portal/c2c |
| package-conversion-for-p2p | package-conversion-for-p2p | /life_portal/p2p |
| payables-planner | payables-planner | /life_portal/payables |
| pending-balances-updates | pending-balances-updates | /life_portal/pendbal; /life_portal/receivables |
| price-list | price-list | /life_portal/pricelist |
| sales-master-data | sales-master-data | /life_portal/salemaster |
| stock-dashboard | stock-dashboard | /life_portal/stock |
| stores-360-testing-2 | stores-360-testing-2 | /life_portal/stores360 |
| task-management | task-management | /life_portal/tasks |
| v | Documents | /life_portal/documents |

## Web Pages that must remain pending review

`call-center-new-report-bhuvan` (route `branch-visit-report-NEW-Bhuvan`) was modified at `2026-10-05 02:06:25.928460`; the migration manifest records `2026-10-03 20:32:21.018321`. Do not delete the live page before reviewing that newer revision. Timestamps here are the raw ERP metadata values.

All other pages absent from the candidate table remain unverified. That includes `life-portal-home`, standalone/test/backup pages, and the separately implemented `billing-v2`. A test/backup name is not evidence of non-use. See the full Web Page CSV for every name.

## API Server Script candidates — only after caller and workflow verification

The replacement column identifies Python methods, not Vue code. Deploy and test these methods, switch every old API caller, and verify document-save side effects before disabling originals. Keep all active non-API scripts below.

| Exact record name | Old route / API | Replacement |
|---|---|---|
| accounts_command_centre_coa | accounts_command_centre_coa | life_slimming.api.server_scripts.accounts_command_centre_coa.run |
| accounts_command_centre_data | accounts_command_centre_data | life_slimming.api.server_scripts.accounts_command_centre_data.run |
| accounts_command_centre_ledger | accounts_command_centre_ledger | life_slimming.api.server_scripts.accounts_command_centre_ledger.run |
| accounts_command_centre_post_entry | accounts_command_centre_post_entry | life_slimming.api.server_scripts.accounts_command_centre_post_entry.run |
| accounts_command_centre_procurement | accounts_command_centre_procurement | life_slimming.api.server_scripts.accounts_command_centre_procurement.run |
| accounts_command_centre_reconcile | accounts_command_centre_reconcile | life_slimming.api.server_scripts.accounts_command_centre_reconcile.run |
| all_approvals_report_data | all_approvals_report_data | life_slimming.api.server_scripts.all_approvals_report_data.run |
| api for expendtiure | expenditure_api | life_slimming.api.server_scripts.expenditure_api.run |
| apply_invoice_discount_NET_FINAL_V2 | apply_invoice_discount_NET_FINAL_V2 | life_slimming.api.server_scripts.apply_invoice_discount_net_final_v2.run |
| Approvals Report Conversion | life_approval_report_conversion_action | life_slimming.api.server_scripts.life_approval_report_conversion_action.run |
| Asset Master Complaint  Resolver Mail | life_asset_complaint | life_slimming.api.server_scripts.life_asset_complaint.run |
| block therapy session while conversion | therapy_plan_conversion_block_status | life_slimming.api.server_scripts.therapy_plan_conversion_block_status.run |
| Branch Audit Report For Master Report | life_audit_branch_access | life_slimming.api.server_scripts.life_audit_branch_access.run |
| Branch Audit Sending Mails Testing | life_audit_topic_approval | life_slimming.api.server_scripts.life_audit_topic_approval.run |
| Branch Expenditure Employees Name | life_get_expenditure_branch_employees | life_slimming.api.server_scripts.life_get_expenditure_branch_employees.run |
| BRANCH RECEIPT EMPLOYEE SEARCH | life_stock_receipt_employee_search | life_slimming.api.server_scripts.life_stock_receipt_employee_search.run |
| Branch Verification And Information Form | get_branch_verification_data | life_slimming.api.server_scripts.get_branch_verification_data.run |
| Branch visit report | life_cc_agent_marketing_data | life_slimming.api.server_scripts.life_cc_agent_marketing_data.run |
| branch_cluster_target_achievement_api | branch_cluster_target_achievement_api | life_slimming.api.server_scripts.branch_cluster_target_achievement_api.run |
| branch_command_center | branch_command_center | life_slimming.api.server_scripts.branch_command_center.run |
| Cancelling MR and Stock entries | life_stock_cancel_test_transactions | life_slimming.api.server_scripts.life_stock_cancel_test_transactions.run |
| Cancelling MR's | life_stock_finalize_test_material_requests | life_slimming.api.server_scripts.life_stock_finalize_test_material_requests.run |
| cc_add_lead_followup | cc_add_lead_followup | life_slimming.api.server_scripts.cc_add_lead_followup.run |
| cc_create_lead | cc_create_lead | life_slimming.api.server_scripts.cc_create_lead.run |
| cc_get_lead_history | cc_get_lead_history | life_slimming.api.server_scripts.cc_get_lead_history.run |
| cc_get_leads | cc_get_leads | life_slimming.api.server_scripts.cc_get_leads.run |
| cc_lead_owner_history | cc_lead_owner_history | life_slimming.api.server_scripts.cc_lead_owner_history.run |
| cc_set_visit_status | cc_set_visit_status | life_slimming.api.server_scripts.cc_set_visit_status.run |
| cc_walkin_details | cc_walkin_details | life_slimming.api.server_scripts.cc_walkin_details.run |
| cc_walkin_update | cc_walkin_update | life_slimming.api.server_scripts.cc_walkin_update.run |
| cc_walkins_range | cc_walkins_range | life_slimming.api.server_scripts.cc_walkins_range.run |
| cc_worksheet | cc_worksheet | life_slimming.api.server_scripts.cc_worksheet.run |
| CC-LEAD-New By Bhuvan | cc_phone_lookup | life_slimming.api.server_scripts.cc_phone_lookup.run |
| check_be_available | check_be_available | life_slimming.api.server_scripts.check_be_available.run |
| Client  Package Conversion Cloent To Client-Emails | send_client_conversion_step_email | life_slimming.api.server_scripts.send_client_conversion_step_email.run |
| Client Appointment status update | life_ops_update_appointment_status | life_slimming.api.server_scripts.life_ops_update_appointment_status.run |
| Client Package Conversion Client To Client | get_package_details | life_slimming.api.server_scripts.get_package_details.run |
| Client Package Conversion Same Client Package to Package | get_client_package_conversion_data | life_slimming.api.server_scripts.get_client_package_conversion_data.run |
| Client Refund Request Form | send_refund_step_email | life_slimming.api.server_scripts.send_refund_step_email.run |
| Client Request And Complaint Form-Auto Fetch And Emails | send_request_complaint_step_email | life_slimming.api.server_scripts.send_request_complaint_step_email.run |
| Client Stock Entries API V14 | client_stock_entries_api_v14 | life_slimming.api.server_scripts.client_stock_entries_api_v14.run |
| Client Transfer Request Form -Emalis | send_client_transfer_step_email | life_slimming.api.server_scripts.send_client_transfer_step_email.run |
| Client Transfer Request Form-Web Form Data Fetch | get_client_transfer_web_details | life_slimming.api.server_scripts.get_client_transfer_web_details.run |
| cluster_dashboard_api | cluster_dashboard_api | life_slimming.api.server_scripts.cluster_dashboard_api.run |
| create_multiple_discount_approval_requests_v2 | create_multiple_discount_approval_requests_v2 | life_slimming.api.server_scripts.create_multiple_discount_approval_requests_v2.run |
| Discount approval test new billing | create_discount_approval_request | life_slimming.api.server_scripts.create_discount_approval_request.run |
| dues_recovery_data | dues_recovery_data | life_slimming.api.server_scripts.dues_recovery_data.run |
| dues_recovery_save | dues_recovery_save | life_slimming.api.server_scripts.dues_recovery_save.run |
| ESSL Manual Sync Trigger | essl_manual_sync | life_slimming.api.server_scripts.essl_manual_sync.run |
| essl_biometric_checkin | essl_biometric_checkin | life_slimming.api.server_scripts.essl_biometric_checkin.run |
| feedback | life_rise.api.get_session_details | life_slimming.api.server_scripts.life_rise_api_get_session_details.run |
| fetch_branch_data | fetch_branch_data | life_slimming.api.server_scripts.fetch_branch_data.run |
| final approval test | apply_invoice_discount_NET_FINAL | life_slimming.api.server_scripts.apply_invoice_discount_net_final.run |
| Followup master diet english to telugu transfer | life_translate_telugu | life_slimming.api.server_scripts.life_translate_telugu.run |
| followup_master_api | followup_master_api | life_slimming.api.server_scripts.followup_master_api.run |
| Get Branch Employees | get_branch_employees | life_slimming.api.server_scripts.get_branch_employees.run |
| Get Current User's Branch | get_user_branch | life_slimming.api.server_scripts.get_user_branch.run |
| Get Expenditure History | get_expenditure_history | life_slimming.api.server_scripts.get_expenditure_history.run |
| get_branch_approvers | get_branch_approvers | life_slimming.api.server_scripts.get_branch_approvers.run |
| get_branch_consultants | get_branch_consultants | life_slimming.api.server_scripts.get_branch_consultants.run |
| get_collection_gst_data | get_collection_gst_data | life_slimming.api.server_scripts.get_collection_gst_data.run |
| get_media_sale_data | get_media_sale_data | life_slimming.api.server_scripts.get_media_sale_data.run |
| get_media_sale_testing | get_media_sale_testing | life_slimming.api.server_scripts.get_media_sale_testing.run |
| get_practitioners_by_branch | get_practitioners_by_branch | life_slimming.api.server_scripts.get_practitioners_by_branch.run |
| get_reference_referral_summary |  | life_slimming.api.server_scripts.get_reference_referral_summary.run |
| get_roster_employees | get_roster_employees | life_slimming.api.server_scripts.get_roster_employees.run |
| get_therapy_plans_for_patient | get_therapy_plans_for_patient | life_slimming.api.server_scripts.get_therapy_plans_for_patient.run |
| Lead Assignment Configuration API | lead_assignment_configuration | life_slimming.api.server_scripts.lead_assignment_configuration.run |
| Lead Assignment Preview API | lead_assignment_preview | life_slimming.api.server_scripts.lead_assignment_preview.run |
| lead_owner_names | lead_owner_names | life_slimming.api.server_scripts.lead_owner_names.run |
| LIFE Client 360 Branch Safe Patient Lookup | life_client360_branch_patient_lookup | life_slimming.api.server_scripts.life_client360_branch_patient_lookup.run |
| LIFE Client Package Conversion Same Client Package To Package | send_same_client_conversion_step_email | life_slimming.api.server_scripts.send_same_client_conversion_step_email.run |
| LIFE Client Record Book API | life_client_record_book_api | life_slimming.api.server_scripts.life_client_record_book_api.run |
| LIFE ConVox Click To Call API | life_convox_api | life_slimming.api.server_scripts.life_convox_api.run |
| LIFE ConVox Frontend API | life_convox_frontend | life_slimming.api.server_scripts.life_convox_frontend.run |
| LIFE Data Correction API | life_data_correction_api | life_slimming.api.server_scripts.life_data_correction_api.run |
| LIFE GLP Prepare Client | life_glp_prepare_client_v61 | life_slimming.api.server_scripts.life_glp_prepare_client_v61.run |
| LIFE Office Approval Action | life_office_approval_action | life_slimming.api.server_scripts.life_office_approval_action.run |
| LIFE WATI Daily Reports API | life_wati_daily_reports | life_slimming.api.server_scripts.life_wati_daily_reports.run |
| life_accounts_dashboard | life_accounts_dashboard | life_slimming.api.server_scripts.life_accounts_dashboard.run |
| life_branch_therapy_stock_transfer | life_branch_therapy_stock_transfer | life_slimming.api.server_scripts.life_branch_therapy_stock_transfer.run |
| life_discount_invoice_report | life_discount_invoice_report | life_slimming.api.server_scripts.life_discount_invoice_report.run |
| life_get_template_offer_price | life_get_template_offer_price | life_slimming.api.server_scripts.life_get_template_offer_price.run |
| life_hrms_360_api | life_hrms_360_api | life_slimming.api.server_scripts.life_hrms_360_api.run |
| life_stock_item_editor | life_stock_item_editor | life_slimming.api.server_scripts.life_stock_item_editor.run |
| life_stores_360_live_api | life_stores_360_live_api | life_slimming.api.server_scripts.life_stores_360_live_api.run |
| lifescc_hrms_dashboard | lifescc_hrms_dashboard | life_slimming.api.server_scripts.lifescc_hrms_dashboard.run |
| lifescc.billing.bootstrap | lifescc.billing.bootstrap | life_slimming.api.server_scripts.lifescc_billing_bootstrap.run |
| lifescc.billing.bootstrap_test | lifescc.billing.bootstrap_test | life_slimming.api.server_scripts.lifescc_billing_bootstrap_test.run |
| lifescc.billing.collect_payment | lifescc.billing.collect_payment | life_slimming.api.server_scripts.lifescc_billing_collect_payment.run |
| lifescc.billing.collect_payment_v4 | lifescc.billing.collect_payment_v4 | life_slimming.api.server_scripts.lifescc_billing_collect_payment_v4.run |
| lifescc.billing.collections_report | lifescc.billing.collections_report | life_slimming.api.server_scripts.lifescc_billing_collections_report.run |
| lifescc.billing.create_client | lifescc.billing.create_client | life_slimming.api.server_scripts.lifescc_billing_create_client.run |
| lifescc.billing.create_plan_and_invoice | lifescc.billing.create_plan_and_invoice | life_slimming.api.server_scripts.lifescc_billing_create_plan_and_invoice.run |
| lifescc.billing.create_plan_and_invoice_TEST | lifescc.billing.create_plan_and_invoice_TEST | life_slimming.api.server_scripts.lifescc_billing_create_plan_and_invoice_test.run |
| lifescc.billing.lead_lookup | lifescc.billing.lead_lookup | life_slimming.api.server_scripts.lifescc_billing_lead_lookup.run |
| lifescc.billing.submit_invoice | lifescc.billing.submit_invoice | life_slimming.api.server_scripts.lifescc_billing_submit_invoice.run |
| Machinary Transfer | get_store_warehouses_for_transfer | life_slimming.api.server_scripts.get_store_warehouses_for_transfer.run |
| Machinery Request and Transfer flow | life_get_machinery_transfers | life_slimming.api.server_scripts.life_get_machinery_transfers.run |
| Machinery Request Approvals | life_get_machinery_requests | life_slimming.api.server_scripts.life_get_machinery_requests.run |
| Machinery request create Permission | life_create_machinery_request | life_slimming.api.server_scripts.life_create_machinery_request.run |
| Machinery Request Source Warehouse | life_get_source_warehouses | life_slimming.api.server_scripts.life_get_source_warehouses.run |
| Machinery Transfer Availabillity | life_get_machinery_availability | life_slimming.api.server_scripts.life_get_machinery_availability.run |
| Machinery Trasfer | life_mark_machinery_transfer_ready | life_slimming.api.server_scripts.life_mark_machinery_transfer_ready.run |
| Machonery Request Assets | life_get_source_machinery_assets | life_slimming.api.server_scripts.life_get_source_machinery_assets.run |
| mask_mobile_on_export | mask_mobile_on_export | life_slimming.api.server_scripts.mask_mobile_on_export.run |
| md_360_api | md_360_api | life_slimming.api.server_scripts.md_360_api.run |
| md_accounts_api | md_accounts_api | life_slimming.api.server_scripts.md_accounts_api.run |
| md_approvals_api | md_approvals_api | life_slimming.api.server_scripts.md_approvals_api.run |
| md_audit_api | md_audit_api | life_slimming.api.server_scripts.md_audit_api.run |
| md_cash_api | md_cash_api | life_slimming.api.server_scripts.md_cash_api.run |
| md_client_api | md_client_api | life_slimming.api.server_scripts.md_client_api.run |
| md_command_center_api | md_command_center_api | life_slimming.api.server_scripts.md_command_center_api.run |
| md_create_po_draft | md_create_po_draft | life_slimming.api.server_scripts.md_create_po_draft.run |
| md_crm_api | md_crm_api | life_slimming.api.server_scripts.md_crm_api.run |
| md_dashboard_prefs | md_dashboard_prefs | life_slimming.api.server_scripts.md_dashboard_prefs.run |
| md_employee_sales_api | md_employee_sales_api | life_slimming.api.server_scripts.md_employee_sales_api.run |
| md_forecast_api | md_forecast_api | life_slimming.api.server_scripts.md_forecast_api.run |
| md_hr_api | md_hr_api | life_slimming.api.server_scripts.md_hr_api.run |
| md_indent_report_api | md_indent_report_api | life_slimming.api.server_scripts.md_indent_report_api.run |
| md_live_dashboard_api | md_live_dashboard_api | life_slimming.api.server_scripts.md_live_dashboard_api.run |
| md_my_approvals_api | md_my_approvals_api | life_slimming.api.server_scripts.md_my_approvals_api.run |
| md_stock_api | md_stock_api | life_slimming.api.server_scripts.md_stock_api.run |
| md_supplier_api | md_supplier_api | life_slimming.api.server_scripts.md_supplier_api.run |
| md_target_daily_api | md_target_daily_api | life_slimming.api.server_scripts.md_target_daily_api.run |
| md_vendor_ageing_api | md_vendor_ageing_api | life_slimming.api.server_scripts.md_vendor_ageing_api.run |
| Monthly indent access for branches | life_monthly_indent_access | life_slimming.api.server_scripts.life_monthly_indent_access.run |
| Operations & Service Module | life_room_ops_dashboard_get_data | life_slimming.api.server_scripts.life_room_ops_dashboard_get_data.run |
| Operations & Service Module Healthcare Practitioner Names | life_ops_branch_practitioners | life_slimming.api.server_scripts.life_ops_branch_practitioners.run |
| p2p run final automation | p2p_run_final_automation | life_slimming.api.server_scripts.p2p_run_final_automation.run |
| payables_planner_api | payables_planner_api | life_slimming.api.server_scripts.payables_planner_api.run |
| portal_is_system_manager | portal_is_system_manager | life_slimming.api.server_scripts.portal_is_system_manager.run |
| report_master_api | report_master_api | life_slimming.api.server_scripts.report_master_api.run |
| roster_employees | roster_employees | life_slimming.api.server_scripts.roster_employees.run |
| Stock dashboard | life_stock_fast_requests | life_slimming.api.server_scripts.life_stock_fast_requests.run |
| stock_indent_360_api | stock_indent_360_api | life_slimming.api.server_scripts.stock_indent_360_api.run |
| Submitting client Complaint api | create_client_request_complaint | life_slimming.api.server_scripts.create_client_request_complaint.run |
| Therapy Session Consent & After Photo | life_setup_therapy_session_media_fields | life_slimming.api.server_scripts.life_setup_therapy_session_media_fields.run |
| User check for Approvals Report | life_approval_report_user_context | life_slimming.api.server_scripts.life_approval_report_user_context.run |
| validate_coupon | validate_coupon | life_slimming.api.server_scripts.validate_coupon.run |

## Enabled API scripts to keep — unresolved migration blockers

- **ADVANCE BOOKING MATERIAL REQUEST** (`life_stock_submit_advance_request`): No named native replacement in the checked-in catalogue.
- **CC update lead Testing kavya** (`cc_update_lead`): No named native replacement in the checked-in catalogue.
- **cc_lead_contacts_form_test** (`cc_lead_contacts_form_test`): No named native replacement in the checked-in catalogue.
- **cc_update_lead** (`cc_update_lead`): Live modified timestamp differs from the migrated source revision. Multiple enabled live scripts share this API method; callers and alias resolution require review.
- **cc_update_lead_form_test** (`cc_update_lead_form_test`): No named native replacement in the checked-in catalogue.
- **create_po_from_indent360** (`create_po_from_indent360`): Multiple enabled live scripts share this API method; callers and alias resolution require review.
- **GLP Master Appointment Mark booked** (`life_glp_appointment_mark_done`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - apply_invoice_discount_NET_FINAL_V2** (`life_billing_pkgtest_apply_invoice_discount_NET_FINAL_V2`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - create_discount_approval_request** (`life_billing_pkgtest_create_discount_approval_request`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - create_multiple_discount_approval_requests_v2** (`life_billing_pkgtest_create_multiple_discount_approval_requests_v2`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - life_stock_fast_requests** (`life_billing_pkgtest_life_stock_fast_requests`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - lifescc.billing.bootstrap** (`life_billing_pkgtest_lifescc_billing_bootstrap`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - lifescc.billing.collect_payment_v4** (`life_billing_pkgtest_lifescc_billing_collect_payment_v4`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - lifescc.billing.collections_report** (`life_billing_pkgtest_lifescc_billing_collections_report`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - lifescc.billing.create_client** (`life_billing_pkgtest_lifescc_billing_create_client`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - lifescc.billing.create_plan_and_invoice_TEST** (`life_billing_pkgtest_lifescc_billing_create_plan_and_invoice_TEST`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - lifescc.billing.lead_lookup** (`life_billing_pkgtest_lifescc_billing_lead_lookup`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - lifescc.billing.submit_invoice** (`life_billing_pkgtest_lifescc_billing_submit_invoice`): No named native replacement in the checked-in catalogue.
- **LIFE Billing Package TEST - validate_coupon** (`life_billing_pkgtest_validate_coupon`): No named native replacement in the checked-in catalogue.
- **LIFE CC Agent Reports v2** (`life_cc_agent_report_v2`): No named native replacement in the checked-in catalogue.
- **LIFE CC Agent Reports v2 Setup** (`life_cc_agent_setup_v2`): No named native replacement in the checked-in catalogue.
- **LIFE CC Rebuild Audit v1** (`life_cc_rebuild_audit_v1`): No named native replacement in the checked-in catalogue.
- **LIFE ConVox Call Popup API** (`life_convox_call_popup`): Guest callback endpoint; external callback configuration must be switched and tested first.
- **LIFE ConVox Call Status API** (`life_convox_call_status`): Guest callback endpoint; external callback configuration must be switched and tested first.
- **LIFE DCR TEST API** (`life_dcr_test_api`): No named native replacement in the checked-in catalogue.
- **life_glp_appointment_safe_update** (`life_glp_appointment_safe_update`): No named native replacement in the checked-in catalogue.
- **Stores 360** (`create_po_from_indent360`): Multiple enabled live scripts share this API method; callers and alias resolution require review.

## Enabled event, scheduler and permission scripts to keep

### DocType Event

- After  Server script discount
- auto email for day target
- Auto Email For WekkTarget
- Auto Email Stock
- auto lead value and media value
- Automate Sessions Transfer Client to Client
- Branch Audit Percentage Change
- C2C list deletion
- Calculate Cost Breakdown
- CC v2 Immutable activity
- CC v2 KPI plan validation
- CC v2 Lead activity
- CC v2 Lead attribution
- CC v2 Protect activity deletion
- Client Feedback And Grievance
- Client Followup Naming Series
- Client Multi Branch Setup
- Client Transfer Request Form
- Client Transfer Request Form - Naming Series
- Complementy session
- Disocunt Aporval
- Dynamic status for approval of client to client PC
- Email For Materail Request
- Email for Purchase Order
- Email for Purchse inoive
- Eradicating name mandatory in Webform
- Existing Client Advance Material Request
- expesne account in pi
- files to public
- GLP Assessment Naming Series
- Glp Doses 4 Sessions
- Grievance Ticket Auto No
- HR Employee Onboarding Auto Fetch Into Employee
- Lead Auto Assignment (Weighted)
- Lead Status Updated Date
- lead_converted_appointment_sync
- lead_normalise_mobile
- LIFE Auto Due Date 30 Days
- LIFE Block Therapy Session if Not Invoiced
- LIFE Client Record Book Unique Validation
- LIFE Comp Sessions Push to Therapy Plan
- LIFE DCR TEST Audit Before Delete
- LIFE DCR TEST Audit Before Rename
- LIFE DCR TEST Audit Guard
- LIFE DCR TEST Request Before Delete
- LIFE DCR TEST Request Before Rename
- LIFE DCR TEST Request Guard
- LIFE DCR TEST Rule Before Delete
- LIFE DCR TEST Rule Before Rename
- LIFE DCR TEST Source Before Cancel
- LIFE DCR TEST Source Before Delete
- LIFE DCR TEST Source Before Rename
- LIFE DCR TEST Source Before Save
- LIFE DCR TEST Source Before Save (Submitted Document)
- LIFE Discount Cycle Tracker Update
- LIFE Fix Sales Invoice Due Date
- LIFE Lock Therapy Offer Pricing
- LIFE Recheck Therapy Plan Invoiced After Payment Cancel
- LIFE Reset Invoiced On SI Cancel
- LIFE Sync custom_therapy_plan from Reference ID
- LIFE Therapy Session Payment Validation
- LIFE Update Therapy Plan Invoiced After Payment Entry
- LIFE Update Therapy Plan Invoiced on Payment
- LIFESCC Consultation Form-BeforeSave
- Machinery Request Approval Validation
- MD LEADS AUTO ASSIGN
- Mobile Number Validation
- Notify L4 Discount Approver
- P2P Dynamic Status Before Save
- P2P Snapshot Before Therapy Update
- Patient Auto Link Lead on Save
- Permanent overlap suppression-Therpy session
- Sales invce after dsocint apporval
- Sales Invoice Auto Visited Booked
- Sales Invoice Block Submit Without Approval
- Send mails on task updates
- Stock Entry Receipt Confirmation Email
- Stock Entry Update Qty On Approval
- Sync Patient Decision to Lead
- Therapy Plan - Validate Sessions Limit
- Therapy Session - Validate Therapy Plan Invoiced
- Therapy Session Auto Consumable Stock Deduction
- Therapy Session Balance Amount
- Therapy Session Cancel Consumable Stock Reversal
- Therapy Session Timestamp Safe Save
- WhatsApp – Lead Appointment Booked Confirmation

### Scheduler Event

- Auto Expire Therapy Plans
- auto submit of stock entries after 24H
- CC v2 Daily metric refresh
- Daily Incentive Calculation
- ESSL Biometric Attendance Sync
- LIFE Previous Day Attendance Finalizer
- LIFE Submit Previous Day Draft Attendance
- LIFE WATI Attendance 1159
- LIFE WATI Doctor 2030

### Permission Query

- Access Team lead
- LIFE Stock Entry Target Warehouse Permission

## Full inventories

- [All 122 Web Pages](portal-retirement-web-pages-2026-10-05.csv)
- [All 371 Server Scripts](portal-retirement-server-scripts-2026-10-05.csv)

Never delete `life_slimming/portal_pages`, `life_slimming/api/server_scripts`, the Vue source, or the portal `www` entry files as part of database record retirement.
