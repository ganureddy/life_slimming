import frappe
from datetime import datetime ,timedelta, date, time
from frappe.utils import add_to_date,now,today
from frappe import _
from frappe.model.mapper import get_mapped_doc
import requests
import gspread as gs
import json
from frappe.utils import cstr 
import openpyxl
import pandas as pd
import sys
import traceback
 
  
# To fetch data to customer_details feild for calander_view 
def fetch_details_data(doc,method=None): 
    if doc.get("custom_cc_booking"):
        return
    # try: 
    fetch_data = frappe.db.get_list("Appointment",filters={'name':doc.name},
                                    fields=['branch','category','concern','customer_name'])
    data = f"{fetch_data[0].branch}\n{fetch_data[0].category}\n{fetch_data[0].concern}\n{fetch_data[0].customer_name}"   
    insert_data = frappe.db.set_value('Appointment', doc.name, 'customer_details', data)
    frappe.db.commit()
    frappe.reload_doctype("Appointment")  
    # except Exception as e:
    #     print(e)

  
def set_appointment_time(doc,method=None):
    if doc.get("custom_cc_booking"):
        return
    # try:
    appointment_data = frappe.db.get_list("Appointment",filters={'name':doc.name},
                                        fields=['scheduled_time','duration','customer_phone_number'])
    # Restrict past date and time to create appointment
    # if not frappe.db.exists({'doctype':'Appointment','customer_phone_number':appointment_data[0]['customer_phone_number']}):
    if appointment_data[0]['scheduled_time'] <= datetime.now() :
        frappe.throw("Appointment cannot be create to past date and time")
        # return False
    else:
        # To set end_time, add start time with duration to get end time  
        new_time = add_to_date(appointment_data[0]['scheduled_time'], 
                            minutes=int(appointment_data[0]['duration'].replace('Minutes',"").replace("1 Hour","60")))
        set_time = frappe.db.set_value('Appointment', doc.name, 'appointment_time', new_time)

        # Restrict appointment, if it is already created appointment slot with branch wise
        get_data = frappe.db.get_list("Appointment",filters={'branch':doc.branch,'date':doc.date},
                                    fields=['name','branch','scheduled_time',
                                            'appointment_time','time','duration','date'])
        for i in get_data:
            if i['name'] != doc.name :
                new_datetime = datetime.strptime(doc.scheduled_time, '%Y-%m-%d %H:%M:%S')
                start_time = i['scheduled_time'].strftime('%Y-%m-%d %H:%M:%S')
                new_start_date = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                end_time = i['appointment_time'].strftime('%Y-%m-%d %H:%M:%S')
                new_end_date = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                if new_start_date <= new_datetime <= new_end_date :
                    frappe.throw("This Appointment slot is already booked")
        frappe.db.commit()
    # except Exception as e:
    #     # exc_type, exc_obj, exc_tb = sys.exc_info()
    #     # frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "set_appointment_time")    
    #     print(e)
        
   
# Total No. of Leads
@frappe.whitelist()
def total_lead(**var):
    filters_details = frappe.parse_json(var['filters'])
    # print(filters_details,"///////////////////////")
    try:
        filters = {}

        if filters_details['company']:
            filters["company"] = filters_details['company']

        filters['creation'] = ['between',(filters_details['undefined'],filters_details['to_date'])]

        # print(filters,"/////////////////,,,,,,,,,,,,,,,,,,")
            
        data = frappe.db.get_all(
                    'Lead',
                    filters = filters,
                    fields=["count(name) as Count"] 
                )[0].Count 
        return data
    except Exception as e:
        print(e)
 
      

# Create Number cards for the Appointments with filter "future appointment"
@frappe.whitelist()
def future_appointment(company=None,from_date = None,to_date = None):
    try:
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date

        now = datetime.now()
        appointment_data = """
                SELECT name,creation,scheduled_time
                FROM `tabAppointment`
                WHERE `scheduled_time` > %(now)s
            """
        results = frappe.db.sql(appointment_data, {'now': now},as_dict=True)
 
        return len(results)

    except Exception as e:
        print(e)


 
   
