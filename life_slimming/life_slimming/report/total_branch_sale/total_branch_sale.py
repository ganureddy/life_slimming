# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint

def execute(filters=None):
    try:
        condition = conditions(filters)
        data = get_date(filters,condition)
        columns = get_columns()
        return columns, data
    except Exception as e:
        frappe.log_error("total branch sale",str(e))


def get_columns():
    column = [
        {
            "label":_("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label":_("Net Total"),
            "fieldname": "total",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label":_("Taxes Amount"),
            "fieldname": "total_taxes",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label":_("Grand Total"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label":_("Paid Amount With Tax"),
            "fieldname": "paid_amount",
            "fieldtype": "Currency",
            "width": 200,
        },
        {
            "label":_("Remaining Amount With Tax"),
            "fieldname": "outstanding_amount",
            "fieldtype": "Currency",
            "width": 200,
        },
        
    ]
    
    return column
def get_date(filters,condition):
    
    row_data = frappe.db.sql(
                """
                Select si.branch,Sum(si.net_total) as total,Sum(si.total_taxes_and_charges) as total_taxes
                ,Sum(si.grand_total) as grand_total,Sum(si.outstanding_amount) as outstanding_amount,
                Sum((si.grand_total - si.outstanding_amount)) as paid_amount from
                `tabSales Invoice` as si
                Where si.status NOT IN ('Unpaid') and si.docstatus = 1 %s
                Group By branch
                ORDER BY si.posting_date desc 
                """
                %condition,
                filters,
                as_dict=1,
            )
    
    return row_data 



    

def conditions(filters):
    conditions = ""
   
    if filters.get("from_date") and filters.get("to_date"):
        conditions += " and si.posting_date between %(from_date)s And %(to_date)s"
        
    user = frappe.session.user
    user_permission = frappe.db.get_list("User Permission",{"user":user,"allow":"Branch"},['allow',"for_value"],ignore_permissions=True)
    if len(user_permission) ==1:
        # Only branch 
        if user_permission[0]["allow"] == "Branch":
            conditions += f" and si.branch = '{user_permission[0]['for_value']}'"
    elif len(user_permission) >= 2:
        # branch manager Wise (Two more than )
        branch = tuple(i["for_value"] for i in user_permission)
        conditions += f" and si.branch IN {branch}"
    else:
        if filters.get("branch"):
            conditions += " AND si.branch = %(branch)s"
   
    return conditions