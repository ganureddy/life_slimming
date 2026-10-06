"""Branch visit report

Original API: life_cc_agent_marketing_data
Source modified: 2026-09-04 14:44:12.586677
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
    # ERPNext / Frappe v15 — API SERVER SCRIPT
    #
    # Server Script Type : API
    # API Method         : life_cc_agent_marketing_data
    # Allow Guest        : OFF
    # Enabled            : ON
    #
    # Security:
    # - Detailed Lead rows are restricted to the logged-in owner for
    #   ordinary agent users.
    # - ranking_rows expose only Lead ID, agent owner, appointment date,
    #   and appointment status. No client name/mobile/remarks are exposed.
    # - This allows every agent to see the full Agent Ranking card while
    #   keeping the detailed Agent Report restricted to their own Leads.
    # ================================================================

    from_date = str(
        frappe.form_dict.get("from_date") or ""
    ).strip()

    to_date = str(
        frappe.form_dict.get("to_date") or ""
    ).strip()

    if not from_date or not to_date:
        frappe.throw(
            "From Date and To Date are required."
        )

    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw(
            "Please log in to view this report."
        )

    roles = []

    if user != "Administrator":
        role_rows = frappe.get_all(
            "Has Role",
            filters={
                "parent": user,
                "parenttype": "User"
            },
            fields=["role"],
            limit_page_length=200
        )

        for role_row in role_rows:
            role_name = str(
                role_row.get("role") or ""
            ).strip()

            if role_name:
                roles.append(role_name)

    # ------------------------------------------------
    # AGENT ACCESS RULE
    #
    # LIFE CC Agent logins are names such as:
    #   lifescc13@gmail.com
    #   lifescc001@gmail.com
    #
    # Agent accounts are restricted to their own Lead rows.
    # Other authenticated report users may load all Agents or one
    # selected Agent via the optional agent_owner argument.
    # ------------------------------------------------

    requested_agent = str(
        frappe.form_dict.get("agent_owner") or ""
    ).strip()

    user_local_part = str(user).split("@")[0].lower()

    agent_suffix = ""

    if user_local_part.startswith("lifescc"):
        agent_suffix = user_local_part[len("lifescc"):]

    is_agent_login = (
        True
        if (
            agent_suffix
            and agent_suffix.isdigit()
        )
        else False
    )

    if is_agent_login:
        owner_filter = user
    elif requested_agent:
        owner_filter = requested_agent
    else:
        owner_filter = ""

    # Vue's essential schedule does not need the financial joins below.
    # Keep exactly the same owner scope as the existing report endpoint.
    if frappe.form_dict.get("view") == "appointments":
        filters = {"custom_appointment_date_and_time": [
            "between", [from_date + " 00:00:00", to_date + " 23:59:59"]
        ]}
        if owner_filter:
            filters["lead_owner"] = owner_filter
        schedule_fields = ["name", "lead_name", "lead_owner", "mobile_no", "branch",
            "lead_assign_to_branch", "custom_appointment_date_and_time",
            "custom_appointment_status", "custom_cc_stage", "status"]
        if frappe.get_meta("Lead").has_field("custom_visit_status"):
            schedule_fields.append("custom_visit_status")
        total = frappe.db.count("Lead", filters=filters)
        schedule = frappe.get_all("Lead", fields=schedule_fields, filters=filters,
            order_by="custom_appointment_date_and_time asc, name asc", limit_page_length=10000)
        frappe.response["message"] = {"ok": True, "rows": schedule, "total": total,
            "truncated": total > len(schedule), "restricted_to_owner": bool(owner_filter)}
        return

    fields = [
        "name",
        "lead_name",
        "lead_owner",
        "gender",
        "age",
        "mobile_no",
        "city",
        "status",
        "creation",

        "branch",
        "lead_assign_to_branch",
        "custom_appointment_status",
        "custom_appointment_date_and_time",
        "custom_consulting_doctor",
        "custom_cc_stage",
        "custom_remarks",
        "custom_conclusion_remark",
        "custom_next_followup_date",

        "source",
        "ad_set",
        "enquired_for",
        "campaign_name",
        "custom_campaignaudience",
        "category",
        "custom_treatment_interests",
        "custom_specific_interests",
        "custom_client_category",
        "custom_media",
        "custom_posting_date",

        "customer"
    ]


    def get_leads(
        date_field,
        start_value,
        end_value
    ):
        filters = {
            date_field: [
                "between",
                [
                    start_value,
                    end_value
                ]
            ]
        }

        if owner_filter:
            filters["lead_owner"] = owner_filter

        return frappe.get_all(
            "Lead",
            fields=fields,
            filters=filters,
            order_by=date_field + " desc",
            limit_page_length=10000
        )


    date_time_from = from_date + " 00:00:00"
    date_time_to = to_date + " 23:59:59"

    rows = []

    rows.extend(
        get_leads(
            "custom_appointment_date_and_time",
            date_time_from,
            date_time_to
        )
    )

    rows.extend(
        get_leads(
            "custom_posting_date",
            from_date,
            to_date
        )
    )

    rows.extend(
        get_leads(
            "creation",
            date_time_from,
            date_time_to
        )
    )

    unique_rows = {}

    for row in rows:
        lead_name = ""

        if row:
            lead_name = str(
                row.get("name") or ""
            ).strip()

        if lead_name:
            unique_rows[lead_name] = row

    final_rows = []

    for lead_name in unique_rows:
        final_rows.append(
            unique_rows[lead_name]
        )

    # ------------------------------------------------
    # Secure Sales Invoice financial mapping — EXACT LINKS ONLY
    #
    # Correct relationship confirmed in the ERPNext DocTypes:
    # Lead.name
    #   -> Patient.custom_lead
    #   -> Sales Invoice.patient
    #   -> Sales Invoice.custom_therapy_plan /
    #      Sales Invoice.therapy_plan_reference_id
    #
    # IMPORTANT:
    # - Never select an invoice only because customer_name/lead_name
    #   happens to be the same (for example "Vinod").
    # - Mobile is used only to find the Patient when an old Patient has
    #   no custom_lead link, and only when the match is unambiguous.
    # ------------------------------------------------

    def normalize_name(value):
        return " ".join(
            str(value or "").strip().lower().split()
        )


    def normalize_mobile(value):
        digits = ""

        for character in str(value or ""):
            if character.isdigit():
                digits += character

        if len(digits) > 10:
            digits = digits[-10:]

        return digits


    def positive_number(value):
        try:
            number = float(value or 0)
        except Exception:
            number = 0

        if number > 0:
            return number

        return 0


    def first_positive(values):
        for value in values:
            number = positive_number(value)

            if number > 0:
                return number

        return 0


    def paid_without_gst_amount(
        paid_amount,
        invoice_with_gst,
        invoice_without_gst
    ):
        paid_value = positive_number(
            paid_amount
        )

        with_gst_value = positive_number(
            invoice_with_gst
        )

        without_gst_value = positive_number(
            invoice_without_gst
        )

        if paid_value <= 0:
            return 0

        if (
            with_gst_value > 0
            and without_gst_value > 0
            and without_gst_value <= with_gst_value
        ):
            return round(
                paid_value
                * without_gst_value
                / with_gst_value,
                2
            )

        return round(
            paid_value / 1.05,
            2
        )


    lead_names = []
    lead_customer_ids = []
    lead_mobile_values = []

    for lead_row in final_rows:
        lead_id = str(
            lead_row.get("name") or ""
        ).strip()

        customer_id = str(
            lead_row.get("customer") or ""
        ).strip()

        mobile_value = normalize_mobile(
            lead_row.get("mobile_no")
        )

        if lead_id and lead_id not in lead_names:
            lead_names.append(lead_id)

        if (
            customer_id
            and customer_id not in lead_customer_ids
        ):
            lead_customer_ids.append(customer_id)

        if mobile_value:
            mobile_variants = [
                mobile_value,
                "91" + mobile_value,
                "+91" + mobile_value
            ]

            for mobile_variant in mobile_variants:
                if mobile_variant not in lead_mobile_values:
                    lead_mobile_values.append(
                        mobile_variant
                    )


    patient_fields = [
        "name",
        "patient_name",
        "mobile",
        "customer",
        "custom_lead",
        "branch_name",
        "modified"
    ]

    patient_map = {}


    def add_patient_rows(rows):
        for patient_row in rows:
            patient_id = str(
                patient_row.get("name") or ""
            ).strip()

            if patient_id:
                patient_map[patient_id] = patient_row


    # Strongest link: Patient.custom_lead -> exact Lead document.
    if lead_names:
        add_patient_rows(
            frappe.get_all(
                "Patient",
                fields=patient_fields,
                filters=[
                    [
                        "custom_lead",
                        "in",
                        lead_names
                    ]
                ],
                limit_page_length=20000
            )
        )


    # Exact Customer ID is a safe old-record fallback.
    if lead_customer_ids:
        add_patient_rows(
            frappe.get_all(
                "Patient",
                fields=patient_fields,
                filters=[
                    [
                        "customer",
                        "in",
                        lead_customer_ids
                    ]
                ],
                limit_page_length=20000
            )
        )


    # Mobile fallback is allowed only through Patient, never directly
    # from a Lead name to a Sales Invoice.
    if lead_mobile_values:
        add_patient_rows(
            frappe.get_all(
                "Patient",
                fields=patient_fields,
                filters=[
                    [
                        "mobile",
                        "in",
                        lead_mobile_values
                    ]
                ],
                order_by="modified desc",
                limit_page_length=20000
            )
        )


    patient_by_lead = {}
    patients_by_customer = {}
    patients_by_mobile = {}

    for patient_id in patient_map:
        patient_row = patient_map[patient_id]

        linked_lead = str(
            patient_row.get("custom_lead") or ""
        ).strip()

        customer_id = str(
            patient_row.get("customer") or ""
        ).strip()

        patient_mobile = normalize_mobile(
            patient_row.get("mobile")
        )

        if (
            linked_lead
            and linked_lead not in patient_by_lead
        ):
            patient_by_lead[linked_lead] = patient_row

        if customer_id:
            if customer_id not in patients_by_customer:
                patients_by_customer[customer_id] = []

            patients_by_customer[
                customer_id
            ].append(patient_row)

        if patient_mobile:
            if patient_mobile not in patients_by_mobile:
                patients_by_mobile[patient_mobile] = []

            patients_by_mobile[
                patient_mobile
            ].append(patient_row)


    lead_patient_map = {}

    for lead_row in final_rows:
        lead_id = str(
            lead_row.get("name") or ""
        ).strip()

        customer_id = str(
            lead_row.get("customer") or ""
        ).strip()

        lead_display_name = normalize_name(
            lead_row.get("lead_name")
        )

        mobile_value = normalize_mobile(
            lead_row.get("mobile_no")
        )

        selected_patient = None

        # 1. Exact Lead link.
        if (
            lead_id
            and lead_id in patient_by_lead
        ):
            selected_patient = patient_by_lead[
                lead_id
            ]

        # 2. Exact Customer ID, only if one Patient uses it.
        if (
            not selected_patient
            and customer_id
            and customer_id in patients_by_customer
        ):
            customer_patients = patients_by_customer[
                customer_id
            ]

            if len(customer_patients) == 1:
                selected_patient = customer_patients[0]

        # 3. Exact mobile fallback. If multiple Patient records share
        #    the mobile, require the Patient name to match the Lead name.
        if (
            not selected_patient
            and mobile_value
            and mobile_value in patients_by_mobile
        ):
            mobile_patients = patients_by_mobile[
                mobile_value
            ]

            if len(mobile_patients) == 1:
                selected_patient = mobile_patients[0]
            else:
                for mobile_patient in mobile_patients:
                    patient_display_name = normalize_name(
                        mobile_patient.get(
                            "patient_name"
                        )
                    )

                    if (
                        lead_display_name
                        and patient_display_name
                        == lead_display_name
                    ):
                        selected_patient = mobile_patient
                        break

        if selected_patient and lead_id:
            lead_patient_map[
                lead_id
            ] = selected_patient


    patient_names = []

    for lead_id in lead_patient_map:
        patient_id = str(
            lead_patient_map[
                lead_id
            ].get("name") or ""
        ).strip()

        if (
            patient_id
            and patient_id not in patient_names
        ):
            patient_names.append(patient_id)


    invoice_fields = [
        "name",
        "patient",
        "patient_name",
        "custom_therapy_plan",
        "therapy_plan_reference_id",
        "customer",
        "customer_name",
        "contact_mobile",
        "posting_date",
        "total",
        "net_total",
        "total_taxes_and_charges",
        "grand_total",
        "rounded_total",
        "base_grand_total",
        "paid_amount",
        "outstanding_amount",
        "status",
        "branch",
        "docstatus"
    ]

    invoice_rows = []

    if patient_names:
        invoice_rows = frappe.get_all(
            "Sales Invoice",
            fields=invoice_fields,
            filters=[
                [
                    "patient",
                    "in",
                    patient_names
                ],
                [
                    "posting_date",
                    "between",
                    [
                        from_date,
                        to_date
                    ]
                ],
                [
                    "docstatus",
                    "=",
                    1
                ]
            ],
            order_by="posting_date asc, creation asc",
            limit_page_length=20000
        )


    invoices_by_patient = {}

    for invoice_row in invoice_rows:
        patient_id = str(
            invoice_row.get("patient") or ""
        ).strip()

        if not patient_id:
            continue

        if patient_id not in invoices_by_patient:
            invoices_by_patient[patient_id] = []

        invoices_by_patient[
            patient_id
        ].append(invoice_row)


    def invoice_plan_id(invoice_row):
        return str(
            invoice_row.get(
                "custom_therapy_plan"
            )
            or invoice_row.get(
                "therapy_plan_reference_id"
            )
            or ""
        ).strip()


    def choose_exact_patient_invoice(
        lead_row,
        patient_row
    ):
        patient_id = str(
            patient_row.get("name") or ""
        ).strip()

        appointment_date = str(
            lead_row.get(
                "custom_appointment_date_and_time"
            ) or ""
        )[:10]

        if not patient_id or not appointment_date:
            return None

        patient_invoices = invoices_by_patient.get(
            patient_id
        ) or []

        # Package financials must belong to the exact transaction date.
        date_candidates = []

        for candidate in patient_invoices:
            candidate_date = str(
                candidate.get("posting_date") or ""
            )[:10]

            if candidate_date == appointment_date:
                date_candidates.append(candidate)

        if not date_candidates:
            return None

        # If there is only one submitted invoice for this exact Patient
        # on this exact date, it is safe to use.
        if len(date_candidates) == 1:
            return date_candidates[0]

        # Multiple same-day invoices:
        # Try to resolve using the invoice's direct Therapy Plan link.
        # We only accept a unique direct-plan candidate.
        linked_candidates = []

        for candidate in date_candidates:
            candidate_plan = invoice_plan_id(
                candidate
            )

            if candidate_plan:
                linked_candidates.append(
                    candidate
                )

        if len(linked_candidates) == 1:
            return linked_candidates[0]

        # Ambiguous = show no package amount rather than a wrong package.
        return None


    for lead_row in final_rows:
        lead_id = str(
            lead_row.get("name") or ""
        ).strip()

        patient_row = lead_patient_map.get(
            lead_id
        )

        if not patient_row:
            continue

        selected_invoice = choose_exact_patient_invoice(
            lead_row,
            patient_row
        )

        # Patient link exists but there is no submitted invoice for that
        # Patient in the selected transaction-date range.
        if not selected_invoice:
            lead_row["financial_patient"] = str(
                patient_row.get("name") or ""
            )

            lead_row["financial_patient_name"] = str(
                patient_row.get("patient_name") or ""
            )

            lead_row["financial_customer"] = str(
                patient_row.get("customer") or ""
            )

            continue

        amount_with_gst = first_positive(
            [
                selected_invoice.get("rounded_total"),
                selected_invoice.get("grand_total"),
                selected_invoice.get("base_grand_total")
            ]
        )

        amount_without_gst = first_positive(
            [
                selected_invoice.get("net_total"),
                selected_invoice.get("total")
            ]
        )

        if amount_without_gst <= 0:
            taxes = positive_number(
                selected_invoice.get(
                    "total_taxes_and_charges"
                )
            )

            calculated_without_gst = (
                amount_with_gst - taxes
            )

            if calculated_without_gst > 0:
                amount_without_gst = (
                    calculated_without_gst
                )

        paid_amount = positive_number(
            selected_invoice.get(
                "paid_amount"
            )
        )

        # Balance immediately after invoice creation.
        # Do NOT use current outstanding_amount because later payments
        # can reduce today's outstanding to zero and falsely make the
        # old invoice look fully paid on its creation date.
        balance_amount = (
            amount_with_gst -
            paid_amount
        )

        if balance_amount < 0:
            balance_amount = 0

        # Later collections are shown from Payment Entry Reference on
        # their own posting dates in financial_events.
        lead_row["financial_without_gst"] = (
            amount_without_gst
        )

        lead_row["financial_with_gst"] = (
            amount_with_gst
        )

        lead_row["financial_paid_amount"] = (
            paid_amount
        )

        lead_row["financial_balance_amount"] = (
            balance_amount
        )

        lead_row["financial_sales_invoice"] = str(
            selected_invoice.get("name") or ""
        )

        lead_row["financial_invoice_date"] = str(
            selected_invoice.get(
                "posting_date"
            ) or ""
        )

        lead_row["financial_patient"] = str(
            selected_invoice.get("patient") or
            patient_row.get("name") or
            ""
        )

        lead_row["financial_patient_name"] = str(
            selected_invoice.get(
                "patient_name"
            ) or patient_row.get(
                "patient_name"
            ) or ""
        )

        lead_row["financial_customer"] = str(
            selected_invoice.get("customer") or
            patient_row.get("customer") or
            ""
        )

        lead_row["financial_therapy_plan"] = (
            invoice_plan_id(
                selected_invoice
            )
        )

        lead_row["financial_match_rule"] = (
            "EXACT_PATIENT_AND_INVOICE_DATE"
        )

    # ------------------------------------------------
    # DATE-BASED INVOICE / PAYMENT ACTIVITY
    #
    # Business rule:
    # - Package is shown on Sales Invoice.posting_date.
    # - Payment is shown on Payment Entry.posting_date.
    # - Same client may appear again on a later payment date.
    # - Payment(s) on the invoice date are merged into the Invoice row,
    #   so a client who pays half on invoice day and half next day
    #   appears exactly twice: invoice day + next payment day.
    # ------------------------------------------------

    event_invoice_fields = [
        "name",
        "patient",
        "patient_name",
        "custom_therapy_plan",
        "therapy_plan_reference_id",
        "customer",
        "customer_name",
        "contact_mobile",
        "posting_date",
        "total",
        "net_total",
        "total_taxes_and_charges",
        "grand_total",
        "rounded_total",
        "base_grand_total",
        "paid_amount",
        "outstanding_amount",
        "is_pos",
        "branch",
        "docstatus"
    ]

    invoice_event_rows = frappe.get_all(
        "Sales Invoice",
        fields=event_invoice_fields,
        filters=[
            [
                "posting_date",
                "between",
                [
                    from_date,
                    to_date
                ]
            ],
            [
                "docstatus",
                "=",
                1
            ]
        ],
        order_by="posting_date asc, creation asc",
        limit_page_length=20000
    )

    payment_rows = frappe.get_all(
        "Payment Entry",
        fields=[
            "name",
            "posting_date",
            "creation",
            "payment_type",
            "party",
            "branch",
            "paid_amount",
            "received_amount",
            "mode_of_payment",
            "docstatus"
        ],
        filters=[
            [
                "posting_date",
                "between",
                [
                    from_date,
                    to_date
                ]
            ],
            [
                "docstatus",
                "=",
                1
            ],
            [
                "payment_type",
                "=",
                "Receive"
            ]
        ],
        order_by="posting_date asc, creation asc",
        limit_page_length=20000
    )

    payment_names = []

    for payment_row in payment_rows:
        payment_name = str(
            payment_row.get("name") or ""
        ).strip()

        if payment_name:
            payment_names.append(payment_name)

    payment_reference_rows = []

    if payment_names:
        payment_reference_rows = frappe.get_all(
            "Payment Entry Reference",
            fields=[
                "parent",
                "reference_doctype",
                "reference_name",
                "allocated_amount",
                "outstanding_amount"
            ],
            filters=[
                [
                    "parent",
                    "in",
                    payment_names
                ],
                [
                    "reference_doctype",
                    "=",
                    "Sales Invoice"
                ]
            ],
            limit_page_length=30000
        )

    payment_by_name = {}

    for payment_row in payment_rows:
        payment_name = str(
            payment_row.get("name") or ""
        ).strip()

        if payment_name:
            payment_by_name[payment_name] = payment_row

    referenced_invoice_names = []

    for reference_row in payment_reference_rows:
        invoice_name = str(
            reference_row.get("reference_name") or ""
        ).strip()

        if (
            invoice_name
            and invoice_name not in referenced_invoice_names
        ):
            referenced_invoice_names.append(invoice_name)

    referenced_invoice_rows = []

    if referenced_invoice_names:
        referenced_invoice_rows = frappe.get_all(
            "Sales Invoice",
            fields=event_invoice_fields,
            filters=[
                [
                    "name",
                    "in",
                    referenced_invoice_names
                ],
                [
                    "docstatus",
                    "=",
                    1
                ]
            ],
            limit_page_length=20000
        )

    event_invoice_map = {}

    for invoice_row in invoice_event_rows:
        invoice_name = str(
            invoice_row.get("name") or ""
        ).strip()

        if invoice_name:
            event_invoice_map[invoice_name] = invoice_row

    for invoice_row in referenced_invoice_rows:
        invoice_name = str(
            invoice_row.get("name") or ""
        ).strip()

        if invoice_name:
            event_invoice_map[invoice_name] = invoice_row


    def invoice_amounts(invoice_row):
        amount_with_gst = first_positive(
            [
                invoice_row.get("rounded_total"),
                invoice_row.get("grand_total"),
                invoice_row.get("base_grand_total")
            ]
        )

        amount_without_gst = first_positive(
            [
                invoice_row.get("net_total"),
                invoice_row.get("total")
            ]
        )

        if amount_without_gst <= 0:
            tax_amount = positive_number(
                invoice_row.get(
                    "total_taxes_and_charges"
                )
            )

            calculated_amount = (
                amount_with_gst - tax_amount
            )

            if calculated_amount > 0:
                amount_without_gst = calculated_amount

        return [
            amount_with_gst,
            amount_without_gst
        ]


    # Payment allocation grouped by invoice + payment date.
    payment_day_map = {}

    for reference_row in payment_reference_rows:
        payment_name = str(
            reference_row.get("parent") or ""
        ).strip()

        invoice_name = str(
            reference_row.get("reference_name") or ""
        ).strip()

        payment_row = payment_by_name.get(
            payment_name
        )

        invoice_row = event_invoice_map.get(
            invoice_name
        )

        if not payment_row or not invoice_row:
            continue

        payment_date = str(
            payment_row.get("posting_date") or ""
        ).strip()

        if not payment_date:
            continue

        event_group_key = (
            invoice_name + "|" + payment_date
        )

        allocated_amount = positive_number(
            reference_row.get(
                "allocated_amount"
            )
        )

        outstanding_before = positive_number(
            reference_row.get(
                "outstanding_amount"
            )
        )

        balance_after = 0

        if outstanding_before > 0:
            balance_after = (
                outstanding_before -
                allocated_amount
            )

            if balance_after < 0:
                balance_after = 0

        if event_group_key not in payment_day_map:
            payment_day_map[event_group_key] = {
                "invoice_name": invoice_name,
                "payment_date": payment_date,
                "paid_amount": 0,
                "balance_after": balance_after,
                "payment_entries": [],
                "mode_of_payment": "",
                "branch": str(
                    invoice_row.get("branch") or
                    payment_row.get("branch") or
                    ""
                ).strip()
            }

        current_payment_group = payment_day_map[
            event_group_key
        ]

        current_payment_group["paid_amount"] = (
            positive_number(
                current_payment_group.get(
                    "paid_amount"
                )
            )
            + allocated_amount
        )

        if balance_after >= 0:
            payment_day_map[
                event_group_key
            ]["balance_after"] = balance_after

        if (
            payment_name
            and payment_name not in payment_day_map[
                event_group_key
            ]["payment_entries"]
        ):
            payment_day_map[
                event_group_key
            ]["payment_entries"].append(
                payment_name
            )

        mode_value = str(
            payment_row.get("mode_of_payment") or ""
        ).strip()

        if mode_value:
            payment_day_map[
                event_group_key
            ]["mode_of_payment"] = mode_value


    financial_events = []

    # Invoice Created rows.
    for invoice_row in invoice_event_rows:
        invoice_name = str(
            invoice_row.get("name") or ""
        ).strip()

        invoice_date = str(
            invoice_row.get("posting_date") or ""
        ).strip()

        amounts = invoice_amounts(
            invoice_row
        )

        amount_with_gst = amounts[0]
        amount_without_gst = amounts[1]

        direct_paid_amount = 0

        # Sales Invoice.paid_amount belongs to POS/direct invoice payment.
        # Normal invoice collections are taken from submitted Payment Entry
        # Reference. This prevents the same receipt being counted twice.
        if int(invoice_row.get("is_pos") or 0) == 1:
            direct_paid_amount = positive_number(
                invoice_row.get("paid_amount")
            )

        same_day_key = (
            invoice_name + "|" + invoice_date
        )

        same_day_payment = payment_day_map.get(
            same_day_key
        )

        payment_entry_paid = 0
        payment_entries = []
        payment_mode = ""

        if same_day_payment:
            payment_entry_paid = positive_number(
                same_day_payment.get(
                    "paid_amount"
                )
            )

            payment_entries = same_day_payment.get(
                "payment_entries"
            ) or []

            payment_mode = str(
                same_day_payment.get(
                    "mode_of_payment"
                ) or ""
            ).strip()

        paid_on_invoice_date = (
            direct_paid_amount +
            payment_entry_paid
        )

        paid_on_invoice_date_without_gst = (
            paid_without_gst_amount(
                paid_on_invoice_date,
                amount_with_gst,
                amount_without_gst
            )
        )

        balance_after = (
            amount_with_gst -
            paid_on_invoice_date
        )

        if balance_after < 0:
            balance_after = 0

        financial_events.append(
            {
                "event_key": (
                    "INV|" +
                    invoice_name +
                    "|" +
                    invoice_date
                ),
                "event_type": "Invoice",
                "event_order": 1,
                "event_date": invoice_date,
                "invoice_date": invoice_date,
                "patient": str(
                    invoice_row.get("patient") or ""
                ),
                "therapy_plan": str(
                    invoice_row.get(
                        "custom_therapy_plan"
                    )
                    or invoice_row.get(
                        "therapy_plan_reference_id"
                    )
                    or ""
                ),
                "customer": str(
                    invoice_row.get("customer") or ""
                ),
                "customer_name": str(
                    invoice_row.get("customer_name") or
                    invoice_row.get("customer") or
                    ""
                ),
                "contact_mobile": str(
                    invoice_row.get(
                        "contact_mobile"
                    ) or ""
                ),
                "branch": str(
                    invoice_row.get("branch") or ""
                ),
                "sales_invoice": invoice_name,
                "payment_entries": payment_entries,
                "mode_of_payment": payment_mode,
                "with_gst": amount_with_gst,
                "without_gst": amount_without_gst,
                "paid_amount": paid_on_invoice_date,
                "paid_with_gst": paid_on_invoice_date,
                "paid_without_gst": (
                    paid_on_invoice_date_without_gst
                ),
                "tax_in_paid": round(
                    paid_on_invoice_date
                    - paid_on_invoice_date_without_gst,
                    2
                ),
                "pe_paid_amount": payment_entry_paid,
                "report_grand_total": positive_number(
                    invoice_row.get("grand_total")
                ),
                "report_net_total": positive_number(
                    invoice_row.get("net_total")
                ),
                "balance_after": balance_after,

                # Current ERPNext Sales Invoice outstanding.
                # This is NOT reconstructed from Payment Entry Reference.
                "current_outstanding": positive_number(
                    invoice_row.get(
                        "outstanding_amount"
                    )
                )
            }
        )


    # Later payment date rows.
    for event_group_key in payment_day_map:
        payment_event = payment_day_map[
            event_group_key
        ]

        invoice_name = str(
            payment_event.get(
                "invoice_name"
            ) or ""
        ).strip()

        payment_date = str(
            payment_event.get(
                "payment_date"
            ) or ""
        ).strip()

        invoice_row = event_invoice_map.get(
            invoice_name
        )

        if not invoice_row:
            continue

        invoice_date = str(
            invoice_row.get("posting_date") or ""
        ).strip()

        # Same-day Payment Entry is already merged into Invoice row.
        if payment_date == invoice_date:
            continue

        amounts = invoice_amounts(
            invoice_row
        )

        payment_event_paid = positive_number(
            payment_event.get(
                "paid_amount"
            )
        )

        payment_event_paid_without_gst = (
            paid_without_gst_amount(
                payment_event_paid,
                amounts[0],
                amounts[1]
            )
        )

        financial_events.append(
            {
                "event_key": (
                    "PAY|" +
                    invoice_name +
                    "|" +
                    payment_date
                ),
                "event_type": "Payment",
                "event_order": 2,
                "event_date": payment_date,

                # Original Sales Invoice posting date.
                # Used in Outstanding Collected popup so the user can see
                # when the invoice was created and when the old outstanding
                # amount was actually collected.
                "invoice_date": invoice_date,
                "patient": str(
                    invoice_row.get("patient") or ""
                ),
                "therapy_plan": str(
                    invoice_row.get(
                        "custom_therapy_plan"
                    )
                    or invoice_row.get(
                        "therapy_plan_reference_id"
                    )
                    or ""
                ),
                "customer": str(
                    invoice_row.get("customer") or ""
                ),
                "customer_name": str(
                    invoice_row.get("customer_name") or
                    invoice_row.get("customer") or
                    ""
                ),
                "contact_mobile": str(
                    invoice_row.get(
                        "contact_mobile"
                    ) or ""
                ),
                # Branch-wise collection belongs to the linked
                # Sales Invoice branch. Payment Entry.branch is only fallback.
                "branch": str(
                    invoice_row.get("branch") or
                    payment_event.get("branch") or
                    ""
                ),
                "sales_invoice": invoice_name,
                "payment_entries": (
                    payment_event.get(
                        "payment_entries"
                    ) or []
                ),
                "mode_of_payment": str(
                    payment_event.get(
                        "mode_of_payment"
                    ) or ""
                ),
                # Repeated for row readability. Totals count these
                # package amounts only on Invoice events.
                "with_gst": amounts[0],
                "without_gst": amounts[1],
                "paid_amount": payment_event_paid,
                "paid_with_gst": payment_event_paid,
                "paid_without_gst": (
                    payment_event_paid_without_gst
                ),
                "tax_in_paid": round(
                    payment_event_paid
                    - payment_event_paid_without_gst,
                    2
                ),
                "pe_paid_amount": payment_event_paid,
                "report_grand_total": positive_number(
                    invoice_row.get("grand_total")
                ),
                "report_net_total": positive_number(
                    invoice_row.get("net_total")
                ),
                "balance_after": positive_number(
                    payment_event.get(
                        "balance_after"
                    )
                ),

                # Current ERPNext Sales Invoice outstanding.
                # Use this for the dashboard Outstanding Amount KPI.
                "current_outstanding": positive_number(
                    invoice_row.get(
                        "outstanding_amount"
                    )
                )
            }
        )

    financial_events.sort(
        key=lambda row: (
            str(row.get("event_date") or ""),
            int(row.get("event_order") or 0),
            str(row.get("sales_invoice") or "")
        )
    )

    # ------------------------------------------------
    # Marketing attribution for payment-date reporting
    #
    # Each invoice/payment event is credited back to the exact Lead through:
    # Sales Invoice.patient -> Patient.custom_lead -> Lead
    #
    # This lets Marketing Agency Summary, Category Summary and Campaign
    # Performance report the actual amount received on Payment Entry posting_date.
    # ------------------------------------------------

    event_patient_ids = []

    for financial_event in financial_events:
        event_patient_id = str(
            financial_event.get("patient") or ""
        ).strip()

        if (
            event_patient_id
            and event_patient_id not in event_patient_ids
        ):
            event_patient_ids.append(
                event_patient_id
            )

    event_patient_rows = []

    if event_patient_ids:
        event_patient_rows = frappe.get_all(
            "Patient",
            fields=[
                "name",
                "patient_name",
                "mobile",
                "customer",
                "custom_lead",
                "branch_name"
            ],
            filters=[
                [
                    "name",
                    "in",
                    event_patient_ids
                ]
            ],
            limit_page_length=20000
        )

    event_patient_map = {}
    event_lead_ids = []

    for event_patient_row in event_patient_rows:
        event_patient_id = str(
            event_patient_row.get("name") or ""
        ).strip()

        linked_lead_id = str(
            event_patient_row.get("custom_lead") or ""
        ).strip()

        if event_patient_id:
            event_patient_map[
                event_patient_id
            ] = event_patient_row

        if (
            linked_lead_id
            and linked_lead_id not in event_lead_ids
        ):
            event_lead_ids.append(
                linked_lead_id
            )

    event_lead_rows = []

    if event_lead_ids:
        event_lead_rows = frappe.get_all(
            "Lead",
            fields=[
                "name",
                "lead_name",
                "first_name",
                "last_name",
                "mobile_no",
                "lead_owner",
                "source",
                "ad_set",
                "enquired_for",
                "lead_assign_to_branch",
                "branch",
                "customer",
                "campaign_name"
            ],
            filters=[
                [
                    "name",
                    "in",
                    event_lead_ids
                ]
            ],
            limit_page_length=20000
        )

    event_lead_map = {}

    for event_lead_row in event_lead_rows:
        event_lead_id = str(
            event_lead_row.get("name") or ""
        ).strip()

        if event_lead_id:
            event_lead_map[
                event_lead_id
            ] = event_lead_row

    for financial_event in financial_events:
        event_patient_id = str(
            financial_event.get("patient") or ""
        ).strip()

        event_patient_row = event_patient_map.get(
            event_patient_id
        ) or {}

        linked_lead_id = str(
            event_patient_row.get("custom_lead") or ""
        ).strip()

        event_lead_row = event_lead_map.get(
            linked_lead_id
        ) or {}

        financial_event["lead"] = linked_lead_id

        financial_event["lead_name"] = str(
            event_lead_row.get("lead_name")
            or event_lead_row.get("first_name")
            or event_patient_row.get("patient_name")
            or financial_event.get("customer_name")
            or ""
        ).strip()

        financial_event["mobile_no"] = str(
            event_lead_row.get("mobile_no")
            or event_patient_row.get("mobile")
            or financial_event.get("contact_mobile")
            or ""
        ).strip()

        financial_event["lead_owner"] = str(
            event_lead_row.get("lead_owner") or ""
        ).strip()

        # ------------------------------------------------
        # CC / CALL CENTER PAYMENT FLAG
        #
        # Count financial activity in CC Branch Visits Report ONLY when:
        #
        # Sales Invoice.patient
        #   -> Patient.custom_lead
        #   -> exact Lead
        #   -> Lead.lead_owner
        #
        # This excludes normal branch/front-desk/other payments that are
        # not linked back to a Call Center Lead.
        # ------------------------------------------------
        financial_event["lead_linked"] = (
            True if linked_lead_id else False
        )

        financial_event["cc_lead_linked"] = (
            True
            if (
                linked_lead_id
                and str(
                    event_lead_row.get("lead_owner") or ""
                ).strip()
            )
            else False
        )

        financial_event["source"] = str(
            event_lead_row.get("source") or ""
        ).strip()

        financial_event["ad_set"] = str(
            event_lead_row.get("ad_set") or ""
        ).strip()

        financial_event["enquired_for"] = str(
            event_lead_row.get("enquired_for") or ""
        ).strip()

        financial_event["campaign_name"] = str(
            event_lead_row.get("campaign_name") or ""
        ).strip()

        # Current Lead branch must be the primary branch.
        # lead_assign_to_branch is retained only as a legacy fallback.
        financial_event["lead_branch"] = str(
            event_lead_row.get("branch")
            or event_lead_row.get("lead_assign_to_branch")
            or event_patient_row.get("branch_name")
            or financial_event.get("branch")
            or ""
        ).strip()

    # ------------------------------------------------
    # EXACT CC INVOICE REPORT — BRANCH SUMMARY SOURCE
    #
    # IMPORTANT:
    # This is intentionally built from Payment Entry Reference rows,
    # not from the generic invoice/payment event timeline.
    #
    # It mirrors "CC Invoice Report":
    #   Payment Entry.posting_date in selected From/To
    #   + submitted Payment Entry
    #   + Payment Entry Reference -> Sales Invoice
    #   + submitted Sales Invoice
    #   + Sales Invoice.therapy_plan_reference_id -> Therapy Plan
    #   + Therapy Plan.media = "Call Center"
    #   + group once per Sales Invoice
    #
    # Financial branch is Sales Invoice.branch.
    # ------------------------------------------------

    cc_invoice_paid_by_invoice = {}

    for cc_reference_row in payment_reference_rows:
        cc_invoice_name = str(
            cc_reference_row.get("reference_name") or ""
        ).strip()

        if not cc_invoice_name:
            continue

        cc_allocated = positive_number(
            cc_reference_row.get("allocated_amount")
        )

        if cc_invoice_name not in cc_invoice_paid_by_invoice:
            cc_invoice_paid_by_invoice[cc_invoice_name] = 0

        cc_invoice_paid_by_invoice[cc_invoice_name] = (
            positive_number(
                cc_invoice_paid_by_invoice.get(
                    cc_invoice_name
                )
            )
            + cc_allocated
        )


    cc_invoice_therapy_ids = []

    for cc_invoice_name in cc_invoice_paid_by_invoice:
        cc_invoice_row = event_invoice_map.get(
            cc_invoice_name
        ) or {}

        cc_therapy_id = str(
            cc_invoice_row.get(
                "therapy_plan_reference_id"
            ) or ""
        ).strip()

        if (
            cc_therapy_id
            and cc_therapy_id not in cc_invoice_therapy_ids
        ):
            cc_invoice_therapy_ids.append(
                cc_therapy_id
            )


    cc_invoice_therapy_media = {}
    cc_invoice_therapy_already_taken = {}

    if cc_invoice_therapy_ids:
        cc_therapy_rows = frappe.get_all(
            "Therapy Plan",
            fields=[
                "name",
                "media",
                "therapy_plan_already_taken_"
            ],
            filters=[
                [
                    "name",
                    "in",
                    cc_invoice_therapy_ids
                ]
            ],
            limit_page_length=20000
        )

        for cc_therapy_row in cc_therapy_rows:
            cc_therapy_name = str(
                cc_therapy_row.get("name") or ""
            ).strip()

            if cc_therapy_name:
                cc_invoice_therapy_media[
                    cc_therapy_name
                ] = str(
                    cc_therapy_row.get("media") or ""
                ).strip()

                cc_invoice_therapy_already_taken[
                    cc_therapy_name
                ] = (
                    1
                    if int(
                        cc_therapy_row.get(
                            "therapy_plan_already_taken_"
                        ) or 0
                    ) == 1
                    else 0
                )


    # ------------------------------------------------
    # STRICT CALL CENTER NEW-PACKAGE GATE
    # ------------------------------------------------
    # Every financial event carries the resolved Therapy Plan media.
    # Any package whose Therapy Plan.media is not exactly "Call Center"
    # must never be used by dashboard financial calculations.
    for strict_financial_event in financial_events:
        strict_therapy_plan = str(
            strict_financial_event.get(
                "therapy_plan"
            ) or ""
        ).strip()

        strict_financial_event[
            "therapy_plan_media"
        ] = str(
            cc_invoice_therapy_media.get(
                strict_therapy_plan
            ) or ""
        ).strip()

        strict_financial_event[
            "therapy_plan_already_taken"
        ] = int(
            cc_invoice_therapy_already_taken.get(
                strict_therapy_plan
            ) or 0
        )

    # Lead / Marketing attribution is optional.
    # The CC Invoice Report itself does NOT require a Lead.
    cc_invoice_meta_by_invoice = {}

    for cc_financial_event in financial_events:
        cc_invoice_name = str(
            cc_financial_event.get(
                "sales_invoice"
            ) or ""
        ).strip()

        if not cc_invoice_name:
            continue

        existing_meta = (
            cc_invoice_meta_by_invoice.get(
                cc_invoice_name
            )
            or {}
        )

        if not existing_meta:
            existing_meta = {
                "lead": "",
                "lead_name": "",
                "lead_owner": "",
                "source": "",
                "ad_set": "",
                "enquired_for": "",
                "campaign_name": "",
                "lead_branch": ""
            }

        metadata_fields = [
            "lead",
            "lead_name",
            "lead_owner",
            "source",
            "ad_set",
            "enquired_for",
            "campaign_name",
            "lead_branch"
        ]

        for metadata_field in metadata_fields:
            current_value = str(
                existing_meta.get(
                    metadata_field
                ) or ""
            ).strip()

            event_value = str(
                cc_financial_event.get(
                    metadata_field
                ) or ""
            ).strip()

            if (
                not current_value
                and event_value
            ):
                existing_meta[
                    metadata_field
                ] = event_value

        cc_invoice_meta_by_invoice[
            cc_invoice_name
        ] = existing_meta


    # Exact Payment Entry Reference rows for Marketing Paid Amount.
    # These rows preserve the true payment date and allocation amount.
    cc_invoice_report_payment_rows = []
    cc_invoice_outstanding_by_invoice = {}

    for cc_reference_row in payment_reference_rows:
        cc_payment_name = str(
            cc_reference_row.get("parent") or ""
        ).strip()

        cc_invoice_name = str(
            cc_reference_row.get(
                "reference_name"
            ) or ""
        ).strip()

        cc_payment_row = payment_by_name.get(
            cc_payment_name
        ) or {}

        cc_invoice_row = event_invoice_map.get(
            cc_invoice_name
        ) or {}

        if (
            not cc_payment_row
            or not cc_invoice_row
        ):
            continue

        cc_therapy_id = str(
            cc_invoice_row.get(
                "therapy_plan_reference_id"
            ) or ""
        ).strip()

        cc_media = str(
            cc_invoice_therapy_media.get(
                cc_therapy_id
            ) or ""
        ).strip().lower()

        cc_already_taken = int(
            cc_invoice_therapy_already_taken.get(
                cc_therapy_id
            ) or 0
        )

        # FINAL CC DASHBOARD QUALIFICATION:
        # 1) Sales Invoice must link to Therapy Plan
        # 2) Therapy Plan.media must be "Call Center"
        # 3) Therapy Plan.therapy_plan_already_taken_ must be 0
        #
        # Existing/execution customer packages are marked by
        # therapy_plan_already_taken_ = 1 and must be excluded.
        if (
            not cc_therapy_id
            or cc_media != "call center"
            or cc_already_taken == 1
        ):
            continue

        cc_paid = positive_number(
            cc_reference_row.get(
                "allocated_amount"
            )
        )

        if cc_paid <= 0:
            continue

        cc_invoice_with_gst_for_paid = positive_number(
            cc_invoice_row.get(
                "grand_total"
            )
        )

        cc_invoice_without_gst_for_paid = positive_number(
            cc_invoice_row.get(
                "net_total"
            )
        )

        if cc_invoice_without_gst_for_paid <= 0:
            cc_invoice_without_gst_for_paid = positive_number(
                cc_invoice_row.get(
                    "total"
                )
            )

        cc_paid_without_gst = (
            paid_without_gst_amount(
                cc_paid,
                cc_invoice_with_gst_for_paid,
                cc_invoice_without_gst_for_paid
            )
        )

        cc_payment_date = str(
            cc_payment_row.get(
                "posting_date"
            ) or ""
        ).strip()[:10]

        cc_invoice_date = str(
            cc_invoice_row.get(
                "posting_date"
            ) or ""
        ).strip()[:10]

        cc_branch = str(
            cc_invoice_row.get("branch") or ""
        ).strip()

        if not cc_branch:
            cc_branch = "Branch Not Available"

        cc_meta = (
            cc_invoice_meta_by_invoice.get(
                cc_invoice_name
            )
            or {}
        )

        # Agent login: exact CC Invoice payment rows are self-only.
        if is_agent_login and owner_filter:
            cc_payment_owner = str(
                cc_meta.get(
                    "lead_owner"
                ) or ""
            ).strip().lower()

            cc_owner_filter_normalized = str(
                owner_filter
            ).strip().lower()

            if (
                not cc_payment_owner
                or cc_payment_owner
                != cc_owner_filter_normalized
            ):
                continue

        cc_is_later_collection = (
            True
            if (
                cc_invoice_date
                and cc_payment_date
                and cc_payment_date > cc_invoice_date
            )
            else False
        )

        if cc_is_later_collection:
            current_outstanding_collection = positive_number(
                cc_invoice_outstanding_by_invoice.get(
                    cc_invoice_name
                )
            )

            cc_invoice_outstanding_by_invoice[
                cc_invoice_name
            ] = (
                current_outstanding_collection
                + cc_paid
            )

        cc_invoice_report_payment_rows.append(
            {
                "payment_entry": cc_payment_name,
                "payment_date": cc_payment_date,
                "invoice": cc_invoice_name,
                "invoice_date": cc_invoice_date,
                "branch": cc_branch,
                "customer": str(
                    cc_invoice_row.get(
                        "customer"
                    ) or ""
                ).strip(),
                "therapy_plan": cc_therapy_id,
                "therapy_plan_media": str(
                    cc_invoice_therapy_media.get(
                        cc_therapy_id
                    ) or ""
                ).strip(),
                "therapy_plan_already_taken": int(
                    cc_invoice_therapy_already_taken.get(
                        cc_therapy_id
                    ) or 0
                ),
                "lead": str(
                    cc_meta.get("lead") or ""
                ).strip(),
                "lead_name": str(
                    cc_meta.get(
                        "lead_name"
                    ) or ""
                ).strip(),
                "lead_owner": str(
                    cc_meta.get(
                        "lead_owner"
                    ) or ""
                ).strip(),
                "source": str(
                    cc_meta.get("source") or ""
                ).strip(),
                "ad_set": str(
                    cc_meta.get("ad_set") or ""
                ).strip(),
                "enquired_for": str(
                    cc_meta.get(
                        "enquired_for"
                    ) or ""
                ).strip(),
                "campaign_name": str(
                    cc_meta.get(
                        "campaign_name"
                    ) or ""
                ).strip(),
                "lead_branch": str(
                    cc_meta.get(
                        "lead_branch"
                    ) or ""
                ).strip(),
                "paid": cc_paid,
                "paid_with_gst": cc_paid,
                "paid_without_gst": (
                    cc_paid_without_gst
                ),
                "tax_in_paid": round(
                    cc_paid
                    - cc_paid_without_gst,
                    2
                ),
                "is_later_collection": (
                    cc_is_later_collection
                ),
                "current_outstanding": (
                    positive_number(
                        cc_invoice_row.get(
                            "outstanding_amount"
                        )
                    )
                )
            }
        )


    cc_invoice_report_rows = []

    cc_invoice_report_totals = {
        "with_gst": 0,
        "without_gst": 0,
        "paid": 0,
        "paid_with_gst": 0,
        "paid_without_gst": 0,
        "paid_without_tax": 0,
        "tax_amount": 0,
        "balance": 0,
        "outstanding_collected": 0,
        "invoice_count": 0
    }

    for cc_invoice_name in cc_invoice_paid_by_invoice:
        cc_invoice_row = event_invoice_map.get(
            cc_invoice_name
        ) or {}

        if not cc_invoice_row:
            continue

        cc_therapy_id = str(
            cc_invoice_row.get(
                "therapy_plan_reference_id"
            ) or ""
        ).strip()

        cc_media = str(
            cc_invoice_therapy_media.get(
                cc_therapy_id
            ) or ""
        ).strip().lower()

        cc_already_taken = int(
            cc_invoice_therapy_already_taken.get(
                cc_therapy_id
            ) or 0
        )

        # FINAL CC DASHBOARD QUALIFICATION:
        # 1) Sales Invoice must link to Therapy Plan
        # 2) Therapy Plan.media must be "Call Center"
        # 3) Therapy Plan.therapy_plan_already_taken_ must be 0
        #
        # Existing/execution customer packages are marked by
        # therapy_plan_already_taken_ = 1 and must be excluded.
        if (
            not cc_therapy_id
            or cc_media != "call center"
            or cc_already_taken == 1
        ):
            continue

        # Agent login: exact CC Invoice rows/totals are self-only.
        if is_agent_login and owner_filter:
            cc_invoice_meta = (
                cc_invoice_meta_by_invoice.get(
                    cc_invoice_name
                )
                or {}
            )

            cc_invoice_owner = str(
                cc_invoice_meta.get(
                    "lead_owner"
                ) or ""
            ).strip().lower()

            cc_owner_filter_normalized = str(
                owner_filter
            ).strip().lower()

            if (
                not cc_invoice_owner
                or cc_invoice_owner
                != cc_owner_filter_normalized
            ):
                continue

        cc_branch = str(
            cc_invoice_row.get("branch") or ""
        ).strip()

        if not cc_branch:
            cc_branch = "Branch Not Available"

        cc_invoice_date = str(
            cc_invoice_row.get("posting_date") or ""
        ).strip()[:10]

        cc_with_gst = positive_number(
            cc_invoice_row.get("grand_total")
        )

        cc_without_gst = positive_number(
            cc_invoice_row.get("net_total")
        )

        if cc_without_gst <= 0:
            cc_without_gst = positive_number(
                cc_invoice_row.get("total")
            )

        cc_paid = positive_number(
            cc_invoice_paid_by_invoice.get(
                cc_invoice_name
            )
        )

        cc_balance = positive_number(
            cc_invoice_row.get(
                "outstanding_amount"
            )
        )

        # Paid With GST is the actual Payment Entry Reference allocation.
        # Paid Without GST uses this invoice's actual Net Total / Grand Total ratio.
        cc_paid_without_tax = (
            paid_without_gst_amount(
                cc_paid,
                cc_with_gst,
                cc_without_gst
            )
        )

        cc_tax_amount = round(
            cc_paid
            - cc_paid_without_tax,
            2
        )

        cc_outstanding_collected = positive_number(
            cc_invoice_outstanding_by_invoice.get(
                cc_invoice_name
            )
        )

        cc_report_row = {
            "invoice": cc_invoice_name,
            "invoice_date": cc_invoice_date,
            "branch": cc_branch,
            "customer": str(
                cc_invoice_row.get("customer") or ""
            ).strip(),
            "therapy_plan": cc_therapy_id,
            "therapy_plan_media": str(
                cc_invoice_therapy_media.get(
                    cc_therapy_id
                ) or ""
            ).strip(),
            "therapy_plan_already_taken": int(
                cc_invoice_therapy_already_taken.get(
                    cc_therapy_id
                ) or 0
            ),
            "lead": str(
                (
                    cc_invoice_meta_by_invoice.get(
                        cc_invoice_name
                    )
                    or {}
                ).get("lead") or ""
            ).strip(),
            "lead_name": str(
                (
                    cc_invoice_meta_by_invoice.get(
                        cc_invoice_name
                    )
                    or {}
                ).get("lead_name") or ""
            ).strip(),
            "lead_owner": str(
                (
                    cc_invoice_meta_by_invoice.get(
                        cc_invoice_name
                    )
                    or {}
                ).get("lead_owner") or ""
            ).strip(),
            "source": str(
                (
                    cc_invoice_meta_by_invoice.get(
                        cc_invoice_name
                    )
                    or {}
                ).get("source") or ""
            ).strip(),
            "ad_set": str(
                (
                    cc_invoice_meta_by_invoice.get(
                        cc_invoice_name
                    )
                    or {}
                ).get("ad_set") or ""
            ).strip(),
            "enquired_for": str(
                (
                    cc_invoice_meta_by_invoice.get(
                        cc_invoice_name
                    )
                    or {}
                ).get("enquired_for") or ""
            ).strip(),
            "campaign_name": str(
                (
                    cc_invoice_meta_by_invoice.get(
                        cc_invoice_name
                    )
                    or {}
                ).get("campaign_name") or ""
            ).strip(),
            "lead_branch": str(
                (
                    cc_invoice_meta_by_invoice.get(
                        cc_invoice_name
                    )
                    or {}
                ).get("lead_branch") or ""
            ).strip(),
            "with_gst": cc_with_gst,
            "without_gst": cc_without_gst,
            "paid": cc_paid,
            "paid_with_gst": cc_paid,
            "paid_without_gst": cc_paid_without_tax,
            "paid_without_tax": cc_paid_without_tax,
            "tax_amount": cc_tax_amount,
            "balance": cc_balance,
            "outstanding_collected": (
                cc_outstanding_collected
            )
        }

        cc_invoice_report_rows.append(
            cc_report_row
        )

        cc_invoice_report_totals["with_gst"] = (
            positive_number(
                cc_invoice_report_totals.get(
                    "with_gst"
                )
            )
            + cc_with_gst
        )

        cc_invoice_report_totals["without_gst"] = (
            positive_number(
                cc_invoice_report_totals.get(
                    "without_gst"
                )
            )
            + cc_without_gst
        )

        cc_invoice_report_totals["paid"] = (
            positive_number(
                cc_invoice_report_totals.get(
                    "paid"
                )
            )
            + cc_paid
        )

        cc_invoice_report_totals["paid_with_gst"] = (
            positive_number(
                cc_invoice_report_totals.get(
                    "paid_with_gst"
                )
            )
            + cc_paid
        )

        cc_invoice_report_totals["paid_without_gst"] = (
            positive_number(
                cc_invoice_report_totals.get(
                    "paid_without_gst"
                )
            )
            + cc_paid_without_tax
        )

        cc_invoice_report_totals["paid_without_tax"] = (
            positive_number(
                cc_invoice_report_totals.get(
                    "paid_without_tax"
                )
            )
            + cc_paid_without_tax
        )

        cc_invoice_report_totals["tax_amount"] = (
            positive_number(
                cc_invoice_report_totals.get(
                    "tax_amount"
                )
            )
            + cc_tax_amount
        )

        cc_invoice_report_totals["balance"] = (
            positive_number(
                cc_invoice_report_totals.get(
                    "balance"
                )
            )
            + cc_balance
        )

        cc_invoice_report_totals[
            "outstanding_collected"
        ] = (
            positive_number(
                cc_invoice_report_totals.get(
                    "outstanding_collected"
                )
            )
            + cc_outstanding_collected
        )

        cc_invoice_report_totals["invoice_count"] = (
            int(
                cc_invoice_report_totals.get(
                    "invoice_count"
                ) or 0
            )
            + 1
        )


    cc_invoice_report_rows.sort(
        key=lambda row: (
            str(row.get("branch") or ""),
            str(row.get("invoice") or "")
        )
    )

    cc_invoice_report_summary = {
        "from_date": from_date,
        "to_date": to_date,
        "package_filter": (
            "STRICT: Therapy Plan.media = Call Center "
            "AND therapy_plan_already_taken_ = 0"
        ),
        "strict_call_center_only": True,
        "exclude_existing_packages": True,
        "excluded_non_call_center_packages": True,
        "agent_login_self_only": (
            True if is_agent_login else False
        ),
        "effective_owner": (
            owner_filter if is_agent_login else ""
        ),
        "call_center_invoice_count": len(
            cc_invoice_report_rows
        ),
        "rows": cc_invoice_report_rows,
        "payment_rows": (
            cc_invoice_report_payment_rows
        ),
        "totals": cc_invoice_report_totals
    }


    # ------------------------------------------------
    # FINANCIAL EVENT OWNER SCOPE
    #
    # Appointment rows and financial events must use the same Agent.
    # This prevents a selected Agent from showing zero appointment
    # counts while amounts from another Agent are still visible.
    # ------------------------------------------------

    if owner_filter:
        normalized_owner_filter = str(
            owner_filter
        ).strip().lower()

        scoped_financial_events = []

        for financial_event in financial_events:
            financial_owner = str(
                financial_event.get(
                    "lead_owner"
                ) or ""
            ).strip().lower()

            if financial_owner == normalized_owner_filter:
                scoped_financial_events.append(
                    financial_event
                )

        financial_events = scoped_financial_events


    # ------------------------------------------------
    # FINAL AUTHORITATIVE AGENT REPORT
    #
    # COUNTS:
    #   selected Lead Owner
    #   + Lead.custom_appointment_date_and_time inside From / To
    #
    # MONEY:
    #   exact CC Invoice Report rule
    #   + submitted Payment Entry posting_date inside From / To
    #   + Payment Entry Reference -> Sales Invoice
    #   + Therapy Plan.media = "Call Center"
    #   + Patient.custom_lead -> selected Lead Owner
    # ------------------------------------------------

    def report_status_key(value):
        text = str(value or "").strip().lower()

        for separator in ["–", "—", "_", "-", "/"]:
            text = text.replace(separator, " ")

        text = " ".join(text.split())

        if text in [
            "visited booked",
            "visited and booked",
            "booked visited",
            "booked and visited"
        ]:
            return "booked"

        if text in [
            "visited not booked",
            "visited and not booked",
            "visited unbooked",
            "not booked visited"
        ]:
            return "not_booked"

        if text == "visited":
            return "visited"

        if text in [
            "not visited",
            "no show",
            "no visit",
            "did not visit"
        ]:
            return "not_visited"

        if text in [
            "booked",
            "appointment booked",
            "scheduled",
            "appointment scheduled",
            "confirmed",
            "re confirm",
            "reconfirmed",
            "awaiting visit",
            "open",
            "pending"
        ]:
            return "scheduled"

        if text in [
            "not booked",
            "unbooked",
            "appointment not booked"
        ]:
            return "not_booked_no_visit"

        if text in [
            "cancelled",
            "canceled",
            "appointment cancelled",
            "appointment canceled"
        ]:
            return "cancelled"

        return "other"


    report_owner = str(
        owner_filter or requested_agent or ""
    ).strip().lower()

    report_counts = {
        "appointments": 0,
        "visited": 0,
        "booked": 0,
        "not_booked": 0,
        "not_visited": 0,
        "scheduled": 0,
        "not_booked_no_visit": 0,
        "cancelled": 0,
        "other": 0,
        "total_visited": 0,
        "booking_percent": 0
    }

    report_branch_map = {}

    def get_report_branch(branch_name):
        branch_name = str(branch_name or "").strip()

        if not branch_name:
            branch_name = "Branch Not Available"

        if branch_name not in report_branch_map:
            report_branch_map[branch_name] = {
                "branch": branch_name,
                "appointments": 0,
                "visited": 0,
                "booked": 0,
                "not_booked": 0,
                "not_visited": 0,
                "scheduled": 0,
                "not_booked_no_visit": 0,
                "cancelled": 0,
                "other": 0,
                "total_visited": 0,
                "booking_percent": 0,
                "with_gst": 0,
                "without_gst": 0,
                "paid": 0,
                "outstanding_collected": 0,
                "balance": 0
            }

        return report_branch_map[branch_name]


    # Exact appointment counts.
    for lead_row in final_rows:
        lead_owner_value = str(
            lead_row.get("lead_owner") or ""
        ).strip().lower()

        if report_owner and lead_owner_value != report_owner:
            continue

        appointment_datetime = str(
            lead_row.get(
                "custom_appointment_date_and_time"
            ) or ""
        ).strip()

        if not appointment_datetime:
            continue

        appointment_date = appointment_datetime[:10]

        if (
            appointment_date < from_date
            or appointment_date > to_date
        ):
            continue

        status_key = report_status_key(
            lead_row.get("custom_appointment_status")
            or lead_row.get("status")
        )

        report_counts["appointments"] = (
            int(report_counts.get("appointments") or 0) + 1
        )

        report_counts[status_key] = (
            int(report_counts.get(status_key) or 0) + 1
        )

        branch_row = get_report_branch(
            # Current branch selected on Lead doctype.
            lead_row.get("branch")
            or lead_row.get("lead_assign_to_branch")
        )

        branch_row["appointments"] = (
            int(branch_row.get("appointments") or 0) + 1
        )

        branch_row[status_key] = (
            int(branch_row.get(status_key) or 0) + 1
        )


    report_counts["total_visited"] = (
        int(report_counts.get("booked") or 0)
        + int(report_counts.get("not_booked") or 0)
        + int(report_counts.get("visited") or 0)
    )

    if report_counts["total_visited"] > 0:
        report_counts["booking_percent"] = int(
            round(
                float(report_counts.get("booked") or 0)
                / float(report_counts["total_visited"])
                * 100
            )
        )


    # Therapy Plan.media = Call Center.
    therapy_ids = []

    for event in financial_events:
        therapy_id = str(
            event.get("therapy_plan") or ""
        ).strip()

        if therapy_id and therapy_id not in therapy_ids:
            therapy_ids.append(therapy_id)

    therapy_media_map = {}

    if therapy_ids:
        therapy_rows = frappe.get_all(
            "Therapy Plan",
            fields=[
                "name",
                "media"
            ],
            filters=[
                [
                    "name",
                    "in",
                    therapy_ids
                ]
            ],
            limit_page_length=20000
        )

        for therapy_row in therapy_rows:
            therapy_media_map[
                str(therapy_row.get("name") or "").strip()
            ] = str(
                therapy_row.get("media") or ""
            ).strip().lower()


    report_financial = {
        "with_gst": 0,
        "without_gst": 0,
        "paid": 0,
        "outstanding_collected": 0,
        "balance": 0,
        "invoice_count": 0
    }

    report_invoice_seen = {}

    for event in financial_events:
        event_owner = str(
            event.get("lead_owner") or ""
        ).strip().lower()

        if report_owner and event_owner != report_owner:
            continue

        therapy_id = str(
            event.get("therapy_plan") or ""
        ).strip()

        if str(
            therapy_media_map.get(therapy_id) or ""
        ).strip().lower() != "call center":
            continue

        pe_paid = positive_number(
            event.get("pe_paid_amount")
        )

        # Exact CC Invoice Report: only submitted PE allocations.
        if pe_paid <= 0:
            continue

        invoice_name = str(
            event.get("sales_invoice") or ""
        ).strip()

        invoice_date = str(
            event.get("invoice_date") or ""
        ).strip()[:10]

        branch_row = get_report_branch(
            event.get("lead_branch")
            or event.get("branch")
        )

        report_financial["paid"] = (
            float(report_financial.get("paid") or 0)
            + pe_paid
        )

        branch_row["paid"] = (
            float(branch_row.get("paid") or 0)
            + pe_paid
        )

        if invoice_date and invoice_date < from_date:
            report_financial["outstanding_collected"] = (
                float(
                    report_financial.get(
                        "outstanding_collected"
                    ) or 0
                )
                + pe_paid
            )

            branch_row["outstanding_collected"] = (
                float(
                    branch_row.get(
                        "outstanding_collected"
                    ) or 0
                )
                + pe_paid
            )

        if invoice_name and not report_invoice_seen.get(invoice_name):
            report_invoice_seen[invoice_name] = True

            with_gst = positive_number(
                event.get("report_grand_total")
            )

            without_gst = positive_number(
                event.get("report_net_total")
            )

            balance = positive_number(
                event.get("current_outstanding")
            )

            report_financial["with_gst"] = (
                float(report_financial.get("with_gst") or 0)
                + with_gst
            )

            report_financial["without_gst"] = (
                float(report_financial.get("without_gst") or 0)
                + without_gst
            )

            report_financial["balance"] = (
                float(report_financial.get("balance") or 0)
                + balance
            )

            report_financial["invoice_count"] = (
                int(report_financial.get("invoice_count") or 0) + 1
            )

            branch_row["with_gst"] = (
                float(branch_row.get("with_gst") or 0)
                + with_gst
            )

            branch_row["without_gst"] = (
                float(branch_row.get("without_gst") or 0)
                + without_gst
            )

            branch_row["balance"] = (
                float(branch_row.get("balance") or 0)
                + balance
            )


    report_branches = []

    for branch_name in sorted(report_branch_map):
        row = report_branch_map[branch_name]

        row["total_visited"] = (
            int(row.get("booked") or 0)
            + int(row.get("not_booked") or 0)
            + int(row.get("visited") or 0)
        )

        if row["total_visited"] > 0:
            row["booking_percent"] = int(
                round(
                    float(row.get("booked") or 0)
                    / float(row["total_visited"])
                    * 100
                )
            )

        report_branches.append(row)


    agent_report_summary = {
        "agent_owner": owner_filter or requested_agent,
        "from_date": from_date,
        "to_date": to_date,
        "counts": report_counts,
        "financial": report_financial,
        "branches": report_branches
    }


    # ------------------------------------------------
    # Aggregate-safe all-agent ranking source
    # ------------------------------------------------
    ranking_rows = frappe.get_all(
        "Lead",
        fields=[
            "name",
            "lead_owner",
            "status",
            "custom_cc_stage",
            "custom_appointment_status",
            "custom_appointment_date_and_time"
        ],
        filters=[
            [
                "custom_appointment_date_and_time",
                "between",
                [
                    date_time_from,
                    date_time_to
                ]
            ],
            [
                "lead_owner",
                "!=",
                ""
            ]
        ],
        order_by=(
            "custom_appointment_date_and_time desc"
        ),
        limit_page_length=20000
    )

    agent_owners = []

    # Ranking rows
    for ranking_row in ranking_rows:
        owner = str(
            ranking_row.get("lead_owner") or ""
        ).strip()

        if owner and owner not in agent_owners:
            agent_owners.append(owner)

    # Financial/payment activity rows
    for financial_event in financial_events:
        owner = str(
            financial_event.get("lead_owner") or ""
        ).strip()

        if owner and owner not in agent_owners:
            agent_owners.append(owner)

    agent_names = {}

    if agent_owners:
        user_rows = frappe.get_all(
            "User",
            fields=[
                "name",
                "full_name"
            ],
            filters={
                "name": [
                    "in",
                    agent_owners
                ]
            },
            limit_page_length=1000
        )

        for user_row in user_rows:
            email = str(
                user_row.get("name") or ""
            ).strip()

            full_name = str(
                user_row.get("full_name") or email
            ).strip()

            if email:
                agent_names[email] = full_name

    # Attach full Agent Name directly to every invoice/payment event.
    for financial_event in financial_events:
        owner = str(
            financial_event.get("lead_owner") or ""
        ).strip()

        agent_name = ""

        if owner:
            agent_name = str(
                agent_names.get(owner) or owner
            ).strip()

        financial_event["agent_name"] = agent_name

    # ------------------------------------------------
    # ALL MARKETING AGENCIES / LEAD SOURCES
    # ------------------------------------------------
    # Marketing Agency in this dashboard is based primarily on Lead.source.
    # Do not build the dropdown only from Leads in the selected date range,
    # because that hides valid Lead Source master values that have no Leads
    # in the current period.
    marketing_agencies = []
    marketing_agency_seen = {}

    lead_source_rows = frappe.get_all(
        "Lead Source",
        fields=[
            "name",
            "source_name"
        ],
        order_by="source_name asc",
        limit_page_length=5000
    )

    for lead_source_row in lead_source_rows:
        agency_value = str(
            lead_source_row.get("name")
            or ""
        ).strip()

        agency_label = str(
            lead_source_row.get("source_name")
            or agency_value
            or ""
        ).strip()

        if (
            agency_value
            and not marketing_agency_seen.get(
                agency_value.lower()
            )
        ):
            marketing_agency_seen[
                agency_value.lower()
            ] = 1

            marketing_agencies.append(
                {
                    "value": agency_value,
                    "label": agency_label or agency_value
                }
            )

    marketing_agencies.sort(
        key=lambda row: str(
            row.get("label")
            or row.get("value")
            or ""
        ).lower()
    )


    frappe.response["message"] = {
        "ok": True,
        "user": user,
        "roles": roles,
        "restricted_to_owner": True if owner_filter else False,
        "requested_agent": requested_agent,
        "strict_agent_cohort": True if requested_agent else False,
        "count": len(final_rows),
        "rows": final_rows,
        "financial_event_count": len(financial_events),
        "financial_events": financial_events,
        "cc_lead_linked_financial_event_count": len(
            [
                row
                for row in financial_events
                if row.get("cc_lead_linked")
            ]
        ),
        "ranking_count": len(ranking_rows),
        "ranking_rows": ranking_rows,
        "agent_names": agent_names,
        "marketing_agencies": marketing_agencies,
        "agent_report_summary": agent_report_summary,
        "cc_invoice_report_summary": cc_invoice_report_summary
    }
