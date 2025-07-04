# Copyright (c) 2024, swathi and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    
    if not filters.get("from_date") or not filters.get("from_date"):
        frappe.throw(_("Please Select From Date and To Date."))
    
    if filters.get("from_date") > filters.get("from_date"):
        frappe.throw(_("From Date Is Not Greater Than To Date."))
    
    if not filters.get("branch"):
        frappe.throw(_("Please Set Atleast One Branch Or Set All Branch."))
    
    try:  
        condition = conditions(filters)
        data = get_data(filters,condition)
        columns = get_columns(filters)
    
        return columns, data
    except Exception as e:
        frappe.log_error("doctor sharing details",str(e))


def get_data(filters,condition):
    
    if filters.get("group_by"):
        sales_invoice = frappe.db.sql('''
                                    SELECT si.name as invoice_id, si.custom_doctor_id,si.custom_doctor_name,si.branch,
                                    SUM(si.net_total) as amount
                                    FROM `tabSales Invoice` as si
                                    WHERE si.status NOT IN ('Unpaid') AND si.custom_doctor_id IS NOT NULL
                                    And si.docstatus =1 %s
                                    '''%condition,
                                    filters,
                                    as_dict=1
                                    )
    if not filters.get("group_by"):
        sales_invoice = frappe.db.sql('''
                                  SELECT si.name as invoice_id, si.custom_doctor_id,si.custom_doctor_name,si.branch,
                                  si.net_total as amount
                                  FROM `tabSales Invoice` as si
                                  WHERE si.status NOT IN ('Unpaid') AND si.custom_doctor_id IS NOT NULL
                                  And si.docstatus =1 %s
                                  '''%condition,
                                  filters,
                                  as_dict=1
                                  )
    
    for each in sales_invoice:
        employee_detail = frappe.db.get_list("Healthcare Practitioner",{'name':each['custom_doctor_id']},['gender','designation','department'])
        if len(employee_detail)>0:
            each.update({
                "designation":employee_detail[0]['designation'],
                "department":employee_detail[0]['department'],
                'gender':employee_detail[0]['gender']
            })
    
    
    return sales_invoice 

def get_columns(filters):
    columns = []
    if not filters.get("group_by"):
        columns += [{
                "label":_("Invoice Id"),
                "fieldname": "invoice_id",
                "fieldtype": "Data",
                "width": 200,
            },]
        
    columns +=[
        {
            "label":_("Employee Id"),
            "fieldname": "custom_doctor_id",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label":_("Employee Name"),
            "fieldname": "custom_doctor_name",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label":_("Gender"),
            "fieldname": "gender",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label":_("Designation"),
            "fieldname": "designation",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label":_("Department"),
            "fieldname": "department",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label":_("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label":_("Amount"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 100,
        },
    ]
    return columns

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
        if filters.get("branch") == "All Branch":
            branch = tuple(i["for_value"] for i in user_permission)
            conditions += f" and si.branch IN {branch}"
        else:
            conditions += f" And si.branch = '{filters.get('branch')}'"
    else:
        if filters.get("branch") != "All Branch":
            conditions += " AND si.branch = %(branch)s"
    
    if filters.get("group_by"):
        conditions += "GROUP BY si.custom_doctor_id \
                        ORDER BY si.custom_doctor_id DESC"
   
    return conditions

