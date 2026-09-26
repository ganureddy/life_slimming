"""p2p run final automation

Original API: p2p_run_final_automation
Source modified: 2026-09-09 14:38:07.556783
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
    # ============================================================
    # P2P FINAL AUTOMATION API - SAFE EXEC VERSION
    # API Method: p2p_run_final_automation
    #
    # FINAL RULE:
    # - If exactly 1 source Therapy Plan is selected:
    #     Update the same Therapy Plan table.
    #     Rows with completed sessions are protected.
    #     Rows with 0 completed sessions may be removed.
    #
    # - If more than 1 source Therapy Plan is selected:
    #     Create a new Therapy Plan.
    #     Close/equalize old source Therapy Plans.
    #
    # Safe-exec notes:
    # - No imports
    # - No .format()
    # - No tuple unpacking
    # ============================================================


    def cstr(value):
        if value is None:
            return ""
        try:
            return str(value).strip()
        except Exception:
            return ""


    def flt(value):
        try:
            if value is None:
                return 0.0
            if value == "":
                return 0.0
            return float(value)
        except Exception:
            return 0.0


    def cint(value):
        try:
            if value is None:
                return 0
            if value == "":
                return 0
            return int(float(value))
        except Exception:
            return 0


    def round_money(value):
        return round(flt(value), 2)


    REQUEST_DOCTYPE = "LIFE Client Package Conversion Same Client Package To Package"
    THERAPY_PLAN_DOCTYPE = "Therapy Plan"
    THERAPY_TYPE_DOCTYPE = "Therapy Type"
    SNAPSHOT_DOCTYPE = "Therapy Plan Conversion Snapshot"
    LEAD_SOURCE_DOCTYPE = "Lead Source"
    ALL_CATEGORY = "All Healthcare Service Units - LSACPL"


    TOTAL_SESSION_FIELDS = [
        "booked_quantity",
        "current_total_sessions",
        "no_of_sessions",
        "sessions",
        "number_of_sessions",
        "total_sessions",
        "qty",
        "quantity",
        "total_quantity",
        "booked_sessions",
        "current_sessions",
        "custom_total_sessions",
        "custom_no_of_sessions",
        "custom_booked_quantity",
        "custom_current_total_sessions"
    ]


    COMPLETED_SESSION_FIELDS = [
        "availed_quantity",
        "sessions_completed",
        "used_quantity",
        "total_sessions_completed",
        "completed_sessions",
        "completed_quantity",
        "completed_qty",
        "availed_sessions",
        "sessions_availed",
        "used_sessions",
        "consumed_sessions",
        "consumed_quantity",
        "completed",
        "session_completed",
        "completed_session",
        "total_completed_sessions",
        "custom_availed_quantity",
        "custom_sessions_completed",
        "custom_completed_sessions",
        "custom_used_sessions",
        "custom_completed_quantity",
        "custom_total_sessions_completed",
        "custom_availed_sessions",
        "custom_used_quantity",
        "custom_consumed_sessions"
    ]


    BALANCE_SESSION_FIELDS = [
        "balance_quantity",
        "balance_qty",
        "remaining_quantity",
        "remaining_sessions",
        "balance_sessions",
        "available_sessions",
        "pending_sessions",
        "pending_quantity",
        "balance",
        "balance_session",
        "pending",
        "custom_balance_quantity",
        "custom_balance_sessions",
        "custom_remaining_sessions",
        "custom_pending_sessions"
    ]


    THERAPY_NAME_FIELDS = [
        "therapy_type",
        "service",
        "service_name",
        "item_code",
        "item_name",
        "therapy_plan_template",
        "healthcare_service_unit"
    ]


    RATE_FIELDS = [
        "rate",
        "price",
        "rate__session",
        "rate_per_session",
        "price_per_session",
        "session_rate"
    ]


    AMOUNT_FIELDS = [
        "amount",
        "total_amount",
        "balance_amount",
        "plan_amount",
        "custom_plan_amount"
    ]


    def has_field(doctype, fieldname):
        try:
            return bool(frappe.get_meta(doctype).get_field(fieldname))
        except Exception:
            return False


    def get_meta_field(doctype, fieldname):
        try:
            return frappe.get_meta(doctype).get_field(fieldname)
        except Exception:
            return None


    def first_value(row, fields):
        for fieldname in fields:
            try:
                value = row.get(fieldname)
            except Exception:
                value = None

            if value is not None and value != "":
                return value

        return None


    def has_any_value(row, fields):
        for fieldname in fields:
            try:
                value = row.get(fieldname)
            except Exception:
                value = None

            if value is not None and value != "":
                return True

        return False


    def therapy_key(value):
        value = cstr(value).lower()
        value = value.replace("\n", " ")
        value = value.replace("\r", " ")

        while "  " in value:
            value = value.replace("  ", " ")

        return value.strip()


    def normalize_db_value(doctype, fieldname, value):
        """Normalize values before direct database updates.

    MariaDB strict mode rejects an empty string for Date, Datetime, Time,
    numeric and Check columns. Frappe document.save() normally performs
    these conversions, but frappe.db.set_value() can reach MariaDB directly.
    """
        df = get_meta_field(doctype, fieldname)

        if not df:
            return value

        fieldtype = cstr(df.fieldtype)

        if value == "":
            if fieldtype in ["Date", "Datetime", "Time"]:
                return None

            if fieldtype in [
                "Check",
                "Int",
                "Float",
                "Currency",
                "Percent",
                "Rating",
                "Duration"
            ]:
                return 0

        return value


    def db_set_values(doctype, name, values, update_modified=True):
        values = values or {}
        safe = {}

        for fieldname in values:
            if not has_field(doctype, fieldname):
                continue

            safe[fieldname] = normalize_db_value(
                doctype,
                fieldname,
                values[fieldname]
            )

        if not safe:
            return {}

        try:
            frappe.db.set_value(
                doctype,
                name,
                safe,
                update_modified=update_modified
            )
        except TypeError:
            # Compatibility fallback for installations that do not support
            # a dict in frappe.db.set_value().
            for fieldname in safe:
                frappe.db.set_value(
                    doctype,
                    name,
                    fieldname,
                    safe[fieldname],
                    update_modified=update_modified
                )

        return safe


    def set_request_values(request_name, values):
        db_set_values(
            REQUEST_DOCTYPE,
            request_name,
            values,
            update_modified=True
        )


    def get_request_restore_snapshot_rows(req):
        # COO must retry from the Audit-approved version. For older requests,
        # fall back to the original Branch snapshot.
        audit_rows = req.get("audit_team_requested_package") or []

        if audit_rows:
            return [audit_rows, "Audit Team Approved Package"]

        branch_rows = req.get("branch_requested_package") or []

        if branch_rows:
            return [branch_rows, "Branch Requested Package"]

        return [[], ""]


    def snapshot_rows_to_active_rows(snapshot_rows):
        active_field = "converted_package__service_name"
        child_doctype = get_child_doctype(REQUEST_DOCTYPE, active_field)
        output = []

        if not child_doctype:
            return output

        for source_row in (snapshot_rows or []):
            therapy = cstr(first_value(source_row, [
                "therapy_type",
                "converted_package__service_name",
                "service_package_name",
                "service_name",
                "package_name"
            ]))

            qty = cint(first_value(source_row, [
                "no_of_sessions",
                "converted_quantity",
                "qty",
                "quantity"
            ]))

            completed = cint(first_value(source_row, [
                "sessions_completed",
                "completed_sessions",
                "availed_quantity",
                "completed"
            ]))

            amount = round_money(first_value(source_row, [
                "amount",
                "balance_amount",
                "total_amount"
            ]))

            rate = round_money(first_value(source_row, RATE_FIELDS))
            applied_sessions = max(qty - completed, 0)

            if applied_sessions > 0 and amount > 0:
                rate = round_money(amount / applied_sessions)
            elif not amount and applied_sessions > 0 and rate > 0:
                amount = round_money(rate * applied_sessions)

            if not therapy or qty <= 0:
                continue

            payload = {}

            for fieldname in [
                "converted_package__service_name",
                "service_package_name",
                "therapy_type",
                "service_name",
                "package_name"
            ]:
                set_child_payload_if_has(
                    payload,
                    child_doctype,
                    fieldname,
                    therapy
                )

            for fieldname in [
                "converted_quantity",
                "no_of_sessions",
                "qty",
                "quantity"
            ]:
                set_child_payload_if_has(
                    payload,
                    child_doctype,
                    fieldname,
                    qty
                )

            for fieldname in [
                "completed_sessions",
                "sessions_completed",
                "availed_quantity",
                "completed"
            ]:
                set_child_payload_if_has(
                    payload,
                    child_doctype,
                    fieldname,
                    completed
                )

            for fieldname in [
                "applied_sessions",
                "new_sessions_to_apply",
                "balance_quantity"
            ]:
                set_child_payload_if_has(
                    payload,
                    child_doctype,
                    fieldname,
                    applied_sessions
                )

            for fieldname in RATE_FIELDS:
                set_child_payload_if_has(
                    payload,
                    child_doctype,
                    fieldname,
                    rate
                )

            for fieldname in [
                "balance_amount",
                "amount",
                "total_amount",
                "applied_amount",
                "new_amount"
            ]:
                set_child_payload_if_has(
                    payload,
                    child_doctype,
                    fieldname,
                    amount
                )

            set_child_payload_if_has(
                payload,
                child_doctype,
                "source_row_name",
                cstr(source_row.get("source_row_name"))
            )

            if payload:
                output.append(payload)

        return output


    def restore_request_active_table(req):
        snapshot_result = get_request_restore_snapshot_rows(req)
        snapshot_rows = snapshot_result[0]
        source_label = snapshot_result[1]

        if not snapshot_rows:
            return {
                "restored": False,
                "source": "",
                "total": 0
            }

        active_rows = snapshot_rows_to_active_rows(snapshot_rows)

        if not active_rows:
            return {
                "restored": False,
                "source": source_label,
                "total": 0
            }

        req.set("converted_package__service_name", [])

        for payload in active_rows:
            req.append("converted_package__service_name", payload)

        total = 0

        for snapshot_row in snapshot_rows:
            total += flt(first_value(snapshot_row, [
                "amount",
                "balance_amount",
                "total_amount"
            ]))

        set_doc_field_if_exists(
            req,
            "new_package_total_price_rs",
            round_money(total)
        )

        return {
            "restored": True,
            "source": source_label,
            "total": round_money(total)
        }



    def fail_request(request_name, message, error_code="AUTOMATION_FAILED"):
        """Reopen the request safely after failed final automation.

    The failed COO approval is cleared and the active converted-package
    table is restored from the Audit-approved snapshot. For older requests,
    the Branch-requested snapshot is used as the fallback.
    """
        request_name = cstr(request_name)
        message = cstr(message)
        error_code = cstr(error_code) or "AUTOMATION_FAILED"

        if not request_name:
            return {
                "ok": False,
                "request_reopened": False,
                "restored": False,
                "restored_from": "",
                "restored_total": 0,
                "warning": "Request name is blank."
            }

        if not frappe.db.exists(REQUEST_DOCTYPE, request_name):
            return {
                "ok": False,
                "request_reopened": False,
                "restored": False,
                "restored_from": "",
                "restored_total": 0,
                "warning": "P2P request does not exist: " + request_name
            }

        req = frappe.get_doc(REQUEST_DOCTYPE, request_name)

        restore_result = restore_request_active_table(req)

        if has_field(REQUEST_DOCTYPE, "current_tab_step"):
            req.set("current_tab_step", 4)

        if has_field(REQUEST_DOCTYPE, "approval_stage"):
            req.set(
                "approval_stage",
                "COO / Management Approval Pending"
            )

        if has_field(REQUEST_DOCTYPE, "final_approval_status"):
            req.set("final_approval_status", "")

        if has_field(REQUEST_DOCTYPE, "approval_display_status"):
            req.set(
                "approval_display_status",
                "COO / Management Approval Pending"
            )

        if has_field(REQUEST_DOCTYPE, "automation_status"):
            req.set(
                "automation_status",
                "Pending Final Approval"
            )

        if has_field(REQUEST_DOCTYPE, "package_conversion_applied"):
            req.set("package_conversion_applied", 0)

        if has_field(REQUEST_DOCTYPE, "coo_management_name"):
            req.set("coo_management_name", "")

        if has_field(REQUEST_DOCTYPE, "coo_management_date"):
            # Date / Datetime fields must use SQL NULL, not an empty string.
            req.set("coo_management_date", None)

        if has_field(REQUEST_DOCTYPE, "coo_management_remarks"):
            req.set("coo_management_remarks", "")

        if has_field(
            REQUEST_DOCTYPE,
            "coo_management_package_edited"
        ):
            req.set("coo_management_package_edited", 0)

        if has_field(
            REQUEST_DOCTYPE,
            "coo_management_final_package"
        ):
            req.set("coo_management_final_package", [])

        current_edited_stage = cstr(
            req.get("final_table_edited_stage")
        )

        if "COO" in current_edited_stage:
            audit_edited = (
                cint(req.get("audit_team_package_edited")) == 1
            )

            if has_field(
                REQUEST_DOCTYPE,
                "final_table_edited_during_approval"
            ):
                req.set(
                    "final_table_edited_during_approval",
                    1 if audit_edited else 0
                )

            if has_field(
                REQUEST_DOCTYPE,
                "final_table_edited_stage"
            ):
                req.set(
                    "final_table_edited_stage",
                    "Audit Team Approval" if audit_edited else ""
                )

            if has_field(
                REQUEST_DOCTYPE,
                "final_table_edited_by"
            ):
                req.set(
                    "final_table_edited_by",
                    cstr(req.get("authorised_name"))
                    if audit_edited
                    else ""
                )

            if has_field(
                REQUEST_DOCTYPE,
                "final_table_edited_on"
            ):
                req.set(
                    "final_table_edited_on",
                    req.get("authorised_date")
                    if audit_edited
                    else None
                )

        available_value = flt(
            req.get(
                "current_package__residual__balance_value_rs"
            )
        )

        restored_total = flt(
            restore_result.get("total")
        )

        override_amount = max(
            restored_total - available_value,
            0
        )

        if has_field(
            REQUEST_DOCTYPE,
            "approval_override_amount"
        ):
            req.set(
                "approval_override_amount",
                round_money(override_amount)
            )

        audit_edited = (
            cint(req.get("audit_team_package_edited")) == 1
        )

        if audit_edited:
            override_note = (
                "Audit Team approved package restored after COO final "
                "automation failure. Restored Package Total: ₹" +
                cstr(round_money(restored_total))
            )

            if override_amount > 0:
                override_note = (
                    override_note +
                    ", Override Amount: ₹" +
                    cstr(round_money(override_amount))
                )

            override_note = override_note + "."
        else:
            override_note = ""

        if has_field(
            REQUEST_DOCTYPE,
            "approval_override_note"
        ):
            req.set(
                "approval_override_note",
                override_note
            )

        log_text = (
            "Automation failed and request was reopened to COO approval."
            "\nError Code: " +
            error_code +
            "\nRestored From: " +
            cstr(restore_result.get("source")) +
            "\nRestored Total: " +
            cstr(round_money(restore_result.get("total"))) +
            "\n\n" +
            message
        )

        if has_field(
            REQUEST_DOCTYPE,
            "package_conversion_log"
        ):
            req.set(
                "package_conversion_log",
                log_text[:10000]
            )

        req.flags.ignore_permissions = True
        req.flags.ignore_mandatory = True

        try:
            req.save(
                ignore_permissions=True,
                ignore_mandatory=True
            )
        except TypeError:
            req.save(ignore_permissions=True)

        return {
            "ok": True,
            "request_reopened": True,
            "restored": bool(
                restore_result.get("restored")
            ),
            "restored_from": cstr(
                restore_result.get("source")
            ),
            "restored_total": round_money(
                restore_result.get("total")
            ),
            "warning": ""
        }



    def safe_fail_request(
        request_name,
        message,
        error_code="AUTOMATION_FAILED"
    ):
        try:
            return fail_request(
                request_name,
                message,
                error_code
            )

        except Exception as rollback_error:
            rollback_message = cstr(
                rollback_error
            )

            try:
                frappe.log_error(
                    title="P2P Request Reopen Failed",
                    message=(
                        "Request: " +
                        cstr(request_name) +
                        "\nError Code: " +
                        cstr(error_code) +
                        "\nRollback Error:\n" +
                        rollback_message +
                        "\n\nOriginal Error:\n" +
                        cstr(message)
                    )[:10000]
                )
            except Exception:
                pass

            return {
                "ok": False,
                "request_reopened": False,
                "restored": False,
                "restored_from": "",
                "restored_total": 0,
                "warning": rollback_message
            }



    def failure_response(
        request_name,
        error_code,
        message
    ):
        reopen_result = safe_fail_request(
            request_name,
            message,
            error_code
        )

        return {
            "ok": False,
            "code": cstr(error_code),
            "message": cstr(message),
            "request_reopened": bool(
                reopen_result.get("request_reopened")
            ),
            "table_restored": bool(
                reopen_result.get("restored")
            ),
            "restored_from": cstr(
                reopen_result.get("restored_from")
            ),
            "restored_total": flt(
                reopen_result.get("restored_total")
            ),
            "rollback_warning": cstr(
                reopen_result.get("warning")
            )
        }


    def normalize_category(value):
        value = cstr(value)

        if not value:
            return ""

        mapping = {
            "All": ALL_CATEGORY,
            "All Healthcare Service Units": ALL_CATEGORY,
            "All Healthcare Service Units - LSACPL": ALL_CATEGORY,

            "Darmat": "Darmat - LSACPL",
            "Darmat - LSACPL": "Darmat - LSACPL",
            "Dermat": "Darmat - LSACPL",
            "Dermat - LSACPL": "Darmat - LSACPL",

            "Hair": "Hair - LSACPL",
            "Hair - LSACPL": "Hair - LSACPL",

            "Laser": "Laser - LSACPL",
            "Laser - LSACPL": "Laser - LSACPL",

            "Physiotherapy": "Physiotherapy - LSACPL",
            "Physiotherapy - LSACPL": "Physiotherapy - LSACPL",

            "Skin": "Skin - LSACPL",
            "Skin - LSACPL": "Skin - LSACPL",

            "Slimming": "Slimming - LSACPL",
            "Slimming - LSACPL": "Slimming - LSACPL",

            "LifeRise": "LifeRise - LSACPL",
            "LifeRise - LSACPL": "LifeRise - LSACPL",

            "HT": "HT - LSACPL",
            "HT - LSACPL": "HT - LSACPL"
        }

        if value in mapping:
            return mapping[value]

        return value


    def get_target_category(req):
        for fieldname in [
            "target_category",
            "shift_client_to_category",
            "conversion_category",
            "new_category",
            "category"
        ]:
            value = req.get(fieldname)

            if value:
                return normalize_category(value)

        if cint(req.get("skin")):
            return "Skin - LSACPL"

        if cint(req.get("hair")):
            return "Hair - LSACPL"

        if cint(req.get("laser")):
            return "Laser - LSACPL"

        if cint(req.get("slimming")):
            return "Slimming - LSACPL"

        if cint(req.get("cs")):
            return "LifeRise - LSACPL"

        if cint(req.get("ht")):
            return "HT - LSACPL"

        return ""


    def get_request_media(req):
        media = cstr(req.get("client_media"))

        if not media:
            media = cstr(req.get("media"))

        if not media:
            media = cstr(req.get("lead_source"))

        if not media:
            media = cstr(req.get("source"))

        return media


    def resolve_therapy_type(therapy):
        therapy = cstr(therapy)

        if not therapy:
            return None

        if frappe.db.exists(THERAPY_TYPE_DOCTYPE, therapy):
            return frappe.get_doc(THERAPY_TYPE_DOCTYPE, therapy)

        found = frappe.db.get_value(
            THERAPY_TYPE_DOCTYPE,
            {"therapy_type": therapy},
            "name"
        )

        if found:
            return frappe.get_doc(THERAPY_TYPE_DOCTYPE, found)

        return None



    def parse_converted_source_rows(source_rows):
        rows = []

        for row in (source_rows or []):
            therapy = first_value(
                row,
                [
                    "converted_package__service_name",
                    "service_package_name",
                    "therapy_type",
                    "service_name",
                    "package_name",
                    "plan"
                ]
            )

            qty = flt(
                first_value(
                    row,
                    [
                        "converted_quantity",
                        "new_sessions",
                        "new_total_sessions",
                        "no_of_sessions",
                        "qty",
                        "quantity",
                        "sessions"
                    ]
                )
            )

            amount = flt(
                first_value(
                    row,
                    [
                        "balance_amount",
                        "amount",
                        "total_amount",
                        "applied_amount",
                        "new_amount"
                    ]
                )
            )

            rate = flt(
                first_value(
                    row,
                    RATE_FIELDS
                )
            )

            completed = flt(
                first_value(
                    row,
                    [
                        "completed",
                        "completed_sessions",
                        "sessions_completed",
                        "availed_quantity"
                    ]
                )
            )

            applied_sessions = flt(
                first_value(
                    row,
                    [
                        "applied_sessions",
                        "new_sessions_to_apply",
                        "balance_quantity"
                    ]
                )
            )

            if applied_sessions <= 0:
                applied_sessions = max(
                    qty - completed,
                    0
                )

            value_sessions = applied_sessions

            if value_sessions <= 0:
                value_sessions = qty

            if (
                not rate and
                amount and
                value_sessions
            ):
                rate = amount / value_sessions

            if (
                not amount and
                rate and
                value_sessions
            ):
                amount = rate * value_sessions

            therapy = cstr(therapy)

            if therapy and qty > 0:
                rows.append({
                    "therapy": therapy,
                    "qty": cint(qty),
                    "rate": round_money(rate),
                    "amount": round_money(amount),
                    "completed": cint(completed),

                    "applied_sessions":
                        cint(applied_sessions),

                    "source_row_name":
                        cstr(
                            row.get(
                                "source_row_name"
                            )
                        ),

                    "source_plan":
                        cstr(
                            row.get(
                                "source_plan"
                            )
                        )
                })

        return rows


    def get_converted_rows(req):
        """
    Read the active converted table first.

    If it is empty or malformed, fall back through the
    approval snapshots in final-to-original order.
    """

        candidate_fields = [
            "converted_package__service_name",
            "coo_management_final_package",
            "audit_team_requested_package",
            "branch_requested_package"
        ]

        for fieldname in candidate_fields:
            source_rows = (
                req.get(fieldname) or []
            )

            parsed_rows = (
                parse_converted_source_rows(
                    source_rows
                )
            )

            if parsed_rows:
                return parsed_rows

        return []

    def add_plan_name(names, value):
        value = cstr(value)

        if not value:
            return

        raw_parts = value.split(",")

        for raw_part in raw_parts:
            part = cstr(raw_part)

            if part:
                if frappe.db.exists(THERAPY_PLAN_DOCTYPE, part):
                    if part not in names:
                        names.append(part)


    def get_source_plan_names(req):
        names = []

        # NEW: safest source for multiple selected plans.
        # This is a Small Text field, not a Link field.
        add_plan_name(names, req.get("source_therapy_plans_text"))

        # Keep old single Link field also.
        add_plan_name(names, req.get("source_therapy_plan"))

        # Existing fallback from original selected plan child rows.
        for row in (req.get("complete_package_details") or []):
            add_plan_name(names, row.get("seserp_entry"))
            add_plan_name(names, row.get("ses_erp_entry"))
            add_plan_name(names, row.get("therapy_plan"))
            add_plan_name(names, row.get("source_therapy_plan"))
            add_plan_name(names, row.get("old_therapy_plan"))

        # Extra fallback from converted package rows, if source_plan exists there.
        for row in (req.get("converted_package__service_name") or []):
            add_plan_name(names, row.get("source_plan"))

        final_names = []

        for name in names:
            if name:
                if name not in final_names:
                    final_names.append(name)

        return final_names

    def validate_converted_rows(converted_rows, target_category):
        if not converted_rows:
            return [False, "No converted package rows found."]

        seen = {}

        for row in converted_rows:
            therapy = cstr(row.get("therapy"))
            qty = cint(row.get("qty"))

            if not therapy:
                return [False, "Converted package has one row without Therapy Type."]

            if qty <= 0:
                return [False, "Therapy Type " + therapy + " has invalid quantity."]

            key = therapy_key(therapy)

            if key in seen:
                return [False, "Duplicate Therapy Type found: " + therapy]

            seen[key] = True

            therapy_doc = resolve_therapy_type(therapy)

            if not therapy_doc:
                return [False, "Therapy Type " + therapy + " does not exist."]

            if cint(therapy_doc.get("disabled")):
                return [False, "Therapy Type " + therapy + " is disabled."]

            if target_category != ALL_CATEGORY:
                unit = cstr(therapy_doc.get("healthcare_service_unit"))

                if unit != target_category:
                    return [
                        False,
                        "Therapy Type " + therapy +
                        " belongs to " + (unit or "blank category") +
                        ". Only " + target_category + " allowed."
                    ]

            row["therapy_type_name"] = therapy_doc.name

        return [True, ""]


    def get_therapy_plan_detail_table_field():
        meta = frappe.get_meta(THERAPY_PLAN_DOCTYPE)

        preferred = [
            "therapy_plan_details",
            "therapy_plan_detail",
            "therapy_details",
            "plan_details",
            "services",
            "items"
        ]

        for fieldname in preferred:
            df = meta.get_field(fieldname)

            if df:
                if df.fieldtype == "Table":
                    return fieldname

        for df in meta.fields:
            if df.fieldtype == "Table":
                label = cstr(df.label).lower()
                fieldname = cstr(df.fieldname).lower()

                if "therapy" in fieldname:
                    return df.fieldname

                if "therapy" in label:
                    return df.fieldname

                if "service" in fieldname:
                    return df.fieldname

                if "service" in label:
                    return df.fieldname

        return ""


    def get_child_doctype(parent_doctype, table_field):
        df = get_meta_field(parent_doctype, table_field)

        if df:
            return cstr(df.options)

        return ""


    def child_has(child_doctype, fieldname):
        return has_field(child_doctype, fieldname)


    def set_child_payload_if_has(payload, child_doctype, fieldname, value):
        if value is None:
            return

        if value == "":
            return

        if child_has(child_doctype, fieldname):
            payload[fieldname] = value


    def set_doc_field_if_exists(doc_obj, fieldname, value):
        if value is None:
            return

        if value == "":
            return

        if has_field(doc_obj.doctype, fieldname):
            doc_obj.set(fieldname, value)


    def get_total_sessions_from_child(row):
        return flt(first_value(row, TOTAL_SESSION_FIELDS))


    def get_balance_sessions_from_child(row):
        return flt(first_value(row, BALANCE_SESSION_FIELDS))


    def get_completed_sessions_from_child(row):
        direct_completed_value_exists = has_any_value(row, COMPLETED_SESSION_FIELDS)

        if direct_completed_value_exists:
            completed = flt(first_value(row, COMPLETED_SESSION_FIELDS))
            return completed

        total = get_total_sessions_from_child(row)
        balance_value_exists = has_any_value(row, BALANCE_SESSION_FIELDS)
        balance = get_balance_sessions_from_child(row)

        if balance_value_exists:
            derived_completed = total - balance

            if derived_completed < 0:
                return 0

            return derived_completed

        return 0


    def get_therapy_name_from_child(row):
        return cstr(first_value(row, THERAPY_NAME_FIELDS))


    def get_rate_from_child(row):
        return flt(first_value(row, RATE_FIELDS))


    def get_amount_from_child(row):
        amount = flt(first_value(row, AMOUNT_FIELDS))

        if amount:
            return amount

        total = get_total_sessions_from_child(row)
        rate = get_rate_from_child(row)

        if total and rate:
            return total * rate

        return 0.0


    def status_allows(value):
        df = get_meta_field(THERAPY_PLAN_DOCTYPE, "status")

        if not df:
            return False

        if df.fieldtype == "Select":
            if df.options:
                allowed = []

                for item in cstr(df.options).split("\n"):
                    clean_item = cstr(item)

                    if clean_item:
                        allowed.append(clean_item)

                if value not in allowed:
                    return False

        return True


    def set_parent_total_sessions(plan_doc, total_sessions):
        for fieldname in [
            "total_sessions",
            "no_of_sessions",
            "total_no_of_sessions",
            "total_session",
            "custom_total_sessions",
            "custom_no_of_sessions"
        ]:
            if has_field(THERAPY_PLAN_DOCTYPE, fieldname):
                plan_doc.set(fieldname, total_sessions)


    def set_parent_completed_balance(plan_doc, completed_sessions, balance_sessions):
        for fieldname in [
            "sessions_completed",
            "completed_sessions",
            "availed_quantity",
            "used_sessions",
            "total_sessions_completed",
            "custom_sessions_completed",
            "custom_completed_sessions"
        ]:
            if has_field(THERAPY_PLAN_DOCTYPE, fieldname):
                plan_doc.set(fieldname, completed_sessions)

        for fieldname in [
            "balance_quantity",
            "balance_sessions",
            "remaining_sessions",
            "pending_sessions",
            "available_sessions",
            "custom_balance_sessions"
        ]:
            if has_field(THERAPY_PLAN_DOCTYPE, fieldname):
                plan_doc.set(fieldname, balance_sessions)


    def set_parent_amount(plan_doc, amount):
        amount = round_money(amount)

        for fieldname in [
            "total_amount",
            "plan_amount",
            "package_amount",
            "grand_total",
            "custom_total_plan_amount"
        ]:
            if has_field(THERAPY_PLAN_DOCTYPE, fieldname):
                plan_doc.set(fieldname, amount)


    def build_child_values(child_doctype, therapy_type_name, total_sessions, completed_sessions, balance_sessions, rate, amount, target_category, set_therapy, set_money):
        values = {}

        if set_therapy:
            for fieldname in [
                "therapy_type",
                "service",
                "service_name",
                "item_code",
                "item_name"
            ]:
                if child_has(child_doctype, fieldname):
                    values[fieldname] = therapy_type_name

        if target_category:
            if child_has(child_doctype, "healthcare_service_unit"):
                values["healthcare_service_unit"] = target_category

        for fieldname in TOTAL_SESSION_FIELDS:
            if child_has(child_doctype, fieldname):
                values[fieldname] = total_sessions

        for fieldname in COMPLETED_SESSION_FIELDS:
            if child_has(child_doctype, fieldname):
                values[fieldname] = completed_sessions

        for fieldname in BALANCE_SESSION_FIELDS:
            if child_has(child_doctype, fieldname):
                values[fieldname] = balance_sessions

        if set_money:
            for fieldname in RATE_FIELDS:
                if child_has(child_doctype, fieldname):
                    values[fieldname] = round_money(rate)

            for fieldname in AMOUNT_FIELDS:
                if child_has(child_doctype, fieldname):
                    values[fieldname] = round_money(amount)

        return values


    def apply_child_values(row, values):
        for fieldname in values:
            try:
                row.set(fieldname, values[fieldname])
            except Exception:
                pass


    def create_conversion_snapshot_for_plan(request_name, plan_name):
        if not frappe.db.exists("DocType", SNAPSHOT_DOCTYPE):
            return ""

        if not frappe.db.exists(THERAPY_PLAN_DOCTYPE, plan_name):
            return ""

        old_plan = frappe.get_doc(THERAPY_PLAN_DOCTYPE, plan_name)

        table_field = get_therapy_plan_detail_table_field()
        rows = old_plan.get(table_field) or []

        before_total_sessions = 0
        before_completed_sessions = 0
        before_total_amount = 0.0

        snapshot = frappe.new_doc(SNAPSHOT_DOCTYPE)

        if has_field(SNAPSHOT_DOCTYPE, "therapy_plan"):
            snapshot.therapy_plan = plan_name

        if has_field(SNAPSHOT_DOCTYPE, "conversion_request"):
            snapshot.conversion_request = request_name

        if has_field(SNAPSHOT_DOCTYPE, "patient"):
            snapshot.patient = old_plan.get("patient") or old_plan.get("client")

        if has_field(SNAPSHOT_DOCTYPE, "patient_name"):
            snapshot.patient_name = old_plan.get("patient_name") or old_plan.get("client_name")

        if has_field(SNAPSHOT_DOCTYPE, "branch"):
            snapshot.branch = old_plan.get("branch")

        if has_field(SNAPSHOT_DOCTYPE, "snapshot_datetime"):
            snapshot.snapshot_datetime = frappe.utils.now()

        if has_field(SNAPSHOT_DOCTYPE, "therapy_plan_template"):
            snapshot.therapy_plan_template = old_plan.get("therapy_plan_template")

        for row in rows:
            therapy_type = get_therapy_name_from_child(row)
            total_sessions = cint(get_total_sessions_from_child(row))
            completed_sessions = cint(get_completed_sessions_from_child(row))
            rate = round_money(get_rate_from_child(row))
            amount = round_money(get_amount_from_child(row))

            before_total_sessions = before_total_sessions + total_sessions
            before_completed_sessions = before_completed_sessions + completed_sessions
            before_total_amount = before_total_amount + amount

            child = snapshot.append("snapshot_rows", {})

            therapy_doc = resolve_therapy_type(therapy_type)

            if therapy_doc:
                child.therapy_type = therapy_doc.name

            child.no_of_sessions = total_sessions
            child.sessions_completed = completed_sessions
            child.rate = rate
            child.amount = amount
            child.source_row_name = row.name

        if has_field(SNAPSHOT_DOCTYPE, "before_total_sessions"):
            snapshot.before_total_sessions = before_total_sessions

        if has_field(SNAPSHOT_DOCTYPE, "before_total_sessions_completed"):
            snapshot.before_total_sessions_completed = before_completed_sessions

        if has_field(SNAPSHOT_DOCTYPE, "before_total_amount"):
            snapshot.before_total_amount = round_money(before_total_amount)

        snapshot.flags.ignore_permissions = True
        snapshot.flags.ignore_mandatory = True

        try:
            snapshot.insert(ignore_permissions=True, ignore_mandatory=True)
        except TypeError:
            snapshot.insert(ignore_permissions=True)

        return snapshot.name


    def create_conversion_snapshots(request_name, source_plan_names):
        created = []

        for plan_name in source_plan_names:
            existing = ""

            try:
                existing = frappe.db.get_value(
                    SNAPSHOT_DOCTYPE,
                    {
                        "conversion_request": request_name,
                        "therapy_plan": plan_name
                    },
                    "name"
                )
            except Exception:
                existing = ""

            if existing:
                created.append(existing)
            else:
                snap_name = create_conversion_snapshot_for_plan(request_name, plan_name)

                if snap_name:
                    created.append(snap_name)

        return created


    def create_new_therapy_plan(req, converted_rows, target_category, source_plan_names):
        table_field = get_therapy_plan_detail_table_field()

        if not table_field:
            raise Exception("Could not find Therapy Plan child table field.")

        child_doctype = get_child_doctype(THERAPY_PLAN_DOCTYPE, table_field)

        if not child_doctype:
            raise Exception("Could not find Therapy Plan child table doctype.")

        source_plan = None

        if source_plan_names:
            source_plan = frappe.get_doc(THERAPY_PLAN_DOCTYPE, source_plan_names[0])

        new_plan = frappe.new_doc(THERAPY_PLAN_DOCTYPE)

        client_id = req.get("client") or req.get("client_name") or req.get("patient")
        client_full_name = req.get("client_full_name") or req.get("patient_name") or req.get("client_name")
        branch = req.get("branch")
        client_media = get_request_media(req)

        if source_plan:
            if not client_id:
                client_id = source_plan.get("patient") or source_plan.get("client")

            if not client_full_name:
                client_full_name = source_plan.get("patient_name") or source_plan.get("client_name")

            if not branch:
                branch = source_plan.get("branch")

        set_doc_field_if_exists(new_plan, "patient", client_id)
        set_doc_field_if_exists(new_plan, "client", client_id)
        set_doc_field_if_exists(new_plan, "patient_name", client_full_name)
        set_doc_field_if_exists(new_plan, "client_name", client_full_name)
        set_doc_field_if_exists(new_plan, "branch", branch)
        set_doc_field_if_exists(new_plan, "category", target_category)
        set_doc_field_if_exists(new_plan, "healthcare_service_unit", target_category)
        set_doc_field_if_exists(new_plan, "custom_category", target_category)
        set_doc_field_if_exists(new_plan, "media", client_media)

        # Converted new Therapy Plan is already backed by old paid invoice value.
        # Mark it invoiced so ERP records treat it as an invoiced Therapy Plan.
        set_doc_field_if_exists(new_plan, "invoiced", 1)

        # This Therapy Plan was produced through an approved package conversion.
        set_doc_field_if_exists(
            new_plan,
            "therapy_plan_already_taken_",
            1
        )

        # Clear notation for newly-created multi-source P2P Therapy Plan.
        set_doc_field_if_exists(new_plan, "custom_p2p_conversion_origin", "P2P Multi Source Conversion")
        set_doc_field_if_exists(new_plan, "custom_p2p_conversion_request", req.name)
        set_doc_field_if_exists(new_plan, "custom_p2p_source_therapy_plans", ", ".join(source_plan_names))
        set_doc_field_if_exists(
            new_plan,
            "custom_p2p_conversion_note",
            "Created from multiple source Therapy Plans through P2P conversion. Source plans were closed/equalized after snapshot."
        )

        today = frappe.utils.today()

        set_doc_field_if_exists(new_plan, "start_date", today)
        set_doc_field_if_exists(new_plan, "date", today)
        set_doc_field_if_exists(new_plan, "posting_date", today)

        if source_plan:
            for fieldname in [
                "company",
                "medical_department",
                "department",
                "practitioner",
                "healthcare_practitioner",
                "therapy_plan_template"
            ]:
                value = source_plan.get(fieldname)

                if value:
                    set_doc_field_if_exists(new_plan, fieldname, value)

        if has_field(THERAPY_PLAN_DOCTYPE, "status"):
            if status_allows("In Progress"):
                new_plan.set("status", "In Progress")
            elif status_allows("Active"):
                new_plan.set("status", "Active")
            elif status_allows("Not Started"):
                new_plan.set("status", "Not Started")

        total_sessions = 0
        total_amount = 0.0

        for row in converted_rows:
            therapy_type_name = cstr(row.get("therapy_type_name") or row.get("therapy"))
            qty = cint(row.get("qty"))
            rate = flt(row.get("rate"))
            amount = flt(row.get("amount"))

            if not rate and amount and qty:
                rate = amount / qty

            if not amount and qty and rate:
                amount = qty * rate

            payload = build_child_values(
                child_doctype,
                therapy_type_name,
                qty,
                0,
                qty,
                rate,
                amount,
                target_category,
                True,
                True
            )

            new_plan.append(table_field, payload)

            total_sessions = total_sessions + qty
            total_amount = total_amount + amount

        set_parent_total_sessions(new_plan, total_sessions)
        set_parent_completed_balance(new_plan, 0, total_sessions)

        request_total = flt(req.get("new_package_total_price_rs"))

        if request_total > 0:
            set_parent_amount(new_plan, request_total)
        else:
            set_parent_amount(new_plan, total_amount)

        new_plan.flags.ignore_permissions = True
        new_plan.flags.ignore_mandatory = True

        try:
            new_plan.insert(
                ignore_permissions=True,
                ignore_mandatory=True
            )
        except TypeError:
            new_plan.insert(
                ignore_permissions=True
            )

        # Always apply these values after successful insertion.
        db_set_values(
            THERAPY_PLAN_DOCTYPE,
            new_plan.name,
            {
                "invoiced": 1,

                # IMPORTANT
                "therapy_plan_already_taken_": 1,

                "custom_p2p_conversion_origin":
                    "P2P Multi Source Conversion",

                "custom_p2p_conversion_request":
                    req.name,

                "custom_p2p_source_therapy_plans":
                    ", ".join(source_plan_names),

                "custom_p2p_conversion_note":
                    "Created from multiple source Therapy Plans "
                    "through P2P conversion. Source plans were "
                    "closed/equalized after snapshot."
            },
            update_modified=False
        )

        return new_plan.name


    def build_equalize_values(child_doctype, completed):
        values = {}

        for fieldname in TOTAL_SESSION_FIELDS:
            if child_has(child_doctype, fieldname):
                values[fieldname] = completed

        for fieldname in COMPLETED_SESSION_FIELDS:
            if child_has(child_doctype, fieldname):
                values[fieldname] = completed

        for fieldname in BALANCE_SESSION_FIELDS:
            if child_has(child_doctype, fieldname):
                values[fieldname] = 0

        return values


    def close_source_therapy_plan(plan_name):
        old_plan = frappe.get_doc(THERAPY_PLAN_DOCTYPE, plan_name)

        table_field = get_therapy_plan_detail_table_field()
        child_doctype = get_child_doctype(THERAPY_PLAN_DOCTYPE, table_field)

        rows = old_plan.get(table_field) or []

        if not rows:
            return "No child rows found in " + plan_name + ". table_field=" + table_field

        completed_sum = 0.0
        before_total_sum = 0.0
        before_balance_sum = 0.0
        updated_rows = 0
        debug_lines = []

        for row in rows:
            before_total = get_total_sessions_from_child(row)
            before_balance = get_balance_sessions_from_child(row)
            completed = get_completed_sessions_from_child(row)

            if completed < 0:
                completed = 0

            before_total_sum = before_total_sum + before_total
            before_balance_sum = before_balance_sum + before_balance
            completed_sum = completed_sum + completed

            values = build_equalize_values(child_doctype, completed)

            for fieldname in values:
                try:
                    row.set(fieldname, values[fieldname])
                except Exception:
                    pass

            if values:
                if row.name:
                    db_set_values(
                        child_doctype,
                        row.name,
                        values,
                        update_modified=False
                    )
                    updated_rows = updated_rows + 1

            debug_lines.append(
                "row=" + cstr(row.name) +
                ", therapy=" + get_therapy_name_from_child(row) +
                ", before_total=" + cstr(before_total) +
                ", before_balance=" + cstr(before_balance) +
                ", completed_used_for_equalization=" + cstr(completed) +
                ", new_total=" + cstr(completed) +
                ", new_balance=0"
            )

        parent_values = {}

        for fieldname in [
            "total_sessions",
            "no_of_sessions",
            "total_no_of_sessions",
            "total_session",
            "custom_total_sessions",
            "custom_no_of_sessions"
        ]:
            if has_field(THERAPY_PLAN_DOCTYPE, fieldname):
                parent_values[fieldname] = completed_sum

        for fieldname in [
            "sessions_completed",
            "completed_sessions",
            "availed_quantity",
            "used_sessions",
            "total_sessions_completed",
            "custom_sessions_completed",
            "custom_completed_sessions"
        ]:
            if has_field(THERAPY_PLAN_DOCTYPE, fieldname):
                parent_values[fieldname] = completed_sum

        for fieldname in [
            "balance_quantity",
            "balance_sessions",
            "remaining_sessions",
            "pending_sessions",
            "available_sessions",
            "custom_balance_sessions"
        ]:
            if has_field(THERAPY_PLAN_DOCTYPE, fieldname):
                parent_values[fieldname] = 0

        # Do not change old Therapy Plan parent status.

        db_set_values(
            THERAPY_PLAN_DOCTYPE,
            plan_name,
            parent_values,
            update_modified=True
        )

        return (
            "Closed sessions only for " + plan_name +
            ": table_field=" + table_field +
            ", child_doctype=" + child_doctype +
            ", rows=" + cstr(len(rows)) +
            ", updated_rows=" + cstr(updated_rows) +
            ", before_total_sum=" + cstr(before_total_sum) +
            ", before_balance_sum=" + cstr(before_balance_sum) +
            ", completed_sum=" + cstr(completed_sum) +
            ". Status not changed. " + " | ".join(debug_lines)
        )


    def build_converted_map(converted_rows):
        converted_by_key = {}

        for row in converted_rows:
            therapy_name = cstr(row.get("therapy_type_name") or row.get("therapy"))
            key = therapy_key(therapy_name)

            if key:
                converted_by_key[key] = row

        return converted_by_key


    def get_converted_rate_amount(row, final_total_sessions, completed_sessions):
        result = {}

        rate = flt(row.get("rate"))
        amount = flt(row.get("amount"))

        applied_sessions = final_total_sessions - completed_sessions

        if applied_sessions < 0:
            applied_sessions = 0

        if not amount and rate and applied_sessions:
            amount = rate * applied_sessions

        result["rate"] = round_money(rate)
        result["amount"] = round_money(amount)

        return result


    def update_existing_therapy_plan_for_single_source(req, plan_name, converted_rows, target_category, client_media):
        plan = frappe.get_doc(THERAPY_PLAN_DOCTYPE, plan_name)

        table_field = get_therapy_plan_detail_table_field()

        if not table_field:
            raise Exception("Could not find Therapy Plan child table field.")

        child_doctype = get_child_doctype(THERAPY_PLAN_DOCTYPE, table_field)

        if not child_doctype:
            raise Exception("Could not find Therapy Plan child table doctype.")

        old_rows = plan.get(table_field) or []

        if not old_rows:
            raise Exception("Selected source Therapy Plan has no therapy rows: " + plan_name)

        converted_by_key = build_converted_map(converted_rows)
        used_converted_keys = {}
        kept_rows = []
        debug_lines = []

        total_sessions_sum = 0
        completed_sessions_sum = 0
        balance_sessions_sum = 0

        removed_zero_completed_rows = 0
        protected_rows = 0
        converted_existing_rows = 0
        added_new_rows = 0

        for row in old_rows:
            old_therapy = get_therapy_name_from_child(row)
            old_key = therapy_key(old_therapy)

            old_total = cint(get_total_sessions_from_child(row))
            old_completed = cint(get_completed_sessions_from_child(row))

            if old_completed < 0:
                old_completed = 0

            converted = None

            if old_key:
                if old_key in converted_by_key:
                    if old_key not in used_converted_keys:
                        converted = converted_by_key[old_key]

            # ----------------------------------------------------
            # RULE 1:
            # Completed rows must never be removed.
            # They can only be reduced down to completed sessions.
            # ----------------------------------------------------
            if old_completed > 0:
                protected_rows = protected_rows + 1

                if converted:
                    converted_qty = cint(converted.get("qty"))

                    final_total = converted_qty

                    if final_total < old_completed:
                        final_total = old_completed

                    balance = final_total - old_completed

                    money = get_converted_rate_amount(converted, final_total, old_completed)

                    values = build_child_values(
                        child_doctype,
                        cstr(converted.get("therapy_type_name") or converted.get("therapy") or old_therapy),
                        final_total,
                        old_completed,
                        balance,
                        money.get("rate"),
                        money.get("amount"),
                        target_category,
                        True,
                        True
                    )

                    apply_child_values(row, values)

                    used_converted_keys[old_key] = True
                    converted_existing_rows = converted_existing_rows + 1

                    debug_lines.append(
                        "PROTECTED_UPDATED row=" + cstr(row.name) +
                        ", therapy=" + old_therapy +
                        ", old_total=" + cstr(old_total) +
                        ", completed=" + cstr(old_completed) +
                        ", final_total=" + cstr(final_total) +
                        ", balance=" + cstr(balance)
                    )
                else:
                    final_total = old_completed
                    balance = 0

                    values = build_child_values(
                        child_doctype,
                        old_therapy,
                        final_total,
                        old_completed,
                        balance,
                        0,
                        0,
                        target_category,
                        False,
                        False
                    )

                    apply_child_values(row, values)

                    debug_lines.append(
                        "PROTECTED_CLOSED row=" + cstr(row.name) +
                        ", therapy=" + old_therapy +
                        ", old_total=" + cstr(old_total) +
                        ", completed=" + cstr(old_completed) +
                        ", final_total=" + cstr(final_total) +
                        ", balance=0"
                    )

                kept_rows.append(row)

                total_sessions_sum = total_sessions_sum + final_total
                completed_sessions_sum = completed_sessions_sum + old_completed
                balance_sessions_sum = balance_sessions_sum + balance

            # ----------------------------------------------------
            # RULE 2:
            # Rows with 0 completed sessions can be removed.
            # If same therapy is in converted rows, keep/update it.
            # ----------------------------------------------------
            else:
                if converted:
                    final_total = cint(converted.get("qty"))

                    if final_total > 0:
                        balance = final_total

                        money = get_converted_rate_amount(converted, final_total, 0)

                        values = build_child_values(
                            child_doctype,
                            cstr(converted.get("therapy_type_name") or converted.get("therapy") or old_therapy),
                            final_total,
                            0,
                            balance,
                            money.get("rate"),
                            money.get("amount"),
                            target_category,
                            True,
                            True
                        )

                        apply_child_values(row, values)

                        kept_rows.append(row)

                        total_sessions_sum = total_sessions_sum + final_total
                        balance_sessions_sum = balance_sessions_sum + balance
                        used_converted_keys[old_key] = True
                        converted_existing_rows = converted_existing_rows + 1

                        debug_lines.append(
                            "ZERO_COMPLETED_CONVERTED_KEEP row=" + cstr(row.name) +
                            ", therapy=" + old_therapy +
                            ", old_total=" + cstr(old_total) +
                            ", final_total=" + cstr(final_total) +
                            ", balance=" + cstr(balance)
                        )
                    else:
                        removed_zero_completed_rows = removed_zero_completed_rows + 1

                        debug_lines.append(
                            "ZERO_COMPLETED_REMOVED_INVALID_QTY row=" + cstr(row.name) +
                            ", therapy=" + old_therapy
                        )
                else:
                    removed_zero_completed_rows = removed_zero_completed_rows + 1

                    debug_lines.append(
                        "ZERO_COMPLETED_REMOVED row=" + cstr(row.name) +
                        ", therapy=" + old_therapy +
                        ", old_total=" + cstr(old_total)
                    )

        # Remove zero-completed rows not kept.
        plan.set(table_field, kept_rows)

        # --------------------------------------------------------
        # RULE 3:
        # Converted therapies that did not exist in old table
        # are added as new rows.
        # --------------------------------------------------------
        for key in converted_by_key:
            if key not in used_converted_keys:
                converted = converted_by_key[key]

                therapy_name = cstr(converted.get("therapy_type_name") or converted.get("therapy"))
                final_total = cint(converted.get("qty"))

                if final_total <= 0:
                    continue

                money = get_converted_rate_amount(converted, final_total, 0)

                payload = build_child_values(
                    child_doctype,
                    therapy_name,
                    final_total,
                    0,
                    final_total,
                    money.get("rate"),
                    money.get("amount"),
                    target_category,
                    True,
                    True
                )

                plan.append(table_field, payload)

                total_sessions_sum = total_sessions_sum + final_total
                balance_sessions_sum = balance_sessions_sum + final_total
                added_new_rows = added_new_rows + 1

                debug_lines.append(
                    "NEW_ROW_ADDED therapy=" + therapy_name +
                    ", total=" + cstr(final_total) +
                    ", completed=0" +
                    ", balance=" + cstr(final_total)
                )

        if total_sessions_sum <= 0:
            raise Exception("Same-plan update would result in zero total sessions. Conversion blocked.")

        set_doc_field_if_exists(plan, "category", target_category)
        set_doc_field_if_exists(plan, "healthcare_service_unit", target_category)
        set_doc_field_if_exists(plan, "custom_category", target_category)
        set_doc_field_if_exists(plan, "media", client_media)
        set_doc_field_if_exists(
            plan,
            "therapy_plan_already_taken_",
            1
        )

        set_parent_total_sessions(plan, total_sessions_sum)
        set_parent_completed_balance(plan, completed_sessions_sum, balance_sessions_sum)

        request_total = flt(req.get("new_package_total_price_rs"))

        if request_total > 0:
            set_parent_amount(plan, request_total)

        # Do not force status to Completed.
        # Do not overwrite existing status unless it is blank.
        if has_field(THERAPY_PLAN_DOCTYPE, "status"):
            if not cstr(plan.get("status")):
                if status_allows("In Progress"):
                    plan.set("status", "In Progress")
                elif status_allows("Active"):
                    plan.set("status", "Active")

        plan.flags.ignore_permissions = True
        plan.flags.ignore_mandatory = True

        try:
            plan.save(ignore_permissions=True, ignore_mandatory=True)
        except TypeError:
            plan.save(ignore_permissions=True)

        return (
            "Same Therapy Plan updated: " + plan_name +
            "\ntable_field=" + table_field +
            "\nchild_doctype=" + child_doctype +
            "\nprotected_rows=" + cstr(protected_rows) +
            "\nconverted_existing_rows=" + cstr(converted_existing_rows) +
            "\nremoved_zero_completed_rows=" + cstr(removed_zero_completed_rows) +
            "\nadded_new_rows=" + cstr(added_new_rows) +
            "\nfinal_total_sessions=" + cstr(total_sessions_sum) +
            "\nfinal_completed_sessions=" + cstr(completed_sessions_sum) +
            "\nfinal_balance_sessions=" + cstr(balance_sessions_sum) +
            "\n\nRow Log:\n" +
            "\n".join(debug_lines)
        )


    def run_api():
        request_name = cstr(
            frappe.form_dict.get("request_name") or
            frappe.form_dict.get("name")
        )

        if not request_name:
            raise Exception("request_name is required.")

        if not frappe.db.exists(REQUEST_DOCTYPE, request_name):
            raise Exception("P2P request not found: " + request_name)

        req = frappe.get_doc(REQUEST_DOCTYPE, request_name)

        if cint(req.get("package_conversion_applied")) == 1:
            return {
                "ok": True,
                "code": "ALREADY_PROCESSED",
                "message": "Already processed.",
                "updated_therapy_plan": cstr(req.get("updated_therapy_plan")),
                "source_plans": get_source_plan_names(req)
            }

        if cstr(req.get("automation_status")) == "Processing":
            return {
                "ok": False,
                "code": "ALREADY_PROCESSING",
                "message": "This request is already being processed. Refresh the request before trying again.",
                "request_reopened": False
            }

        start_log = (
            "API STARTED: " + req.name +
            "\nfinal_approval_status=" + cstr(req.get("final_approval_status")) +
            "\napproval_stage=" + cstr(req.get("approval_stage")) +
            "\nautomation_status=" + cstr(req.get("automation_status")) +
            "\npackage_conversion_applied=" + cstr(req.get("package_conversion_applied")) +
            "\nupdated_therapy_plan=" + cstr(req.get("updated_therapy_plan"))
        )

        set_request_values(request_name, {
            "package_conversion_log": start_log
        })

        if cstr(req.get("final_approval_status")) != "Approved" and cstr(req.get("approval_stage")) != "Approved":
            return failure_response(
                request_name,
                "NOT_FINAL_APPROVED",
                "Request is not final approved."
            )

        target_category = get_target_category(req)

        if not target_category:
            return failure_response(
                request_name,
                "TARGET_CATEGORY_MISSING",
                "Target category is missing."
            )

        client_media = get_request_media(req)

        if not client_media:
            return failure_response(
                request_name,
                "CLIENT_MEDIA_MISSING",
                "Client Media is missing. Please select Client Media before final approval."
            )

        if not frappe.db.exists(LEAD_SOURCE_DOCTYPE, client_media):
            return failure_response(
                request_name,
                "INVALID_CLIENT_MEDIA",
                "Invalid Client Media: " + client_media
            )

        converted_rows = get_converted_rows(req)

        validation_result = validate_converted_rows(converted_rows, target_category)
        ok = validation_result[0]
        msg = validation_result[1]

        if not ok:
            return failure_response(
                request_name,
                "CONVERTED_TABLE_VALIDATION_FAILED",
                msg
            )

        source_plan_names = get_source_plan_names(req)

        if not source_plan_names:
            return failure_response(
                request_name,
                "SOURCE_PLANS_MISSING",
                "No source Therapy Plans found."
            )

        snapshot_names = create_conversion_snapshots(request_name, source_plan_names)

        set_request_values(request_name, {
            "automation_status": "Processing",
            "approval_display_status": "Processing Therapy Plan Update",
            "package_conversion_log":
                start_log +
                "\nSOURCE PLANS FOUND: " + ", ".join(source_plan_names) +
                "\nSNAPSHOTS: " + ", ".join(snapshot_names) +
                "\nCLIENT MEDIA: " + client_media +
                "\nTARGET CATEGORY: " + target_category
        })

        mode = ""
        new_plan_name = ""
        close_logs = []

        # ========================================================
        # NEW RULE:
        # One selected source Therapy Plan = edit same plan table.
        # ========================================================
        if len(source_plan_names) == 1:
            source_plan_name = source_plan_names[0]

            same_plan_log = update_existing_therapy_plan_for_single_source(
                req,
                source_plan_name,
                converted_rows,
                target_category,
                client_media
            )

            new_plan_name = source_plan_name
            mode = "Same Therapy Plan Updated"

            close_logs.append(same_plan_log)

        # ========================================================
        # Multiple selected source Therapy Plans = create new plan.
        # ========================================================
        else:
            existing_new_plan = cstr(req.get("updated_therapy_plan"))

            if existing_new_plan:
                if frappe.db.exists(THERAPY_PLAN_DOCTYPE, existing_new_plan):
                    new_plan_name = existing_new_plan

                    if has_field(THERAPY_PLAN_DOCTYPE, "media"):
                        current_media = cstr(
                            frappe.db.get_value(
                                THERAPY_PLAN_DOCTYPE,
                                new_plan_name,
                                "media"
                            )
                        )

                        if not current_media:
                            db_set_values(
                                THERAPY_PLAN_DOCTYPE,
                                new_plan_name,
                                {
                                    "media": client_media
                                },
                                update_modified=True
                            )
                else:
                    new_plan_name = create_new_therapy_plan(
                        req,
                        converted_rows,
                        target_category,
                        source_plan_names
                    )

                    set_request_values(request_name, {
                        "updated_therapy_plan": new_plan_name
                    })
            else:
                new_plan_name = create_new_therapy_plan(
                    req,
                    converted_rows,
                    target_category,
                    source_plan_names
                )

                set_request_values(request_name, {
                    "updated_therapy_plan": new_plan_name
                })

            # Multiple-source conversion always means the target/new Therapy Plan
            # must be treated as invoiced.
            if new_plan_name:
                db_set_values(
                    THERAPY_PLAN_DOCTYPE,
                    new_plan_name,
                    {
                        "invoiced": 1
                    },
                    update_modified=True
                )

            mode = "New Therapy Plan Created"

            for plan_name in source_plan_names:
                close_logs.append(close_source_therapy_plan(plan_name))

        # ========================================================
        # FINAL THERAPY PLAN FLAG
        # Only reached after Therapy Plan conversion succeeded.
        # ========================================================

        if new_plan_name and frappe.db.exists(
            THERAPY_PLAN_DOCTYPE,
            new_plan_name
        ):
            db_set_values(
                THERAPY_PLAN_DOCTYPE,
                new_plan_name,
                {
                    "therapy_plan_already_taken_": 1
                },
                update_modified=True
            )

        final_log = (
            "Process Completed.\n"
            "Mode: " + mode +
            "\nUpdated Therapy Plan: " + new_plan_name +
            "\nSource Plans: " + ", ".join(source_plan_names) +
            "\nSnapshot Records: " + ", ".join(snapshot_names) +
            "\nClient Media: " + client_media +
            "\nTarget Category: " + target_category +
            "\n\nTherapy Plan Update Log:\n" +
            "\n".join(close_logs)
        )

        set_request_values(request_name, {
            "updated_therapy_plan": new_plan_name,
            "package_conversion_applied": 1,
            "automation_status": "Process Completed",
            "approval_display_status": "Process Completed",
            "current_tab_step": 5,
            "package_conversion_log": final_log[:10000]
        })

        return {
            "ok": True,
            "code": "PROCESS_COMPLETED",
            "message": "Process Completed",
            "mode": mode,
            "updated_therapy_plan": new_plan_name,
            "source_plans": source_plan_names,
            "snapshots": snapshot_names,
            "client_media": client_media,
            "target_category": target_category
        }


    try:
        frappe.response["message"] = run_api()

    except Exception as e:
        user_message = cstr(e) or "Unexpected P2P final automation error."
        technical_message = user_message

        try:
            trace = frappe.get_traceback()

            if trace:
                technical_message = technical_message + "\n\n" + trace
        except Exception:
            pass

        request_name = cstr(
            frappe.form_dict.get("request_name") or
            frappe.form_dict.get("name")
        )

        # Roll back snapshots / Therapy Plan writes performed by this API call.
        # The COO approval itself was saved by the previous browser request, so
        # fail_request() explicitly reopens and restores that request afterwards.
        database_rollback_warning = ""

        try:
            frappe.db.rollback()
        except Exception as rollback_exception:
            database_rollback_warning = cstr(rollback_exception)

        reopen_result = {
            "ok": False,
            "request_reopened": False,
            "restored": False,
            "restored_from": "",
            "warning": ""
        }

        if request_name:
            reopen_result = safe_fail_request(
                request_name,
                technical_message,
                "AUTOMATION_EXCEPTION"
            )

        try:
            frappe.log_error(
                title="P2P Final Automation Failed",
                message=(
                    "Request: " + request_name +
                    "\nUser Error: " + user_message +
                    "\nDatabase Rollback Warning: " + database_rollback_warning +
                    "\nRequest Reopen Warning: " + cstr(reopen_result.get("warning")) +
                    "\n\nTechnical Details:\n" + technical_message
                )[:10000]
            )
        except Exception:
            pass

        frappe.response["message"] = {
            "ok": False,
            "code": "AUTOMATION_EXCEPTION",
            "message": user_message,
            "request_reopened": bool(reopen_result.get("request_reopened")),
            "table_restored": bool(reopen_result.get("restored")),
            "restored_from": cstr(reopen_result.get("restored_from")),
            "rollback_warning": (
                cstr(reopen_result.get("warning")) or
                database_rollback_warning
            )
        }
