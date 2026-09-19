"""accounts_command_centre_data

Original API: accounts_command_centre_data
Source modified: 2026-09-01 17:30:30.091754
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
    # =====================================================================
    #  SERVER SCRIPT  (type = "API")
    #  Name        : accounts_command_centre_data
    #  Allow Guest : NO
    #
    #  safe_exec SAFE (v2 - NO .format(), no f-strings, no imports):
    #    SQL is assembled with plain string concatenation (+) and every
    #    dynamic value is passed as a bound parameter.
    # =====================================================================

    month  = frappe.form_dict.get("month")
    branch = frappe.form_dict.get("branch")
    from_date = frappe.form_dict.get("from_date")
    to_date   = frappe.form_dict.get("to_date")

    if not branch:
        branch = "ALL"

    # Webpage sends short branch codes. Accounting tables store full Cost Center names.
    BRANCH_CC_MAP = {
        "HO": "Main - LSACPL",
        "MP": "Madhapur - LSACPL",
        "BH": "Banjara Hills - LSACPL",
        "CN": "Chandanagar - LSACPL",
        "CHN": "Chandanagar - LSACPL",
        "SRN": "SR Nagar - LSACPL",
        "HN": "Himayathnagar - LSACPL",
        "DN": "Dilsukhnagar - LSACPL",
        "DSK": "Dilsukhnagar - LSACPL",
        "GB": "Gachibowli - LSACPL",
        "GCB": "Gachibowli - LSACPL",
        "KP": "Kukatpally - LSACPL",
        "VW": "Vijayawada - LSACPL",
        "VJA": "Vijayawada - LSACPL",
        "VZ": "Vizag - LSACPL",
        "NLR": "Nellore - LSACPL"
    }

    branch_code = branch
    branch_cc = branch
    if branch != "ALL":
        mapped_cc = BRANCH_CC_MAP.get(branch)
        if mapped_cc:
            branch_cc = mapped_cc
        if not frappe.db.exists("Cost Center", branch_cc):
            frappe.throw("Unknown branch / Cost Center: " + str(branch))

    # Date range: prefer explicit from/to; fall back to month; else current month
    if from_date and to_date:
        month_start = from_date
        month_end = to_date
    else:
        if not month:
            month = frappe.utils.nowdate()[:7]
        month_start = month + "-01"
        month_end = frappe.utils.get_last_day(month_start)

    use_branch = 0
    if branch != "ALL":
        use_branch = 1

    # 0. Branch master
    branch_rows = _read_sql("""
    SELECT name AS cc, cost_center_name AS label
    FROM `tabCost Center`
    WHERE is_group = 0
    ORDER BY cost_center_name
""", as_dict=True)

    # 1. SALES SUMMARY
    sales_sql = """
    SELECT
        si.cost_center                              AS cc,
        COUNT(DISTINCT si.name)                     AS invoices,
        SUM(si.grand_total)                         AS gross,
        SUM(si.base_net_total)                      AS net,
        SUM(si.grand_total - si.outstanding_amount) AS collected,
        SUM(si.outstanding_amount)                  AS due
    FROM `tabSales Invoice` si
    WHERE si.docstatus = 1
      AND si.posting_date BETWEEN %(ms)s AND %(me)s
"""
    if use_branch:
        sales_sql = sales_sql + " AND si.cost_center = %(branch)s "
    sales_sql = sales_sql + " GROUP BY si.cost_center "
    sales_summary = _read_sql(sales_sql,
        {"ms": month_start, "me": month_end, "branch": branch_cc}, as_dict=True)

    # 2. COLLECTION BY PAYMENT MODE  -> from Payment Entries (Receive)
    mode_sql = """
    SELECT pe.mode_of_payment AS mode, SUM(pe.received_amount) AS amount
    FROM `tabPayment Entry` pe
    WHERE pe.docstatus = 1
      AND pe.payment_type = 'Receive'
      AND pe.posting_date BETWEEN %(ms)s AND %(me)s
