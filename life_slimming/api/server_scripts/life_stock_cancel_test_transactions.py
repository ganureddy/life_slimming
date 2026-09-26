"""Cancelling MR and Stock entries

Original API: life_stock_cancel_test_transactions
Source modified: 2026-09-16 00:57:44.247253
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
    # LIFE STOCK — ONE-TIME TEST TRANSACTION CLEANUP
    #
    # Server Script Type : API
    # API Method         : life_stock_cancel_test_transactions
    # Allow Guest        : OFF
    #
    # TARGET RECORDS
    # Material Request : MAT-MR-2026-01839
    # Stock Entry      : MAT-STE-2026-01448
    #
    # CURRENT STATE
    # Material Request : Cancelled (docstatus = 2)
    # Stock Entry      : Draft     (docstatus = 0)
    #
    # ACTION
    # 1. Validate exact MR <-> Stock Entry relationship.
    # 2. Clear Material Request -> Stock Entry custom backlink.
    # 3. Delete Draft Stock Entry.
    # 4. Delete already-cancelled Material Request.
    #
    # Preview is the default mode.
    # Execution requires:
    # CANCEL TEST STOCK TRANSACTIONS
    # ============================================================================


    MR_DOCTYPE = "Material Request"
    SE_DOCTYPE = "Stock Entry"
    SE_ITEM_DOCTYPE = "Stock Entry Detail"

    CONFIRMATION_PHRASE = (
        "CANCEL TEST STOCK TRANSACTIONS"
    )

    TEST_TRANSACTION_MAP = {
        "MAT-MR-2026-02171":
            "MAT-STE-2026-01746"
    }


    # ============================================================================
    # BASIC HELPERS
    # ============================================================================

    def life_cleanup_int(value, default_value=0):
        try:
            return frappe.utils.cint(value)
        except Exception:
            return default_value


    def life_cleanup_parse_payload():
        raw = frappe.form_dict.get("payload")

        if raw is None or raw == "":
            return {}

        if isinstance(raw, dict):
            return raw

        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except Exception:
                frappe.throw(
                    "Payload must contain valid JSON."
                )

            if not isinstance(parsed, dict):
                frappe.throw(
                    "Payload must be a JSON object."
                )

            return parsed

        frappe.throw(
            "Unsupported payload type."
        )


    def life_cleanup_docstatus_label(docstatus):
        value = life_cleanup_int(
            docstatus,
            0
        )

        if value == 0:
            return "Draft"

        if value == 1:
            return "Submitted"

        if value == 2:
            return "Cancelled"

        return str(value)


    # ============================================================================
    # SECURITY
    # ============================================================================

    def life_cleanup_roles(user):
        rows = frappe.get_all(
            "Has Role",
            filters={
                "parent": user,
                "parenttype": "User"
            },
            fields=[
                "role"
            ],
            page_length=500
        )

        roles = []

        for row in rows:
            role = str(
                row.get("role") or ""
            ).strip()

            if (
                role and
                role not in roles
            ):
                roles.append(role)

        return roles


    def life_cleanup_require_authorised_user():
        user = str(
            frappe.session.user or ""
        ).strip()

        if (
            not user or
            user == "Guest"
        ):
            frappe.throw(
                "Please log in to continue.",
                frappe.AuthenticationError
            )

        if user == "Administrator":
            return user

        roles = life_cleanup_roles(
            user
        )

        if (
            "System Manager" not in roles and
            "Stock Manager" not in roles
        ):
            frappe.throw(
                "Only Administrator, System Manager "
                "or Stock Manager can run this cleanup.",
                frappe.PermissionError
            )

        return user


    # ============================================================================
    # LINK HELPERS
    # ============================================================================

    def life_cleanup_linked_stock_entries(
        material_request_name
    ):
        names = []

        # --------------------------------------------------------
        # Direct custom link from Material Request
        # --------------------------------------------------------
        if frappe.db.exists(
            MR_DOCTYPE,
            material_request_name
        ):
            mr = frappe.get_doc(
                MR_DOCTYPE,
                material_request_name
            )

            mr_meta = frappe.get_meta(
                MR_DOCTYPE
            )

            if mr_meta.get_field(
                "custom_stock_entry_reference"
            ):
                direct_reference = str(
                    mr.get(
                        "custom_stock_entry_reference"
                    ) or ""
                ).strip()

                if (
                    direct_reference and
                    frappe.db.exists(
                        SE_DOCTYPE,
                        direct_reference
                    ) and
                    direct_reference not in names
                ):
                    names.append(
                        direct_reference
                    )

        # --------------------------------------------------------
        # Stock Entry Detail -> Material Request link
        # --------------------------------------------------------
        rows = frappe.get_all(
            SE_ITEM_DOCTYPE,
            filters={
                "material_request":
                    material_request_name,
                "parenttype":
                    SE_DOCTYPE
            },
            fields=[
                "parent"
            ],
            page_length=500
        )

        for row in rows:
            parent = str(
                row.get("parent") or ""
            ).strip()

            if (
                parent and
                parent not in names
            ):
                names.append(parent)

        return names


    def life_cleanup_stock_entry_request_names(
        stock_entry
    ):
        names = []

        for item in stock_entry.get(
            "items"
        ) or []:

            request_name = str(
                item.get(
                    "material_request"
                ) or ""
            ).strip()

            if (
                request_name and
                request_name not in names
            ):
                names.append(
                    request_name
                )

        return names


    # ============================================================================
    # VALIDATION
    # ============================================================================

    def life_cleanup_validate_transaction_map():
        plan = []

        for material_request_name in (
            TEST_TRANSACTION_MAP
        ):
            expected_stock_entry = (
                TEST_TRANSACTION_MAP.get(
                    material_request_name
                )
            )

            # ----------------------------------------------------
            # Material Request must exist
            # ----------------------------------------------------
            if not frappe.db.exists(
                MR_DOCTYPE,
                material_request_name
            ):
                frappe.throw(
                    "Material Request does not exist: " +
                    material_request_name
                )

            material_request = frappe.get_doc(
                MR_DOCTYPE,
                material_request_name
            )

            # ----------------------------------------------------
            # Expected Stock Entry must exist
            # ----------------------------------------------------
            if not frappe.db.exists(
                SE_DOCTYPE,
                expected_stock_entry
            ):
                frappe.throw(
                    "Stock Entry does not exist: " +
                    expected_stock_entry
                )

            stock_entry = frappe.get_doc(
                SE_DOCTYPE,
                expected_stock_entry
            )

            # ----------------------------------------------------
            # Verify MR -> SE relationship
            # ----------------------------------------------------
            linked_stock_entries = (
                life_cleanup_linked_stock_entries(
                    material_request_name
                )
            )

            if (
                expected_stock_entry not in
                linked_stock_entries
            ):
                frappe.throw(
                    "Safety check failed for " +
                    material_request_name +
                    ". Expected linked Stock Entry " +
                    expected_stock_entry +
                    ", but found: " +
                    (
                        ", ".join(
                            linked_stock_entries
                        )
                        if linked_stock_entries
                        else "none"
                    )
                )

            if len(
                linked_stock_entries
            ) != 1:
                frappe.throw(
                    "Safety check failed. " +
                    material_request_name +
                    " must have exactly one linked "
                    "Stock Entry. Found: " +
                    ", ".join(
                        linked_stock_entries
                    )
                )

            # ----------------------------------------------------
            # Verify SE does not contain another MR
            # ----------------------------------------------------
            request_names = (
                life_cleanup_stock_entry_request_names(
                    stock_entry
                )
            )

            unexpected_requests = []

            for request_name in request_names:
                if (
                    request_name !=
                    material_request_name
                ):
                    unexpected_requests.append(
                        request_name
                    )

            if unexpected_requests:
                frappe.throw(
                    "Cleanup stopped. Stock Entry " +
                    expected_stock_entry +
                    " also contains other "
                    "Material Requests: " +
                    ", ".join(
                        unexpected_requests
                    )
                )

            # ----------------------------------------------------
            # This specific cleanup expects:
            # MR = Cancelled
            # SE = Draft
            # ----------------------------------------------------
            mr_docstatus = life_cleanup_int(
                material_request.docstatus,
                0
            )

            se_docstatus = life_cleanup_int(
                stock_entry.docstatus,
                0
            )

            if mr_docstatus != 2:
                frappe.throw(
                    "Safety check failed. " +
                    material_request_name +
                    " is expected to be Cancelled, "
                    "but its current state is " +
                    life_cleanup_docstatus_label(
                        mr_docstatus
                    ) +
                    "."
                )

            if se_docstatus != 0:
                frappe.throw(
                    "Safety check failed. " +
                    expected_stock_entry +
                    " is expected to be Draft, "
                    "but its current state is " +
                    life_cleanup_docstatus_label(
                        se_docstatus
                    ) +
                    "."
                )

            plan.append({
                "material_request":
                    material_request_name,

                "material_request_docstatus":
                    mr_docstatus,

                "material_request_status":
                    life_cleanup_docstatus_label(
                        mr_docstatus
                    ),

                "material_request_workflow_state":
                    material_request.get(
                        "workflow_state"
                    ),

                "material_request_erp_status":
                    material_request.get(
                        "status"
                    ),

                "stock_entry":
                    expected_stock_entry,

                "stock_entry_docstatus":
                    se_docstatus,

                "stock_entry_status":
                    life_cleanup_docstatus_label(
                        se_docstatus
                    ),

                "stock_entry_workflow_state":
                    stock_entry.get(
                        "workflow_state"
                    ),

                "stock_entry_from_warehouse":
                    stock_entry.get(
                        "from_warehouse"
                    ),

                "stock_entry_to_warehouse":
                    stock_entry.get(
                        "to_warehouse"
                    )
            })

        return plan


    # ============================================================================
    # CLEAR MATERIAL REQUEST -> STOCK ENTRY BACKLINKS
    # ============================================================================

    def life_cleanup_detach_material_request_links(
        material_request_name,
        stock_entry_name
    ):
        detached_links = []

        if not frappe.db.exists(
            MR_DOCTYPE,
            material_request_name
        ):
            return detached_links

        material_request = frappe.get_doc(
            MR_DOCTYPE,
            material_request_name
        )

        meta = frappe.get_meta(
            MR_DOCTYPE
        )

        # --------------------------------------------------------
        # Detect every Link field pointing to Stock Entry
        # --------------------------------------------------------
        for field in meta.fields:
            fieldname = str(
                field.get(
                    "fieldname"
                ) or ""
            ).strip()

            fieldtype = str(
                field.get(
                    "fieldtype"
                ) or ""
            ).strip()

            options = str(
                field.get(
                    "options"
                ) or ""
            ).strip()

            if not fieldname:
                continue

            if (
                fieldtype == "Link" and
                options == SE_DOCTYPE
            ):
                current_value = str(
                    material_request.get(
                        fieldname
                    ) or ""
                ).strip()

                if (
                    current_value ==
                    stock_entry_name
                ):
                    detached_links.append({
                        "doctype":
                            MR_DOCTYPE,
                        "name":
                            material_request_name,
                        "fieldname":
                            fieldname,
                        "old_value":
                            current_value
                    })

                    frappe.db.set_value(
                        MR_DOCTYPE,
                        material_request_name,
                        fieldname,
                        "",
                        update_modified=False
                    )

        # --------------------------------------------------------
        # Explicit fallback for known field
        # --------------------------------------------------------
        if meta.get_field(
            "custom_stock_entry_reference"
        ):
            current_reference = str(
                frappe.db.get_value(
                    MR_DOCTYPE,
                    material_request_name,
                    "custom_stock_entry_reference"
                ) or ""
            ).strip()

            if (
                current_reference ==
                stock_entry_name
            ):
                already_added = False

                for link in detached_links:
                    if (
                        link.get("fieldname") ==
                        "custom_stock_entry_reference"
                    ):
                        already_added = True
                        break

                if not already_added:
                    detached_links.append({
                        "doctype":
                            MR_DOCTYPE,
                        "name":
                            material_request_name,
                        "fieldname":
                            "custom_stock_entry_reference",
                        "old_value":
                            current_reference
                    })

                    frappe.db.set_value(
                        MR_DOCTYPE,
                        material_request_name,
                        "custom_stock_entry_reference",
                        "",
                        update_modified=False
                    )

        return detached_links


    def life_cleanup_restore_links(
        links
    ):
        for link in links:
            doctype = str(
                link.get("doctype") or ""
            ).strip()

            name = str(
                link.get("name") or ""
            ).strip()

            fieldname = str(
                link.get("fieldname") or ""
            ).strip()

            old_value = link.get(
                "old_value"
            )

            if (
                not doctype or
                not name or
                not fieldname
            ):
                continue

            if frappe.db.exists(
                doctype,
                name
            ):
                frappe.db.set_value(
                    doctype,
                    name,
                    fieldname,
                    old_value,
                    update_modified=False
                )


    # ============================================================================
    # DELETE STOCK ENTRY
    # ============================================================================

    def life_cleanup_delete_stock_entry(
        stock_entry_name,
        material_request_name
    ):
        if not frappe.db.exists(
            SE_DOCTYPE,
            stock_entry_name
        ):
            return {
                "result":
                    "Already Deleted",
                "detached_links":
                    []
            }

        stock_entry = frappe.get_doc(
            SE_DOCTYPE,
            stock_entry_name
        )

        docstatus = life_cleanup_int(
            stock_entry.docstatus,
            0
        )

        # --------------------------------------------------------
        # This transaction is expected to still be Draft.
        # Draft Stock Entries have no submitted stock movement.
        # --------------------------------------------------------
        if docstatus != 0:
            frappe.throw(
                "Stock Entry " +
                stock_entry_name +
                " is no longer Draft. "
                "Cleanup stopped for safety. "
                "Current state: " +
                life_cleanup_docstatus_label(
                    docstatus
                )
            )

        detached_links = (
            life_cleanup_detach_material_request_links(
                material_request_name,
                stock_entry_name
            )
        )

        try:
            frappe.delete_doc(
                SE_DOCTYPE,
                stock_entry_name,
                ignore_permissions=True
            )

        except Exception as error:
            life_cleanup_restore_links(
                detached_links
            )

            frappe.throw(
                "Could not delete Draft Stock Entry " +
                stock_entry_name +
                ": " +
                str(error or "")
            )

        return {
            "result":
                "Deleted Draft",

            "detached_links":
                detached_links
        }


    # ============================================================================
    # DELETE MATERIAL REQUEST
    # ============================================================================

    def life_cleanup_delete_material_request(
        material_request_name
    ):
        if not frappe.db.exists(
            MR_DOCTYPE,
            material_request_name
        ):
            return "Already Deleted"

        material_request = frappe.get_doc(
            MR_DOCTYPE,
            material_request_name
        )

        docstatus = life_cleanup_int(
            material_request.docstatus,
            0
        )

        # --------------------------------------------------------
        # This exact transaction is expected to already be
        # cancelled.
        # --------------------------------------------------------
        if docstatus != 2:
            frappe.throw(
                "Material Request " +
                material_request_name +
                " is not Cancelled. "
                "Cleanup stopped for safety. "
                "Current state: " +
                life_cleanup_docstatus_label(
                    docstatus
                )
            )

        try:
            frappe.delete_doc(
                MR_DOCTYPE,
                material_request_name,
                ignore_permissions=True
            )

        except Exception as error:
            frappe.throw(
                "Could not delete Cancelled "
                "Material Request " +
                material_request_name +
                ": " +
                str(error or "")
            )

        return "Deleted Cancelled"


    # ============================================================================
    # EXECUTION
    # ============================================================================

    user = (
        life_cleanup_require_authorised_user()
    )

    payload = (
        life_cleanup_parse_payload()
    )

    mode = str(
        payload.get("mode") or
        "preview"
    ).strip().lower()


    if mode not in [
        "preview",
        "execute"
    ]:
        frappe.throw(
            "Mode must be preview or execute."
        )


    # Always validate before preview or execution.
    plan = (
        life_cleanup_validate_transaction_map()
    )


    # ============================================================================
    # PREVIEW MODE
    # ============================================================================

    if mode == "preview":

        result = {
            "ok": True,
            "mode": "preview",
            "executed": False,
            "run_by": user,

            "confirmation_required":
                CONFIRMATION_PHRASE,

            "plan": plan,

            "message": (
                "Preview completed successfully. "
                "No records were changed. "
                "The Draft Stock Entry will be deleted first, "
                "followed by the already-cancelled Material Request."
            )
        }


    # ============================================================================
    # EXECUTE MODE
    # ============================================================================

    else:

        confirmation = str(
            payload.get(
                "confirmation"
            ) or ""
        ).strip()

        if (
            confirmation !=
            CONFIRMATION_PHRASE
        ):
            frappe.throw(
                "Execution blocked. Enter the exact "
                "confirmation phrase: " +
                CONFIRMATION_PHRASE
            )

        stock_entry_results = []
        material_request_results = []

        # ------------------------------------------------------------------------
        # FIRST: DELETE STOCK ENTRY
        # ------------------------------------------------------------------------
        for plan_row in plan:

            stock_entry_name = str(
                plan_row.get(
                    "stock_entry"
                ) or ""
            ).strip()

            material_request_name = str(
                plan_row.get(
                    "material_request"
                ) or ""
            ).strip()

            stock_result = (
                life_cleanup_delete_stock_entry(
                    stock_entry_name,
                    material_request_name
                )
            )

            stock_entry_results.append({
                "stock_entry":
                    stock_entry_name,

                "material_request":
                    material_request_name,

                "result":
                    stock_result.get(
                        "result"
                    ),

                "detached_links":
                    stock_result.get(
                        "detached_links"
                    ) or []
            })


        # ------------------------------------------------------------------------
        # SECOND: DELETE CANCELLED MATERIAL REQUEST
        # ------------------------------------------------------------------------
        for plan_row in plan:

            material_request_name = str(
                plan_row.get(
                    "material_request"
                ) or ""
            ).strip()

            mr_result = (
                life_cleanup_delete_material_request(
                    material_request_name
                )
            )

            material_request_results.append({
                "material_request":
                    material_request_name,

                "result":
                    mr_result
            })


        result = {
            "ok": True,
            "mode": "execute",
            "executed": True,
            "run_by": user,

            "stock_entries":
                stock_entry_results,

            "material_requests":
                material_request_results,

            "message": (
                "Cleanup completed successfully. "
                "Draft Stock Entry MAT-STE-2026-01448 "
                "was deleted first and cancelled Material Request "
                "MAT-MR-2026-01839 was deleted afterwards."
            )
        }


    frappe.response["message"] = result
