# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt


import frappe
import erpnext
from frappe import _

def execute(filters=None):
    
    columns = get_columns()
    
    data = get_data(filters)

    return columns,data
        
    
def get_columns():
    return[
        {
            "label": ("Client Name"),
            "fieldname": "patient",
            "fieldtype": "Link",
            "options": "Patient",
        },
        
        {
            "label": ("Client Id"),
            "fieldname": "uid",
            "fieldtype": "Data",
        },
        
        {
            "label": ("Gender"),
            "fieldname": "sex",
            "fieldtype": "Data",
        },
        
        {
            "label": ("Mobile"),
            "fieldname": "mobile",
            "fieldtype": "Data",
        }, 
        # {
        #     "label": ("Media"),
        #     "fieldname":"media",
        #     "fieldtype": "Data",
        # },
        {
            "label": ("Sales Invoice ID"),
            "fieldname": "sales_invoice",
            "fieldtype": "Link",
            "options":"Sales Invoice",
        },
        {
            "label": ("Grand Total With Tax"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
        },
        {
            "label": ("Remaining Balance"),
            "fieldname": "outstanding_amount",
            "fieldtype": "Currency",
        },
        
        {
            "label": ("Payment Entry ID"),
            "fieldname": "payment_entry_id",
            "fieldtype": "Link",
            "options":"Payment Entry"
        },
        {
            "label": ("Paid Amount"),
            "fieldname": "paid_amount",
            "fieldtype": "Currency",
        },
        
        {
            "label": ("Client Appointment Date"),
            "fieldname": "appointment_date",
            "fieldtype": "date",
        },
        {
            "label": ("Therapy Plan"),
            "fieldname": "therapy_plan",
            "fieldtype": "Link",
            "options":"Therapy Plan",
        },
        {
            "label": ("Therapy Type"),
            "fieldname": "therapy_type",
            "fieldtype": "Link",
            "options":"Therapy Type",
        },
        {
            "label": ("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
        },
        {
            "label": ("No of Sessions"),
            "fieldname": "no_of_sessions",
            "fieldtype": "Int",
        },
        {
            "label": ("Sessions Completed"),
            "fieldname": "sessions_completed",
            "fieldtype": "Int",
        },	
    ]

def get_conditions(filters):
    
    try:
        conditions = []
        conditions.append(f"DATE(p.creation) BETWEEN '{filters.from_date}' AND '{filters.to_date}'")
 
        if filters.get("from_date") > filters.get("to_date"):
            frappe.throw(
                _("{0} cannot be future days").format(frappe.bold(_("From Date")))
            )
        
        # if filters.get("sex"):
        #     conditions.append(f" and p.sex='{filters.sex}'")
        
        # if filters.get("status"):
        #     conditions.append(f" and p.status='{filters.status}'")
        
        if filters.get("patient_name"):
            conditions.append(f" and p.patient_name LIKE '%{filters.patient_name}%'")
            
        if filters.get("patient_name"):
            conditions += f" AND p.patient_name LIKE '%{filters.patient_name}%'"

        if filters.get("uid"):
            conditions += f" AND p.uid LIKE '%{filters.uid}%'"
            if filters.get("uid"):
                conditions.append(f" and p.uid LIKE '%{filters.uid}%'")

            if filters.get("branch_name"):
                conditions.append(f" and p.branch='{filters.branch}'")

            return " ".join(conditions) if conditions else ""

    except Exception as e:
        print(e)

def get_data(filters):
    
    therapy_detail = frappe.db.sql(
        """
            SELECT th.patient,p.sex,p.mobile,th.media,th.name as therapy_plan ,th.start_date,th.status,
            th.due_date,th_d.no_of_sessions,th_d.sessions_completed,th_d.therapy_type
            FROM
            `tabTherapy Plan` as th,
            `tabTherapy Plan Detail` as th_d,
            `tabPatient` as p
            Where
            th_d.parent = th.name and p.first_name = th.patient
            ORDER BY th.creation DESC
            
        """,as_dict=1)
    
    
    
    for each in therapy_detail:
        
        sales_invoice = frappe.db.sql("""
                                      SELECT si.name,si.grand_total,si.outstanding_amount
                                      FROM
                                      `tabSales Invoice` as si,
                                      `tabSales Invoice Item` as sii
                                      WHERE
                                      sii.parent=si.name
                                      And sii.reference_dn = '{reference_dn}'
                                      """.format(reference_dn=each['therapy_plan']),as_dict=1
                                      )
        

        if len(sales_invoice) > 0:
            each.update({'sales_invoice':sales_invoice[0]["name"],"grand_total":sales_invoice[0]["grand_total"],
                         'outstanding_amount':sales_invoice[0]["outstanding_amount"]})
        
            payment_entry = frappe.db.sql("""
                                        SELECT pe.name,per.total_amount,per.allocated_amount,pe.paid_amount
                                        FROM
                                        `tabPayment Entry` as pe,
                                        `tabPayment Entry Reference` as per
                                        WHERE
                                        per.parent = pe.name
                                        And per.reference_name = '{reference_name}'
                                        """.format(reference_name=sales_invoice[0]["name"]),as_dict=1
                                        )
            
            if len(payment_entry) > 0:
                each.update({'payment_entry_id':payment_entry[0]["name"],"paid_amount":payment_entry[0]["paid_amount"]})
            
            
    

                    
    return therapy_detail