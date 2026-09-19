"""life_discount_invoice_report

Original API: life_discount_invoice_report
Source modified: 2026-09-07 20:40:04.179648
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
    # LIFE Discount Invoice Report API
    # Frappe Server Script settings:
    #   Script Type : API
    #   API Method  : life_discount_invoice_report
    #   Allow Guest : No

    # Request parameters:
    #   action          = report | branches
    #   from_date       = YYYY-MM-DD
    #   to_date         = YYYY-MM-DD
    #   branch          = optional Branch name
    #   approval_status = optional Approved / Pending Approval / Rejected
    #   search          = optional invoice/client/mobile search text
    #   page            = default 1
    #   page_length     = default 50, maximum 200
    #   export          = 1 to return up to 5000 rows

    params = frappe.form_dict or {}
    action = (params.get("action") or "report").strip().lower()

    # Restrict this financial report to appropriate roles.
    # frappe.get_roles() is not exposed inside Server Script safe-exec, so roles
    # are checked directly from the standard Has Role table.
    has_access = frappe.session.user == "Administrator"

    if not has_access:
        role_check = _read_sql(
            """
        SELECT COUNT(*) AS role_count
        FROM `tabHas Role`
        WHERE parent = %(user)s
          AND parenttype = 'User'
          AND role IN ('System Manager', 'Accounts Manager', 'Accounts User')
        """,
            {"user": frappe.session.user},
            as_dict=True
        )
        has_access = bool(role_check and role_check[0].role_count)

    if not has_access:
        frappe.throw("You do not have permission to view the Discount Invoice Report.")


    if action == "branches":
        branches = frappe.get_all(
            "Branch",
            filters={"name": ["not in", ["Testing Branch"]]},
            fields=["name"],
            order_by="name asc",
            limit_page_length=500
        )

        frappe.response["message"] = {
            "success": True,
            "branches": [row.name for row in branches]
        }

    else:
        from_date = (params.get("from_date") or "").strip()
        to_date = (params.get("to_date") or "").strip()
        branch = (params.get("branch") or "").strip()
        approval_status = (params.get("approval_status") or "").strip()
        approval_level = (params.get("approval_level") or "").strip()
        search = (params.get("search") or "").strip()
        export_mode = frappe.utils.cint(params.get("export")) == 1

        if not from_date or not to_date:
            frappe.throw("From Date and To Date are required.")

        from_date_obj = frappe.utils.getdate(from_date)
        to_date_obj = frappe.utils.getdate(to_date)

        if from_date_obj > to_date_obj:
            frappe.throw("From Date cannot be after To Date.")

        allowed_statuses = ["", "Approved", "Pending Approval", "Rejected"]
        if approval_status not in allowed_statuses:
            frappe.throw("Invalid approval status.")

        if approval_level not in ["", "L1", "L2", "L3", "L4"]:
            frappe.throw("Invalid approval level.")

        page = max(frappe.utils.cint(params.get("page")) or 1, 1)
        page_length = frappe.utils.cint(params.get("page_length")) or 50
        page_length = min(max(page_length, 10), 200)

        if export_mode:
            page = 1
            page_length = 5000

        offset = (page - 1) * page_length

        values = {
            "from_date": from_date_obj,
            "to_date": to_date_obj,
            "branch": branch,
            "approval_status": approval_status,
            "approval_level": approval_level,
            "search": "%" + search + "%",
            "limit": page_length,
            "offset": offset
        }

        conditions = [
            "si.docstatus = 1",
            "si.is_return = 0",
            "si.posting_date BETWEEN %(from_date)s AND %(to_date)s",
            "IFNULL(si.branch, '') != 'Testing Branch'",
            "(da.invoice_id IS NOT NULL OR IFNULL(si.approver_discount_amount, 0) > 0 OR IFNULL(si.discount_amount, 0) > 0)"
        ]

        if branch:
            conditions.append("si.branch = %(branch)s")

        if approval_status == "Approved":
            conditions.append("IFNULL(da.has_approved, 0) = 1")
        elif approval_status == "Rejected":
            conditions.append("IFNULL(da.has_rejected, 0) = 1")
        elif approval_status == "Pending Approval":
            conditions.append("IFNULL(da.has_pending, 0) = 1")

        if approval_level:
            conditions.append("EXISTS (SELECT 1 FROM `tabDiscount Approval Request` dl WHERE dl.linked_invoice = si.name AND dl.approval_level = %(approval_level)s)")

        if search:
            conditions.append("""(
            si.name LIKE %(search)s
            OR IFNULL(si.patient_name, si.customer_name) LIKE %(search)s
            OR IFNULL(si.contact_mobile, '') LIKE %(search)s
            OR IFNULL(si.custom_referring_name, '') LIKE %(search)s
        )""")

        where_sql = " AND ".join(conditions)

        payment_join = """
        LEFT JOIN (
            SELECT
                per.reference_name AS invoice_id,
                SUM(
                    CASE
                        WHEN pe.payment_type = 'Receive' THEN IFNULL(per.allocated_amount, 0)
                        WHEN pe.payment_type = 'Pay' THEN -IFNULL(per.allocated_amount, 0)
                        ELSE 0
                    END
                ) AS payment_entry_paid,
                GROUP_CONCAT(DISTINCT pe.name ORDER BY pe.posting_date, pe.name SEPARATOR ', ') AS payment_entries,
                MAX(pe.posting_date) AS last_payment_date
            FROM `tabPayment Entry Reference` per
            INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
            WHERE
                pe.docstatus = 1
                AND per.reference_doctype = 'Sales Invoice'
            GROUP BY per.reference_name
        ) pay ON pay.invoice_id = si.name
    """

        approval_join = """
        LEFT JOIN (
            SELECT
                dar.linked_invoice AS invoice_id,
                GROUP_CONCAT(
                    DISTINCT CONCAT(
                        IFNULL(dar.approval_level, 'Approval'),
                        ' - ',
                        IFNULL(NULLIF(u.full_name, ''), IFNULL(NULLIF(dar.approved_by, ''), IFNULL(dar.selected_approver, 'Not Assigned'))),
                        ' (', IFNULL(dar.status, 'Unknown'), ')'
                    )
                    ORDER BY dar.approved_at, dar.approval_level
                    SEPARATOR ', '
                ) AS approved_by_names,
                GROUP_CONCAT(
                    DISTINCT CONCAT(
                        IFNULL(dar.approval_level, 'Approval'),
                        ': ',
                        FORMAT(IFNULL(dar.approved_discount_pct, 0), 2),
                        '%% - ', IFNULL(dar.status, 'Unknown')
                    )
                    ORDER BY dar.approved_at, dar.approval_level
                    SEPARATOR ', '
                ) AS approval_breakup,
                MAX(IFNULL(dar.bill_total, 0)) AS approval_base_amount,
                MAX(CASE WHEN dar.status = 'Approved' THEN 1 ELSE 0 END) AS has_approved,
                MAX(CASE WHEN dar.status = 'Rejected' THEN 1 ELSE 0 END) AS has_rejected,
                MAX(CASE WHEN dar.status = 'Pending' THEN 1 ELSE 0 END) AS has_pending,
                MAX(IFNULL(dar.approved_at, dar.modified)) AS latest_approval_at,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(dar.status ORDER BY IFNULL(dar.approved_at, dar.modified) DESC SEPARATOR ','),
                    ',', 1
                ) AS latest_status
            FROM `tabDiscount Approval Request` dar
            LEFT JOIN `tabUser` u ON u.name = IFNULL(NULLIF(dar.approved_by, ''), dar.selected_approver)
            GROUP BY dar.linked_invoice
        ) da ON da.invoice_id = si.name
    """

        # The live Discount Approval Request link field is `linked_invoice`.

        data_sql = """
        SELECT SQL_CALC_FOUND_ROWS
            si.name AS sales_invoice,
            si.posting_date AS invoice_date,
            si.branch,
            COALESCE(NULLIF(si.patient_name, ''), NULLIF(si.customer_name, ''), si.customer) AS client_name,
            CASE
                WHEN LENGTH(REPLACE(REPLACE(IFNULL(si.contact_mobile, ''), ' ', ''), '-', '')) >= 6
                THEN CONCAT(
                    LEFT(REPLACE(REPLACE(si.contact_mobile, ' ', ''), '-', ''), 3),
                    '****',
                    RIGHT(REPLACE(REPLACE(si.contact_mobile, ' ', ''), '-', ''), 3)
                )
                WHEN IFNULL(si.contact_mobile, '') != '' THEN '******'
                ELSE ''
            END AS masked_mobile,
            IFNULL(si.contact_mobile, '') AS mobile_number,
            IFNULL(si.custom_referring_name, '') AS referring_name,
            ROUND(
                CASE
                    WHEN IFNULL(si.original_bill_total, 0) > 0 THEN si.original_bill_total * 1.05
                    WHEN IFNULL(da.approval_base_amount, 0) > 0 THEN da.approval_base_amount
                    ELSE IFNULL(si.grand_total, 0) + COALESCE(NULLIF(si.approver_discount_amount, 0), NULLIF(si.discount_amount, 0), 0)
                END,
                2
            ) AS original_bill_total,
            ROUND(IFNULL(si.grand_total, 0), 2) AS grand_total,
            ROUND(
                CASE
                    WHEN IFNULL(pay.payment_entry_paid, 0) != 0 THEN pay.payment_entry_paid
                    ELSE GREATEST(IFNULL(si.grand_total, 0) - IFNULL(si.outstanding_amount, 0), 0)
                END,
                2
            ) AS paid_amount,
            ROUND(
                COALESCE(
                    NULLIF(si.approver_discount_amount, 0),
                    NULLIF(si.discount_amount, 0),
                    GREATEST(IFNULL(da.approval_base_amount, 0) - IFNULL(si.grand_total, 0), 0),
                    0
                ),
                2
            ) AS discount_used,
            ROUND(IFNULL(si.total_approver_discount_pct, 0), 2) AS discount_percentage,
            IFNULL(da.approved_by_names, '') AS approved_by,
            IFNULL(da.approval_breakup, '') AS approval_breakup,
            CASE WHEN da.latest_status = 'Pending' THEN 'Pending Approval'
                 ELSE COALESCE(da.latest_status, NULLIF(si.approval_workflow_status, ''), '') END AS approval_status,
            da.latest_approval_at,
            ROUND(IFNULL(si.outstanding_amount, 0), 2) AS outstanding_amount,
            IFNULL(pay.payment_entries, '') AS payment_entries,
            pay.last_payment_date
        FROM `tabSales Invoice` si
    """ + payment_join + approval_join + """
        WHERE """ + where_sql + """
        ORDER BY si.posting_date DESC, si.creation DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """

        rows = _read_sql(data_sql, values, as_dict=True)
        total_rows = _read_sql("SELECT FOUND_ROWS() AS total", as_dict=True)[0].total

        summary_sql = """
        SELECT
            COUNT(si.name) AS invoice_count,
            ROUND(SUM(
                CASE
                    WHEN IFNULL(si.original_bill_total, 0) > 0 THEN si.original_bill_total * 1.05
                    WHEN IFNULL(da.approval_base_amount, 0) > 0 THEN da.approval_base_amount
                    ELSE IFNULL(si.grand_total, 0) + COALESCE(NULLIF(si.approver_discount_amount, 0), NULLIF(si.discount_amount, 0), 0)
                END
            ), 2) AS total_original_bill,
            ROUND(SUM(IFNULL(si.grand_total, 0)), 2) AS total_grand_total,
            ROUND(SUM(
                CASE
                    WHEN IFNULL(pay.payment_entry_paid, 0) != 0 THEN pay.payment_entry_paid
                    ELSE GREATEST(IFNULL(si.grand_total, 0) - IFNULL(si.outstanding_amount, 0), 0)
                END
            ), 2) AS total_paid,
            ROUND(SUM(
                COALESCE(
                    NULLIF(si.approver_discount_amount, 0),
                    NULLIF(si.discount_amount, 0),
                    GREATEST(IFNULL(da.approval_base_amount, 0) - IFNULL(si.grand_total, 0), 0),
                    0
                )
            ), 2) AS total_discount,
            ROUND(SUM(IFNULL(si.outstanding_amount, 0)), 2) AS total_outstanding
        FROM `tabSales Invoice` si
    """ + payment_join + approval_join + """
        WHERE """ + where_sql

        summary_rows = _read_sql(summary_sql, values, as_dict=True)
        summary = summary_rows[0] if summary_rows else {}

        frappe.response["message"] = {
            "success": True,
            "data": rows,
            "summary": summary,
            "pagination": {
                "page": page,
                "page_length": page_length,
                "total_rows": total_rows,
                "total_pages": max((total_rows + page_length - 1) // page_length, 1)
            },
            "filters": {
                "from_date": str(from_date_obj),
                "to_date": str(to_date_obj),
                "branch": branch,
                "approval_status": approval_status,
                "approval_level": approval_level,
                "search": search
            }
        }
