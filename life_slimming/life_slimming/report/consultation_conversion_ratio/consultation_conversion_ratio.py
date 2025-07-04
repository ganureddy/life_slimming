# Copyright (c) 2024, swathi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
from dateutil import relativedelta


def execute(filters=None):
    is_current_year = True
    range_month = 1
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
        try:
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
        except Exception as e:
            frappe.log_error(str(e))
            return [],[]
    
    try:
        if not filters.get("employee_conversion_check"):
            final_data,attribute = get_filter_data(month_wise_result)
        else:
            final_data = month_wise_result
            
        # chart = get_chart(final_data,attribute)
            
        columns = get_columns(filters)
        
        return columns,final_data
    except Exception as e:
        frappe.log_error("consultation conversion ratio",str(e))

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
    
    condit += f" AND DATE(creation) BETWEEN '{from_date}' And '{to_date}'"
    
    user = frappe.session.user
    user_permission = frappe.db.get_list("User Permission",{"user":user,"allow":"Branch"},['allow',"for_value"],ignore_permissions=True)
    
    if len(user_permission) ==1:
        # Only branch 
        if user_permission[0]["allow"] == "Branch":
            condit += f" AND ld.lead_assign_to_branch = '{user_permission[0]['for_value']}'"
            
    elif len(user_permission) >= 2:
        # branch manager Wise (Two more than )
        if filters.get("branch") == "All Branch":
            branch = tuple(i["for_value"] for i in user_permission)
            condit += f" and ld.lead_assign_to_branch IN {branch}"
        else:
            condit += f" And ld.lead_assign_to_branch = '{filters.get('branch')}'"
        
    else:
        if filters.get("branch") != "All Branch":
            condit += f" AND ld.lead_assign_to_branch = '{filters.get('branch')}'"
    
    return condit

def get_data(filters,condit,from_date,columns_month):
    
    month_year = datetime.strptime(from_date,"%Y-%m-%d")
    
    columns_month.insert(0,month_year.strftime("%b-%Y"))
    # this is total count of lead documentation between date or select month
    total_lead = frappe.db.sql(
    """
    SELECT COUNT(ld.name) As count,ld.lead_assign_to_branch As branch
    FROM `tabLead` As ld
    WHERE ld.docstatus = 0 And ld.lead_assign_to_branch IS NOT NULL
    And ld.lead_assign_to_branch NOT IN ("")
    {cond}
    GROUP BY ld.lead_assign_to_branch
    """.format(cond=condit),
    as_dict=1
    )
     
    branch_detail,branch_count = get_send_to_branch_count(filters,condit)
    total_lead.extend(branch_count)
    
    if not filters.get("employee_conversion_check"):
        conversion_in_branch = get_conversion_count(branch_detail,filters)
        total_lead.extend(conversion_in_branch)
        
        return total_lead
    else:
        conversion_in_branch = get_conversion_count(branch_detail,filters)
        
        return conversion_in_branch
    

def get_send_to_branch_count(filters,condit):
    
    #this give total count of lead where status equal to Consultation Done 
    send_to_branch_details = frappe.db.sql(
    """
    SELECT ld.name,ld.lead_name,ld.mobile_no,ld.gender,
    ld.category,ld.consultant,ld.lead_assign_to_branch As branch
    FROM `tabLead` As ld
    WHERE ld.docstatus = 0 And ld.lead_assign_to_branch IS NOT NULL
    And ld.lead_assign_to_branch != ""
    And ld.status = "Consultation Done"
    {cond}
    """.format(cond=condit),
    as_dict=1
    )
    # this give details of client for lead documentation where status equal to Consultation Done
    send_to_branch_count = frappe.db.sql(
    """
    SELECT COUNT(ld.name) As send_To_consultation,ld.lead_assign_to_branch As branch
    FROM `tabLead` As ld
    WHERE ld.docstatus = 0 And ld.lead_assign_to_branch IS NOT NULL
    And ld.lead_assign_to_branch != "" And status = "Consultation Done"
    {cond}
    GROUP BY ld.lead_assign_to_branch
    """.format(cond=condit),
    as_dict=1
    )
    
    return send_to_branch_details,send_to_branch_count