"""
    if use_branch:
        mode_sql = mode_sql + " AND pe.cost_center = %(branch)s "
    mode_sql = mode_sql + " GROUP BY pe.mode_of_payment ORDER BY amount DESC "
    mode_summary = _read_sql(mode_sql,
        {"ms": month_start, "me": month_end, "branch": branch_cc}, as_dict=True)

    # 3. CASH COLLECTED per branch  -> from Payment Entries (Receive, Cash),
    #    since Sales Invoice Payment child table is empty in this instance.
    cash_sql = """
    SELECT pe.cost_center AS cc, SUM(pe.received_amount) AS cash_collected
    FROM `tabPayment Entry` pe
    WHERE pe.docstatus = 1
      AND pe.payment_type = 'Receive'
      AND pe.mode_of_payment = 'Cash'
      AND pe.posting_date BETWEEN %(ms)s AND %(me)s
"""
    if use_branch:
        cash_sql = cash_sql + " AND pe.cost_center = %(branch)s "
    cash_sql = cash_sql + " GROUP BY pe.cost_center "
    cash_in = _read_sql(cash_sql,
        {"ms": month_start, "me": month_end, "branch": branch_cc}, as_dict=True)

    # 4. EXPENSES per branch
    exp_sql = """
    SELECT gle.cost_center AS cc, SUM(gle.debit) AS expense
    FROM `tabGL Entry` gle
    INNER JOIN `tabAccount` acc ON acc.name = gle.account
    WHERE gle.is_cancelled = 0
      AND acc.root_type = 'Expense'
      AND gle.posting_date BETWEEN %(ms)s AND %(me)s
"""
    if use_branch:
        exp_sql = exp_sql + " AND gle.cost_center = %(branch)s "
    exp_sql = exp_sql + " GROUP BY gle.cost_center "
    expense_summary = _read_sql(exp_sql,
        {"ms": month_start, "me": month_end, "branch": branch_cc}, as_dict=True)

    # 5. CASH HANDOVER TO HO
    CASH_ACCOUNT_LIKE = "173001%"
    ho_sql = """
    SELECT gle.cost_center AS cc, SUM(gle.credit) AS handover
    FROM `tabGL Entry` gle
    INNER JOIN `tabJournal Entry` je ON je.name = gle.voucher_no
    WHERE gle.is_cancelled = 0
      AND gle.voucher_type = 'Journal Entry'
      AND gle.account LIKE %(cash)s
      AND gle.credit > 0
      AND (je.user_remark LIKE '%%handover%%' OR je.title LIKE '%%Handover%%')
      AND gle.posting_date BETWEEN %(ms)s AND %(me)s
"""
    if use_branch:
        ho_sql = ho_sql + " AND gle.cost_center = %(branch)s "
    ho_sql = ho_sql + " GROUP BY gle.cost_center "
    handover_summary = _read_sql(ho_sql,
        {"cash": CASH_ACCOUNT_LIKE, "ms": month_start, "me": month_end, "branch": branch_cc},
        as_dict=True)

    # 6. SALE BY BOOKING TYPE  -> grouped by invoice status (no custom field)
    bt_sql = """
    SELECT si.status AS bt, SUM(si.grand_total) AS gross
    FROM `tabSales Invoice` si
    WHERE si.docstatus = 1
      AND si.posting_date BETWEEN %(ms)s AND %(me)s
"""
    if use_branch:
        bt_sql = bt_sql + " AND si.cost_center = %(branch)s "
    bt_sql = bt_sql + " GROUP BY si.status ORDER BY gross DESC "
    booktype_summary = _read_sql(bt_sql,
        {"ms": month_start, "me": month_end, "branch": branch_cc}, as_dict=True)

    # 7. PDC / CHEQUE ALERTS
    pdc_rows = _read_sql("""
    SELECT pe.name AS voucher, pe.reference_no AS chq_no,
           pe.reference_date AS chq_date, pe.party_name AS party,
           pe.paid_amount AS amount, pe.paid_from AS bank_account,
           pe.clearance_date AS cleared_on
    FROM `tabPayment Entry` pe
    WHERE pe.docstatus = 1
      AND pe.mode_of_payment IN ('Cheque', 'Bank Draft')
      AND pe.reference_date >= %(ms)s
    ORDER BY pe.reference_date ASC
    LIMIT 100
