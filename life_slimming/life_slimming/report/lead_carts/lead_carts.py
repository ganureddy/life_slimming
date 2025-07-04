# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
import erpnext
from frappe import _

def execute(filters=None):
    
    data = get_data(filters)
    columns = get_columns()
    chart = create_charts(data)
    return columns, data, None ,chart

def get_data(filters):
    conditions = ''
    conditions +=(f"DATE(creation) BETWEEN '{filters.from_date}' AND '{filters.to_date}'")
    data = frappe.db.sql("""select status,COUNT(status) as count from `tabLead` WHERE {conditions} GROUP BY status""".format(conditions=conditions),as_dict =1)
    return data

def create_charts(data):
    
    chart = {
    'data':{
        'labels':[value['status'] for value in data],
        'datasets':[
            {'values':[j['count'] for j in data]},
        ]
    },
    'type':'bar',
    'height':300,
    'colors':['#7cd6fd', '#743ee2']
    }
    return chart


def get_columns():
   return [
    {
        "label": _("Status"),
        "fieldname": "status",
        "fieldtype": "Data",
        "width": 150,
    },
    {
        "label": _("Counts"), 
        "fieldname": "count",
        "fieldtype": "Data",
        "width": 120,
      }
]