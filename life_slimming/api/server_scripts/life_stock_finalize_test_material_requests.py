"""Cancelling MR's

Original API: life_stock_finalize_test_material_requests
Source modified: 2026-08-03 11:21:54.682986
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
    # ============================================================================
    # LIFE STOCK — FINALIZE TEST MATERIAL REQUEST CANCELLATION
    #
    # Server Script Type : API
    # API Method         : life_stock_finalize_test_material_requests
    # Allow Guest        : OFF
    #
    # Use only after the exact linked Stock Entries have already been cancelled.
    #
    # Exact test records:
    #   MAT-MR-2026-01565 -> MAT-STE-2026-01265
    #   MAT-MR-2026-01564 -> MAT-STE-2026-01266
    #   MAT-MR-2026-01562 -> MAT-STE-2026-01264
    #
    # Preview is the default mode.
    # Disable/delete this Server Script after successful cleanup.
    # ============================================================================

    MR_DOCTYPE = "Material Request"
    SE_DOCTYPE = "Stock Entry"

    CONFIRMATION_PHRASE = "FINALIZE TEST MATERIAL REQUESTS"

    TEST_TRANSACTION_MAP = {
        "MAT-MR-2026-01565": "MAT-STE-2026-01265",
        "MAT-MR-2026-01564": "MAT-STE-2026-01266",
        "MAT-MR-2026-01562": "MAT-STE-2026-01264"
    }


    def life_finalizer_int(value, default_value=0):
        try:
            return frappe.utils.cint(value)
        except Exception:
            return default_value


    def life_finalizer_parse_payload():
        raw = frappe.form_dict.get("payload")

        if raw is None or raw == "":
            return {}

        if isinstance(raw, dict):
            return raw

        if isinstance(raw, str):
            parsed = json.loads(raw)

            if not isinstance(parsed, dict):
                frappe.throw("Payload must be a JSON object.")

            return parsed

        frappe.throw("Unsupported payload type.")


    def life_finalizer_roles(user):
        rows = frappe.get_all(
            "Has Role",
            filters={
                "parent": user,
                "parenttype": "User"
            },
            fields=["role"],
            page_length=500
        )

        roles = []

        for row in rows:
            role = str(row.get("role") or "").strip()

            if role and role not in roles:
                roles.append(role)

        return roles


    def life_finalizer_require_authorised_user():
        user = str(frappe.session.user or "").strip()

        if not user or user == "Guest":
            frappe.throw(
                "Please log in to continue.",
                frappe.AuthenticationError
            )

        if user == "Administrator":
            return user

        roles = life_finalizer_roles(user)

        if (
            "System Manager" not in roles and
            "Stock Manager" not in roles
        ):
            frappe.throw(
                "Only Administrator, System Manager, or Stock Manager can run this cleanup.",
                frappe.PermissionError
            )

        return user


    def life_finalizer_active_workflow():
        rows = frappe.get_all(
            "Workflow",
            filters={
                "document_type": MR_DOCTYPE,
                "is_active": 1
            },
            fields=[
                "name",
                "workflow_state_field"
            ],
            order_by="modified desc",
            page_length=1
        )

        if not rows:
            return {
                "name": "",
                "workflow_state_field": "",
                "cancelled_state": ""
            }

        workflow_name = str(
            rows[0].get("name") or ""
        ).strip()

        workflow_state_field = str(
            rows[0].get("workflow_state_field") or ""
        ).strip()

        cancelled_state = ""

        if workflow_name:
            workflow = frappe.get_doc(
                "Workflow",
                workflow_name
            )

            for state_row in workflow.get("states") or []:
                if str(
                    state_row.get("doc_status") or ""
                ).strip() == "2":
                    cancelled_state = str(
                        state_row.get("state") or ""
                    ).strip()

                    if cancelled_state:
                        break

        return {
            "name": workflow_name,
            "workflow_state_field": workflow_state_field,
            "cancelled_state": cancelled_state
        }


    def life_finalizer_clear_stock_entry_backlinks(
        material_request_name,
        stock_entry_name
    ):
        cleared = []

        material_request = frappe.get_doc(
            MR_DOCTYPE,
            material_request_name
        )

        meta = frappe.get_meta(MR_DOCTYPE)

        for field in meta.fields:
            fieldname = str(
                field.get("fieldname") or ""
            ).strip()

            fieldtype = str(
                field.get("fieldtype") or ""
            ).strip()

            options = str(
                field.get("options") or ""
            ).strip()

            if not fieldname:
                continue

            value = str(
                material_request.get(fieldname) or ""
            ).strip()

            if (
                fieldtype == "Link" and
                options == SE_DOCTYPE and
                value == stock_entry_name
            ):
                frappe.db.set_value(
                    MR_DOCTYPE,
                    material_request_name,
                    fieldname,
                    "",
                    update_modified=False
                )

                cleared.append({
                    "fieldname": fieldname,
                    "old_value": value
                })

            elif (
                fieldtype == "Dynamic Link" and
                value == stock_entry_name
            ):
                dynamic_doctype = str(
                    material_request.get(options) or ""
                ).strip()

                if dynamic_doctype == SE_DOCTYPE:
                    frappe.db.set_value(
                        MR_DOCTYPE,
                        material_request_name,
                        fieldname,
                        "",
                        update_modified=False
                    )

                    cleared.append({
                        "fieldname": fieldname,
                        "old_value": value
                    })

        return cleared


    def life_finalizer_normalize_cancelled_fields(
        material_request_name,
        workflow_info
    ):
        meta = frappe.get_meta(MR_DOCTYPE)

        values = {
            "status": "Cancelled",
            "custom_stock_entry_reference": "",
            "custom_stock_request_status": "Cancelled",
            "transfer_status": "Cancelled"
        }

        workflow_state_field = str(
            workflow_info.get("workflow_state_field") or ""
        ).strip()

        cancelled_state = str(
            workflow_info.get("cancelled_state") or ""
        ).strip()

        if workflow_state_field and cancelled_state:
            values[workflow_state_field] = cancelled_state

        updated = {}

        for fieldname in values:
            if fieldname == "status" or meta.get_field(fieldname):
                value = values.get(fieldname)

                frappe.db.set_value(
                    MR_DOCTYPE,
                    material_request_name,
                    fieldname,
                    value,
                    update_modified=False
                )

                updated[fieldname] = value

        return updated


    def life_finalizer_preview_row(
        material_request_name,
        stock_entry_name,
        workflow_info
    ):
        if not frappe.db.exists(
            MR_DOCTYPE,
            material_request_name
        ):
            frappe.throw(
                "Material Request does not exist: " +
                material_request_name
            )

        if not frappe.db.exists(
            SE_DOCTYPE,
            stock_entry_name
        ):
            frappe.throw(
                "Stock Entry does not exist: " +
                stock_entry_name
            )

        material_request = frappe.get_doc(
            MR_DOCTYPE,
            material_request_name
        )

        stock_entry = frappe.get_doc(
            SE_DOCTYPE,
            stock_entry_name
        )

        stock_entry_docstatus = life_finalizer_int(
            stock_entry.docstatus,
            0
        )

        if stock_entry_docstatus != 2:
            frappe.throw(
                "Safety check failed. Stock Entry " +
                stock_entry_name +
                " must be cancelled before its Material Request is finalized. " +
                "Current docstatus: " +
                str(stock_entry_docstatus)
            )

        workflow_state_field = str(
            workflow_info.get("workflow_state_field") or ""
        ).strip()

        return {
            "material_request": material_request_name,
            "material_request_docstatus": life_finalizer_int(
                material_request.docstatus,
                0
            ),
            "material_request_status": material_request.get("status"),
            "material_request_workflow_state": (
                material_request.get(workflow_state_field)
                if workflow_state_field
                else ""
            ),
            "stock_entry": stock_entry_name,
            "stock_entry_docstatus": stock_entry_docstatus,
            "stock_entry_status": stock_entry.get("status"),
            "workflow": workflow_info.get("name"),
            "workflow_state_field": workflow_state_field,
            "configured_cancelled_state": (
                workflow_info.get("cancelled_state")
            )
        }


    def life_finalizer_cancel_material_request(
        material_request_name,
        stock_entry_name,
        workflow_info
    ):
        material_request = frappe.get_doc(
            MR_DOCTYPE,
            material_request_name
        )

        docstatus = life_finalizer_int(
            material_request.docstatus,
            0
        )

        cleared_links = (
            life_finalizer_clear_stock_entry_backlinks(
                material_request_name,
                stock_entry_name
            )
        )

        if docstatus == 1:
            # Do not set status/workflow fields to Cancelled before cancel().
            # Frappe must first perform the legal Submitted -> Cancelled transition.
            material_request.reload()
            material_request.flags.ignore_permissions = True
            material_request.cancel()
            result = "Cancelled"

        elif docstatus == 2:
            # The document is already cancelled. Applying the Cancelled workflow
            # action again would attempt an illegal Cancelled -> Cancelled transition.
            result = "Already Cancelled"

        elif docstatus == 0:
            frappe.delete_doc(
                MR_DOCTYPE,
                material_request_name,
                ignore_permissions=True
            )

            return {
                "material_request": material_request_name,
                "result": "Deleted Draft",
                "cleared_links": cleared_links,
                "normalized_fields": {}
            }

        else:
            frappe.throw(
                "Unsupported Material Request docstatus for " +
                material_request_name +
                ": " +
                str(docstatus)
            )

        normalized_fields = (
            life_finalizer_normalize_cancelled_fields(
                material_request_name,
                workflow_info
            )
        )

        return {
            "material_request": material_request_name,
            "result": result,
            "cleared_links": cleared_links,
            "normalized_fields": normalized_fields
        }


    # ----------------------------------------------------------------------------
    # EXECUTION
    # ----------------------------------------------------------------------------
    user = life_finalizer_require_authorised_user()
    payload = life_finalizer_parse_payload()

    mode = str(
        payload.get("mode") or
        "preview"
    ).strip().lower()

    if mode not in ["preview", "execute"]:
        frappe.throw(
            "Mode must be preview or execute."
        )

    workflow_info = life_finalizer_active_workflow()

    preview_rows = []

    for material_request_name in TEST_TRANSACTION_MAP:
        stock_entry_name = TEST_TRANSACTION_MAP.get(
            material_request_name
        )

        preview_rows.append(
            life_finalizer_preview_row(
                material_request_name,
                stock_entry_name,
                workflow_info
            )
        )

    if mode == "preview":
        result = {
            "ok": True,
            "mode": "preview",
            "executed": False,
            "run_by": user,
            "confirmation_required": CONFIRMATION_PHRASE,
            "workflow": workflow_info,
            "rows": preview_rows,
            "message": (
                "Preview completed. No Material Request was changed."
            )
        }

    else:
        confirmation = str(
            payload.get("confirmation") or ""
        ).strip()

        if confirmation != CONFIRMATION_PHRASE:
            frappe.throw(
                "Execution blocked. Enter the exact confirmation phrase: " +
                CONFIRMATION_PHRASE
            )

        completed = []

        for material_request_name in TEST_TRANSACTION_MAP:
            stock_entry_name = TEST_TRANSACTION_MAP.get(
                material_request_name
            )

            completed.append(
                life_finalizer_cancel_material_request(
                    material_request_name,
                    stock_entry_name,
                    workflow_info
                )
            )

        result = {
            "ok": True,
            "mode": "execute",
            "executed": True,
            "run_by": user,
            "workflow": workflow_info,
            "results": completed,
            "message": (
                "Test Material Requests were finalized. Already-cancelled records " +
                "were not cancelled again; their status and workflow display fields " +
                "were normalized."
            )
        }

    frappe.response["message"] = result
