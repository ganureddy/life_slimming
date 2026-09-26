"""accounts_command_centre_procurement

Original API: accounts_command_centre_procurement
Source modified: 2026-07-31 13:16:54.060930
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
    #  Name        : accounts_command_centre_procurement
    #  Allow Guest : NO
    #
    #  Full ACCOUNTS-MODULE live data: Suppliers, Purchase Invoices,
    #  Purchase Orders, Payment Entries, Journal Entries, Cost Centers,
    #  AP ageing, GL activity.
    #
    #  safe_exec SAFE: no .format(), no f-strings, no imports.
    #  All dynamic values are bound parameters; period filter via + concat.
    # =====================================================================

    month  = frappe.form_dict.get("month")
    from_date = frappe.form_dict.get("from_date")
    to_date   = frappe.form_dict.get("to_date")

    if from_date and to_date:
        month_start = from_date
        month_end = to_date
    else:
        if not month:
            month = frappe.utils.nowdate()[:7]
        month_start = month + "-01"
        month_end = frappe.utils.get_last_day(month_start)
    today       = frappe.utils.nowdate()

    # ---------------------------------------------------------------------
    # 1. COST CENTERS (branch master with company)
    # ---------------------------------------------------------------------
    cost_centers = _read_sql("""
    SELECT cc.name AS cc, cc.cost_center_name AS label,
           cc.is_group AS is_group, cc.company AS company,
           cc.parent_cost_center AS parent
    FROM `tabCost Center` cc
    ORDER BY cc.is_group DESC, cc.cost_center_name
""", as_dict=True)

    # ---------------------------------------------------------------------
    # 2. SUPPLIER SUMMARY (masters + type breakdown)
    # ---------------------------------------------------------------------
    supplier_counts = _read_sql("""
    SELECT COALESCE(supplier_type, 'Unknown') AS stype,
           COUNT(*) AS cnt
    FROM `tabSupplier`
    WHERE disabled = 0
    GROUP BY COALESCE(supplier_type, 'Unknown')
    ORDER BY cnt DESC
""", as_dict=True)

    supplier_total = _read_sql("""
    SELECT COUNT(*) AS total FROM `tabSupplier` WHERE disabled = 0
""", as_dict=True)

    # ---------------------------------------------------------------------
    # 3. ACCOUNTS PAYABLE - outstanding by supplier (top 50)
    # ---------------------------------------------------------------------
    ap_by_supplier = _read_sql("""
    SELECT pi.supplier AS vid, sup.supplier_name AS name,
           COUNT(DISTINCT pi.name) AS bills,
           SUM(pi.grand_total) AS billed,
           SUM(pi.outstanding_amount) AS due
    FROM `tabPurchase Invoice` pi
    INNER JOIN `tabSupplier` sup ON sup.name = pi.supplier
    WHERE pi.docstatus = 1 AND pi.outstanding_amount > 0
    GROUP BY pi.supplier, sup.supplier_name
    ORDER BY due DESC
    LIMIT 50
""", as_dict=True)

    # ---------------------------------------------------------------------
    # 4. AP AGEING BUCKETS (by due_date vs today)
    # ---------------------------------------------------------------------
    ap_ageing = _read_sql("""
    SELECT
        SUM(CASE WHEN DATEDIFF(%(td)s, pi.due_date) <= 0 THEN pi.outstanding_amount ELSE 0 END) AS not_due,
        SUM(CASE WHEN DATEDIFF(%(td)s, pi.due_date) BETWEEN 1 AND 30 THEN pi.outstanding_amount ELSE 0 END) AS d1_30,
        SUM(CASE WHEN DATEDIFF(%(td)s, pi.due_date) BETWEEN 31 AND 60 THEN pi.outstanding_amount ELSE 0 END) AS d31_60,
        SUM(CASE WHEN DATEDIFF(%(td)s, pi.due_date) BETWEEN 61 AND 90 THEN pi.outstanding_amount ELSE 0 END) AS d61_90,
        SUM(CASE WHEN DATEDIFF(%(td)s, pi.due_date) > 90 THEN pi.outstanding_amount ELSE 0 END) AS d90_plus,
        SUM(pi.outstanding_amount) AS total_due
    FROM `tabPurchase Invoice` pi
    WHERE pi.docstatus = 1 AND pi.outstanding_amount > 0
