"""Stock dashboard

Original API: life_stock_fast_requests
Source modified: 2026-09-16 12:32:35.737020
See ../CATALOG.md for migration notes and validation limits.
"""

import json
import re

import frappe
from frappe.integrations.utils import make_post_request as _make_post_request
from frappe.utils.safe_exec import read_sql as _read_sql
from frappe.utils.safe_exec import call_whitelisted_function as _call_whitelisted
from life_slimming.api._runtime import script_endpoint


@script_endpoint(allow_guest=False)
def run(**kwargs):
    # # ============================================================================
    # # LIFE STOCK MANAGEMENT — COMPLETE MATERIAL REQUEST API
    # # Server Script Type : API
    # # API Method         : life_stock_fast_requests
    # # Allow Guest        : OFF
    # #
    # # One endpoint, selected by the `action` argument.
    # #
    # # Supported actions:
    # #   get_context
    # #   check_setup
    # #   list_requests              (default; backward compatible)
    # #   get_request
    # #   get_stock_availability
    # #   get_item_stock_availability
    # #   submit_request
    # #   approve_request
    # #   reject_request
    # #   release_stock
    # #   list_branch_receipts
    # #   confirm_branch_receipt
    # #   submit_receipt_adjustment
    # #   approve_receipt_adjustment
    # #   decide_receipt_adjustment
    # #   list_stock_reconciliations
    # #   get_stock_reconciliation
    # #   create_stock_reconciliation_request
    # #   apply_stock_reconciliation_workflow
    # #   invoke                     (permission-aware gateway for approved methods)
    # #   batch                      (up to 30 approved gateway calls)
    # #   upload_file                (multipart upload through this API method)
    # #   stock_intelligence         (cached core/trend data)
    # # ============================================================================

    # MR_DOCTYPE = "Material Request"
    # MR_ITEM_DOCTYPE = "Material Request Item"
    # SE_DOCTYPE = "Stock Entry"
    # SE_ITEM_DOCTYPE = "Stock Entry Detail"
    # FILE_DOCTYPE = "File"
    # RECEIPT_ADJUSTMENT_DOCTYPE = "LIFE Stock Receipt Adjustment Request"
    # RECEIPT_ADJUSTMENT_ITEM_DOCTYPE = "LIFE Stock Receipt Adjustment Item"
    # RECEIPT_ADJUSTMENT_PENDING = "Pending Stock Manager Approval"
    # RECEIPT_ADJUSTMENT_CORRECTION = "Correction Requested"
    # RECEIPT_ADJUSTMENT_APPROVED = "Approved"
    # RECEIPT_ADJUSTMENT_REJECTED = "Rejected"
    # RECEIPT_ADJUSTMENT_COMPLETED = "Adjustment Completed"

    # STOCK_RECONCILIATION_DOCTYPE = "Stock Reconciliation"
    # STOCK_RECONCILIATION_DRAFT = "Draft"
    # STOCK_RECONCILIATION_PENDING = "Pending Stock Manager Approval"
    # STOCK_RECONCILIATION_REJECTED = "Rejected"
    # STOCK_RECONCILIATION_APPROVED = "Approved"
    # STOCK_RECONCILIATION_CANCELLED = "Cancelled"

    # COMPANY_FALLBACK = "Life Slimming And Cosmetic Pvt Ltd"
    # MR_PENDING_STATE = "Pending Inventory"
    # MR_APPROVED_STATE = "Approved"
    # MR_REJECTED_STATE = "Rejected"
    # SE_PENDING_RECEIPT_STATE = "Pending Receipt (Sub WH)"

    # REQUEST_TYPE_SPECIAL = "Special Material Request"
    # REQUEST_TYPE_ADVANCE = "Advance Material Request"
    # REQUEST_TYPE_MONTHLY = "Monthly Indent Request"
    # ALLOWED_REQUEST_TYPES = [
    #     REQUEST_TYPE_SPECIAL,
    #     REQUEST_TYPE_ADVANCE,
    #     REQUEST_TYPE_MONTHLY
    # ]

    # HO_ROLES = ["System Manager", "Stock Manager"]
    # HO_USERS = [
    #     "administrator",
    #     "bhuvan@lifescc.com",
    #     "inventory@lifescc.com",
    #     "lokakavyareddy3@gmail.com",
    #     "narendhar@lifescc.com",
    #     "yaswanthkumaryy1234@gmail.com"
    # ]

    # REQUEST_ATTACHMENT_TABLE = "custom_treatment_card_attachments"
    # REQUEST_ATTACHMENT_LEGACY = "custom_attachments"
    # REQUEST_ATTACHMENT_CHILD = "Special Material Request Attachment"


    # def life_parse_json(value):
    #     if value is None or value == "":
    #         return {}
    #     if isinstance(value, dict):
    #         return value
    #     if isinstance(value, str):
    #         parsed = json.loads(value)
    #         if not isinstance(parsed, dict):
    #             frappe.throw("Payload must be a JSON object.")
    #         return parsed
    #     frappe.throw("Unsupported payload type.")


    # def life_payload():
    #     raw = frappe.form_dict.get("payload")
    #     if raw is None or raw == "":
    #         return {}
    #     return life_parse_json(raw)


    # def life_arg(payload, key, default_value=None):
    #     if isinstance(payload, dict) and payload.get(key) is not None:
    #         return payload.get(key)
    #     value = frappe.form_dict.get(key)
    #     if value is None:
    #         return default_value
    #     return value


    # def life_int(value, default_value=0):
    #     try:
    #         return frappe.utils.cint(value)
    #     except Exception:
    #         return default_value


    # def life_float(value, default_value=0):
    #     try:
    #         return frappe.utils.flt(value)
    #     except Exception:
    #         return default_value


    # def life_require_login():
    #     user = str(frappe.session.user or "").strip()
    #     if not user or user == "Guest":
    #         frappe.throw("Please log in to continue.", frappe.AuthenticationError)
    #     return user


    # def life_user_roles():
    #     user = life_require_login()
    #     rows = frappe.get_all(
    #         "Has Role",
    #         filters={"parent": user, "parenttype": "User"},
    #         fields=["role"],
    #         page_length=500
    #     )
    #     roles = []
    #     for row in rows:
    #         role = str(row.get("role") or "").strip()
    #         if role and role not in roles:
    #             roles.append(role)
    #     return roles


    # def life_is_ho_user():
    #     user = life_require_login().lower()
    #     if user in HO_USERS:
    #         return True
    #     roles = life_user_roles()
    #     for role in roles:
    #         if role in HO_ROLES:
    #             return True
    #     return False


    # def life_require_ho():
    #     if not life_is_ho_user():
    #         frappe.throw(
    #             "Only an authorised Stock Manager or System Manager can perform this action.",
    #             frappe.PermissionError
    #         )


    # def life_has_field(doctype, fieldname):
    #     return bool(frappe.get_meta(doctype).get_field(fieldname))


    # def life_set_if_field(doc, fieldname, value):
    #     if life_has_field(doc.doctype, fieldname):
    #         doc.set(fieldname, value)
    #         return True
    #     return False


    # def life_db_set_if_field(doctype, name, fieldname, value):
    #     if life_has_field(doctype, fieldname):
    #         frappe.db.set_value(
    #             doctype,
    #             name,
    #             fieldname,
    #             value,
    #             update_modified=False
    #         )
    #         return True
    #     return False


    # def life_current_employee():
    #     user = life_require_login()
    #     employee_meta = frappe.get_meta("Employee")
    #     fields = ["name", "employee_name", "status"]
    #     for fieldname in ["branch", "company", "designation", "user_id"]:
    #         if employee_meta.get_field(fieldname):
    #             fields.append(fieldname)

    #     filters = {"status": "Active"}
    #     if employee_meta.get_field("user_id"):
    #         filters["user_id"] = user
    #     else:
    #         return None

    #     rows = frappe.get_all(
    #         "Employee",
    #         filters=filters,
    #         fields=fields,
    #         order_by="modified desc",
    #         page_length=1
    #     )
    #     return rows[0] if rows else None


    # def life_normalize_key(value):
    #     text = str(value or "").strip().lower()
    #     result = ""
    #     for character in text:
    #         if character.isalnum():
    #             result = result + character
    #     return result


    # def life_branch_from_warehouse(warehouse):
    #     warehouse = str(warehouse or "").strip()
    #     if not warehouse:
    #         return ""

    #     if frappe.db.exists("Warehouse", warehouse):
    #         warehouse_meta = frappe.get_meta("Warehouse")
    #         for fieldname in ["branch", "custom_branch"]:
    #             if warehouse_meta.get_field(fieldname):
    #                 branch_value = frappe.db.get_value("Warehouse", warehouse, fieldname)
    #                 if branch_value:
    #                     return str(branch_value).strip()

    #     text = warehouse
    #     suffixes = [
    #         " - LSACPL",
    #         "- LSACPL",
    #         " Store Warehouse",
    #         " store warehouse",
    #         " Warehouse",
    #         " warehouse"
    #     ]
    #     for suffix in suffixes:
    #         if text.endswith(suffix):
    #             text = text[0:len(text) - len(suffix)].strip()
    #     return text


    # def life_warehouse_matches_branch(warehouse, branch):
    #     warehouse_key = life_normalize_key(warehouse)
    #     branch_key = life_normalize_key(branch)
    #     derived_key = life_normalize_key(life_branch_from_warehouse(warehouse))
    #     if not warehouse_key or not branch_key:
    #         return False
    #     return derived_key == branch_key or branch_key in warehouse_key


    # def life_allowed_branches():
    #     if life_is_ho_user():
    #         return []

    #     branches = []
    #     employee = life_current_employee()
    #     if employee and employee.get("branch"):
    #         branches.append(str(employee.get("branch")).strip())

    #     rows = frappe.get_all(
    #         "User Permission",
    #         filters={
    #             "user": frappe.session.user,
    #             "allow": "Branch"
    #         },
    #         fields=["for_value"],
    #         page_length=500
    #     )
    #     for row in rows:
    #         branch = str(row.get("for_value") or "").strip()
    #         if branch and branch not in branches:
    #             branches.append(branch)
    #     return branches


    # def life_allowed_request_warehouses():
    #     """
    #     Return the Warehouses that should be shown in LIFE request forms.

    #     This is an additive UI-context helper only:
    #     - Stock Manager / System Manager: all enabled leaf Warehouses.
    #     - Normal users: existing branch-derived Warehouses PLUS explicit
    #       Warehouse User Permissions.
    #     - Group Warehouse permissions include enabled leaf descendants unless
    #       hide_descendants is enabled.

    #     Existing submit/approval/receipt/reconciliation permission checks are
    #     intentionally not changed by this helper.
    #     """
    #     user = life_require_login()

    #     warehouse_rows = frappe.get_all(
    #         "Warehouse",
    #         fields=[
    #             "name",
    #             "warehouse_name",
    #             "company",
    #             "is_group",
    #             "disabled",
    #             "lft",
    #             "rgt"
    #         ],
    #         order_by="name asc",
    #         page_length=2000
    #     )

    #     active_leaf_rows = []
    #     warehouse_by_name = {}

    #     for row in warehouse_rows:
    #         warehouse_name = str(row.get("name") or "").strip()

    #         if warehouse_name:
    #             warehouse_by_name[warehouse_name] = row

    #         if life_int(row.get("is_group"), 0):
    #             continue

    #         if life_int(row.get("disabled"), 0):
    #             continue

    #         active_leaf_rows.append(row)

    #     # Existing HO rule is preserved: Stock Manager / System Manager already
    #     # bypass branch warehouse restriction in life_require_branch_warehouse().
    #     if life_is_ho_user():
    #         return [
    #             {
    #                 "name": row.get("name"),
    #                 "warehouse_name": row.get("warehouse_name"),
    #                 "company": row.get("company"),
    #                 "is_group": 0,
    #                 "disabled": 0
    #             }
    #             for row in active_leaf_rows
    #         ]

    #     allowed_names = []

    #     def add_allowed_name(warehouse_name):
    #         warehouse_name = str(warehouse_name or "").strip()
    #         if warehouse_name and warehouse_name not in allowed_names:
    #             allowed_names.append(warehouse_name)

    #     # Preserve existing branch-based availability as a fallback/base.
    #     for branch in life_allowed_branches():
    #         for row in active_leaf_rows:
    #             warehouse_name = str(row.get("name") or "").strip()

    #             if life_warehouse_matches_branch(
    #                 warehouse_name,
    #                 branch
    #             ):
    #                 add_allowed_name(warehouse_name)

    #     # Add explicit Warehouse User Permissions.
    #     permission_rows = frappe.get_all(
    #         "User Permission",
    #         filters={
    #             "user": user,
    #             "allow": "Warehouse"
    #         },
    #         fields=[
    #             "for_value",
    #             "hide_descendants"
    #         ],
    #         page_length=500
    #     )

    #     for permission in permission_rows:
    #         permitted_name = str(
    #             permission.get("for_value") or ""
    #         ).strip()

    #         if not permitted_name:
    #             continue

    #         permitted_row = warehouse_by_name.get(
    #             permitted_name
    #         )

    #         if not permitted_row:
    #             continue

    #         if not life_int(
    #             permitted_row.get("is_group"),
    #             0
    #         ):
    #             if not life_int(
    #                 permitted_row.get("disabled"),
    #                 0
    #             ):
    #                 add_allowed_name(
    #                     permitted_name
    #                 )
    #             continue

    #         if life_int(
    #             permission.get("hide_descendants"),
    #             0
    #         ):
    #             continue

    #         parent_lft = life_int(
    #             permitted_row.get("lft"),
    #             0
    #         )
    #         parent_rgt = life_int(
    #             permitted_row.get("rgt"),
    #             0
    #         )

    #         for row in active_leaf_rows:
    #             row_lft = life_int(
    #                 row.get("lft"),
    #                 0
    #             )
    #             row_rgt = life_int(
    #                 row.get("rgt"),
    #                 0
    #             )

    #             if (
    #                 row_lft > parent_lft and
    #                 row_rgt < parent_rgt
    #             ):
    #                 add_allowed_name(
    #                     row.get("name")
    #                 )

    #     allowed_map = {}

    #     for warehouse_name in allowed_names:
    #         allowed_map[warehouse_name] = True

    #     result = []

    #     for row in active_leaf_rows:
    #         warehouse_name = str(
    #             row.get("name") or ""
    #         ).strip()

    #         if not allowed_map.get(
    #             warehouse_name
    #         ):
    #             continue

    #         result.append({
    #             "name": row.get("name"),
    #             "warehouse_name": row.get("warehouse_name"),
    #             "company": row.get("company"),
    #             "is_group": 0,
    #             "disabled": 0
    #         })

    #     return result


    # def life_require_branch_warehouse(warehouse, label):
    #     life_require_login()
    #     if life_is_ho_user():
    #         return

    #     branches = life_allowed_branches()
    #     if not branches:
    #         frappe.throw(
    #             "No active Employee branch or Branch User Permission is available for this user.",
    #             frappe.PermissionError
    #         )

    #     allowed = False
    #     for branch in branches:
    #         if life_warehouse_matches_branch(warehouse, branch):
    #             allowed = True
    #             break

    #     if not allowed:
    #         frappe.throw(
    #             str(label or "Warehouse") + " " + str(warehouse) + " is not assigned to your branch.",
    #             frappe.PermissionError
    #         )


    # def life_validate_employee(employee_name, branch=""):
    #     employee_name = str(
    #         employee_name or ""
    #     ).strip()

    #     if not employee_name:
    #         frappe.throw(
    #             "Received By / Requesting Employee is required."
    #         )

    #     employee_meta = frappe.get_meta("Employee")

    #     fields = [
    #         "name",
    #         "employee_name",
    #         "status"
    #     ]

    #     for fieldname in [
    #         "branch",
    #         "company",
    #         "designation",
    #         "user_id"
    #     ]:
    #         if employee_meta.get_field(fieldname):
    #             fields.append(fieldname)

    #     rows = frappe.get_all(
    #         "Employee",
    #         filters={
    #             "name": employee_name,
    #             "status": "Active"
    #         },
    #         fields=fields,
    #         page_length=1
    #     )

    #     if not rows:
    #         frappe.throw(
    #             "The selected employee is not active or could not be found."
    #         )

    #     return rows[0]

    # def life_request_type(row):
    #     if isinstance(row, dict):
    #         value = row.get("custom_stock_request_type") or row.get("custom_request_type")
    #         notes = row.get("custom_additional_notes")
    #     else:
    #         value = row.get("custom_stock_request_type") or row.get("custom_request_type")
    #         notes = row.get("custom_additional_notes")

    #     value = str(value or "").strip()
    #     if value:
    #         return value

    #     notes = str(notes or "").lower()
    #     if "monthly indent" in notes:
    #         return REQUEST_TYPE_MONTHLY
    #     if "advance material" in notes or "expected client" in notes:
    #         return REQUEST_TYPE_ADVANCE
    #     return REQUEST_TYPE_SPECIAL


    # def life_status_text(value):
    #     return str(value or "").strip().lower()


    # def life_is_rejected(value):
    #     text = life_status_text(value)
    #     return "reject" in text or "cancel" in text or "stop" in text


    # def life_is_released(value):
    #     text = life_status_text(value)
    #     return (
    #         "release" in text or
    #         "deliver" in text or
    #         "transit" in text or
    #         "receive" in text or
    #         "complete" in text
    #     )


    # def life_is_approved(value):
    #     return "approv" in life_status_text(value)


    # def life_request_group(row):
    #     transfer_status = row.get("transfer_status") or ""
    #     workflow_state = row.get("workflow_state") or ""
    #     custom_status = row.get("custom_stock_request_status") or ""
    #     erp_status = row.get("status") or ""

    #     if life_is_released(transfer_status) or life_is_released(custom_status):
    #         return "released"
    #     if life_is_rejected(workflow_state) or life_is_rejected(custom_status) or life_is_rejected(erp_status):
    #         return "rejected"
    #     if life_is_approved(workflow_state) or life_is_approved(custom_status):
    #         return "approved"
    #     return "pending"


    # def life_transition_next_state(transition):
    #     if not transition:
    #         return ""
    #     return str(
    #         transition.get("next_state") or
    #         transition.get("next_workflow_state") or
    #         transition.get("workflow_state") or
    #         ""
    #     ).strip()


    # def life_apply_workflow_state(doc, target_state):
    #     target_state = str(target_state or "").strip()
    #     if not target_state:
    #         frappe.throw("Target workflow state is required.")

    #     doc.reload()
    #     current_state = str(doc.get("workflow_state") or "").strip()
    #     if current_state.lower() == target_state.lower():
    #         return doc

    #     transitions = life_gateway_workflow_get_transitions(doc) or []

    #     selected_action = ""
    #     available = []
    #     for transition in transitions:
    #         action_name = str(transition.get("action") or "").strip()
    #         next_state = life_transition_next_state(transition)
    #         if action_name:
    #             available.append(action_name + " -> " + next_state)
    #         if next_state.lower() == target_state.lower():
    #             selected_action = action_name
    #             break

    #     if not selected_action:
    #         frappe.throw(
    #             "No permitted workflow transition moves " +
    #             (current_state or "Draft") + " to " + target_state +
    #             ". Available transitions: " + (", ".join(available) or "None")
    #         )

    #     result = life_gateway_workflow_apply(
    #         doc,
    #         selected_action
    #     )

    #     updated_name = doc.name
    #     if isinstance(result, dict) and result.get("name"):
    #         updated_name = result.get("name")

    #     updated = frappe.get_doc(doc.doctype, updated_name)
    #     final_state = str(updated.get("workflow_state") or "").strip()
    #     if final_state.lower() != target_state.lower():
    #         frappe.throw(
    #             "Workflow action completed, but the document is in " +
    #             (final_state or "Blank") + " instead of " + target_state + "."
    #         )
    #     return updated


    # def life_apply_receipt_submit(stock_entry):
    #     stock_entry.reload()
    #     transitions = life_gateway_workflow_get_transitions(stock_entry) or []
    #     if not transitions:
    #         frappe.throw("No branch receipt workflow action is available.")

    #     state_docstatus = {}
    #     workflows = frappe.get_all(
    #         "Workflow",
    #         filters={"document_type": SE_DOCTYPE, "is_active": 1},
    #         fields=["name"],
    #         page_length=1
    #     )
    #     if workflows:
    #         workflow_doc = frappe.get_doc("Workflow", workflows[0].get("name"))
    #         for state_row in workflow_doc.get("states") or []:
    #             state_docstatus[str(state_row.get("state") or "")] = life_int(state_row.get("doc_status"), 0)

    #     preferred_words = ["approve", "receive", "receipt", "confirm"]
    #     selected_action = ""
    #     fallback_action = ""
    #     available = []

    #     for transition in transitions:
    #         action_name = str(transition.get("action") or "").strip()
    #         next_state = life_transition_next_state(transition)
    #         next_docstatus = life_int(state_docstatus.get(next_state), -1)
    #         if action_name:
    #             available.append(action_name)
    #         if next_docstatus == 1 and not fallback_action:
    #             fallback_action = action_name
    #         if next_docstatus == 1:
    #             action_lower = action_name.lower()
    #             for word in preferred_words:
    #                 if word in action_lower:
    #                     selected_action = action_name
    #                     break
    #         if selected_action:
    #             break

    #     if not selected_action:
    #         selected_action = fallback_action

    #     if not selected_action:
    #         frappe.throw(
    #             "No receipt workflow action submits the Stock Entry. Available actions: " +
    #             (", ".join(available) or "None")
    #         )

    #     result = life_gateway_workflow_apply(
    #         stock_entry,
    #         selected_action
    #     )

    #     updated_name = stock_entry.name
    #     if isinstance(result, dict) and result.get("name"):
    #         updated_name = result.get("name")

    #     submitted = frappe.get_doc(SE_DOCTYPE, updated_name)
    #     if life_int(submitted.docstatus, 0) != 1:
    #         frappe.throw(
    #             "The receipt workflow action " + selected_action +
    #             " did not submit the Stock Entry."
    #         )
    #     return submitted


    # def life_requester_name_map(requester_ids):
    #     name_map = {}
    #     clean_ids = []
    #     for value in requester_ids:
    #         key = str(value or "").strip()
    #         if key and key not in clean_ids:
    #             clean_ids.append(key)

    #     if not clean_ids:
    #         return name_map

    #     employee_meta = frappe.get_meta("Employee")
    #     employee_fields = ["name", "employee_name"]
    #     if employee_meta.get_field("user_id"):
    #         employee_fields.append("user_id")

    #     employees = frappe.get_all(
    #         "Employee",
    #         filters={"name": ["in", clean_ids]},
    #         fields=employee_fields,
    #         page_length=len(clean_ids)
    #     )
    #     for employee in employees:
    #         display = employee.get("employee_name") or employee.get("name")
    #         if employee.get("name"):
    #             name_map[employee.get("name")] = display
    #         if employee.get("user_id"):
    #             name_map[employee.get("user_id")] = display

    #     if employee_meta.get_field("user_id"):
    #         employees_by_user = frappe.get_all(
    #             "Employee",
    #             filters={"user_id": ["in", clean_ids]},
    #             fields=employee_fields,
    #             page_length=len(clean_ids)
    #         )
    #         for employee in employees_by_user:
    #             display = employee.get("employee_name") or employee.get("name")
    #             if employee.get("name"):
    #                 name_map[employee.get("name")] = display
    #             if employee.get("user_id"):
    #                 name_map[employee.get("user_id")] = display

    #     users = frappe.get_all(
    #         "User",
    #         filters={"name": ["in", clean_ids]},
    #         fields=["name", "full_name", "first_name", "last_name"],
    #         page_length=len(clean_ids)
    #     )
    #     for user in users:
    #         user_id = user.get("name")
    #         full_name = str(user.get("full_name") or "").strip()
    #         if not full_name:
    #             full_name = (
    #                 str(user.get("first_name") or "").strip() + " " +
    #                 str(user.get("last_name") or "").strip()
    #             ).strip()
    #         if user_id and full_name:
    #             name_map[user_id] = full_name

    #     return name_map


    # def life_parent_fields():
    #     meta = frappe.get_meta(MR_DOCTYPE)
    #     fields = ["name", "creation", "modified", "owner", "docstatus"]
    #     candidates = [
    #         "transaction_date", "schedule_date", "title", "status",
    #         "workflow_state", "transfer_status", "material_request_type",
    #         "custom_stock_request_type", "custom_request_type",
    #         "custom_stock_request_status", "custom_stock_entry_reference",
    #         "custom_store_manager_instructions", "custom_store_manager_remarks",
    #         "custom_client_name", "custom_therapy_id", "custom_priority",
    #         "custom_additional_notes", "custom_reasonjustification",
    #         "custom_material_request_by", "set_from_warehouse", "set_warehouse",
    #         "company", "per_ordered", "per_received"
    #     ]
    #     for fieldname in candidates:
    #         if meta.get_field(fieldname) and fieldname not in fields:
    #             fields.append(fieldname)
    #     return fields


    # def life_child_fields():
    #     meta = frappe.get_meta(MR_ITEM_DOCTYPE)
    #     fields = ["name", "parent", "idx"]
    #     candidates = [
    #         "item_code", "item_name", "description", "qty", "uom", "stock_uom",
    #         "conversion_factor", "warehouse", "from_warehouse", "schedule_date",
    #         "custom_approved_qty", "cost_center", "project",
    #         "custom_client_name", "custom_package_number"
    #     ]
    #     for fieldname in candidates:
    #         if meta.get_field(fieldname) and fieldname not in fields:
    #             fields.append(fieldname)
    #     return fields


    # def life_material_summary(items):
    #     parts = []
    #     for item in items or []:
    #         item_label = item.get("item_name") or item.get("item_code") or "Material"
    #         qty = life_float(item.get("qty"), 0)
    #         qty_text = str(qty)
    #         if qty_text.endswith(".0"):
    #             qty_text = qty_text[0:len(qty_text) - 2]
    #         parts.append(str(item_label) + " ×" + qty_text)
    #     return ", ".join(parts) if parts else "—"


    # def life_prepare_request_rows(permitted_names, selected_names):
    #     if not selected_names:
    #         return []

    #     parent_rows = frappe.get_all(
    #         MR_DOCTYPE,
    #         filters={"name": ["in", selected_names]},
    #         fields=life_parent_fields(),
    #         page_length=len(selected_names)
    #     )
    #     parent_map = {}
    #     for row in parent_rows:
    #         if row.get("name"):
    #             parent_map[row.get("name")] = row

    #     child_rows = frappe.get_all(
    #         MR_ITEM_DOCTYPE,
    #         filters={
    #             "parent": ["in", selected_names],
    #             "parenttype": MR_DOCTYPE
    #         },
    #         fields=life_child_fields(),
    #         order_by="parent asc, idx asc",
    #         page_length=10000
    #     )
    #     items_by_parent = {}
    #     for item in child_rows:
    #         parent_name = item.get("parent")
    #         if parent_name:
    #             if not items_by_parent.get(parent_name):
    #                 items_by_parent[parent_name] = []
    #             items_by_parent.get(parent_name).append(item)

    #     requester_ids = []
    #     for name in selected_names:
    #         row = parent_map.get(name)
    #         if row:
    #             requester_id = row.get("custom_material_request_by") or row.get("owner")
    #             requester_id = str(requester_id or "").strip()
    #             if requester_id and requester_id not in requester_ids:
    #                 requester_ids.append(requester_id)

    #     requester_map = life_requester_name_map(requester_ids)
    #     ordered_rows = []
    #     for request_name in selected_names:
    #         row = parent_map.get(request_name)
    #         if not row:
    #             continue
    #         items = items_by_parent.get(request_name) or []
    #         requester_id = str(
    #             row.get("custom_material_request_by") or row.get("owner") or ""
    #         ).strip()
    #         requester_display = requester_map.get(requester_id)
    #         if not requester_display:
    #             requester_display = requester_id.split("@")[0] if "@" in requester_id else requester_id

    #         row.update({
    #             "items": items,
    #             "_home_items": items,
    #             "_home_materials": life_material_summary(items),
    #             "_requested_by_name": requester_display or "—",
    #             "_homeHydrated": True,
    #             "branch": life_branch_from_warehouse(row.get("set_warehouse")),
    #             "_group": life_request_group(row)
    #         })
    #         ordered_rows.append(row)
    #     return ordered_rows


    # def life_action_get_context(payload):
    #     user = life_require_login()
    #     employee = life_current_employee()
    #     roles = life_user_roles()
    #     return {
    #         "ok": True,
    #         "user": user,
    #         "roles": roles,
    #         "is_ho": life_is_ho_user(),
    #         "employee": employee,
    #         "branch": employee.get("branch") if employee else "",
    #         "company": employee.get("company") if employee else "",
    #         "allowed_warehouses": life_allowed_request_warehouses()
    #     }


    # def life_action_check_setup(payload):
    #     life_require_login()
    #     required = {
    #         MR_DOCTYPE: [
    #             "custom_stock_request_type",
    #             "custom_stock_request_status",
    #             "custom_store_manager_approval_required",
    #             "custom_material_request_by"
    #         ],
    #         MR_ITEM_DOCTYPE: ["custom_approved_qty"],
    #         SE_DOCTYPE: [
    #             "custom_stock_release_remarks",
    #             "custom_sending_method",
    #             "custom_delivery_reference",
    #             "custom_stock_released_by",
    #             "custom_stock_release_date",
    #             "custom_delivery_challan_photo_1",
    #             "custom_delivery_challan_photo_2",
    #             "custom_delivery_challan_photo_3",
    #             "custom_received_by",
    #             "custom_received_date",
    #             "custom_branch_receipt_remarks"
    #         ],
    #         SE_ITEM_DOCTYPE: ["custom_received_qty"]
    #     }
    #     missing = {}
    #     for doctype in required:
    #         absent = []
    #         for fieldname in required.get(doctype):
    #             if not life_has_field(doctype, fieldname):
    #                 absent.append(fieldname)
    #         if absent:
    #             missing[doctype] = absent

    #     mr_workflows = frappe.get_all(
    #         "Workflow",
    #         filters={"document_type": MR_DOCTYPE, "is_active": 1},
    #         fields=["name"],
    #         page_length=1
    #     )
    #     se_workflows = frappe.get_all(
    #         "Workflow",
    #         filters={"document_type": SE_DOCTYPE, "is_active": 1},
    #         fields=["name"],
    #         page_length=1
    #     )

    #     approved_field = frappe.get_meta(MR_ITEM_DOCTYPE).get_field("custom_approved_qty")
    #     allow_on_submit = bool(approved_field and life_int(approved_field.allow_on_submit, 0) == 1)

    #     return {
    #         "ok": not bool(missing) and allow_on_submit,
    #         "missing_fields": missing,
    #         "approved_qty_allow_on_submit": allow_on_submit,
    #         "active_material_request_workflow": mr_workflows[0].get("name") if mr_workflows else "",
    #         "active_stock_entry_workflow": se_workflows[0].get("name") if se_workflows else ""
    #     }


    # def life_action_list_requests(payload):
    #     life_require_login()

    #     view = str(
    #         life_arg(payload, "view", "ho") or "ho"
    #     ).strip().lower()

    #     branch = str(
    #         life_arg(payload, "branch", "") or ""
    #     ).strip()

    #     group = str(
    #         life_arg(payload, "group", "") or ""
    #     ).strip().lower()

    #     page = max(
    #         1,
    #         life_int(
    #             life_arg(payload, "page", 1),
    #             1
    #         )
    #     )

    #     limit = life_int(
    #         life_arg(payload, "limit", 200),
    #         200
    #     )
    #     limit = min(500, max(1, limit))

    #     page_size_raw = life_arg(
    #         payload,
    #         "page_size",
    #         None
    #     )

    #     if page_size_raw is None or page_size_raw == "":
    #         page_size = limit
    #     else:
    #         page_size = min(
    #             200,
    #             max(
    #                 1,
    #                 life_int(page_size_raw, 10)
    #             )
    #         )

    #     filters = [["docstatus", "<", 2]]

    #     # ============================================================
    #     # BRANCH VIEW
    #     # ============================================================
    #     if view == "branch":
    #         if not branch:
    #             employee = life_current_employee()
    #             branch = str(
    #                 employee.get("branch") or ""
    #             ).strip() if employee else ""

    #         if not branch:
    #             frappe.throw(
    #                 "Branch could not be resolved for the logged-in user."
    #             )

    #         filters.append(
    #             [
    #                 "set_warehouse",
    #                 "like",
    #                 "%" + branch + "%"
    #             ]
    #         )

    #         # Branch users continue to respect normal ERPNext permissions.
    #         headers = frappe.get_list(
    #             MR_DOCTYPE,
    #             filters=filters,
    #             fields=["name"],
    #             order_by="modified desc",
    #             limit_start=0,
    #             limit_page_length=limit
    #         )

    #     # ============================================================
    #     # HO / STOCK MANAGER VIEW
    #     # ============================================================
    #     else:
    #         # Important security gate before bypassing branch permissions.
    #         life_require_ho()

    #         # HO / Stock Manager needs requests from every branch.
    #         headers = frappe.get_all(
    #             MR_DOCTYPE,
    #             filters=filters,
    #             fields=["name"],
    #             order_by="modified desc",
    #             limit_start=0,
    #             limit_page_length=limit
    #         )

    #     # ============================================================
    #     # COMMON PROCESSING FOR BOTH BRANCH AND HO
    #     # ============================================================
    #     permitted_names = []
    #     for header in headers:
    #         name = header.get("name")
    #         if name:
    #             permitted_names.append(name)

    #     if not permitted_names:
    #         return {
    #             "ok": True,
    #             "rows": [],
    #             "counts": {
    #                 "pending": 0,
    #                 "approved": 0,
    #                 "released": 0,
    #                 "rejected": 0
    #             },
    #             "total": 0,
    #             "total_pages": 1,
    #             "page": page,
    #             "page_size": page_size,
    #             "view": view,
    #             "branch": branch,
    #             "group": group or "all",
    #             "limit": limit
    #         }

    #     status_fields = [
    #         "name",
    #         "workflow_state",
    #         "status",
    #         "docstatus"
    #     ]

    #     parent_meta = frappe.get_meta(MR_DOCTYPE)
    #     for fieldname in [
    #         "transfer_status",
    #         "custom_stock_request_status"
    #     ]:
    #         if parent_meta.get_field(fieldname):
    #             status_fields.append(fieldname)

    #     status_rows = frappe.get_all(
    #         MR_DOCTYPE,
    #         filters={"name": ["in", permitted_names]},
    #         fields=status_fields,
    #         page_length=len(permitted_names)
    #     )

    #     status_map = {}
    #     counts = {
    #         "pending": 0,
    #         "approved": 0,
    #         "released": 0,
    #         "rejected": 0
    #     }

    #     for row in status_rows:
    #         row_group = life_request_group(row)
    #         row.update({"_group": row_group})
    #         status_map[row.get("name")] = row
    #         counts[row_group] = counts.get(row_group, 0) + 1

    #     selected_names = []
    #     for name in permitted_names:
    #         status_row = status_map.get(name)
    #         row_group = status_row.get("_group") if status_row else "pending"

    #         if group in ["pending", "approved", "released", "rejected"]:
    #             if row_group == group:
    #                 selected_names.append(name)
    #         else:
    #             selected_names.append(name)

    #     total = len(selected_names)
    #     start = (page - 1) * page_size
    #     page_names = selected_names[start:start + page_size]

    #     rows = life_prepare_request_rows(
    #         permitted_names,
    #         page_names
    #     )

    #     return {
    #         "ok": True,
    #         "rows": rows,
    #         "counts": counts,
    #         "total": total,
    #         "total_pages": max(
    #             1,
    #             int((total + page_size - 1) / page_size)
    #         ),
    #         "page": page,
    #         "page_size": page_size,
    #         "view": view,
    #         "branch": branch,
    #         "group": group or "all",
    #         "limit": limit
    #     }


    # def life_action_get_request(payload):
    #     life_require_login()
    #     request_name = str(
    #         life_arg(payload, "name", "") or
    #         life_arg(payload, "request_name", "") or
    #         life_arg(payload, "material_request", "") or
    #         ""
    #     ).strip()
    #     if not request_name:
    #         frappe.throw("Material Request name is required.")

    #     doc = frappe.get_doc(MR_DOCTYPE, request_name)
    #     doc.check_permission("read")
    #     rows = life_prepare_request_rows([request_name], [request_name])
    #     summary = rows[0] if rows else {}
    #     return {
    #         "ok": True,
    #         "request": doc.as_dict(),
    #         "summary": summary
    #     }


    # def life_action_get_stock_availability(payload):
    #     life_require_ho()
    #     request_name = str(
    #         life_arg(payload, "request_name", "") or
    #         life_arg(payload, "material_request", "") or
    #         ""
    #     ).strip()
    #     if not request_name:
    #         frappe.throw("Material Request name is required.")

    #     doc = frappe.get_doc(MR_DOCTYPE, request_name)
    #     doc.check_permission("read")
    #     item_codes = []
    #     for item in doc.get("items") or []:
    #         code = str(item.get("item_code") or "").strip()
    #         if code and code not in item_codes:
    #             item_codes.append(code)

    #     if not item_codes:
    #         return {
    #             "ok": True,
    #             "request_name": request_name,
    #             "target_warehouse": doc.get("set_warehouse"),
    #             "rows": []
    #         }

    #     bins = frappe.get_all(
    #         "Bin",
    #         filters={"item_code": ["in", item_codes]},
    #         fields=["item_code", "warehouse", "actual_qty", "reserved_qty", "projected_qty"],
    #         order_by="item_code asc, actual_qty desc",
    #         page_length=10000
    #     )
    #     rows = []
    #     for row in bins:
    #         if row.get("warehouse") == doc.get("set_warehouse"):
    #             continue
    #         actual_qty = life_float(row.get("actual_qty"), 0)
    #         reserved_qty = life_float(row.get("reserved_qty"), 0)
    #         rows.append({
    #             "item_code": row.get("item_code"),
    #             "warehouse": row.get("warehouse"),
    #             "actual_qty": actual_qty,
    #             "reserved_qty": reserved_qty,
    #             "available_qty": max(0, actual_qty - reserved_qty),
    #             "projected_qty": life_float(row.get("projected_qty"), 0)
    #         })

    #     return {
    #         "ok": True,
    #         "request_name": request_name,
    #         "target_warehouse": doc.get("set_warehouse"),
    #         "rows": rows
    #     }



    # def life_action_get_item_stock_availability(payload):
    #     life_require_login()

    #     item_code = str(
    #         life_arg(payload, "item_code", "") or
    #         life_arg(payload, "item", "") or
    #         ""
    #     ).strip()

    #     if not item_code:
    #         frappe.throw("Item Code is required.")

    #     company = str(
    #         life_arg(payload, "company", "") or
    #         COMPANY_FALLBACK
    #     ).strip()

    #     source_warehouse = str(
    #         life_arg(payload, "source_warehouse", "") or
    #         ""
    #     ).strip()

    #     target_warehouse = str(
    #         life_arg(payload, "target_warehouse", "") or
    #         ""
    #     ).strip()

    #     requested_branch = str(
    #         life_arg(payload, "branch", "") or
    #         ""
    #     ).strip()

    #     if life_is_ho_user():
    #         branch = requested_branch
    #     else:
    #         employee = life_current_employee()
    #         branch = str(
    #             employee.get("branch") if employee else ""
    #         ).strip()

    #     if not branch and target_warehouse:
    #         branch = life_branch_from_warehouse(target_warehouse)

    #     warehouse_rows = frappe.get_all(
    #         "Warehouse",
    #         filters={
    #             "company": company,
    #             "is_group": 0
    #         },
    #         fields=["name"],
    #         order_by="name asc",
    #         page_length=10000
    #     )

    #     warehouse_names = []
    #     for warehouse_row in warehouse_rows:
    #         warehouse_name = str(
    #             warehouse_row.get("name") or ""
    #         ).strip()

    #         if warehouse_name:
    #             warehouse_names.append(warehouse_name)

    #     bin_filters = {
    #         "item_code": item_code
    #     }

    #     if warehouse_names:
    #         bin_filters["warehouse"] = ["in", warehouse_names]

    #     bins = frappe.get_all(
    #         "Bin",
    #         filters=bin_filters,
    #         fields=[
    #             "item_code",
    #             "warehouse",
    #             "actual_qty",
    #             "reserved_qty",
    #             "projected_qty",
    #             "ordered_qty",
    #             "planned_qty",
    #             "indented_qty"
    #         ],
    #         order_by="actual_qty desc, warehouse asc",
    #         page_length=10000
    #     )

    #     rows = []
    #     branch_qty = 0
    #     ho_qty = 0
    #     total_qty = 0
    #     total_available_qty = 0

    #     source_key = life_normalize_key(source_warehouse)

    #     for bin_row in bins:
    #         warehouse = str(
    #             bin_row.get("warehouse") or ""
    #         ).strip()

    #         if not warehouse:
    #             continue

    #         actual_qty = life_float(
    #             bin_row.get("actual_qty"),
    #             0
    #         )

    #         reserved_qty = life_float(
    #             bin_row.get("reserved_qty"),
    #             0
    #         )

    #         available_qty = actual_qty - reserved_qty
    #         projected_qty = life_float(
    #             bin_row.get("projected_qty"),
    #             available_qty
    #         )

    #         total_qty = total_qty + actual_qty
    #         total_available_qty = total_available_qty + available_qty

    #         is_branch_warehouse = False

    #         if target_warehouse and warehouse == target_warehouse:
    #             is_branch_warehouse = True
    #         elif branch and life_warehouse_matches_branch(
    #             warehouse,
    #             branch
    #         ):
    #             is_branch_warehouse = True

    #         warehouse_key = life_normalize_key(warehouse)
    #         is_ho_warehouse = False

    #         if source_key and warehouse_key == source_key:
    #             is_ho_warehouse = True
    #         elif (
    #             "stores" in warehouse_key or
    #             "headoffice" in warehouse_key or
    #             "central" in warehouse_key or
    #             warehouse_key.startswith("ho")
    #         ):
    #             is_ho_warehouse = True

    #         if is_branch_warehouse:
    #             branch_qty = branch_qty + actual_qty

    #         if is_ho_warehouse:
    #             ho_qty = ho_qty + actual_qty

    #         rows.append({
    #             "item_code": item_code,
    #             "warehouse": warehouse,
    #             "actual_qty": actual_qty,
    #             "reserved_qty": reserved_qty,
    #             "available_qty": available_qty,
    #             "projected_qty": projected_qty,
    #             "ordered_qty": life_float(
    #                 bin_row.get("ordered_qty"),
    #                 0
    #             ),
    #             "planned_qty": life_float(
    #                 bin_row.get("planned_qty"),
    #                 0
    #             ),
    #             "indented_qty": life_float(
    #                 bin_row.get("indented_qty"),
    #                 0
    #             ),
    #             "is_branch_warehouse": 1 if is_branch_warehouse else 0,
    #             "is_ho_warehouse": 1 if is_ho_warehouse else 0
    #         })

    #     return {
    #         "ok": True,
    #         "item_code": item_code,
    #         "company": company,
    #         "branch": branch,
    #         "source_warehouse": source_warehouse,
    #         "target_warehouse": target_warehouse,
    #         "branch_qty": branch_qty,
    #         "ho_qty": ho_qty,
    #         "total_qty": total_qty,
    #         "total_available_qty": total_available_qty,
    #         "rows": rows
    #     }


    # def life_normalize_attachments(value, maximum):
    #     if not value:
    #         return []
    #     if isinstance(value, str):
    #         value = json.loads(value)
    #     if not isinstance(value, list):
    #         frappe.throw("Attachments must be an array.")
    #     if len(value) > maximum:
    #         frappe.throw("A maximum of " + str(maximum) + " attachments is allowed.")

    #     rows = []
    #     index = 0
    #     for item in value:
    #         index = index + 1
    #         if isinstance(item, str):
    #             item = {"file_url": item}
    #         if not isinstance(item, dict):
    #             frappe.throw("Attachment " + str(index) + " is invalid.")
    #         file_url = str(
    #             item.get("file_url") or item.get("url") or item.get("attachment") or ""
    #         ).strip()
    #         if not file_url:
    #             frappe.throw("Attachment " + str(index) + " has no File URL.")
    #         rows.append({
    #             "file_url": file_url,
    #             "label": str(
    #                 item.get("label") or item.get("document_name") or
    #                 ("Attachment " + str(index))
    #             ).strip(),
    #             "slot_number": max(1, life_int(item.get("slot_number"), index))
    #         })
    #     return rows


    # def life_validate_file_access(file_url):
    #     """Validate that a file exists and is accessible to the current user."""

    #     if not file_url:
    #         return True

    #     file_url = str(file_url).strip()

    #     # Strategy 1: Exact file_url match
    #     try:
    #         file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
    #         if file_name:
    #             return True
    #     except Exception:
    #         pass

    #     # Strategy 2: Match by file_name (extract from URL)
    #     try:
    #         file_name_part = file_url.split("/")[-1].split("?")[0]
    #         file_name = frappe.db.get_value("File", {"file_name": file_name_part}, "name")
    #         if file_name:
    #             return True
    #     except Exception:
    #         pass

    #     # Strategy 3: Clean URL (remove /files/ prefix)
    #     try:
    #         clean_url = file_url.replace("/files/", "")
    #         file_name = frappe.db.get_value("File", {"file_url": clean_url}, "name")
    #         if file_name:
    #             return True
    #     except Exception:
    #         pass

    #     # Strategy 4: Search using LIKE with proper Frappe syntax
    #     try:
    #         file_name_part = file_url.split("/")[-1].split("?")[0]
    #         # Use the correct Frappe filter syntax for LIKE
    #         files = frappe.db.get_list(
    #             "File",
    #             filters={"file_url": ["like", f"%{file_name_part}%"]},
    #             fields=["name"],
    #             limit_page_length=1
    #         )
    #         if files and len(files) > 0:
    #             return True
    #     except Exception:
    #         pass

    #     # Strategy 5: Check if the file exists in the filesystem
    #     try:
    #         file_path = file_url
    #         if file_path.startswith("/files/"):
    #             file_path = file_path[7:]  # Remove "/files/"

    #         import os
    #         private_path = os.path.join(frappe.get_site_path("private", "files"), file_path)
    #         public_path = os.path.join(frappe.get_site_path("public", "files"), file_path)

    #         if os.path.exists(private_path) or os.path.exists(public_path):
    #             # File exists on disk, create a File record for it
    #             try:
    #                 new_file = frappe.get_doc({
    #                     "doctype": "File",
    #                     "file_url": file_url,
    #                     "file_name": file_url.split("/")[-1],
    #                 })
    #                 new_file.insert(ignore_permissions=True)
    #                 return True
    #             except Exception:
    #                 pass
    #             return True
    #     except Exception:
    #         pass

    #     # If all strategies fail, raise a clear error
    #     frappe.throw(
    #         f"Uploaded file was not found: {file_url}. Please ensure the file upload completed successfully and try again."
    #     )


    # def life_attach_request_files(request_name, attachments):
    #     """Attach files to a Material Request document."""

    #     if not attachments:
    #         return

    #     attached_count = 0

    #     for attachment in attachments:
    #         file_url = attachment.get("file_url")
    #         label = attachment.get("label", "Attachment")

    #         if not file_url:
    #             continue

    #         try:
    #             # Check if this file is already attached to this request
    #             existing = frappe.db.get_value(
    #                 "File",
    #                 {
    #                     "attached_to_doctype": "Material Request",
    #                     "attached_to_name": request_name,
    #                     "file_url": file_url
    #                 },
    #                 "name"
    #             )

    #             if existing:
    #                 # File already attached, skip
    #                 continue

    #             # First validate the file exists
    #             if not life_validate_file_access(file_url):
    #                 continue

    #             # Create the attachment record
    #             file_doc = frappe.get_doc({
    #                 "doctype": "File",
    #                 "file_url": file_url,
    #                 "attached_to_doctype": "Material Request",
    #                 "attached_to_name": request_name,
    #                 "attached_to_field": "custom_treatment_card_attachments",
    #                 "file_name": label or file_url.split("/")[-1]
    #             })
    #             file_doc.insert(ignore_permissions=True)
    #             attached_count += 1

    #         except Exception as e:
    #             # Log error with truncated message to avoid character length issues
    #             error_msg = str(e)[:100]  # Truncate to prevent Error Log length error
    #             frappe.log_error(
    #                 f"Failed to attach file to {request_name}: {error_msg}",
    #                 "LIFE Stock Attach Request Files"
    #             )
    #             # Continue with other files - don't fail the entire submission

    #     return attached_count

    # def life_validate_item_for_request(item, source, target, schedule_date):
    #     if not isinstance(item, dict):
    #         frappe.throw("A Material Request item row is invalid.")

    #     item_code = str(item.get("item_code") or "").strip()
    #     if not item_code:
    #         frappe.throw("Every Material Request row requires an Item Code.")

    #     item_rows = frappe.get_all(
    #         "Item",
    #         filters={"name": item_code},
    #         fields=["name", "item_code", "item_name", "item_group", "stock_uom", "disabled", "is_stock_item"],
    #         page_length=1
    #     )
    #     if not item_rows:
    #         frappe.throw("Item " + item_code + " does not exist.")
    #     item_master = item_rows[0]
    #     if life_int(item_master.get("disabled"), 0) == 1:
    #         frappe.throw("Item " + item_code + " is disabled.")
    #     if life_int(item_master.get("is_stock_item"), 0) != 1:
    #         frappe.throw("Item " + item_code + " is not a stock item.")

    #     group_text = str(item_master.get("item_group") or "").strip().lower()
    #     if group_text in ["asset", "assets", "service", "services"]:
    #         frappe.throw("Assets and Services cannot be requested as stock: " + item_code)

    #     qty = life_float(item.get("qty"), 0)
    #     if qty <= 0:
    #         frappe.throw("Requested quantity for " + item_code + " must be greater than zero.")

    #     row = {
    #         "item_code": item_code,
    #         "qty": qty,
    #         "schedule_date": item.get("schedule_date") or schedule_date,
    #         "from_warehouse": source,
    #         "warehouse": target
    #     }

    #     item_meta = frappe.get_meta(MR_ITEM_DOCTYPE)
    #     for fieldname in [
    #         "description", "cost_center", "project", "custom_client_name",
    #         "custom_package_number", "uom", "stock_uom", "conversion_factor"
    #     ]:
    #         if item_meta.get_field(fieldname) and item.get(fieldname) is not None:
    #             row[fieldname] = item.get(fieldname)
    #     return row


    # def life_action_submit_request(payload):
    #     life_require_login()
    #     request_doc = payload.get("request_doc") or payload.get("document") or payload
    #     if isinstance(request_doc, str):
    #         request_doc = json.loads(request_doc)
    #     if not isinstance(request_doc, dict):
    #         frappe.throw("request_doc must be a JSON object.")

    #     request_type = str(
    #         request_doc.get("custom_stock_request_type") or
    #         request_doc.get("custom_request_type") or ""
    #     ).strip()
    #     if request_type not in ALLOWED_REQUEST_TYPES:
    #         frappe.throw(
    #             "Request Type must be Special Material Request, Advance Material Request, or Monthly Indent Request."
    #         )

    #     attachments = life_normalize_attachments(payload.get("attachments") or [], 15)
    #     if request_type == REQUEST_TYPE_SPECIAL:
    #         present_slots = []
    #         for row in attachments:
    #             present_slots.append(life_int(row.get("slot_number"), 0))
    #         missing_slots = []
    #         for slot_number in [1, 2, 3]:
    #             if slot_number not in present_slots:
    #                 missing_slots.append(slot_number)
    #         if missing_slots:
    #             frappe.throw(
    #                 "Mandatory attachment slots are missing: " +
    #                 ", ".join([str(value) for value in missing_slots])
    #             )
    #         elif request_type == REQUEST_TYPE_ADVANCE:
    #             # Only slot 1 is mandatory for Advance Material Requests
    #             present_slots = []
    #             for row in attachments:
    #                 present_slots.append(life_int(row.get("slot_number"), 0))
    #             if 1 not in present_slots:
    #                 frappe.throw("Mandatory attachment slot 1 (Walk-In Form / Client Details) is missing.")

    #     if not life_has_field(MR_DOCTYPE, "custom_stock_request_type"):
    #         frappe.throw("Create Material Request.custom_stock_request_type first.")
    #     if not life_has_field(MR_DOCTYPE, "custom_stock_request_status"):
    #         frappe.throw("Create Material Request.custom_stock_request_status first.")
    #     if not life_has_field(MR_DOCTYPE, "custom_store_manager_approval_required"):
    #         frappe.throw("Create Material Request.custom_store_manager_approval_required first.")

    #     source = str(request_doc.get("set_from_warehouse") or "").strip()
    #     target = str(request_doc.get("set_warehouse") or "").strip()
    #     if not source or not target:
    #         frappe.throw("Source Warehouse and Target Warehouse are required.")
    #     if source == target:
    #         frappe.throw("Source Warehouse and Target Warehouse cannot be the same.")
    #     life_require_branch_warehouse(target, "Target Warehouse")

    #     transaction_date = request_doc.get("transaction_date") or frappe.utils.nowdate()
    #     schedule_date = request_doc.get("schedule_date")
    #     if not schedule_date:
    #         frappe.throw("Required By date is mandatory.")
    #     if frappe.utils.get_datetime(schedule_date) < frappe.utils.get_datetime(transaction_date):
    #         frappe.throw("Required By cannot be before Request Date.")

    #     items = request_doc.get("items") or []
    #     if not isinstance(items, list) or not items:
    #         frappe.throw("Add at least one stock item.")

    #     doc = frappe.new_doc(MR_DOCTYPE)
    #     parent_meta = frappe.get_meta(MR_DOCTYPE)
    #     parent_fields = [
    #         "naming_series", "title", "company", "custom_store_manager_instructions",
    #         "custom_requested_consumable_amount", "custom_coo_notification_required",
    #         "custom_coo_notification_status", "custom_client_name", "custom_therapy_id",
    #         "custom_material_request_by", "custom_total_billed", "custom_total_paid",
    #         "custom_outstanding_amount", "custom_priority", "custom_reasonjustification",
    #         "custom_additional_notes", "custom_expected_client_name",
    #         "custom_expected_client_phone", "custom_expected_joining_date",
    #         "custom_expected_treatment_category", "custom_expected_sessions",
    #         "custom_existing_life_client", "custom_previous_branch",
    #         "custom_recent_walkin_client", "custom_sales_cluster_head",
    #         "custom_cluster_head_approval_confirmed", "custom_stock_unavailable_declaration",
    #         "custom_records_maintenance_declaration", "custom_stock_responsibility_declaration",
    #         "custom_monthly_indent_confirmed", "custom_general_branch_consumption_confirmed"
    #     ]
    #     for fieldname in parent_fields:
    #         if parent_meta.get_field(fieldname) and request_doc.get(fieldname) is not None:
    #             doc.set(fieldname, request_doc.get(fieldname))

    #     doc.material_request_type = "Material Transfer"
    #     doc.transaction_date = transaction_date
    #     doc.schedule_date = schedule_date
    #     doc.company = request_doc.get("company") or COMPANY_FALLBACK
    #     doc.custom_stock_request_type = request_type
    #     doc.custom_stock_request_status = MR_PENDING_STATE
    #     doc.custom_store_manager_approval_required = 1
    #     doc.set_from_warehouse = source
    #     doc.set_warehouse = target

    #     if not doc.get("custom_material_request_by"):
    #         employee = life_current_employee()
    #         if employee and life_has_field(MR_DOCTYPE, "custom_material_request_by"):
    #             doc.custom_material_request_by = employee.get("name")

    #     if not doc.get("title"):
    #         doc.title = request_type + " - " + (life_branch_from_warehouse(target) or target)

    #     for item in items:
    #         doc.append(
    #             "items",
    #             life_validate_item_for_request(item, source, target, schedule_date)
    #         )

    #     therapy_field = "custom_special_material_request_details"
    #     therapy_details = request_doc.get(therapy_field) or request_doc.get("therapy_details") or []
    #     if therapy_details and parent_meta.get_field(therapy_field):
    #         if not isinstance(therapy_details, list):
    #             frappe.throw("Therapy Details must be an array.")
    #         child_doctype = str(parent_meta.get_field(therapy_field).options or "")
    #         child_meta = frappe.get_meta(child_doctype) if child_doctype else None
    #         for detail in therapy_details:
    #             if not isinstance(detail, dict):
    #                 frappe.throw("A Therapy Detail row is invalid.")
    #             row = {}
    #             for fieldname in [
    #                 "therapy_plan", "therapy_detail_row", "therapy_type", "sales_invoices",
    #                 "branch", "booked_sessions", "completed_sessions", "remaining_sessions"
    #             ]:
    #                 if child_meta and child_meta.get_field(fieldname) and detail.get(fieldname) is not None:
    #                     row[fieldname] = detail.get(fieldname)
    #             doc.append(therapy_field, row)

    #     doc.insert()
    #     if attachments:
    #         life_attach_request_files(doc, attachments)
    #         doc.reload()

    #     doc = life_apply_workflow_state(doc, MR_PENDING_STATE)
    #     rows = life_prepare_request_rows([doc.name], [doc.name])
    #     return {
    #         "ok": True,
    #         "message": "Material Request " + doc.name + " submitted for Store Manager review.",
    #         "request": rows[0] if rows else doc.as_dict()
    #     }


    # def life_find_request_item(items, approval):
    #     row_name = str(
    #         approval.get("item_row_name") or approval.get("row_name") or ""
    #     ).strip()
    #     item_code = str(approval.get("item_code") or "").strip()
    #     item_idx = life_int(approval.get("item_idx"), 0)

    #     if row_name:
    #         for item in items:
    #             if str(item.name or "") == row_name:
    #                 return item
    #     if item_idx:
    #         for item in items:
    #             if life_int(item.idx, 0) == item_idx:
    #                 if not item_code or str(item.item_code or "") == item_code:
    #                     return item
    #     if item_code:
    #         matches = []
    #         for item in items:
    #             if str(item.item_code or "") == item_code:
    #                 matches.append(item)
    #         if len(matches) == 1:
    #             return matches[0]
    #     return None


    # def life_bin_usable(item_code, warehouse):
    #     rows = frappe.get_all(
    #         "Bin",
    #         filters={"item_code": item_code, "warehouse": warehouse},
    #         fields=["actual_qty", "reserved_qty"],
    #         page_length=1
    #     )
    #     if not rows:
    #         return 0
    #     actual_qty = life_float(rows[0].get("actual_qty"), 0)
    #     reserved_qty = life_float(rows[0].get("reserved_qty"), 0)
    #     return max(0, actual_qty - reserved_qty)


    # def life_manager_remarks_field():
    #     for fieldname in [
    #         "custom_store_manager_remarks",
    #         "custom_store_manager_instructions",
    #         "custom_approval_remarks"
    #     ]:
    #         if life_has_field(MR_DOCTYPE, fieldname):
    #             return fieldname
    #     return ""


    # def life_validate_approval_rows(material_request, approvals):
    #     approved_field = frappe.get_meta(MR_ITEM_DOCTYPE).get_field("custom_approved_qty")
    #     if not approved_field:
    #         frappe.throw("Create Material Request Item.custom_approved_qty as a Float field.")
    #     if life_int(approved_field.allow_on_submit, 0) != 1:
    #         frappe.throw("Enable Allow on Submit for Material Request Item.custom_approved_qty.")

    #     items = list(material_request.get("items") or [])
    #     if not items:
    #         frappe.throw("No Material Request Item rows were found.")
    #     if not isinstance(approvals, list) or not approvals:
    #         frappe.throw("Approval quantities are required.")

    #     target = str(material_request.get("set_warehouse") or "").strip()
    #     if not target:
    #         frappe.throw("Target Warehouse is missing on the Material Request.")

    #     resolved = []
    #     demand = {}
    #     for approval in approvals:
    #         if not isinstance(approval, dict):
    #             frappe.throw("An Approval row is invalid.")
    #         item = life_find_request_item(items, approval)
    #         if not item:
    #             frappe.throw(
    #                 "Material Request Item was not found for " +
    #                 str(approval.get("item_code") or "a row") + "."
    #             )

    #         requested_qty = max(0, life_float(item.qty, 0))
    #         approved_qty = life_float(approval.get("approved_qty"), 0)
    #         if approved_qty < 0:
    #             frappe.throw("Approved Quantity cannot be negative for " + str(item.item_code) + ".")
    #         if approved_qty > requested_qty + 0.000001:
    #             frappe.throw(
    #                 "Approved Quantity " + str(approved_qty) +
    #                 " cannot exceed Requested Quantity " + str(requested_qty) +
    #                 " for " + str(item.item_code) + "."
    #             )

    #         source = str(approval.get("source_warehouse") or "").strip()
    #         conversion_factor = life_float(item.get("conversion_factor"), 1) or 1
    #         stock_qty = approved_qty * conversion_factor
    #         if approved_qty > 0:
    #             if not source:
    #                 frappe.throw("Select a Source Warehouse for " + str(item.item_code) + ".")
    #             if source == target:
    #                 frappe.throw(
    #                     "Source and Target Warehouse cannot be the same for " +
    #                     str(item.item_code) + "."
    #                 )
    #             key = str(item.item_code) + "||" + source
    #             demand[key] = life_float(demand.get(key), 0) + stock_qty

    #         resolved.append({
    #             "item": item,
    #             "item_code": item.item_code,
    #             "requested_qty": requested_qty,
    #             "approved_qty": approved_qty,
    #             "source_warehouse": source,
    #             "conversion_factor": conversion_factor,
    #             "stock_qty": stock_qty
    #         })

    #     positive = False
    #     for row in resolved:
    #         if row.get("approved_qty") > 0:
    #             positive = True
    #             break
    #     if not positive:
    #         frappe.throw("At least one item must have an Approved Quantity greater than zero.")

    #     errors = []
    #     for key in demand:
    #         parts = key.split("||", 1)
    #         item_code = parts[0]
    #         warehouse = parts[1]
    #         required_qty = life_float(demand.get(key), 0)
    #         usable = life_bin_usable(item_code, warehouse)
    #         if usable <= 0:
    #             errors.append(item_code + ": no usable stock is available in " + warehouse + ".")
    #         elif required_qty > usable + 0.000001:
    #             errors.append(
    #                 item_code + ": approved stock quantity " + str(required_qty) +
    #                 " exceeds usable stock " + str(usable) + " in " + warehouse + "."
    #             )

    #     if errors:
    #         frappe.throw("<br>".join(errors), title="Stock Availability Validation Failed")
    #     return resolved


    # def life_persist_approved_qty(material_request, resolved):
    #     if life_int(material_request.docstatus, 0) == 0:
    #         for row in resolved:
    #             row.get("item").custom_approved_qty = row.get("approved_qty")
    #         material_request.save()
    #     else:
    #         for row in resolved:
    #             frappe.db.set_value(
    #                 MR_ITEM_DOCTYPE,
    #                 row.get("item").name,
    #                 "custom_approved_qty",
    #                 row.get("approved_qty"),
    #                 update_modified=False
    #             )

    #     material_request.reload()
    #     for row in resolved:
    #         saved_item = None
    #         for item in material_request.get("items") or []:
    #             if str(item.name) == str(row.get("item").name):
    #                 saved_item = item
    #                 break
    #         if not saved_item:
    #             frappe.throw("Approved Quantity row was not saved for " + str(row.get("item_code")) + ".")
    #         if abs(life_float(saved_item.get("custom_approved_qty"), 0) - life_float(row.get("approved_qty"), 0)) > 0.000001:
    #             frappe.throw("Approved Quantity was not saved for " + str(row.get("item_code")) + ".")
    #     return material_request


    # def life_find_stock_entry(material_request, draft_only=False):
    #     reference = ""
    #     if life_has_field(MR_DOCTYPE, "custom_stock_entry_reference"):
    #         reference = str(material_request.get("custom_stock_entry_reference") or "").strip()
    #     if reference and frappe.db.exists(SE_DOCTYPE, reference):
    #         doc = frappe.get_doc(SE_DOCTYPE, reference)
    #         if not draft_only or life_int(doc.docstatus, 0) == 0:
    #             return doc

    #     rows = frappe.get_all(
    #         SE_ITEM_DOCTYPE,
    #         filters={
    #             "material_request": material_request.name,
    #             "parenttype": SE_DOCTYPE
    #         },
    #         fields=["parent"],
    #         page_length=500
    #     )
    #     parents = []
    #     for row in rows:
    #         parent = str(row.get("parent") or "").strip()
    #         if parent and parent not in parents:
    #             parents.append(parent)
    #     for parent in parents:
    #         doc = frappe.get_doc(SE_DOCTYPE, parent)
    #         if not draft_only or life_int(doc.docstatus, 0) == 0:
    #             return doc
    #     return None


    # def life_create_or_refresh_stock_entry(material_request, resolved):
    #     positive_rows = []
    #     for row in resolved:
    #         if life_float(row.get("approved_qty"), 0) > 0:
    #             positive_rows.append(row)
    #     if not positive_rows:
    #         frappe.throw("No approved item is available for Stock Entry creation.")

    #     stock_entry = life_find_stock_entry(material_request, True)
    #     if stock_entry and life_int(stock_entry.docstatus, 0) != 0:
    #         stock_entry = None

    #     if not stock_entry:
    #         stock_entry = frappe.new_doc(SE_DOCTYPE)
    #         stock_entry.stock_entry_type = "Material Transfer"
    #         stock_entry.purpose = "Material Transfer"
    #         stock_entry.company = material_request.get("company") or COMPANY_FALLBACK
    #         stock_entry.posting_date = frappe.utils.nowdate()
    #     else:
    #         stock_entry.check_permission("write")
    #         stock_entry.set("items", [])

    #     sources = []
    #     for row in positive_rows:
    #         source = str(row.get("source_warehouse") or "")
    #         if source and source not in sources:
    #             sources.append(source)

    #     stock_entry.from_warehouse = sources[0] if len(sources) == 1 else ""
    #     stock_entry.to_warehouse = material_request.get("set_warehouse")
    #     stock_entry.remarks = (
    #         "Draft Stock Entry created from approved Material Request " +
    #         material_request.name + ". Pending Stock Dispatch."
    #     )

    #     se_item_meta = frappe.get_meta(SE_ITEM_DOCTYPE)
    #     for row in positive_rows:
    #         item = row.get("item")
    #         values = {
    #             "item_code": item.item_code,
    #             "qty": row.get("approved_qty"),
    #             "uom": item.get("uom") or item.get("stock_uom"),
    #             "stock_uom": item.get("stock_uom") or item.get("uom"),
    #             "conversion_factor": row.get("conversion_factor") or 1,
    #             "s_warehouse": row.get("source_warehouse"),
    #             "t_warehouse": material_request.get("set_warehouse"),
    #             "material_request": material_request.name,
    #             "material_request_item": item.name
    #         }
    #         if se_item_meta.get_field("custom_received_qty"):
    #             values["custom_received_qty"] = 0
    #         for fieldname in ["cost_center", "custom_client_name", "custom_package_number"]:
    #             value = item.get(fieldname) or material_request.get(fieldname)
    #             if value and se_item_meta.get_field(fieldname):
    #                 values[fieldname] = value
    #         stock_entry.append("items", values)

    #     if stock_entry.is_new():
    #         stock_entry.insert()
    #     else:
    #         stock_entry.save()

    #     life_db_set_if_field(
    #         MR_DOCTYPE,
    #         material_request.name,
    #         "custom_stock_entry_reference",
    #         stock_entry.name
    #     )
    #     return stock_entry


    # def life_action_approve_request(payload):
    #     life_require_ho()
    #     request_name = str(
    #         payload.get("request_name") or payload.get("material_request") or ""
    #     ).strip()
    #     if not request_name:
    #         frappe.throw("Material Request name is required.")

    #     material_request = frappe.get_doc(MR_DOCTYPE, request_name)
    #     material_request.check_permission("read")
    #     if life_request_group(material_request) == "rejected":
    #         frappe.throw("Rejected requests cannot be approved.")

    #     approvals = payload.get("approvals") or []
    #     resolved = life_validate_approval_rows(material_request, approvals)
    #     remarks = str(payload.get("remarks") or "").strip()
    #     remarks_field = life_manager_remarks_field()
    #     if remarks and remarks_field:
    #         material_request.set(remarks_field, remarks)

    #     material_request = life_persist_approved_qty(material_request, resolved)
    #     current_state = str(material_request.get("workflow_state") or "").strip()
    #     if current_state.lower() != MR_APPROVED_STATE.lower():
    #         if life_int(material_request.docstatus, 0) == 0 and remarks and remarks_field:
    #             material_request.set(remarks_field, remarks)
    #             material_request.save()
    #         material_request = life_apply_workflow_state(material_request, MR_APPROVED_STATE)

    #     material_request = life_persist_approved_qty(material_request, resolved)
    #     stock_entry = life_create_or_refresh_stock_entry(material_request, resolved)
    #     life_db_set_if_field(
    #         MR_DOCTYPE,
    #         material_request.name,
    #         "custom_stock_request_status",
    #         MR_APPROVED_STATE
    #     )
    #     material_request.reload()

    #     rows = life_prepare_request_rows([material_request.name], [material_request.name])
    #     return {
    #         "ok": True,
    #         "message": (
    #             "Request " + material_request.name + " approved. Draft Stock Entry " +
    #             stock_entry.name + " is ready for release."
    #         ),
    #         "request": rows[0] if rows else material_request.as_dict(),
    #         "stock_entry": stock_entry.as_dict()
    #     }


    # def life_action_reject_request(payload):
    #     life_require_ho()
    #     request_name = str(
    #         payload.get("request_name") or payload.get("material_request") or ""
    #     ).strip()
    #     remarks = str(payload.get("remarks") or "").strip()
    #     if not request_name:
    #         frappe.throw("Material Request name is required.")
    #     if not remarks:
    #         frappe.throw("Store Manager Remarks are required before rejection.")

    #     material_request = frappe.get_doc(MR_DOCTYPE, request_name)
    #     material_request.check_permission("read")
    #     if life_request_group(material_request) == "approved":
    #         frappe.throw("An approved request cannot be rejected from this action.")

    #     remarks_field = life_manager_remarks_field()
    #     if remarks_field:
    #         material_request.set(remarks_field, remarks)
    #     if life_int(material_request.docstatus, 0) == 0:
    #         material_request.save()

    #     material_request = life_apply_workflow_state(material_request, MR_REJECTED_STATE)
    #     life_db_set_if_field(
    #         MR_DOCTYPE,
    #         material_request.name,
    #         "custom_stock_request_status",
    #         MR_REJECTED_STATE
    #     )
    #     material_request.reload()
    #     rows = life_prepare_request_rows([material_request.name], [material_request.name])
    #     return {
    #         "ok": True,
    #         "message": "Request " + material_request.name + " rejected.",
    #         "request": rows[0] if rows else material_request.as_dict()
    #     }


    # # def life_attach_urls_to_fields(doc, attachments, fieldnames):
    # #     rows = life_normalize_attachments(attachments, len(fieldnames))
    # #     urls = []
    # #     for row in rows:
    # #         file_url = row.get("file_url")
    # #         file_doc = life_validate_file_access(file_url)
    # #         file_doc.attached_to_doctype = doc.doctype
    # #         file_doc.attached_to_name = doc.name
    # #         file_doc.attached_to_field = ""
    # #         file_doc.save(ignore_permissions=True)
    # #         urls.append(file_url)

    # #     index = 0
    # #     for fieldname in fieldnames:
    # #         if not life_has_field(doc.doctype, fieldname):
    # #             frappe.throw("Required field " + doc.doctype + "." + fieldname + " is missing.")
    # #         doc.set(fieldname, urls[index] if index < len(urls) else "")
    # #         index = index + 1
    # #     return urls
    # def life_attach_urls_to_fields(doc, attachments, fieldnames):
    #     rows = life_normalize_attachments(attachments, len(fieldnames))
    #     urls = []

    #     for row in rows:
    #         file_url = row.get("file_url")

    #         if not file_url:
    #             continue

    #         # Validate that the current user is allowed to use this file.
    #         # This function returns True/False, not a File document.
    #         has_access = life_validate_file_access(file_url)

    #         if not has_access:
    #             frappe.throw("You do not have permission to use file: " + file_url)

    #         # Fetch the actual File document separately.
    #         file_name = frappe.db.get_value(
    #             "File",
    #             {"file_url": file_url},
    #             "name"
    #         )

    #         if not file_name:
    #             frappe.throw("File record was not found for: " + file_url)

    #         file_doc = frappe.get_doc("File", file_name)
    #         file_doc.attached_to_doctype = doc.doctype
    #         file_doc.attached_to_name = doc.name
    #         file_doc.attached_to_field = ""
    #         file_doc.save(ignore_permissions=True)

    #         urls.append(file_url)

    #     index = 0

    #     for fieldname in fieldnames:
    #         if not life_has_field(doc.doctype, fieldname):
    #             frappe.throw(
    #                 "Required field "
    #                 + doc.doctype
    #                 + "."
    #                 + fieldname
    #                 + " is missing."
    #             )

    #         if index < len(urls):
    #             doc.set(fieldname, urls[index])
    #         else:
    #             doc.set(fieldname, "")

    #         index = index + 1

    #     return urls


    # def life_action_release_stock(payload):
    #     life_require_ho()
    #     request_name = str(
    #         payload.get("request_name") or payload.get("material_request") or ""
    #     ).strip()
    #     delivery_method = str(payload.get("delivery_method") or "").strip()
    #     delivery_reference = str(payload.get("delivery_reference") or "").strip()
    #     release_remarks = str(payload.get("remarks") or payload.get("release_remarks") or "").strip()
    #     attachments = payload.get("attachments") or []

    #     if not request_name:
    #         frappe.throw("Material Request name is required.")
    #     if not delivery_method:
    #         frappe.throw("Sending Method is mandatory.")
    #     if not delivery_reference:
    #         frappe.throw("Delivery / Person / Tracking Reference is mandatory.")
    #     if not attachments:
    #         frappe.throw("Add at least one Delivery Challan image.")

    #     material_request = frappe.get_doc(MR_DOCTYPE, request_name)
    #     material_request.check_permission("read")
    #     if life_request_group(material_request) != "approved":
    #         frappe.throw("Only approved requests pending stock release can be released.")

    #     stock_entry = life_find_stock_entry(material_request, True)
    #     if not stock_entry:
    #         frappe.throw("No Draft Stock Entry is linked to this approved Material Request.")
    #     if life_int(stock_entry.docstatus, 0) != 0:
    #         frappe.throw("Stock Entry " + stock_entry.name + " is no longer a draft.")

    #     required_fields = [
    #         "custom_stock_release_remarks", "custom_sending_method",
    #         "custom_delivery_reference", "custom_stock_released_by",
    #         "custom_stock_release_date", "custom_delivery_challan_photo_1",
    #         "custom_delivery_challan_photo_2", "custom_delivery_challan_photo_3"
    #     ]
    #     missing = []
    #     for fieldname in required_fields:
    #         if not life_has_field(SE_DOCTYPE, fieldname):
    #             missing.append(fieldname)
    #     if missing:
    #         frappe.throw("Create these Stock Entry fields first: " + ", ".join(missing))

    #     life_attach_urls_to_fields(
    #         stock_entry,
    #         attachments,
    #         [
    #             "custom_delivery_challan_photo_1",
    #             "custom_delivery_challan_photo_2",
    #             "custom_delivery_challan_photo_3"
    #         ]
    #     )

    #     stock_entry.custom_stock_release_remarks = release_remarks
    #     stock_entry.custom_sending_method = delivery_method
    #     stock_entry.custom_delivery_reference = delivery_reference

    #     released_by = str(payload.get("released_by") or "").strip()
    #     if not released_by:
    #         employee = life_current_employee()
    #         released_by = str(employee.get("name") or "").strip() if employee else ""
    #     released_employee = life_validate_employee(released_by) if released_by else None

    #     stock_entry.custom_stock_released_by = released_employee.get("name") if released_employee else ""
    #     stock_entry.custom_stock_release_date = frappe.utils.now()
    #     remarks = [
    #         "Created from Material Request " + material_request.name,
    #         "Sending Method: " + delivery_method,
    #         "Person / Tracking Reference: " + delivery_reference
    #     ]
    #     if release_remarks:
    #         remarks.append("Store Manager Remarks: " + release_remarks)
    #     stock_entry.remarks = "\n".join(remarks)
    #     stock_entry.save()

    #     stock_entry = life_apply_workflow_state(stock_entry, SE_PENDING_RECEIPT_STATE)
    #     life_db_set_if_field(
    #         MR_DOCTYPE,
    #         material_request.name,
    #         "custom_stock_entry_reference",
    #         stock_entry.name
    #     )
    #     life_db_set_if_field(
    #         MR_DOCTYPE,
    #         material_request.name,
    #         "custom_stock_request_status",
    #         "Released"
    #     )
    #     life_db_set_if_field(
    #         MR_DOCTYPE,
    #         material_request.name,
    #         "transfer_status",
    #         "In Transit"
    #     )
    #     material_request.reload()
    #     rows = life_prepare_request_rows([material_request.name], [material_request.name])

    #     return {
    #         "ok": True,
    #         "message": (
    #             "Stock Entry " + stock_entry.name + " moved to " +
    #             SE_PENDING_RECEIPT_STATE + "."
    #         ),
    #         "request": rows[0] if rows else material_request.as_dict(),
    #         "stock_entry": stock_entry.as_dict()
    #     }


    # def life_stock_entry_targets_branch(stock_entry, branch):
    #     target = str(stock_entry.get("to_warehouse") or "").strip()
    #     if target and life_warehouse_matches_branch(target, branch):
    #         return True
    #     for item in stock_entry.get("items") or []:
    #         if life_warehouse_matches_branch(item.get("t_warehouse"), branch):
    #             return True
    #     return False


    # def life_stock_entry_row(stock_entry):
    #     items = []
    #     for item in stock_entry.get("items") or []:
    #         items.append({
    #             "name": item.name,
    #             "item_code": item.get("item_code"),
    #             "item_name": item.get("item_name"),
    #             "qty": life_float(item.get("qty"), 0),
    #             "transfer_qty": life_float(item.get("transfer_qty"), 0),
    #             "uom": item.get("uom"),
    #             "stock_uom": item.get("stock_uom"),
    #             "conversion_factor": life_float(item.get("conversion_factor"), 1) or 1,
    #             "s_warehouse": item.get("s_warehouse"),
    #             "t_warehouse": item.get("t_warehouse"),
    #             "material_request": item.get("material_request"),
    #             "material_request_item": item.get("material_request_item"),
    #             "custom_received_qty": item.get("custom_received_qty")
    #         })

    #     released_by_identifier = str(
    #         stock_entry.get("custom_stock_released_by") or
    #         stock_entry.get("custom_released_by") or
    #         stock_entry.get("released_by") or
    #         stock_entry.get("custom_released_by_employee") or
    #         stock_entry.get("owner") or
    #         stock_entry.get("modified_by") or
    #         ""
    #     ).strip()

    #     row = {
    #         "name": stock_entry.name,
    #         "owner": stock_entry.get("owner"),
    #         "modified_by": stock_entry.get("modified_by"),
    #         "creation": stock_entry.get("creation"),
    #         "modified": stock_entry.get("modified"),
    #         "docstatus": life_int(stock_entry.docstatus, 0),
    #         "workflow_state": stock_entry.get("workflow_state"),
    #         "posting_date": stock_entry.get("posting_date"),
    #         "from_warehouse": stock_entry.get("from_warehouse"),
    #         "to_warehouse": stock_entry.get("to_warehouse"),
    #         "purpose": stock_entry.get("purpose"),
    #         "stock_entry_type": stock_entry.get("stock_entry_type"),
    #         "base_grand_total": stock_entry.get("base_grand_total"),
    #         "released_by": released_by_identifier,
    #         "items": items
    #     }
    #     for fieldname in [
    #         "custom_sending_method", "custom_delivery_reference",
    #         "custom_stock_release_remarks", "custom_stock_released_by",
    #         "custom_stock_release_date", "custom_delivery_challan_photo_1",
    #         "custom_delivery_challan_photo_2", "custom_delivery_challan_photo_3",
    #         "custom_received_by", "custom_received_date", "custom_branch_receipt_remarks"
    #     ]:
    #         if life_has_field(SE_DOCTYPE, fieldname):
    #             row[fieldname] = stock_entry.get(fieldname)
    #     return row


    # def life_action_list_branch_receipts(payload):
    #     life_require_login()
    #     page = max(1, life_int(life_arg(payload, "page", 1), 1))
    #     page_size = min(200, max(1, life_int(life_arg(payload, "page_size", 10), 10)))
    #     branch = str(life_arg(payload, "branch", "") or "").strip()
    #     if not branch:
    #         employee = life_current_employee()
    #         branch = str(employee.get("branch") or "").strip() if employee else ""
    #     if not branch and not life_is_ho_user():
    #         frappe.throw("Branch could not be resolved for the logged-in user.")

    #     headers = frappe.get_list(
    #         SE_DOCTYPE,
    #         filters={"docstatus": 0, "purpose": "Material Transfer"},
    #         fields=["name"],
    #         order_by="modified desc",
    #         limit_page_length=500
    #     )

    #     rows = []
    #     for header in headers:
    #         stock_entry = frappe.get_doc(SE_DOCTYPE, header.get("name"))
    #         stock_entry.check_permission("read")
    #         workflow_text = life_status_text(stock_entry.get("workflow_state"))
    #         if "pending receipt" not in workflow_text and not life_is_ho_user():
    #             continue
    #         if branch and not life_stock_entry_targets_branch(stock_entry, branch):
    #             continue
    #         rows.append(life_stock_entry_row(stock_entry))

    #     released_by_identifiers = []
    #     for row in rows:
    #         released_by_identifier = str(
    #             row.get("released_by") or
    #             row.get("custom_stock_released_by") or
    #             row.get("owner") or
    #             row.get("modified_by") or
    #             ""
    #         ).strip()

    #         row["released_by"] = released_by_identifier

    #         if (
    #             released_by_identifier and
    #             released_by_identifier not in released_by_identifiers
    #         ):
    #             released_by_identifiers.append(released_by_identifier)

    #     released_by_name_map = life_requester_name_map(
    #         released_by_identifiers
    #     )

    #     for row in rows:
    #         released_by_identifier = str(
    #             row.get("released_by") or ""
    #         ).strip()

    #         row["released_by_name"] = (
    #             released_by_name_map.get(released_by_identifier) or
    #             released_by_identifier or
    #             "—"
    #         )

    #     total = len(rows)
    #     start = (page - 1) * page_size
    #     return {
    #         "ok": True,
    #         "branch": branch,
    #         "page": page,
    #         "page_size": page_size,
    #         "total": total,
    #         "total_pages": max(1, int((total + page_size - 1) / page_size)),
    #         "rows": rows[start:start + page_size]
    #     }


    # def life_action_confirm_branch_receipt(payload):
    #     life_require_login()
    #     stock_entry_name = str(payload.get("stock_entry") or "").strip()
    #     received_by = str(payload.get("received_by") or "").strip()
    #     receipt_remarks = str(
    #         payload.get("receipt_remarks") or payload.get("remarks") or ""
    #     ).strip()
    #     item_rows = payload.get("items") or []

    #     if not stock_entry_name:
    #         frappe.throw("Stock Entry name is required.")
    #     if not isinstance(item_rows, list) or not item_rows:
    #         frappe.throw("Received Quantities are required.")

    #     stock_entry = frappe.get_doc(SE_DOCTYPE, stock_entry_name)
    #     stock_entry.check_permission("read")
    #     if life_int(stock_entry.docstatus, 0) != 0:
    #         frappe.throw("This Stock Entry is no longer open for receipt.")
    #     purpose = str(stock_entry.get("purpose") or stock_entry.get("stock_entry_type") or "").strip()
    #     if purpose != "Material Transfer":
    #         frappe.throw("Only Material Transfer Stock Entries can be received here.")

    #     target_warehouse = str(stock_entry.get("to_warehouse") or "").strip()
    #     if not target_warehouse:
    #         for item in stock_entry.get("items") or []:
    #             if item.get("t_warehouse"):
    #                 target_warehouse = str(item.get("t_warehouse"))
    #                 break
    #     if not target_warehouse:
    #         frappe.throw("Receiving Warehouse is missing on the Stock Entry.")

    #     life_require_branch_warehouse(target_warehouse, "Receiving Warehouse")
    #     receiving_branch = life_branch_from_warehouse(target_warehouse)
    #     employee = life_validate_employee(received_by, receiving_branch)

    #     required_fields = [
    #         "custom_received_by", "custom_received_date", "custom_branch_receipt_remarks"
    #     ]
    #     missing = []
    #     for fieldname in required_fields:
    #         if not life_has_field(SE_DOCTYPE, fieldname):
    #             missing.append(fieldname)
    #     if not life_has_field(SE_ITEM_DOCTYPE, "custom_received_qty"):
    #         missing.append("Stock Entry Detail.custom_received_qty")
    #     if missing:
    #         frappe.throw("Create these Receipt fields first: " + ", ".join(missing))

    #     receipt_map = {}
    #     for row in item_rows:
    #         if not isinstance(row, dict):
    #             continue
    #         row_name = str(
    #             row.get("row_name") or row.get("stock_entry_detail") or ""
    #         ).strip()
    #         if row_name:
    #             receipt_map[row_name] = row

    #     for item in stock_entry.get("items") or []:
    #         receipt = receipt_map.get(str(item.name))
    #         if not receipt:
    #             frappe.throw("Received Quantity is missing for " + str(item.item_code) + ".")
    #         received_qty = life_float(receipt.get("received_qty"), 0)
    #         released_qty = max(0, life_float(item.get("qty"), 0))
    #         if received_qty < 0:
    #             frappe.throw("Received Quantity cannot be negative for " + str(item.item_code) + ".")
    #         if received_qty > released_qty + 0.000001:
    #             frappe.throw(
    #                 "Received Quantity " + str(received_qty) +
    #                 " cannot exceed Released Quantity " + str(released_qty) +
    #                 " for " + str(item.item_code) + "."
    #             )
    #         item.custom_received_qty = received_qty

    #     stock_entry.custom_received_by = employee.get("name")
    #     stock_entry.custom_received_date = frappe.utils.now()
    #     stock_entry.custom_branch_receipt_remarks = receipt_remarks

    #     # Permission is enforced above through target branch access and the workflow.
    #     # ignore_permissions only allows the controlled custom receipt fields to save.
    #     stock_entry.save(ignore_permissions=True)
    #     submitted = life_apply_receipt_submit(stock_entry)

    #     request_names = []
    #     for item in submitted.get("items") or []:
    #         request_name = str(item.get("material_request") or "").strip()
    #         if request_name and request_name not in request_names:
    #             request_names.append(request_name)

    #     for request_name in request_names:
    #         life_db_set_if_field(
    #             MR_DOCTYPE,
    #             request_name,
    #             "custom_stock_request_status",
    #             "Completed"
    #         )
    #         life_db_set_if_field(
    #             MR_DOCTYPE,
    #             request_name,
    #             "transfer_status",
    #             "Completed"
    #         )

    #     return {
    #         "ok": True,
    #         "message": "Stock Entry " + submitted.name + " receipt approved and submitted.",
    #         "stock_entry": submitted.as_dict(),
    #         "material_requests": request_names
    #     }



    # # ----------------------------------------------------------------------------
    # # STOCK RECONCILIATION WEB WORKFLOW — CONTROLLED PERMISSION GATEWAY
    # # ----------------------------------------------------------------------------

    # def life_stock_reconciliation_state(value, docstatus=0):
    #     state = str(value or "").strip()
    #     if state:
    #         return state

    #     status_value = life_int(docstatus, 0)
    #     if status_value == 1:
    #         return STOCK_RECONCILIATION_APPROVED
    #     if status_value == 2:
    #         return STOCK_RECONCILIATION_CANCELLED
    #     return STOCK_RECONCILIATION_DRAFT


    # def life_stock_reconciliation_requested_warehouses(payload):
    #     values = payload.get("warehouses") or []
    #     if isinstance(values, str):
    #         try:
    #             parsed = json.loads(values)
    #             values = parsed if isinstance(parsed, list) else [values]
    #         except Exception:
    #             values = [values]

    #     result = []
    #     if isinstance(values, (list, tuple)):
    #         for value in values:
    #             warehouse = str(value or "").strip()
    #             if warehouse and warehouse not in result:
    #                 result.append(warehouse)
    #     return result


    # def life_stock_reconciliation_doc_warehouses(doc):
    #     warehouses = []
    #     parent_warehouse = str(doc.get("set_warehouse") or "").strip()
    #     if parent_warehouse:
    #         warehouses.append(parent_warehouse)

    #     for row in doc.get("items") or []:
    #         warehouse = str(row.get("warehouse") or parent_warehouse or "").strip()
    #         if warehouse and warehouse not in warehouses:
    #             warehouses.append(warehouse)
    #     return warehouses


    # def life_stock_reconciliation_user_can_access_warehouses(warehouses):
    #     life_require_login()
    #     if life_is_ho_user():
    #         return True

    #     allowed_branches = life_allowed_branches()
    #     if not allowed_branches or not warehouses:
    #         return False

    #     for warehouse in warehouses:
    #         matched = False
    #         for branch in allowed_branches:
    #             if life_warehouse_matches_branch(warehouse, branch):
    #                 matched = True
    #                 break
    #         if not matched:
    #             return False
    #     return True


    # def life_stock_reconciliation_require_doc_access(doc):
    #     warehouses = life_stock_reconciliation_doc_warehouses(doc)
    #     if not life_stock_reconciliation_user_can_access_warehouses(warehouses):
    #         frappe.throw(
    #             "This Stock Reconciliation does not belong to a warehouse assigned to your branch.",
    #             frappe.PermissionError
    #         )


    # def life_stock_reconciliation_safe_doc(doc):
    #     output = {
    #         "name": doc.get("name"),
    #         "doctype": STOCK_RECONCILIATION_DOCTYPE,
    #         "posting_date": doc.get("posting_date"),
    #         "posting_time": doc.get("posting_time"),
    #         "set_warehouse": doc.get("set_warehouse"),
    #         "workflow_state": life_stock_reconciliation_state(
    #             doc.get("workflow_state"),
    #             doc.get("docstatus")
    #         ),
    #         "docstatus": life_int(doc.get("docstatus"), 0),
    #         "owner": doc.get("owner"),
    #         "creation": doc.get("creation"),
    #         "modified": doc.get("modified"),
    #         "modified_by": doc.get("modified_by"),
    #         "difference_amount": life_float(doc.get("difference_amount"), 0),
    #         "company": doc.get("company"),
    #         "purpose": doc.get("purpose"),
    #         "items": []
    #     }

    #     item_rows = []
    #     for row in doc.get("items") or []:
    #         item_rows.append({
    #             "name": row.get("name"),
    #             "idx": row.get("idx"),
    #             "item_code": row.get("item_code"),
    #             "item_name": row.get("item_name"),
    #             "warehouse": row.get("warehouse") or doc.get("set_warehouse"),
    #             "stock_uom": row.get("stock_uom"),
    #             "current_qty": life_float(row.get("current_qty"), 0),
    #             "qty": life_float(row.get("qty"), 0),
    #             "quantity_difference": life_float(row.get("quantity_difference"), 0),
    #             "valuation_rate": life_float(row.get("valuation_rate"), 0),
    #             "current_valuation_rate": life_float(row.get("current_valuation_rate"), 0),
    #             "amount": life_float(row.get("amount"), 0),
    #             "amount_difference": life_float(row.get("amount_difference"), 0)
    #         })
    #     output["items"] = item_rows
    #     return output


    # def life_action_list_stock_reconciliations(payload):
    #     life_require_login()
    #     scope = str(payload.get("scope") or "branch").strip().lower()
    #     if scope == "manager":
    #         life_require_ho()
    #     else:
    #         scope = "branch"

    #     status_filter = str(payload.get("status") or "").strip()
    #     from_date = str(payload.get("from_date") or "").strip()
    #     to_date = str(payload.get("to_date") or "").strip()
    #     search_text = str(payload.get("branch") or "").strip().lower()
    #     requested_warehouses = life_stock_reconciliation_requested_warehouses(payload)
    #     limit_value = life_int(payload.get("limit"), 500)
    #     if limit_value <= 0:
    #         limit_value = 500
    #     if limit_value > 2000:
    #         limit_value = 2000

    #     filters = []
    #     if from_date:
    #         filters.append(["posting_date", ">=", from_date])
    #     if to_date:
    #         filters.append(["posting_date", "<=", to_date])

    #     fields = [
    #         "name",
    #         "posting_date",
    #         "posting_time",
    #         "set_warehouse",
    #         "workflow_state",
    #         "docstatus",
    #         "owner",
    #         "creation",
    #         "modified",
    #         "modified_by",
    #         "difference_amount"
    #     ]

    #     rows = frappe.get_all(
    #         STOCK_RECONCILIATION_DOCTYPE,
    #         fields=fields,
    #         filters=filters,
    #         order_by="posting_date desc, creation desc",
    #         page_length=limit_value
    #     )

    #     allowed_branches = [] if life_is_ho_user() else life_allowed_branches()
    #     output = []
    #     for row in rows:
    #         warehouse = str(row.get("set_warehouse") or "").strip()
    #         state = life_stock_reconciliation_state(
    #             row.get("workflow_state"),
    #             row.get("docstatus")
    #         )

    #         if status_filter and state != status_filter:
    #             continue

    #         if scope == "branch":
    #             if not life_is_ho_user():
    #                 matched = False
    #                 for branch in allowed_branches:
    #                     if life_warehouse_matches_branch(warehouse, branch):
    #                         matched = True
    #                         break
    #                 if not matched:
    #                     continue

    #             if requested_warehouses:
    #                 requested_match = False
    #                 warehouse_key = life_normalize_key(warehouse)
    #                 warehouse_branch_key = life_normalize_key(
    #                     life_branch_from_warehouse(warehouse)
    #                 )
    #                 for requested_warehouse in requested_warehouses:
    #                     requested_key = life_normalize_key(requested_warehouse)
    #                     requested_branch_key = life_normalize_key(
    #                         life_branch_from_warehouse(requested_warehouse)
    #                     )
    #                     if (
    #                         warehouse_key == requested_key or
    #                         warehouse_branch_key == requested_branch_key or
    #                         life_warehouse_matches_branch(warehouse, requested_warehouse) or
    #                         life_warehouse_matches_branch(requested_warehouse, warehouse)
    #                     ):
    #                         requested_match = True
    #                         break
    #                 if not requested_match:
    #                     continue

    #         if scope == "manager" and search_text:
    #             warehouse_text = warehouse.lower()
    #             branch_text = life_branch_from_warehouse(warehouse).lower()
    #             if search_text not in warehouse_text and search_text not in branch_text:
    #                 continue

    #         output.append({
    #             "name": row.get("name"),
    #             "posting_date": row.get("posting_date"),
    #             "posting_time": row.get("posting_time"),
    #             "set_warehouse": warehouse,
    #             "workflow_state": state,
    #             "docstatus": life_int(row.get("docstatus"), 0),
    #             "owner": row.get("owner"),
    #             "creation": row.get("creation"),
    #             "modified": row.get("modified"),
    #             "modified_by": row.get("modified_by"),
    #             "difference_amount": life_float(row.get("difference_amount"), 0)
    #         })

    #     return {
    #         "ok": True,
    #         "rows": output,
    #         "count": len(output),
    #         "scope": scope
    #     }


    # def life_action_get_stock_reconciliation(payload):
    #     life_require_login()
    #     name = str(payload.get("name") or "").strip()
    #     if not name:
    #         frappe.throw("Stock Reconciliation name is required.")
    #     if not frappe.db.exists(STOCK_RECONCILIATION_DOCTYPE, name):
    #         frappe.throw("Stock Reconciliation " + name + " was not found.")

    #     doc = frappe.get_doc(STOCK_RECONCILIATION_DOCTYPE, name)
    #     life_stock_reconciliation_require_doc_access(doc)
    #     return {
    #         "ok": True,
    #         "doc": life_stock_reconciliation_safe_doc(doc)
    #     }


    # def life_stock_reconciliation_validate_create_doc(doc_data):
    #     if isinstance(doc_data, str):
    #         doc_data = json.loads(doc_data)
    #     if not isinstance(doc_data, dict):
    #         frappe.throw("Stock Reconciliation data must be a JSON object.")

    #     set_warehouse = str(doc_data.get("set_warehouse") or "").strip()
    #     if not set_warehouse:
    #         frappe.throw("Warehouse is required for physical stock verification.")
    #     life_require_branch_warehouse(set_warehouse, "Warehouse")

    #     raw_items = doc_data.get("items") or []
    #     if not isinstance(raw_items, list) or not raw_items:
    #         frappe.throw("Enter at least one physical stock count.")

    #     items = []
    #     for index, row in enumerate(raw_items):
    #         if not isinstance(row, dict):
    #             frappe.throw("Invalid item row at position " + str(index + 1) + ".")

    #         item_code = str(row.get("item_code") or "").strip()
    #         warehouse = str(row.get("warehouse") or set_warehouse).strip()
    #         quantity = life_float(row.get("qty"), 0)
    #         valuation_rate = life_float(row.get("valuation_rate"), 0)

    #         if not item_code:
    #             frappe.throw("Item Code is required at row " + str(index + 1) + ".")
    #         if not frappe.db.exists("Item", item_code):
    #             frappe.throw("Item " + item_code + " was not found.")
    #         if not warehouse:
    #             frappe.throw("Warehouse is required at row " + str(index + 1) + ".")
    #         life_require_branch_warehouse(warehouse, "Warehouse")
    #         if quantity < 0:
    #             frappe.throw("Physical quantity cannot be negative for " + item_code + ".")
    #         if quantity > 0 and valuation_rate <= 0:
    #             frappe.throw(
    #                 "Valuation Rate is required for " + item_code + " in " + warehouse + "."
    #             )

    #         items.append({
    #             "item_code": item_code,
    #             "warehouse": warehouse,
    #             "qty": quantity,
    #             "valuation_rate": valuation_rate
    #         })

    #     posting_date = str(doc_data.get("posting_date") or frappe.utils.today()).strip()
    #     company = str(doc_data.get("company") or COMPANY_FALLBACK).strip()
    #     if company != COMPANY_FALLBACK:
    #         frappe.throw("Invalid company for LIFE Stock Reconciliation.")

    #     return {
    #         "doctype": STOCK_RECONCILIATION_DOCTYPE,
    #         "purpose": "Stock Reconciliation",
    #         "company": company,
    #         "set_warehouse": set_warehouse,
    #         "posting_date": posting_date,
    #         "items": items
    #     }


    # def life_stock_reconciliation_transition(doc, action_name):
    #     action_name = str(action_name or "").strip()
    #     current_state = life_stock_reconciliation_state(
    #         doc.get("workflow_state"),
    #         doc.get("docstatus")
    #     )

    #     next_state = ""
    #     next_docstatus = 0
    #     manager_action = False

    #     if current_state == STOCK_RECONCILIATION_DRAFT and action_name == "Send for Approval":
    #         next_state = STOCK_RECONCILIATION_PENDING
    #     elif current_state == STOCK_RECONCILIATION_PENDING and action_name == "Reject":
    #         next_state = STOCK_RECONCILIATION_REJECTED
    #         manager_action = True
    #     elif current_state == STOCK_RECONCILIATION_PENDING and action_name == "Approve":
    #         next_state = STOCK_RECONCILIATION_APPROVED
    #         next_docstatus = 1
    #         manager_action = True
    #     elif current_state == STOCK_RECONCILIATION_APPROVED and action_name == "Cancel":
    #         next_state = STOCK_RECONCILIATION_CANCELLED
    #         next_docstatus = 2
    #         manager_action = True
    #     else:
    #         frappe.throw(
    #             "Workflow action " + action_name + " is not valid from " + current_state + "."
    #         )

    #     if manager_action:
    #         life_require_ho()
    #     else:
    #         life_stock_reconciliation_require_doc_access(doc)

    #     previous_install_flag = frappe.flags.get("in_install")
    #     try:
    #         frappe.flags.in_install = "frappe"
    #         doc.set("workflow_state", next_state)
    #         doc.flags.ignore_permissions = True

    #         if next_docstatus == 1:
    #             doc.submit()
    #         elif next_docstatus == 2:
    #             doc.cancel()
    #         else:
    #             doc.save(ignore_permissions=True)
    #     finally:
    #         frappe.flags.in_install = previous_install_flag

    #     doc.add_comment(
    #         "Workflow",
    #         next_state + " via LIFE Stock Dashboard by " + str(frappe.session.user)
    #     )
    #     return doc


    # def life_action_create_stock_reconciliation_request(payload):
    #     life_require_login()
    #     clean_doc = life_stock_reconciliation_validate_create_doc(payload.get("doc") or {})
    #     doc = frappe.get_doc(clean_doc)
    #     doc.insert(ignore_permissions=True)
    #     doc = life_stock_reconciliation_transition(doc, "Send for Approval")

    #     return {
    #         "ok": True,
    #         "message": "Physical stock verification request submitted for Stock Manager approval.",
    #         "doc": life_stock_reconciliation_safe_doc(doc)
    #     }


    # def life_action_apply_stock_reconciliation_workflow(payload):
    #     life_require_login()
    #     name = str(payload.get("name") or "").strip()
    #     action_name = str(payload.get("workflow_action") or payload.get("action_name") or "").strip()

    #     if not name:
    #         frappe.throw("Stock Reconciliation name is required.")
    #     if not action_name:
    #         frappe.throw("Workflow action is required.")
    #     if not frappe.db.exists(STOCK_RECONCILIATION_DOCTYPE, name):
    #         frappe.throw("Stock Reconciliation " + name + " was not found.")

    #     doc = frappe.get_doc(STOCK_RECONCILIATION_DOCTYPE, name)
    #     life_stock_reconciliation_require_doc_access(doc)
    #     doc = life_stock_reconciliation_transition(doc, action_name)

    #     return {
    #         "ok": True,
    #         "message": action_name + " completed successfully.",
    #         "doc": life_stock_reconciliation_safe_doc(doc)
    #     }


    # # ----------------------------------------------------------------------------
    # # UNIFIED STOCK API GATEWAY + STOCK INTELLIGENCE OPTIMISATION
    # # ----------------------------------------------------------------------------

    # LIFE_GATEWAY_ALLOWED_METHODS = [
    #     "frappe.client.get_list",
    #     "frappe.client.get_count",
    #     "frappe.client.get",
    #     "frappe.client.get_value",
    #     "frappe.client.insert",
    #     "frappe.client.submit",
    #     "frappe.client.cancel",
    #     "frappe.client.set_value",
    #     "frappe.model.workflow.get_transitions",
    #     "frappe.model.workflow.apply_workflow",
    #     "frappe.desk.query_report.run",
    #     "life_monthly_indent_access"
    # ]

    # LIFE_STOCK_INTELLIGENCE_COMPANY = COMPANY_FALLBACK
    # LIFE_STOCK_INTELLIGENCE_CORE_CACHE_SECONDS = 300
    # LIFE_STOCK_INTELLIGENCE_TRENDS_CACHE_SECONDS = 900

    # # Stock Intelligence monetary values use Item.valuation_rate.
    # # ERPNext Stock Balance remains the quantity source only.
    # # No Item Price, Purchase Receipt, Purchase Invoice, or last purchase rate is used.


    # def life_gateway_serializable(value):
    #     if value is None:
    #         return None

    #     if isinstance(value, dict):
    #         output = {}
    #         for key, item in value.items():
    #             output[key] = life_gateway_serializable(item)
    #         return output

    #     if isinstance(value, (list, tuple)):
    #         output = []
    #         for item in value:
    #             output.append(life_gateway_serializable(item))
    #         return output

    #     try:
    #         mapped = value.as_dict()
    #         return life_gateway_serializable(mapped)
    #     except Exception:
    #         return value


    # # ----------------------------------------------------------------------------
    # # RECEIPT DISCREPANCY — ORIGINAL TRANSFER + REVERSE MATERIAL TRANSFER
    # # ----------------------------------------------------------------------------

    # def life_receipt_adjustment_require_setup():
    #     missing = []
    #     for doctype in [RECEIPT_ADJUSTMENT_DOCTYPE, RECEIPT_ADJUSTMENT_ITEM_DOCTYPE]:
    #         if not frappe.db.exists("DocType", doctype):
    #             missing.append(doctype)

    #     required_parent_fields = [
    #         "status", "stock_entry", "material_request", "company",
    #         "source_warehouse", "target_warehouse", "target_branch",
    #         "reported_by", "reported_by_name", "reported_on",
    #         "branch_receipt_remarks", "adjustment_items",
    #         "total_released_qty", "total_received_qty", "total_missing_qty",
    #         "total_damaged_qty", "total_return_to_source_qty",
    #         "stock_manager_remarks", "approved_by", "approved_on",
    #         "submitted_stock_entry", "correction_requested_by",
    #         "correction_requested_on", "rejected_by", "rejected_on"
    #     ]
    #     if frappe.db.exists("DocType", RECEIPT_ADJUSTMENT_DOCTYPE):
    #         for fieldname in required_parent_fields:
    #             if not life_has_field(RECEIPT_ADJUSTMENT_DOCTYPE, fieldname):
    #                 missing.append(RECEIPT_ADJUSTMENT_DOCTYPE + "." + fieldname)

    #     required_child_fields = [
    #         "stock_entry_detail", "item_code", "item_name", "uom",
    #         "source_warehouse", "target_warehouse", "released_qty",
    #         "received_qty", "missing_qty", "damaged_qty",
    #         "return_to_source_qty", "discrepancy_type", "row_status",
    #         "discrepancy_remarks"
    #     ]
    #     if frappe.db.exists("DocType", RECEIPT_ADJUSTMENT_ITEM_DOCTYPE):
    #         for fieldname in required_child_fields:
    #             if not life_has_field(RECEIPT_ADJUSTMENT_ITEM_DOCTYPE, fieldname):
    #                 missing.append(RECEIPT_ADJUSTMENT_ITEM_DOCTYPE + "." + fieldname)

    #     if missing:
    #         frappe.throw(
    #             "Create or correct these receipt-adjustment fields first: " +
    #             ", ".join(missing)
    #         )


    # def life_receipt_adjustment_discrepancy_type(missing_qty, damaged_qty):
    #     if missing_qty > 0 and damaged_qty > 0:
    #         return "Missing and Damaged"
    #     if missing_qty > 0:
    #         return "Missing"
    #     if damaged_qty > 0:
    #         return "Damaged"
    #     return "No Discrepancy"


    # def life_receipt_adjustment_target_warehouse(stock_entry):
    #     target_warehouse = str(stock_entry.get("to_warehouse") or "").strip()
    #     if target_warehouse:
    #         return target_warehouse
    #     for item in stock_entry.get("items") or []:
    #         target_warehouse = str(item.get("t_warehouse") or "").strip()
    #         if target_warehouse:
    #             return target_warehouse
    #     return ""


    # def life_receipt_adjustment_source_warehouse(stock_entry):
    #     source_warehouse = str(stock_entry.get("from_warehouse") or "").strip()
    #     if source_warehouse:
    #         return source_warehouse
    #     for item in stock_entry.get("items") or []:
    #         source_warehouse = str(item.get("s_warehouse") or "").strip()
    #         if source_warehouse:
    #             return source_warehouse
    #     return ""


    # def life_receipt_adjustment_valid_material_request(stock_entry):
    #     for item in stock_entry.get("items") or []:
    #         request_name = str(item.get("material_request") or "").strip()
    #         if not request_name:
    #             continue
    #         if not frappe.db.exists(MR_DOCTYPE, request_name):
    #             continue
    #         docstatus = life_int(
    #             frappe.db.get_value(MR_DOCTYPE, request_name, "docstatus"),
    #             0
    #         )
    #         if docstatus != 2:
    #             return request_name
    #     return ""


    # def life_receipt_adjustment_clear_cancelled_links(stock_entry):
    #     valid_request_names = []
    #     for item in stock_entry.get("items") or []:
    #         request_name = str(item.get("material_request") or "").strip()
    #         if not request_name:
    #             continue
    #         docstatus = 2
    #         if frappe.db.exists(MR_DOCTYPE, request_name):
    #             docstatus = life_int(
    #                 frappe.db.get_value(MR_DOCTYPE, request_name, "docstatus"),
    #                 0
    #             )
    #         if docstatus == 2:
    #             item.set("material_request", None)
    #             item.set("material_request_item", None)
    #         elif request_name not in valid_request_names:
    #             valid_request_names.append(request_name)
    #     return valid_request_names


    # def life_receipt_adjustment_payload_rows(stock_entry, payload_rows):
    #     if not isinstance(payload_rows, list) or not payload_rows:
    #         frappe.throw("Item-wise receipt quantities are required.")

    #     payload_map = {}
    #     for row in payload_rows:
    #         if not isinstance(row, dict):
    #             continue
    #         row_name = str(
    #             row.get("row_name") or row.get("stock_entry_detail") or ""
    #         ).strip()
    #         if row_name:
    #             payload_map[row_name] = row

    #     resolved = []
    #     has_discrepancy = False
    #     tolerance = 0.0001

    #     for item in stock_entry.get("items") or []:
    #         payload_row = payload_map.get(str(item.name))
    #         if not payload_row:
    #             frappe.throw(
    #                 "Receipt quantities are missing for " +
    #                 str(item.get("item_code") or item.name) + "."
    #             )

    #         released_qty = max(0, life_float(item.get("qty"), 0))
    #         received_qty = life_float(payload_row.get("received_qty"), 0)
    #         missing_qty = life_float(payload_row.get("missing_qty"), 0)
    #         damaged_qty = life_float(payload_row.get("damaged_qty"), 0)
    #         discrepancy_remarks = str(
    #             payload_row.get("discrepancy_remarks") or ""
    #         ).strip()

    #         if received_qty < 0 or missing_qty < 0 or damaged_qty < 0:
    #             frappe.throw(
    #                 "Receipt quantities cannot be negative for " +
    #                 str(item.get("item_code") or item.name) + "."
    #             )

    #         accounted_qty = received_qty + missing_qty + damaged_qty
    #         if abs(accounted_qty - released_qty) > tolerance:
    #             frappe.throw(
    #                 "Received + Missing + Damaged must equal Released Qty " +
    #                 str(released_qty) + " for " +
    #                 str(item.get("item_code") or item.name) +
    #                 ". Current total: " + str(accounted_qty) + "."
    #             )

    #         return_qty = missing_qty + damaged_qty
    #         if return_qty > tolerance and not discrepancy_remarks:
    #             frappe.throw(
    #                 "Enter discrepancy remarks for " +
    #                 str(item.get("item_code") or item.name) + "."
    #             )

    #         if return_qty > tolerance:
    #             has_discrepancy = True

    #         resolved.append({
    #             "stock_item": item,
    #             "stock_entry_detail": item.name,
    #             "item_code": item.get("item_code"),
    #             "item_name": item.get("item_name") or item.get("item_code"),
    #             "uom": item.get("uom") or item.get("stock_uom") or "Nos",
    #             "source_warehouse": item.get("s_warehouse") or life_receipt_adjustment_source_warehouse(stock_entry),
    #             "target_warehouse": item.get("t_warehouse") or life_receipt_adjustment_target_warehouse(stock_entry),
    #             "released_qty": released_qty,
    #             "received_qty": received_qty,
    #             "missing_qty": missing_qty,
    #             "damaged_qty": damaged_qty,
    #             "return_to_source_qty": return_qty,
    #             "discrepancy_type": life_receipt_adjustment_discrepancy_type(
    #                 missing_qty,
    #                 damaged_qty
    #             ),
    #             "discrepancy_remarks": discrepancy_remarks
    #         })

    #     if not has_discrepancy:
    #         frappe.throw(
    #             "No missing or damaged quantity was reported. " +
    #             "Use the normal receipt confirmation instead."
    #         )

    #     return resolved


    # def life_receipt_adjustment_totals(rows):
    #     totals = {
    #         "released": 0,
    #         "received": 0,
    #         "missing": 0,
    #         "damaged": 0,
    #         "return_qty": 0
    #     }
    #     for row in rows:
    #         totals["released"] = totals.get("released", 0) + life_float(row.get("released_qty"), 0)
    #         totals["received"] = totals.get("received", 0) + life_float(row.get("received_qty"), 0)
    #         totals["missing"] = totals.get("missing", 0) + life_float(row.get("missing_qty"), 0)
    #         totals["damaged"] = totals.get("damaged", 0) + life_float(row.get("damaged_qty"), 0)
    #         totals["return_qty"] = totals.get("return_qty", 0) + life_float(row.get("return_to_source_qty"), 0)
    #     return totals


    # def life_receipt_adjustment_existing(stock_entry_name):
    #     request_name = frappe.db.get_value(
    #         RECEIPT_ADJUSTMENT_DOCTYPE,
    #         {"stock_entry": stock_entry_name},
    #         "name"
    #     )
    #     if request_name:
    #         return frappe.get_doc(RECEIPT_ADJUSTMENT_DOCTYPE, request_name)
    #     return None


    # def life_action_submit_receipt_adjustment(payload):
    #     life_require_login()
    #     life_receipt_adjustment_require_setup()

    #     stock_entry_name = str(payload.get("stock_entry") or "").strip()
    #     received_by = str(payload.get("received_by") or "").strip()
    #     receipt_remarks = str(
    #         payload.get("receipt_remarks") or payload.get("remarks") or ""
    #     ).strip()

    #     if not stock_entry_name:
    #         frappe.throw("Stock Entry name is required.")

    #     stock_entry = frappe.get_doc(SE_DOCTYPE, stock_entry_name)
    #     stock_entry.check_permission("read")

    #     if life_int(stock_entry.docstatus, 0) != 0:
    #         frappe.throw("This Stock Entry is no longer open for branch receipt.")

    #     purpose = str(
    #         stock_entry.get("purpose") or stock_entry.get("stock_entry_type") or ""
    #     ).strip()
    #     if purpose != "Material Transfer":
    #         frappe.throw("Only Material Transfer Stock Entries are supported.")

    #     target_warehouse = life_receipt_adjustment_target_warehouse(stock_entry)
    #     if not target_warehouse:
    #         frappe.throw("Receiving Warehouse is missing on the Stock Entry.")

    #     life_require_branch_warehouse(target_warehouse, "Receiving Warehouse")
    #     receiving_branch = life_branch_from_warehouse(target_warehouse)
    #     employee = life_validate_employee(received_by, receiving_branch)

    #     rows = life_receipt_adjustment_payload_rows(
    #         stock_entry,
    #         payload.get("items") or []
    #     )
    #     totals = life_receipt_adjustment_totals(rows)

    #     request = life_receipt_adjustment_existing(stock_entry.name)
    #     if request:
    #         status = str(request.get("status") or "Draft").strip()
    #         if status not in ["Draft", RECEIPT_ADJUSTMENT_CORRECTION]:
    #             frappe.throw(
    #                 "Adjustment request " + request.name + " is already " +
    #                 status + " and cannot be changed by the branch."
    #             )
    #         request.set("adjustment_items", [])
    #     else:
    #         request = frappe.new_doc(RECEIPT_ADJUSTMENT_DOCTYPE)
    #         if life_has_field(RECEIPT_ADJUSTMENT_DOCTYPE, "naming_series"):
    #             request.naming_series = "LSRA-.YYYY.-.#####"
    #         request.stock_entry = stock_entry.name

    #     material_request = life_receipt_adjustment_valid_material_request(stock_entry)
    #     request.status = RECEIPT_ADJUSTMENT_PENDING
    #     request.material_request = material_request or None
    #     request.company = stock_entry.get("company") or COMPANY_FALLBACK
    #     request.source_warehouse = life_receipt_adjustment_source_warehouse(stock_entry)
    #     request.target_warehouse = target_warehouse
    #     request.target_branch = receiving_branch or None
    #     request.reported_by = employee.get("name")
    #     request.reported_by_name = employee.get("employee_name") or employee.get("name")
    #     request.reported_on = frappe.utils.now()
    #     request.branch_receipt_remarks = receipt_remarks
    #     request.total_released_qty = totals.get("released")
    #     request.total_received_qty = totals.get("received")
    #     request.total_missing_qty = totals.get("missing")
    #     request.total_damaged_qty = totals.get("damaged")
    #     request.total_return_to_source_qty = totals.get("return_qty")
    #     request.stock_manager_remarks = ""
    #     request.approved_by = None
    #     request.approved_on = None
    #     request.submitted_stock_entry = None
    #     request.correction_requested_by = None
    #     request.correction_requested_on = None
    #     request.rejected_by = None
    #     request.rejected_on = None

    #     for row in rows:
    #         request.append("adjustment_items", {
    #             "stock_entry_detail": row.get("stock_entry_detail"),
    #             "item_code": row.get("item_code"),
    #             "item_name": row.get("item_name"),
    #             "uom": row.get("uom"),
    #             "source_warehouse": row.get("source_warehouse"),
    #             "target_warehouse": row.get("target_warehouse"),
    #             "released_qty": row.get("released_qty"),
    #             "received_qty": row.get("received_qty"),
    #             "missing_qty": row.get("missing_qty"),
    #             "damaged_qty": row.get("damaged_qty"),
    #             "return_to_source_qty": row.get("return_to_source_qty"),
    #             "discrepancy_type": row.get("discrepancy_type"),
    #             "row_status": "Pending Approval",
    #             "discrepancy_remarks": row.get("discrepancy_remarks")
    #         })

    #     if request.is_new():
    #         request.insert(ignore_permissions=True)
    #     else:
    #         request.save(ignore_permissions=True)

    #     return {
    #         "ok": True,
    #         "message": (
    #             "Receipt adjustment " + request.name +
    #             " is pending Stock Manager approval."
    #         ),
    #         "adjustment_request": request.as_dict(),
    #         "stock_entry": stock_entry.name
    #     }


    # def life_receipt_adjustment_request_item_map(request):
    #     by_detail = {}
    #     by_item = {}
    #     for row in request.get("adjustment_items") or []:
    #         detail = str(row.get("stock_entry_detail") or "").strip()
    #         item_code = str(row.get("item_code") or "").strip()
    #         if detail:
    #             by_detail[detail] = row
    #         if item_code and item_code not in by_item:
    #             by_item[item_code] = row
    #     return {"by_detail": by_detail, "by_item": by_item}


    # def life_receipt_adjustment_find_row(stock_item, request_map):
    #     detail = str(stock_item.get("name") or "").strip()
    #     item_code = str(stock_item.get("item_code") or "").strip()
    #     return (
    #         request_map.get("by_detail", {}).get(detail) or
    #         request_map.get("by_item", {}).get(item_code)
    #     )


    # def life_receipt_adjustment_existing_reverse(request, original_stock_entry_name):
    #     submitted_name = str(request.get("submitted_stock_entry") or "").strip()
    #     if submitted_name and submitted_name != original_stock_entry_name:
    #         if frappe.db.exists(SE_DOCTYPE, submitted_name):
    #             return frappe.get_doc(SE_DOCTYPE, submitted_name)

    #     if not life_has_field(SE_ITEM_DOCTYPE, "custom_adjustment_request"):
    #         return None

    #     rows = frappe.get_all(
    #         SE_ITEM_DOCTYPE,
    #         filters={
    #             "custom_adjustment_request": request.name,
    #             "parenttype": SE_DOCTYPE,
    #             "parent": ["!=", original_stock_entry_name],
    #             "docstatus": ["<", 2]
    #         },
    #         fields=["parent"],
    #         order_by="creation desc",
    #         page_length=1
    #     )
    #     if rows and rows[0].get("parent"):
    #         return frappe.get_doc(SE_DOCTYPE, rows[0].get("parent"))
    #     return None


    # def life_receipt_adjustment_apply_custom_fields(stock_item, adjustment_row, request_name):
    #     values = {
    #         "custom_released_qty": life_float(adjustment_row.get("released_qty"), 0),
    #         "custom_received_qty": life_float(adjustment_row.get("received_qty"), 0),
    #         "custom_missing_qty": life_float(adjustment_row.get("missing_qty"), 0),
    #         "custom_damaged_qty": life_float(adjustment_row.get("damaged_qty"), 0),
    #         "custom_return_to_source_qty": life_float(adjustment_row.get("return_to_source_qty"), 0),
    #         "custom_discrepancy_remarks": str(adjustment_row.get("discrepancy_remarks") or ""),
    #         "custom_adjustment_request": request_name
    #     }
    #     for fieldname, value in values.items():
    #         if life_has_field(SE_ITEM_DOCTYPE, fieldname):
    #             stock_item.set(fieldname, value)


    # def life_receipt_adjustment_submit_original(request, stock_entry):
    #     request_map = life_receipt_adjustment_request_item_map(request)
    #     valid_request_names = life_receipt_adjustment_clear_cancelled_links(stock_entry)

    #     for stock_item in stock_entry.get("items") or []:
    #         adjustment_row = life_receipt_adjustment_find_row(stock_item, request_map)
    #         if not adjustment_row:
    #             frappe.throw(
    #                 "Adjustment quantities are missing for Stock Entry item " +
    #                 str(stock_item.get("item_code") or stock_item.name) + "."
    #             )
    #         released_qty = life_float(adjustment_row.get("released_qty"), 0)
    #         received_qty = life_float(adjustment_row.get("received_qty"), 0)
    #         missing_qty = life_float(adjustment_row.get("missing_qty"), 0)
    #         damaged_qty = life_float(adjustment_row.get("damaged_qty"), 0)
    #         if abs((received_qty + missing_qty + damaged_qty) - released_qty) > 0.0001:
    #             frappe.throw(
    #                 "Adjustment quantities are not balanced for " +
    #                 str(stock_item.get("item_code") or stock_item.name) + "."
    #             )
    #         if abs(life_float(stock_item.get("qty"), 0) - released_qty) > 0.0001:
    #             frappe.throw(
    #                 "The released quantity changed after the branch report for " +
    #                 str(stock_item.get("item_code") or stock_item.name) + "."
    #             )
    #         life_receipt_adjustment_apply_custom_fields(
    #             stock_item,
    #             adjustment_row,
    #             request.name
    #         )

    #     life_set_if_field(stock_entry, "custom_received_by", request.get("reported_by"))
    #     life_set_if_field(stock_entry, "custom_received_date", request.get("reported_on") or frappe.utils.now())
    #     life_set_if_field(stock_entry, "custom_branch_receipt_remarks", request.get("branch_receipt_remarks") or "")

    #     if life_int(stock_entry.docstatus, 0) == 0:
    #         stock_entry.save(ignore_permissions=True)
    #         stock_entry.submit()
    #         stock_entry.reload()
    #     elif life_int(stock_entry.docstatus, 0) != 1:
    #         frappe.throw("The original Stock Entry is cancelled and cannot be adjusted.")

    #     return {"stock_entry": stock_entry, "material_requests": valid_request_names}


    # def life_receipt_adjustment_build_reverse(request, original_stock_entry):
    #     existing_reverse = life_receipt_adjustment_existing_reverse(
    #         request,
    #         original_stock_entry.name
    #     )
    #     if existing_reverse:
    #         if life_int(existing_reverse.docstatus, 0) == 0:
    #             existing_reverse.submit()
    #             existing_reverse.reload()
    #         if life_int(existing_reverse.docstatus, 0) != 1:
    #             frappe.throw("The existing reverse Stock Entry is not submitted.")
    #         return existing_reverse

    #     request_map = life_receipt_adjustment_request_item_map(request)
    #     reverse_items = []
    #     reverse_sources = []
    #     reverse_targets = []

    #     for stock_item in original_stock_entry.get("items") or []:
    #         adjustment_row = life_receipt_adjustment_find_row(stock_item, request_map)
    #         if not adjustment_row:
    #             continue

    #         return_qty = life_float(adjustment_row.get("return_to_source_qty"), 0)
    #         if return_qty <= 0.0001:
    #             continue

    #         if (
    #             stock_item.get("serial_and_batch_bundle") or
    #             stock_item.get("serial_no") or
    #             stock_item.get("batch_no")
    #         ):
    #             frappe.throw(
    #                 "Automatic reverse transfer is not supported for serial/batch-controlled item " +
    #                 str(stock_item.get("item_code") or stock_item.name) +
    #                 ". Create the reverse transfer manually with the correct Serial and Batch Bundle."
    #             )

    #         reverse_source = str(
    #             stock_item.get("t_warehouse") or request.get("target_warehouse") or ""
    #         ).strip()
    #         reverse_target = str(
    #             stock_item.get("s_warehouse") or adjustment_row.get("source_warehouse") or
    #             request.get("source_warehouse") or ""
    #         ).strip()

    #         if not reverse_source or not reverse_target:
    #             frappe.throw(
    #                 "Source or target warehouse is missing for reverse transfer item " +
    #                 str(stock_item.get("item_code") or stock_item.name) + "."
    #             )

    #         if reverse_source not in reverse_sources:
    #             reverse_sources.append(reverse_source)
    #         if reverse_target not in reverse_targets:
    #             reverse_targets.append(reverse_target)

    #         values = {
    #             "item_code": stock_item.get("item_code"),
    #             "qty": return_qty,
    #             "uom": stock_item.get("uom") or stock_item.get("stock_uom") or "Nos",
    #             "stock_uom": stock_item.get("stock_uom") or stock_item.get("uom") or "Nos",
    #             "conversion_factor": life_float(stock_item.get("conversion_factor"), 1) or 1,
    #             "s_warehouse": reverse_source,
    #             "t_warehouse": reverse_target
    #         }

    #         for fieldname in ["cost_center", "allow_zero_valuation_rate"]:
    #             if stock_item.get(fieldname) is not None and life_has_field(SE_ITEM_DOCTYPE, fieldname):
    #                 values[fieldname] = stock_item.get(fieldname)

    #         custom_values = {
    #             "custom_released_qty": adjustment_row.get("released_qty"),
    #             "custom_received_qty": adjustment_row.get("received_qty"),
    #             "custom_missing_qty": adjustment_row.get("missing_qty"),
    #             "custom_damaged_qty": adjustment_row.get("damaged_qty"),
    #             "custom_return_to_source_qty": return_qty,
    #             "custom_discrepancy_remarks": adjustment_row.get("discrepancy_remarks") or "",
    #             "custom_adjustment_request": request.name
    #         }
    #         for fieldname, value in custom_values.items():
    #             if life_has_field(SE_ITEM_DOCTYPE, fieldname):
    #                 values[fieldname] = value

    #         reverse_items.append(values)

    #     if not reverse_items:
    #         frappe.throw("No missing or damaged quantity is available for reverse transfer.")

    #     reverse_entry = frappe.new_doc(SE_DOCTYPE)
    #     reverse_entry.stock_entry_type = "Material Transfer"
    #     reverse_entry.purpose = "Material Transfer"
    #     reverse_entry.company = original_stock_entry.get("company") or request.get("company") or COMPANY_FALLBACK
    #     if len(reverse_sources) == 1:
    #         reverse_entry.from_warehouse = reverse_sources[0]
    #     if len(reverse_targets) == 1:
    #         reverse_entry.to_warehouse = reverse_targets[0]
    #     reverse_entry.remarks = (
    #         "Reverse receipt adjustment " + request.name +
    #         " against original Stock Entry " + original_stock_entry.name +
    #         ". Missing Qty: " + str(request.get("total_missing_qty") or 0) +
    #         ", Damaged Qty: " + str(request.get("total_damaged_qty") or 0) + "."
    #     )

    #     for values in reverse_items:
    #         reverse_entry.append("items", values)

    #     reverse_entry.insert(ignore_permissions=True)
    #     reverse_entry.submit()
    #     reverse_entry.reload()

    #     if life_int(reverse_entry.docstatus, 0) != 1:
    #         frappe.throw("ERPNext did not submit the reverse Material Transfer.")

    #     return reverse_entry


    # def life_action_approve_receipt_adjustment(payload):
    #     life_require_ho()
    #     life_receipt_adjustment_require_setup()

    #     request_name = str(
    #         payload.get("request_name") or payload.get("name") or ""
    #     ).strip()
    #     manager_remarks = str(
    #         payload.get("remarks") or payload.get("stock_manager_remarks") or ""
    #     ).strip()

    #     if not request_name:
    #         frappe.throw("Receipt Adjustment Request name is required.")

    #     request = frappe.get_doc(RECEIPT_ADJUSTMENT_DOCTYPE, request_name)
    #     status = str(request.get("status") or "Draft").strip()

    #     if status == RECEIPT_ADJUSTMENT_COMPLETED:
    #         original = frappe.get_doc(SE_DOCTYPE, request.get("stock_entry"))
    #         reverse = None
    #         reverse_name = str(request.get("submitted_stock_entry") or "").strip()
    #         if reverse_name and frappe.db.exists(SE_DOCTYPE, reverse_name):
    #             reverse = frappe.get_doc(SE_DOCTYPE, reverse_name)
    #         return {
    #             "ok": True,
    #             "message": "Receipt adjustment was already completed.",
    #             "adjustment_request": request.as_dict(),
    #             "original_stock_entry": original.as_dict(),
    #             "adjustment_stock_entry": reverse.as_dict() if reverse else None,
    #             "already_completed": True
    #         }

    #     if status not in [RECEIPT_ADJUSTMENT_PENDING, RECEIPT_ADJUSTMENT_APPROVED]:
    #         frappe.throw(
    #             "Only Pending or Approved receipt adjustments can be completed."
    #         )

    #     material_request = str(request.get("material_request") or "").strip()
    #     if material_request:
    #         if (
    #             not frappe.db.exists(MR_DOCTYPE, material_request) or
    #             life_int(frappe.db.get_value(MR_DOCTYPE, material_request, "docstatus"), 0) == 2
    #         ):
    #             request.material_request = None

    #     original_stock_entry = frappe.get_doc(
    #         SE_DOCTYPE,
    #         request.get("stock_entry")
    #     )

    #     purpose = str(
    #         original_stock_entry.get("purpose") or
    #         original_stock_entry.get("stock_entry_type") or ""
    #     ).strip()
    #     if purpose != "Material Transfer":
    #         frappe.throw("The original Stock Entry is not a Material Transfer.")

    #     request.status = RECEIPT_ADJUSTMENT_APPROVED
    #     request.stock_manager_remarks = manager_remarks
    #     request.approved_by = life_require_login()
    #     request.approved_on = frappe.utils.now()

    #     original_result = life_receipt_adjustment_submit_original(
    #         request,
    #         original_stock_entry
    #     )
    #     original_stock_entry = original_result.get("stock_entry")

    #     reverse_stock_entry = life_receipt_adjustment_build_reverse(
    #         request,
    #         original_stock_entry
    #     )

    #     request.status = RECEIPT_ADJUSTMENT_COMPLETED
    #     request.submitted_stock_entry = reverse_stock_entry.name
    #     for row in request.get("adjustment_items") or []:
    #         row.row_status = "Approved"
    #     request.save(ignore_permissions=True)

    #     for request_name_value in original_result.get("material_requests") or []:
    #         life_db_set_if_field(
    #             MR_DOCTYPE,
    #             request_name_value,
    #             "custom_stock_request_status",
    #             "Completed"
    #         )
    #         life_db_set_if_field(
    #             MR_DOCTYPE,
    #             request_name_value,
    #             "transfer_status",
    #             "Completed"
    #         )

    #     return {
    #         "ok": True,
    #         "message": (
    #             "Original Stock Entry " + original_stock_entry.name +
    #             " was submitted and reverse Material Transfer " +
    #             reverse_stock_entry.name + " returned Missing + Damaged stock " +
    #             "to the source warehouse."
    #         ),
    #         "adjustment_request": request.as_dict(),
    #         "original_stock_entry": original_stock_entry.as_dict(),
    #         "adjustment_stock_entry": reverse_stock_entry.as_dict(),
    #         "already_completed": False
    #     }


    # def life_action_decide_receipt_adjustment(payload):
    #     life_require_ho()
    #     life_receipt_adjustment_require_setup()

    #     request_name = str(
    #         payload.get("request_name") or payload.get("name") or ""
    #     ).strip()
    #     decision = str(payload.get("decision") or "").strip().lower()
    #     remarks = str(
    #         payload.get("remarks") or payload.get("stock_manager_remarks") or ""
    #     ).strip()

    #     if not request_name:
    #         frappe.throw("Receipt Adjustment Request name is required.")
    #     if decision not in ["correction", "reject"]:
    #         frappe.throw("Decision must be correction or reject.")
    #     if not remarks:
    #         frappe.throw("Stock Manager Remarks are required.")

    #     request = frappe.get_doc(RECEIPT_ADJUSTMENT_DOCTYPE, request_name)
    #     if str(request.get("status") or "").strip() != RECEIPT_ADJUSTMENT_PENDING:
    #         frappe.throw("Only a pending receipt adjustment can be updated.")

    #     material_request = str(request.get("material_request") or "").strip()
    #     if material_request:
    #         if (
    #             not frappe.db.exists(MR_DOCTYPE, material_request) or
    #             life_int(frappe.db.get_value(MR_DOCTYPE, material_request, "docstatus"), 0) == 2
    #         ):
    #             request.material_request = None

    #     request.stock_manager_remarks = remarks
    #     current_user = life_require_login()
    #     current_time = frappe.utils.now()

    #     if decision == "correction":
    #         request.status = RECEIPT_ADJUSTMENT_CORRECTION
    #         request.correction_requested_by = current_user
    #         request.correction_requested_on = current_time
    #         row_status = "Correction Requested"
    #         message = "Receipt adjustment returned to the branch for correction."
    #     else:
    #         request.status = RECEIPT_ADJUSTMENT_REJECTED
    #         request.rejected_by = current_user
    #         request.rejected_on = current_time
    #         row_status = "Rejected"
    #         message = "Receipt adjustment rejected. No stock was changed."

    #     for row in request.get("adjustment_items") or []:
    #         row.row_status = row_status

    #     request.save(ignore_permissions=True)

    #     return {
    #         "ok": True,
    #         "message": message,
    #         "adjustment_request": request.as_dict()
    #     }


    # def life_gateway_method_allowed(method):
    #     method = str(method or "").strip()
    #     return method in LIFE_GATEWAY_ALLOWED_METHODS


    # def life_gateway_nested_call_begin():
    #     saved = {}

    #     for key in ["cmd", "action", "payload"]:
    #         if key in frappe.form_dict:
    #             saved[key] = frappe.form_dict.get(key)
    #             frappe.form_dict.pop(key)

    #     return saved


    # def life_gateway_nested_call_end(saved):
    #     if not isinstance(saved, dict):
    #         return

    #     for key, value in saved.items():
    #         frappe.form_dict[key] = value


    # def life_gateway_workflow_get_transitions(doc):
    #     saved = life_gateway_nested_call_begin()

    #     try:
    #         return frappe.call(
    #             "frappe.model.workflow.get_transitions",
    #             doc=doc
    #         )
    #     finally:
    #         life_gateway_nested_call_end(saved)


    # def life_gateway_workflow_apply(doc, action_name):
    #     saved = life_gateway_nested_call_begin()

    #     try:
    #         return frappe.call(
    #             "frappe.model.workflow.apply_workflow",
    #             doc=doc,
    #             action=action_name
    #         )
    #     finally:
    #         life_gateway_nested_call_end(saved)


    # def life_gateway_query_report(
    #     report_name,
    #     filters,
    #     ignore_prepared_report=1,
    #     are_default_filters=0
    # ):
    #     saved = life_gateway_nested_call_begin()

    #     if isinstance(filters, dict):
    #         filters_value = json.dumps(filters)
    #     else:
    #         filters_value = str(filters or "{}")

    #     ignore_value = 1 if life_int(ignore_prepared_report, 1) else 0
    #     default_value = 1 if life_int(are_default_filters, 0) else 0

    #     try:
    #         return frappe.call(
    #             "frappe.desk.query_report.run",
    #             report_name=str(report_name or "").strip(),
    #             filters=filters_value,
    #             ignore_prepared_report=ignore_value,
    #             are_default_filters=default_value
    #         )
    #     finally:
    #         life_gateway_nested_call_end(saved)


    # def life_gateway_get_list(args):
    #     doctype = str(args.get("doctype") or "").strip()
    #     if not doctype:
    #         frappe.throw("DocType is required.")

    #     fields = args.get("fields") or ["name"]
    #     filters = args.get("filters") or {}
    #     or_filters = args.get("or_filters") or {}
    #     order_by = str(args.get("order_by") or "modified desc").strip()
    #     group_by = str(args.get("group_by") or "").strip()
    #     limit_start = max(0, life_int(args.get("limit_start"), 0))
    #     limit_page_length = life_int(args.get("limit_page_length"), 20)

    #     if limit_page_length <= 0:
    #         limit_page_length = 5000

    #     if group_by:
    #         return frappe.get_list(
    #             doctype,
    #             fields=fields,
    #             filters=filters,
    #             or_filters=or_filters,
    #             order_by=order_by,
    #             group_by=group_by,
    #             limit_start=limit_start,
    #             limit_page_length=limit_page_length
    #         )

    #     return frappe.get_list(
    #         doctype,
    #         fields=fields,
    #         filters=filters,
    #         or_filters=or_filters,
    #         order_by=order_by,
    #         limit_start=limit_start,
    #         limit_page_length=limit_page_length
    #     )


    # def life_gateway_get_count(args):
    #     doctype = str(args.get("doctype") or "").strip()
    #     if not doctype:
    #         frappe.throw("DocType is required.")

    #     rows = frappe.get_list(
    #         doctype,
    #         fields=["count(name) as total_count"],
    #         filters=args.get("filters") or {},
    #         or_filters=args.get("or_filters") or {},
    #         limit_start=0,
    #         limit_page_length=1
    #     )

    #     if not rows:
    #         return 0

    #     return life_int(rows[0].get("total_count"), 0)


    # def life_gateway_get_doc(args):
    #     doctype = str(args.get("doctype") or "").strip()
    #     name = str(args.get("name") or "").strip()

    #     if not doctype:
    #         frappe.throw("DocType is required.")

    #     if not name:
    #         rows = frappe.get_list(
    #             doctype,
    #             fields=["name"],
    #             filters=args.get("filters") or {},
    #             limit_start=0,
    #             limit_page_length=1
    #         )

    #         if not rows:
    #             return None

    #         name = str(rows[0].get("name") or "").strip()

    #     if not name:
    #         return None

    #     doc = frappe.get_doc(doctype, name)
    #     doc.check_permission("read")
    #     return doc.as_dict()


    # def life_gateway_get_value(args):
    #     doctype = str(args.get("doctype") or "").strip()
    #     if not doctype:
    #         frappe.throw("DocType is required.")

    #     fieldname = args.get("fieldname") or "name"

    #     if isinstance(fieldname, (list, tuple)):
    #         fields = []
    #         for field in fieldname:
    #             clean_field = str(field or "").strip()
    #             if clean_field:
    #                 fields.append(clean_field)
    #     else:
    #         fields = [str(fieldname or "name").strip()]

    #     if not fields:
    #         fields = ["name"]

    #     rows = frappe.get_list(
    #         doctype,
    #         fields=fields,
    #         filters=args.get("filters") or {},
    #         limit_start=0,
    #         limit_page_length=1
    #     )

    #     if not rows:
    #         return {}

    #     return rows[0]


    # def life_gateway_parse_doc(value):
    #     if isinstance(value, str):
    #         value = json.loads(value)

    #     if not isinstance(value, dict):
    #         frappe.throw("Document data must be a JSON object.")

    #     return value


    # def life_gateway_insert(args):
    #     doc_data = life_gateway_parse_doc(args.get("doc"))
    #     doc = frappe.get_doc(doc_data)
    #     doc.insert()
    #     return doc.as_dict()


    # def life_gateway_submit(args):
    #     doc_data = life_gateway_parse_doc(args.get("doc"))
    #     doc = frappe.get_doc(doc_data)
    #     doc.submit()
    #     return doc.as_dict()


    # def life_gateway_cancel(args):
    #     doctype = str(args.get("doctype") or "").strip()
    #     name = str(args.get("name") or "").strip()

    #     if not doctype or not name:
    #         frappe.throw("DocType and document name are required.")

    #     doc = frappe.get_doc(doctype, name)
    #     doc.cancel()
    #     return doc.as_dict()


    # def life_gateway_set_value(args):
    #     doctype = str(args.get("doctype") or "").strip()
    #     name = str(args.get("name") or "").strip()
    #     fieldname = args.get("fieldname")
    #     value = args.get("value")

    #     if not doctype or not name:
    #         frappe.throw("DocType and document name are required.")

    #     doc = frappe.get_doc(doctype, name)
    #     doc.check_permission("write")

    #     if isinstance(fieldname, dict):
    #         for key, field_value in fieldname.items():
    #             doc.set(key, field_value)
    #     else:
    #         clean_fieldname = str(fieldname or "").strip()
    #         if not clean_fieldname:
    #             frappe.throw("Field name is required.")
    #         doc.set(clean_fieldname, value)

    #     doc.save()
    #     return doc.as_dict()


    # def life_gateway_monthly_indent_access(args):
    #     settings_doctype = "LIFE Stock Request Settings"
    #     settings_field = "enable_monthly_indent_exception"
    #     requested_action = str(args.get("action") or "get").strip().lower()

    #     if requested_action not in ["get", "set", "status"]:
    #         frappe.throw("Unsupported Monthly Indent access action.")

    #     enabled = life_int(
    #         frappe.db.get_single_value(
    #             settings_doctype,
    #             settings_field
    #         ),
    #         0
    #     )

    #     if requested_action == "set":
    #         life_require_ho()

    #         enabled = 1 if life_int(args.get("enabled"), 0) else 0

    #         frappe.db.set_single_value(
    #             settings_doctype,
    #             settings_field,
    #             enabled
    #         )

    #     return {
    #         "enabled": enabled,
    #         "action": requested_action
    #     }


    # def life_gateway_dispatch(method, args):
    #     if method == "frappe.client.get_list":
    #         return life_gateway_get_list(args)

    #     if method == "frappe.client.get_count":
    #         return life_gateway_get_count(args)

    #     if method == "frappe.client.get":
    #         return life_gateway_get_doc(args)

    #     if method == "frappe.client.get_value":
    #         return life_gateway_get_value(args)

    #     if method == "frappe.client.insert":
    #         return life_gateway_insert(args)

    #     if method == "frappe.client.submit":
    #         return life_gateway_submit(args)

    #     if method == "frappe.client.cancel":
    #         return life_gateway_cancel(args)

    #     if method == "frappe.client.set_value":
    #         return life_gateway_set_value(args)

    #     if method == "frappe.model.workflow.get_transitions":
    #         return life_gateway_workflow_get_transitions(
    #             args.get("doc")
    #         )

    #     if method == "frappe.model.workflow.apply_workflow":
    #         return life_gateway_workflow_apply(
    #             args.get("doc"),
    #             str(args.get("action") or "").strip()
    #         )

    #     if method == "frappe.desk.query_report.run":
    #         return life_gateway_query_report(
    #             args.get("report_name"),
    #             args.get("filters") or {},
    #             args.get("ignore_prepared_report"),
    #             args.get("are_default_filters")
    #         )

    #     if method == "life_monthly_indent_access":
    #         return life_gateway_monthly_indent_access(args)

    #     frappe.throw(
    #         "No dispatcher is configured for the LIFE Stock API method: " +
    #         str(method)
    #     )


    # def life_action_invoke(payload):
    #     life_require_login()

    #     method = str(payload.get("method") or "").strip()
    #     args = payload.get("args") or {}

    #     if not life_gateway_method_allowed(method):
    #         frappe.throw(
    #             "This server method is not allowed through the LIFE Stock API: " +
    #             str(method),
    #             frappe.PermissionError
    #         )

    #     if not isinstance(args, dict):
    #         frappe.throw("API method arguments must be a JSON object.")

    #     result = life_gateway_dispatch(method, args)

    #     return {
    #         "ok": True,
    #         "method": method,
    #         "data": life_gateway_serializable(result)
    #     }


    # def life_action_batch(payload):
    #     life_require_login()

    #     operations = payload.get("operations") or []
    #     if not isinstance(operations, list):
    #         frappe.throw("Batch operations must be a list.")
    #     if len(operations) > 30:
    #         frappe.throw("A maximum of 30 API operations is allowed in one batch.")

    #     results = []
    #     for index, operation in enumerate(operations):
    #         if not isinstance(operation, dict):
    #             frappe.throw("Invalid batch operation at position " + str(index + 1) + ".")

    #         method = str(operation.get("method") or "").strip()
    #         args = operation.get("args") or {}

    #         try:
    #             response = life_action_invoke({
    #                 "method": method,
    #                 "args": args
    #             })
    #             results.append({
    #                 "ok": True,
    #                 "method": method,
    #                 "data": response.get("data")
    #             })
    #         except Exception as error:
    #             results.append({
    #                 "ok": False,
    #                 "method": method,
    #                 "message": str(error)
    #             })

    #     return {
    #         "ok": True,
    #         "results": results
    #     }


    # def life_action_upload_file(payload):
    #     life_require_login()

    #     try:
    #         files = frappe.request.files
    #     except Exception:
    #         files = None

    #     upload = files.get("file") if files else None
    #     if not upload:
    #         frappe.throw("No file was received.")

    #     try:
    #         stream = upload.stream
    #     except Exception:
    #         stream = upload

    #     content = stream.read()
    #     if content is None:
    #         frappe.throw("The uploaded file could not be read.")

    #     maximum_bytes = 10 * 1024 * 1024
    #     if len(content) > maximum_bytes:
    #         frappe.throw("The uploaded file exceeds the 10 MB limit.")

    #     try:
    #         uploaded_file_name = upload.filename
    #     except Exception:
    #         uploaded_file_name = None

    #     file_name = str(
    #         uploaded_file_name or
    #         payload.get("file_name") or
    #         "upload.bin"
    #     ).strip()

    #     file_doc = frappe.get_doc({
    #         "doctype": "File",
    #         "file_name": file_name,
    #         "is_private": life_int(payload.get("is_private"), 1),
    #         "content": content,
    #         "attached_to_doctype": str(payload.get("attached_to_doctype") or "").strip() or None,
    #         "attached_to_name": str(payload.get("attached_to_name") or "").strip() or None,
    #         "attached_to_field": str(payload.get("attached_to_field") or "").strip() or None
    #     })
    #     file_doc.insert()

    #     return {
    #         "ok": True,
    #         "file_name": file_doc.name,
    #         "file_url": file_doc.file_url,
    #         "is_private": file_doc.is_private
    #     }


    # def life_si_cache_get(cache_key):
    #     try:
    #         return frappe.cache().get_value(cache_key)
    #     except Exception:
    #         return None


    # def life_si_cache_set(cache_key, value, expires_in_sec):
    #     try:
    #         frappe.cache().set_value(
    #             cache_key,
    #             value,
    #             expires_in_sec=expires_in_sec
    #         )
    #     except Exception:
    #         pass


    # def life_si_cache_key(phase, payload):
    #     keys = [
    #         "from_date",
    #         "to_date",
    #         "prev_from_date",
    #         "prev_to_date",
    #         "fc1_from_date",
    #         "fc1_to_date",
    #         "fc2_from_date",
    #         "fc2_to_date",
    #         "fc3_from_date",
    #         "fc3_to_date",
    #         "ledger_from_date",
    #         "ledger_to_date"
    #     ]

    #     parts = [
    #         "life_stock_intelligence_v7_item_doctype_valuation",
    #         str(phase or "core"),
    #         LIFE_STOCK_INTELLIGENCE_COMPANY
    #     ]

    #     for key in keys:
    #         parts.append(str(payload.get(key) or ""))

    #     return ":".join(parts)


    # def life_si_report(report_name, filters):
    #     return life_gateway_query_report(
    #         report_name,
    #         filters,
    #         1,
    #         1
    #     )


    # def life_si_safe_load(pack, failed, key, loader):
    #     try:
    #         pack[key] = life_gateway_serializable(loader())
    #     except Exception as error:
    #         pack[key] = []
    #         failed.append(key + ": " + str(error))


    # def life_si_item_group_map(item_codes):
    #     output = {}
    #     codes = []
    #     for item_code in item_codes or []:
    #         item_code = str(item_code or "").strip()
    #         if item_code and item_code not in codes:
    #             codes.append(item_code)

    #     chunk_size = 500
    #     start = 0
    #     while start < len(codes):
    #         chunk = codes[start:start + chunk_size]
    #         rows = frappe.get_all(
    #             "Item",
    #             filters={"name": ["in", chunk]},
    #             fields=["name", "item_group"],
    #             page_length=len(chunk)
    #         )
    #         for row in rows:
    #             output[str(row.get("name") or "")] = str(row.get("item_group") or "")
    #         start = start + chunk_size

    #     return output



    # def life_si_report_rows(report_data):
    #     """Return the row list from the ERPNext report response shape."""
    #     if isinstance(report_data, list):
    #         return report_data

    #     if isinstance(report_data, dict):
    #         result = report_data.get("result")
    #         if isinstance(result, list):
    #             return result

    #         message = report_data.get("message")
    #         if isinstance(message, dict):
    #             nested_result = message.get("result")
    #             if isinstance(nested_result, list):
    #                 return nested_result

    #         if isinstance(message, list):
    #             return message

    #     return []


    # def life_si_item_valuation_rate_map(item_codes):
    #     """
    #     Return Item.valuation_rate for the requested item codes.

    #     Stock Intelligence monetary rule:
    #     - quantity source: ERPNext Stock Balance / Stock Ledger
    #     - rate source: Item.valuation_rate only
    #     - no Item Price / selling price / purchase-rate fallback
    #     - missing or zero valuation_rate = 0
    #     """
    #     clean_codes = []

    #     for item_code in item_codes or []:
    #         item_code = str(item_code or "").strip()
    #         if item_code and item_code not in clean_codes:
    #             clean_codes.append(item_code)

    #     output = {}
    #     chunk_size = 500
    #     start = 0

    #     while start < len(clean_codes):
    #         chunk = clean_codes[start:start + chunk_size]

    #         rows = frappe.get_all(
    #             "Item",
    #             filters={"name": ["in", chunk]},
    #             fields=["name", "valuation_rate"],
    #             page_length=len(chunk)
    #         )

    #         for row in rows or []:
    #             item_code = str(row.get("name") or "").strip()
    #             if not item_code:
    #                 continue

    #             output[item_code] = life_float(
    #                 row.get("valuation_rate"),
    #                 0
    #             )

    #         start = start + chunk_size

    #     return output


    # def life_si_apply_item_valuation_rates(report_data):
    #     """
    #     Keep ERPNext Stock Balance quantities, but rebuild monetary fields from
    #     Item.valuation_rate.

    #     Existing frontend field names stay compatible:
    #     - val_rate = Item.valuation_rate
    #     - bal_val = bal_qty * Item.valuation_rate
    #     - opening_val / in_val / out_val = corresponding qty * Item.valuation_rate
    #     """
    #     rows = life_si_report_rows(report_data)
    #     if not rows:
    #         return report_data

    #     item_codes = []

    #     for row in rows:
    #         # Query Reports may append a final Total row as a list.
    #         if not isinstance(row, dict):
    #             continue

    #         item_code = str(row.get("item_code") or "").strip()
    #         if item_code and item_code not in item_codes:
    #             item_codes.append(item_code)

    #     rate_map = life_si_item_valuation_rate_map(item_codes)

    #     for row in rows:
    #         if not isinstance(row, dict):
    #             continue

    #         item_code = str(row.get("item_code") or "").strip()
    #         item_rate = life_float(rate_map.get(item_code), 0)

    #         # Preserve original Stock Balance valuation for diagnostics only.
    #         row["stock_balance_val_rate"] = life_float(row.get("val_rate"), 0)
    #         row["stock_balance_bal_val"] = life_float(row.get("bal_val"), 0)
    #         row["stock_balance_opening_val"] = life_float(row.get("opening_val"), 0)
    #         row["stock_balance_in_val"] = life_float(row.get("in_val"), 0)
    #         row["stock_balance_out_val"] = life_float(row.get("out_val"), 0)

    #         row["item_valuation_rate"] = item_rate
    #         row["valuation_rate_source"] = "Item.valuation_rate"
    #         row["valuation_rate_missing"] = 0 if item_rate > 0 else 1

    #         # Compatibility alias used by the existing Stock Intelligence JS.
    #         row["val_rate"] = item_rate

    #         if "opening_qty" in row:
    #             row["opening_val"] = (
    #                 life_float(row.get("opening_qty"), 0) * item_rate
    #             )

    #         if "in_qty" in row:
    #             row["in_val"] = (
    #                 life_float(row.get("in_qty"), 0) * item_rate
    #             )

    #         if "out_qty" in row:
    #             row["out_val"] = (
    #                 life_float(row.get("out_qty"), 0) * item_rate
    #             )

    #         if "bal_qty" in row:
    #             row["bal_val"] = (
    #                 life_float(row.get("bal_qty"), 0) * item_rate
    #             )

    #     return report_data


    # def life_si_aggregate_ledger(from_date, to_date, mode):
    #     filters = {
    #         "company": LIFE_STOCK_INTELLIGENCE_COMPANY,
    #         "posting_date": ["between", [from_date, to_date]],
    #         "is_cancelled": 0
    #     }

    #     if mode == "movement":
    #         filters["actual_qty"] = ["<", 0]
    #         or_filters = None
    #     else:
    #         or_filters = {
    #             "actual_qty": ["<", 0],
    #             "stock_value_difference": ["<", 0]
    #         }

    #     rows = frappe.get_all(
    #         "Stock Ledger Entry",
    #         filters=filters,
    #         or_filters=or_filters,
    #         fields=[
    #             "item_code",
    #             "warehouse",
    #             "actual_qty",
    #             "stock_value_difference",
    #             "valuation_rate",
    #             "posting_date"
    #         ],
    #         order_by="posting_date asc",
    #         page_length=100000
    #     )

    #     aggregate = {}
    #     item_codes = []

    #     for row in rows:
    #         item_code = str(row.get("item_code") or "").strip()
    #         warehouse = str(row.get("warehouse") or "").strip()
    #         if not item_code or not warehouse:
    #             continue

    #         if item_code not in item_codes:
    #             item_codes.append(item_code)

    #         key = item_code + "||" + warehouse
    #         if key not in aggregate:
    #             aggregate[key] = {
    #                 "item_code": item_code,
    #                 "warehouse": warehouse,
    #                 "actual_qty": 0,
    #                 "stock_value_difference": 0,
    #                 "valuation_rate": 0,
    #                 "posting_date": ""
    #             }

    #         target = aggregate[key]
    #         actual_qty = life_float(row.get("actual_qty"), 0)
    #         value_difference = life_float(row.get("stock_value_difference"), 0)
    #         valuation_rate = life_float(row.get("valuation_rate"), 0)
    #         posting_date = str(row.get("posting_date") or "")

    #         if actual_qty < 0:
    #             target["actual_qty"] = target.get("actual_qty", 0) - abs(actual_qty)

    #         if value_difference < 0:
    #             target["stock_value_difference"] = target.get("stock_value_difference", 0) - abs(value_difference)

    #         if valuation_rate > 0:
    #             target["valuation_rate"] = valuation_rate

    #         if posting_date > target["posting_date"]:
    #             target["posting_date"] = posting_date

    #     item_groups = life_si_item_group_map(item_codes)
    #     rate_map = life_si_item_valuation_rate_map(item_codes)
    #     output = []

    #     for row in aggregate.values():
    #         item_code = str(row.get("item_code") or "").strip()
    #         item_rate = life_float(rate_map.get(item_code), 0)

    #         # Preserve original Stock Ledger valuation for diagnostics only.
    #         row["stock_ledger_valuation_rate"] = life_float(
    #             row.get("valuation_rate"),
    #             0
    #         )
    #         row["stock_ledger_value_difference"] = life_float(
    #             row.get("stock_value_difference"),
    #             0
    #         )

    #         row["item_valuation_rate"] = item_rate
    #         row["valuation_rate_source"] = "Item.valuation_rate"
    #         row["valuation_rate_missing"] = 0 if item_rate > 0 else 1

    #         # Compatibility aliases for the current frontend.
    #         row["valuation_rate"] = item_rate

    #         movement_qty = life_float(row.get("actual_qty"), 0)
    #         if movement_qty < 0:
    #             row["stock_value_difference"] = (
    #                 -abs(movement_qty) * item_rate
    #             )
    #         else:
    #             row["stock_value_difference"] = 0

    #         row["item_group"] = item_groups.get(item_code, "")
    #         output.append(row)

    #     return output


    # def life_si_warehouses():
    #     rows = frappe.get_list(
    #         "Warehouse",
    #         filters={
    #             "company": LIFE_STOCK_INTELLIGENCE_COMPANY,
    #             "disabled": 0
    #         },
    #         fields=["name", "is_group", "company", "disabled"],
    #         order_by="name asc",
    #         page_length=1000
    #     )
    #     return rows


    # def life_si_sessions(from_date, to_date):
    #     return frappe.get_list(
    #         "Therapy Session",
    #         filters={
    #             "start_date": ["between", [from_date, to_date]],
    #             "docstatus": ["!=", 2]
    #         },
    #         fields=[
    #             "name",
    #             "patient",
    #             "therapy_type",
    #             "service_unit",
    #             "start_date",
    #             "docstatus",
    #             "owner"
    #         ],
    #         order_by="start_date desc",
    #         page_length=10000
    #     )


    # def life_si_assets():
    #     return frappe.get_list(
    #         "Asset",
    #         filters={"status": "Submitted"},
    #         fields=[
    #             "name",
    #             "docstatus",
    #             "asset_name",
    #             "asset_category",
    #             "location",
    #             "gross_purchase_amount",
    #             "status",
    #             "image"
    #         ],
    #         order_by="modified desc",
    #         page_length=5000
    #     )


    # def life_si_batches():
    #     today = frappe.utils.today()
    #     next_30_days = frappe.utils.add_days(today, 30)

    #     return frappe.get_list(
    #         "Batch",
    #         filters={
    #             "disabled": 0,
    #             "expiry_date": ["between", [today, next_30_days]]
    #         },
    #         fields=[
    #             "name",
    #             "batch_id",
    #             "item_name",
    #             "batch_qty",
    #             "item",
    #             "expiry_date",
    #             "disabled"
    #         ],
    #         order_by="expiry_date asc",
    #         page_length=5000
    #     )


    # def life_action_stock_intelligence(payload):
    #     life_require_ho()

    #     phase = str(payload.get("phase") or "core").strip().lower()
    #     if phase not in ["core", "trends"]:
    #         frappe.throw("Stock Intelligence phase must be core or trends.")

    #     required_dates = ["from_date", "to_date"]
    #     if phase == "trends":
    #         required_dates = required_dates + [
    #             "prev_from_date",
    #             "prev_to_date",
    #             "fc1_from_date",
    #             "fc1_to_date",
    #             "fc2_from_date",
    #             "fc2_to_date",
    #             "fc3_from_date",
    #             "fc3_to_date"
    #         ]

    #     for fieldname in required_dates:
    #         if not str(payload.get(fieldname) or "").strip():
    #             frappe.throw("Missing Stock Intelligence date: " + fieldname)

    #     force_refresh = bool(life_int(payload.get("force_refresh"), 0))
    #     cache_key = life_si_cache_key(phase, payload)

    #     if not force_refresh:
    #         cached = life_si_cache_get(cache_key)
    #         if cached:
    #             cached["ok"] = True
    #             cached["cached"] = True
    #             return cached

    #     pack = {}
    #     failed = []

    #     company = LIFE_STOCK_INTELLIGENCE_COMPANY
    #     from_date = str(payload.get("from_date"))
    #     to_date = str(payload.get("to_date"))


    #     if phase == "core":
    #         ledger_from_date = str(
    #             payload.get("ledger_from_date") or
    #             frappe.utils.add_months(to_date, -4)
    #         )
    #         ledger_to_date = str(payload.get("ledger_to_date") or to_date)

    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "warehouses",
    #             lambda: life_si_warehouses()
    #         )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "stockBalanceCurrent",
    #             lambda: life_si_report(
    #                 "Stock Balance",
    #                 {
    #                     "company": company,
    #                     "from_date": from_date,
    #                     "to_date": to_date,
    #                     "item_code": [],
    #                     "warehouse": [],
    #                     "valuation_field_type": "Currency"
    #                 }
    #             )
    #         )

    #         # Stock Balance remains the quantity source. Convert only its
    #         # monetary fields to Item.valuation_rate after the known-good
    #         # ERPNext report call has completed.
    #         if pack.get("stockBalanceCurrent"):
    #             try:
    #                 pack["stockBalanceCurrent"] = life_si_apply_item_valuation_rates(
    #                     pack.get("stockBalanceCurrent")
    #                 )
    #             except Exception as error:
    #                 pack["stockBalanceCurrent"] = []
    #                 failed.append(
    #                     "stockBalanceCurrent Item valuation conversion: " + str(error)
    #                 )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "stockProjected",
    #             lambda: life_si_report(
    #                 "Stock Projected Qty",
    #                 {"company": company}
    #             )
    #         )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "stockLedger4m",
    #             lambda: life_si_aggregate_ledger(
    #                 ledger_from_date,
    #                 ledger_to_date,
    #                 "movement"
    #             )
    #         )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "assets",
    #             lambda: life_si_assets()
    #         )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "batches",
    #             lambda: life_si_batches()
    #         )

    #         expires = LIFE_STOCK_INTELLIGENCE_CORE_CACHE_SECONDS

    #     else:
    #         prev_from_date = str(payload.get("prev_from_date"))
    #         prev_to_date = str(payload.get("prev_to_date"))

    #         fc1_from_date = str(payload.get("fc1_from_date"))
    #         fc1_to_date = str(payload.get("fc1_to_date"))
    #         fc2_from_date = str(payload.get("fc2_from_date"))
    #         fc2_to_date = str(payload.get("fc2_to_date"))
    #         fc3_from_date = str(payload.get("fc3_from_date"))
    #         fc3_to_date = str(payload.get("fc3_to_date"))

    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "stockBalancePrevious",
    #             lambda: life_si_report(
    #                 "Stock Balance",
    #                 {
    #                     "company": company,
    #                     "from_date": prev_from_date,
    #                     "to_date": prev_to_date,
    #                     "item_code": [],
    #                     "warehouse": [],
    #                     "valuation_field_type": "Currency"
    #                 }
    #             )
    #         )

    #         # Previous-period quantity is also valued using the current
    #         # Item.valuation_rate, so all Stock Intelligence monetary values use
    #         # one consistent Item-master rate source.
    #         if pack.get("stockBalancePrevious"):
    #             try:
    #                 pack["stockBalancePrevious"] = life_si_apply_item_valuation_rates(
    #                     pack.get("stockBalancePrevious")
    #                 )
    #             except Exception as error:
    #                 pack["stockBalancePrevious"] = []
    #                 failed.append(
    #                     "stockBalancePrevious Item valuation conversion: " + str(error)
    #                 )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "forecastLedger1",
    #             lambda: life_si_aggregate_ledger(
    #                 fc1_from_date,
    #                 fc1_to_date,
    #                 "forecast"
    #             )
    #         )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "forecastLedger2",
    #             lambda: life_si_aggregate_ledger(
    #                 fc2_from_date,
    #                 fc2_to_date,
    #                 "forecast"
    #             )
    #         )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "forecastLedger3",
    #             lambda: life_si_aggregate_ledger(
    #                 fc3_from_date,
    #                 fc3_to_date,
    #                 "forecast"
    #             )
    #         )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "therapySessions",
    #             lambda: life_si_sessions(from_date, to_date)
    #         )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "therapySessionsPrev",
    #             lambda: life_si_sessions(prev_from_date, prev_to_date)
    #         )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "therapyRevenue",
    #             lambda: life_si_report(
    #                 "ITEM WISE SALES – COLLECTION",
    #                 {
    #                     "from_date": from_date,
    #                     "to_date": to_date
    #                 }
    #             )
    #         )
    #         life_si_safe_load(
    #             pack,
    #             failed,
    #             "therapyRevenuePrev",
    #             lambda: life_si_report(
    #                 "ITEM WISE SALES – COLLECTION",
    #                 {
    #                     "from_date": prev_from_date,
    #                     "to_date": prev_to_date
    #                 }
    #             )
    #         )

    #         # These arrays were previously loaded only to recover Item Group names.
    #         # Aggregated ledger rows now include item_group, so the duplicate
    #         # Stock Balance report executions are no longer required.
    #         pack["stockBalanceOlder"] = []
    #         pack["forecastStock1"] = []
    #         pack["forecastStock2"] = []
    #         pack["forecastStock3"] = []

    #         expires = LIFE_STOCK_INTELLIGENCE_TRENDS_CACHE_SECONDS

    #     response = {
    #         "ok": True,
    #         "phase": phase,
    #         "cached": False,
    #         "generated_at": frappe.utils.now(),
    #         "data": pack,
    #         "failed": failed
    #     }

    #     life_si_cache_set(cache_key, response, expires)
    #     return response


    # # ----------------------------------------------------------------------------
    # # API DISPATCH
    # # ----------------------------------------------------------------------------
    # life_require_login()
    # request_payload = life_payload()
    # action = str(
    #     frappe.form_dict.get("action") or
    #     request_payload.get("action") or
    #     "list_requests"
    # ).strip().lower()

    # if action == "get_context":
    #     result = life_action_get_context(request_payload)
    # elif action == "check_setup":
    #     result = life_action_check_setup(request_payload)
    # elif action == "list_requests":
    #     result = life_action_list_requests(request_payload)
    # elif action == "get_request":
    #     result = life_action_get_request(request_payload)
    # elif action == "get_stock_availability":
    #     result = life_action_get_stock_availability(request_payload)
    # elif action == "get_item_stock_availability":
    #     result = life_action_get_item_stock_availability(request_payload)
    # elif action == "submit_request":
    #     result = life_action_submit_request(request_payload)
    # elif action == "approve_request":
    #     result = life_action_approve_request(request_payload)
    # elif action == "reject_request":
    #     result = life_action_reject_request(request_payload)
    # elif action == "release_stock":
    #     result = life_action_release_stock(request_payload)
    # elif action == "list_branch_receipts":
    #     result = life_action_list_branch_receipts(request_payload)
    # elif action == "confirm_branch_receipt":
    #     result = life_action_confirm_branch_receipt(request_payload)
    # elif action == "submit_receipt_adjustment":
    #     result = life_action_submit_receipt_adjustment(request_payload)
    # elif action == "approve_receipt_adjustment":
    #     result = life_action_approve_receipt_adjustment(request_payload)
    # elif action == "decide_receipt_adjustment":
    #     result = life_action_decide_receipt_adjustment(request_payload)
    # elif action == "list_stock_reconciliations":
    #     result = life_action_list_stock_reconciliations(request_payload)
    # elif action == "get_stock_reconciliation":
    #     result = life_action_get_stock_reconciliation(request_payload)
    # elif action == "create_stock_reconciliation_request":
    #     result = life_action_create_stock_reconciliation_request(request_payload)
    # elif action == "apply_stock_reconciliation_workflow":
    #     result = life_action_apply_stock_reconciliation_workflow(request_payload)
    # elif action == "invoke":
    #     result = life_action_invoke(request_payload)
    # elif action == "batch":
    #     result = life_action_batch(request_payload)
    # elif action == "upload_file":
    #     result = life_action_upload_file(request_payload)
    # elif action == "stock_intelligence":
    #     result = life_action_stock_intelligence(request_payload)
    # else:
    #     frappe.throw("Unsupported LIFE Stock API action: " + action)

    # frappe.response["message"] = result


    # ============================================================================
    # LIFE STOCK MANAGEMENT — COMPLETE MATERIAL REQUEST API
    # Server Script Type : API
    # API Method         : life_stock_fast_requests
    # Allow Guest        : OFF
    #
    # One endpoint, selected by the `action` argument.
    #
    # Supported actions:
    #   get_context
    #   check_setup
    #   list_requests              (default; backward compatible)
    #   get_request
    #   get_stock_availability
    #   get_item_stock_availability
    #   submit_request
    #   approve_request
    #   reject_request
    #   release_stock
    #   list_branch_receipts
    #   confirm_branch_receipt
    #   billing_receipt_gate       (System User Billing gate; 24-hour receipt SLA)
    #   submit_receipt_adjustment
    #   approve_receipt_adjustment
    #   decide_receipt_adjustment
    #   list_stock_reconciliations
    #   get_stock_reconciliation
    #   create_stock_reconciliation_request
    #   apply_stock_reconciliation_workflow
    #   invoke                     (permission-aware gateway for approved methods)
    #   batch                      (up to 30 approved gateway calls)
    #   upload_file                (multipart upload through this API method)
    #   stock_intelligence         (cached core/trend data)
    # ============================================================================

    RECEIPT_RULE_START_DATE = "2026-08-01"
    MR_DOCTYPE = "Material Request"
    MR_ITEM_DOCTYPE = "Material Request Item"
    SE_DOCTYPE = "Stock Entry"
    SE_ITEM_DOCTYPE = "Stock Entry Detail"
    FILE_DOCTYPE = "File"
    RECEIPT_ADJUSTMENT_DOCTYPE = "LIFE Stock Receipt Adjustment Request"
    RECEIPT_ADJUSTMENT_ITEM_DOCTYPE = "LIFE Stock Receipt Adjustment Item"
    RECEIPT_ADJUSTMENT_PENDING = "Pending Stock Manager Approval"
    RECEIPT_ADJUSTMENT_CORRECTION = "Correction Requested"
    RECEIPT_ADJUSTMENT_APPROVED = "Approved"
    RECEIPT_ADJUSTMENT_REJECTED = "Rejected"
    RECEIPT_ADJUSTMENT_COMPLETED = "Adjustment Completed"

    STOCK_RECONCILIATION_DOCTYPE = "Stock Reconciliation"
    STOCK_RECONCILIATION_DRAFT = "Draft"
    STOCK_RECONCILIATION_PENDING = "Pending Stock Manager Approval"
    STOCK_RECONCILIATION_REJECTED = "Rejected"
    STOCK_RECONCILIATION_APPROVED = "Approved"
    STOCK_RECONCILIATION_CANCELLED = "Cancelled"

    COMPANY_FALLBACK = "Life Slimming And Cosmetic Pvt Ltd"
    MR_PENDING_STATE = "Pending Inventory"
    MR_APPROVED_STATE = "Approved"
    MR_REJECTED_STATE = "Rejected"
    SE_PENDING_RECEIPT_STATE = "Pending Receipt (Sub WH)"

    REQUEST_TYPE_SPECIAL = "Special Material Request"
    REQUEST_TYPE_ADVANCE = "Advance Material Request"
    REQUEST_TYPE_MONTHLY = "Monthly Indent Request"
    ALLOWED_REQUEST_TYPES = [
        REQUEST_TYPE_SPECIAL,
        REQUEST_TYPE_ADVANCE,
        REQUEST_TYPE_MONTHLY
    ]

    HO_ROLES = ["System Manager", "Stock Manager"]
    HO_USERS = [
        "administrator",
        "bhuvan@lifescc.com",
        "inventory@lifescc.com",
        "lokakavyareddy3@gmail.com",
        "narendhar@lifescc.com",
        "yaswanthkumaryy1234@gmail.com"
    ]

    REQUEST_ATTACHMENT_TABLE = "custom_treatment_card_attachments"
    REQUEST_ATTACHMENT_LEGACY = "custom_attachments"
    REQUEST_ATTACHMENT_CHILD = "Special Material Request Attachment"


    def life_parse_json(value):
        if value is None or value == "":
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                frappe.throw("Payload must be a JSON object.")
            return parsed
        frappe.throw("Unsupported payload type.")


    def life_payload():
        raw = frappe.form_dict.get("payload")
        if raw is None or raw == "":
            return {}
        return life_parse_json(raw)


    def life_arg(payload, key, default_value=None):
        if isinstance(payload, dict) and payload.get(key) is not None:
            return payload.get(key)
        value = frappe.form_dict.get(key)
        if value is None:
            return default_value
        return value


    def life_int(value, default_value=0):
        try:
            return frappe.utils.cint(value)
        except Exception:
            return default_value


    def life_float(value, default_value=0):
        try:
            return frappe.utils.flt(value)
        except Exception:
            return default_value


    def life_require_login():
        user = str(frappe.session.user or "").strip()
        if not user or user == "Guest":
            frappe.throw("Please log in to continue.", frappe.AuthenticationError)
        return user


    def life_user_roles():
        user = life_require_login()
        rows = frappe.get_all(
            "Has Role",
            filters={"parent": user, "parenttype": "User"},
            fields=["role"],
            page_length=500
        )
        roles = []
        for row in rows:
            role = str(row.get("role") or "").strip()
            if role and role not in roles:
                roles.append(role)
        return roles


    def life_is_ho_user():
        user = life_require_login().lower()
        if user in HO_USERS:
            return True
        roles = life_user_roles()
        for role in roles:
            if role in HO_ROLES:
                return True
        return False


    def life_require_ho():
        if not life_is_ho_user():
            frappe.throw(
                "Only an authorised Stock Manager or System Manager can perform this action.",
                frappe.PermissionError
            )


    def life_has_field(doctype, fieldname):
        return bool(frappe.get_meta(doctype).get_field(fieldname))


    def life_set_if_field(doc, fieldname, value):
        if life_has_field(doc.doctype, fieldname):
            doc.set(fieldname, value)
            return True
        return False


    def life_db_set_if_field(doctype, name, fieldname, value):
        if life_has_field(doctype, fieldname):
            frappe.db.set_value(
                doctype,
                name,
                fieldname,
                value,
                update_modified=False
            )
            return True
        return False


    def life_current_employee():
        user = life_require_login()
        employee_meta = frappe.get_meta("Employee")
        fields = ["name", "employee_name", "status"]
        for fieldname in ["branch", "company", "designation", "user_id"]:
            if employee_meta.get_field(fieldname):
                fields.append(fieldname)

        filters = {"status": "Active"}
        if employee_meta.get_field("user_id"):
            filters["user_id"] = user
        else:
            return None

        rows = frappe.get_all(
            "Employee",
            filters=filters,
            fields=fields,
            order_by="modified desc",
            page_length=1
        )
        return rows[0] if rows else None


    def life_normalize_key(value):
        text = str(value or "").strip().lower()
        result = ""
        for character in text:
            if character.isalnum():
                result = result + character
        return result


    def life_branch_from_warehouse(warehouse):
        warehouse = str(warehouse or "").strip()
        if not warehouse:
            return ""

        if frappe.db.exists("Warehouse", warehouse):
            warehouse_meta = frappe.get_meta("Warehouse")
            for fieldname in ["branch", "custom_branch"]:
                if warehouse_meta.get_field(fieldname):
                    branch_value = frappe.db.get_value("Warehouse", warehouse, fieldname)
                    if branch_value:
                        return str(branch_value).strip()

        text = warehouse
        suffixes = [
            " - LSACPL",
            "- LSACPL",
            " Store Warehouse",
            " store warehouse",
            " Warehouse",
            " warehouse"
        ]
        for suffix in suffixes:
            if text.endswith(suffix):
                text = text[0:len(text) - len(suffix)].strip()
        return text


    def life_warehouse_matches_branch(warehouse, branch):
        warehouse_key = life_normalize_key(warehouse)
        branch_key = life_normalize_key(branch)
        derived_key = life_normalize_key(life_branch_from_warehouse(warehouse))
        if not warehouse_key or not branch_key:
            return False
        return derived_key == branch_key or branch_key in warehouse_key


    def life_allowed_branches():
        if life_is_ho_user():
            return []

        branches = []
        employee = life_current_employee()
        if employee and employee.get("branch"):
            branches.append(str(employee.get("branch")).strip())

        rows = frappe.get_all(
            "User Permission",
            filters={
                "user": frappe.session.user,
                "allow": "Branch"
            },
            fields=["for_value"],
            page_length=500
        )
        for row in rows:
            branch = str(row.get("for_value") or "").strip()
            if branch and branch not in branches:
                branches.append(branch)
        return branches


    def life_allowed_request_warehouses():
        """
    Return the Warehouses that should be shown in LIFE request forms.

    This is an additive UI-context helper only:
    - Stock Manager / System Manager: all enabled leaf Warehouses.
    - Normal users: existing branch-derived Warehouses PLUS explicit
      Warehouse User Permissions.
    - Group Warehouse permissions include enabled leaf descendants unless
      hide_descendants is enabled.

    Existing submit/approval/receipt/reconciliation permission checks are
    intentionally not changed by this helper.
    """
        user = life_require_login()

        warehouse_rows = frappe.get_all(
            "Warehouse",
            fields=[
                "name",
                "warehouse_name",
                "company",
                "is_group",
                "disabled",
                "lft",
                "rgt"
            ],
            order_by="name asc",
            page_length=2000
        )

        active_leaf_rows = []
        warehouse_by_name = {}

        for row in warehouse_rows:
            warehouse_name = str(row.get("name") or "").strip()

            if warehouse_name:
                warehouse_by_name[warehouse_name] = row

            if life_int(row.get("is_group"), 0):
                continue

            if life_int(row.get("disabled"), 0):
                continue

            active_leaf_rows.append(row)

        # Existing HO rule is preserved: Stock Manager / System Manager already
        # bypass branch warehouse restriction in life_require_branch_warehouse().
        if life_is_ho_user():
            return [
                {
                    "name": row.get("name"),
                    "warehouse_name": row.get("warehouse_name"),
                    "company": row.get("company"),
                    "is_group": 0,
                    "disabled": 0
                }
                for row in active_leaf_rows
            ]

        allowed_names = []

        def add_allowed_name(warehouse_name):
            warehouse_name = str(warehouse_name or "").strip()
            if warehouse_name and warehouse_name not in allowed_names:
                allowed_names.append(warehouse_name)

        # Preserve existing branch-based availability as a fallback/base.
        for branch in life_allowed_branches():
            for row in active_leaf_rows:
                warehouse_name = str(row.get("name") or "").strip()

                if life_warehouse_matches_branch(
                    warehouse_name,
                    branch
                ):
                    add_allowed_name(warehouse_name)

        # Add explicit Warehouse User Permissions.
        permission_rows = frappe.get_all(
            "User Permission",
            filters={
                "user": user,
                "allow": "Warehouse"
            },
            fields=[
                "for_value",
                "hide_descendants"
            ],
            page_length=500
        )

        for permission in permission_rows:
            permitted_name = str(
                permission.get("for_value") or ""
            ).strip()

            if not permitted_name:
                continue

            permitted_row = warehouse_by_name.get(
                permitted_name
            )

            if not permitted_row:
                continue

            if not life_int(
                permitted_row.get("is_group"),
                0
            ):
                if not life_int(
                    permitted_row.get("disabled"),
                    0
                ):
                    add_allowed_name(
                        permitted_name
                    )
                continue

            if life_int(
                permission.get("hide_descendants"),
                0
            ):
                continue

            parent_lft = life_int(
                permitted_row.get("lft"),
                0
            )
            parent_rgt = life_int(
                permitted_row.get("rgt"),
                0
            )

            for row in active_leaf_rows:
                row_lft = life_int(
                    row.get("lft"),
                    0
                )
                row_rgt = life_int(
                    row.get("rgt"),
                    0
                )

                if (
                    row_lft > parent_lft and
                    row_rgt < parent_rgt
                ):
                    add_allowed_name(
                        row.get("name")
                    )

        allowed_map = {}

        for warehouse_name in allowed_names:
            allowed_map[warehouse_name] = True

        result = []

        for row in active_leaf_rows:
            warehouse_name = str(
                row.get("name") or ""
            ).strip()

            if not allowed_map.get(
                warehouse_name
            ):
                continue

            result.append({
                "name": row.get("name"),
                "warehouse_name": row.get("warehouse_name"),
                "company": row.get("company"),
                "is_group": 0,
                "disabled": 0
            })

        return result


    def life_require_branch_warehouse(warehouse, label):
        life_require_login()
        if life_is_ho_user():
            return

        branches = life_allowed_branches()
        if not branches:
            frappe.throw(
                "No active Employee branch or Branch User Permission is available for this user.",
                frappe.PermissionError
            )

        allowed = False
        for branch in branches:
            if life_warehouse_matches_branch(warehouse, branch):
                allowed = True
                break

        if not allowed:
            frappe.throw(
                str(label or "Warehouse") + " " + str(warehouse) + " is not assigned to your branch.",
                frappe.PermissionError
            )


    def life_validate_employee(employee_name, branch=""):
        employee_name = str(
            employee_name or ""
        ).strip()

        if not employee_name:
            frappe.throw(
                "Received By / Requesting Employee is required."
            )

        employee_meta = frappe.get_meta("Employee")

        fields = [
            "name",
            "employee_name",
            "status"
        ]

        for fieldname in [
            "branch",
            "company",
            "designation",
            "user_id"
        ]:
            if employee_meta.get_field(fieldname):
                fields.append(fieldname)

        rows = frappe.get_all(
            "Employee",
            filters={
                "name": employee_name,
                "status": "Active"
            },
            fields=fields,
            page_length=1
        )

        if not rows:
            frappe.throw(
                "The selected employee is not active or could not be found."
            )

        return rows[0]

    def life_request_type(row):
        if isinstance(row, dict):
            value = row.get("custom_stock_request_type") or row.get("custom_request_type")
            notes = row.get("custom_additional_notes")
        else:
            value = row.get("custom_stock_request_type") or row.get("custom_request_type")
            notes = row.get("custom_additional_notes")

        value = str(value or "").strip()
        if value:
            return value

        notes = str(notes or "").lower()
        if "monthly indent" in notes:
            return REQUEST_TYPE_MONTHLY
        if "advance material" in notes or "expected client" in notes:
            return REQUEST_TYPE_ADVANCE
        return REQUEST_TYPE_SPECIAL


    def life_status_text(value):
        return str(value or "").strip().lower()


    def life_is_rejected(value):
        text = life_status_text(value)
        return "reject" in text or "cancel" in text or "stop" in text


    def life_is_released(value):
        text = life_status_text(value)
        return (
            "release" in text or
            "deliver" in text or
            "transit" in text or
            "receive" in text or
            "complete" in text
        )


    def life_is_approved(value):
        return "approv" in life_status_text(value)


    def life_request_group(row):
        transfer_status = row.get("transfer_status") or ""
        workflow_state = row.get("workflow_state") or ""
        custom_status = row.get("custom_stock_request_status") or ""
        erp_status = row.get("status") or ""

        if life_is_released(transfer_status) or life_is_released(custom_status):
            return "released"
        if life_is_rejected(workflow_state) or life_is_rejected(custom_status) or life_is_rejected(erp_status):
            return "rejected"
        if life_is_approved(workflow_state) or life_is_approved(custom_status):
            return "approved"
        return "pending"


    def life_transition_next_state(transition):
        if not transition:
            return ""
        return str(
            transition.get("next_state") or
            transition.get("next_workflow_state") or
            transition.get("workflow_state") or
            ""
        ).strip()


    def life_apply_workflow_state(doc, target_state):
        target_state = str(target_state or "").strip()
        if not target_state:
            frappe.throw("Target workflow state is required.")

        doc.reload()
        current_state = str(doc.get("workflow_state") or "").strip()
        if current_state.lower() == target_state.lower():
            return doc

        transitions = life_gateway_workflow_get_transitions(doc) or []

        selected_action = ""
        available = []
        for transition in transitions:
            action_name = str(transition.get("action") or "").strip()
            next_state = life_transition_next_state(transition)
            if action_name:
                available.append(action_name + " -> " + next_state)
            if next_state.lower() == target_state.lower():
                selected_action = action_name
                break

        if not selected_action:
            frappe.throw(
                "No permitted workflow transition moves " +
                (current_state or "Draft") + " to " + target_state +
                ". Available transitions: " + (", ".join(available) or "None")
            )

        result = life_gateway_workflow_apply(
            doc,
            selected_action
        )

        updated_name = doc.name
        if isinstance(result, dict) and result.get("name"):
            updated_name = result.get("name")

        updated = frappe.get_doc(doc.doctype, updated_name)
        final_state = str(updated.get("workflow_state") or "").strip()
        if final_state.lower() != target_state.lower():
            frappe.throw(
                "Workflow action completed, but the document is in " +
                (final_state or "Blank") + " instead of " + target_state + "."
            )
        return updated


    def life_apply_receipt_submit(stock_entry):
        stock_entry.reload()
        transitions = life_gateway_workflow_get_transitions(stock_entry) or []
        if not transitions:
            frappe.throw("No branch receipt workflow action is available.")

        state_docstatus = {}
        workflows = frappe.get_all(
            "Workflow",
            filters={"document_type": SE_DOCTYPE, "is_active": 1},
            fields=["name"],
            page_length=1
        )
        if workflows:
            workflow_doc = frappe.get_doc("Workflow", workflows[0].get("name"))
            for state_row in workflow_doc.get("states") or []:
                state_docstatus[str(state_row.get("state") or "")] = life_int(state_row.get("doc_status"), 0)

        preferred_words = ["approve", "receive", "receipt", "confirm"]
        selected_action = ""
        fallback_action = ""
        available = []

        for transition in transitions:
            action_name = str(transition.get("action") or "").strip()
            next_state = life_transition_next_state(transition)
            next_docstatus = life_int(state_docstatus.get(next_state), -1)
            if action_name:
                available.append(action_name)
            if next_docstatus == 1 and not fallback_action:
                fallback_action = action_name
            if next_docstatus == 1:
                action_lower = action_name.lower()
                for word in preferred_words:
                    if word in action_lower:
                        selected_action = action_name
                        break
            if selected_action:
                break

        if not selected_action:
            selected_action = fallback_action

        if not selected_action:
            frappe.throw(
                "No receipt workflow action submits the Stock Entry. Available actions: " +
                (", ".join(available) or "None")
            )

        result = life_gateway_workflow_apply(
            stock_entry,
            selected_action
        )

        updated_name = stock_entry.name
        if isinstance(result, dict) and result.get("name"):
            updated_name = result.get("name")

        submitted = frappe.get_doc(SE_DOCTYPE, updated_name)
        if life_int(submitted.docstatus, 0) != 1:
            frappe.throw(
                "The receipt workflow action " + selected_action +
                " did not submit the Stock Entry."
            )
        return submitted


    def life_requester_name_map(requester_ids):
        name_map = {}
        clean_ids = []
        for value in requester_ids:
            key = str(value or "").strip()
            if key and key not in clean_ids:
                clean_ids.append(key)

        if not clean_ids:
            return name_map

        employee_meta = frappe.get_meta("Employee")
        employee_fields = ["name", "employee_name"]
        if employee_meta.get_field("user_id"):
            employee_fields.append("user_id")

        employees = frappe.get_all(
            "Employee",
            filters={"name": ["in", clean_ids]},
            fields=employee_fields,
            page_length=len(clean_ids)
        )
        for employee in employees:
            display = employee.get("employee_name") or employee.get("name")
            if employee.get("name"):
                name_map[employee.get("name")] = display
            if employee.get("user_id"):
                name_map[employee.get("user_id")] = display

        if employee_meta.get_field("user_id"):
            employees_by_user = frappe.get_all(
                "Employee",
                filters={"user_id": ["in", clean_ids]},
                fields=employee_fields,
                page_length=len(clean_ids)
            )
            for employee in employees_by_user:
                display = employee.get("employee_name") or employee.get("name")
                if employee.get("name"):
                    name_map[employee.get("name")] = display
                if employee.get("user_id"):
                    name_map[employee.get("user_id")] = display

        users = frappe.get_all(
            "User",
            filters={"name": ["in", clean_ids]},
            fields=["name", "full_name", "first_name", "last_name"],
            page_length=len(clean_ids)
        )
        for user in users:
            user_id = user.get("name")
            full_name = str(user.get("full_name") or "").strip()
            if not full_name:
                full_name = (
                    str(user.get("first_name") or "").strip() + " " +
                    str(user.get("last_name") or "").strip()
                ).strip()
            if user_id and full_name:
                name_map[user_id] = full_name

        return name_map


    def life_parent_fields():
        meta = frappe.get_meta(MR_DOCTYPE)
        fields = ["name", "creation", "modified", "owner", "docstatus"]
        candidates = [
            "transaction_date", "schedule_date", "title", "status",
            "workflow_state", "transfer_status", "material_request_type",
            "custom_stock_request_type", "custom_request_type",
            "custom_stock_request_status", "custom_stock_entry_reference",
            "custom_store_manager_instructions", "custom_store_manager_remarks",
            "custom_client_name", "custom_therapy_id", "custom_priority",
            "custom_additional_notes", "custom_reasonjustification",
            "custom_material_request_by", "set_from_warehouse", "set_warehouse",
            "company", "per_ordered", "per_received"
        ]
        for fieldname in candidates:
            if meta.get_field(fieldname) and fieldname not in fields:
                fields.append(fieldname)
        return fields


    def life_child_fields():
        meta = frappe.get_meta(MR_ITEM_DOCTYPE)
        fields = ["name", "parent", "idx"]
        candidates = [
            "item_code", "item_name", "description", "qty", "uom", "stock_uom",
            "conversion_factor", "warehouse", "from_warehouse", "schedule_date",
            "custom_approved_qty", "cost_center", "project",
            "custom_client_name", "custom_package_number"
        ]
        for fieldname in candidates:
            if meta.get_field(fieldname) and fieldname not in fields:
                fields.append(fieldname)
        return fields


    def life_material_summary(items):
        parts = []
        for item in items or []:
            item_label = item.get("item_name") or item.get("item_code") or "Material"
            qty = life_float(item.get("qty"), 0)
            qty_text = str(qty)
            if qty_text.endswith(".0"):
                qty_text = qty_text[0:len(qty_text) - 2]
            parts.append(str(item_label) + " ×" + qty_text)
        return ", ".join(parts) if parts else "—"


    def life_prepare_request_rows(permitted_names, selected_names):
        if not selected_names:
            return []

        parent_rows = frappe.get_all(
            MR_DOCTYPE,
            filters={"name": ["in", selected_names]},
            fields=life_parent_fields(),
            page_length=len(selected_names)
        )
        parent_map = {}
        for row in parent_rows:
            if row.get("name"):
                parent_map[row.get("name")] = row

        child_rows = frappe.get_all(
            MR_ITEM_DOCTYPE,
            filters={
                "parent": ["in", selected_names],
                "parenttype": MR_DOCTYPE
            },
            fields=life_child_fields(),
            order_by="parent asc, idx asc",
            page_length=10000
        )
        items_by_parent = {}
        for item in child_rows:
            parent_name = item.get("parent")
            if parent_name:
                if not items_by_parent.get(parent_name):
                    items_by_parent[parent_name] = []
                items_by_parent.get(parent_name).append(item)

        requester_ids = []
        for name in selected_names:
            row = parent_map.get(name)
            if row:
                requester_id = row.get("custom_material_request_by") or row.get("owner")
                requester_id = str(requester_id or "").strip()
                if requester_id and requester_id not in requester_ids:
                    requester_ids.append(requester_id)

        requester_map = life_requester_name_map(requester_ids)
        ordered_rows = []
        for request_name in selected_names:
            row = parent_map.get(request_name)
            if not row:
                continue
            items = items_by_parent.get(request_name) or []
            requester_id = str(
                row.get("custom_material_request_by") or row.get("owner") or ""
            ).strip()
            requester_display = requester_map.get(requester_id)
            if not requester_display:
                requester_display = requester_id.split("@")[0] if "@" in requester_id else requester_id

            row.update({
                "items": items,
                "_home_items": items,
                "_home_materials": life_material_summary(items),
                "_requested_by_name": requester_display or "—",
                "_homeHydrated": True,
                "branch": life_branch_from_warehouse(row.get("set_warehouse")),
                "_group": life_request_group(row)
            })
            ordered_rows.append(row)
        return ordered_rows


    def life_action_get_context(payload):
        user = life_require_login()
        employee = life_current_employee()
        roles = life_user_roles()
        return {
            "ok": True,
            "user": user,
            "roles": roles,
            "is_ho": life_is_ho_user(),
            "employee": employee,
            "branch": employee.get("branch") if employee else "",
            "company": employee.get("company") if employee else "",
            "allowed_warehouses": life_allowed_request_warehouses()
        }


    def life_action_check_setup(payload):
        life_require_login()
        required = {
            MR_DOCTYPE: [
                "custom_stock_request_type",
                "custom_stock_request_status",
                "custom_store_manager_approval_required",
                "custom_material_request_by"
            ],
            MR_ITEM_DOCTYPE: ["custom_approved_qty"],
            SE_DOCTYPE: [
                "custom_stock_release_remarks",
                "custom_sending_method",
                "custom_delivery_reference",
                "custom_stock_released_by",
                "custom_stock_release_date",
                "custom_delivery_challan_photo_1",
                "custom_delivery_challan_photo_2",
                "custom_delivery_challan_photo_3",
                "custom_received_by",
                "custom_received_date",
                "custom_branch_receipt_remarks"
            ],
            SE_ITEM_DOCTYPE: ["custom_received_qty"]
        }
        missing = {}
        for doctype in required:
            absent = []
            for fieldname in required.get(doctype):
                if not life_has_field(doctype, fieldname):
                    absent.append(fieldname)
            if absent:
                missing[doctype] = absent

        mr_workflows = frappe.get_all(
            "Workflow",
            filters={"document_type": MR_DOCTYPE, "is_active": 1},
            fields=["name"],
            page_length=1
        )
        se_workflows = frappe.get_all(
            "Workflow",
            filters={"document_type": SE_DOCTYPE, "is_active": 1},
            fields=["name"],
            page_length=1
        )

        approved_field = frappe.get_meta(MR_ITEM_DOCTYPE).get_field("custom_approved_qty")
        allow_on_submit = bool(approved_field and life_int(approved_field.allow_on_submit, 0) == 1)

        return {
            "ok": not bool(missing) and allow_on_submit,
            "missing_fields": missing,
            "approved_qty_allow_on_submit": allow_on_submit,
            "active_material_request_workflow": mr_workflows[0].get("name") if mr_workflows else "",
            "active_stock_entry_workflow": se_workflows[0].get("name") if se_workflows else ""
        }


    def life_action_list_requests(payload):
        life_require_login()

        view = str(
            life_arg(payload, "view", "ho") or "ho"
        ).strip().lower()

        branch = str(
            life_arg(payload, "branch", "") or ""
        ).strip()

        group = str(
            life_arg(payload, "group", "") or ""
        ).strip().lower()

        page = max(
            1,
            life_int(
                life_arg(payload, "page", 1),
                1
            )
        )

        limit = life_int(
            life_arg(payload, "limit", 200),
            200
        )
        limit = min(500, max(1, limit))

        page_size_raw = life_arg(
            payload,
            "page_size",
            None
        )

        if page_size_raw is None or page_size_raw == "":
            page_size = limit
        else:
            page_size = min(
                200,
                max(
                    1,
                    life_int(page_size_raw, 10)
                )
            )

        filters = [["docstatus", "<", 2]]

        # ============================================================
        # BRANCH VIEW
        # ============================================================
        if view == "branch":
            if not branch:
                employee = life_current_employee()
                branch = str(
                    employee.get("branch") or ""
                ).strip() if employee else ""

            if not branch:
                frappe.throw(
                    "Branch could not be resolved for the logged-in user."
                )

            filters.append(
                [
                    "set_warehouse",
                    "like",
                    "%" + branch + "%"
                ]
            )

            # Branch users continue to respect normal ERPNext permissions.
            headers = frappe.get_list(
                MR_DOCTYPE,
                filters=filters,
                fields=["name"],
                order_by="modified desc",
                limit_start=0,
                limit_page_length=limit
            )

        # ============================================================
        # HO / STOCK MANAGER VIEW
        # ============================================================
        else:
            # Important security gate before bypassing branch permissions.
            life_require_ho()

            # HO / Stock Manager needs requests from every branch.
            headers = frappe.get_all(
                MR_DOCTYPE,
                filters=filters,
                fields=["name"],
                order_by="modified desc",
                limit_start=0,
                limit_page_length=limit
            )

        # ============================================================
        # COMMON PROCESSING FOR BOTH BRANCH AND HO
        # ============================================================
        permitted_names = []
        for header in headers:
            name = header.get("name")
            if name:
                permitted_names.append(name)

        if not permitted_names:
            return {
                "ok": True,
                "rows": [],
                "counts": {
                    "pending": 0,
                    "approved": 0,
                    "released": 0,
                    "rejected": 0
                },
                "total": 0,
                "total_pages": 1,
                "page": page,
                "page_size": page_size,
                "view": view,
                "branch": branch,
                "group": group or "all",
                "limit": limit
            }

        status_fields = [
            "name",
            "workflow_state",
            "status",
            "docstatus"
        ]

        parent_meta = frappe.get_meta(MR_DOCTYPE)
        for fieldname in [
            "transfer_status",
            "custom_stock_request_status"
        ]:
            if parent_meta.get_field(fieldname):
                status_fields.append(fieldname)

        status_rows = frappe.get_all(
            MR_DOCTYPE,
            filters={"name": ["in", permitted_names]},
            fields=status_fields,
            page_length=len(permitted_names)
        )

        status_map = {}
        counts = {
            "pending": 0,
            "approved": 0,
            "released": 0,
            "rejected": 0
        }

        for row in status_rows:
            row_group = life_request_group(row)
            row.update({"_group": row_group})
            status_map[row.get("name")] = row
            counts[row_group] = counts.get(row_group, 0) + 1

        selected_names = []
        for name in permitted_names:
            status_row = status_map.get(name)
            row_group = status_row.get("_group") if status_row else "pending"

            if group in ["pending", "approved", "released", "rejected"]:
                if row_group == group:
                    selected_names.append(name)
            else:
                selected_names.append(name)

        total = len(selected_names)
        start = (page - 1) * page_size
        page_names = selected_names[start:start + page_size]

        rows = life_prepare_request_rows(
            permitted_names,
            page_names
        )

        return {
            "ok": True,
            "rows": rows,
            "counts": counts,
            "total": total,
            "total_pages": max(
                1,
                int((total + page_size - 1) / page_size)
            ),
            "page": page,
            "page_size": page_size,
            "view": view,
            "branch": branch,
            "group": group or "all",
            "limit": limit
        }


    def life_action_get_request(payload):
        life_require_login()
        request_name = str(
            life_arg(payload, "name", "") or
            life_arg(payload, "request_name", "") or
            life_arg(payload, "material_request", "") or
            ""
        ).strip()
        if not request_name:
            frappe.throw("Material Request name is required.")

        doc = frappe.get_doc(MR_DOCTYPE, request_name)
        doc.check_permission("read")
        rows = life_prepare_request_rows([request_name], [request_name])
        summary = rows[0] if rows else {}
        return {
            "ok": True,
            "request": doc.as_dict(),
            "summary": summary
        }


    def life_action_get_stock_availability(payload):
        life_require_ho()
        request_name = str(
            life_arg(payload, "request_name", "") or
            life_arg(payload, "material_request", "") or
            ""
        ).strip()
        if not request_name:
            frappe.throw("Material Request name is required.")

        doc = frappe.get_doc(MR_DOCTYPE, request_name)
        doc.check_permission("read")
        item_codes = []
        for item in doc.get("items") or []:
            code = str(item.get("item_code") or "").strip()
            if code and code not in item_codes:
                item_codes.append(code)

        if not item_codes:
            return {
                "ok": True,
                "request_name": request_name,
                "target_warehouse": doc.get("set_warehouse"),
                "rows": []
            }

        bins = frappe.get_all(
            "Bin",
            filters={"item_code": ["in", item_codes]},
            fields=["item_code", "warehouse", "actual_qty", "reserved_qty", "projected_qty"],
            order_by="item_code asc, actual_qty desc",
            page_length=10000
        )
        rows = []
        for row in bins:
            if row.get("warehouse") == doc.get("set_warehouse"):
                continue
            actual_qty = life_float(row.get("actual_qty"), 0)
            reserved_qty = life_float(row.get("reserved_qty"), 0)
            rows.append({
                "item_code": row.get("item_code"),
                "warehouse": row.get("warehouse"),
                "actual_qty": actual_qty,
                "reserved_qty": reserved_qty,
                "available_qty": max(0, actual_qty - reserved_qty),
                "projected_qty": life_float(row.get("projected_qty"), 0)
            })

        return {
            "ok": True,
            "request_name": request_name,
            "target_warehouse": doc.get("set_warehouse"),
            "rows": rows
        }



    def life_action_get_item_stock_availability(payload):
        life_require_login()

        item_code = str(
            life_arg(payload, "item_code", "") or
            life_arg(payload, "item", "") or
            ""
        ).strip()

        if not item_code:
            frappe.throw("Item Code is required.")

        company = str(
            life_arg(payload, "company", "") or
            COMPANY_FALLBACK
        ).strip()

        source_warehouse = str(
            life_arg(payload, "source_warehouse", "") or
            ""
        ).strip()

        target_warehouse = str(
            life_arg(payload, "target_warehouse", "") or
            ""
        ).strip()

        requested_branch = str(
            life_arg(payload, "branch", "") or
            ""
        ).strip()

        if life_is_ho_user():
            branch = requested_branch
        else:
            employee = life_current_employee()
            branch = str(
                employee.get("branch") if employee else ""
            ).strip()

        if not branch and target_warehouse:
            branch = life_branch_from_warehouse(target_warehouse)

        warehouse_rows = frappe.get_all(
            "Warehouse",
            filters={
                "company": company,
                "is_group": 0
            },
            fields=["name"],
            order_by="name asc",
            page_length=10000
        )

        warehouse_names = []
        for warehouse_row in warehouse_rows:
            warehouse_name = str(
                warehouse_row.get("name") or ""
            ).strip()

            if warehouse_name:
                warehouse_names.append(warehouse_name)

        bin_filters = {
            "item_code": item_code
        }

        if warehouse_names:
            bin_filters["warehouse"] = ["in", warehouse_names]

        bins = frappe.get_all(
            "Bin",
            filters=bin_filters,
            fields=[
                "item_code",
                "warehouse",
                "actual_qty",
                "reserved_qty",
                "projected_qty",
                "ordered_qty",
                "planned_qty",
                "indented_qty"
            ],
            order_by="actual_qty desc, warehouse asc",
            page_length=10000
        )

        rows = []
        branch_qty = 0
        ho_qty = 0
        total_qty = 0
        total_available_qty = 0

        source_key = life_normalize_key(source_warehouse)

        for bin_row in bins:
            warehouse = str(
                bin_row.get("warehouse") or ""
            ).strip()

            if not warehouse:
                continue

            actual_qty = life_float(
                bin_row.get("actual_qty"),
                0
            )

            reserved_qty = life_float(
                bin_row.get("reserved_qty"),
                0
            )

            available_qty = actual_qty - reserved_qty
            projected_qty = life_float(
                bin_row.get("projected_qty"),
                available_qty
            )

            total_qty = total_qty + actual_qty
            total_available_qty = total_available_qty + available_qty

            is_branch_warehouse = False

            if target_warehouse and warehouse == target_warehouse:
                is_branch_warehouse = True
            elif branch and life_warehouse_matches_branch(
                warehouse,
                branch
            ):
                is_branch_warehouse = True

            warehouse_key = life_normalize_key(warehouse)
            is_ho_warehouse = False

            if source_key and warehouse_key == source_key:
                is_ho_warehouse = True
            elif (
                "stores" in warehouse_key or
                "headoffice" in warehouse_key or
                "central" in warehouse_key or
                warehouse_key.startswith("ho")
            ):
                is_ho_warehouse = True

            if is_branch_warehouse:
                branch_qty = branch_qty + actual_qty

            if is_ho_warehouse:
                ho_qty = ho_qty + actual_qty

            rows.append({
                "item_code": item_code,
                "warehouse": warehouse,
                "actual_qty": actual_qty,
                "reserved_qty": reserved_qty,
                "available_qty": available_qty,
                "projected_qty": projected_qty,
                "ordered_qty": life_float(
                    bin_row.get("ordered_qty"),
                    0
                ),
                "planned_qty": life_float(
                    bin_row.get("planned_qty"),
                    0
                ),
                "indented_qty": life_float(
                    bin_row.get("indented_qty"),
                    0
                ),
                "is_branch_warehouse": 1 if is_branch_warehouse else 0,
                "is_ho_warehouse": 1 if is_ho_warehouse else 0
            })

        return {
            "ok": True,
            "item_code": item_code,
            "company": company,
            "branch": branch,
            "source_warehouse": source_warehouse,
            "target_warehouse": target_warehouse,
            "branch_qty": branch_qty,
            "ho_qty": ho_qty,
            "total_qty": total_qty,
            "total_available_qty": total_available_qty,
            "rows": rows
        }


    def life_normalize_attachments(value, maximum):
        if not value:
            return []
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, list):
            frappe.throw("Attachments must be an array.")
        if len(value) > maximum:
            frappe.throw("A maximum of " + str(maximum) + " attachments is allowed.")

        rows = []
        index = 0
        for item in value:
            index = index + 1
            if isinstance(item, str):
                item = {"file_url": item}
            if not isinstance(item, dict):
                frappe.throw("Attachment " + str(index) + " is invalid.")
            file_url = str(
                item.get("file_url") or item.get("url") or item.get("attachment") or ""
            ).strip()
            if not file_url:
                frappe.throw("Attachment " + str(index) + " has no File URL.")
            rows.append({
                "file_url": file_url,
                "label": str(
                    item.get("label") or item.get("document_name") or
                    ("Attachment " + str(index))
                ).strip(),
                "slot_number": max(1, life_int(item.get("slot_number"), index))
            })
        return rows


    def life_validate_file_access(file_url):
        """Validate that a file exists and is accessible to the current user."""

        if not file_url:
            return True

        file_url = str(file_url).strip()

        # Strategy 1: Exact file_url match
        try:
            file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
            if file_name:
                return True
        except Exception:
            pass

        # Strategy 2: Match by file_name (extract from URL)
        try:
            file_name_part = file_url.split("/")[-1].split("?")[0]
            file_name = frappe.db.get_value("File", {"file_name": file_name_part}, "name")
            if file_name:
                return True
        except Exception:
            pass

        # Strategy 3: Clean URL (remove /files/ prefix)
        try:
            clean_url = file_url.replace("/files/", "")
            file_name = frappe.db.get_value("File", {"file_url": clean_url}, "name")
            if file_name:
                return True
        except Exception:
            pass

        # Strategy 4: Search using LIKE with proper Frappe syntax
        try:
            file_name_part = file_url.split("/")[-1].split("?")[0]
            # Use the correct Frappe filter syntax for LIKE
            files = frappe.db.get_list(
                "File",
                filters={"file_url": ["like", f"%{file_name_part}%"]},
                fields=["name"],
                limit_page_length=1
            )
            if files and len(files) > 0:
                return True
        except Exception:
            pass

        # Strategy 5: Check if the file exists in the filesystem
        try:
            file_path = file_url
            if file_path.startswith("/files/"):
                file_path = file_path[7:]  # Remove "/files/"

            import os
            private_path = os.path.join(frappe.get_site_path("private", "files"), file_path)
            public_path = os.path.join(frappe.get_site_path("public", "files"), file_path)

            if os.path.exists(private_path) or os.path.exists(public_path):
                # File exists on disk, create a File record for it
                try:
                    new_file = frappe.get_doc({
                        "doctype": "File",
                        "file_url": file_url,
                        "file_name": file_url.split("/")[-1],
                    })
                    new_file.insert(ignore_permissions=True)
                    return True
                except Exception:
                    pass
                return True
        except Exception:
            pass

        # If all strategies fail, raise a clear error
        frappe.throw(
            f"Uploaded file was not found: {file_url}. Please ensure the file upload completed successfully and try again."
        )


    def life_attach_request_files(request_name, attachments):
        """Attach files to a Material Request document."""

        if not attachments:
            return

        attached_count = 0

        for attachment in attachments:
            file_url = attachment.get("file_url")
            label = attachment.get("label", "Attachment")

            if not file_url:
                continue

            try:
                # Check if this file is already attached to this request
                existing = frappe.db.get_value(
                    "File",
                    {
                        "attached_to_doctype": "Material Request",
                        "attached_to_name": request_name,
                        "file_url": file_url
                    },
                    "name"
                )

                if existing:
                    # File already attached, skip
                    continue

                # First validate the file exists
                if not life_validate_file_access(file_url):
                    continue

                # Create the attachment record
                file_doc = frappe.get_doc({
                    "doctype": "File",
                    "file_url": file_url,
                    "attached_to_doctype": "Material Request",
                    "attached_to_name": request_name,
                    "attached_to_field": "custom_treatment_card_attachments",
                    "file_name": label or file_url.split("/")[-1]
                })
                file_doc.insert(ignore_permissions=True)
                attached_count += 1

            except Exception as e:
                # Log error with truncated message to avoid character length issues
                error_msg = str(e)[:100]  # Truncate to prevent Error Log length error
                frappe.log_error(
                    f"Failed to attach file to {request_name}: {error_msg}",
                    "LIFE Stock Attach Request Files"
                )
                # Continue with other files - don't fail the entire submission

        return attached_count

    def life_validate_item_for_request(item, source, target, schedule_date):
        if not isinstance(item, dict):
            frappe.throw("A Material Request item row is invalid.")

        item_code = str(item.get("item_code") or "").strip()
        if not item_code:
            frappe.throw("Every Material Request row requires an Item Code.")

        item_rows = frappe.get_all(
            "Item",
            filters={"name": item_code},
            fields=["name", "item_code", "item_name", "item_group", "stock_uom", "disabled", "is_stock_item"],
            page_length=1
        )
        if not item_rows:
            frappe.throw("Item " + item_code + " does not exist.")
        item_master = item_rows[0]
        if life_int(item_master.get("disabled"), 0) == 1:
            frappe.throw("Item " + item_code + " is disabled.")
        if life_int(item_master.get("is_stock_item"), 0) != 1:
            frappe.throw("Item " + item_code + " is not a stock item.")

        group_text = str(item_master.get("item_group") or "").strip().lower()
        if group_text in ["asset", "assets", "service", "services"]:
            frappe.throw("Assets and Services cannot be requested as stock: " + item_code)

        qty = life_float(item.get("qty"), 0)
        if qty <= 0:
            frappe.throw("Requested quantity for " + item_code + " must be greater than zero.")

        row = {
            "item_code": item_code,
            "qty": qty,
            "schedule_date": item.get("schedule_date") or schedule_date,
            "from_warehouse": source,
            "warehouse": target
        }

        item_meta = frappe.get_meta(MR_ITEM_DOCTYPE)
        for fieldname in [
            "description", "cost_center", "project", "custom_client_name",
            "custom_package_number", "uom", "stock_uom", "conversion_factor"
        ]:
            if item_meta.get_field(fieldname) and item.get(fieldname) is not None:
                row[fieldname] = item.get(fieldname)
        return row


    def life_action_submit_request(payload):
        life_require_login()
        request_doc = payload.get("request_doc") or payload.get("document") or payload
        if isinstance(request_doc, str):
            request_doc = json.loads(request_doc)
        if not isinstance(request_doc, dict):
            frappe.throw("request_doc must be a JSON object.")

        request_type = str(
            request_doc.get("custom_stock_request_type") or
            request_doc.get("custom_request_type") or ""
        ).strip()
        if request_type not in ALLOWED_REQUEST_TYPES:
            frappe.throw(
                "Request Type must be Special Material Request, Advance Material Request, or Monthly Indent Request."
            )

        attachments = life_normalize_attachments(payload.get("attachments") or [], 15)

        # Consumable / Special Material Request:
        # only Slot 1 and Slot 2 are mandatory.
        if request_type == REQUEST_TYPE_SPECIAL:
            present_slots = []
            for row in attachments:
                slot_number = life_int(row.get("slot_number"), 0)
                if slot_number > 0 and slot_number not in present_slots:
                    present_slots.append(slot_number)

            missing_slots = []
            for slot_number in [1, 2]:
                if slot_number not in present_slots:
                    missing_slots.append(slot_number)

            if missing_slots:
                frappe.throw(
                    "Mandatory attachment slots are missing: " +
                    ", ".join([str(value) for value in missing_slots])
                )

        # Advance Material Request keeps its own independent validation.
        elif request_type == REQUEST_TYPE_ADVANCE:
            present_slots = []
            for row in attachments:
                slot_number = life_int(row.get("slot_number"), 0)
                if slot_number > 0 and slot_number not in present_slots:
                    present_slots.append(slot_number)

            if 1 not in present_slots:
                frappe.throw(
                    "Mandatory attachment slot 1 (Walk-In Form / Client Details) is missing."
                )

        if not life_has_field(MR_DOCTYPE, "custom_stock_request_type"):
            frappe.throw("Create Material Request.custom_stock_request_type first.")
        if not life_has_field(MR_DOCTYPE, "custom_stock_request_status"):
            frappe.throw("Create Material Request.custom_stock_request_status first.")
        if not life_has_field(MR_DOCTYPE, "custom_store_manager_approval_required"):
            frappe.throw("Create Material Request.custom_store_manager_approval_required first.")

        source = str(request_doc.get("set_from_warehouse") or "").strip()
        target = str(request_doc.get("set_warehouse") or "").strip()
        if not source or not target:
            frappe.throw("Source Warehouse and Target Warehouse are required.")
        if source == target:
            frappe.throw("Source Warehouse and Target Warehouse cannot be the same.")
        life_require_branch_warehouse(target, "Target Warehouse")

        transaction_date = request_doc.get("transaction_date") or frappe.utils.nowdate()
        schedule_date = request_doc.get("schedule_date")
        if not schedule_date:
            frappe.throw("Required By date is mandatory.")
        if frappe.utils.get_datetime(schedule_date) < frappe.utils.get_datetime(transaction_date):
            frappe.throw("Required By cannot be before Request Date.")

        items = request_doc.get("items") or []
        if not isinstance(items, list) or not items:
            frappe.throw("Add at least one stock item.")

        doc = frappe.new_doc(MR_DOCTYPE)
        parent_meta = frappe.get_meta(MR_DOCTYPE)
        parent_fields = [
            "naming_series", "title", "company", "custom_store_manager_instructions",
            "custom_requested_consumable_amount", "custom_coo_notification_required",
            "custom_coo_notification_status", "custom_client_name", "custom_therapy_id",
            "custom_material_request_by", "custom_total_billed", "custom_total_paid",
            "custom_outstanding_amount", "custom_priority", "custom_reasonjustification",
            "custom_additional_notes", "custom_expected_client_name",
            "custom_expected_client_phone", "custom_expected_joining_date",
            "custom_expected_treatment_category", "custom_expected_sessions",
            "custom_existing_life_client", "custom_previous_branch",
            "custom_recent_walkin_client", "custom_sales_cluster_head",
            "custom_cluster_head_approval_confirmed", "custom_stock_unavailable_declaration",
            "custom_records_maintenance_declaration", "custom_stock_responsibility_declaration",
            "custom_monthly_indent_confirmed", "custom_general_branch_consumption_confirmed"
        ]
        for fieldname in parent_fields:
            if parent_meta.get_field(fieldname) and request_doc.get(fieldname) is not None:
                doc.set(fieldname, request_doc.get(fieldname))

        doc.material_request_type = "Material Transfer"
        doc.transaction_date = transaction_date
        doc.schedule_date = schedule_date
        doc.company = request_doc.get("company") or COMPANY_FALLBACK
        doc.custom_stock_request_type = request_type
        doc.custom_stock_request_status = MR_PENDING_STATE
        doc.custom_store_manager_approval_required = 1
        doc.set_from_warehouse = source
        doc.set_warehouse = target

        if not doc.get("custom_material_request_by"):
            employee = life_current_employee()
            if employee and life_has_field(MR_DOCTYPE, "custom_material_request_by"):
                doc.custom_material_request_by = employee.get("name")

        if not doc.get("title"):
            doc.title = request_type + " - " + (life_branch_from_warehouse(target) or target)

        for item in items:
            doc.append(
                "items",
                life_validate_item_for_request(item, source, target, schedule_date)
            )

        therapy_field = "custom_special_material_request_details"
        therapy_details = request_doc.get(therapy_field) or request_doc.get("therapy_details") or []
        if therapy_details and parent_meta.get_field(therapy_field):
            if not isinstance(therapy_details, list):
                frappe.throw("Therapy Details must be an array.")
            child_doctype = str(parent_meta.get_field(therapy_field).options or "")
            child_meta = frappe.get_meta(child_doctype) if child_doctype else None
            for detail in therapy_details:
                if not isinstance(detail, dict):
                    frappe.throw("A Therapy Detail row is invalid.")
                row = {}
                for fieldname in [
                    "therapy_plan", "therapy_detail_row", "therapy_type", "sales_invoices",
                    "branch", "booked_sessions", "completed_sessions", "remaining_sessions"
                ]:
                    if child_meta and child_meta.get_field(fieldname) and detail.get(fieldname) is not None:
                        row[fieldname] = detail.get(fieldname)
                doc.append(therapy_field, row)

        doc.insert()
        if attachments:
            life_attach_request_files(doc, attachments)
            doc.reload()

        doc = life_apply_workflow_state(doc, MR_PENDING_STATE)
        rows = life_prepare_request_rows([doc.name], [doc.name])
        return {
            "ok": True,
            "message": "Material Request " + doc.name + " submitted for Store Manager review.",
            "request": rows[0] if rows else doc.as_dict()
        }


    def life_find_request_item(items, approval):
        row_name = str(
            approval.get("item_row_name") or approval.get("row_name") or ""
        ).strip()
        item_code = str(approval.get("item_code") or "").strip()
        item_idx = life_int(approval.get("item_idx"), 0)

        if row_name:
            for item in items:
                if str(item.name or "") == row_name:
                    return item
        if item_idx:
            for item in items:
                if life_int(item.idx, 0) == item_idx:
                    if not item_code or str(item.item_code or "") == item_code:
                        return item
        if item_code:
            matches = []
            for item in items:
                if str(item.item_code or "") == item_code:
                    matches.append(item)
            if len(matches) == 1:
                return matches[0]
        return None


    def life_bin_usable(item_code, warehouse):
        rows = frappe.get_all(
            "Bin",
            filters={"item_code": item_code, "warehouse": warehouse},
            fields=["actual_qty", "reserved_qty"],
            page_length=1
        )
        if not rows:
            return 0
        actual_qty = life_float(rows[0].get("actual_qty"), 0)
        reserved_qty = life_float(rows[0].get("reserved_qty"), 0)
        return max(0, actual_qty - reserved_qty)


    def life_manager_remarks_field():
        for fieldname in [
            "custom_store_manager_remarks",
            "custom_store_manager_instructions",
            "custom_approval_remarks"
        ]:
            if life_has_field(MR_DOCTYPE, fieldname):
                return fieldname
        return ""


    def life_validate_approval_rows(material_request, approvals):
        approved_field = frappe.get_meta(MR_ITEM_DOCTYPE).get_field("custom_approved_qty")
        if not approved_field:
            frappe.throw("Create Material Request Item.custom_approved_qty as a Float field.")
        if life_int(approved_field.allow_on_submit, 0) != 1:
            frappe.throw("Enable Allow on Submit for Material Request Item.custom_approved_qty.")

        items = list(material_request.get("items") or [])
        if not items:
            frappe.throw("No Material Request Item rows were found.")
        if not isinstance(approvals, list) or not approvals:
            frappe.throw("Approval quantities are required.")

        target = str(material_request.get("set_warehouse") or "").strip()
        if not target:
            frappe.throw("Target Warehouse is missing on the Material Request.")

        resolved = []
        demand = {}
        for approval in approvals:
            if not isinstance(approval, dict):
                frappe.throw("An Approval row is invalid.")
            item = life_find_request_item(items, approval)
            if not item:
                frappe.throw(
                    "Material Request Item was not found for " +
                    str(approval.get("item_code") or "a row") + "."
                )

            requested_qty = max(0, life_float(item.qty, 0))
            approved_qty = life_float(approval.get("approved_qty"), 0)
            if approved_qty < 0:
                frappe.throw("Approved Quantity cannot be negative for " + str(item.item_code) + ".")
            if approved_qty > requested_qty + 0.000001:
                frappe.throw(
                    "Approved Quantity " + str(approved_qty) +
                    " cannot exceed Requested Quantity " + str(requested_qty) +
                    " for " + str(item.item_code) + "."
                )

            source = str(approval.get("source_warehouse") or "").strip()
            conversion_factor = life_float(item.get("conversion_factor"), 1) or 1
            stock_qty = approved_qty * conversion_factor
            if approved_qty > 0:
                if not source:
                    frappe.throw("Select a Source Warehouse for " + str(item.item_code) + ".")
                if source == target:
                    frappe.throw(
                        "Source and Target Warehouse cannot be the same for " +
                        str(item.item_code) + "."
                    )
                key = str(item.item_code) + "||" + source
                demand[key] = life_float(demand.get(key), 0) + stock_qty

            resolved.append({
                "item": item,
                "item_code": item.item_code,
                "requested_qty": requested_qty,
                "approved_qty": approved_qty,
                "source_warehouse": source,
                "conversion_factor": conversion_factor,
                "stock_qty": stock_qty
            })

        positive = False
        for row in resolved:
            if row.get("approved_qty") > 0:
                positive = True
                break
        if not positive:
            frappe.throw("At least one item must have an Approved Quantity greater than zero.")

        errors = []
        for key in demand:
            parts = key.split("||", 1)
            item_code = parts[0]
            warehouse = parts[1]
            required_qty = life_float(demand.get(key), 0)
            usable = life_bin_usable(item_code, warehouse)
            if usable <= 0:
                errors.append(item_code + ": no usable stock is available in " + warehouse + ".")
            elif required_qty > usable + 0.000001:
                errors.append(
                    item_code + ": approved stock quantity " + str(required_qty) +
                    " exceeds usable stock " + str(usable) + " in " + warehouse + "."
                )

        if errors:
            frappe.throw("<br>".join(errors), title="Stock Availability Validation Failed")
        return resolved


    def life_persist_approved_qty(material_request, resolved):
        if life_int(material_request.docstatus, 0) == 0:
            for row in resolved:
                row.get("item").custom_approved_qty = row.get("approved_qty")
            material_request.save()
        else:
            for row in resolved:
                frappe.db.set_value(
                    MR_ITEM_DOCTYPE,
                    row.get("item").name,
                    "custom_approved_qty",
                    row.get("approved_qty"),
                    update_modified=False
                )

        material_request.reload()
        for row in resolved:
            saved_item = None
            for item in material_request.get("items") or []:
                if str(item.name) == str(row.get("item").name):
                    saved_item = item
                    break
            if not saved_item:
                frappe.throw("Approved Quantity row was not saved for " + str(row.get("item_code")) + ".")
            if abs(life_float(saved_item.get("custom_approved_qty"), 0) - life_float(row.get("approved_qty"), 0)) > 0.000001:
                frappe.throw("Approved Quantity was not saved for " + str(row.get("item_code")) + ".")
        return material_request


    def life_find_stock_entry(material_request, draft_only=False):
        reference = ""
        if life_has_field(MR_DOCTYPE, "custom_stock_entry_reference"):
            reference = str(material_request.get("custom_stock_entry_reference") or "").strip()
        if reference and frappe.db.exists(SE_DOCTYPE, reference):
            doc = frappe.get_doc(SE_DOCTYPE, reference)
            if not draft_only or life_int(doc.docstatus, 0) == 0:
                return doc

        rows = frappe.get_all(
            SE_ITEM_DOCTYPE,
            filters={
                "material_request": material_request.name,
                "parenttype": SE_DOCTYPE
            },
            fields=["parent"],
            page_length=500
        )
        parents = []
        for row in rows:
            parent = str(row.get("parent") or "").strip()
            if parent and parent not in parents:
                parents.append(parent)
        for parent in parents:
            doc = frappe.get_doc(SE_DOCTYPE, parent)
            if not draft_only or life_int(doc.docstatus, 0) == 0:
                return doc
        return None


    def life_create_or_refresh_stock_entry(material_request, resolved):
        positive_rows = []
        for row in resolved:
            if life_float(row.get("approved_qty"), 0) > 0:
                positive_rows.append(row)
        if not positive_rows:
            frappe.throw("No approved item is available for Stock Entry creation.")

        stock_entry = life_find_stock_entry(material_request, True)
        if stock_entry and life_int(stock_entry.docstatus, 0) != 0:
            stock_entry = None

        if not stock_entry:
            stock_entry = frappe.new_doc(SE_DOCTYPE)
            stock_entry.stock_entry_type = "Material Transfer"
            stock_entry.purpose = "Material Transfer"
            stock_entry.company = material_request.get("company") or COMPANY_FALLBACK
            stock_entry.posting_date = frappe.utils.nowdate()
        else:
            stock_entry.check_permission("write")
            stock_entry.set("items", [])

        sources = []
        for row in positive_rows:
            source = str(row.get("source_warehouse") or "")
            if source and source not in sources:
                sources.append(source)

        stock_entry.from_warehouse = sources[0] if len(sources) == 1 else ""
        stock_entry.to_warehouse = material_request.get("set_warehouse")
        stock_entry.remarks = (
            "Draft Stock Entry created from approved Material Request " +
            material_request.name + ". Pending Stock Dispatch."
        )

        se_item_meta = frappe.get_meta(SE_ITEM_DOCTYPE)
        for row in positive_rows:
            item = row.get("item")
            values = {
                "item_code": item.item_code,
                "qty": row.get("approved_qty"),
                "uom": item.get("uom") or item.get("stock_uom"),
                "stock_uom": item.get("stock_uom") or item.get("uom"),
                "conversion_factor": row.get("conversion_factor") or 1,
                "s_warehouse": row.get("source_warehouse"),
                "t_warehouse": material_request.get("set_warehouse"),
                "material_request": material_request.name,
                "material_request_item": item.name
            }
            if se_item_meta.get_field("custom_received_qty"):
                values["custom_received_qty"] = 0
            for fieldname in ["cost_center", "custom_client_name", "custom_package_number"]:
                value = item.get(fieldname) or material_request.get(fieldname)
                if value and se_item_meta.get_field(fieldname):
                    values[fieldname] = value
            stock_entry.append("items", values)

        if stock_entry.is_new():
            stock_entry.insert()
        else:
            stock_entry.save()

        life_db_set_if_field(
            MR_DOCTYPE,
            material_request.name,
            "custom_stock_entry_reference",
            stock_entry.name
        )
        return stock_entry


    def life_action_approve_request(payload):
        life_require_ho()
        request_name = str(
            payload.get("request_name") or payload.get("material_request") or ""
        ).strip()
        if not request_name:
            frappe.throw("Material Request name is required.")

        material_request = frappe.get_doc(MR_DOCTYPE, request_name)
        material_request.check_permission("read")
        if life_request_group(material_request) == "rejected":
            frappe.throw("Rejected requests cannot be approved.")

        approvals = payload.get("approvals") or []
        resolved = life_validate_approval_rows(material_request, approvals)
        remarks = str(payload.get("remarks") or "").strip()
        remarks_field = life_manager_remarks_field()
        if remarks and remarks_field:
            material_request.set(remarks_field, remarks)

        material_request = life_persist_approved_qty(material_request, resolved)
        current_state = str(material_request.get("workflow_state") or "").strip()
        if current_state.lower() != MR_APPROVED_STATE.lower():
            if life_int(material_request.docstatus, 0) == 0 and remarks and remarks_field:
                material_request.set(remarks_field, remarks)
                material_request.save()
            material_request = life_apply_workflow_state(material_request, MR_APPROVED_STATE)

        material_request = life_persist_approved_qty(material_request, resolved)
        stock_entry = life_create_or_refresh_stock_entry(material_request, resolved)
        life_db_set_if_field(
            MR_DOCTYPE,
            material_request.name,
            "custom_stock_request_status",
            MR_APPROVED_STATE
        )
        material_request.reload()

        rows = life_prepare_request_rows([material_request.name], [material_request.name])
        return {
            "ok": True,
            "message": (
                "Request " + material_request.name + " approved. Draft Stock Entry " +
                stock_entry.name + " is ready for release."
            ),
            "request": rows[0] if rows else material_request.as_dict(),
            "stock_entry": stock_entry.as_dict()
        }


    def life_action_reject_request(payload):
        life_require_ho()
        request_name = str(
            payload.get("request_name") or payload.get("material_request") or ""
        ).strip()
        remarks = str(payload.get("remarks") or "").strip()
        if not request_name:
            frappe.throw("Material Request name is required.")
        if not remarks:
            frappe.throw("Store Manager Remarks are required before rejection.")

        material_request = frappe.get_doc(MR_DOCTYPE, request_name)
        material_request.check_permission("read")
        if life_request_group(material_request) == "approved":
            frappe.throw("An approved request cannot be rejected from this action.")

        remarks_field = life_manager_remarks_field()
        if remarks_field:
            material_request.set(remarks_field, remarks)
        if life_int(material_request.docstatus, 0) == 0:
            material_request.save()

        material_request = life_apply_workflow_state(material_request, MR_REJECTED_STATE)
        life_db_set_if_field(
            MR_DOCTYPE,
            material_request.name,
            "custom_stock_request_status",
            MR_REJECTED_STATE
        )
        material_request.reload()
        rows = life_prepare_request_rows([material_request.name], [material_request.name])
        return {
            "ok": True,
            "message": "Request " + material_request.name + " rejected.",
            "request": rows[0] if rows else material_request.as_dict()
        }


    # def life_attach_urls_to_fields(doc, attachments, fieldnames):
    #     rows = life_normalize_attachments(attachments, len(fieldnames))
    #     urls = []
    #     for row in rows:
    #         file_url = row.get("file_url")
    #         file_doc = life_validate_file_access(file_url)
    #         file_doc.attached_to_doctype = doc.doctype
    #         file_doc.attached_to_name = doc.name
    #         file_doc.attached_to_field = ""
    #         file_doc.save(ignore_permissions=True)
    #         urls.append(file_url)

    #     index = 0
    #     for fieldname in fieldnames:
    #         if not life_has_field(doc.doctype, fieldname):
    #             frappe.throw("Required field " + doc.doctype + "." + fieldname + " is missing.")
    #         doc.set(fieldname, urls[index] if index < len(urls) else "")
    #         index = index + 1
    #     return urls
    def life_attach_urls_to_fields(doc, attachments, fieldnames):
        rows = life_normalize_attachments(attachments, len(fieldnames))
        urls = []

        for row in rows:
            file_url = row.get("file_url")

            if not file_url:
                continue

            # Validate that the current user is allowed to use this file.
            # This function returns True/False, not a File document.
            has_access = life_validate_file_access(file_url)

            if not has_access:
                frappe.throw("You do not have permission to use file: " + file_url)

            # Fetch the actual File document separately.
            file_name = frappe.db.get_value(
                "File",
                {"file_url": file_url},
                "name"
            )

            if not file_name:
                frappe.throw("File record was not found for: " + file_url)

            file_doc = frappe.get_doc("File", file_name)
            file_doc.attached_to_doctype = doc.doctype
            file_doc.attached_to_name = doc.name
            file_doc.attached_to_field = ""
            file_doc.save(ignore_permissions=True)

            urls.append(file_url)

        index = 0

        for fieldname in fieldnames:
            if not life_has_field(doc.doctype, fieldname):
                frappe.throw(
                    "Required field "
                    + doc.doctype
                    + "."
                    + fieldname
                    + " is missing."
                )

            if index < len(urls):
                doc.set(fieldname, urls[index])
            else:
                doc.set(fieldname, "")

            index = index + 1

        return urls


    def life_action_release_stock(payload):
        life_require_ho()
        request_name = str(
            payload.get("request_name") or payload.get("material_request") or ""
        ).strip()
        delivery_method = str(payload.get("delivery_method") or "").strip()
        delivery_reference = str(payload.get("delivery_reference") or "").strip()
        release_remarks = str(payload.get("remarks") or payload.get("release_remarks") or "").strip()
        attachments = payload.get("attachments") or []

        if not request_name:
            frappe.throw("Material Request name is required.")
        if not delivery_method:
            frappe.throw("Sending Method is mandatory.")
        if not delivery_reference:
            frappe.throw("Delivery / Person / Tracking Reference is mandatory.")
        if not attachments:
            frappe.throw("Add at least one Delivery Challan image.")

        material_request = frappe.get_doc(MR_DOCTYPE, request_name)
        material_request.check_permission("read")
        if life_request_group(material_request) != "approved":
            frappe.throw("Only approved requests pending stock release can be released.")

        stock_entry = life_find_stock_entry(material_request, True)
        if not stock_entry:
            frappe.throw("No Draft Stock Entry is linked to this approved Material Request.")
        if life_int(stock_entry.docstatus, 0) != 0:
            frappe.throw("Stock Entry " + stock_entry.name + " is no longer a draft.")

        required_fields = [
            "custom_stock_release_remarks", "custom_sending_method",
            "custom_delivery_reference", "custom_stock_released_by",
            "custom_stock_release_date", "custom_delivery_challan_photo_1",
            "custom_delivery_challan_photo_2", "custom_delivery_challan_photo_3"
        ]
        missing = []
        for fieldname in required_fields:
            if not life_has_field(SE_DOCTYPE, fieldname):
                missing.append(fieldname)
        if missing:
            frappe.throw("Create these Stock Entry fields first: " + ", ".join(missing))

        life_attach_urls_to_fields(
            stock_entry,
            attachments,
            [
                "custom_delivery_challan_photo_1",
                "custom_delivery_challan_photo_2",
                "custom_delivery_challan_photo_3"
            ]
        )

        stock_entry.custom_stock_release_remarks = release_remarks
        stock_entry.custom_sending_method = delivery_method
        stock_entry.custom_delivery_reference = delivery_reference

        released_by = str(payload.get("released_by") or "").strip()
        if not released_by:
            employee = life_current_employee()
            released_by = str(employee.get("name") or "").strip() if employee else ""
        released_employee = life_validate_employee(released_by) if released_by else None

        stock_entry.custom_stock_released_by = released_employee.get("name") if released_employee else ""
        stock_entry.custom_stock_release_date = frappe.utils.now()
        remarks = [
            "Created from Material Request " + material_request.name,
            "Sending Method: " + delivery_method,
            "Person / Tracking Reference: " + delivery_reference
        ]
        if release_remarks:
            remarks.append("Store Manager Remarks: " + release_remarks)
        stock_entry.remarks = "\n".join(remarks)
        stock_entry.save()

        stock_entry = life_apply_workflow_state(stock_entry, SE_PENDING_RECEIPT_STATE)
        life_db_set_if_field(
            MR_DOCTYPE,
            material_request.name,
            "custom_stock_entry_reference",
            stock_entry.name
        )
        life_db_set_if_field(
            MR_DOCTYPE,
            material_request.name,
            "custom_stock_request_status",
            "Released"
        )
        life_db_set_if_field(
            MR_DOCTYPE,
            material_request.name,
            "transfer_status",
            "In Transit"
        )
        material_request.reload()
        rows = life_prepare_request_rows([material_request.name], [material_request.name])

        return {
            "ok": True,
            "message": (
                "Stock Entry " + stock_entry.name + " moved to " +
                SE_PENDING_RECEIPT_STATE + "."
            ),
            "request": rows[0] if rows else material_request.as_dict(),
            "stock_entry": stock_entry.as_dict()
        }


    def life_stock_entry_targets_branch(stock_entry, branch):
        target = str(stock_entry.get("to_warehouse") or "").strip()
        if target and life_warehouse_matches_branch(target, branch):
            return True
        for item in stock_entry.get("items") or []:
            if life_warehouse_matches_branch(item.get("t_warehouse"), branch):
                return True
        return False


    def life_stock_entry_row(stock_entry):
        items = []
        for item in stock_entry.get("items") or []:
            items.append({
                "name": item.name,
                "item_code": item.get("item_code"),
                "item_name": item.get("item_name"),
                "qty": life_float(item.get("qty"), 0),
                "transfer_qty": life_float(item.get("transfer_qty"), 0),
                "uom": item.get("uom"),
                "stock_uom": item.get("stock_uom"),
                "conversion_factor": life_float(item.get("conversion_factor"), 1) or 1,
                "s_warehouse": item.get("s_warehouse"),
                "t_warehouse": item.get("t_warehouse"),
                "material_request": item.get("material_request"),
                "material_request_item": item.get("material_request_item"),
                "custom_received_qty": item.get("custom_received_qty")
            })

        released_by_identifier = str(
            stock_entry.get("custom_stock_released_by") or
            stock_entry.get("custom_released_by") or
            stock_entry.get("released_by") or
            stock_entry.get("custom_released_by_employee") or
            stock_entry.get("owner") or
            stock_entry.get("modified_by") or
            ""
        ).strip()

        row = {
            "name": stock_entry.name,
            "owner": stock_entry.get("owner"),
            "modified_by": stock_entry.get("modified_by"),
            "creation": stock_entry.get("creation"),
            "modified": stock_entry.get("modified"),
            "docstatus": life_int(stock_entry.docstatus, 0),
            "workflow_state": stock_entry.get("workflow_state"),
            "posting_date": stock_entry.get("posting_date"),
            "from_warehouse": stock_entry.get("from_warehouse"),
            "to_warehouse": stock_entry.get("to_warehouse"),
            "purpose": stock_entry.get("purpose"),
            "stock_entry_type": stock_entry.get("stock_entry_type"),
            "base_grand_total": stock_entry.get("base_grand_total"),
            "released_by": released_by_identifier,
            "items": items
        }
        for fieldname in [
            "custom_sending_method", "custom_delivery_reference",
            "custom_stock_release_remarks", "custom_stock_released_by",
            "custom_stock_release_date", "custom_delivery_challan_photo_1",
            "custom_delivery_challan_photo_2", "custom_delivery_challan_photo_3",
            "custom_received_by", "custom_received_date", "custom_branch_receipt_remarks"
        ]:
            if life_has_field(SE_DOCTYPE, fieldname):
                row[fieldname] = stock_entry.get(fieldname)
        return row


    def life_action_billing_receipt_gate(payload):
        """
    Billing access gate used by the Billing web page.

    Final rule:

    1. Administrator:
       - Never blocked.

    2. System Manager role:
       - Never blocked, even if User.user_type == "System User".

    3. Website User / non-System User:
       - Never blocked.

    4. System User WITHOUT System Manager role:
       - Receipt validation applies.
       - Only Material Transfer Stock Entries are checked.
       - Only Pending Receipt (Sub WH) entries are checked.
       - Only entries released on/after 01-Aug-2026 are checked.
       - Only entries relevant to the user's receiving branch are checked.
       - If receipt remains pending for 24+ hours, Billing is blocked.

    5. custom_received_date:
       - If populated, the Stock Entry is treated as received and does not block.
    """

        # ============================================================
        # 1. LOGIN
        # ============================================================

        user = life_require_login()

        user_key = str(
            user or ""
        ).strip().lower()


        # ============================================================
        # 2. USER TYPE
        # ============================================================

        user_type = str(
            frappe.db.get_value(
                "User",
                user,
                "user_type"
            ) or ""
        ).strip()


        # ============================================================
        # 3. USER ROLES
        # ============================================================

        roles = life_user_roles() or []

        clean_roles = []

        for role in roles:
            role_name = str(
                role or ""
            ).strip()

            if role_name:
                clean_roles.append(
                    role_name
                )


        is_system_manager = (
            "System Manager" in clean_roles
        )


        # ============================================================
        # 4. ADMINISTRATOR / SYSTEM MANAGER BYPASS
        #
        # IMPORTANT:
        # These users must NEVER be blocked by receipt validation.
        # ============================================================

        if (
            user_key == "administrator" or
            is_system_manager
        ):
            return {
                "ok": True,

                "applies": False,
                "blocked": False,

                "user": user,
                "user_type": user_type,

                "is_system_manager": True,
                "bypass": True,
                "bypass_reason": (
                    "Administrator"
                    if user_key == "administrator"
                    else "System Manager"
                ),

                "branch": "",

                "receipt_rule_start_date":
                    "2026-08-01",

                "threshold_hours": 24,

                "overdue_count": 0,
                "overdue_receipts": []
            }


        # ============================================================
        # 5. ONLY SYSTEM USERS ARE SUBJECT TO BLOCKING
        #
        # Website Users or any other User Type are not affected.
        # ============================================================

        if user_type != "System User":
            return {
                "ok": True,

                "applies": False,
                "blocked": False,

                "user": user,
                "user_type": user_type,

                "is_system_manager": False,
                "bypass": True,
                "bypass_reason":
                    "Receipt Billing lock applies only to System Users.",

                "branch": "",

                "receipt_rule_start_date":
                    "2026-08-01",

                "threshold_hours": 24,

                "overdue_count": 0,
                "overdue_receipts": []
            }


        # ============================================================
        # FROM HERE:
        #
        # User Type       = System User
        # System Manager  = NO
        #
        # Only these users can be blocked.
        # ============================================================


        # ============================================================
        # 6. RESOLVE USER BRANCH
        # ============================================================

        employee = life_current_employee()

        branch = ""

        if employee:
            branch = str(
                employee.get("branch") or ""
            ).strip()


        # ------------------------------------------------------------
        # If Employee.branch is unavailable, try explicit Branch
        # User Permission.
        #
        # Only use it when exactly one branch is assigned.
        # Do not guess when multiple branches are assigned.
        # ------------------------------------------------------------

        if not branch:

            permission_rows = frappe.get_all(
                "User Permission",
                filters={
                    "user": user,
                    "allow": "Branch"
                },
                fields=[
                    "for_value"
                ],
                page_length=500
            )

            permitted_branches = []

            for permission_row in permission_rows:

                permitted_branch = str(
                    permission_row.get(
                        "for_value"
                    ) or ""
                ).strip()

                if (
                    permitted_branch and
                    permitted_branch
                    not in permitted_branches
                ):
                    permitted_branches.append(
                        permitted_branch
                    )


            if len(permitted_branches) == 1:
                branch = permitted_branches[0]


        # ============================================================
        # 7. STOCK ENTRY FIELDS
        # ============================================================

        stock_entry_meta = frappe.get_meta(
            SE_DOCTYPE
        )

        fields = [
            "name",
            "creation",
            "modified",
            "docstatus",
            "workflow_state",
            "posting_date",
            "posting_time",
            "purpose",
            "stock_entry_type",
            "from_warehouse",
            "to_warehouse"
        ]


        optional_fields = [
            "custom_stock_release_date",
            "custom_received_date",
            "custom_received_by",
            "custom_sending_method",
            "custom_delivery_reference"
        ]


        for fieldname in optional_fields:

            if stock_entry_meta.get_field(
                fieldname
            ):
                fields.append(
                    fieldname
                )


        # ============================================================
        # 8. LOAD ONLY STOCK ENTRIES AVAILABLE TO THIS USER
        #
        # Important:
        # Use frappe.get_list(), NOT frappe.get_all().
        #
        # Normal ERPNext permissions remain respected.
        # ============================================================

        rows = frappe.get_list(
            SE_DOCTYPE,
            filters={
                "docstatus": 0,
                "purpose": "Material Transfer"
            },
            fields=fields,
            order_by="modified asc",
            limit_page_length=2000
        )


        # ============================================================
        # 9. RULE SETTINGS
        # ============================================================

        now_dt = frappe.utils.now_datetime()

        receipt_rule_start_dt = (
            frappe.utils.get_datetime(
                "2026-08-01 00:00:00"
            )
        )

        threshold_hours = 24

        overdue = []


        # ============================================================
        # 10. CHECK STOCK ENTRIES
        # ============================================================

        for row in rows:

            # --------------------------------------------------------
            # Must be Pending Receipt
            # --------------------------------------------------------

            workflow_state = life_status_text(
                row.get(
                    "workflow_state"
                )
            )


            if "pending receipt" not in workflow_state:
                continue


            # --------------------------------------------------------
            # Already received = do not block
            # --------------------------------------------------------

            if row.get(
                "custom_received_date"
            ):
                continue


            # --------------------------------------------------------
            # Load Stock Entry
            # --------------------------------------------------------

            stock_entry_name = str(
                row.get("name") or ""
            ).strip()


            if not stock_entry_name:
                continue


            if not frappe.db.exists(
                SE_DOCTYPE,
                stock_entry_name
            ):
                continue


            stock_entry = frappe.get_doc(
                SE_DOCTYPE,
                stock_entry_name
            )


            # Preserve normal read permission.
            stock_entry.check_permission(
                "read"
            )


            # --------------------------------------------------------
            # Branch validation
            #
            # If we know the user's branch, only receipts targeting
            # that branch may block that user.
            # --------------------------------------------------------

            if branch:

                if not life_stock_entry_targets_branch(
                    stock_entry,
                    branch
                ):
                    continue


            # --------------------------------------------------------
            # RELEASE DATE
            #
            # Primary source:
            # custom_stock_release_date
            #
            # Fallback is retained for older records.
            # --------------------------------------------------------

            release_value = row.get(
                "custom_stock_release_date"
            )


            if not release_value:
                release_value = (
                    row.get("modified") or
                    row.get("creation")
                )


            if not release_value:
                continue


            # --------------------------------------------------------
            # Convert release date
            # --------------------------------------------------------

            try:

                release_dt = (
                    frappe.utils.get_datetime(
                        release_value
                    )
                )

            except Exception:
                continue


            # ========================================================
            # 11. RECEIPT RULE START DATE
            #
            # Anything before 01-Aug-2026 does not participate in
            # Billing blocking.
            # ========================================================

            if (
                release_dt <
                receipt_rule_start_dt
            ):
                continue


            # ========================================================
            # 12. 24-HOUR VALIDATION
            # ========================================================

            try:

                elapsed_hours = (
                    frappe.utils.time_diff_in_hours(
                        now_dt,
                        release_dt
                    )
                )

            except Exception:
                continue


            if elapsed_hours < threshold_hours:
                continue


            # ========================================================
            # 13. OVERDUE RECEIPT
            # ========================================================

            overdue.append({
                "stock_entry":
                    stock_entry_name,

                "branch":
                    branch,

                "from_warehouse":
                    row.get(
                        "from_warehouse"
                    ),

                "to_warehouse":
                    row.get(
                        "to_warehouse"
                    ),

                "workflow_state":
                    row.get(
                        "workflow_state"
                    ),

                "posting_date":
                    str(
                        row.get(
                            "posting_date"
                        ) or ""
                    ),

                "release_date":
                    str(
                        release_value
                    ),

                "hours_pending":
                    round(
                        life_float(
                            elapsed_hours,
                            0
                        ),
                        1
                    ),

                "days_pending":
                    round(
                        life_float(
                            elapsed_hours,
                            0
                        ) / 24.0,
                        1
                    ),

                "sending_method":
                    row.get(
                        "custom_sending_method"
                    ) or "",

                "delivery_reference":
                    row.get(
                        "custom_delivery_reference"
                    ) or ""
            })


        # ============================================================
        # 14. OLDEST OVERDUE FIRST
        # ============================================================

        overdue.sort(
            key=lambda row:
                str(
                    row.get(
                        "release_date"
                    ) or ""
                )
        )


        # ============================================================
        # 15. FINAL RESULT
        # ============================================================

        blocked = True if overdue else False


        return {
            "ok": True,

            "applies": True,
            "blocked": blocked,

            "user": user,
            "user_type": user_type,

            "is_system_manager": False,
            "bypass": False,
            "bypass_reason": "",

            "branch": branch,

            "receipt_rule_start_date":
                "2026-08-01",

            "threshold_hours":
                threshold_hours,

            "overdue_count":
                len(overdue),

            "overdue_receipts":
                overdue
        }


    # ============================================================
    # HO / STOCK MANAGER — BRANCH STOCK RECEIPT UPDATES
    # ============================================================

    def life_action_list_ho_receipt_updates(payload):
        """
    Return all Stock Entries relevant to the HO / Stock Manager
    'Branch Stock Receipt Updates' section.

    Included:
      1. Draft Material Transfer + Pending Receipt
      2. Submitted Material Transfer with branch receipt completed

    This endpoint intentionally uses frappe.get_all() AFTER
    life_require_ho(), because Stock Manager / System Manager
    must see receipt updates across all branches regardless of
    individual Stock Entry User Permissions.
    """

        life_require_login()
        life_require_ho()

        stock_entry_meta = frappe.get_meta(SE_DOCTYPE)

        # --------------------------------------------------------
        # Fetch all relevant Material Transfer headers.
        # Do not use frappe.get_list here because this is the
        # authorised HO / Stock Manager cross-branch view.
        # --------------------------------------------------------
        headers = frappe.get_all(
            SE_DOCTYPE,
            filters={
                "purpose": "Material Transfer",
                "docstatus": ["in", [0, 1]]
            },
            fields=["name"],
            order_by="modified desc",
            page_length=2000
        )

        rows = []

        for header in headers:

            stock_entry_name = str(
                header.get("name") or ""
            ).strip()

            if not stock_entry_name:
                continue

            stock_entry = frappe.get_doc(
                SE_DOCTYPE,
                stock_entry_name
            )

            docstatus = life_int(
                stock_entry.docstatus,
                0
            )

            workflow_text = life_status_text(
                stock_entry.get(
                    "workflow_state"
                )
            )

            received_by = ""
            received_date = None

            if stock_entry_meta.get_field(
                "custom_received_by"
            ):
                received_by = str(
                    stock_entry.get(
                        "custom_received_by"
                    ) or ""
                ).strip()

            if stock_entry_meta.get_field(
                "custom_received_date"
            ):
                received_date = stock_entry.get(
                    "custom_received_date"
                )

            # ----------------------------------------------------
            # DRAFT:
            # show only Stock Entries awaiting branch receipt.
            # ----------------------------------------------------
            if docstatus == 0:

                if "pending receipt" not in workflow_text:
                    continue

            # ----------------------------------------------------
            # SUBMITTED:
            # show only Stock Entries actually confirmed/received
            # by a branch.
            # ----------------------------------------------------
            elif docstatus == 1:

                if not received_by and not received_date:
                    continue

            else:
                continue

            row = life_stock_entry_row(
                stock_entry
            )

            rows.append(row)

        # --------------------------------------------------------
        # Resolve Released By names server-side as well.
        # Frontend may hydrate again; that is harmless.
        # --------------------------------------------------------
        released_identifiers = []

        for row in rows:

            released_identifier = str(
                row.get("released_by") or
                row.get(
                    "custom_stock_released_by"
                ) or
                row.get("owner") or
                row.get("modified_by") or
                ""
            ).strip()

            row["released_by"] = (
                released_identifier
            )

            if (
                released_identifier and
                released_identifier
                not in released_identifiers
            ):
                released_identifiers.append(
                    released_identifier
                )

        released_name_map = (
            life_requester_name_map(
                released_identifiers
            )
        )

        for row in rows:

            released_identifier = str(
                row.get("released_by") or ""
            ).strip()

            row["released_by_name"] = (
                released_name_map.get(
                    released_identifier
                ) or
                released_identifier or
                "—"
            )

        # --------------------------------------------------------
        # Pending first, then newest received/released records.
        # --------------------------------------------------------
        pending_rows = []
        received_rows = []

        for row in rows:

            row_docstatus = life_int(
                row.get("docstatus"),
                0
            )

            workflow_text = life_status_text(
                row.get("workflow_state")
            )

            if (
                row_docstatus == 0 and
                "pending receipt" in workflow_text
            ):
                pending_rows.append(row)
            else:
                received_rows.append(row)

        pending_rows.sort(
            key=lambda row: str(
                row.get(
                    "custom_stock_release_date"
                ) or
                row.get("modified") or
                row.get("creation") or
                ""
            ),
            reverse=True
        )

        received_rows.sort(
            key=lambda row: str(
                row.get(
                    "custom_received_date"
                ) or
                row.get("modified") or
                row.get("creation") or
                ""
            ),
            reverse=True
        )

        rows = pending_rows + received_rows

        return {
            "ok": True,
            "scope": "ho",
            "total": len(rows),
            "pending_count": len(
                pending_rows
            ),
            "received_count": len(
                received_rows
            ),
            "rows": rows
        }

    def life_action_list_branch_receipts(payload):
        user = life_require_login()

        page = max(
            1,
            life_int(
                life_arg(payload, "page", 1),
                1
            )
        )

        page_size = min(
            200,
            max(
                1,
                life_int(
                    life_arg(payload, "page_size", 10),
                    10
                )
            )
        )

        # ============================================================
        # USER / ROLE CONTEXT
        # ============================================================

        roles = life_user_roles() or []

        is_system_manager = (
            user == "Administrator" or
            "System Manager" in roles
        )

        is_stock_manager = (
            "Stock Manager" in roles
        )

        is_ho_user = (
            is_system_manager or
            is_stock_manager
        )

        # ============================================================
        # BRANCH FROM REQUEST
        # ============================================================

        branch = str(
            life_arg(payload, "branch", "") or ""
        ).strip()

        # ============================================================
        # FALLBACK 1 — EMPLOYEE BRANCH
        # ============================================================

        if not branch:
            employee = life_current_employee()

            if employee:
                branch = str(
                    employee.get("branch") or ""
                ).strip()

        # ============================================================
        # FALLBACK 2 — SINGLE BRANCH USER PERMISSION
        # ============================================================

        if not branch:

            permission_rows = frappe.get_all(
                "User Permission",
                filters={
                    "user": user,
                    "allow": "Branch"
                },
                fields=["for_value"],
                page_length=500
            )

            permitted_branches = []

            for permission_row in permission_rows:

                permitted_branch = str(
                    permission_row.get("for_value") or ""
                ).strip()

                if (
                    permitted_branch and
                    permitted_branch not in permitted_branches
                ):
                    permitted_branches.append(
                        permitted_branch
                    )

            if len(permitted_branches) == 1:
                branch = permitted_branches[0]

        # ============================================================
        # SYSTEM MANAGER / STOCK MANAGER
        #
        # They may legitimately have no single branch.
        # DO NOT THROW 417.
        # Wait until a branch is selected.
        # ============================================================

        if not branch and is_ho_user:

            return {
                "ok": True,
                "rows": [],
                "total": 0,
                "total_pages": 1,
                "page": page,
                "page_size": page_size,
                "branch": "",
                "requires_branch_selection": True,
                "is_ho_user": True,
                "message": (
                    "Select a branch to load "
                    "Branch Stock Receipt Updates."
                )
            }

        # ============================================================
        # NORMAL SYSTEM USER
        #
        # Normal branch users MUST have a branch.
        # ============================================================

        if not branch:

            frappe.throw(
                "Branch could not be resolved for the logged-in user."
            )

        # ============================================================
        # PERMISSION-AWARE STOCK ENTRY LIST
        # ============================================================

        headers = frappe.get_list(
            SE_DOCTYPE,
            filters={
                "docstatus": 0,
                "purpose": "Material Transfer"
            },
            fields=["name"],
            order_by="modified desc",
            limit_page_length=500
        )

        rows = []

        for header in headers:

            stock_entry = frappe.get_doc(
                SE_DOCTYPE,
                header.get("name")
            )

            stock_entry.check_permission("read")

            workflow_text = life_status_text(
                stock_entry.get("workflow_state")
            )

            # Only Pending Receipt entries.
            if "pending receipt" not in workflow_text:
                continue

            # ========================================================
            # RECEIPT RULE STARTS 01-AUG-2026
            # ========================================================

            release_value = (
                stock_entry.get("custom_stock_release_date") or
                stock_entry.get("modified") or
                stock_entry.get("creation")
            )

            if not release_value:
                continue

            try:
                release_dt = frappe.utils.get_datetime(
                    release_value
                )

                receipt_rule_start_dt = (
                    frappe.utils.get_datetime(
                        "2026-08-01 00:00:00"
                    )
                )

                if release_dt < receipt_rule_start_dt:
                    continue

            except Exception:
                continue

            # ========================================================
            # SELECTED / RESOLVED BRANCH ONLY
            # ========================================================

            if not life_stock_entry_targets_branch(
                stock_entry,
                branch
            ):
                continue

            rows.append(
                life_stock_entry_row(
                    stock_entry
                )
            )

        # ============================================================
        # RELEASED-BY DISPLAY NAME
        # ============================================================

        released_by_identifiers = []

        for row in rows:

            released_by_identifier = str(
                row.get("released_by") or
                row.get("custom_stock_released_by") or
                row.get("owner") or
                row.get("modified_by") or
                ""
            ).strip()

            row["released_by"] = (
                released_by_identifier
            )

            if (
                released_by_identifier and
                released_by_identifier
                not in released_by_identifiers
            ):
                released_by_identifiers.append(
                    released_by_identifier
                )

        released_by_name_map = (
            life_requester_name_map(
                released_by_identifiers
            )
        )

        for row in rows:

            released_by_identifier = str(
                row.get("released_by") or ""
            ).strip()

            row["released_by_name"] = (
                released_by_name_map.get(
                    released_by_identifier
                ) or
                released_by_identifier or
                "—"
            )

        total = len(rows)

        start = (
            page - 1
        ) * page_size

        return {
            "ok": True,
            "branch": branch,
            "is_ho_user": is_ho_user,
            "requires_branch_selection": False,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(
                1,
                int(
                    (
                        total +
                        page_size -
                        1
                    ) / page_size
                )
            ),
            "rows": rows[
                start:
                start + page_size
            ]
        }


    def life_action_confirm_branch_receipt(payload):
        life_require_login()
        stock_entry_name = str(payload.get("stock_entry") or "").strip()
        received_by = str(payload.get("received_by") or "").strip()
        receipt_remarks = str(
            payload.get("receipt_remarks") or payload.get("remarks") or ""
        ).strip()
        item_rows = payload.get("items") or []

        if not stock_entry_name:
            frappe.throw("Stock Entry name is required.")
        if not isinstance(item_rows, list) or not item_rows:
            frappe.throw("Received Quantities are required.")

        stock_entry = frappe.get_doc(SE_DOCTYPE, stock_entry_name)
        stock_entry.check_permission("read")
        if life_int(stock_entry.docstatus, 0) != 0:
            frappe.throw("This Stock Entry is no longer open for receipt.")
        purpose = str(stock_entry.get("purpose") or stock_entry.get("stock_entry_type") or "").strip()
        if purpose != "Material Transfer":
            frappe.throw("Only Material Transfer Stock Entries can be received here.")

        target_warehouse = str(stock_entry.get("to_warehouse") or "").strip()
        if not target_warehouse:
            for item in stock_entry.get("items") or []:
                if item.get("t_warehouse"):
                    target_warehouse = str(item.get("t_warehouse"))
                    break
        if not target_warehouse:
            frappe.throw("Receiving Warehouse is missing on the Stock Entry.")

        life_require_branch_warehouse(target_warehouse, "Receiving Warehouse")
        receiving_branch = life_branch_from_warehouse(target_warehouse)
        employee = life_validate_employee(received_by, receiving_branch)

        required_fields = [
            "custom_received_by", "custom_received_date", "custom_branch_receipt_remarks"
        ]
        missing = []
        for fieldname in required_fields:
            if not life_has_field(SE_DOCTYPE, fieldname):
                missing.append(fieldname)
        if not life_has_field(SE_ITEM_DOCTYPE, "custom_received_qty"):
            missing.append("Stock Entry Detail.custom_received_qty")
        if missing:
            frappe.throw("Create these Receipt fields first: " + ", ".join(missing))

        receipt_map = {}
        for row in item_rows:
            if not isinstance(row, dict):
                continue
            row_name = str(
                row.get("row_name") or row.get("stock_entry_detail") or ""
            ).strip()
            if row_name:
                receipt_map[row_name] = row

        for item in stock_entry.get("items") or []:
            receipt = receipt_map.get(str(item.name))
            if not receipt:
                frappe.throw("Received Quantity is missing for " + str(item.item_code) + ".")
            received_qty = life_float(receipt.get("received_qty"), 0)
            released_qty = max(0, life_float(item.get("qty"), 0))
            if received_qty < 0:
                frappe.throw("Received Quantity cannot be negative for " + str(item.item_code) + ".")
            if received_qty > released_qty + 0.000001:
                frappe.throw(
                    "Received Quantity " + str(received_qty) +
                    " cannot exceed Released Quantity " + str(released_qty) +
                    " for " + str(item.item_code) + "."
                )
            item.custom_received_qty = received_qty

        stock_entry.custom_received_by = employee.get("name")
        stock_entry.custom_received_date = frappe.utils.now()
        stock_entry.custom_branch_receipt_remarks = receipt_remarks

        # Permission is enforced above through target branch access and the workflow.
        # ignore_permissions only allows the controlled custom receipt fields to save.
        stock_entry.save(ignore_permissions=True)
        submitted = life_apply_receipt_submit(stock_entry)

        request_names = []
        for item in submitted.get("items") or []:
            request_name = str(item.get("material_request") or "").strip()
            if request_name and request_name not in request_names:
                request_names.append(request_name)

        for request_name in request_names:
            life_db_set_if_field(
                MR_DOCTYPE,
                request_name,
                "custom_stock_request_status",
                "Completed"
            )
            life_db_set_if_field(
                MR_DOCTYPE,
                request_name,
                "transfer_status",
                "Completed"
            )

        return {
            "ok": True,
            "message": "Stock Entry " + submitted.name + " receipt approved and submitted.",
            "stock_entry": submitted.as_dict(),
            "material_requests": request_names
        }



    # ----------------------------------------------------------------------------
    # STOCK RECONCILIATION WEB WORKFLOW — CONTROLLED PERMISSION GATEWAY
    # ----------------------------------------------------------------------------

    def life_stock_reconciliation_state(value, docstatus=0):
        state = str(value or "").strip()
        if state:
            return state

        status_value = life_int(docstatus, 0)
        if status_value == 1:
            return STOCK_RECONCILIATION_APPROVED
        if status_value == 2:
            return STOCK_RECONCILIATION_CANCELLED
        return STOCK_RECONCILIATION_DRAFT


    def life_stock_reconciliation_requested_warehouses(payload):
        values = payload.get("warehouses") or []
        if isinstance(values, str):
            try:
                parsed = json.loads(values)
                values = parsed if isinstance(parsed, list) else [values]
            except Exception:
                values = [values]

        result = []
        if isinstance(values, (list, tuple)):
            for value in values:
                warehouse = str(value or "").strip()
                if warehouse and warehouse not in result:
                    result.append(warehouse)
        return result


    def life_stock_reconciliation_doc_warehouses(doc):
        warehouses = []
        parent_warehouse = str(doc.get("set_warehouse") or "").strip()
        if parent_warehouse:
            warehouses.append(parent_warehouse)

        for row in doc.get("items") or []:
            warehouse = str(row.get("warehouse") or parent_warehouse or "").strip()
            if warehouse and warehouse not in warehouses:
                warehouses.append(warehouse)
        return warehouses


    def life_stock_reconciliation_user_can_access_warehouses(warehouses):
        life_require_login()
        if life_is_ho_user():
            return True

        allowed_branches = life_allowed_branches()
        if not allowed_branches or not warehouses:
            return False

        for warehouse in warehouses:
            matched = False
            for branch in allowed_branches:
                if life_warehouse_matches_branch(warehouse, branch):
                    matched = True
                    break
            if not matched:
                return False
        return True


    def life_stock_reconciliation_require_doc_access(doc):
        warehouses = life_stock_reconciliation_doc_warehouses(doc)
        if not life_stock_reconciliation_user_can_access_warehouses(warehouses):
            frappe.throw(
                "This Stock Reconciliation does not belong to a warehouse assigned to your branch.",
                frappe.PermissionError
            )


    def life_stock_reconciliation_safe_doc(doc):
        output = {
            "name": doc.get("name"),
            "doctype": STOCK_RECONCILIATION_DOCTYPE,
            "posting_date": doc.get("posting_date"),
            "posting_time": doc.get("posting_time"),
            "set_warehouse": doc.get("set_warehouse"),
            "workflow_state": life_stock_reconciliation_state(
                doc.get("workflow_state"),
                doc.get("docstatus")
            ),
            "docstatus": life_int(doc.get("docstatus"), 0),
            "owner": doc.get("owner"),
            "creation": doc.get("creation"),
            "modified": doc.get("modified"),
            "modified_by": doc.get("modified_by"),
            "difference_amount": life_float(doc.get("difference_amount"), 0),
            "company": doc.get("company"),
            "purpose": doc.get("purpose"),
            "items": []
        }

        item_rows = []
        for row in doc.get("items") or []:
            item_rows.append({
                "name": row.get("name"),
                "idx": row.get("idx"),
                "item_code": row.get("item_code"),
                "item_name": row.get("item_name"),
                "warehouse": row.get("warehouse") or doc.get("set_warehouse"),
                "stock_uom": row.get("stock_uom"),
                "current_qty": life_float(row.get("current_qty"), 0),
                "qty": life_float(row.get("qty"), 0),
                "quantity_difference": life_float(row.get("quantity_difference"), 0),
                "valuation_rate": life_float(row.get("valuation_rate"), 0),
                "current_valuation_rate": life_float(row.get("current_valuation_rate"), 0),
                "amount": life_float(row.get("amount"), 0),
                "amount_difference": life_float(row.get("amount_difference"), 0)
            })
        output["items"] = item_rows
        return output


    def life_action_list_stock_reconciliations(payload):
        life_require_login()
        scope = str(payload.get("scope") or "branch").strip().lower()
        if scope == "manager":
            life_require_ho()
        else:
            scope = "branch"

        status_filter = str(payload.get("status") or "").strip()
        from_date = str(payload.get("from_date") or "").strip()
        to_date = str(payload.get("to_date") or "").strip()
        search_text = str(payload.get("branch") or "").strip().lower()
        requested_warehouses = life_stock_reconciliation_requested_warehouses(payload)
        limit_value = life_int(payload.get("limit"), 500)
        if limit_value <= 0:
            limit_value = 500
        if limit_value > 2000:
            limit_value = 2000

        filters = []
        if from_date:
            filters.append(["posting_date", ">=", from_date])
        if to_date:
            filters.append(["posting_date", "<=", to_date])

        fields = [
            "name",
            "posting_date",
            "posting_time",
            "set_warehouse",
            "workflow_state",
            "docstatus",
            "owner",
            "creation",
            "modified",
            "modified_by",
            "difference_amount"
        ]

        rows = frappe.get_all(
            STOCK_RECONCILIATION_DOCTYPE,
            fields=fields,
            filters=filters,
            order_by="posting_date desc, creation desc",
            page_length=limit_value
        )

        allowed_branches = [] if life_is_ho_user() else life_allowed_branches()
        output = []
        for row in rows:
            warehouse = str(row.get("set_warehouse") or "").strip()
            state = life_stock_reconciliation_state(
                row.get("workflow_state"),
                row.get("docstatus")
            )

            if status_filter and state != status_filter:
                continue

            if scope == "branch":
                if not life_is_ho_user():
                    matched = False
                    for branch in allowed_branches:
                        if life_warehouse_matches_branch(warehouse, branch):
                            matched = True
                            break
                    if not matched:
                        continue

                if requested_warehouses:
                    requested_match = False
                    warehouse_key = life_normalize_key(warehouse)
                    warehouse_branch_key = life_normalize_key(
                        life_branch_from_warehouse(warehouse)
                    )
                    for requested_warehouse in requested_warehouses:
                        requested_key = life_normalize_key(requested_warehouse)
                        requested_branch_key = life_normalize_key(
                            life_branch_from_warehouse(requested_warehouse)
                        )
                        if (
                            warehouse_key == requested_key or
                            warehouse_branch_key == requested_branch_key or
                            life_warehouse_matches_branch(warehouse, requested_warehouse) or
                            life_warehouse_matches_branch(requested_warehouse, warehouse)
                        ):
                            requested_match = True
                            break
                    if not requested_match:
                        continue

            if scope == "manager" and search_text:
                warehouse_text = warehouse.lower()
                branch_text = life_branch_from_warehouse(warehouse).lower()
                if search_text not in warehouse_text and search_text not in branch_text:
                    continue

            output.append({
                "name": row.get("name"),
                "posting_date": row.get("posting_date"),
                "posting_time": row.get("posting_time"),
                "set_warehouse": warehouse,
                "workflow_state": state,
                "docstatus": life_int(row.get("docstatus"), 0),
                "owner": row.get("owner"),
                "creation": row.get("creation"),
                "modified": row.get("modified"),
                "modified_by": row.get("modified_by"),
                "difference_amount": life_float(row.get("difference_amount"), 0)
            })

        return {
            "ok": True,
            "rows": output,
            "count": len(output),
            "scope": scope
        }


    def life_action_get_stock_reconciliation(payload):
        life_require_login()
        name = str(payload.get("name") or "").strip()
        if not name:
            frappe.throw("Stock Reconciliation name is required.")
        if not frappe.db.exists(STOCK_RECONCILIATION_DOCTYPE, name):
            frappe.throw("Stock Reconciliation " + name + " was not found.")

        doc = frappe.get_doc(STOCK_RECONCILIATION_DOCTYPE, name)
        life_stock_reconciliation_require_doc_access(doc)
        return {
            "ok": True,
            "doc": life_stock_reconciliation_safe_doc(doc)
        }


    def life_stock_reconciliation_validate_create_doc(doc_data):
        if isinstance(doc_data, str):
            doc_data = json.loads(doc_data)
        if not isinstance(doc_data, dict):
            frappe.throw("Stock Reconciliation data must be a JSON object.")

        set_warehouse = str(doc_data.get("set_warehouse") or "").strip()
        if not set_warehouse:
            frappe.throw("Warehouse is required for physical stock verification.")
        life_require_branch_warehouse(set_warehouse, "Warehouse")

        raw_items = doc_data.get("items") or []
        if not isinstance(raw_items, list) or not raw_items:
            frappe.throw("Enter at least one physical stock count.")

        items = []
        for index, row in enumerate(raw_items):
            if not isinstance(row, dict):
                frappe.throw("Invalid item row at position " + str(index + 1) + ".")

            item_code = str(row.get("item_code") or "").strip()
            warehouse = str(row.get("warehouse") or set_warehouse).strip()
            quantity = life_float(row.get("qty"), 0)
            valuation_rate = life_float(row.get("valuation_rate"), 0)

            if not item_code:
                frappe.throw("Item Code is required at row " + str(index + 1) + ".")
            if not frappe.db.exists("Item", item_code):
                frappe.throw("Item " + item_code + " was not found.")
            if not warehouse:
                frappe.throw("Warehouse is required at row " + str(index + 1) + ".")
            life_require_branch_warehouse(warehouse, "Warehouse")
            if quantity < 0:
                frappe.throw("Physical quantity cannot be negative for " + item_code + ".")
            if quantity > 0 and valuation_rate <= 0:
                frappe.throw(
                    "Valuation Rate is required for " + item_code + " in " + warehouse + "."
                )

            items.append({
                "item_code": item_code,
                "warehouse": warehouse,
                "qty": quantity,
                "valuation_rate": valuation_rate
            })

        posting_date = str(doc_data.get("posting_date") or frappe.utils.today()).strip()
        company = str(doc_data.get("company") or COMPANY_FALLBACK).strip()
        if company != COMPANY_FALLBACK:
            frappe.throw("Invalid company for LIFE Stock Reconciliation.")

        return {
            "doctype": STOCK_RECONCILIATION_DOCTYPE,
            "purpose": "Stock Reconciliation",
            "company": company,
            "set_warehouse": set_warehouse,
            "posting_date": posting_date,
            "items": items
        }


    def life_stock_reconciliation_transition(doc, action_name):
        action_name = str(action_name or "").strip()
        current_state = life_stock_reconciliation_state(
            doc.get("workflow_state"),
            doc.get("docstatus")
        )

        next_state = ""
        next_docstatus = 0
        manager_action = False

        if current_state == STOCK_RECONCILIATION_DRAFT and action_name == "Send for Approval":
            next_state = STOCK_RECONCILIATION_PENDING
        elif current_state == STOCK_RECONCILIATION_PENDING and action_name == "Reject":
            next_state = STOCK_RECONCILIATION_REJECTED
            manager_action = True
        elif current_state == STOCK_RECONCILIATION_PENDING and action_name == "Approve":
            next_state = STOCK_RECONCILIATION_APPROVED
            next_docstatus = 1
            manager_action = True
        elif current_state == STOCK_RECONCILIATION_APPROVED and action_name == "Cancel":
            next_state = STOCK_RECONCILIATION_CANCELLED
            next_docstatus = 2
            manager_action = True
        else:
            frappe.throw(
                "Workflow action " + action_name + " is not valid from " + current_state + "."
            )

        if manager_action:
            life_require_ho()
        else:
            life_stock_reconciliation_require_doc_access(doc)

        previous_install_flag = frappe.flags.get("in_install")
        try:
            frappe.flags.in_install = "frappe"
            doc.set("workflow_state", next_state)
            doc.flags.ignore_permissions = True

            if next_docstatus == 1:
                doc.submit()
            elif next_docstatus == 2:
                doc.cancel()
            else:
                doc.save(ignore_permissions=True)
        finally:
            frappe.flags.in_install = previous_install_flag

        doc.add_comment(
            "Workflow",
            next_state + " via LIFE Stock Dashboard by " + str(frappe.session.user)
        )
        return doc


    def life_action_create_stock_reconciliation_request(payload):
        life_require_login()
        clean_doc = life_stock_reconciliation_validate_create_doc(payload.get("doc") or {})
        doc = frappe.get_doc(clean_doc)
        doc.insert(ignore_permissions=True)
        doc = life_stock_reconciliation_transition(doc, "Send for Approval")

        return {
            "ok": True,
            "message": "Physical stock verification request submitted for Stock Manager approval.",
            "doc": life_stock_reconciliation_safe_doc(doc)
        }


    def life_action_apply_stock_reconciliation_workflow(payload):
        life_require_login()
        name = str(payload.get("name") or "").strip()
        action_name = str(payload.get("workflow_action") or payload.get("action_name") or "").strip()

        if not name:
            frappe.throw("Stock Reconciliation name is required.")
        if not action_name:
            frappe.throw("Workflow action is required.")
        if not frappe.db.exists(STOCK_RECONCILIATION_DOCTYPE, name):
            frappe.throw("Stock Reconciliation " + name + " was not found.")

        doc = frappe.get_doc(STOCK_RECONCILIATION_DOCTYPE, name)
        life_stock_reconciliation_require_doc_access(doc)
        doc = life_stock_reconciliation_transition(doc, action_name)

        return {
            "ok": True,
            "message": action_name + " completed successfully.",
            "doc": life_stock_reconciliation_safe_doc(doc)
        }


    # ----------------------------------------------------------------------------
    # UNIFIED STOCK API GATEWAY + STOCK INTELLIGENCE OPTIMISATION
    # ----------------------------------------------------------------------------

    LIFE_GATEWAY_ALLOWED_METHODS = [
        "frappe.client.get_list",
        "frappe.client.get_count",
        "frappe.client.get",
        "frappe.client.get_value",
        "frappe.client.insert",
        "frappe.client.submit",
        "frappe.client.cancel",
        "frappe.client.set_value",
        "frappe.model.workflow.get_transitions",
        "frappe.model.workflow.apply_workflow",
        "frappe.desk.query_report.run",
        "life_monthly_indent_access"
    ]

    LIFE_STOCK_INTELLIGENCE_COMPANY = COMPANY_FALLBACK
    LIFE_STOCK_INTELLIGENCE_CORE_CACHE_SECONDS = 300
    LIFE_STOCK_INTELLIGENCE_TRENDS_CACHE_SECONDS = 900

    # Stock Intelligence monetary values use Item.valuation_rate.
    # ERPNext Stock Balance remains the quantity source only.
    # No Item Price, Purchase Receipt, Purchase Invoice, or last purchase rate is used.


    def life_gateway_serializable(value):
        if value is None:
            return None

        if isinstance(value, dict):
            output = {}
            for key, item in value.items():
                output[key] = life_gateway_serializable(item)
            return output

        if isinstance(value, (list, tuple)):
            output = []
            for item in value:
                output.append(life_gateway_serializable(item))
            return output

        try:
            mapped = value.as_dict()
            return life_gateway_serializable(mapped)
        except Exception:
            return value


    # ----------------------------------------------------------------------------
    # RECEIPT DISCREPANCY — ORIGINAL TRANSFER + REVERSE MATERIAL TRANSFER
    # ----------------------------------------------------------------------------

    def life_receipt_adjustment_require_setup():
        missing = []
        for doctype in [RECEIPT_ADJUSTMENT_DOCTYPE, RECEIPT_ADJUSTMENT_ITEM_DOCTYPE]:
            if not frappe.db.exists("DocType", doctype):
                missing.append(doctype)

        required_parent_fields = [
            "status", "stock_entry", "material_request", "company",
            "source_warehouse", "target_warehouse", "target_branch",
            "reported_by", "reported_by_name", "reported_on",
            "branch_receipt_remarks", "adjustment_items",
            "total_released_qty", "total_received_qty", "total_missing_qty",
            "total_damaged_qty", "total_return_to_source_qty",
            "stock_manager_remarks", "approved_by", "approved_on",
            "submitted_stock_entry", "correction_requested_by",
            "correction_requested_on", "rejected_by", "rejected_on"
        ]
        if frappe.db.exists("DocType", RECEIPT_ADJUSTMENT_DOCTYPE):
            for fieldname in required_parent_fields:
                if not life_has_field(RECEIPT_ADJUSTMENT_DOCTYPE, fieldname):
                    missing.append(RECEIPT_ADJUSTMENT_DOCTYPE + "." + fieldname)

        required_child_fields = [
            "stock_entry_detail", "item_code", "item_name", "uom",
            "source_warehouse", "target_warehouse", "released_qty",
            "received_qty", "missing_qty", "damaged_qty",
            "return_to_source_qty", "discrepancy_type", "row_status",
            "discrepancy_remarks"
        ]
        if frappe.db.exists("DocType", RECEIPT_ADJUSTMENT_ITEM_DOCTYPE):
            for fieldname in required_child_fields:
                if not life_has_field(RECEIPT_ADJUSTMENT_ITEM_DOCTYPE, fieldname):
                    missing.append(RECEIPT_ADJUSTMENT_ITEM_DOCTYPE + "." + fieldname)

        if missing:
            frappe.throw(
                "Create or correct these receipt-adjustment fields first: " +
                ", ".join(missing)
            )


    def life_receipt_adjustment_discrepancy_type(missing_qty, damaged_qty):
        if missing_qty > 0 and damaged_qty > 0:
            return "Missing and Damaged"
        if missing_qty > 0:
            return "Missing"
        if damaged_qty > 0:
            return "Damaged"
        return "No Discrepancy"


    def life_receipt_adjustment_target_warehouse(stock_entry):
        target_warehouse = str(stock_entry.get("to_warehouse") or "").strip()
        if target_warehouse:
            return target_warehouse
        for item in stock_entry.get("items") or []:
            target_warehouse = str(item.get("t_warehouse") or "").strip()
            if target_warehouse:
                return target_warehouse
        return ""


    def life_receipt_adjustment_source_warehouse(stock_entry):
        source_warehouse = str(stock_entry.get("from_warehouse") or "").strip()
        if source_warehouse:
            return source_warehouse
        for item in stock_entry.get("items") or []:
            source_warehouse = str(item.get("s_warehouse") or "").strip()
            if source_warehouse:
                return source_warehouse
        return ""


    def life_receipt_adjustment_valid_material_request(stock_entry):
        for item in stock_entry.get("items") or []:
            request_name = str(item.get("material_request") or "").strip()
            if not request_name:
                continue
            if not frappe.db.exists(MR_DOCTYPE, request_name):
                continue
            docstatus = life_int(
                frappe.db.get_value(MR_DOCTYPE, request_name, "docstatus"),
                0
            )
            if docstatus != 2:
                return request_name
        return ""


    def life_receipt_adjustment_clear_cancelled_links(stock_entry):
        valid_request_names = []
        for item in stock_entry.get("items") or []:
            request_name = str(item.get("material_request") or "").strip()
            if not request_name:
                continue
            docstatus = 2
            if frappe.db.exists(MR_DOCTYPE, request_name):
                docstatus = life_int(
                    frappe.db.get_value(MR_DOCTYPE, request_name, "docstatus"),
                    0
                )
            if docstatus == 2:
                item.set("material_request", None)
                item.set("material_request_item", None)
            elif request_name not in valid_request_names:
                valid_request_names.append(request_name)
        return valid_request_names


    def life_receipt_adjustment_payload_rows(stock_entry, payload_rows):
        if not isinstance(payload_rows, list) or not payload_rows:
            frappe.throw("Item-wise receipt quantities are required.")

        payload_map = {}
        for row in payload_rows:
            if not isinstance(row, dict):
                continue
            row_name = str(
                row.get("row_name") or row.get("stock_entry_detail") or ""
            ).strip()
            if row_name:
                payload_map[row_name] = row

        resolved = []
        has_discrepancy = False
        tolerance = 0.0001

        for item in stock_entry.get("items") or []:
            payload_row = payload_map.get(str(item.name))
            if not payload_row:
                frappe.throw(
                    "Receipt quantities are missing for " +
                    str(item.get("item_code") or item.name) + "."
                )

            released_qty = max(0, life_float(item.get("qty"), 0))
            received_qty = life_float(payload_row.get("received_qty"), 0)
            missing_qty = life_float(payload_row.get("missing_qty"), 0)
            damaged_qty = life_float(payload_row.get("damaged_qty"), 0)
            discrepancy_remarks = str(
                payload_row.get("discrepancy_remarks") or ""
            ).strip()

            if received_qty < 0 or missing_qty < 0 or damaged_qty < 0:
                frappe.throw(
                    "Receipt quantities cannot be negative for " +
                    str(item.get("item_code") or item.name) + "."
                )

            accounted_qty = received_qty + missing_qty + damaged_qty
            if abs(accounted_qty - released_qty) > tolerance:
                frappe.throw(
                    "Received + Missing + Damaged must equal Released Qty " +
                    str(released_qty) + " for " +
                    str(item.get("item_code") or item.name) +
                    ". Current total: " + str(accounted_qty) + "."
                )

            return_qty = missing_qty + damaged_qty
            if return_qty > tolerance and not discrepancy_remarks:
                frappe.throw(
                    "Enter discrepancy remarks for " +
                    str(item.get("item_code") or item.name) + "."
                )

            if return_qty > tolerance:
                has_discrepancy = True

            resolved.append({
                "stock_item": item,
                "stock_entry_detail": item.name,
                "item_code": item.get("item_code"),
                "item_name": item.get("item_name") or item.get("item_code"),
                "uom": item.get("uom") or item.get("stock_uom") or "Nos",
                "source_warehouse": item.get("s_warehouse") or life_receipt_adjustment_source_warehouse(stock_entry),
                "target_warehouse": item.get("t_warehouse") or life_receipt_adjustment_target_warehouse(stock_entry),
                "released_qty": released_qty,
                "received_qty": received_qty,
                "missing_qty": missing_qty,
                "damaged_qty": damaged_qty,
                "return_to_source_qty": return_qty,
                "discrepancy_type": life_receipt_adjustment_discrepancy_type(
                    missing_qty,
                    damaged_qty
                ),
                "discrepancy_remarks": discrepancy_remarks
            })

        if not has_discrepancy:
            frappe.throw(
                "No missing or damaged quantity was reported. " +
                "Use the normal receipt confirmation instead."
            )

        return resolved


    def life_receipt_adjustment_totals(rows):
        totals = {
            "released": 0,
            "received": 0,
            "missing": 0,
            "damaged": 0,
            "return_qty": 0
        }
        for row in rows:
            totals["released"] = totals.get("released", 0) + life_float(row.get("released_qty"), 0)
            totals["received"] = totals.get("received", 0) + life_float(row.get("received_qty"), 0)
            totals["missing"] = totals.get("missing", 0) + life_float(row.get("missing_qty"), 0)
            totals["damaged"] = totals.get("damaged", 0) + life_float(row.get("damaged_qty"), 0)
            totals["return_qty"] = totals.get("return_qty", 0) + life_float(row.get("return_to_source_qty"), 0)
        return totals


    def life_receipt_adjustment_existing(stock_entry_name):
        request_name = frappe.db.get_value(
            RECEIPT_ADJUSTMENT_DOCTYPE,
            {"stock_entry": stock_entry_name},
            "name"
        )
        if request_name:
            return frappe.get_doc(RECEIPT_ADJUSTMENT_DOCTYPE, request_name)
        return None


    def life_action_submit_receipt_adjustment(payload):
        life_require_login()
        life_receipt_adjustment_require_setup()

        stock_entry_name = str(payload.get("stock_entry") or "").strip()
        received_by = str(payload.get("received_by") or "").strip()
        receipt_remarks = str(
            payload.get("receipt_remarks") or payload.get("remarks") or ""
        ).strip()

        if not stock_entry_name:
            frappe.throw("Stock Entry name is required.")

        stock_entry = frappe.get_doc(SE_DOCTYPE, stock_entry_name)
        stock_entry.check_permission("read")

        if life_int(stock_entry.docstatus, 0) != 0:
            frappe.throw("This Stock Entry is no longer open for branch receipt.")

        purpose = str(
            stock_entry.get("purpose") or stock_entry.get("stock_entry_type") or ""
        ).strip()
        if purpose != "Material Transfer":
            frappe.throw("Only Material Transfer Stock Entries are supported.")

        target_warehouse = life_receipt_adjustment_target_warehouse(stock_entry)
        if not target_warehouse:
            frappe.throw("Receiving Warehouse is missing on the Stock Entry.")

        life_require_branch_warehouse(target_warehouse, "Receiving Warehouse")
        receiving_branch = life_branch_from_warehouse(target_warehouse)
        employee = life_validate_employee(received_by, receiving_branch)

        rows = life_receipt_adjustment_payload_rows(
            stock_entry,
            payload.get("items") or []
        )
        totals = life_receipt_adjustment_totals(rows)

        request = life_receipt_adjustment_existing(stock_entry.name)
        if request:
            status = str(request.get("status") or "Draft").strip()
            if status not in ["Draft", RECEIPT_ADJUSTMENT_CORRECTION]:
                frappe.throw(
                    "Adjustment request " + request.name + " is already " +
                    status + " and cannot be changed by the branch."
                )
            request.set("adjustment_items", [])
        else:
            request = frappe.new_doc(RECEIPT_ADJUSTMENT_DOCTYPE)
            if life_has_field(RECEIPT_ADJUSTMENT_DOCTYPE, "naming_series"):
                request.naming_series = "LSRA-.YYYY.-.#####"
            request.stock_entry = stock_entry.name

        material_request = life_receipt_adjustment_valid_material_request(stock_entry)
        request.status = RECEIPT_ADJUSTMENT_PENDING
        request.material_request = material_request or None
        request.company = stock_entry.get("company") or COMPANY_FALLBACK
        request.source_warehouse = life_receipt_adjustment_source_warehouse(stock_entry)
        request.target_warehouse = target_warehouse
        request.target_branch = receiving_branch or None
        request.reported_by = employee.get("name")
        request.reported_by_name = employee.get("employee_name") or employee.get("name")
        request.reported_on = frappe.utils.now()
        request.branch_receipt_remarks = receipt_remarks
        request.total_released_qty = totals.get("released")
        request.total_received_qty = totals.get("received")
        request.total_missing_qty = totals.get("missing")
        request.total_damaged_qty = totals.get("damaged")
        request.total_return_to_source_qty = totals.get("return_qty")
        request.stock_manager_remarks = ""
        request.approved_by = None
        request.approved_on = None
        request.submitted_stock_entry = None
        request.correction_requested_by = None
        request.correction_requested_on = None
        request.rejected_by = None
        request.rejected_on = None

        for row in rows:
            request.append("adjustment_items", {
                "stock_entry_detail": row.get("stock_entry_detail"),
                "item_code": row.get("item_code"),
                "item_name": row.get("item_name"),
                "uom": row.get("uom"),
                "source_warehouse": row.get("source_warehouse"),
                "target_warehouse": row.get("target_warehouse"),
                "released_qty": row.get("released_qty"),
                "received_qty": row.get("received_qty"),
                "missing_qty": row.get("missing_qty"),
                "damaged_qty": row.get("damaged_qty"),
                "return_to_source_qty": row.get("return_to_source_qty"),
                "discrepancy_type": row.get("discrepancy_type"),
                "row_status": "Pending Approval",
                "discrepancy_remarks": row.get("discrepancy_remarks")
            })

        if request.is_new():
            request.insert(ignore_permissions=True)
        else:
            request.save(ignore_permissions=True)

        return {
            "ok": True,
            "message": (
                "Receipt adjustment " + request.name +
                " is pending Stock Manager approval."
            ),
            "adjustment_request": request.as_dict(),
            "stock_entry": stock_entry.name
        }


    def life_receipt_adjustment_request_item_map(request):
        by_detail = {}
        by_item = {}
        for row in request.get("adjustment_items") or []:
            detail = str(row.get("stock_entry_detail") or "").strip()
            item_code = str(row.get("item_code") or "").strip()
            if detail:
                by_detail[detail] = row
            if item_code and item_code not in by_item:
                by_item[item_code] = row
        return {"by_detail": by_detail, "by_item": by_item}


    def life_receipt_adjustment_find_row(stock_item, request_map):
        detail = str(stock_item.get("name") or "").strip()
        item_code = str(stock_item.get("item_code") or "").strip()
        return (
            request_map.get("by_detail", {}).get(detail) or
            request_map.get("by_item", {}).get(item_code)
        )


    def life_receipt_adjustment_existing_reverse(request, original_stock_entry_name):
        submitted_name = str(request.get("submitted_stock_entry") or "").strip()
        if submitted_name and submitted_name != original_stock_entry_name:
            if frappe.db.exists(SE_DOCTYPE, submitted_name):
                return frappe.get_doc(SE_DOCTYPE, submitted_name)

        if not life_has_field(SE_ITEM_DOCTYPE, "custom_adjustment_request"):
            return None

        rows = frappe.get_all(
            SE_ITEM_DOCTYPE,
            filters={
                "custom_adjustment_request": request.name,
                "parenttype": SE_DOCTYPE,
                "parent": ["!=", original_stock_entry_name],
                "docstatus": ["<", 2]
            },
            fields=["parent"],
            order_by="creation desc",
            page_length=1
        )
        if rows and rows[0].get("parent"):
            return frappe.get_doc(SE_DOCTYPE, rows[0].get("parent"))
        return None


    def life_receipt_adjustment_apply_custom_fields(stock_item, adjustment_row, request_name):
        values = {
            "custom_released_qty": life_float(adjustment_row.get("released_qty"), 0),
            "custom_received_qty": life_float(adjustment_row.get("received_qty"), 0),
            "custom_missing_qty": life_float(adjustment_row.get("missing_qty"), 0),
            "custom_damaged_qty": life_float(adjustment_row.get("damaged_qty"), 0),
            "custom_return_to_source_qty": life_float(adjustment_row.get("return_to_source_qty"), 0),
            "custom_discrepancy_remarks": str(adjustment_row.get("discrepancy_remarks") or ""),
            "custom_adjustment_request": request_name
        }
        for fieldname, value in values.items():
            if life_has_field(SE_ITEM_DOCTYPE, fieldname):
                stock_item.set(fieldname, value)


    def life_receipt_adjustment_submit_original(request, stock_entry):
        request_map = life_receipt_adjustment_request_item_map(request)
        valid_request_names = life_receipt_adjustment_clear_cancelled_links(stock_entry)

        for stock_item in stock_entry.get("items") or []:
            adjustment_row = life_receipt_adjustment_find_row(stock_item, request_map)
            if not adjustment_row:
                frappe.throw(
                    "Adjustment quantities are missing for Stock Entry item " +
                    str(stock_item.get("item_code") or stock_item.name) + "."
                )
            released_qty = life_float(adjustment_row.get("released_qty"), 0)
            received_qty = life_float(adjustment_row.get("received_qty"), 0)
            missing_qty = life_float(adjustment_row.get("missing_qty"), 0)
            damaged_qty = life_float(adjustment_row.get("damaged_qty"), 0)
            if abs((received_qty + missing_qty + damaged_qty) - released_qty) > 0.0001:
                frappe.throw(
                    "Adjustment quantities are not balanced for " +
                    str(stock_item.get("item_code") or stock_item.name) + "."
                )
            if abs(life_float(stock_item.get("qty"), 0) - released_qty) > 0.0001:
                frappe.throw(
                    "The released quantity changed after the branch report for " +
                    str(stock_item.get("item_code") or stock_item.name) + "."
                )
            life_receipt_adjustment_apply_custom_fields(
                stock_item,
                adjustment_row,
                request.name
            )

        life_set_if_field(stock_entry, "custom_received_by", request.get("reported_by"))
        life_set_if_field(stock_entry, "custom_received_date", request.get("reported_on") or frappe.utils.now())
        life_set_if_field(stock_entry, "custom_branch_receipt_remarks", request.get("branch_receipt_remarks") or "")

        if life_int(stock_entry.docstatus, 0) == 0:
            stock_entry.save(ignore_permissions=True)
            stock_entry.submit()
            stock_entry.reload()
        elif life_int(stock_entry.docstatus, 0) != 1:
            frappe.throw("The original Stock Entry is cancelled and cannot be adjusted.")

        return {"stock_entry": stock_entry, "material_requests": valid_request_names}


    def life_receipt_adjustment_build_reverse(request, original_stock_entry):
        existing_reverse = life_receipt_adjustment_existing_reverse(
            request,
            original_stock_entry.name
        )
        if existing_reverse:
            if life_int(existing_reverse.docstatus, 0) == 0:
                existing_reverse.submit()
                existing_reverse.reload()
            if life_int(existing_reverse.docstatus, 0) != 1:
                frappe.throw("The existing reverse Stock Entry is not submitted.")
            return existing_reverse

        request_map = life_receipt_adjustment_request_item_map(request)
        reverse_items = []
        reverse_sources = []
        reverse_targets = []

        for stock_item in original_stock_entry.get("items") or []:
            adjustment_row = life_receipt_adjustment_find_row(stock_item, request_map)
            if not adjustment_row:
                continue

            return_qty = life_float(adjustment_row.get("return_to_source_qty"), 0)
            if return_qty <= 0.0001:
                continue

            if (
                stock_item.get("serial_and_batch_bundle") or
                stock_item.get("serial_no") or
                stock_item.get("batch_no")
            ):
                frappe.throw(
                    "Automatic reverse transfer is not supported for serial/batch-controlled item " +
                    str(stock_item.get("item_code") or stock_item.name) +
                    ". Create the reverse transfer manually with the correct Serial and Batch Bundle."
                )

            reverse_source = str(
                stock_item.get("t_warehouse") or request.get("target_warehouse") or ""
            ).strip()
            reverse_target = str(
                stock_item.get("s_warehouse") or adjustment_row.get("source_warehouse") or
                request.get("source_warehouse") or ""
            ).strip()

            if not reverse_source or not reverse_target:
                frappe.throw(
                    "Source or target warehouse is missing for reverse transfer item " +
                    str(stock_item.get("item_code") or stock_item.name) + "."
                )

            if reverse_source not in reverse_sources:
                reverse_sources.append(reverse_source)
            if reverse_target not in reverse_targets:
                reverse_targets.append(reverse_target)

            values = {
                "item_code": stock_item.get("item_code"),
                "qty": return_qty,
                "uom": stock_item.get("uom") or stock_item.get("stock_uom") or "Nos",
                "stock_uom": stock_item.get("stock_uom") or stock_item.get("uom") or "Nos",
                "conversion_factor": life_float(stock_item.get("conversion_factor"), 1) or 1,
                "s_warehouse": reverse_source,
                "t_warehouse": reverse_target
            }

            for fieldname in ["cost_center", "allow_zero_valuation_rate"]:
                if stock_item.get(fieldname) is not None and life_has_field(SE_ITEM_DOCTYPE, fieldname):
                    values[fieldname] = stock_item.get(fieldname)

            custom_values = {
                "custom_released_qty": adjustment_row.get("released_qty"),
                "custom_received_qty": adjustment_row.get("received_qty"),
                "custom_missing_qty": adjustment_row.get("missing_qty"),
                "custom_damaged_qty": adjustment_row.get("damaged_qty"),
                "custom_return_to_source_qty": return_qty,
                "custom_discrepancy_remarks": adjustment_row.get("discrepancy_remarks") or "",
                "custom_adjustment_request": request.name
            }
            for fieldname, value in custom_values.items():
                if life_has_field(SE_ITEM_DOCTYPE, fieldname):
                    values[fieldname] = value

            reverse_items.append(values)

        if not reverse_items:
            frappe.throw("No missing or damaged quantity is available for reverse transfer.")

        reverse_entry = frappe.new_doc(SE_DOCTYPE)
        reverse_entry.stock_entry_type = "Material Transfer"
        reverse_entry.purpose = "Material Transfer"
        reverse_entry.company = original_stock_entry.get("company") or request.get("company") or COMPANY_FALLBACK
        if len(reverse_sources) == 1:
            reverse_entry.from_warehouse = reverse_sources[0]
        if len(reverse_targets) == 1:
            reverse_entry.to_warehouse = reverse_targets[0]
        reverse_entry.remarks = (
            "Reverse receipt adjustment " + request.name +
            " against original Stock Entry " + original_stock_entry.name +
            ". Missing Qty: " + str(request.get("total_missing_qty") or 0) +
            ", Damaged Qty: " + str(request.get("total_damaged_qty") or 0) + "."
        )

        for values in reverse_items:
            reverse_entry.append("items", values)

        reverse_entry.insert(ignore_permissions=True)
        reverse_entry.submit()
        reverse_entry.reload()

        if life_int(reverse_entry.docstatus, 0) != 1:
            frappe.throw("ERPNext did not submit the reverse Material Transfer.")

        return reverse_entry


    def life_action_approve_receipt_adjustment(payload):
        life_require_ho()
        life_receipt_adjustment_require_setup()

        request_name = str(
            payload.get("request_name") or payload.get("name") or ""
        ).strip()
        manager_remarks = str(
            payload.get("remarks") or payload.get("stock_manager_remarks") or ""
        ).strip()

        if not request_name:
            frappe.throw("Receipt Adjustment Request name is required.")

        request = frappe.get_doc(RECEIPT_ADJUSTMENT_DOCTYPE, request_name)
        status = str(request.get("status") or "Draft").strip()

        if status == RECEIPT_ADJUSTMENT_COMPLETED:
            original = frappe.get_doc(SE_DOCTYPE, request.get("stock_entry"))
            reverse = None
            reverse_name = str(request.get("submitted_stock_entry") or "").strip()
            if reverse_name and frappe.db.exists(SE_DOCTYPE, reverse_name):
                reverse = frappe.get_doc(SE_DOCTYPE, reverse_name)
            return {
                "ok": True,
                "message": "Receipt adjustment was already completed.",
                "adjustment_request": request.as_dict(),
                "original_stock_entry": original.as_dict(),
                "adjustment_stock_entry": reverse.as_dict() if reverse else None,
                "already_completed": True
            }

        if status not in [RECEIPT_ADJUSTMENT_PENDING, RECEIPT_ADJUSTMENT_APPROVED]:
            frappe.throw(
                "Only Pending or Approved receipt adjustments can be completed."
            )

        material_request = str(request.get("material_request") or "").strip()
        if material_request:
            if (
                not frappe.db.exists(MR_DOCTYPE, material_request) or
                life_int(frappe.db.get_value(MR_DOCTYPE, material_request, "docstatus"), 0) == 2
            ):
                request.material_request = None

        original_stock_entry = frappe.get_doc(
            SE_DOCTYPE,
            request.get("stock_entry")
        )

        purpose = str(
            original_stock_entry.get("purpose") or
            original_stock_entry.get("stock_entry_type") or ""
        ).strip()
        if purpose != "Material Transfer":
            frappe.throw("The original Stock Entry is not a Material Transfer.")

        request.status = RECEIPT_ADJUSTMENT_APPROVED
        request.stock_manager_remarks = manager_remarks
        request.approved_by = life_require_login()
        request.approved_on = frappe.utils.now()

        original_result = life_receipt_adjustment_submit_original(
            request,
            original_stock_entry
        )
        original_stock_entry = original_result.get("stock_entry")

        reverse_stock_entry = life_receipt_adjustment_build_reverse(
            request,
            original_stock_entry
        )

        request.status = RECEIPT_ADJUSTMENT_COMPLETED
        request.submitted_stock_entry = reverse_stock_entry.name
        for row in request.get("adjustment_items") or []:
            row.row_status = "Approved"
        request.save(ignore_permissions=True)

        for request_name_value in original_result.get("material_requests") or []:
            life_db_set_if_field(
                MR_DOCTYPE,
                request_name_value,
                "custom_stock_request_status",
                "Completed"
            )
            life_db_set_if_field(
                MR_DOCTYPE,
                request_name_value,
                "transfer_status",
                "Completed"
            )

        return {
            "ok": True,
            "message": (
                "Original Stock Entry " + original_stock_entry.name +
                " was submitted and reverse Material Transfer " +
                reverse_stock_entry.name + " returned Missing + Damaged stock " +
                "to the source warehouse."
            ),
            "adjustment_request": request.as_dict(),
            "original_stock_entry": original_stock_entry.as_dict(),
            "adjustment_stock_entry": reverse_stock_entry.as_dict(),
            "already_completed": False
        }


    def life_action_decide_receipt_adjustment(payload):
        life_require_ho()
        life_receipt_adjustment_require_setup()

        request_name = str(
            payload.get("request_name") or payload.get("name") or ""
        ).strip()
        decision = str(payload.get("decision") or "").strip().lower()
        remarks = str(
            payload.get("remarks") or payload.get("stock_manager_remarks") or ""
        ).strip()

        if not request_name:
            frappe.throw("Receipt Adjustment Request name is required.")
        if decision not in ["correction", "reject"]:
            frappe.throw("Decision must be correction or reject.")
        if not remarks:
            frappe.throw("Stock Manager Remarks are required.")

        request = frappe.get_doc(RECEIPT_ADJUSTMENT_DOCTYPE, request_name)
        if str(request.get("status") or "").strip() != RECEIPT_ADJUSTMENT_PENDING:
            frappe.throw("Only a pending receipt adjustment can be updated.")

        material_request = str(request.get("material_request") or "").strip()
        if material_request:
            if (
                not frappe.db.exists(MR_DOCTYPE, material_request) or
                life_int(frappe.db.get_value(MR_DOCTYPE, material_request, "docstatus"), 0) == 2
            ):
                request.material_request = None

        request.stock_manager_remarks = remarks
        current_user = life_require_login()
        current_time = frappe.utils.now()

        if decision == "correction":
            request.status = RECEIPT_ADJUSTMENT_CORRECTION
            request.correction_requested_by = current_user
            request.correction_requested_on = current_time
            row_status = "Correction Requested"
            message = "Receipt adjustment returned to the branch for correction."
        else:
            request.status = RECEIPT_ADJUSTMENT_REJECTED
            request.rejected_by = current_user
            request.rejected_on = current_time
            row_status = "Rejected"
            message = "Receipt adjustment rejected. No stock was changed."

        for row in request.get("adjustment_items") or []:
            row.row_status = row_status

        request.save(ignore_permissions=True)

        return {
            "ok": True,
            "message": message,
            "adjustment_request": request.as_dict()
        }


    def life_gateway_method_allowed(method):
        method = str(method or "").strip()
        return method in LIFE_GATEWAY_ALLOWED_METHODS


    def life_gateway_nested_call_begin():
        saved = {}

        for key in ["cmd", "action", "payload"]:
            if key in frappe.form_dict:
                saved[key] = frappe.form_dict.get(key)
                frappe.form_dict.pop(key)

        return saved


    def life_gateway_nested_call_end(saved):
        if not isinstance(saved, dict):
            return

        for key, value in saved.items():
            frappe.form_dict[key] = value


    def life_gateway_workflow_get_transitions(doc):
        saved = life_gateway_nested_call_begin()

        try:
            return _call_whitelisted(
                "frappe.model.workflow.get_transitions",
                doc=doc
            )
        finally:
            life_gateway_nested_call_end(saved)


    def life_gateway_workflow_apply(doc, action_name):
        saved = life_gateway_nested_call_begin()

        try:
            return _call_whitelisted(
                "frappe.model.workflow.apply_workflow",
                doc=doc,
                action=action_name
            )
        finally:
            life_gateway_nested_call_end(saved)


    def life_gateway_query_report(
        report_name,
        filters,
        ignore_prepared_report=1,
        are_default_filters=0
    ):
        saved = life_gateway_nested_call_begin()

        if isinstance(filters, dict):
            filters_value = json.dumps(filters)
        else:
            filters_value = str(filters or "{}")

        ignore_value = 1 if life_int(ignore_prepared_report, 1) else 0
        default_value = 1 if life_int(are_default_filters, 0) else 0

        try:
            return _call_whitelisted(
                "frappe.desk.query_report.run",
                report_name=str(report_name or "").strip(),
                filters=filters_value,
                ignore_prepared_report=ignore_value,
                are_default_filters=default_value
            )
        finally:
            life_gateway_nested_call_end(saved)


    def life_gateway_get_list(args):
        doctype = str(args.get("doctype") or "").strip()
        if not doctype:
            frappe.throw("DocType is required.")

        fields = args.get("fields") or ["name"]
        filters = args.get("filters") or {}
        or_filters = args.get("or_filters") or {}
        order_by = str(args.get("order_by") or "modified desc").strip()
        group_by = str(args.get("group_by") or "").strip()
        limit_start = max(0, life_int(args.get("limit_start"), 0))
        limit_page_length = life_int(args.get("limit_page_length"), 20)

        if limit_page_length <= 0:
            limit_page_length = 5000

        if group_by:
            return frappe.get_list(
                doctype,
                fields=fields,
                filters=filters,
                or_filters=or_filters,
                order_by=order_by,
                group_by=group_by,
                limit_start=limit_start,
                limit_page_length=limit_page_length
            )

        return frappe.get_list(
            doctype,
            fields=fields,
            filters=filters,
            or_filters=or_filters,
            order_by=order_by,
            limit_start=limit_start,
            limit_page_length=limit_page_length
        )


    def life_gateway_get_count(args):
        doctype = str(args.get("doctype") or "").strip()
        if not doctype:
            frappe.throw("DocType is required.")

        rows = frappe.get_list(
            doctype,
            fields=["count(name) as total_count"],
            filters=args.get("filters") or {},
            or_filters=args.get("or_filters") or {},
            limit_start=0,
            limit_page_length=1
        )

        if not rows:
            return 0

        return life_int(rows[0].get("total_count"), 0)


    def life_gateway_get_doc(args):
        doctype = str(args.get("doctype") or "").strip()
        name = str(args.get("name") or "").strip()

        if not doctype:
            frappe.throw("DocType is required.")

        if not name:
            rows = frappe.get_list(
                doctype,
                fields=["name"],
                filters=args.get("filters") or {},
                limit_start=0,
                limit_page_length=1
            )

            if not rows:
                return None

            name = str(rows[0].get("name") or "").strip()

        if not name:
            return None

        doc = frappe.get_doc(doctype, name)
        doc.check_permission("read")
        return doc.as_dict()


    def life_gateway_get_value(args):
        doctype = str(args.get("doctype") or "").strip()
        if not doctype:
            frappe.throw("DocType is required.")

        fieldname = args.get("fieldname") or "name"

        if isinstance(fieldname, (list, tuple)):
            fields = []
            for field in fieldname:
                clean_field = str(field or "").strip()
                if clean_field:
                    fields.append(clean_field)
        else:
            fields = [str(fieldname or "name").strip()]

        if not fields:
            fields = ["name"]

        rows = frappe.get_list(
            doctype,
            fields=fields,
            filters=args.get("filters") or {},
            limit_start=0,
            limit_page_length=1
        )

        if not rows:
            return {}

        return rows[0]


    def life_gateway_parse_doc(value):
        if isinstance(value, str):
            value = json.loads(value)

        if not isinstance(value, dict):
            frappe.throw("Document data must be a JSON object.")

        return value


    def life_gateway_insert(args):
        doc_data = life_gateway_parse_doc(args.get("doc"))
        doc = frappe.get_doc(doc_data)
        doc.insert()
        return doc.as_dict()


    def life_gateway_submit(args):
        doc_data = life_gateway_parse_doc(args.get("doc"))
        doc = frappe.get_doc(doc_data)
        doc.submit()
        return doc.as_dict()


    def life_gateway_cancel(args):
        doctype = str(args.get("doctype") or "").strip()
        name = str(args.get("name") or "").strip()

        if not doctype or not name:
            frappe.throw("DocType and document name are required.")

        doc = frappe.get_doc(doctype, name)
        doc.cancel()
        return doc.as_dict()


    def life_gateway_set_value(args):
        doctype = str(args.get("doctype") or "").strip()
        name = str(args.get("name") or "").strip()
        fieldname = args.get("fieldname")
        value = args.get("value")

        if not doctype or not name:
            frappe.throw("DocType and document name are required.")

        doc = frappe.get_doc(doctype, name)
        doc.check_permission("write")

        if isinstance(fieldname, dict):
            for key, field_value in fieldname.items():
                doc.set(key, field_value)
        else:
            clean_fieldname = str(fieldname or "").strip()
            if not clean_fieldname:
                frappe.throw("Field name is required.")
            doc.set(clean_fieldname, value)

        doc.save()
        return doc.as_dict()


    def life_gateway_monthly_indent_access(args):
        settings_doctype = "LIFE Stock Request Settings"
        settings_field = "enable_monthly_indent_exception"
        requested_action = str(args.get("action") or "get").strip().lower()

        if requested_action not in ["get", "set", "status"]:
            frappe.throw("Unsupported Monthly Indent access action.")

        enabled = life_int(
            frappe.db.get_single_value(
                settings_doctype,
                settings_field
            ),
            0
        )

        if requested_action == "set":
            life_require_ho()

            enabled = 1 if life_int(args.get("enabled"), 0) else 0

            frappe.db.set_single_value(
                settings_doctype,
                settings_field,
                enabled
            )

        return {
            "enabled": enabled,
            "action": requested_action
        }


    def life_gateway_dispatch(method, args):
        if method == "frappe.client.get_list":
            return life_gateway_get_list(args)

        if method == "frappe.client.get_count":
            return life_gateway_get_count(args)

        if method == "frappe.client.get":
            return life_gateway_get_doc(args)

        if method == "frappe.client.get_value":
            return life_gateway_get_value(args)

        if method == "frappe.client.insert":
            return life_gateway_insert(args)

        if method == "frappe.client.submit":
            return life_gateway_submit(args)

        if method == "frappe.client.cancel":
            return life_gateway_cancel(args)

        if method == "frappe.client.set_value":
            return life_gateway_set_value(args)

        if method == "frappe.model.workflow.get_transitions":
            return life_gateway_workflow_get_transitions(
                args.get("doc")
            )

        if method == "frappe.model.workflow.apply_workflow":
            return life_gateway_workflow_apply(
                args.get("doc"),
                str(args.get("action") or "").strip()
            )

        if method == "frappe.desk.query_report.run":
            return life_gateway_query_report(
                args.get("report_name"),
                args.get("filters") or {},
                args.get("ignore_prepared_report"),
                args.get("are_default_filters")
            )

        if method == "life_monthly_indent_access":
            return life_gateway_monthly_indent_access(args)

        frappe.throw(
            "No dispatcher is configured for the LIFE Stock API method: " +
            str(method)
        )


    def life_action_invoke(payload):
        life_require_login()

        method = str(payload.get("method") or "").strip()
        args = payload.get("args") or {}

        if not life_gateway_method_allowed(method):
            frappe.throw(
                "This server method is not allowed through the LIFE Stock API: " +
                str(method),
                frappe.PermissionError
            )

        if not isinstance(args, dict):
            frappe.throw("API method arguments must be a JSON object.")

        result = life_gateway_dispatch(method, args)

        return {
            "ok": True,
            "method": method,
            "data": life_gateway_serializable(result)
        }


    def life_action_batch(payload):
        life_require_login()

        operations = payload.get("operations") or []
        if not isinstance(operations, list):
            frappe.throw("Batch operations must be a list.")
        if len(operations) > 30:
            frappe.throw("A maximum of 30 API operations is allowed in one batch.")

        results = []
        for index, operation in enumerate(operations):
            if not isinstance(operation, dict):
                frappe.throw("Invalid batch operation at position " + str(index + 1) + ".")

            method = str(operation.get("method") or "").strip()
            args = operation.get("args") or {}

            try:
                response = life_action_invoke({
                    "method": method,
                    "args": args
                })
                results.append({
                    "ok": True,
                    "method": method,
                    "data": response.get("data")
                })
            except Exception as error:
                results.append({
                    "ok": False,
                    "method": method,
                    "message": str(error)
                })

        return {
            "ok": True,
            "results": results
        }


    def life_action_upload_file(payload):
        life_require_login()

        try:
            files = frappe.request.files
        except Exception:
            files = None

        upload = files.get("file") if files else None
        if not upload:
            frappe.throw("No file was received.")

        try:
            stream = upload.stream
        except Exception:
            stream = upload

        content = stream.read()
        if content is None:
            frappe.throw("The uploaded file could not be read.")

        maximum_bytes = 10 * 1024 * 1024
        if len(content) > maximum_bytes:
            frappe.throw("The uploaded file exceeds the 10 MB limit.")

        try:
            uploaded_file_name = upload.filename
        except Exception:
            uploaded_file_name = None

        file_name = str(
            uploaded_file_name or
            payload.get("file_name") or
            "upload.bin"
        ).strip()

        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "is_private": life_int(payload.get("is_private"), 1),
            "content": content,
            "attached_to_doctype": str(payload.get("attached_to_doctype") or "").strip() or None,
            "attached_to_name": str(payload.get("attached_to_name") or "").strip() or None,
            "attached_to_field": str(payload.get("attached_to_field") or "").strip() or None
        })
        file_doc.insert()

        return {
            "ok": True,
            "file_name": file_doc.name,
            "file_url": file_doc.file_url,
            "is_private": file_doc.is_private
        }


    def life_si_cache_get(cache_key):
        try:
            return frappe.cache().get_value(cache_key)
        except Exception:
            return None


    def life_si_cache_set(cache_key, value, expires_in_sec):
        try:
            frappe.cache().set_value(
                cache_key,
                value,
                expires_in_sec=expires_in_sec
            )
        except Exception:
            pass


    def life_si_cache_key(phase, payload):
        keys = [
            "from_date",
            "to_date",
            "prev_from_date",
            "prev_to_date",
            "fc1_from_date",
            "fc1_to_date",
            "fc2_from_date",
            "fc2_to_date",
            "fc3_from_date",
            "fc3_to_date",
            "ledger_from_date",
            "ledger_to_date"
        ]

        parts = [
            "life_stock_intelligence_v7_item_doctype_valuation",
            str(phase or "core"),
            LIFE_STOCK_INTELLIGENCE_COMPANY
        ]

        for key in keys:
            parts.append(str(payload.get(key) or ""))

        return ":".join(parts)


    def life_si_report(report_name, filters):
        return life_gateway_query_report(
            report_name,
            filters,
            1,
            1
        )


    def life_si_safe_load(pack, failed, key, loader):
        try:
            pack[key] = life_gateway_serializable(loader())
        except Exception as error:
            pack[key] = []
            failed.append(key + ": " + str(error))


    def life_si_item_group_map(item_codes):
        output = {}
        codes = []
        for item_code in item_codes or []:
            item_code = str(item_code or "").strip()
            if item_code and item_code not in codes:
                codes.append(item_code)

        chunk_size = 500
        start = 0
        while start < len(codes):
            chunk = codes[start:start + chunk_size]
            rows = frappe.get_all(
                "Item",
                filters={"name": ["in", chunk]},
                fields=["name", "item_group"],
                page_length=len(chunk)
            )
            for row in rows:
                output[str(row.get("name") or "")] = str(row.get("item_group") or "")
            start = start + chunk_size

        return output



    def life_si_report_rows(report_data):
        """Return the row list from the ERPNext report response shape."""
        if isinstance(report_data, list):
            return report_data

        if isinstance(report_data, dict):
            result = report_data.get("result")
            if isinstance(result, list):
                return result

            message = report_data.get("message")
            if isinstance(message, dict):
                nested_result = message.get("result")
                if isinstance(nested_result, list):
                    return nested_result

            if isinstance(message, list):
                return message

        return []


    def life_si_item_valuation_rate_map(item_codes):
        """
    Return Item.valuation_rate for the requested item codes.

    Stock Intelligence monetary rule:
    - quantity source: ERPNext Stock Balance / Stock Ledger
    - rate source: Item.valuation_rate only
    - no Item Price / selling price / purchase-rate fallback
    - missing or zero valuation_rate = 0
    """
        clean_codes = []

        for item_code in item_codes or []:
            item_code = str(item_code or "").strip()
            if item_code and item_code not in clean_codes:
                clean_codes.append(item_code)

        output = {}
        chunk_size = 500
        start = 0

        while start < len(clean_codes):
            chunk = clean_codes[start:start + chunk_size]

            rows = frappe.get_all(
                "Item",
                filters={"name": ["in", chunk]},
                fields=["name", "valuation_rate"],
                page_length=len(chunk)
            )

            for row in rows or []:
                item_code = str(row.get("name") or "").strip()
                if not item_code:
                    continue

                output[item_code] = life_float(
                    row.get("valuation_rate"),
                    0
                )

            start = start + chunk_size

        return output


    def life_si_apply_item_valuation_rates(report_data):
        """
    Keep ERPNext Stock Balance quantities, but rebuild monetary fields from
    Item.valuation_rate.

    Existing frontend field names stay compatible:
    - val_rate = Item.valuation_rate
    - bal_val = bal_qty * Item.valuation_rate
    - opening_val / in_val / out_val = corresponding qty * Item.valuation_rate
    """
        rows = life_si_report_rows(report_data)
        if not rows:
            return report_data

        item_codes = []

        for row in rows:
            # Query Reports may append a final Total row as a list.
            if not isinstance(row, dict):
                continue

            item_code = str(row.get("item_code") or "").strip()
            if item_code and item_code not in item_codes:
                item_codes.append(item_code)

        rate_map = life_si_item_valuation_rate_map(item_codes)

        for row in rows:
            if not isinstance(row, dict):
                continue

            item_code = str(row.get("item_code") or "").strip()
            item_rate = life_float(rate_map.get(item_code), 0)

            # Preserve original Stock Balance valuation for diagnostics only.
            row["stock_balance_val_rate"] = life_float(row.get("val_rate"), 0)
            row["stock_balance_bal_val"] = life_float(row.get("bal_val"), 0)
            row["stock_balance_opening_val"] = life_float(row.get("opening_val"), 0)
            row["stock_balance_in_val"] = life_float(row.get("in_val"), 0)
            row["stock_balance_out_val"] = life_float(row.get("out_val"), 0)

            row["item_valuation_rate"] = item_rate
            row["valuation_rate_source"] = "Item.valuation_rate"
            row["valuation_rate_missing"] = 0 if item_rate > 0 else 1

            # Compatibility alias used by the existing Stock Intelligence JS.
            row["val_rate"] = item_rate

            if "opening_qty" in row:
                row["opening_val"] = (
                    life_float(row.get("opening_qty"), 0) * item_rate
                )

            if "in_qty" in row:
                row["in_val"] = (
                    life_float(row.get("in_qty"), 0) * item_rate
                )

            if "out_qty" in row:
                row["out_val"] = (
                    life_float(row.get("out_qty"), 0) * item_rate
                )

            if "bal_qty" in row:
                row["bal_val"] = (
                    life_float(row.get("bal_qty"), 0) * item_rate
                )

        return report_data


    def life_si_aggregate_ledger(from_date, to_date, mode):
        filters = {
            "company": LIFE_STOCK_INTELLIGENCE_COMPANY,
            "posting_date": ["between", [from_date, to_date]],
            "is_cancelled": 0
        }

        if mode == "movement":
            filters["actual_qty"] = ["<", 0]
            or_filters = None
        else:
            or_filters = {
                "actual_qty": ["<", 0],
                "stock_value_difference": ["<", 0]
            }

        rows = frappe.get_all(
            "Stock Ledger Entry",
            filters=filters,
            or_filters=or_filters,
            fields=[
                "item_code",
                "warehouse",
                "actual_qty",
                "stock_value_difference",
                "valuation_rate",
                "posting_date"
            ],
            order_by="posting_date asc",
            page_length=100000
        )

        aggregate = {}
        item_codes = []

        for row in rows:
            item_code = str(row.get("item_code") or "").strip()
            warehouse = str(row.get("warehouse") or "").strip()
            if not item_code or not warehouse:
                continue

            if item_code not in item_codes:
                item_codes.append(item_code)

            key = item_code + "||" + warehouse
            if key not in aggregate:
                aggregate[key] = {
                    "item_code": item_code,
                    "warehouse": warehouse,
                    "actual_qty": 0,
                    "stock_value_difference": 0,
                    "valuation_rate": 0,
                    "posting_date": ""
                }

            target = aggregate[key]
            actual_qty = life_float(row.get("actual_qty"), 0)
            value_difference = life_float(row.get("stock_value_difference"), 0)
            valuation_rate = life_float(row.get("valuation_rate"), 0)
            posting_date = str(row.get("posting_date") or "")

            if actual_qty < 0:
                target["actual_qty"] = target.get("actual_qty", 0) - abs(actual_qty)

            if value_difference < 0:
                target["stock_value_difference"] = target.get("stock_value_difference", 0) - abs(value_difference)

            if valuation_rate > 0:
                target["valuation_rate"] = valuation_rate

            if posting_date > target["posting_date"]:
                target["posting_date"] = posting_date

        item_groups = life_si_item_group_map(item_codes)
        rate_map = life_si_item_valuation_rate_map(item_codes)
        output = []

        for row in aggregate.values():
            item_code = str(row.get("item_code") or "").strip()
            item_rate = life_float(rate_map.get(item_code), 0)

            # Preserve original Stock Ledger valuation for diagnostics only.
            row["stock_ledger_valuation_rate"] = life_float(
                row.get("valuation_rate"),
                0
            )
            row["stock_ledger_value_difference"] = life_float(
                row.get("stock_value_difference"),
                0
            )

            row["item_valuation_rate"] = item_rate
            row["valuation_rate_source"] = "Item.valuation_rate"
            row["valuation_rate_missing"] = 0 if item_rate > 0 else 1

            # Compatibility aliases for the current frontend.
            row["valuation_rate"] = item_rate

            movement_qty = life_float(row.get("actual_qty"), 0)
            if movement_qty < 0:
                row["stock_value_difference"] = (
                    -abs(movement_qty) * item_rate
                )
            else:
                row["stock_value_difference"] = 0

            row["item_group"] = item_groups.get(item_code, "")
            output.append(row)

        return output


    def life_si_warehouses():
        rows = frappe.get_list(
            "Warehouse",
            filters={
                "company": LIFE_STOCK_INTELLIGENCE_COMPANY,
                "disabled": 0
            },
            fields=["name", "is_group", "company", "disabled"],
            order_by="name asc",
            page_length=1000
        )
        return rows


    def life_si_sessions(from_date, to_date):
        return frappe.get_list(
            "Therapy Session",
            filters={
                "start_date": ["between", [from_date, to_date]],
                "docstatus": ["!=", 2]
            },
            fields=[
                "name",
                "patient",
                "therapy_type",
                "service_unit",
                "start_date",
                "docstatus",
                "owner"
            ],
            order_by="start_date desc",
            page_length=10000
        )


    def life_si_assets():
        return frappe.get_list(
            "Asset",
            filters={"status": "Submitted"},
            fields=[
                "name",
                "docstatus",
                "asset_name",
                "asset_category",
                "location",
                "gross_purchase_amount",
                "status",
                "image"
            ],
            order_by="modified desc",
            page_length=5000
        )


    def life_si_batches():
        today = frappe.utils.today()
        next_30_days = frappe.utils.add_days(today, 30)

        return frappe.get_list(
            "Batch",
            filters={
                "disabled": 0,
                "expiry_date": ["between", [today, next_30_days]]
            },
            fields=[
                "name",
                "batch_id",
                "item_name",
                "batch_qty",
                "item",
                "expiry_date",
                "disabled"
            ],
            order_by="expiry_date asc",
            page_length=5000
        )


    def life_action_stock_intelligence(payload):
        life_require_ho()

        phase = str(payload.get("phase") or "core").strip().lower()
        if phase not in ["core", "trends"]:
            frappe.throw("Stock Intelligence phase must be core or trends.")

        required_dates = ["from_date", "to_date"]
        if phase == "trends":
            required_dates = required_dates + [
                "prev_from_date",
                "prev_to_date",
                "fc1_from_date",
                "fc1_to_date",
                "fc2_from_date",
                "fc2_to_date",
                "fc3_from_date",
                "fc3_to_date"
            ]

        for fieldname in required_dates:
            if not str(payload.get(fieldname) or "").strip():
                frappe.throw("Missing Stock Intelligence date: " + fieldname)

        force_refresh = bool(life_int(payload.get("force_refresh"), 0))
        cache_key = life_si_cache_key(phase, payload)

        if not force_refresh:
            cached = life_si_cache_get(cache_key)
            if cached:
                cached["ok"] = True
                cached["cached"] = True
                return cached

        pack = {}
        failed = []

        company = LIFE_STOCK_INTELLIGENCE_COMPANY
        from_date = str(payload.get("from_date"))
        to_date = str(payload.get("to_date"))


        if phase == "core":
            ledger_from_date = str(
                payload.get("ledger_from_date") or
                frappe.utils.add_months(to_date, -4)
            )
            ledger_to_date = str(payload.get("ledger_to_date") or to_date)

            life_si_safe_load(
                pack,
                failed,
                "warehouses",
                lambda: life_si_warehouses()
            )
            life_si_safe_load(
                pack,
                failed,
                "stockBalanceCurrent",
                lambda: life_si_report(
                    "Stock Balance",
                    {
                        "company": company,
                        "from_date": from_date,
                        "to_date": to_date,
                        "item_code": [],
                        "warehouse": [],
                        "valuation_field_type": "Currency"
                    }
                )
            )

            # Stock Balance remains the quantity source. Convert only its
            # monetary fields to Item.valuation_rate after the known-good
            # ERPNext report call has completed.
            if pack.get("stockBalanceCurrent"):
                try:
                    pack["stockBalanceCurrent"] = life_si_apply_item_valuation_rates(
                        pack.get("stockBalanceCurrent")
                    )
                except Exception as error:
                    pack["stockBalanceCurrent"] = []
                    failed.append(
                        "stockBalanceCurrent Item valuation conversion: " + str(error)
                    )
            life_si_safe_load(
                pack,
                failed,
                "stockProjected",
                lambda: life_si_report(
                    "Stock Projected Qty",
                    {"company": company}
                )
            )
            life_si_safe_load(
                pack,
                failed,
                "stockLedger4m",
                lambda: life_si_aggregate_ledger(
                    ledger_from_date,
                    ledger_to_date,
                    "movement"
                )
            )
            life_si_safe_load(
                pack,
                failed,
                "assets",
                lambda: life_si_assets()
            )
            life_si_safe_load(
                pack,
                failed,
                "batches",
                lambda: life_si_batches()
            )

            expires = LIFE_STOCK_INTELLIGENCE_CORE_CACHE_SECONDS

        else:
            prev_from_date = str(payload.get("prev_from_date"))
            prev_to_date = str(payload.get("prev_to_date"))

            fc1_from_date = str(payload.get("fc1_from_date"))
            fc1_to_date = str(payload.get("fc1_to_date"))
            fc2_from_date = str(payload.get("fc2_from_date"))
            fc2_to_date = str(payload.get("fc2_to_date"))
            fc3_from_date = str(payload.get("fc3_from_date"))
            fc3_to_date = str(payload.get("fc3_to_date"))

            life_si_safe_load(
                pack,
                failed,
                "stockBalancePrevious",
                lambda: life_si_report(
                    "Stock Balance",
                    {
                        "company": company,
                        "from_date": prev_from_date,
                        "to_date": prev_to_date,
                        "item_code": [],
                        "warehouse": [],
                        "valuation_field_type": "Currency"
                    }
                )
            )

            # Previous-period quantity is also valued using the current
            # Item.valuation_rate, so all Stock Intelligence monetary values use
            # one consistent Item-master rate source.
            if pack.get("stockBalancePrevious"):
                try:
                    pack["stockBalancePrevious"] = life_si_apply_item_valuation_rates(
                        pack.get("stockBalancePrevious")
                    )
                except Exception as error:
                    pack["stockBalancePrevious"] = []
                    failed.append(
                        "stockBalancePrevious Item valuation conversion: " + str(error)
                    )
            life_si_safe_load(
                pack,
                failed,
                "forecastLedger1",
                lambda: life_si_aggregate_ledger(
                    fc1_from_date,
                    fc1_to_date,
                    "forecast"
                )
            )
            life_si_safe_load(
                pack,
                failed,
                "forecastLedger2",
                lambda: life_si_aggregate_ledger(
                    fc2_from_date,
                    fc2_to_date,
                    "forecast"
                )
            )
            life_si_safe_load(
                pack,
                failed,
                "forecastLedger3",
                lambda: life_si_aggregate_ledger(
                    fc3_from_date,
                    fc3_to_date,
                    "forecast"
                )
            )
            life_si_safe_load(
                pack,
                failed,
                "therapySessions",
                lambda: life_si_sessions(from_date, to_date)
            )
            life_si_safe_load(
                pack,
                failed,
                "therapySessionsPrev",
                lambda: life_si_sessions(prev_from_date, prev_to_date)
            )
            life_si_safe_load(
                pack,
                failed,
                "therapyRevenue",
                lambda: life_si_report(
                    "ITEM WISE SALES – COLLECTION",
                    {
                        "from_date": from_date,
                        "to_date": to_date
                    }
                )
            )
            life_si_safe_load(
                pack,
                failed,
                "therapyRevenuePrev",
                lambda: life_si_report(
                    "ITEM WISE SALES – COLLECTION",
                    {
                        "from_date": prev_from_date,
                        "to_date": prev_to_date
                    }
                )
            )

            # These arrays were previously loaded only to recover Item Group names.
            # Aggregated ledger rows now include item_group, so the duplicate
            # Stock Balance report executions are no longer required.
            pack["stockBalanceOlder"] = []
            pack["forecastStock1"] = []
            pack["forecastStock2"] = []
            pack["forecastStock3"] = []

            expires = LIFE_STOCK_INTELLIGENCE_TRENDS_CACHE_SECONDS

        response = {
            "ok": True,
            "phase": phase,
            "cached": False,
            "generated_at": frappe.utils.now(),
            "data": pack,
            "failed": failed
        }

        life_si_cache_set(cache_key, response, expires)
        return response


    # ----------------------------------------------------------------------------
    # API DISPATCH
    # ----------------------------------------------------------------------------
    life_require_login()
    request_payload = life_payload()
    action = str(
        frappe.form_dict.get("action") or
        request_payload.get("action") or
        "list_requests"
    ).strip().lower()

    if action == "get_context":
        result = life_action_get_context(request_payload)
    elif action == "check_setup":
        result = life_action_check_setup(request_payload)
    elif action == "list_requests":
        result = life_action_list_requests(request_payload)
    elif action == "get_request":
        result = life_action_get_request(request_payload)
    elif action == "get_stock_availability":
        result = life_action_get_stock_availability(request_payload)
    elif action == "get_item_stock_availability":
        result = life_action_get_item_stock_availability(request_payload)
    elif action == "submit_request":
        result = life_action_submit_request(request_payload)
    elif action == "approve_request":
        result = life_action_approve_request(request_payload)
    elif action == "reject_request":
        result = life_action_reject_request(request_payload)
    elif action == "release_stock":
        result = life_action_release_stock(
            request_payload
        )

    elif action == "list_ho_receipt_updates":
        result = life_action_list_ho_receipt_updates(
            request_payload
        )

    elif action == "list_branch_receipts":
        result = life_action_list_branch_receipts(
            request_payload
        )

    elif action == "confirm_branch_receipt":
        result = life_action_confirm_branch_receipt(
            request_payload
        )

    elif action == "billing_receipt_gate":
        result = life_action_billing_receipt_gate(
            request_payload
        )
    elif action == "confirm_branch_receipt":
        result = life_action_confirm_branch_receipt(request_payload)
    elif action == "billing_receipt_gate":
        result = life_action_billing_receipt_gate(request_payload)
    elif action == "submit_receipt_adjustment":
        result = life_action_submit_receipt_adjustment(request_payload)
    elif action == "approve_receipt_adjustment":
        result = life_action_approve_receipt_adjustment(request_payload)
    elif action == "decide_receipt_adjustment":
        result = life_action_decide_receipt_adjustment(request_payload)
    elif action == "list_stock_reconciliations":
        result = life_action_list_stock_reconciliations(request_payload)
    elif action == "get_stock_reconciliation":
        result = life_action_get_stock_reconciliation(request_payload)
    elif action == "create_stock_reconciliation_request":
        result = life_action_create_stock_reconciliation_request(request_payload)
    elif action == "apply_stock_reconciliation_workflow":
        result = life_action_apply_stock_reconciliation_workflow(request_payload)
    elif action == "invoke":
        result = life_action_invoke(request_payload)
    elif action == "batch":
        result = life_action_batch(request_payload)
    elif action == "upload_file":
        result = life_action_upload_file(request_payload)
    elif action == "stock_intelligence":
        result = life_action_stock_intelligence(request_payload)
    else:
        frappe.throw("Unsupported LIFE Stock API action: " + action)

    frappe.response["message"] = result
