"""block therapy session while conversion

Original API: therapy_plan_conversion_block_status
Source modified: 2026-07-28 15:26:10.616395
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
    therapy_plan = str(
        frappe.form_dict.get("therapy_plan") or ""
    ).strip()

    P2P_DOCTYPE = (
        "LIFE Client Package Conversion Same Client Package To Package"
    )

    C2C_DOCTYPE = (
        "Client Package Conversion Client To Client"
    )

    CHILD_DOCTYPE = "Client Details Current Package Details"

    result = {
        "blocked": False,
        "therapy_plan": therapy_plan,
        "request": None,
        "source": "",
        "matched_request_count": 0,
        "latest_connected_request": None
    }


    # ============================================================
    # COMMON HELPERS
    # ============================================================

    def clean(value):
        return str(value or "").strip()


    def checked(value):
        return clean(value).lower() in [
            "1",
            "true",
            "yes"
        ]


    def doctype_has_field(doctype, fieldname):
        try:
            return bool(
                frappe.get_meta(doctype).get_field(fieldname)
            )
        except Exception:
            return False


    def add_candidate(
        candidates,
        doctype,
        name,
        modified=""
    ):
        name = clean(name)

        if not name:
            return

        key = doctype + "::" + name

        for existing in candidates:
            if existing.get("key") == key:
                return

        candidates.append({
            "key": key,
            "doctype": doctype,
            "name": name,
            "modified": clean(modified)
        })


    def text_contains_exact_plan(
        value,
        plan_name
    ):
        value = clean(value)
        plan_name = clean(plan_name)

        if not value or not plan_name:
            return False

        normalized = value

        normalized = normalized.replace(
            "\r",
            ","
        )

        normalized = normalized.replace(
            "\n",
            ","
        )

        normalized = normalized.replace(
            "\t",
            ","
        )

        normalized = normalized.replace(
            ";",
            ","
        )

        normalized = normalized.replace(
            "|",
            ","
        )

        for item in normalized.split(","):
            item = clean(item)

            item = item.strip(
                "[]'\" "
            )

            if item == plan_name:
                return True

        return False


    # ============================================================
    # FINISHED / REJECTED / COMPLETED STATUS CHECK
    # ============================================================

    def status_is_terminal(value):
        value = clean(value).lower()

        if not value:
            return False

        # Any rejected request must not block.
        if "reject" in value:
            return True

        # Cancelled requests must not block.
        if "cancel" in value:
            return True

        if value == "skipped":
            return True

        if value == "completed":
            return True

        if value == "process completed":
            return True

        if "process completed" in value:
            return True

        if value == "transfer completed":
            return True

        if value.endswith(" completed"):
            return True

        return False


    def request_is_finished(doc):
        # Cancelled ERP document.
        try:
            if int(
                doc.get("docstatus") or 0
            ) == 2:
                return True
        except Exception:
            pass

        # P2P automation already applied.
        if checked(
            doc.get("package_conversion_applied")
        ):
            return True

        # C2C automation already applied.
        if checked(
            doc.get("package_transfer_applied")
        ):
            return True

        status_values = [
            doc.get("approval_display_status"),
            doc.get("conversion_status"),
            doc.get("approval_stage"),
            doc.get("final_approval_status"),
            doc.get("automation_status")
        ]

        for value in status_values:
            if status_is_terminal(value):
                return True

        return False


    # ============================================================
    # DISPLAY STATUS
    # ============================================================

    def get_display_status(doc):
        values = [
            doc.get("approval_display_status"),
            doc.get("conversion_status"),
            doc.get("approval_stage"),
            doc.get("automation_status"),
            doc.get("final_approval_status")
        ]

        for value in values:
            value = clean(value)

            if not value:
                continue

            value = value.replace(
                "Operations Head Approval Pending",
                "Audit Team Approval Pending"
            )

            value = value.replace(
                "Operations Head",
                "Audit Team"
            )

            return value

        return "Approval Pending"


    # ============================================================
    # BUILD RESPONSE DATA FOR ONE REQUEST
    # ============================================================

    def build_request_data(candidate):
        doc = frappe.get_doc(
            candidate.get("doctype"),
            candidate.get("name")
        )

        source = "P2P"

        if (
            candidate.get("doctype") ==
            C2C_DOCTYPE
        ):
            source = "C2C"

        return {
            "name": doc.name,

            "doctype": candidate.get(
                "doctype"
            ),

            "source": source,

            "display_status":
                get_display_status(doc),

            "approval_display_status":
                clean(
                    doc.get(
                        "approval_display_status"
                    )
                ),

            "approval_stage":
                clean(
                    doc.get(
                        "approval_stage"
                    )
                ),

            "conversion_status":
                clean(
                    doc.get(
                        "conversion_status"
                    )
                ),

            "final_approval_status":
                clean(
                    doc.get(
                        "final_approval_status"
                    )
                ),

            "automation_status":
                clean(
                    doc.get(
                        "automation_status"
                    )
                ),

            "package_conversion_applied":
                (
                    doc.get(
                        "package_conversion_applied"
                    ) or 0
                ),

            "package_transfer_applied":
                (
                    doc.get(
                        "package_transfer_applied"
                    ) or 0
                ),

            "creation":
                clean(
                    doc.get("creation")
                ),

            "modified":
                clean(
                    doc.get("modified")
                ),

            "finished":
                request_is_finished(doc)
        }


    def request_order_value(request_data):
        creation = clean(
            request_data.get("creation")
        )

        modified = clean(
            request_data.get("modified")
        )

        name = clean(
            request_data.get("name")
        )

        # Creation comes first intentionally.
        # An old request modified later must not become newer
        # than a genuinely later-created request.
        return (
            creation +
            "|" +
            modified +
            "|" +
            name
        )


    # ============================================================
    # FIND ALL EXACTLY CONNECTED REQUESTS
    # ============================================================

    if therapy_plan:
        candidates = []

        # --------------------------------------------------------
        # 1. Child-table links shared by P2P and C2C
        # --------------------------------------------------------

        child_link_fields = [
            "seserp_entry",
            "ses_erp_entry",
            "therapy_plan",
            "source_therapy_plan",
            "therapy_plan_no"
        ]

        for parent_doctype in [
            P2P_DOCTYPE,
            C2C_DOCTYPE
        ]:
            for child_field in child_link_fields:
                if not doctype_has_field(
                    CHILD_DOCTYPE,
                    child_field
                ):
                    continue

                rows = frappe.get_all(
                    CHILD_DOCTYPE,

                    filters={
                        "parenttype":
                            parent_doctype,

                        "parentfield":
                            "complete_package_details",

                        child_field:
                            therapy_plan
                    },

                    fields=[
                        "parent",
                        "modified"
                    ],

                    limit_page_length=5000
                )

                for row in rows:
                    add_candidate(
                        candidates,
                        parent_doctype,
                        row.get("parent"),
                        row.get("modified")
                    )

        # --------------------------------------------------------
        # 2. Exact top-level P2P links
        # --------------------------------------------------------

        p2p_direct_fields = [
            "source_therapy_plan",
            "updated_therapy_plan"
        ]

        for fieldname in p2p_direct_fields:
            if not doctype_has_field(
                P2P_DOCTYPE,
                fieldname
            ):
                continue

            rows = frappe.get_all(
                P2P_DOCTYPE,

                filters={
                    fieldname:
                        therapy_plan
                },

                fields=[
                    "name",
                    "modified"
                ],

                limit_page_length=5000
            )

            for row in rows:
                add_candidate(
                    candidates,
                    P2P_DOCTYPE,
                    row.get("name"),
                    row.get("modified")
                )

        # --------------------------------------------------------
        # 3. Older P2P records containing multiple source plans
        # --------------------------------------------------------

        if doctype_has_field(
            P2P_DOCTYPE,
            "source_therapy_plans_text"
        ):
            rows = frappe.get_all(
                P2P_DOCTYPE,

                filters={
                    "source_therapy_plans_text": [
                        "like",
                        "%" + therapy_plan + "%"
                    ]
                },

                fields=[
                    "name",
                    "modified",
                    "source_therapy_plans_text"
                ],

                limit_page_length=5000
            )

            for row in rows:
                if text_contains_exact_plan(
                    row.get(
                        "source_therapy_plans_text"
                    ),
                    therapy_plan
                ):
                    add_candidate(
                        candidates,
                        P2P_DOCTYPE,
                        row.get("name"),
                        row.get("modified")
                    )

        # --------------------------------------------------------
        # 4. Exact top-level C2C links
        # --------------------------------------------------------

        c2c_direct_fields = [
            "source_therapy_plan",
            "transferor_therapy_plan",
            "updated_transferor_therapy_plan",
            "created_transferee_therapy_plan"
        ]

        for fieldname in c2c_direct_fields:
            if not doctype_has_field(
                C2C_DOCTYPE,
                fieldname
            ):
                continue

            rows = frappe.get_all(
                C2C_DOCTYPE,

                filters={
                    fieldname:
                        therapy_plan
                },

                fields=[
                    "name",
                    "modified"
                ],

                limit_page_length=5000
            )

            for row in rows:
                add_candidate(
                    candidates,
                    C2C_DOCTYPE,
                    row.get("name"),
                    row.get("modified")
                )

        # --------------------------------------------------------
        # 5. Optional C2C text field containing created plans
        # --------------------------------------------------------

        if doctype_has_field(
            C2C_DOCTYPE,
            "created_receiving_therapy_plans"
        ):
            rows = frappe.get_all(
                C2C_DOCTYPE,

                filters={
                    "created_receiving_therapy_plans": [
                        "like",
                        "%" + therapy_plan + "%"
                    ]
                },

                fields=[
                    "name",
                    "modified",
                    "created_receiving_therapy_plans"
                ],

                limit_page_length=5000
            )

            for row in rows:
                if text_contains_exact_plan(
                    row.get(
                        "created_receiving_therapy_plans"
                    ),
                    therapy_plan
                ):
                    add_candidate(
                        candidates,
                        C2C_DOCTYPE,
                        row.get("name"),
                        row.get("modified")
                    )

        # ========================================================
        # LOAD EVERY CONNECTED REQUEST
        #
        # Do not remove completed requests before selecting the
        # latest request.
        # ========================================================

        all_requests = []

        for candidate in candidates:
            request_data = build_request_data(
                candidate
            )

            all_requests.append(
                request_data
            )

        result["matched_request_count"] = len(
            all_requests
        )

        # ========================================================
        # SELECT THE NEWEST CONNECTED REQUEST FIRST
        #
        # Example:
        #
        # Older request:
        # Indhiraa-P2P-2026-01135
        # Pending Audit Team approval
        #
        # Newer request:
        # Indhiraa-P2P-2026-01136
        # Process Completed
        #
        # Result:
        # The newer completed request supersedes the older pending
        # request, so the Therapy Plan must not be blocked.
        # ========================================================

        latest_request = None

        for request_data in all_requests:
            if not latest_request:
                latest_request = request_data
                continue

            current_order = request_order_value(
                request_data
            )

            latest_order = request_order_value(
                latest_request
            )

            if current_order > latest_order:
                latest_request = request_data

        # ========================================================
        # FINAL BLOCK DECISION
        # ========================================================

        if latest_request:
            result["latest_connected_request"] = {
                "name":
                    latest_request.get("name"),

                "doctype":
                    latest_request.get("doctype"),

                "source":
                    latest_request.get("source"),

                "display_status":
                    latest_request.get(
                        "display_status"
                    ),

                "finished":
                    latest_request.get(
                        "finished"
                    ),

                "creation":
                    latest_request.get(
                        "creation"
                    ),

                "modified":
                    latest_request.get(
                        "modified"
                    )
            }

            # Only the newest connected request decides the block.
            if not latest_request.get("finished"):
                result["blocked"] = True

                result["request"] = (
                    latest_request
                )

                result["source"] = (
                    latest_request.get("source")
                )

            else:
                result["blocked"] = False
                result["request"] = None
                result["source"] = ""


    frappe.response["message"] = result
