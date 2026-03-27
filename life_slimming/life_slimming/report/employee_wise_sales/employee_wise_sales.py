# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint
import pandas as pd
import traceback
import sys

def execute(filters=None):
    
    # if filters.get("branch"):
    validate_filters(filters)
    try:
        
        columns = get_columns(filters)
        condition,invoice = branch_wise_conditions(filters)
        data = get_data(condition,filters)
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
    column = [
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Link",
            "options": "Healthcare Practitioner",
            "width": 200
        },
        {
            "label": _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label":_("Amount"),
            "fieldname":"amount",
            "fieldtype":"Data",
            "width": 120
        }
    ]
    
    return column


def get_data(cond,filters):
    
    row_data = frappe.db.sql(
        """SELECT
            pe.name as payment_id,pe.posting_date,
            si.posting_date as invoice_date,
            pe.party as client_name,
            pe.mode_of_payment,
            si.ref_practitioner,
            si.custom_referring_name,
            si.custom_incentive_employee_name,
            si.therapy_plan_reference_id as package_id,
            pe.branch,
            ROUND((pe.paid_amount*100)/105,0) as net_paid_amount,
            ROUND((pe.paid_amount*05)/105,0) as net_tax_amount,
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
    
    filter_data = []
    if len(row_data)>0:
        for each in row_data:
            if each.package_id:
                
                if not each.get("custom_incentive_employee_name"):
                    filter_data.append({
                        "employee_name":frappe.db.get_value("Healthcare Practitioner",{'name': each.get("ref_practitioner"),"branch":each.get('branch'),"status":"Active"},['practitioner_name']),
                        "branch":frappe.db.get_value("Healthcare Practitioner",{'name': each.get("ref_practitioner"),"branch":each.get('branch'),"status":"Active"},['branch']),
                        'amount':each.get("net_paid_amount"),
                        'designation' : frappe.db.get_value("Healthcare Practitioner", {'name': each.get("ref_practitioner"),"branch":each.get('branch'),"status":"Active"}, ['designation'])
                    })
                    
                else:
                    if each.get("ref_practitioner"):
                        filter_data.append({
                            "employee_name":frappe.db.get_value("Healthcare Practitioner",{'name': each.get("ref_practitioner"),"branch":each.get('branch'),"status":"Active"},['practitioner_name']),
                            "branch":frappe.db.get_value("Healthcare Practitioner",{'name': each.get("ref_practitioner"),"branch":each.get('branch'),"status":"Active"},['branch']),
                            'amount':round(each.get("net_paid_amount")/2,2),
                            'designation' : frappe.db.get_value("Healthcare Practitioner", {'name': each.get("ref_practitioner"),"branch":each.get('branch'),"status":"Active"}, ['designation']) 
                        })
                    
                    if each.get("custom_incentive_employee_name"):
                        filter_data.append({
                            "employee_name":each.get("custom_incentive_employee_name"),
                            "branch":frappe.db.get_value("Healthcare Practitioner",{'name': each.get("ref_practitioner"),"branch":each.get('branch'),"status":"Active"},['branch']),
                            'amount':round(each.get("net_paid_amount")/2,2),
                            'designation' : frappe.db.get_value("Healthcare Practitioner", {'practitioner_name': each.get("custom_incentive_employee_name"),"branch":each['branch'],"status":"Active"}, ['designation']) 
                        })
                            
        if len(filter_data) >0:
            df = pd.DataFrame(filter_data)            
            meg_data = df.groupby(['employee_name','designation', 'branch'],as_index=False).sum()
            convert_data = meg_data.to_dict('records')
        
            return convert_data
        else:
            return []

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