def get_conversion_count(branch_detail,filters):
    
    client_data = []
    
    for each in branch_detail:
        if each["mobile_no"]:
            mobile = each["mobile_no"][-8:]
            data = frappe.db.sql(
                """
                SELECT cl.name,cl.mobile,cl.sex,
                cl.branch_name As branch
                FROM `tabPatient` As cl
                WHERE cl.docstatus = 0 And cl.branch_name=(%s)
                And cl.mobile LIKE (%s)
                """,
                (each['branch'],f"%{mobile}"),
                as_dict=True
            )
            client_data.extend(data)
            
    client_mobile = tuple(set([i['mobile'] for i in client_data]))
    
    if not filters.get("employee_conversion_check"):
        total_invoice = []
        if len(client_mobile)>0:
            for each_mobile in client_mobile:
                first_invoice = frappe.db.sql(
                    """
                    SELECT si.name AS conversion,si.branch,si.net_total as conversion_amount,si.posting_date,
                    (si.grand_total - si.outstanding_amount) as paid_amount
                    FROM `tabSales Invoice` AS si
                    WHERE si.docstatus=1 AND si.contact_mobile = (%s)
                    ORDER BY si.posting_date ASC
                    LIMIT 1
                    """,
                    each_mobile,
                    as_dict=True
                )
                total_invoice.extend(first_invoice)
                
            if len(total_invoice):
                filter_data= [{k: v for k, v in d.items() if k != 'posting_date'} for d in total_invoice]
                inital_data = {}
                
                for outer in filter_data:
                    branch_key = outer.get("branch")

                    if branch_key not in inital_data:
                        inital_data[branch_key]={
                            'branch':outer.get("branch"),
                            "conversion":0,
                            "conversion_amount":0.0,
                            "paid_amount":0.0
                        }
                    inital_data[branch_key]["conversion"] += 1
                    inital_data[branch_key]['conversion_amount'] += round(outer.get("conversion_amount",0.0),2)
                    net_paid = round(outer.get("paid_amount",0.0),2)*100/(118)
                    inital_data[branch_key]['paid_amount'] += net_paid
                
                final_data  = list(inital_data.values())
                
                return final_data
            
            return []
        
        return []
    else:
        row_data = get_empolyee_conversion_detail(client_mobile)
        return row_data
        
def get_empolyee_conversion_detail(client_mobile):
    total_invoice = []
    if len(client_mobile)>0:
        for each_mobile in client_mobile:
            first_invoice = frappe.db.sql(
                """
                SELECT si.name as conversion,si.branch,si.net_total as amount,si.posting_date,
                si.contact_mobile as mobile_no,
                si.customer,si.custom_referring_name,si.service_unit,
                (si.grand_total - si.outstanding_amount) as paid_amount
                FROM `tabSales Invoice` AS si
                WHERE si.docstatus=1 AND si.contact_mobile = (%s)
                ORDER BY si.posting_date ASC
                LIMIT 1
                """,
                each_mobile,
                as_dict=True
            )
            total_invoice.extend(first_invoice)
            
        inital_data = {} 
        for outer in total_invoice:
            custom_referring_name_key = outer.get("custom_referring_name")

            if custom_referring_name_key not in inital_data:
                inital_data[custom_referring_name_key]={
                    'custom_referring_name':outer.get("custom_referring_name"),
                    "branch":outer.get("branch"),
                    "conversion":0,
                    "amount":0.0,
                    "paid_amount":0.0,
                }
            inital_data[custom_referring_name_key]["conversion"] += 1
            inital_data[custom_referring_name_key]['amount'] += round(outer.get("amount",0.0),2)
            net_paid = round(outer.get("paid_amount",0.0),2)*100/(118)
            inital_data[custom_referring_name_key]['paid_amount'] += net_paid
        
        final_data  = list(inital_data.values())
        
        [each.update({"ticket_size":round(each['paid_amount']/each['conversion'],2)})for each in final_data]
      
        return final_data
    return []

