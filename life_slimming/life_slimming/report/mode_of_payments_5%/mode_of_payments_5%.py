# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import traceback
import sys

def execute(filters=None):
    
    # if filters.get("branch"):
    validate_filters(filters)
    
    try:
        condition,si_invoices= get_conditions(filters)
        data = get_data(filters, condition,si_invoices)
        columns = get_column(filters)
        return columns, data
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "execute")
        
   
def validate_filters(filters):
    
    if not filters.get("from_date") and not filters.get("to_date"):
        frappe.throw(
            _("{0} and {1} are mandatory").format(frappe.bold(_("From Date")), frappe.bold(_("To Date")))
        )
               
    if filters.get("from_date") > filters.get("to_date"):
        frappe.throw(
            _("{0} not greater than To Date").format(frappe.bold(_("From Date")))
        )

      
def get_data(filters, condition, si_invoices):
    
    filter_data = []
    
    row_data = frappe.db.sql(
        """SELECT
            pe.name as payment_id, pe.posting_date,
            si.posting_date as invoice_date,
            pe.party as client_name,
            si.ref_practitioner,
            si.custom_referring_name,
            si.custom_incentive_employee_name,
            pe.mode_of_payment,
            pe.branch,
            pe.paid_amount,
            per.reference_name as sales_invoice_id,
            per.total_amount
        FROM
            `tabPayment Entry` as pe,
            `tabPayment Entry Reference` as per,
            `tabSales Invoice` as si
        WHERE
            pe.docstatus = 1 AND pe.payment_type = "Receive"
            AND si.name = per.reference_name
            AND per.parent = pe.name %s
        ORDER BY pe.posting_date DESC
        """ % condition,
        filters,
        as_dict=1
    ) or []

    # Get SI names already covered by Payment Entries
    paid_si_names = {row['sales_invoice_id'] for row in row_data}

    # Only process SI invoices NOT already in Payment Entry results
    remaining_invoices = [inv for inv in si_invoices if inv not in paid_si_names]

    for invoice in remaining_invoices:
        je_conditions = f" AND je.posting_date BETWEEN '{filters.get('from_date')}' AND '{filters.get('to_date')}'"
        
        entry_account = frappe.db.sql(
            """SELECT je.posting_date, jec.reference_name, je.name,
                jec.reference_type, jec.credit, jec.against_account,
                jec.party, je.total_amount
                FROM
                `tabJournal Entry Account` as jec,
                `tabJournal Entry` as je
                WHERE
                je.docstatus = 1 AND
                jec.parent = je.name
                {cond}
                AND jec.reference_name = '{reference}'
                AND jec.credit > 0
            """.format(reference=invoice, cond=je_conditions),
            as_dict=1
        )
        
        if entry_account:
            value = {
                "posting_date": entry_account[0]['posting_date'],
                "payment_id": entry_account[0]['name'],
                "sales_invoice_id": entry_account[0]['reference_name'],
                "client_name": entry_account[0]['party'],
                "mode_of_payment": entry_account[0]['against_account'].split(",")[0].replace("- LSACPL", '').strip(),
                "total_amount": frappe.db.get_value('Sales Invoice', invoice, 'grand_total'),
                "paid_amount": entry_account[0]['credit'],
                "branch": frappe.db.get_value('Sales Invoice', invoice, 'branch'),
                "charge": round((entry_account[0]['credit'] - entry_account[0]['total_amount']), 2)
            }
            filter_data.append(value)
            
    final_data = row_data + filter_data
    total_paid = 0.0
    paid_wo_tx = 0.0
    tax_amount = 0.0
    
    for each in final_data:
        total_paid += round(each.get('paid_amount') or 0, 2)
        paid_amount_without_tx = round(((each.get('paid_amount') or 0) * 100) / 105, 2)
        tax_amount_on_paid_amount = round(((each.get('paid_amount') or 0) * 5) / 105, 2)
        each.update({
            "paid_amount_without_tx": paid_amount_without_tx,
            "tax_amount_on_paid_amount": tax_amount_on_paid_amount
        })
        paid_wo_tx += each['paid_amount_without_tx']
        tax_amount += each['tax_amount_on_paid_amount']

    final_data.append({})
    final_data.append({
        "posting_date": _("Total Amount"),
        "paid_amount": round(total_paid, 2),
        "paid_amount_without_tx": round(paid_wo_tx, 2),
        "tax_amount_on_paid_amount": round(tax_amount, 2)
    })
    
    return final_data if final_data else []

def get_column(filters):
    columns = [
        {
            "label": "Payment Date",
            "fieldname": "posting_date",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Payment Id Or Journal Entry Id",
            "fieldname": "payment_id",
            "fieldtype": "Data",
            # "options": "Payment Entry",
            "width": 200
        },
        {
            "label": "Sales Invoice Id",
            "fieldname": "sales_invoice_id",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 200
        },
        {
            "label": "Invoice Date",
            "fieldname": "invoice_date",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Branch",
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Client Name",
            "fieldname": "client_name",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label":_("Referring Name"),
            "fieldname": "custom_referring_name",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label":_("Incentive Employee Name"),
            "fieldname": "custom_incentive_employee_name",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Mode of Payment",
            "fieldname": "mode_of_payment",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Total Amount",
            "fieldname": "total_amount",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Paid Amount W/O Tx",
            "fieldname": "paid_amount_without_tx",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Tax Amount On Paid Amount",
            "fieldname": "tax_amount_on_paid_amount",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Paid Amount",
            "fieldname": "paid_amount",
            "fieldtype": "Data",
            "width": 120
        },
    ]
    if filters.get("branch") == "All Branch":
        columns+=[
            {
            "label": "Charge",
            "fieldname": "charge",
            "fieldtype": "Data",
            "width": 120
            }
        ]
            
    
    return columns

def get_conditions(filters):
    conditions = ""
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s"
        
    user = frappe.session.user
    user_permission = frappe.db.get_list(
        "User Permission",
        {"user": user, "allow": "Branch"},
        ['allow', "for_value"],
        ignore_permissions=True
    )
    
    # Always include date range in SI filters
    si_filters = {
        "posting_date": ["between", [filters.get("from_date"), filters.get("to_date")]],
        "docstatus": 1
    }

    if len(user_permission) == 1:
        branch_val = user_permission[0]['for_value']
        conditions += f" AND pe.branch = '{branch_val}'"
        si_filters["branch"] = branch_val

    elif len(user_permission) >= 2:
        if not filters.get("branch"):
            branch_tuple = tuple(i["for_value"] for i in user_permission)
            conditions += f" AND pe.branch IN {branch_tuple}"
            si_filters["branch"] = ["IN", list(branch_tuple)]
        else:
            conditions += " AND pe.branch = %(branch)s"
            si_filters["branch"] = filters.get("branch")
    else:
        # Admin/no restriction — filter by branch only if passed
        if filters.get("branch"):
            conditions += " AND pe.branch = %(branch)s"
            si_filters["branch"] = filters.get("branch")
        # No branch filter = show ALL branches

    if filters.get("mode_of_payment"):
        conditions += " AND pe.mode_of_payment = %(mode_of_payment)s"

    si_invoice = frappe.db.get_list(
        "Sales Invoice",
        filters=si_filters,
        fields=['name'],
        pluck='name'
    ) or []

    return conditions, si_invoice