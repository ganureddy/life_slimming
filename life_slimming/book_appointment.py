import frappe
from frappe import _
import sys
import traceback
import datetime
from life_slimming.user_wise_roles import get_roles
from frappe.utils import add_to_date,now,today
import json

# Create clinet appointment through sales invoice

def create_appointment_through_si(data,method=None):
    
    new_entry = data.as_dict()
    
    therapy_plan_details = frappe.db.get_list("Therapy Plan",{'patient':new_entry.patient},['name'])
    
    next_appointment = frappe.db.get_list("Patient Appointment",{"patient":new_entry.patient,'call_back_status':"Scheduled",'appointment_date':(">=",(new_entry.poating_date))})
    
    if not next_appointment and therapy_plan_details:
        frappe.throw(
                _("Please Create Appointment For The First Therapy Session of {}").format(
                    frappe.bold("".join([new_entry.patient]))
                ),
            )
        


# Create clinet appointment through therapy sessions

def create_appointment_through_therapy_s(data,menthod=None):
    
    new_entry = data.as_dict()
    
    today_day = datetime.datetime.now().replace(minute=0, hour=0, second=0, microsecond=0)
        
    therapy_date = None
    
    if isinstance(new_entry.start_date,str):
        
        therapy_date = datetime.datetime.strptime(new_entry.start_date,"%Y-%m-%d").replace(minute=0, hour=0, second=0, microsecond=0)
    else:
        
        therapy_date = new_entry.start_date
            
    therapy_plane_details = frappe.db.get_list("Therapy Plan",{'name':new_entry.therapy_plan},['total_sessions_completed','total_sessions'])
    
    remaining_session = therapy_plane_details[0]['total_sessions'] - therapy_plane_details[0]["total_sessions_completed"] - 1
    
    if therapy_date >= today_day:
    
        next_appointment = frappe.db.get_list("Patient Appointment",{"patient":new_entry.patient,'call_back_status':"Scheduled",'appointment_date':(">=",(new_entry.start_date))})
        
        if remaining_session > 0 and not next_appointment:
            frappe.throw(
                    _("Please Take Next Appointment of Client {}").format(
                        frappe.bold("".join([new_entry.patient]))
                    ),
                )
        else:
            pass


# Restrict Service room base on room in patient appointment doctype
def service_room_restrict(doc,method=None):
    new_entry = doc.as_dict()
    service_room = new_entry.service_room
    date = new_entry.appointment_date
    time = new_entry.appointment_time
    status = new_entry.call_back_status
    
    exist_appointments = frappe.db.get_list(new_entry.doctype,{"service_room":service_room,"appointment_date":date,"appointment_time":time,'call_back_status':("in",("Re-Scheduled","Scheduled"))})
            
    if exist_appointments and status not in ['Not Answering','Closed','Re-Confirm',"Cancel"]:
        frappe.throw(
            _("Not allowed, Room {}").format(
                frappe.bold(", ".join([service_room,date,time]))
            ),
        )
    
# Change title name base on status in patient appointment doctype
def rename_base_on_conf_status(doc,method=None):
    try:
        if doc.appointment_time:
            start_datetime = datetime.datetime.strptime(doc.appointment_time, "%H:%M:%S")
            duration_timedelta = datetime.timedelta(minutes=doc.duration)
            end_datetime = start_datetime + duration_timedelta
            duration_time = end_datetime.strftime("%H:%M:%S")
            frappe.db.set_value("Patient Appointment",{"name":doc.name},{"custom_duration_time":duration_time})
            frappe.db.commit()
            
        old_name = doc.name
        
        new_name = f"{doc.patient_name}-{doc.concern}-{doc.call_back_status}-{doc.appointment_date}-{doc.appointment_time}"
        
        if old_name != new_name:
            frappe.rename_doc(doc.doctype, old_name, new_name,merge=False)
            
        doc.reload()
            
            
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "rename_base_on_conf_status")
        return {"success":True,"data":"Satatus is Update"}

        


