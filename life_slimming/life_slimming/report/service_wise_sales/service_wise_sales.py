# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint
import pandas as pd
from life_slimming.life_slimming.report.branch_wise_sales_report.branch_wise_sales_report import execute as execute_ 

def execute(filters=None):
    
    try:
        
        data = get_data(filters)
        columns = get_columns(filters)
        return columns, data
    
    except Exception as e:
        frappe.log_error("service wise sales report",str(e))





def get_data(filters):
    
    row_data = execute_(filters)
    
    if row_data[1]:
    
        data_frame = pd.DataFrame.from_records(row_data[1])
        
        del data_frame['posting_date']    
        
        group_by_service = data_frame.groupby(by=["service_unit","branch"],as_index=False).sum()
        
        data = group_by_service.to_dict("records")
        
        user = frappe.session.user
        user_permission = frappe.db.get_list("User Permission",{"user":user,"allow":"Branch"},['allow',"for_value"],ignore_permissions=True)
        
        if user_permission:
            return data
        else:
            data_frame = pd.DataFrame.from_records(row_data[1])
        
            del data_frame['posting_date']
            del data_frame['branch']
            del data_frame['item_code']   
            
            group_by_service = data_frame.groupby(by=["service_unit"],as_index=False).sum()
            group_by_service['net_sales'] = group_by_service["net_sales"].apply(lambda row:round(row,2))
            
            data = group_by_service.to_dict("records")
                    
            return data
            
    else:
     return []
    
    

def get_columns(filters):
    column = [

    {
        "label":_("Service Unit"),
        "fieldname":"service_unit",
        "fieldtype":"Data",
        "width": 120,
        
    },
    ]
    user = frappe.session.user
    user_permission = frappe.db.get_list("User Permission",{"user":user,"allow":"Branch"},['allow',"for_value"],ignore_permissions=True)
        
    if user_permission:
        column.append({
            "label":_("Branch"),
            "fieldname":"branch",
            "fieldtype": "Data",
            "width": 120,
        }),
        
    column.append({
            "label":_("Net Sales"),
            "fieldname": "net_sales",
            "fieldtype": "Currency",
            "width": 120,
        })
        
    return column