# Create Number cards for the leads with "Lead" status 
@frappe.whitelist()
def lead_status(company=None,from_date=None,to_date=None,status='Lead'):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Lead":
                status_lead = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count 
                return status_lead
        else: 
            return 0
    except Exception as e:
        print(e)   
        

        
# Create Number cards for the leads with "Open" status        
@frappe.whitelist()
def open_status(company=None,from_date=None,to_date=None,status="Open"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Open":
                status_open = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                          
                return status_open
        else: 
            return 0
 
    except Exception as e:
        print(e)   
        
        
        
# Create Number cards for the leads with "Call Back" status         
@frappe.whitelist()
def call_back_status(company=None,from_date=None,to_date=None,status="Call Back"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Call Back":
                status_call_back = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count 
                return status_call_back 
    
        else :
            return 0

    except Exception as e:
        print(e)   
   
   
        
# Create Number cards for the leads with "Get Back" status        
@frappe.whitelist()
def get_back_status(company=None,from_date=None,to_date=None,status="Get Back"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Get Back":
                status_get_back = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_get_back 
        else:
            return 0
    except Exception as e:
        print(e)  
        

# Create Number cards for the leads with "Consultation Done" status 
@frappe.whitelist()
def consultation_done_status(company=None,from_date=None,to_date=None,status="Consultation Done"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Consultation Done":             
                status_consultation_done = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_consultation_done
        else:
            return 0
    except Exception as e:
        print(e)  
        


# Create Number cards for the leads with "DND" status 
@frappe.whitelist()
def dnd_status(company=None,from_date=None,to_date=None,status="DND"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "DND":             
                status_dnd = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_dnd
        else: 
            return 0
  
    except Exception as e:
        print(e)  




# Create Number cards for the leads with "NID" status 
@frappe.whitelist()
def nid_status(company=None,from_date=None,to_date=None,status="NID"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "NID":             
                status_nid = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count
                  
                return status_nid 
        else: 
            return 0
  
    except Exception as e:
        print(e)  
        


# Create Number cards for the leads with "Interested" status         
@frappe.whitelist()
def interested_status(company=None,from_date=None,to_date=None,status="Interested"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Interested":             
                status_interested = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_interested
        else: 
            return 0
  
    except Exception as e:
        print(e)  




# Create Number cards for the leads with "Appointment Booked" status 
@frappe.whitelist()
def appointment_booked_status(company=None,from_date=None,to_date=None,status="Appointment Booked"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Appointment Booked":             
                status_appointment_booked = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_appointment_booked 
        else: 
            return 0
  
    except Exception as e:
        print(e)  




# Create Number cards for the leads with "Not Interested" status 
@frappe.whitelist()
def not_interested_status(company=None,from_date=None,to_date=None,status="Not Interested"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Not Interested":             
                status_not_interested = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_not_interested
        else:
            return 0
    except Exception as e:
        print(e)  
        


# Create Number cards for the leads with "Not Response" status 
@frappe.whitelist()
def not_response_status(company=None,from_date=None,to_date=None,status="Not Response"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Not Response":             
                status_not_response = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_not_response
        else:
            return 0
    except Exception as e:
        print(e)  



# Create Number cards for the leads with "Existing Client" status 
@frappe.whitelist()
def existing_client_status(company=None,from_date=None,to_date=None,status="Existing Client"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Existing Client":             
                status_existing_client = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_existing_client
        else:
            return 0
    except Exception as e:
        print(e)  


# Create Number cards for the leads with "Wrong Call" status 
@frappe.whitelist()
def wrong_call_status(company=None,from_date=None,to_date=None,status="Wrong Call"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Wrong Call":             
                status_wrong_call = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_wrong_call
        else:
            return 0
    except Exception as e:
        print(e)  
        
        
# Create Number cards for the leads with "Switch Off" status 
@frappe.whitelist()
def switch_off_status(company=None,from_date=None,to_date=None,status="Switch Off"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Switch Off":             
                status_switch_off = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_switch_off
        else:
            return 0
    except Exception as e:
        print(e)  
        
 
        
# Create Number cards for the leads with "Not Enquired" status 
@frappe.whitelist()
def not_enquired_status(company=None,from_date=None,to_date=None,status="Not Enquired"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Not Enquired":             
                status_not_enquired = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_not_enquired
        else:
            return 0
    except Exception as e:
        print(e)  
        


# Create Number cards for the leads with "Appointment No Response" status 
@frappe.whitelist()
def appointment_no_response_status(company=None,from_date=None,to_date=None,status="Appointment No Response"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Appointment No Response":             
                status_appointment_no_response = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_appointment_no_response
        else:
            return 0
  
    except Exception as e:
        print(e)  
        
        
# Create Number cards for the leads with "TNA" status        
@frappe.whitelist()
def tna_status(company=None,from_date=None,to_date=None,status="TNA"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "TNA":             
                status_tna = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_tna
        else:
            return 0
  
    except Exception as e:
        print(e) 
       
        
# Create Number cards for the leads with "Out of Service" status        
@frappe.whitelist()
def out_of_service_status(company=None,from_date=None,to_date=None,status="Out of Service"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Out of Service":             
                status_out_of_service = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count  
                return status_out_of_service
        else:
            return 0
    except Exception as e:
        print(e)  
         


# Create Number cards for the leads with "Not Reachable" status 
@frappe.whitelist()
def not_reachable_status(company=None,from_date=None,to_date=None,status="Not Reachable"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Not Reachable":             
                status_not_reachable = frappe.db.get_all("Lead",
                                filters = filters , 
                                fields=["count(name) as Count"])[0].Count
                
                return status_not_reachable
        else:
            return 0
    except Exception as e:
        print(e)  




# Create Number cards for the leads with "Joined" status 
@frappe.whitelist()
def joined_status(company=None,from_date=None,to_date=None,status="Joined"):
    try:
        status_data = frappe.db.get_list("Lead", fields=['status'])
        filters = {}
        if company:
            filters["company"] = company
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        if status:
            filters["status"] = status
        for i in status_data:
            if i['status'] == "Joined":             
                status_joined = frappe.db.get_all("Lead",
                                            filters = filters , 
                                            fields=["count(name) as Count"])[0].Count  
                return status_joined
        else:
            return 0
  
    except Exception as e:
        print(e)  


# call back alter.
@frappe.whitelist()
def update_call_back_status():
    try:
        
        user_name = frappe.session.user
        if user_name not in ['All', 'Guest', 'Administrator']:
            date = datetime.now().date()
            get_data = frappe.db.sql('''Select l.name,l.first_name,l.mobile_no,f.followup_next_date,
                                    f.time from `tabLead` as l ,`tabFollowup` as f
                                    where l.lead_owner = '{user_name}' and l.status = 'Call Back' and l.name = f.parent and
                                    f.followup_next_date = '{date}' 
                                    '''.format(user_name=user_name,date=date),as_dict=True)
            test_data = []
            # for i in get_data:
            #     followup_next_date = i["followup_next_date"]
            #     followup_next_time = i['time']
            #     now_date =  datetime.now().date()
            #     now_time = datetime.now()
            #     total_sec = now_time.hour*3600 + now_time.minute*60     
            #     now_time_value = timedelta(seconds=total_sec) 
            #     followup_lead = i['name']
            #     print(followup_next_date,'------------',now_date,'--------',followup_next_date == now_date)
            #     print(followup_next_time,'------------',now_time_value,'--------',followup_next_time == now_time_value)
            #     if followup_next_date == now_date and followup_next_time == now_time_value:
            #         test_data.append(i)
            # if len(test_data)>0:
            return {"Message":True,'Data':get_data}
            # else:
            #     return {'Message':False,'Data':[]}
                
    except Exception as e:
        print(e)
        


# not entry duplicate lead
def restrict_duplicate_lead(doc,method=None):
    without_91_or_with91 = doc.mobile_no[-8:]
    # data = frappe.db.get_list('Lead',{'mobile_no':('Like',(f'%{without_91_or_with91}%'))},['name',"first_name","mobile_no"])
    data = frappe.db.sql('''Select name,first_name,mobile_no from `tabLead` Where mobile_no LIKE '%{mobile}' '''.format(mobile = without_91_or_with91),as_dict=1)
    for i in data:
        if i.name != doc.name:
            if not frappe.db.exists({'doctype':'Lead','mobile_no':i['mobile_no']}):
                pass
            else:
                frappe.throw("Lead already exists and mobile No. is {}".format(i["mobile_no"]))
                
# Create new lead           
def new_lead_doc(doc,method=None):
    
    marketing_lead_data = frappe.db.get_list("Marketing Lead", filters={"parent":doc.name},
                                            fields=['first_name','gender','age',
                                                    'enquired_for','client_area','email',
                                                    'mobile_no'])
    for i in marketing_lead_data:
        new_lead_doc = frappe.get_doc({
            "doctype" : "Lead",
            "first_name": i['first_name'],
            "lead_name" : i['first_name'],
            "gender": i['gender'],
            "age": i['age'],
            "enquired_for": i['enquired_for'],
            "mobile_no": i['mobile_no'],
            "city": i['client_area'],
            "email_id": i['email']
        })
        new_lead_doc.insert()
        
        
        
    
# # Fetching google sheet and read the data for may month
# @frappe.whitelist()
# def get_google_sheet_data(sheet_name):
# 	try:
# 		# Fetching the path of the site
# 		folder_path = frappe.utils.get_bench_path()
# 		site_name = cstr(frappe.local.site)
# 		file_path = (folder_path+"/sites/"+site_name)
        
# 		gc = gs.service_account(filename=f'{file_path}/pipedream-integration-389109-e09d84a95703.json')
# 		sh = gc.open_by_url('https://docs.google.com/spreadsheets/d/1WUb_iV-XAkWHEhX_BEIdyy6cOmInbiHiIRhr8RAaE9k/edit#gid=1650927659')
# 		spreadsheets = [spreadsheet.get_all_values() for spreadsheet in sh]
# 		headers = [data.pop(0) for data in spreadsheets]		
# 		data = [pd.DataFrame(spreadsheets[i],columns = headers[i]) for i in range(0,len(spreadsheets))][1]
        
# 		return data.to_json()
# 	except Exception as e:
# 		exc_type, exc_obj, exc_tb = sys.exc_info()
# 		frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "get_google_sheet_data")




  
# # Getting google sheet data from get_google_sheet_data function and create leads
# @frappe.whitelist(allow_guest=True)
# def google_sheet_integration(data):
#     try:
#         frappe.log_error(f"test parameter pass value :{data}")
#         data_1 = get_google_sheet_data(data)
#         data_1 = json.loads(data_1)
#         for j in range(0,len(data_1['Name'])):
#             first_name = data_1['Name'][str(j)]
            
#             remove_extra_char=data_1['Phone no'][str(j)][5:]
            
#             mobile_no = remove_extra_char
#             email_id = data_1["Email Id"][str(j)]
            
#             datetime_str = data_1["Call back time"][str(j)]
#             datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S%z")
#             date_obj = datetime_obj.date()
#             time_obj = datetime_obj.time()
            
#             followup_next_date = date_obj
#             time = time_obj
#             ad_set = data_1["Ad Set"][str(j)]

#             # enquired_for = data_1['Enquired For'][str(j)]
#             if frappe.db.exists("Lead",{"mobile_no": ('Like',(f'%{mobile_no[-8:]}%'))}):
#                 pass
                
#             else:
#                 new_lead = frappe.get_doc({
#                     'doctype': "Lead",
#                     'first_name':first_name,
#                     'mobile_no': mobile_no,
#                     'email_id': email_id,
#                     'ad_set': ad_set,
#                     'followup': [{
#                         'followup_next_date': followup_next_date,
#                         'time':time
#                     }]
#                     # 'enquired_for': enquired_for
#                 })
#                 new_lead.insert()
#                 frappe.db.commit()
#         return {"Message":True}
#     except Exception as e:
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "google_sheet_integration")
  




# Fetching google sheet data and test in dev site 

def get_google_sheet_data(sheet_id):
    try:
        # Fetching the path of the site
        print(sheet_id)
        folder_path = frappe.utils.get_bench_path()
        site_name = cstr(frappe.local.site)
        file_path = (folder_path+"/sites/"+site_name)       
        gc = gs.service_account(filename=f'{file_path}/pipedream-integration-389109-e09d84a95703.json')
        sh = gc.open_by_url('https://docs.google.com/spreadsheets/d/1WUb_iV-XAkWHEhX_BEIdyy6cOmInbiHiIRhr8RAaE9k/edit')
        print(sh,"//////////////////////")
        
        sheet_value = []
        for i in sh:
            if int(sheet_id) == int(i.id):
                sheet_value.append(i)
                
        spreadsheets = [spreadsheet.get_all_values() for spreadsheet in sheet_value]
        headers = [data.pop(0) for data in spreadsheets]
        columns = []
        for i in headers[0]:
            columns.append(i.strip())
        
        headers = [columns]
        
        url = (f'https://docs.google.com/spreadsheets/d/1bxIkZY6WAedDl1S78PepABcEC_5il-ecrq1IGqdgL7M/edit#gid={sheet_id}')
        
        gc = gs.service_account(filename=f'{file_path}/google_service_account.json')
        sh = gc.open_by_url(f'https://docs.google.com/spreadsheets/d/1bxIkZY6WAedDl1S78PepABcEC_5il-ecrq1IGqdgL7M/edit')
        sheet_value = []
        for i in sh:
            if sheet_id == i.id:
                sheet_value.append(i)
            
        print(sheet_value)
        
        # print(sh.get_all_values())
        spreadsheets = [spreadsheet.get_all_values() for spreadsheet in sheet_value]
        headers = [data.pop(0) for data in spreadsheets]		
        data = [pd.DataFrame(spreadsheets[i],columns = headers[i]) for i in range(0,len(spreadsheets))][0]
        df = data.loc[:,'Name':]
        
        return df.to_json()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "get_google_sheet_data")




def google_sheet_integration(sheet_id):
    try:
        raw_data = get_google_sheet_data(sheet_id)
        data = json.loads(raw_data)
        for j in range(0,len(data['Name'])):
            if data['Name'][str(j)] != '' and (data['Phone no'][str(j)] != '' and data['Phone no'][str(j)] != '#ERROR!'):
                first_name = data['Name'][str(j)]
                
                remove_extra_char=data['Phone no'][str(j)]
                
                if 'p:' in remove_extra_char:
                    mobile_no = remove_extra_char.replace('p:','').strip()
                else:      
                    if len(remove_extra_char.strip()) <=13:    
                        mobile_no = remove_extra_char.strip()
                    else:
                        continue
                
                if frappe.db.exists("Lead",{"email_id": ('Like',(f'%{data["Email Id"][str(j)]}%'))}):
                    email_id = None
                else:
                    email_id = data["Email Id"][str(j)] if "@" in data["Email Id"][str(j)] else None 
                       
                enquired_for =data["Campaign"][str(j)]
                ad_set = data["Ad Set"][str(j)] 
            else:
                continue
 
            if frappe.db.exists("Lead",{"mobile_no": ('Like',(f'%{mobile_no[-8:]}%'))}):
                pass   
            else:
                new_lead = frappe.get_doc({
                    'doctype': "Lead",
                    'first_name':first_name,
                    'mobile_no': mobile_no,
                    'email_id': email_id,
                    'enquired_for': enquired_for,
                    'ad_set': ad_set,
                })
                new_lead.insert(ignore_permissions = True)
                frappe.db.commit()
                
        return {"Message":True}
        
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "google_sheet_integration")
        
@frappe.whitelist(allow_guest=True)
def background_jobs_for_leads():
    print(";;;;;;;;;;;;;;;;;;;")
    try:
        frappe.enqueue(
        "life_slimming.events.google_sheet_integration", # python function or a module path as string
        queue="default", # one of short, default, long
        timeout=80000, # pass timeout manually
        is_async=True, # if this is True, method is run in worker
        now=True, # if this is True, method is run directly (not in a worker)
        sheet_id = 1278507161,
        job_name="Create Lead from Google Sheet", # specify a job name
        enqueue_after_commit=False, # enqueue the job after the database commit is done at the end of the request
        at_front=False, # put the job at the front of the queue
        # kwargs are passed to the method as arguments
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "background_jobs_for_leads")
    
  


# Creating Sales Invoice from Therapy Plan through a button
@frappe.whitelist()
def create_si_item_from_therapy_type(name):
    try:
        sii_data = frappe.db.get_list("Therapy Plan Detail",filters={"parent":name},fields=['parent','parenttype','therapy_type','no_of_sessions',"custom_is_offer_"],ignore_permissions = True)
        for i in sii_data:
            theray_type_item_code = frappe.db.get_value('Therapy Type',i['therapy_type'], 'item_code')
            item_detali = frappe.db.get_list('Item',{'item_code':theray_type_item_code},['item_code','stock_uom','description'])
            if item_detali:
                i.update(item_detali[0])
            else:
                frappe.throw("No Item Detail found for Therapy Type")
        return sii_data
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "create_si_item_from_therapy_type")
        
        
 


# def closing_checklist_data(doc, method=None):
#     try:
#         checklists = frappe.get_all("Closing Checklist", filters={
#             "name": doc.name}, fields=["name", "branch", "five_hundred", "two_hundred",
#                                        "hundred", "fifty", "count1", "count2", "count3", "count4", "amount1", "amount2", "amount3", "amount4",
#                                        "five_hundred1", "two_hundred1", "hundred1", "fifty1", "twenty", "ten", "count6", "count7", "count8", "count9",
#                                        "count10", "count11", "amount6", "amount7", "amount8", "amount9", "amount10", "amount11", "total_amount", "coins"])

#         for checklist in checklists:
#             doc.amount1 = int(checklist["five_hundred"]) * int(checklist["count1"])
#             doc.amount2 = int(checklist["two_hundred"]) * int(checklist["count2"])
#             doc.amount3 = int(checklist["hundred"]) * int(checklist["count3"])
#             doc.amount4 = int(checklist["fifty"]) * int(checklist["count4"])
#             doc.amount6 = int(checklist["five_hundred1"]
#                               ) * int(checklist["count6"])
#             doc.amount7 = int(
#                 checklist["two_hundred1"]) * int(checklist["count7"])
#             doc.amount8 = int(checklist["hundred1"]) * int(checklist["count8"])
#             doc.amount9 = int(checklist["fifty1"]) * int(checklist["count9"])
#             doc.amount10 = int(checklist["twenty"]) * int(checklist["count10"])
#             doc.amount11 = int(checklist["ten"]) * int(checklist["count11"])

#             doc.total_amount = doc.amount1 or ''+doc.amount2 or ''+doc.amount3 or ''+doc.amount4 or ''+doc.amount6 or ''+ \
#                 doc.amount7 or ''+doc.amount8 or ''+doc.amount9 or ''+ \
#                 doc.amount10+doc.amount11+int(doc.coins) or ''

#             # print(doc.amount2, '++++++++++++++++++++++++++')
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "amount1", doc.amount1)
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "amount2", doc.amount2)
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "amount3", doc.amount3)
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "amount4", doc.amount4)
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "amount6", doc.amount6)
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "amount7", doc.amount7)
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "amount8", doc.amount8)
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "amount9", doc.amount9)
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "amount10", doc.amount10)
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "amount1", doc.amount11)
#             frappe.db.set_value("Closing Checklist",
#                                 checklist["name"], "total_amount", doc.total_amount)


#     except Exception as e:
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "closing_checklist_data")
        




#  Restricting sales invoice item rate within therapy type minimum, maximum rate if there is no pricing rule for this item
def sii_rate_within_therapy_type_min_max_rate(doc, method=None):
    
    sii_data = frappe.db.get_list("Sales Invoice Item",filters={"parent":doc.name},
                                  fields= ["item_code","rate"],ignore_permissions=True)
    price_rule_table = frappe.db.get_list("Pricing Rule Detail", filters={"parent": doc.name},
                                          fields=["pricing_rule","item_code"],ignore_permissions=True)
    
    item_codes_to_match = [data['item_code'] for data in price_rule_table]
    
    role_data = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, 
                               fields=["role"], ignore_permissions=True)
    head_of_accounts = [i for i in role_data if i.role == "Head of Accounts" and frappe.session.user != doc.owner]
    
    if len(head_of_accounts)==0:
        
        for data in sii_data:
            
            if data['item_code'] in item_codes_to_match :
                continue
            else :
                minimum_rate,maximum_rate = frappe.db.get_value("Therapy Type", {"item_code":data['item_code']},
                                                                ["minimum_price","maximum_price"])
                if minimum_rate > data['rate']:
                    frappe.throw("{} can't be less than minimum price of {}".format(data['item_code'],minimum_rate))
                elif maximum_rate < data['rate']:
                    frappe.throw("{} can't be more than maximum price of {}".format(data['item_code'], maximum_rate))
                
               
                
def restrict_therapy_session_without_payment(doc,method=None):
    therapy_plan = frappe.db.get_value(
        "Therapy Plan",
        doc.therapy_plan,
        ["therapy_plan_already_taken_"],
        as_dict=True
    )

    if therapy_plan and therapy_plan.therapy_plan_already_taken_:
        return

    sales_invoice_id = frappe.db.get_value("Sales Invoice",{"therapy_plan_reference_id":doc.therapy_plan,"docstatus":1},["name"])
    if sales_invoice_id:
        try:
            total,outstanding,status = frappe.db.get_value("Sales Invoice",
                                                        {"name":sales_invoice_id,'docstatus':1},
                                                        ["grand_total","outstanding_amount","status"])
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "restrict_therapy_session_without_payment")
            
        if status != "Paid" and status != "Draft":
            try:
                total_sessions,complete_session_number = frappe.db.get_value("Therapy Plan",
                                                        {"name":doc.therapy_plan},["total_sessions","total_sessions_completed"])
                print(total_sessions,complete_session_number)
            except Exception as e:
                frappe.throw("Please Check Therapy Plane, No of Sessions Is Zero")
                exc_type, exc_obj, exc_tb = sys.exc_info()
                frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "restrict_therapy_session_without_payment")
                
            paid_amount = round(total - outstanding)
            per_session_cost = round(total/total_sessions)
                 
            if paid_amount != 0:
                   
                paid_sessions_count = round(paid_amount/per_session_cost)
                
                if paid_sessions_count == complete_session_number:               
                    frappe.throw("Not enough payment for next Therapy Session")
    else:
        frappe.throw(
            _("Please Check Sales Invoice of This Therapy Plan And Id Of therapy Plan Is {}").format(
                frappe.bold(", ".join([doc.therapy_plan]))
            ),
            )
            
    