""", {"ms": month_start}, as_dict=True)

    # 8. HO CASH DEPOSITS
    ho_deposits = _read_sql("""
    SELECT je.posting_date AS d, je.user_remark AS remark,
           je.total_debit AS amount, je.name AS voucher
    FROM `tabJournal Entry` je
    WHERE je.docstatus = 1
      AND je.posting_date BETWEEN %(ms)s AND %(me)s
      AND (je.title LIKE '%%Deposit%%' OR je.user_remark LIKE '%%deposit%%')
    ORDER BY je.posting_date ASC
    LIMIT 100
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # 9. VENDOR PAYABLES
    vendor_rows = _read_sql("""
    SELECT pi.supplier AS vid, sup.supplier_name AS name,
           SUM(pi.outstanding_amount) AS due
    FROM `tabPurchase Invoice` pi
    INNER JOIN `tabSupplier` sup ON sup.name = pi.supplier
    WHERE pi.docstatus = 1 AND pi.outstanding_amount > 0
    GROUP BY pi.supplier, sup.supplier_name
    ORDER BY due DESC
    LIMIT 50
""", as_dict=True)

    # 10. BANK ACCOUNTS + live GL balance (single query, no python loop)
    #     Compute each bank's GL balance inline via a correlated subquery so
    #     we never assign to a dict subscript (safe_exec restriction).
    bank_rows = _read_sql("""
    SELECT ba.name AS id, ba.account_name AS label, ba.account AS gl_account,
           COALESCE((
               SELECT SUM(gle.debit) - SUM(gle.credit)
               FROM `tabGL Entry` gle
               WHERE gle.account = ba.account
                 AND gle.is_cancelled = 0
                 AND gle.posting_date <= %(me)s
           ), 0) AS gl_balance
    FROM `tabBank Account` ba
    WHERE ba.disabled = 0
    ORDER BY ba.account_name
""", {"me": month_end}, as_dict=True)

    # 11. BANK RECONCILIATION
    #     Recent GL entries against bank accounts (clearance tracking lives on
    #     Bank Transaction, not Journal Entry Account, in this instance).
    unrecon_gl = _read_sql("""
    SELECT gle.account AS gl_account, gle.posting_date AS d,
           gle.voucher_type AS vtype, gle.voucher_no AS voucher,
           gle.debit AS debit, gle.credit AS credit, gle.against AS against
    FROM `tabGL Entry` gle
    INNER JOIN `tabAccount` acc ON acc.name = gle.account
    WHERE gle.is_cancelled = 0
      AND acc.account_type = 'Bank'
      AND gle.posting_date BETWEEN %(ms)s AND %(me)s
    ORDER BY gle.posting_date DESC
    LIMIT 200
""", {"ms": month_start, "me": month_end}, as_dict=True)

    unrecon_bank_txn = _read_sql("""
    SELECT bt.name AS txn, bt.date AS d, bt.bank_account AS bank_account,
           bt.description AS description, bt.deposit AS deposit,
           bt.withdrawal AS withdrawal, bt.allocated_amount AS allocated,
           bt.unallocated_amount AS unallocated, bt.status AS status
    FROM `tabBank Transaction` bt
    WHERE bt.docstatus = 1
      AND bt.date BETWEEN %(ms)s AND %(me)s
      AND bt.status != 'Reconciled'
    ORDER BY bt.date DESC
    LIMIT 200
""", {"ms": month_start, "me": month_end}, as_dict=True)

    recon_totals = _read_sql("""
    SELECT bt.bank_account AS bank_account,
           SUM(bt.deposit) AS total_deposit,
           SUM(bt.withdrawal) AS total_withdrawal,
           SUM(bt.unallocated_amount) AS total_unallocated,
           SUM(CASE WHEN bt.status = 'Reconciled' THEN 1 ELSE 0 END) AS reconciled_count,
           SUM(CASE WHEN bt.status != 'Reconciled' THEN 1 ELSE 0 END) AS pending_count
    FROM `tabBank Transaction` bt
    WHERE bt.docstatus = 1 AND bt.date BETWEEN %(ms)s AND %(me)s
    GROUP BY bt.bank_account
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # RESPONSE
    # 6b. CATEGORY-WISE SALES  -> by therapy_type from the therapy child table
    cat_sql = """
    SELECT tpd.therapy_type AS category,
           COUNT(DISTINCT si.name) AS invoices,
           SUM(tpd.no_of_sessions) AS sessions
    FROM `tabTherapy Plan Detail` tpd
    INNER JOIN `tabSales Invoice` si ON si.name = tpd.parent
    WHERE si.docstatus = 1
      AND tpd.parenttype = 'Sales Invoice'
      AND si.posting_date BETWEEN %(ms)s AND %(me)s
"""
    if use_branch:
        cat_sql = cat_sql + " AND si.cost_center = %(branch)s "
    cat_sql = cat_sql + " GROUP BY tpd.therapy_type ORDER BY invoices DESC LIMIT 40 "
    category_sales = _read_sql(cat_sql,
        {"ms": month_start, "me": month_end, "branch": branch_cc}, as_dict=True)

    # 6c. SERVICE-LINE SALES  -> by item income account (Skin/Slimming/Hair..)
    #     amount from Sales Invoice Item net_amount, grouped by income_account.
    line_sql = """
    SELECT sii.income_account AS acc, SUM(sii.net_amount) AS amount,
           COUNT(DISTINCT sii.parent) AS invoices
    FROM `tabSales Invoice Item` sii
    INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
    WHERE si.docstatus = 1
      AND si.posting_date BETWEEN %(ms)s AND %(me)s
"""
    if use_branch:
        line_sql = line_sql + " AND si.cost_center = %(branch)s "
    line_sql = line_sql + " GROUP BY sii.income_account ORDER BY amount DESC LIMIT 40 "
    serviceline_sales = _read_sql(line_sql,
        {"ms": month_start, "me": month_end, "branch": branch_cc}, as_dict=True)

    # 6d. EMPLOYEE-WISE SALES  -> credited to referring name AND/OR incentive
    #     employee. Amount credited = PAID amount after GST, split 50-50 when
    #     both names present, 100% when only one.
    #     Branch filter handled with a param that is a no-op when ALL.
    emp_branch = "%"
    if use_branch:
        emp_branch = branch_cc

    emp_sql = """
    SELECT employee, SUM(share) AS paid_after_gst, COUNT(*) AS invoices
    FROM (
        SELECT
            si.custom_referring_name AS employee,
            (CASE WHEN si.grand_total > 0
                  THEN (si.grand_total - si.outstanding_amount) / si.grand_total * si.base_net_total
                  ELSE 0 END)
            * (CASE WHEN si.custom_referring_name IS NOT NULL
                        AND si.custom_referring_name != ''
                        AND si.custom_incentive_employee_name IS NOT NULL
                        AND si.custom_incentive_employee_name != ''
                    THEN 0.5 ELSE 1 END) AS share
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
          AND si.custom_referring_name IS NOT NULL AND si.custom_referring_name != ''
          AND si.posting_date BETWEEN %(ms)s AND %(me)s
          AND (si.cost_center = %(emp_branch)s OR %(emp_branch)s = '%%')

        UNION ALL

        SELECT
            si.custom_incentive_employee_name AS employee,
            (CASE WHEN si.grand_total > 0
                  THEN (si.grand_total - si.outstanding_amount) / si.grand_total * si.base_net_total
                  ELSE 0 END)
            * (CASE WHEN si.custom_referring_name IS NOT NULL
                        AND si.custom_referring_name != ''
                        AND si.custom_incentive_employee_name IS NOT NULL
                        AND si.custom_incentive_employee_name != ''
                    THEN 0.5 ELSE 1 END) AS share
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
          AND si.custom_incentive_employee_name IS NOT NULL AND si.custom_incentive_employee_name != ''
          AND si.posting_date BETWEEN %(ms)s AND %(me)s
          AND (si.cost_center = %(emp_branch)s OR %(emp_branch)s = '%%')
    ) AS emp_union
    GROUP BY employee
    ORDER BY paid_after_gst DESC
    LIMIT 80
"""
    employee_sales = _read_sql(emp_sql,
        {"ms": month_start, "me": month_end, "emp_branch": emp_branch}, as_dict=True)

    frappe.response["message"] = {
        "meta": {"month": month, "month_start": month_start,
                 "month_end": str(month_end), "branch": branch_code,
                 "cost_center": branch_cc,
                 "generated_at": frappe.utils.now()},
        "branches": branch_rows,
        "sales_summary": sales_summary,
        "mode_summary": mode_summary,
        "cash_in": cash_in,
        "expense_summary": expense_summary,
        "handover_summary": handover_summary,
        "booktype_summary": booktype_summary,
        "category_sales": category_sales,
        "serviceline_sales": serviceline_sales,
        "employee_sales": employee_sales,
        "pdc": pdc_rows,
        "ho_deposits": ho_deposits,
        "vendors": vendor_rows,
        "banks": bank_rows,
        "bank_recon": {"unreconciled_gl": unrecon_gl,
                       "unreconciled_bank_txn": unrecon_bank_txn,
                       "totals": recon_totals}
    }
