# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint
import traceback
import sys


def execute(filters=None):
    
    validate_filters(filters)
    try:
        columns = get_columns(filters)
        branch_codit,sales_invoice = branch_wise_conditions(filters)
        data = get_data(branch_codit,filters)
        
        return columns,data
    
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

def get_columns(filters):
    
    if filters.get('type_of') == "Service Wise":
        column = [
            {
                "label":_("Service Unit"),
                "fieldname":"service_unit",
                "fieldtype":"Data",
                "width": 120,
            },
            {
                "label":_("Branch"),
                "fieldname":"branch",
                "fieldtype": "Data",
                "width": 120,
            },
            {
                "label":_("Net Sales"),
                "fieldname": "net_sales",
                "fieldtype": "Data",
                "width": 120,
            }
        ]
            
        return column
    
    if filters.get('type_of') == "Customer Wise":
        column = [
            
        {
            "label": "Payment Date",
            "fieldname": "posting_date",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Payment Id",
            "fieldname": "payment_id",
            "fieldtype": "Data",
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
            "label": "Client Name",
            "fieldname": "client_name",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Mode of Payment",
            "fieldname": "mode_of_payment",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label":_("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": 120,
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
            "label": "Net Paid Amount",
            "fieldname": "net_paid_amount",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Tax Amount",
            "fieldname": "net_tax_amount",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Paid Amount",
            "fieldname": "paid_amount",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label":_("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 120,
        }   
        ]
        
        return column
    
    if filters.get('type_of') == "Branch Wise":
        column = [
            {
                "label":_("Branch"),
                "fieldname": "branch",
                "fieldtype": "Data",
                "width": 120,
            },
            {
                "label":_("Net Paid Amount"),
                "fieldname": "net_paid_amount",
                "fieldtype": "Data",
                "width": 200,
            },
            {
                "label":_("Tax Amount"),
                "fieldname": "net_tax_amount",
                "fieldtype": "Data",
                "width": 200,
            },
            {
                "label":_("Paid Amount"),
                "fieldname": "paid_amount",
                "fieldtype": "Data",
                "width": 200,
            },
            
        ]
        
        return column
      
def get_data(cond,filters):
    
    if filters.get('type_of') == "Service Wise":
        
        row_data = frappe.db.sql(
        """SELECT
            si.service_unit,ROUND(SUM(pe.paid_amount*100/105),0) as net_sales,
            si.branch
        FROM
            `tabPayment Entry` as pe,
            `tabPayment Entry Reference` as per,
            `tabSales Invoice` as si
        WHERE
            pe.docstatus = 1 AND pe.payment_type = "Receive"
            AND si.name = per.reference_name
            AND per.parent = pe.name %s
            GROUP BY si.service_unit,si.branch
            ORDER BY pe.posting_date
        """
        % cond,
        filters,
        as_dict=1
        )
        
        return row_data
    
    if filters.get('type_of') == "Customer Wise":
        
        row_data = frappe.db.sql(
        """SELECT
            pe.name as payment_id,pe.posting_date,
            si.posting_date as invoice_date,
            pe.party as client_name,
            pe.mode_of_payment,
            pe.branch,
            si.ref_practitioner,
            si.custom_referring_name,
            si.custom_incentive_employee_name,
            ROUND((pe.paid_amount*100)/105,0) as net_paid_amount,
            ROUND((pe.paid_amount*5)/105,0) as net_tax_amount,
            pe.paid_amount,
            per.reference_name as sales_invoice_id,
            per.total_amount,
            si.status
        FROM
            `tabPayment Entry` as pe,
            `tabPayment Entry Reference` as per,
            `tabSales Invoice` as si
        WHERE
            pe.docstatus = 1 AND pe.payment_type = "Receive"
            AND si.name = per.reference_name
            AND per.parent = pe.name %s
        ORDER BY pe.posting_date desc
        """
        % cond,
        filters,
        as_dict=1
        )

        return row_data
    
    if filters.get('type_of') == "Branch Wise":
        
        row_data = frappe.db.sql(
        """SELECT
            pe.branch,
            ROUND(SUM((pe.paid_amount*100)/105),0) as net_paid_amount,
            ROUND(SUM((pe.paid_amount*5)/105),0) as net_tax_amount,
            Sum(pe.paid_amount) as paid_amount
        FROM
            `tabPayment Entry` as pe,
            `tabPayment Entry Reference` as per,
            `tabSales Invoice` as si
        WHERE
            pe.docstatus = 1 AND pe.payment_type = "Receive"
            AND si.name = per.reference_name
            AND per.parent = pe.name %s
            Group BY pe.branch
            ORDER BY pe.posting_date desc
        """
        % cond,
        filters,
        as_dict=1
        )
        
        return row_data
    

def branch_wise_conditions(filters):
    conditions = ""
    si_invoice = None
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s"
        
    user = frappe.session.user
    user_permission = frappe.db.get_list("User Permission",{"user":user,"allow":"Branch"},['allow',"for_value"],ignore_permissions=True)
    
    if len(user_permission) ==1:
        if user_permission[0]["allow"] == "Branch":
            conditions += f" and pe.branch = '{user_permission[0]['for_value']}'"
            si_invoice = frappe.db.get_list("Sales Invoice",{"branch":user_permission[0]['for_value']},['name'],pluck='name')

    elif len(user_permission) >= 2:
        if not filters.get("branch"):
            branch = tuple(i["for_value"] for i in user_permission)
            conditions += f" and pe.branch IN {branch}"
            si_invoice = frappe.db.get_list("Sales Invoice",{"branch":["IN",[branch]]},['name'],pluck='name')
        else:
            conditions += " AND pe.branch = %(branch)s"
            si_invoice = frappe.db.get_list("Sales Invoice",{"branch":filters.get("branch")},['name'],pluck='name')

    else:
        if not filters.get("branch"):
            si_invoice = frappe.db.get_list("Sales Invoice",['name'],pluck='name')
        else: 
            conditions += " AND pe.branch = %(branch)s"
            si_invoice = frappe.db.get_list("Sales Invoice",{"branch":filters.get("branch")},['name'],pluck='name')

    return conditions ,si_invoice
	