# change patient Appointment status(closed) after therapy session is finish
def change_status(doc,method=None):
    try:
    
        new_entry = doc.as_dict()
        date = new_entry.start_date
        time = new_entry.start_time
        appointment = new_entry.appointment
            
        appointment_detail = frappe.db.get_list("Patient Appointment",{'name':appointment,'appointment_date':date,'call_back_status':"Re-Confirm"},['name','patient','concern'])
        
        if appointment_detail:
            
            frappe.db.set_value("Patient Appointment",appointment,{'call_back_status':'Closed'})
            frappe.db.commit()
            
            old_name = appointment_detail[0]['name']
            new_name = f"{appointment_detail[0]['patient']}-{appointment_detail[0]['concern']}-{'Closed'}-{date}-{time}"
            
            if old_name != new_name:
                
                frappe.rename_doc("Patient Appointment", old_name, new_name,merge=False)
                
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "change_status")

        
# create material issue (stock entry) through consumed items in therapy session

def issue_consumed_items_from_stock(self,method=None):
    consumed_data = frappe.db.get_list("Consumed Items", filters={"parent": self.name},
                                        fields=["item_code", "item_name", "uom", "quantity"],
                                        ignore_permissions=True)
    

    if consumed_data:
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")
        
        data_doc = {"doctype":"Stock Entry","stock_entry_type": "Material Issue","from_warehouse":f"{self.branch} - {company_abbr}"}
        items = []
        for item in consumed_data:
            items.append({
                "doctype": "Stock Entry Detail",
                "parent": "Stock Entry",
                "s_warehouse": f"{self.branch} - {company_abbr}",
                "item_code": item.item_code,
                "qty": item.quantity
            })
            
        data_doc.update({'items':items})
        issue_item = frappe.get_doc(data_doc)
        issue_item.docstatus = 1
        
        issue_item.insert()
        frappe.db.commit()

        frappe.msgprint(f"Material Issue created for {item.item_code}")


# To check therapy plan id and ref prectitioner            
def check_therapy_id_and_collected(doc,method=None):
        
    roles = get_roles(user=None,with_standard=True)
    
    if "Branch Sales Invoice" in roles:
        if not doc.therapy_plan_reference_id and not doc.ref_practitioner:
            frappe.throw("Please Check Therapy Plan Reference Id And Referring Practitioner are Present in Sales Invoice.")
        else:
            pass
    else:
        pass
    

# To Cancelled Invoice narration
def to_check_narration(doc,method=None):
    
    if  not doc.custom_narration:
        frappe.throw("Please Fill Narration Field About Cancelled Invoice")
    else:
        pass
    

# Custome api for client appointment (patient appointment) doctype
@frappe.whitelist(allow_guest=True)
def get_create_appointment(patient=None,appointment_date=None,
                           appointment_time=None,branch=None,service_room =None,
                           concern=None,service_unit=None
                           ):
    try:
        if service_unit.replace("- LSACPL",'') in  service_room:
            data = frappe.get_doc({"doctype":"Patient Appointment",
                                "patient":patient,"appointment_date":appointment_date,
                                "appointment_time":appointment_time,"branch":branch,
                                "service_room":service_room,"concern":concern,
                                "service_unit":service_unit
                                })
            data.save()
        
            return{
                "status":True,
                "message":f"Client Appointment Is Created:{data.name}"
            }
        else:
            return{
                "status":False,
                "message":f"{service_room}=!{service_unit}:Service Room Not Match With Service Uint"
            }
    except Exception as e:
        frappe.log_error(str(e))
        return {
            "status":False,
            "message":str(e),
        }
    
@frappe.whitelist(allow_guest=True)
def get_update_appointment(name=None,data=None):
    try:
        new_data=json.loads(data)
        if new_data.get("appointment_time"):
            appointment_detail = frappe.db.get_list("Patient Appointment",{'name':name},['name','patient','concern',"duration"])
            start_datetime = datetime.datetime.strptime(new_data["appointment_time"], "%H:%M:%S")
            duration_timedelta = datetime.timedelta(minutes=int(appointment_detail[0]["duration"]))
            end_datetime = start_datetime + duration_timedelta
            duration_time = end_datetime.strftime("%H:%M:%S")
            frappe.db.set_value("Patient Appointment",{"name":name},{"custom_duration_time":duration_time})
            frappe.db.commit()
            
        frappe.db.set_value("Patient Appointment",
                                    {
                                        "name":name
                                    },
                                    new_data
                                    )
        frappe.db.commit()
    
        
        return{
            "status":True,
            "message":'updated data'
        }
    except Exception as e:
        frappe.log_error(str(e))
        return {
            "status":False,
            "message":str(e),
        }

        
