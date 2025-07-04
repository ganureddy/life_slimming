# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "label": _("Customer Name"),
            "fieldname": "customer_name",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150,
        },
        {
            "label": _("Lead"),
            "fieldname": "lead_name",
            "fieldtype": "Link",
            "options": "Lead",
            "width": 150,
        },
        {
            "label": _("Source"),
            "fieldname": "media",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "options": "Branch",
            "width": 150,
        },
        {
            "label": _("Appointment Name"),
            "fieldname": "appointment_name",
            "fieldtype": "Link",
            "options": "Appointment",
            "width": 150,
        },
        {
            "label": _("Appointment Category"),
            "fieldname": "appointment_category",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Appointment Concern"),
            "fieldname": "appointment_concern",
            "fieldtype": "Data",
            "width": 150,
        },
        
        {
            "label": _("Therapy Plan"),
            "fieldname": "therapy_plan",
            "fieldtype": "Link",
            "options": "Therapy Plan",
            "width": 150,
        },
        {
            "label": _("Total Therapy Session"),
            "fieldname": "total_sessions",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Total Therapy Session Completed"),
            "fieldname": "total_sessions_completed",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Sales Invoice"),
            "fieldname": "sales_invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 150,
        },
        {
            "label": _("Amount"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "width": 150,
        },
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    data = frappe.db.sql(f"""
        SELECT c.name as customer_name,c.branch_name as branch,tp.media,c.sex,c.mobile,l.lead_name,
               tp.category AS appointment_category, l.consultant AS appointment_concern,
               si.name AS sales_invoice,si.grand_total as grand_total, tp.name AS therapy_plan, tp.total_sessions AS total_sessions,
               tp.total_sessions_completed AS total_sessions_completed 
        FROM `tabPatient` AS c
        LEFT JOIN `tabLead` AS l ON c.mobile = l.mobile_no
        LEFT JOIN `tabSales Invoice` AS si ON c.name = si.customer 
        LEFT JOIN `tabTherapy Plan` AS tp ON c.name = tp.patient AND tp.name =si.therapy_plan_reference_id
        LEFT JOIN `tabTherapy Session` AS ts ON c.name = ts.patient
        WHERE {conditions}
        GROUP BY si.name,tp.name
    """, as_dict=1)
    
    print(data,"ppppppppppppppppppppppppppp")
    return data

def get_conditions(filters):
    conditions = ""
    conditions += "si.docstatus=1"
    if filters.get("customer_name"):
        conditions += f" AND c.name = '{filters['customer_name']}'"
    if filters.get("lead_name"):
        conditions += f" AND c.lead_name = '{filters['lead_name']}'"
    return conditions
