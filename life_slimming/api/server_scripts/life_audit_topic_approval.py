"""Branch Audit Sending Mails Testing

Original API: life_audit_topic_approval
Source modified: 2026-07-27 13:27:02.182569
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
    # ================================================================
    # SERVER SCRIPT SETTINGS
    # ================================================================
    # Script Type : API
    # API Method  : life_audit_topic_approval
    # Enabled     : Checked
    # Allow Guest : Unchecked
    #
    # This ONE script handles:
    # 1. Audit team sends a proposed topic
    # 2. Email goes to COO and Kavya
    # 3. COO sees pending requests in the Audit Command Center
    # 4. COO approves
    # 5. Approved topic is added automatically
    # 6. Branch users can securely read only their sent reports
    # 7. Approvers can remove topics previously added through approval
    # 8. Management can enable or disable individual audit topics
    #
    # No custom Branch Audit Topic Request DocType is required.
    # No JSON helper is used.
    # ================================================================

    PRIMARY_APPROVER_EMAIL = "bhuvan@lifescc.com"

    APPROVER_EMAILS = [
        "bhuvan@lifescc.com",
        "lokakavyareddy3@gmail.com",
        "Administrator"
    ]

    NOTIFICATION_EMAILS = [
        "bhuvan@lifescc.com",
        "lokakavyareddy3@gmail.com"
    ]

    REQUEST_MARKER = "LIFE_AUDIT_TOPIC_REQUEST_V5"
    PROCESSED_MARKER = "LIFE_AUDIT_TOPIC_PROCESSED_V5"
    REMOVED_MARKER = "LIFE_AUDIT_TOPIC_REMOVED_V5"
    TOPIC_TOGGLE_FIELD = "custom_is_enabled"

    DEPRECATED_TOPIC_KEY = (
        "media & lead entries and forms are updated daily "
        "by foe/acm in erp"
    )

    action = (
        frappe.form_dict.get("action")
        or ""
    ).strip().lower()


    # ------------------------------------------------
    # Common login validation
    # ------------------------------------------------
    if frappe.session.user == "Guest":
        frappe.throw(
            "Please log in before using audit topic approval."
        )


    # ================================================================
    # ACTION: SUBMIT
    # ================================================================
    if action == "submit":
        section = (
            frappe.form_dict.get("section")
            or ""
        ).strip()

        proposed_topic = (
            frappe.form_dict.get("proposed_topic")
            or ""
        ).strip()

        justification = (
            frappe.form_dict.get("justification")
            or ""
        ).strip()

        evidence_attachment = (
            frappe.form_dict.get("evidence_attachment")
            or ""
        ).strip()

        points = frappe.utils.flt(
            frappe.form_dict.get("points")
        )

        is_critical_item = frappe.utils.cint(
            frappe.form_dict.get("is_critical_item")
        )

        if not section:
            frappe.throw(
                "Select an audit section."
            )

        if not frappe.db.exists(
            "Branch Audit Section",
            section
        ):
            frappe.throw(
                "The selected audit section does not exist."
            )

        if not proposed_topic:
            frappe.throw(
                "Enter the proposed audit topic."
            )

        if points <= 0:
            frappe.throw(
                "Raw Points must be greater than zero."
            )

        if not justification:
            frappe.throw(
                "Enter the reason for adding this topic."
            )

        approver_enabled = frappe.db.get_value(
            "User",
            PRIMARY_APPROVER_EMAIL,
            "enabled"
        )

        if approver_enabled is None:
            frappe.throw(
                "The COO User bhuvan@lifescc.com does not exist."
            )

        if frappe.utils.cint(
            approver_enabled
        ) != 1:
            frappe.throw(
                "The COO User bhuvan@lifescc.com is disabled."
            )

        section_label = frappe.db.get_value(
            "Branch Audit Section",
            section,
            "section_name"
        ) or section

        # Keep marker data on one line per value.
        marker_section = section.replace(
            "\n",
            " "
        ).replace(
            "\r",
            " "
        )

        marker_section_label = section_label.replace(
            "\n",
            " "
        ).replace(
            "\r",
            " "
        )

        marker_topic = proposed_topic.replace(
            "\n",
            " "
        ).replace(
            "\r",
            " "
        )

        marker_justification = justification.replace(
            "\n",
            " "
        ).replace(
            "\r",
            " "
        )

        marker_evidence = evidence_attachment.replace(
            "\n",
            ""
        ).replace(
            "\r",
            ""
        )

        requested_on = frappe.utils.now()

        hidden_request_data = (
            "\n"
            + REQUEST_MARKER
            + "\nSECTION="
            + marker_section
            + "\nSECTION_LABEL="
            + marker_section_label
            + "\nTOPIC="
            + marker_topic
            + "\nPOINTS="
            + str(points)
            + "\nCRITICAL="
            + (
                "1"
                if is_critical_item
                else "0"
            )
            + "\nJUSTIFICATION="
            + marker_justification
            + "\nEVIDENCE="
            + marker_evidence
            + "\nREQUESTED_BY="
            + frappe.session.user
            + "\nREQUESTED_ON="
            + requested_on
            + "\nEND_"
            + REQUEST_MARKER
        )

        # Basic HTML escaping using normal string methods only.
        safe_user = frappe.session.user.replace(
            "&",
            "&amp;"
        ).replace(
            "<",
            "&lt;"
        ).replace(
            ">",
            "&gt;"
        )

        safe_section_label = section_label.replace(
            "&",
            "&amp;"
        ).replace(
            "<",
            "&lt;"
        ).replace(
            ">",
            "&gt;"
        )

        safe_topic = proposed_topic.replace(
            "&",
            "&amp;"
        ).replace(
            "<",
            "&lt;"
        ).replace(
            ">",
            "&gt;"
        )

        safe_justification = justification.replace(
            "&",
            "&amp;"
        ).replace(
            "<",
            "&lt;"
        ).replace(
            ">",
            "&gt;"
        )

        evidence_html = ""

        if evidence_attachment:
            safe_evidence = evidence_attachment.replace(
                "&",
                "&amp;"
            ).replace(
                '"',
                "&quot;"
            ).replace(
                "<",
                "&lt;"
            ).replace(
                ">",
                "&gt;"
            )

            evidence_html = (
                '<p><b>Supporting Evidence:</b> '
                '<a href="'
                + safe_evidence
                + '" target="_blank">'
                'Open attachment</a></p>'
            )

        description = (
            '<div>'
            '<h3>Audit Topic Approval Request</h3>'
            '<p><b>Requested By:</b> '
            + safe_user
            + '</p>'
            '<p><b>Audit Section:</b> '
            + safe_section_label
            + '</p>'
            '<p><b>Proposed Topic:</b> '
            + safe_topic
            + '</p>'
            '<p><b>Raw Points:</b> '
            + str(points)
            + '</p>'
            '<p><b>Critical Check Point:</b> '
            + (
                "Yes"
                if is_critical_item
                else "No"
            )
            + '</p>'
            '<p><b>Justification:</b><br>'
            + safe_justification
            + '</p>'
            + evidence_html
            + '</div>'
            + hidden_request_data
        )

        todo = frappe.get_doc(
            {
                "doctype": "ToDo",
                "status": "Open",
                "priority": "Medium",
                "date": frappe.utils.today(),
                "allocated_to": PRIMARY_APPROVER_EMAIL,
                "assigned_by": frappe.session.user,
                "reference_type": "Branch Audit Section",
                "reference_name": section,
                "description": description
            }
        )

        todo.insert(
            ignore_permissions=True
        )

        requested_approval_page_url = (
            frappe.form_dict.get(
                "approval_page_url"
            )
            or ""
        ).strip()

        approval_page_url = (
            requested_approval_page_url
            if requested_approval_page_url.startswith(
                "https://portal.lifescc.com/"
            )
            else (
                "https://portal.lifescc.com/"
                "?topic_approval=1"
            )
        )

        approval_page_url = (
            approval_page_url
            + (
                "&request="
                if "?" in approval_page_url
                else "?request="
            )
            + todo.name
        )

        email_message = (
            '<p>A new audit topic is waiting '
            'for COO approval.</p>'
            '<p><b>Request:</b> '
            + todo.name
            + '</p>'
            '<p><b>Requested By:</b> '
            + safe_user
            + '</p>'
            '<p><b>Audit Section:</b> '
            + safe_section_label
            + '</p>'
            '<p><b>Proposed Topic:</b> '
            + safe_topic
            + '</p>'
            '<p><b>Raw Points:</b> '
            + str(points)
            + '</p>'
            '<p><b>Critical:</b> '
            + (
                "Yes"
                if is_critical_item
                else "No"
            )
            + '</p>'
            '<p><b>Justification:</b><br>'
            + safe_justification
            + '</p>'
            + evidence_html
            + '<p style="margin-top:18px">'
            '<a href="'
            + approval_page_url
            + '" style="display:inline-block;'
            'padding:10px 16px;'
            'background:#1B5E20;'
            'color:#ffffff;'
            'text-decoration:none;'
            'border-radius:6px">'
            'Open COO Topic Approvals'
            '</a>'
            '</p>'
        )

        frappe.sendmail(
            recipients=NOTIFICATION_EMAILS,
            subject=(
                "COO Approval Required — Audit Topic — "
                + todo.name
            ),
            message=email_message,
            reference_doctype="ToDo",
            reference_name=todo.name,
            now=True
        )

        frappe.response["message"] = {
            "ok": True,
            "request_name": todo.name,
            "email_sent_to": NOTIFICATION_EMAILS,
            "message": (
                "Topic request sent to COO for approval."
            )
        }


    # ================================================================
    # ACTION: LIST
    # ================================================================
    elif action == "list":
        if frappe.session.user not in APPROVER_EMAILS:
            frappe.throw(
                "Only an authorised approver can view pending audit topic requests."
            )

        todo_rows = frappe.db.get_all(
            "ToDo",
            filters={
                "allocated_to": PRIMARY_APPROVER_EMAIL,
                "status": "Open"
            },
            fields=[
                "name",
                "description",
                "creation",
                "assigned_by",
                "reference_name"
            ],
            order_by="creation desc",
            limit_page_length=0
        )

        requests = []

        for todo_row in todo_rows:
            description = (
                todo_row.description
                or ""
            )

            if REQUEST_MARKER not in description:
                continue

            if PROCESSED_MARKER in description:
                continue

            section = ""
            section_label = ""
            proposed_topic = ""
            points = 0.0
            is_critical_item = 0
            justification = ""
            evidence_attachment = ""
            requested_by = (
                todo_row.assigned_by
                or ""
            )
            requested_on = (
                todo_row.creation
                or ""
            )

            for request_line in description.splitlines():
                if request_line.startswith(
                    "SECTION="
                ):
                    section = request_line[
                        len("SECTION="):
                    ]

                elif request_line.startswith(
                    "SECTION_LABEL="
                ):
                    section_label = request_line[
                        len("SECTION_LABEL="):
                    ]

                elif request_line.startswith(
                    "TOPIC="
                ):
                    proposed_topic = request_line[
                        len("TOPIC="):
                    ]

                elif request_line.startswith(
                    "POINTS="
                ):
                    points = frappe.utils.flt(
                        request_line[
                            len("POINTS="):
                        ]
                    )

                elif request_line.startswith(
                    "CRITICAL="
                ):
                    is_critical_item = frappe.utils.cint(
                        request_line[
                            len("CRITICAL="):
                        ]
                    )

                elif request_line.startswith(
                    "JUSTIFICATION="
                ):
                    justification = request_line[
                        len("JUSTIFICATION="):
                    ]

                elif request_line.startswith(
                    "EVIDENCE="
                ):
                    evidence_attachment = request_line[
                        len("EVIDENCE="):
                    ]

                elif request_line.startswith(
                    "REQUESTED_BY="
                ):
                    requested_by = request_line[
                        len("REQUESTED_BY="):
                    ]

                elif request_line.startswith(
                    "REQUESTED_ON="
                ):
                    requested_on = request_line[
                        len("REQUESTED_ON="):
                    ]

            requests.append(
                {
                    "name": todo_row.name,
                    "requested_by": requested_by,
                    "requested_on": requested_on,
                    "section": (
                        section
                        or todo_row.reference_name
                        or ""
                    ),
                    "section_label": (
                        section_label
                        or section
                        or todo_row.reference_name
                        or ""
                    ),
                    "proposed_topic": proposed_topic,
                    "points": points,
                    "is_critical_item": is_critical_item,
                    "justification": justification,
                    "evidence_attachment": evidence_attachment
                }
            )

        frappe.response["message"] = {
            "ok": True,
            "requests": requests
        }


    # ================================================================
    # ACTION: APPROVE
    # ================================================================
    elif action == "approve":
        if frappe.session.user not in APPROVER_EMAILS:
            frappe.throw(
                "Only an authorised approver can approve audit topic requests."
            )

        request_name = (
            frappe.form_dict.get("request_name")
            or ""
        ).strip()

        if not request_name:
            frappe.throw(
                "Audit topic request name is required."
            )

        if not frappe.db.exists(
            "ToDo",
            request_name
        ):
            frappe.throw(
                "Audit topic request does not exist."
            )

        todo = frappe.get_doc(
            "ToDo",
            request_name
        )

        if todo.status != "Open":
            frappe.throw(
                "This request has already been processed."
            )

        description = (
            todo.description
            or ""
        )

        if REQUEST_MARKER not in description:
            frappe.throw(
                "This is not a LIFE audit topic request."
            )

        section = ""
        section_label = ""
        proposed_topic = ""
        points = 0.0
        is_critical_item = 0
        requested_by = (
            todo.assigned_by
            or ""
        )

        for request_line in description.splitlines():
            if request_line.startswith(
                "SECTION="
            ):
                section = request_line[
                    len("SECTION="):
                ]

            elif request_line.startswith(
                "SECTION_LABEL="
            ):
                section_label = request_line[
                    len("SECTION_LABEL="):
                ]

            elif request_line.startswith(
                "TOPIC="
            ):
                proposed_topic = request_line[
                    len("TOPIC="):
                ]

            elif request_line.startswith(
                "POINTS="
            ):
                points = frappe.utils.flt(
                    request_line[
                        len("POINTS="):
                    ]
                )

            elif request_line.startswith(
                "CRITICAL="
            ):
                is_critical_item = frappe.utils.cint(
                    request_line[
                        len("CRITICAL="):
                    ]
                )

            elif request_line.startswith(
                "REQUESTED_BY="
            ):
                requested_by = request_line[
                    len("REQUESTED_BY="):
                ]

        if not section:
            frappe.throw(
                "Audit Section is missing from this request."
            )

        if not proposed_topic:
            frappe.throw(
                "Proposed audit topic is missing."
            )

        if not frappe.db.exists(
            "Branch Audit Section",
            section
        ):
            frappe.throw(
                "The selected audit section no longer exists."
            )

        parentfield = frappe.db.get_value(
            "Branch Audit Item",
            {
                "parent": section,
                "parenttype": "Branch Audit Section"
            },
            "parentfield"
        )

        if not parentfield:
            parentfield = frappe.db.get_value(
                "DocField",
                {
                    "parent": "Branch Audit Section",
                    "fieldtype": "Table",
                    "options": "Branch Audit Item"
                },
                "fieldname"
            )

        if not parentfield:
            frappe.throw(
                "Branch Audit Item table field was not found."
            )

        existing_items = frappe.db.get_all(
            "Branch Audit Item",
            filters={
                "parent": section,
                "parenttype": "Branch Audit Section"
            },
            fields=[
                "name",
                "question",
                "points",
                TOPIC_TOGGLE_FIELD
            ],
            order_by="idx asc",
            limit_page_length=0
        )

        proposed_key = " ".join(
            proposed_topic.lower().split()
        )

        duplicate_found = False
        calculated_raw_max = 0.0

        deprecated_key = " ".join(
            DEPRECATED_TOPIC_KEY.lower().split()
        )

        for existing_item in existing_items:
            existing_enabled_value = existing_item.get(
                TOPIC_TOGGLE_FIELD
            )

            existing_is_enabled = (
                0
                if (
                    existing_enabled_value == 0
                    or existing_enabled_value == "0"
                )
                else 1
            )

            existing_key = " ".join(
                (
                    existing_item.question
                    or ""
                ).lower().split()
            )

            if existing_key == proposed_key:
                duplicate_found = True

            if (
                existing_key != deprecated_key
                and existing_is_enabled == 1
            ):
                calculated_raw_max += frappe.utils.flt(
                    existing_item.points
                )

        topic_added = False

        if not duplicate_found:
            section_doc = frappe.get_doc(
                "Branch Audit Section",
                section
            )

            section_doc.append(
                parentfield,
                {
                    "question": proposed_topic,
                    "points": points,
                    "is_critical_item": (
                        1
                        if is_critical_item
                        else 0
                    ),
                    TOPIC_TOGGLE_FIELD: 1
                }
            )

            section_doc.raw_max = (
                calculated_raw_max
                + points
            )

            section_doc.save(
                ignore_permissions=True
            )

            topic_added = True

        processed_description = (
            description
            + "\n"
            + PROCESSED_MARKER
            + "=APPROVED"
            + "\nAPPROVED_BY="
            + frappe.session.user
            + "\nAPPROVED_ON="
            + frappe.utils.now()
            + "\nTOPIC_ADDED="
            + (
                "1"
                if topic_added
                else "0"
            )
        )

        frappe.db.set_value(
            "ToDo",
            todo.name,
            {
                "status": "Closed",
                "description": processed_description
            },
            update_modified=True
        )

        if requested_by:
            safe_request_topic = proposed_topic.replace(
                "&",
                "&amp;"
            ).replace(
                "<",
                "&lt;"
            ).replace(
                ">",
                "&gt;"
            )

            safe_request_section = (
                section_label
                or section
            ).replace(
                "&",
                "&amp;"
            ).replace(
                "<",
                "&lt;"
            ).replace(
                ">",
                "&gt;"
            )

            frappe.sendmail(
                recipients=[
                    requested_by
                ],
                subject=(
                    "Audit Topic Approved — "
                    + todo.name
                ),
                message=(
                    '<p>Your audit topic was approved by COO.</p>'
                    '<p><b>Section:</b> '
                    + safe_request_section
                    + '</p>'
                    '<p><b>Topic:</b> '
                    + safe_request_topic
                    + '</p>'
                    '<p>'
                    + (
                        "The topic was added automatically "
                        "to the live audit checklist."
                        if topic_added
                        else
                        "The same topic already existed, "
                        "so a duplicate was not created."
                    )
                    + '</p>'
                ),
                reference_doctype="ToDo",
                reference_name=todo.name,
                now=True
            )

        frappe.response["message"] = {
            "ok": True,
            "request_name": todo.name,
            "topic_added": (
                1
                if topic_added
                else 0
            ),
            "message": (
                "Topic approved and added automatically."
                if topic_added
                else
                "Topic approved. The topic already existed."
            )
        }


    # ================================================================
    # ACTION: REJECT
    # ================================================================
    elif action == "reject":
        if frappe.session.user not in APPROVER_EMAILS:
            frappe.throw(
                "Only an authorised approver can reject audit topic requests."
            )

        request_name = (
            frappe.form_dict.get("request_name")
            or ""
        ).strip()

        approval_remarks = (
            frappe.form_dict.get("approval_remarks")
            or ""
        ).strip()

        if not request_name:
            frappe.throw(
                "Audit topic request name is required."
            )

        if not approval_remarks:
            frappe.throw(
                "Enter rejection remarks."
            )

        if not frappe.db.exists(
            "ToDo",
            request_name
        ):
            frappe.throw(
                "Audit topic request does not exist."
            )

        todo = frappe.get_doc(
            "ToDo",
            request_name
        )

        if todo.status != "Open":
            frappe.throw(
                "This request has already been processed."
            )

        description = (
            todo.description
            or ""
        )

        if REQUEST_MARKER not in description:
            frappe.throw(
                "This is not a LIFE audit topic request."
            )

        proposed_topic = ""
        requested_by = (
            todo.assigned_by
            or ""
        )

        for request_line in description.splitlines():
            if request_line.startswith(
                "TOPIC="
            ):
                proposed_topic = request_line[
                    len("TOPIC="):
                ]

            elif request_line.startswith(
                "REQUESTED_BY="
            ):
                requested_by = request_line[
                    len("REQUESTED_BY="):
                ]

        processed_description = (
            description
            + '<p><b>COO Rejection Remarks:</b><br>'
            + approval_remarks.replace(
                "&",
                "&amp;"
            ).replace(
                "<",
                "&lt;"
            ).replace(
                ">",
                "&gt;"
            )
            + '</p>'
            + "\n"
            + PROCESSED_MARKER
            + "=REJECTED"
            + "\nREJECTED_BY="
            + frappe.session.user
            + "\nREJECTED_ON="
            + frappe.utils.now()
        )

        frappe.db.set_value(
            "ToDo",
            todo.name,
            {
                "status": "Cancelled",
                "description": processed_description
            },
            update_modified=True
        )

        if requested_by:
            safe_request_topic = proposed_topic.replace(
                "&",
                "&amp;"
            ).replace(
                "<",
                "&lt;"
            ).replace(
                ">",
                "&gt;"
            )

            safe_rejection_remarks = approval_remarks.replace(
                "&",
                "&amp;"
            ).replace(
                "<",
                "&lt;"
            ).replace(
                ">",
                "&gt;"
            )

            frappe.sendmail(
                recipients=[
                    requested_by
                ],
                subject=(
                    "Audit Topic Rejected — "
                    + todo.name
                ),
                message=(
                    '<p>Your audit topic request '
                    'was rejected by COO.</p>'
                    '<p><b>Topic:</b> '
                    + safe_request_topic
                    + '</p>'
                    '<p><b>Remarks:</b><br>'
                    + safe_rejection_remarks
                    + '</p>'
                ),
                reference_doctype="ToDo",
                reference_name=todo.name,
                now=True
            )

        frappe.response["message"] = {
            "ok": True,
            "request_name": todo.name,
            "message": (
                "Topic request rejected."
            )
        }


    # ================================================================
    # ACTION: LIST APPROVED ADDED TOPICS
    # ================================================================
    elif action == "list_approved_topics":
        if frappe.session.user not in APPROVER_EMAILS:
            frappe.throw(
                "Only an authorised approver can view approved audit topics."
            )

        todo_rows = frappe.db.get_all(
            "ToDo",
            filters={
                "allocated_to": PRIMARY_APPROVER_EMAIL,
                "status": "Closed"
            },
            fields=[
                "name",
                "description",
                "creation",
                "assigned_by",
                "reference_name"
            ],
            order_by="creation desc",
            limit_page_length=0
        )

        topics = []

        for todo_row in todo_rows:
            description = (
                todo_row.description
                or ""
            )

            approved_marker = (
                PROCESSED_MARKER
                + "=APPROVED"
            )

            if REQUEST_MARKER not in description:
                continue

            if approved_marker not in description:
                continue

            if REMOVED_MARKER in description:
                continue

            section = ""
            section_label = ""
            proposed_topic = ""
            points = 0.0
            is_critical_item = 0
            approved_by = ""
            approved_on = ""
            topic_added_marker = ""

            for request_line in description.splitlines():
                if request_line.startswith(
                    "SECTION="
                ):
                    section = request_line[
                        len("SECTION="):
                    ]

                elif request_line.startswith(
                    "SECTION_LABEL="
                ):
                    section_label = request_line[
                        len("SECTION_LABEL="):
                    ]

                elif request_line.startswith(
                    "TOPIC="
                ):
                    proposed_topic = request_line[
                        len("TOPIC="):
                    ]

                elif request_line.startswith(
                    "POINTS="
                ):
                    points = frappe.utils.flt(
                        request_line[
                            len("POINTS="):
                        ]
                    )

                elif request_line.startswith(
                    "CRITICAL="
                ):
                    is_critical_item = frappe.utils.cint(
                        request_line[
                            len("CRITICAL="):
                        ]
                    )

                elif request_line.startswith(
                    "APPROVED_BY="
                ):
                    approved_by = request_line[
                        len("APPROVED_BY="):
                    ]

                elif request_line.startswith(
                    "APPROVED_ON="
                ):
                    approved_on = request_line[
                        len("APPROVED_ON="):
                    ]

                elif request_line.startswith(
                    "TOPIC_ADDED="
                ):
                    topic_added_marker = request_line[
                        len("TOPIC_ADDED="):
                    ]

            if not section or not proposed_topic:
                continue

            # Older approvals did not store TOPIC_ADDED. They are still shown
            # only when the exact approved topic currently exists in the section.
            # New duplicate approvals store TOPIC_ADDED=0 and are never removable.
            if topic_added_marker == "0":
                continue

            proposed_key = " ".join(
                proposed_topic.lower().split()
            )

            existing_items = frappe.db.get_all(
                "Branch Audit Item",
                filters={
                    "parent": section,
                    "parenttype": "Branch Audit Section"
                },
                fields=[
                    "name",
                    "question"
                ],
                order_by="idx asc",
                limit_page_length=0
            )

            topic_exists = False

            for existing_item in existing_items:
                existing_key = " ".join(
                    (
                        existing_item.question
                        or ""
                    ).lower().split()
                )

                if existing_key == proposed_key:
                    topic_exists = True
                    break

            if not topic_exists:
                continue

            topics.append(
                {
                    "name": todo_row.name,
                    "section": section,
                    "section_label": (
                        section_label
                        or section
                    ),
                    "proposed_topic": proposed_topic,
                    "points": points,
                    "is_critical_item": is_critical_item,
                    "approved_by": approved_by,
                    "approved_on": (
                        approved_on
                        or todo_row.creation
                    )
                }
            )

        frappe.response["message"] = {
            "ok": True,
            "topics": topics
        }


    # ================================================================
    # ACTION: REMOVE APPROVED TOPIC
    # ================================================================
    elif action == "remove_approved_topic":
        if frappe.session.user not in APPROVER_EMAILS:
            frappe.throw(
                "Only an authorised approver can remove an approved audit topic."
            )

        request_name = (
            frappe.form_dict.get("request_name")
            or ""
        ).strip()

        if not request_name:
            frappe.throw(
                "Audit topic request name is required."
            )

        if not frappe.db.exists(
            "ToDo",
            request_name
        ):
            frappe.throw(
                "Audit topic request does not exist."
            )

        todo = frappe.get_doc(
            "ToDo",
            request_name
        )

        description = (
            todo.description
            or ""
        )

        approved_marker = (
            PROCESSED_MARKER
            + "=APPROVED"
        )

        if REQUEST_MARKER not in description:
            frappe.throw(
                "This is not a LIFE audit topic request."
            )

        if approved_marker not in description:
            frappe.throw(
                "Only an approved topic can be removed."
            )

        if REMOVED_MARKER in description:
            frappe.throw(
                "This topic has already been removed."
            )

        section = ""
        section_label = ""
        proposed_topic = ""
        requested_by = (
            todo.assigned_by
            or ""
        )
        topic_added_marker = ""

        for request_line in description.splitlines():
            if request_line.startswith(
                "SECTION="
            ):
                section = request_line[
                    len("SECTION="):
                ]

            elif request_line.startswith(
                "SECTION_LABEL="
            ):
                section_label = request_line[
                    len("SECTION_LABEL="):
                ]

            elif request_line.startswith(
                "TOPIC="
            ):
                proposed_topic = request_line[
                    len("TOPIC="):
                ]

            elif request_line.startswith(
                "REQUESTED_BY="
            ):
                requested_by = request_line[
                    len("REQUESTED_BY="):
                ]

            elif request_line.startswith(
                "TOPIC_ADDED="
            ):
                topic_added_marker = request_line[
                    len("TOPIC_ADDED="):
                ]

        if topic_added_marker == "0":
            frappe.throw(
                "This approval did not add a new checklist row, so nothing can be removed."
            )

        if not section:
            frappe.throw(
                "Audit Section is missing from this request."
            )

        if not proposed_topic:
            frappe.throw(
                "Approved audit topic is missing."
            )

        if not frappe.db.exists(
            "Branch Audit Section",
            section
        ):
            frappe.throw(
                "The selected audit section no longer exists."
            )

        parentfield = frappe.db.get_value(
            "Branch Audit Item",
            {
                "parent": section,
                "parenttype": "Branch Audit Section"
            },
            "parentfield"
        )

        if not parentfield:
            parentfield = frappe.db.get_value(
                "DocField",
                {
                    "parent": "Branch Audit Section",
                    "fieldtype": "Table",
                    "options": "Branch Audit Item"
                },
                "fieldname"
            )

        if not parentfield:
            frappe.throw(
                "Branch Audit Item table field was not found."
            )

        section_doc = frappe.get_doc(
            "Branch Audit Section",
            section
        )

        proposed_key = " ".join(
            proposed_topic.lower().split()
        )

        target_row = None

        for item_row in (
            section_doc.get(parentfield)
            or []
        ):
            item_key = " ".join(
                (
                    item_row.question
                    or ""
                ).lower().split()
            )

            if item_key == proposed_key:
                target_row = item_row
                break

        if not target_row:
            frappe.throw(
                "This approved topic is no longer present in the live checklist."
            )

        section_doc.remove(
            target_row
        )

        recalculated_raw_max = 0.0
        deprecated_key = " ".join(
            DEPRECATED_TOPIC_KEY.lower().split()
        )

        for remaining_row in (
            section_doc.get(parentfield)
            or []
        ):
            remaining_key = " ".join(
                (
                    remaining_row.question
                    or ""
                ).lower().split()
            )

            if remaining_key == deprecated_key:
                continue

            remaining_enabled_value = remaining_row.get(
                TOPIC_TOGGLE_FIELD
            )

            remaining_is_enabled = (
                0
                if (
                    remaining_enabled_value == 0
                    or remaining_enabled_value == "0"
                )
                else 1
            )

            if remaining_is_enabled == 1:
                recalculated_raw_max += frappe.utils.flt(
                    remaining_row.points
                )

        section_doc.raw_max = (
            recalculated_raw_max
        )

        section_doc.save(
            ignore_permissions=True
        )

        processed_description = (
            description
            + "\n"
            + REMOVED_MARKER
            + "=1"
            + "\nREMOVED_BY="
            + frappe.session.user
            + "\nREMOVED_ON="
            + frappe.utils.now()
        )

        frappe.db.set_value(
            "ToDo",
            todo.name,
            "description",
            processed_description,
            update_modified=True
        )

        if requested_by:
            safe_topic = proposed_topic.replace(
                "&",
                "&amp;"
            ).replace(
                "<",
                "&lt;"
            ).replace(
                ">",
                "&gt;"
            )

            safe_section = (
                section_label
                or section
            ).replace(
                "&",
                "&amp;"
            ).replace(
                "<",
                "&lt;"
            ).replace(
                ">",
                "&gt;"
            )

            frappe.sendmail(
                recipients=[
                    requested_by
                ],
                subject=(
                    "Approved Audit Topic Removed — "
                    + todo.name
                ),
                message=(
                    '<p>An approved audit topic was removed '
                    'from the live checklist.</p>'
                    '<p><b>Section:</b> '
                    + safe_section
                    + '</p>'
                    '<p><b>Topic:</b> '
                    + safe_topic
                    + '</p>'
                    '<p><b>Removed By:</b> '
                    + frappe.session.user
                    + '</p>'
                ),
                reference_doctype="ToDo",
                reference_name=todo.name,
                now=True
            )

        frappe.response["message"] = {
            "ok": True,
            "request_name": todo.name,
            "section": section,
            "topic": proposed_topic,
            "raw_max": recalculated_raw_max,
            "message": (
                "Topic removed and section raw maximum recalculated."
            )
        }


    # ================================================================
    # ACTION: ENABLE / DISABLE ONE AUDIT TOPIC
    # ================================================================
    elif action == "toggle_audit_topic":
        current_user = (
            frappe.session.user
            or ""
        )

        can_manage_topics = (
            current_user in APPROVER_EMAILS
            or frappe.db.exists(
                "Has Role",
                {
                    "parent": current_user,
                    "parenttype": "User",
                    "role": "System Manager"
                }
            )
            or frappe.db.exists(
                "Has Role",
                {
                    "parent": current_user,
                    "parenttype": "User",
                    "role": "Accounts Manager"
                }
            )
        )

        if not can_manage_topics:
            frappe.throw(
                "Only authorised management users can enable or disable audit topics."
            )

        toggle_field_exists = (
            frappe.db.exists(
                "Custom Field",
                {
                    "dt": "Branch Audit Item",
                    "fieldname": TOPIC_TOGGLE_FIELD
                }
            )
            or frappe.db.exists(
                "DocField",
                {
                    "parent": "Branch Audit Item",
                    "fieldname": TOPIC_TOGGLE_FIELD
                }
            )
        )

        if not toggle_field_exists:
            frappe.throw(
                "Create a Check field named custom_is_enabled in Branch Audit Item with default 1."
            )

        item_name = (
            frappe.form_dict.get("item_name")
            or ""
        ).strip()

        enabled = frappe.utils.cint(
            frappe.form_dict.get("enabled")
        )

        if enabled not in [
            0,
            1
        ]:
            frappe.throw(
                "Enabled must be 0 or 1."
            )

        if not item_name:
            frappe.throw(
                "Audit topic row name is required."
            )

        if not frappe.db.exists(
            "Branch Audit Item",
            item_name
        ):
            frappe.throw(
                "Audit topic row does not exist."
            )

        item_values = frappe.db.get_value(
            "Branch Audit Item",
            item_name,
            [
                "parent",
                "parenttype",
                "question",
                "points",
                TOPIC_TOGGLE_FIELD
            ]
        )

        if not item_values:
            frappe.throw(
                "Audit topic row could not be loaded."
            )

        section = (
            item_values[0]
            or ""
        )

        parenttype = (
            item_values[1]
            or ""
        )

        question = (
            item_values[2]
            or ""
        )

        if parenttype != "Branch Audit Section":
            frappe.throw(
                "This audit topic is not linked to a Branch Audit Section."
            )

        section_items = frappe.db.get_all(
            "Branch Audit Item",
            filters={
                "parent": section,
                "parenttype": "Branch Audit Section"
            },
            fields=[
                "name",
                "question",
                "points",
                TOPIC_TOGGLE_FIELD
            ],
            order_by="idx asc",
            limit_page_length=0
        )

        deprecated_key = " ".join(
            DEPRECATED_TOPIC_KEY.lower().split()
        )

        current_active_count = 0
        target_currently_enabled = 1

        for section_item in section_items:
            item_key = " ".join(
                (
                    section_item.question
                    or ""
                ).lower().split()
            )

            if item_key == deprecated_key:
                continue

            enabled_value = section_item.get(
                TOPIC_TOGGLE_FIELD
            )

            item_is_enabled = (
                0
                if (
                    enabled_value == 0
                    or enabled_value == "0"
                )
                else 1
            )

            if section_item.name == item_name:
                target_currently_enabled = item_is_enabled

            if item_is_enabled == 1:
                current_active_count += 1

        if (
            enabled == 0
            and target_currently_enabled == 1
            and current_active_count <= 1
        ):
            frappe.throw(
                "This is the last active topic in the section. Disable the complete section instead."
            )

        frappe.db.set_value(
            "Branch Audit Item",
            item_name,
            TOPIC_TOGGLE_FIELD,
            enabled,
            update_modified=True
        )

        recalculated_raw_max = 0.0
        active_count = 0
        total_count = 0

        for section_item in section_items:
            item_key = " ".join(
                (
                    section_item.question
                    or ""
                ).lower().split()
            )

            if item_key == deprecated_key:
                continue

            total_count += 1

            item_enabled_value = section_item.get(
                TOPIC_TOGGLE_FIELD
            )

            item_is_enabled = (
                0
                if (
                    item_enabled_value == 0
                    or item_enabled_value == "0"
                )
                else 1
            )

            if section_item.name == item_name:
                item_is_enabled = enabled

            if item_is_enabled == 1:
                active_count += 1
                recalculated_raw_max += frappe.utils.flt(
                    section_item.points
                )

        frappe.db.set_value(
            "Branch Audit Section",
            section,
            "raw_max",
            recalculated_raw_max,
            update_modified=True
        )

        frappe.response["message"] = {
            "ok": True,
            "item_name": item_name,
            "question": question,
            "enabled": enabled,
            "section": section,
            "active_count": active_count,
            "total_count": total_count,
            "raw_max": recalculated_raw_max,
            "message": (
                "Topic enabled and score recalculated."
                if enabled == 1
                else "Topic disabled and score recalculated."
            )
        }


    # ================================================================
    # ACTION: BRANCH MASTER REPORT
    # ================================================================
    elif action == "branch_master_report":
        current_user = (
            frappe.session.user
            or ""
        ).strip().lower()

        user_prefix = (
            current_user.split("@")[0]
            if "@" in current_user
            else current_user
        )

        user_key = (
            user_prefix
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
            .replace(".", "")
            .lower()
        )

        matched_branch = ""

        branch_rows = frappe.db.get_all(
            "Branch",
            fields=[
                "name"
            ],
            order_by="name asc",
            limit_page_length=0
        )

        for branch_row in branch_rows:
            branch_name = (
                branch_row.name
                or ""
            )

            branch_key = (
                branch_name
                .replace(" ", "")
                .replace("-", "")
                .replace("_", "")
                .replace(".", "")
                .lower()
            )

            if branch_key == user_key:
                matched_branch = branch_name
                break

        if not matched_branch:
            frappe.throw(
                "Your login is not mapped to an active branch."
            )

        allowed_statuses = [
            "Sent to Branch",
            "Actioned",
            "Closed"
        ]

        requested_status = (
            frappe.form_dict.get("status")
            or ""
        ).strip()

        from_date = (
            frappe.form_dict.get("from_date")
            or ""
        ).strip()

        to_date = (
            frappe.form_dict.get("to_date")
            or ""
        ).strip()

        requested_sort = (
            frappe.form_dict.get("sort")
            or "desc"
        ).strip().lower()

        if requested_sort not in [
            "asc",
            "desc"
        ]:
            requested_sort = "desc"

        filters = {
            "branch": matched_branch,
            "audit_status": [
                "in",
                allowed_statuses
            ]
        }

        if requested_status:
            if requested_status not in allowed_statuses:
                frappe.throw(
                    "This report status is not available to branch users."
                )

            filters["audit_status"] = (
                requested_status
            )

        if from_date and to_date:
            filters["audit_date"] = [
                "between",
                [
                    from_date,
                    to_date
                ]
            ]
        elif from_date:
            filters["audit_date"] = [
                ">=",
                from_date
            ]
        elif to_date:
            filters["audit_date"] = [
                "<=",
                to_date
            ]

        audit_rows = frappe.db.get_all(
            "Branch Audit",
            filters=filters,
            fields=[
                "name",
                "branch",
                "audit_date",
                "auditor",
                "audit_status",
                "total_score",
                "max_score",
                "percentage",
                "grade",
                "has_violation",
                "violation_summary",
                "docstatus",
                "creation",
                "management_remarks_to_auditor",
                "management_remarks_to_branch",
                "verified_on",
                "verified_by",
                "sent_to_branch_on",
                "sent_to_branch_by",
                "branch_report_email"
            ],
            order_by=(
                "audit_date "
                + requested_sort
                + ", creation desc"
            ),
            limit_page_length=200
        )

        result_audits = []

        for audit_row in audit_rows:
            full_audit = frappe.get_doc(
                "Branch Audit",
                audit_row.name
            )

            section_scores = []

            for score_row in (
                full_audit.section_scores
                or []
            ):
                section_scores.append(
                    {
                        "section_code": (
                            score_row.section_code
                            or ""
                        ),
                        "section_name": (
                            score_row.section_name
                            or ""
                        ),
                        "raw": frappe.utils.flt(
                            score_row.raw
                        ),
                        "raw_max": frappe.utils.flt(
                            score_row.raw_max
                        ),
                        "group_score": frappe.utils.flt(
                            score_row.group_score
                        ),
                        "weight": frappe.utils.flt(
                            score_row.weight
                        )
                    }
                )

            ratings = []

            for rating_row in (
                full_audit.ratings
                or []
            ):
                ratings.append(
                    {
                        "section_code": (
                            rating_row.section_code
                            or ""
                        ),
                        "question": (
                            rating_row.question
                            or ""
                        ),
                        "points": frappe.utils.flt(
                            rating_row.points
                        ),
                        "rating": (
                            rating_row.rating
                            or ""
                        ),
                        "scored": frappe.utils.flt(
                            rating_row.scored
                        ),
                        "is_critical_item": (
                            frappe.utils.cint(
                                rating_row.is_critical_item
                            )
                        )
                    }
                )

            result_audits.append(
                {
                    "name": audit_row.name,
                    "branch": audit_row.branch,
                    "audit_date": audit_row.audit_date,
                    "auditor": audit_row.auditor,
                    "audit_status": audit_row.audit_status,
                    "total_score": frappe.utils.flt(
                        audit_row.total_score
                    ),
                    "max_score": frappe.utils.flt(
                        audit_row.max_score
                    ),
                    "percentage": frappe.utils.flt(
                        audit_row.percentage
                    ),
                    "grade": audit_row.grade or "",
                    "has_violation": (
                        frappe.utils.cint(
                            audit_row.has_violation
                        )
                    ),
                    "violation_summary": (
                        audit_row.violation_summary
                        or ""
                    ),
                    "docstatus": audit_row.docstatus,
                    "creation": audit_row.creation,
                    "management_remarks_to_auditor": (
                        audit_row.management_remarks_to_auditor
                        or ""
                    ),
                    "management_remarks_to_branch": (
                        audit_row.management_remarks_to_branch
                        or ""
                    ),
                    "verified_on": (
                        audit_row.verified_on
                        or ""
                    ),
                    "verified_by": (
                        audit_row.verified_by
                        or ""
                    ),
                    "sent_to_branch_on": (
                        audit_row.sent_to_branch_on
                        or ""
                    ),
                    "sent_to_branch_by": (
                        audit_row.sent_to_branch_by
                        or ""
                    ),
                    "branch_report_email": (
                        audit_row.branch_report_email
                        or ""
                    ),
                    "section_scores": section_scores,
                    "ratings": ratings
                }
            )

        frappe.response["message"] = {
            "ok": True,
            "branch": matched_branch,
            "audits": result_audits
        }


    # ================================================================
    # INVALID ACTION
    # ================================================================
    else:
        frappe.throw(
            "Invalid audit topic action."
        )
