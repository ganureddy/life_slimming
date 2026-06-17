# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
import erpnext
from frappe import _
import sys
import traceback
from erpnext.crm.doctype.lead import lead

def execute(filters=None):
    try:
        columns = get_columns()
        data = get_data(filters)
        return columns,data
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "execute")

def get_columns():
  return [
    {
        "label": _("Lead"),
        "fieldname": "name",
        "fieldtype": "Link",
        "options": "Lead",
        "width": 150,
    },
    {
        "label": _("Lead Name"), 
        "fieldname": "lead_name",
        "fieldtype": "Data",
        "width": 120,
      },
    {
        "label": _("Client Profession"),
        "fieldname":"job_title", 
        "fieldtype": "Data", 
        "width": 120,
    },
    {
        "label": _("Status"),
        "fieldname": "status", 
        "fieldtype": "Data",
        "width": 120,
    },
    {
        "label": _("Gender"),
        "fieldname":"gender",
        "filedtype": "Link",
        "options": "Gender",
        "width":150,
    },
    {	
        "label": _("Lead Owner"),
        "fieldname": "lead_owner",
        "fieldtype": "Link",
        "options": "User",
        "width": 100,
    },
    {
        "label": _("Location"),
        "fieldname": "lead_assign_to_branch",
        "fieldtype": "Data",
        "width": 100,
    },
    {
        "label": _("Email"), 
        "fieldname": "email_id",
        "fieldtype": "Data",
        "width": 150
    },
    {
        "label": _("Category"),
        "fieldname": "category",
        "fieldtype":"Link",
        "options":"Healthcare Service Unit",
        "width":150,
    },
    {
        "label": _("Concern"),
        "fieldname": "consultant",
        "fieldtype":"Link",
        "options":"Therapy Type",
        "width":150,
    },
    {
        "label": _("Source"),
        "fieldname": "source",
        "fieldtype":"Link",
        "options":"Lead Source",
        "width":150,
    },
    {
        "label": _("Modified Date and Time"),
        "fieldname": "modified1",
        "fieldtype":"DateTime",
        "width":150,
    },
    {
        "label": _("Followup by Person"),
        "fieldname": "followup_by_person",
        "fieldtype":"Link",
        "options":"User",
        "width":150,
     },
    {
        "label": _("Followup Next Date"),
        "fieldname": "followup_next_date",
        "fieldtype":"Date",
        "width":100,
    },
    {
        "label": _("Followup Next Time"),
        "fieldname": "followup_next_time",
        "fieldtype":"Time",
        "width":100,
    },
    {
        "label": _("Followup Remarks"),
        "fieldname": "followup_remarks",
        "fieldtype": "Data",
        "width":100,
    },
    
  ]
  

def get_conditions(filters):
    try:
        conditions = []
        conditions.append(f"DATE(creation) BETWEEN '{filters.from_date}' AND '{filters.to_date}'")
        if filters.get("status"):
            conditions.append(f" and status ='{filters.status}'")
        
        if filters.get("from_date") > filters.get("to_date"):
            frappe.throw(
                _("{0} cannot be future days").format(frappe.bold(_("From Date")))
            )
        
        if filters.get("lead_assign_to_branch"):
            conditions.append(f" and lead_assign_to_branch='{filters.lead_assign_to_branch}'")
        
        if filters.get("lead_owner"):
            conditions.append(f" and lead_owner='{filters.lead_owner}'")
            
        if filters.get("followup_by_person"):
            conditions.append(f" and followup_by_person='{filters.followup_by_person}'")
        
        if filters.get("category"):
            conditions.append(f" and category='{filters.category}'")
        
        if filters.get("source"):
            conditions.append(f" and source='{filters.source}'")
        
        if filters.get("gender"):
            conditions.append(f" and gender='{filters.gender}'")

        return " ".join(conditions) if conditions else ""
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "get_conditions")



def get_data(filters):
    try:
        if filters.get("lead_owner"):
            data = frappe.db.sql("""
                                    SELECT name,lead_name,job_title,status,gender,
                                    lead_owner,lead_assign_to_branch,email_id,age,
                                    category,consultant,source from `tabLead` Where 
                                    {condition} ORDER BY creation DESC
                                    """.format(condition=get_conditions(filters)),as_dict=1)
            for i in data:
                child_data = frappe.db.sql("""Select modified1,followup_by_person,
                                        followup_next_date,followup_remarks,
                                        time as followup_next_time from `tabFollowup`
                                        Where parent='{name}'  ORDER BY modified1 DESC Limit 1
                                        """.format(name = i.get('name')),filters,as_dict=1)
                
                if len(child_data) > 0:
                    for j in child_data[0]:
                        if "modified1" in j:
                            i[j] = child_data[0][j]
                        if "followup_by_person" in j:
                            i[j] = child_data[0][j]
                        if "followup_next_date" in j:
                            i[j] = child_data[0][j]
                        if "followup_remarks" in j:
                            i[j] = child_data[0][j]
                        if "followup_next_time" in j:
                            i[j] = child_data[0][j]
            
            return data
        else:
            return []
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "get_data")


 