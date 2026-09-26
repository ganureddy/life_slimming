# ERP Portal API catalogue

141 enabled Server Scripts migrated to native Python; disabled scripts are excluded.

Use **POST** `/api/method/<Python method>` with the Frappe session cookie and CSRF token.
The Vue client uses `dataApi(id, params)` from `src/api/index.js`.

Source conversion and import checks do not validate business results against production data.
Read `MIGRATION.md` for missing local schema and explicit behavior changes.

| API ID / file | Original API method | Guest | Notes |
|---|---|---|---|
| [accounts_command_centre_coa](server_scripts/accounts_command_centre_coa.py) | `accounts_command_centre_coa` | No |  |
| [accounts_command_centre_data](server_scripts/accounts_command_centre_data.py) | `accounts_command_centre_data` | No |  |
| [accounts_command_centre_ledger](server_scripts/accounts_command_centre_ledger.py) | `accounts_command_centre_ledger` | No |  |
| [accounts_command_centre_post_entry](server_scripts/accounts_command_centre_post_entry.py) | `accounts_command_centre_post_entry` | No |  |
| [accounts_command_centre_procurement](server_scripts/accounts_command_centre_procurement.py) | `accounts_command_centre_procurement` | No |  |
| [accounts_command_centre_reconcile](server_scripts/accounts_command_centre_reconcile.py) | `accounts_command_centre_reconcile` | No |  |
| [all_approvals_report_data](server_scripts/all_approvals_report_data.py) | `all_approvals_report_data` | No |  |
| [expenditure_api](server_scripts/expenditure_api.py) | `expenditure_api` | No |  |
| [apply_invoice_discount_net_final_v2](server_scripts/apply_invoice_discount_net_final_v2.py) | `apply_invoice_discount_NET_FINAL_V2` | No |  |
| [life_approval_report_conversion_action](server_scripts/life_approval_report_conversion_action.py) | `life_approval_report_conversion_action` | No |  |
| [life_asset_complaint](server_scripts/life_asset_complaint.py) | `life_asset_complaint` | No |  |
| [therapy_plan_conversion_block_status](server_scripts/therapy_plan_conversion_block_status.py) | `therapy_plan_conversion_block_status` | No |  |
| [life_audit_branch_access](server_scripts/life_audit_branch_access.py) | `life_audit_branch_access` | No |  |
| [life_audit_topic_approval](server_scripts/life_audit_topic_approval.py) | `life_audit_topic_approval` | No |  |
| [life_get_expenditure_branch_employees](server_scripts/life_get_expenditure_branch_employees.py) | `life_get_expenditure_branch_employees` | No |  |
| [get_branch_verification_data](server_scripts/get_branch_verification_data.py) | `get_branch_verification_data` | No | Function-only Server Script: the native entry now invokes get_branch_verification_data. |
| [life_cc_agent_marketing_data](server_scripts/life_cc_agent_marketing_data.py) | `life_cc_agent_marketing_data` | No |  |
| [branch_cluster_target_achievement_api](server_scripts/branch_cluster_target_achievement_api.py) | `branch_cluster_target_achievement_api` | No |  |
| [branch_command_center](server_scripts/branch_command_center.py) | `branch_command_center` | No |  |
| [life_stock_cancel_test_transactions](server_scripts/life_stock_cancel_test_transactions.py) | `life_stock_cancel_test_transactions` | No |  |
| [life_stock_finalize_test_material_requests](server_scripts/life_stock_finalize_test_material_requests.py) | `life_stock_finalize_test_material_requests` | No |  |
| [cc_add_lead_followup](server_scripts/cc_add_lead_followup.py) | `cc_add_lead_followup` | No |  |
| [cc_create_lead](server_scripts/cc_create_lead.py) | `cc_create_lead` | No |  |
| [cc_get_lead_history](server_scripts/cc_get_lead_history.py) | `cc_get_lead_history` | No |  |
| [cc_get_leads](server_scripts/cc_get_leads.py) | `cc_get_leads` | No |  |
| [cc_lead_owner_history](server_scripts/cc_lead_owner_history.py) | `cc_lead_owner_history` | No |  |
| [cc_set_visit_status](server_scripts/cc_set_visit_status.py) | `cc_set_visit_status` | No |  |
| [cc_update_lead](server_scripts/cc_update_lead.py) | `cc_update_lead` | No |  |
| [cc_walkin_details](server_scripts/cc_walkin_details.py) | `cc_walkin_details` | No |  |
| [cc_walkin_update](server_scripts/cc_walkin_update.py) | `cc_walkin_update` | No |  |
| [cc_walkins_range](server_scripts/cc_walkins_range.py) | `cc_walkins_range` | No |  |
| [cc_worksheet](server_scripts/cc_worksheet.py) | `cc_worksheet` | No |  |
| [check_be_available](server_scripts/check_be_available.py) | `check_be_available` | No |  |
| [send_client_conversion_step_email](server_scripts/send_client_conversion_step_email.py) | `send_client_conversion_step_email` | No |  |
| [life_ops_update_appointment_status](server_scripts/life_ops_update_appointment_status.py) | `life_ops_update_appointment_status` | No |  |
| [get_package_details](server_scripts/get_package_details.py) | `get_package_details` | No | Function-only Server Script: the native entry now invokes get_client_packages. |
| [get_client_package_conversion_data](server_scripts/get_client_package_conversion_data.py) | `get_client_package_conversion_data` | No | Function-only Server Script: the native entry now invokes client_package_conversion_data. |
| [send_refund_step_email](server_scripts/send_refund_step_email.py) | `send_refund_step_email` | No |  |
| [send_request_complaint_step_email](server_scripts/send_request_complaint_step_email.py) | `send_request_complaint_step_email` | No |  |
| [client_stock_entries_api_v14](server_scripts/client_stock_entries_api_v14.py) | `client_stock_entries_api_v14` | No |  |
| [send_client_transfer_step_email](server_scripts/send_client_transfer_step_email.py) | `send_client_transfer_step_email` | No |  |
| [get_client_transfer_web_details](server_scripts/get_client_transfer_web_details.py) | `get_client_transfer_web_details` | No | Patient-data endpoint now requires authentication and Patient read permission. |
| [cluster_dashboard_api](server_scripts/cluster_dashboard_api.py) | `cluster_dashboard_api` | No |  |
| [create_multiple_discount_approval_requests_v2](server_scripts/create_multiple_discount_approval_requests_v2.py) | `create_multiple_discount_approval_requests_v2` | No |  |
| [create_po_from_indent360__72bd3525](server_scripts/create_po_from_indent360__72bd3525.py) | `create_po_from_indent360` | No | Duplicate original API method: use this explicit local endpoint; no ambiguous alias. |
| [create_discount_approval_request](server_scripts/create_discount_approval_request.py) | `create_discount_approval_request` | No |  |
| [dues_recovery_data](server_scripts/dues_recovery_data.py) | `dues_recovery_data` | No |  |
| [dues_recovery_save](server_scripts/dues_recovery_save.py) | `dues_recovery_save` | No |  |
| [essl_manual_sync](server_scripts/essl_manual_sync.py) | `essl_manual_sync` | No |  |
| [essl_biometric_checkin](server_scripts/essl_biometric_checkin.py) | `essl_biometric_checkin` | No | Function-only Server Script: the native entry now invokes essl_biometric_checkin. |
| [life_rise_api_get_session_details](server_scripts/life_rise_api_get_session_details.py) | `life_rise.api.get_session_details` | No | Function-only Server Script: the native entry now invokes get_session_details. |
| [fetch_branch_data](server_scripts/fetch_branch_data.py) | `fetch_branch_data` | No |  |
| [apply_invoice_discount_net_final](server_scripts/apply_invoice_discount_net_final.py) | `apply_invoice_discount_NET_FINAL` | No |  |
| [life_translate_telugu](server_scripts/life_translate_telugu.py) | `life_translate_telugu` | No | Translation key is read from local site config: life_google_translate_api_key. |
| [followup_master_api](server_scripts/followup_master_api.py) | `followup_master_api` | No |  |
| [get_branch_employees](server_scripts/get_branch_employees.py) | `get_branch_employees` | No |  |
| [get_user_branch](server_scripts/get_user_branch.py) | `get_user_branch` | No |  |
| [get_expenditure_history](server_scripts/get_expenditure_history.py) | `get_expenditure_history` | No |  |
| [get_branch_approvers](server_scripts/get_branch_approvers.py) | `get_branch_approvers` | No |  |
| [get_branch_consultants](server_scripts/get_branch_consultants.py) | `get_branch_consultants` | No |  |
| [get_collection_gst_data](server_scripts/get_collection_gst_data.py) | `get_collection_gst_data` | No |  |
| [get_media_sale_data](server_scripts/get_media_sale_data.py) | `get_media_sale_data` | No |  |
| [get_media_sale_testing](server_scripts/get_media_sale_testing.py) | `get_media_sale_testing` | No |  |
| [get_practitioners_by_branch](server_scripts/get_practitioners_by_branch.py) | `get_practitioners_by_branch` | No |  |
| [get_reference_referral_summary](server_scripts/get_reference_referral_summary.py) | `(blank)` | No | Original API Method was blank; new local endpoint uses the script name. |
| [get_roster_employees](server_scripts/get_roster_employees.py) | `get_roster_employees` | No |  |
| [get_therapy_plans_for_patient](server_scripts/get_therapy_plans_for_patient.py) | `get_therapy_plans_for_patient` | No |  |
| [lead_assignment_configuration](server_scripts/lead_assignment_configuration.py) | `lead_assignment_configuration` | No |  |
| [lead_assignment_preview](server_scripts/lead_assignment_preview.py) | `lead_assignment_preview` | No |  |
| [lead_owner_names](server_scripts/lead_owner_names.py) | `lead_owner_names` | No |  |
| [send_same_client_conversion_step_email](server_scripts/send_same_client_conversion_step_email.py) | `send_same_client_conversion_step_email` | No |  |
| [life_convox_call_popup](server_scripts/life_convox_call_popup.py) | `life_convox_call_popup` | Token callback |  |
| [life_convox_call_status](server_scripts/life_convox_call_status.py) | `life_convox_call_status` | Token callback |  |
| [life_convox_api](server_scripts/life_convox_api.py) | `life_convox_api` | No |  |
| [life_convox_frontend](server_scripts/life_convox_frontend.py) | `life_convox_frontend` | No |  |
| [life_data_correction_api](server_scripts/life_data_correction_api.py) | `life_data_correction_api` | No |  |
| [life_glp_prepare_client_v61](server_scripts/life_glp_prepare_client_v61.py) | `life_glp_prepare_client_v61` | No |  |
| [life_office_approval_action](server_scripts/life_office_approval_action.py) | `life_office_approval_action` | No |  |
| [life_wati_daily_reports](server_scripts/life_wati_daily_reports.py) | `life_wati_daily_reports` | No |  |
| [life_accounts_dashboard](server_scripts/life_accounts_dashboard.py) | `life_accounts_dashboard` | No |  |
| [life_branch_therapy_stock_transfer](server_scripts/life_branch_therapy_stock_transfer.py) | `life_branch_therapy_stock_transfer` | No |  |
| [life_discount_invoice_report](server_scripts/life_discount_invoice_report.py) | `life_discount_invoice_report` | No |  |
| [life_get_template_offer_price](server_scripts/life_get_template_offer_price.py) | `life_get_template_offer_price` | No |  |
| [life_hrms_360_api](server_scripts/life_hrms_360_api.py) | `life_hrms_360_api` | No |  |
| [life_stock_item_editor](server_scripts/life_stock_item_editor.py) | `life_stock_item_editor` | No |  |
| [life_stores_360_live_api](server_scripts/life_stores_360_live_api.py) | `life_stores_360_live_api` | No |  |
| [lifescc_billing_bootstrap](server_scripts/lifescc_billing_bootstrap.py) | `lifescc.billing.bootstrap` | No |  |
| [lifescc_billing_bootstrap_test](server_scripts/lifescc_billing_bootstrap_test.py) | `lifescc.billing.bootstrap_test` | No |  |
| [lifescc_billing_collect_payment](server_scripts/lifescc_billing_collect_payment.py) | `lifescc.billing.collect_payment` | No |  |
| [lifescc_billing_collect_payment_v4](server_scripts/lifescc_billing_collect_payment_v4.py) | `lifescc.billing.collect_payment_v4` | No |  |
| [lifescc_billing_collections_report](server_scripts/lifescc_billing_collections_report.py) | `lifescc.billing.collections_report` | No |  |
| [lifescc_billing_create_client](server_scripts/lifescc_billing_create_client.py) | `lifescc.billing.create_client` | No |  |
| [lifescc_billing_create_plan_and_invoice](server_scripts/lifescc_billing_create_plan_and_invoice.py) | `lifescc.billing.create_plan_and_invoice` | No |  |
| [lifescc_billing_create_plan_and_invoice_test](server_scripts/lifescc_billing_create_plan_and_invoice_test.py) | `lifescc.billing.create_plan_and_invoice_TEST` | No |  |
| [lifescc_billing_lead_lookup](server_scripts/lifescc_billing_lead_lookup.py) | `lifescc.billing.lead_lookup` | No |  |
| [lifescc_billing_submit_invoice](server_scripts/lifescc_billing_submit_invoice.py) | `lifescc.billing.submit_invoice` | No |  |
| [lifescc_hrms_dashboard](server_scripts/lifescc_hrms_dashboard.py) | `lifescc_hrms_dashboard` | No |  |
| [get_store_warehouses_for_transfer](server_scripts/get_store_warehouses_for_transfer.py) | `get_store_warehouses_for_transfer` | No |  |
| [life_get_machinery_transfers](server_scripts/life_get_machinery_transfers.py) | `life_get_machinery_transfers` | No |  |
| [life_get_machinery_requests](server_scripts/life_get_machinery_requests.py) | `life_get_machinery_requests` | No |  |
| [life_create_machinery_request](server_scripts/life_create_machinery_request.py) | `life_create_machinery_request` | No |  |
| [life_get_source_warehouses](server_scripts/life_get_source_warehouses.py) | `life_get_source_warehouses` | No |  |
| [life_get_machinery_availability](server_scripts/life_get_machinery_availability.py) | `life_get_machinery_availability` | No |  |
| [life_mark_machinery_transfer_ready](server_scripts/life_mark_machinery_transfer_ready.py) | `life_mark_machinery_transfer_ready` | No |  |
| [life_get_source_machinery_assets](server_scripts/life_get_source_machinery_assets.py) | `life_get_source_machinery_assets` | No |  |
| [mask_mobile_on_export](server_scripts/mask_mobile_on_export.py) | `mask_mobile_on_export` | No |  |
| [md_360_api](server_scripts/md_360_api.py) | `md_360_api` | No |  |
| [md_accounts_api](server_scripts/md_accounts_api.py) | `md_accounts_api` | No |  |
| [md_approvals_api](server_scripts/md_approvals_api.py) | `md_approvals_api` | No |  |
| [md_audit_api](server_scripts/md_audit_api.py) | `md_audit_api` | No |  |
| [md_cash_api](server_scripts/md_cash_api.py) | `md_cash_api` | No |  |
| [md_client_api](server_scripts/md_client_api.py) | `md_client_api` | No |  |
| [md_command_center_api](server_scripts/md_command_center_api.py) | `md_command_center_api` | No |  |
| [md_create_po_draft](server_scripts/md_create_po_draft.py) | `md_create_po_draft` | No |  |
| [md_crm_api](server_scripts/md_crm_api.py) | `md_crm_api` | No |  |
| [md_dashboard_prefs](server_scripts/md_dashboard_prefs.py) | `md_dashboard_prefs` | No |  |
| [md_employee_sales_api](server_scripts/md_employee_sales_api.py) | `md_employee_sales_api` | No |  |
| [md_forecast_api](server_scripts/md_forecast_api.py) | `md_forecast_api` | No |  |
| [md_hr_api](server_scripts/md_hr_api.py) | `md_hr_api` | No |  |
| [md_indent_report_api](server_scripts/md_indent_report_api.py) | `md_indent_report_api` | No |  |
| [md_live_dashboard_api](server_scripts/md_live_dashboard_api.py) | `md_live_dashboard_api` | No |  |
| [md_my_approvals_api](server_scripts/md_my_approvals_api.py) | `md_my_approvals_api` | No |  |
| [md_stock_api](server_scripts/md_stock_api.py) | `md_stock_api` | No |  |
| [md_supplier_api](server_scripts/md_supplier_api.py) | `md_supplier_api` | No |  |
| [md_target_daily_api](server_scripts/md_target_daily_api.py) | `md_target_daily_api` | No |  |
| [md_vendor_ageing_api](server_scripts/md_vendor_ageing_api.py) | `md_vendor_ageing_api` | No |  |
| [life_monthly_indent_access](server_scripts/life_monthly_indent_access.py) | `life_monthly_indent_access` | No |  |
| [life_room_ops_dashboard_get_data](server_scripts/life_room_ops_dashboard_get_data.py) | `life_room_ops_dashboard_get_data` | No |  |
| [life_ops_branch_practitioners](server_scripts/life_ops_branch_practitioners.py) | `life_ops_branch_practitioners` | No |  |
| [p2p_run_final_automation](server_scripts/p2p_run_final_automation.py) | `p2p_run_final_automation` | No |  |
| [payables_planner_api](server_scripts/payables_planner_api.py) | `payables_planner_api` | No |  |
| [portal_is_system_manager](server_scripts/portal_is_system_manager.py) | `portal_is_system_manager` | No |  |
| [report_master_api](server_scripts/report_master_api.py) | `report_master_api` | No |  |
| [roster_employees](server_scripts/roster_employees.py) | `roster_employees` | No |  |
| [life_stock_fast_requests](server_scripts/life_stock_fast_requests.py) | `life_stock_fast_requests` | No |  |
| [stock_indent_360_api](server_scripts/stock_indent_360_api.py) | `stock_indent_360_api` | No |  |
| [create_po_from_indent360__0fdd830f](server_scripts/create_po_from_indent360__0fdd830f.py) | `create_po_from_indent360` | No | Duplicate original API method: use this explicit local endpoint; no ambiguous alias. |
| [create_client_request_complaint](server_scripts/create_client_request_complaint.py) | `create_client_request_complaint` | No |  |
| [life_setup_therapy_session_media_fields](server_scripts/life_setup_therapy_session_media_fields.py) | `life_setup_therapy_session_media_fields` | No |  |
| [life_approval_report_user_context](server_scripts/life_approval_report_user_context.py) | `life_approval_report_user_context` | No |  |
| [validate_coupon](server_scripts/validate_coupon.py) | `validate_coupon` | No |  |
