# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.utils import flt, get_link_to_form, get_time, getdate
from frappe import _
import operator
import pandas as pd

# get_time(appointment_time)
@frappe.whitelist(allow_guest=True)
def execute(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    else:
        filters = dict(filters)
            
    if "branch" not in  filters:
        return {"message":"Please Select Branch"}
        
    columns = get_columns(filters)
    cond = get_conditions(filters)
    data = get_data_details(filters,cond)
    summary = report_summary(filters)
    
    
    if data:
        return columns, data, None, None, summary
    
    else:
        return [],[]


def get_conditions(filters):
    conds = {}
    
    if filters["date"]:
        conds.update({"appointment_date":filters["date"]})
        
    if filters["branch"]:
        conds.update({"branch":filters["branch"]})
    
    return conds

def get_data_details(filters,cond):
    
    if filters["branch"]:
        
        fields = ['name','patient','service_room',"service_unit","concern",'appointment_time','call_back_status','duration',"custom_duration_time"]
        
        data_appointment = frappe.db.get_list("Patient Appointment",cond,fields,order_by='appointment_time asc')
        
        
        for i in data_appointment:
            i.update({f"{i['service_room']}":i['name']})
                 
        crm_field = ['name','date','time','customer_name','category','concern','status']
        crm_date = {"date":cond['appointment_date'],"branch":filters["branch"]}
        crm_appointment = frappe.db.get_list("Appointment",crm_date,crm_field,order_by='time asc')
        
        for i in crm_appointment:
            i.update({'appointment_time':i["time"]})
            i.update({f"{'Consultation Room'}":i['name']})
            
        total_data = data_appointment+crm_appointment
        
        if len(total_data)>0:
            
            total_data.sort(key=operator.itemgetter('appointment_time'))
            convert_data = pd.DataFrame.from_records(total_data)
            group_data = convert_data.groupby(by='appointment_time',as_index=False).sum()
            actual_data = group_data.to_dict("records")
            
        else:
            return []

                
        return actual_data
    

def get_columns(filters):
    # service_room = frappe.db.get_list("Healthcare Schedule Time Slot",pluck='name',order_by='service_room asc')
    columns = [
        {
			"label": _("Appointment Time"),
			"fieldname":"appointment_time",
			"fieldtype": "Time",
		},
        
    ]
    columns +=[

        {
            "label": _("Consultation Room"),
			"fieldname":"Consultation Room",
			"fieldtype": "Link",
            "options":'Appointment',
            # "width": 100
		},

  ]
    service_room = frappe.db.get_list("Service Room",{'service_room':('Not in',('Consultation Room')),'branch':filters["branch"]},pluck='name',order_by='service_room asc')
    columns += [{"label": _(each),"fieldname": each, "fieldtype": "Link", "options":'Patient Appointment',"wrap":True} for each in service_room]
    

    return columns

def report_summary(filters):
    
    not_answering  = 0
    closed = 0
    re_confirm = 0
    re_sechdule = 0
    cancel = 0
    
    row_data = frappe.db.sql("""
                             SELECT Count(call_back_status) as count,call_back_status from
                             `tabPatient Appointment` Where call_back_status IN ("Not Answering","Closed","Re-Confirm","Re-Scheduled","Cancel") And
                              appointment_date BETWEEN '{date}' And '{date}' And
                              branch ='{branch}' GROUP BY call_back_status
                             """.format(date=filters["date"],branch=filters["branch"]),as_dict=True)
        
    if len(row_data)<=0:
        
        report_summary_ = [
            {"label":"Not Answering","value":0,'indicator':'Red'},
            {"label":"Closed","value":0,'indicator':'Blue'},
            {"label":"Re-Confirm","value":0,'indicator':"Green"},
            {"label":"Re-Scheduled","value:":0,"indicator":"Orange"},
            {"label":"Cancel","value:":0,"indicator":"Red"}
            ]
        
        return report_summary_
    
    
    for i in row_data:
        
        if "Not Answering" in list(i.values()):
           not_answering = i['count']
        
        if "Closed" in list(i.values()):
           closed = i['count']
        
        if "Re-Confirm" in list(i.values()):
           re_confirm = i['count']
        
        if "Re-Scheduled" in list(i.values()):
           re_sechdule = i['count']
        if "Cancel" in list(i.values()):
           cancel = i['count']
        
    report_summary = [
    {"label":"Not Answering","value":not_answering if not_answering else 0,'indicator':'Red'},
    {"label":"Closed","value":closed if closed else 0,'indicator':'Blue'},
    {"label":"Re-Confirm","value":re_confirm if re_confirm else 0,'indicator':"Green"},
    {"label":"Re-Scheduled","value":re_sechdule if re_sechdule else 0,"indicator":"Orange"},
    {"label":"Cancel","value":cancel if cancel else 0,"indicator":"Red"}
    ]
        
    return report_summary