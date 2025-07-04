# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
from dateutil import relativedelta
import collections


is_current_year = True

def execute(filters=None):
    
    range_month = 3
 
    columns_month = []
    month_change = []
    month_wise_result = []
    
    if not filters.get("month"):
        return [],[]
    
    if not filters.get("fiscal_year"):
        # message = "Please Select Fiscal Year"
        frappe.throw(_("Please Select Fiscal Year"))
        return [],[]
    
    # Take year and month from filter and check it is current year and month
    year = frappe.get_doc("Fiscal Year",{'name':filters.get("fiscal_year")})
    
    year_month = f"{year.year_end_date.strftime('%Y')}-{filters.get('month')}"
    
    for each in range(0,range_month):
        
        if each == 0:
            curr_month_change = datetime.now()
            check_current_month = curr_month_change.strftime('%Y-%b')
   
            if check_current_month  == year_month:
                month_change.append(curr_month_change)
                is_current_year = True
            else:
                date = datetime.strptime(f"{year_month}-06","%Y-%b-%d").strftime("%Y-%m-%d")
                change_date = datetime.strptime(date,"%Y-%m-%d")
                month_change.append(change_date)
                is_current_year = False
                    
        from_date,to_date = get_range(month_change,each,is_current_year)
        
        condition = conditions(filters,from_date,to_date)
        
        data = get_data(filters,condition,from_date,columns_month)
        
        month_wise_result.extend(data)
        
    
    final_data = get_filter_data(month_wise_result)
 
    # chart = get_chart(final_data,columns_month)
        
    columns = get_columns(columns_month)
    
    return columns,final_data

def get_range(month_change,each,is_current_year):
    
    from_date = None
    to_date = None
    
    if each ==0:
        if is_current_year:
            
            current_date = month_change[0]
            previous_date = current_date
            
            from_date = f"{previous_date.strftime('%Y-%m')}-06"
            to_date = f"{current_date.strftime('%Y-%m-%d')}"
            
            month_change.pop()
            month_change.append(previous_date)
            
        else:
            current_date = month_change[0]
            next_month_date = current_date + relativedelta.relativedelta(months=1)
            
            next_month_year = next_month_date
            
            from_date = f"{current_date.strftime('%Y-%m')}-06"
            to_date = f"{next_month_year.strftime('%Y-%m')}-05"
            
            
            month_change.pop()
            
            month_change.append(current_date)
            
    else:
        current_date = month_change[0]
        
        previous_date = current_date - timedelta(days=current_date.day)
        # previous_month = previous_month_date
        
        from_date = f"{previous_date.strftime('%Y-%m')}-06"
        to_date = f"{current_date.strftime('%Y-%m')}-05"
        
        month_change.pop()
        
        month_change.append(previous_date)
    
    return from_date,to_date
    
    
def conditions(filters,from_date,to_date):
    
    condit = " "
    
    condit += f" And si.posting_date between '{from_date}' And '{to_date}'"
    
    user = frappe.session.user
    user_permission = frappe.db.get_list("User Permission",{"user":user,"allow":"Branch"},['allow',"for_value"],ignore_permissions=True)
    
    if len(user_permission) ==1:
        # Only branch 
        if user_permission[0]["allow"] == "Branch":
            condit += f" and si.branch = '{user_permission[0]['for_value']}'"
    elif len(user_permission) >= 2:
        # branch manager Wise (Two more than )
        if filters.get("branch") == "All Branch":
            branch = tuple(i["for_value"] for i in user_permission)
            condit += f" and si.branch IN {branch}"
        else:
            condit += f" And si.branch = '{filters.get('branch')}'"
    else:
        if filters.get("branch") != "All Branch":
            condit += f" And si.branch = '{filters.get('branch')}'"
    
    return condit


def get_data(filters,condit,from_date,columns_month):
    
    month_year = datetime.strptime(from_date,"%Y-%m-%d")
    
    columns_month.insert(0,month_year.strftime("%b-%Y"))
    
    row_data = frappe.db.sql(
    """
    SELECT SUM(si.net_total) as amount, si.service_unit,si.branch
    FROM `tabSales Invoice` as si
    WHERE si.docstatus = 1 And si.status NOT IN ('Unpaid')
    {cond}
    GROUP BY si.service_unit,si.branch
    ORDER BY si.service_unit DESC
    """.format(cond=condit),
    as_dict=1
    )
    
    for each in row_data:
        each.update({
            "month":month_year.strftime("%b-%Y")
        })      
   
    return row_data

def get_columns(columns_month):
    columns = [
		{
            "label":_("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": 120,
        }
        ]
    columns.append(
        {
        "label":_("Service"),
        "fieldname": "service_unit",
        "fieldtype": "Data",
        "width": 120,
    }),
    for each in columns_month:
        columns.append({
            "label":(_(each)),
            "fieldtype": "Currency",
            "fieldname": each,
            "width": "150px",
        })
    

    return columns

def get_filter_data(month_wise_result):
   
    inital_data = collections.defaultdict(dict)

    for each in month_wise_result:
        branch_key = each.get("branch")
        service_key = each.get("service_unit") if each.get("service_unit") else "Other"
        
        if branch_key not in inital_data or service_key not in inital_data[branch_key]:
            inital_data[branch_key][service_key]={
                'branch':each.get("branch"),
                'service_unit':each.get("service_unit").replace("- LSACPL","").strip() if each.get("service_unit") else "Other"
            }
        
        inital_data[branch_key][service_key][each.get("month")] = each.get("amount",0)
        
    row_data  = inital_data.values()
    final_data =[]
    
    for i in row_data:
        k = i.values()
        final_data.extend(k)
        
    return final_data
            

    