""", {"td": today}, as_dict=True)

    # ---------------------------------------------------------------------
    # 5. PURCHASE INVOICES this month (list + status split)
    # ---------------------------------------------------------------------
    pi_list = _read_sql("""
    SELECT pi.name AS voucher, pi.supplier AS vid, pi.supplier_name AS name,
           pi.posting_date AS d, pi.due_date AS due, pi.bill_no AS bill_no,
           pi.net_total AS without_gst, pi.total_taxes_and_charges AS gst,
           pi.grand_total AS total, pi.outstanding_amount AS due_amt,
           pi.status AS status, pi.cost_center AS cc
    FROM `tabPurchase Invoice` pi
    WHERE pi.docstatus = 1
      AND pi.posting_date BETWEEN %(ms)s AND %(me)s
    ORDER BY pi.posting_date DESC
    LIMIT 300
""", {"ms": month_start, "me": month_end}, as_dict=True)

    pi_status = _read_sql("""
    SELECT pi.status AS status, COUNT(*) AS cnt,
           SUM(pi.grand_total) AS total
    FROM `tabPurchase Invoice` pi
    WHERE pi.docstatus = 1
      AND pi.posting_date BETWEEN %(ms)s AND %(me)s
    GROUP BY pi.status
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # ---------------------------------------------------------------------
    # 6. PURCHASE ORDERS (open + status split)
    # ---------------------------------------------------------------------
    po_list = _read_sql("""
    SELECT po.name AS voucher, po.supplier AS vid, po.supplier_name AS name,
           po.transaction_date AS d, po.grand_total AS total,
           po.status AS status, po.per_received AS pct_recd,
           po.per_billed AS pct_billed
    FROM `tabPurchase Order` po
    WHERE po.docstatus = 1
      AND po.status NOT IN ('Closed', 'Completed')
    ORDER BY po.transaction_date DESC
    LIMIT 200
""", as_dict=True)

    po_status = _read_sql("""
    SELECT po.status AS status, COUNT(*) AS cnt,
           SUM(po.grand_total) AS total
    FROM `tabPurchase Order` po
    WHERE po.docstatus = 1
    GROUP BY po.status
""", as_dict=True)

    # ---------------------------------------------------------------------
    # 7. PAYMENT ENTRIES this month (in / out split)
    # ---------------------------------------------------------------------
    pe_list = _read_sql("""
    SELECT pe.name AS voucher, pe.payment_type AS ptype,
           pe.party_type AS party_type, pe.party_name AS party,
           pe.posting_date AS d, pe.paid_amount AS paid,
           pe.received_amount AS received,
           pe.paid_amount_after_tax AS paid_after_tax,
           pe.received_amount_after_tax AS recd_after_tax,
           pe.total_taxes_and_charges AS taxes,
           pe.custom_bajaj_card_charges_amount AS card_charges,
           pe.mode_of_payment AS mode,
           pe.reference_no AS ref_no, pe.reference_date AS ref_date,
           pe.clearance_date AS cleared, pe.cost_center AS cc
    FROM `tabPayment Entry` pe
    WHERE pe.docstatus = 1
      AND pe.posting_date BETWEEN %(ms)s AND %(me)s
    ORDER BY pe.posting_date DESC
    LIMIT 300
""", {"ms": month_start, "me": month_end}, as_dict=True)

    pe_summary = _read_sql("""
    SELECT pe.payment_type AS ptype, COUNT(*) AS cnt,
           SUM(pe.paid_amount) AS total
    FROM `tabPayment Entry` pe
    WHERE pe.docstatus = 1
      AND pe.posting_date BETWEEN %(ms)s AND %(me)s
    GROUP BY pe.payment_type
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # ---------------------------------------------------------------------
    # 8. JOURNAL ENTRIES this month (by type)
    # ---------------------------------------------------------------------
    je_list = _read_sql("""
    SELECT je.name AS voucher, je.voucher_type AS vtype,
           je.posting_date AS d, je.total_debit AS amount,
           je.title AS title, je.user_remark AS remark
    FROM `tabJournal Entry` je
    WHERE je.docstatus = 1
      AND je.posting_date BETWEEN %(ms)s AND %(me)s
    ORDER BY je.posting_date DESC
    LIMIT 300
""", {"ms": month_start, "me": month_end}, as_dict=True)

    je_summary = _read_sql("""
    SELECT je.voucher_type AS vtype, COUNT(*) AS cnt,
           SUM(je.total_debit) AS total
    FROM `tabJournal Entry` je
    WHERE je.docstatus = 1
      AND je.posting_date BETWEEN %(ms)s AND %(me)s
    GROUP BY je.voucher_type
    ORDER BY total DESC
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # ---------------------------------------------------------------------
    # 9. PURCHASE SPEND by cost center (PI with cost center set)
    # ---------------------------------------------------------------------
    spend_by_cc = _read_sql("""
    SELECT COALESCE(pi.cost_center, 'Unassigned') AS cc,
           COUNT(*) AS bills,
           SUM(pi.net_total) AS without_gst,
           SUM(pi.total_taxes_and_charges) AS gst,
           SUM(pi.grand_total) AS spend
    FROM `tabPurchase Invoice` pi
    WHERE pi.docstatus = 1
      AND pi.posting_date BETWEEN %(ms)s AND %(me)s
    GROUP BY COALESCE(pi.cost_center, 'Unassigned')
    ORDER BY spend DESC
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # ---------------------------------------------------------------------
    # 9b. DAY-WISE BOOK: Payment Entries grouped by date -> branch -> mode
    #     (cost_center holds the branch, e.g. 'Vizag - LSACPL')
    # ---------------------------------------------------------------------
    daybook = _read_sql("""
    SELECT pe.posting_date AS d,
           COALESCE(pe.cost_center, 'Unassigned') AS cc,
           pe.mode_of_payment AS mode,
           pe.payment_type AS ptype,
           COUNT(*) AS cnt,
           SUM(CASE WHEN pe.payment_type='Receive' THEN pe.received_amount ELSE 0 END) AS received,
           SUM(CASE WHEN pe.payment_type='Pay' THEN pe.paid_amount ELSE 0 END) AS paid
    FROM `tabPayment Entry` pe
    WHERE pe.docstatus = 1
      AND pe.posting_date BETWEEN %(ms)s AND %(me)s
    GROUP BY pe.posting_date, COALESCE(pe.cost_center, 'Unassigned'),
             pe.mode_of_payment, pe.payment_type
    ORDER BY pe.posting_date DESC, cc, mode
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # day-wise collection totals per branch (Receive only), for summary
    daybook_branch = _read_sql("""
    SELECT COALESCE(pe.cost_center, 'Unassigned') AS cc,
           SUM(CASE WHEN pe.mode_of_payment='Cash' THEN pe.received_amount ELSE 0 END) AS cash,
           SUM(CASE WHEN pe.mode_of_payment!='Cash' THEN pe.received_amount ELSE 0 END) AS noncash,
           SUM(pe.received_amount) AS total_recd
    FROM `tabPayment Entry` pe
    WHERE pe.docstatus = 1
      AND pe.payment_type = 'Receive'
      AND pe.posting_date BETWEEN %(ms)s AND %(me)s
    GROUP BY COALESCE(pe.cost_center, 'Unassigned')
    ORDER BY total_recd DESC
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # ---------------------------------------------------------------------
    # 9c. HO CASH HANDOVER: Journal Entries titled 'Cash-Hitech' — branch
    #     cash handed to Head Office. custom_branch holds the branch cleanly.
    # ---------------------------------------------------------------------
    ho_handover = _read_sql("""
    SELECT je.name AS voucher, je.posting_date AS d,
           je.title AS title, je.custom_branch AS branch,
           je.total_debit AS amount, je.user_remark AS remark
    FROM `tabJournal Entry` je
    WHERE je.docstatus = 1
      AND je.title LIKE '%%Cash-Hitech%%'
      AND je.posting_date BETWEEN %(ms)s AND %(me)s
    ORDER BY je.posting_date DESC
    LIMIT 300
""", {"ms": month_start, "me": month_end}, as_dict=True)

    ho_handover_total = _read_sql("""
    SELECT COALESCE(SUM(je.total_debit),0) AS total, COUNT(*) AS cnt
    FROM `tabJournal Entry` je
    WHERE je.docstatus = 1
      AND je.title LIKE '%%Cash-Hitech%%'
      AND je.posting_date BETWEEN %(ms)s AND %(me)s
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # handover by branch (for branch-wise summary)
    ho_by_branch = _read_sql("""
    SELECT COALESCE(je.custom_branch, 'Unknown') AS branch,
           COUNT(*) AS cnt, SUM(je.total_debit) AS amount
    FROM `tabJournal Entry` je
    WHERE je.docstatus = 1
      AND je.title LIKE '%%Cash-Hitech%%'
      AND je.posting_date BETWEEN %(ms)s AND %(me)s
    GROUP BY COALESCE(je.custom_branch, 'Unknown')
    ORDER BY amount DESC
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # ---------------------------------------------------------------------
    # 10. MONTH TOTALS (headline KPIs)
    # ---------------------------------------------------------------------
    totals = _read_sql("""
    SELECT
        (SELECT COALESCE(SUM(net_total),0) FROM `tabPurchase Invoice`
         WHERE docstatus=1 AND posting_date BETWEEN %(ms)s AND %(me)s) AS pi_without_gst,
        (SELECT COALESCE(SUM(total_taxes_and_charges),0) FROM `tabPurchase Invoice`
         WHERE docstatus=1 AND posting_date BETWEEN %(ms)s AND %(me)s) AS pi_gst,
        (SELECT COALESCE(SUM(grand_total),0) FROM `tabPurchase Invoice`
         WHERE docstatus=1 AND posting_date BETWEEN %(ms)s AND %(me)s) AS pi_total,
        (SELECT COALESCE(SUM(outstanding_amount),0) FROM `tabPurchase Invoice`
         WHERE docstatus=1 AND outstanding_amount>0) AS ap_total,
        (SELECT COALESCE(SUM(grand_total),0) FROM `tabPurchase Order`
         WHERE docstatus=1 AND status NOT IN ('Closed','Completed')) AS po_open,
        (SELECT COALESCE(SUM(paid_amount),0) FROM `tabPayment Entry`
         WHERE docstatus=1 AND payment_type='Pay'
         AND posting_date BETWEEN %(ms)s AND %(me)s) AS paid_out,
        (SELECT COALESCE(SUM(paid_amount_after_tax),0) FROM `tabPayment Entry`
         WHERE docstatus=1 AND payment_type='Pay'
         AND posting_date BETWEEN %(ms)s AND %(me)s) AS paid_out_after_tax,
        (SELECT COALESCE(SUM(received_amount),0) FROM `tabPayment Entry`
         WHERE docstatus=1 AND payment_type='Receive'
         AND posting_date BETWEEN %(ms)s AND %(me)s) AS recd_in,
        (SELECT COALESCE(SUM(received_amount_after_tax),0) FROM `tabPayment Entry`
         WHERE docstatus=1 AND payment_type='Receive'
         AND posting_date BETWEEN %(ms)s AND %(me)s) AS recd_in_after_tax
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # ---------------------------------------------------------------------
    # RESPONSE
    # ---------------------------------------------------------------------
    # ---------------------------------------------------------------------
    # 12. VENDOR PAYOUTS: Purchase Invoices with the Payment Entries made
    #     against them (via Payment Entry Reference).
    # ---------------------------------------------------------------------
    vendor_payouts = _read_sql("""
    SELECT pi.name AS invoice, pi.supplier_name AS supplier,
           pi.posting_date AS inv_date, pi.grand_total AS inv_total,
           pi.outstanding_amount AS due,
           per.parent AS payment, pe.posting_date AS pay_date,
           per.allocated_amount AS paid, pe.mode_of_payment AS mode
    FROM `tabPurchase Invoice` pi
    LEFT JOIN `tabPayment Entry Reference` per
           ON per.reference_name = pi.name
          AND per.reference_doctype = 'Purchase Invoice'
    LEFT JOIN `tabPayment Entry` pe
           ON pe.name = per.parent AND pe.docstatus = 1
    WHERE pi.docstatus = 1
      AND pi.posting_date BETWEEN %(ms)s AND %(me)s
    ORDER BY pi.posting_date DESC
    LIMIT 300
""", {"ms": month_start, "me": month_end}, as_dict=True)

    # payout totals
    vendor_payout_totals = _read_sql("""
    SELECT COALESCE(SUM(per.allocated_amount),0) AS total_paid
    FROM `tabPayment Entry Reference` per
    INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
    WHERE pe.docstatus = 1
      AND per.reference_doctype = 'Purchase Invoice'
      AND pe.posting_date BETWEEN %(ms)s AND %(me)s
""", {"ms": month_start, "me": month_end}, as_dict=True)

    frappe.response["message"] = {
        "meta": {"month": month, "month_start": month_start,
                 "month_end": str(month_end), "today": today,
                 "generated_at": frappe.utils.now()},
        "cost_centers": cost_centers,
        "supplier_counts": supplier_counts,
        "supplier_total": (supplier_total[0].get("total") if supplier_total else 0),
        "ap_by_supplier": ap_by_supplier,
        "ap_ageing": (ap_ageing[0] if ap_ageing else {}),
        "purchase_invoices": pi_list,
        "pi_status": pi_status,
        "purchase_orders": po_list,
        "po_status": po_status,
        "payment_entries": pe_list,
        "pe_summary": pe_summary,
        "journal_entries": je_list,
        "je_summary": je_summary,
        "spend_by_cc": spend_by_cc,
        "daybook": daybook,
        "daybook_branch": daybook_branch,
        "ho_handover": ho_handover,
        "ho_handover_total": (ho_handover_total[0].get("total") if ho_handover_total else 0),
        "ho_handover_count": (ho_handover_total[0].get("cnt") if ho_handover_total else 0),
        "ho_by_branch": ho_by_branch,
        "vendor_payouts": vendor_payouts,
        "vendor_payout_total": (vendor_payout_totals[0].get("total_paid") if vendor_payout_totals else 0),
        "totals": (totals[0] if totals else {})
    }
