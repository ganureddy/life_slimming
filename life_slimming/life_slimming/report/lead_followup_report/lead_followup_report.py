# # Copyright (c) 2023, swathi and contributors
# # For license information, please see license.txt

import frappe
import erpnext
from frappe import _
import sys
import traceback

def execute(filters=None):
    if not filters:
        return [],[]
    
    if filters.get("from_date") > filters.get("to_date"):
        frappe.throw(
            _("{0} cannot be future days").format(frappe.bold(_("From Date")))
        )
        
    data = get_data(filters)
    columns = get_columns()
    return columns,data


def get_conditions(filters):
    conditions = ""
    conditions += f"DATE(l.creation) BETWEEN'{filters.from_date}'AND'{filters.to_date}'"
        
    if filters.followup_next_date:
        conditions += f" AND DATE(f.followup_next_date) ='{filters.followup_next_date}'"
    
    if filters.followup_by_person:
        conditions += f" AND l.lead_owner ='{filters.followup_by_person}'"
        
    if filters.name:
        conditions += f" AND f.parent='{filters.name}'"
    
    if filters.get("gender"):
        conditions += f" AND l.gender='{filters.gender}'"
    
    if filters.get("lead_assign_to_branch"):
        conditions += f" AND l.lead_assign_to_branch='{filters.lead_assign_to_branch}'"  
        
    return conditions


def get_data(filters):
    if filters.get("followup_by_person"):
        data = frappe.db.sql("""Select l.lead_name,l.gender,l.name,l.status,l.lead_assign_to_branch,l.lead_owner,
                            f.modified1,f.followup_by_person,f.followup_next_date,f.followup_remarks,
                            f.time as followup_next_time from `tabLead` as l,`tabFollowup` as f
                            WHERE f.parent = l.name and {condition} ORDER BY modified1 DESC """.format(condition = get_conditions(filters)),as_dict=1)


        if len(data) >0:
            for i in data:
                full_name = frappe.db.get_list("User",{"name":i.lead_owner},["full_name"])
                if len(full_name) >0:
                    i['full_name'] = full_name[0]['full_name']
            return data
    else:
        return []	

def get_columns():
    return [
        {
            "label": _("Lead"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Lead",
            "width":150,
        },
        {
            "label": _("Full Name"),
            "fieldname":"lead_name",
            "fieldtype":"Data",
            "default": "",
            "width": 100,
        },
        {
            "label": _("Gender"),
            "fieldname":"gender",
            "fieldtype": "Data",
            "default":"",
            "width": 100,
        },
        {
            "label": _("Lead Assign To Branch"),
            "fieldname":"lead_assign_to_branch",
            "fieldtype":"Data",
            "width":100,   
        },
        # {
        #     "label": _("Status"),
        #     "fieldname":"status",
        #     "fieldtype":"Data",
        #     "width":100,
        # },
        {
            "label": _("Modified Date And Time"),
            "fieldname":"modified1",
            "fieldtype":"DateTime",
            "width":150,   
        },
        {
            "label": _("Followup By Person"),
            "fieldname":"full_name",
            "fieldtype":"Data",
            "width":150,   
        },
        {
            "label": _("Followup By Next Date"),
            "fieldname": "followup_next_date",
            "fieldtype":"Date",
            "width":150,
        },
        {
            "label": _("Followup Next time"),
            "fieldname":"followup_next_time",
            "fieldtype":"Time",
            "width":150,
        },
        {
            "label": _("Followup Remarks"),
            "fieldname":"followup_remarks",
            "fieldtype":"Data",
            "width":250,
        },
    ]
    