def get_columns(filters):
    
    columns = []
    
    if not filters.get("employee_conversion_check"):
        columns +=[
            {
            "label":_("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": "150px",
            },
            {
            "label":_("Total Lead"),
            "fieldname": "count",
            "fieldtype": "Int",
            "width": "100px",
            },
            {
            "label":_("Send To Consultation"),
            "fieldname": "send_To_consultation",
            "fieldtype": "Int",
            "width": "150px",
            },
            {
            "label":_("Conversion"),
            "fieldname": "conversion",
            "fieldtype": "Int",
            "width": "150px",
            },
            {
            "label":_("Lead To Consultation Ratio"),
            "fieldname": "lead_to_consultation_ratio",
            "fieldtype": "Percent",
            "width": "150px",
            },
            {
            "label":_("Consultation To Conversion Ratio"),
            "fieldname": "consultation_to_conversion_ratio",
            "fieldtype": "Percent",
            "width": "150px",
            },
            {
            "label":_("Lead To Conversion Ratio"),
            "fieldname": "lead_to_conversion_ratio",
            "fieldtype": "Percent",
            "width": "150px",
            },
            {
            "label":_("Conversion Amount"),
            "fieldname": "conversion_amount",
            "fieldtype": "Currency",
            "width": "150px",
            },
            {
            "label":_("Net Paid"),
            "fieldname": "paid_amount",
            "fieldtype": "Currency",
            "width": "150px",
            },
            {
            "label":_("Ticket Size(Avg.)"),
            "fieldname": "ticket_amount",
            "fieldtype": "Currency",
            "width": "150px",
            },
        ]
    if filters.get("employee_conversion_check"):
        columns+=[
            {
                "label":_("Branch"),
                "fieldname": "branch",
                "fieldtype": "Data",
                "width": "150px",
            },
             {
                "label":_("Conversion"),
                "fieldname": "conversion",
                "fieldtype": "Data",
                "width": "150px",
            },
            {
                "label":_("Net Amount"),
                "fieldname": "amount",
                "fieldtype": "Currency",
                "width": "180px",
            },
            {
                "label":_("Net Paid"),
                "fieldname": "paid_amount",
                "fieldtype": "Currency",
                "width": "180px",
            },
            {
                "label":_("Ticket Size(Avg.)"),
                "fieldname": "ticket_size",
                "fieldtype": "Currency",
                "width": "180px",
            },
            {
                "label":_("Taking By"),
                "fieldname": "custom_referring_name",
                "fieldtype": "Data",
                "width": "180px",
            }
        ]
        
    return columns

def get_filter_data(month_wise_result):
   
    inital_data = {}
    attribute = ['lead_to_consultation_ratio','consultation_to_conversion_ratio','lead_to_conversion_ratio']
 
    for outer in month_wise_result:
      
        branch_key = outer.get("branch")
        keys = list(outer.keys())
        keys.remove("branch")

        if branch_key not in inital_data:
            inital_data[branch_key]={
                'branch':outer.get("branch")
            }

        for key in keys:
            inital_data[branch_key][key] = outer.get(key,0)
        
    final_data  = list(inital_data.values())
    
    # Get Ratio of each
    for outer_loop in final_data:
        try:
            if outer_loop.get('count'):
                lead_to_consultation_ratio = round((outer_loop.get('send_To_consultation',0)/outer_loop.get('count',0))*100,2)
                lead_to_conversion_ratio = round((outer_loop.get('conversion',0)/outer_loop.get('count',0))*100,2)
            else:
                lead_to_consultation_ratio = 0.0
                lead_to_conversion_ratio = 0.0
            
            if outer_loop.get('send_To_consultation'):
                consultation_to_conversion_ratio = round((outer_loop.get('conversion',0)/outer_loop.get('send_To_consultation',0))*100,2)
            else:
                consultation_to_conversion_ratio = 0.0
            
            if outer.get("conversion") and outer_loop.get('paid_amount'):
                ticket_amount = round(outer_loop.get('paid_amount',0)/outer_loop.get('conversion',0),2)
            else:
                ticket_amount = 0.0
            
            
            outer_loop.update({
                        "lead_to_consultation_ratio":lead_to_consultation_ratio,
                        "consultation_to_conversion_ratio":consultation_to_conversion_ratio,
                        "lead_to_conversion_ratio":lead_to_conversion_ratio,
                        "ticket_amount":ticket_amount
                    })
        except Exception as e:
            frappe.log_error(str(e))
    
       
    return final_data ,attribute

def get_chart(final_data,attribute):
        
    branch = []
    month_data = []
    for i in attribute:
        local_list = []
        for each in final_data:
            if each['branch'] not in branch:
                branch.append(each['branch'])
            local_list.append(each.get(i,0))
        month_data.append(local_list)
    
    chart = {
    'data':{
        'labels':branch,
        'datasets':[
            {'name':attribute[0].replace("_"," ").capitalize(),'values':month_data[0],'chartType':'bar'},
            {'name':attribute[1].replace("_"," ").capitalize(),'values':month_data[1],'chartType':'bar'},
            {'name':attribute[2].replace("_"," ").capitalize(),'values':month_data[2],'chartType':'bar'},
        ]
    },
    'type':'axis-mixed',
    'height':600,
    'colors':['#7E055D', '#52057E', '#08056C'],
    }
    
    return chart
    
