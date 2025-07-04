import frappe
from frappe import _
from dateutil.relativedelta import relativedelta
from frappe.desk.doctype.dashboard_chart.dashboard_chart import get_result
from frappe.utils import getdate
from frappe.utils.dashboard import cache_source
from datetime import datetime
# from frappe.utils.dateutils import get_period


@frappe.whitelist()
@cache_source
def get_data(
    chart_name=None,
    chart=None,
    no_cache=None,
    filters=None,
    from_date=None,
    to_date=None,
    timespan=None,
    time_interval=None,
    heatmap_year=None,
) -> dict[str,list]:
    if filters:
        filters = frappe.parse_json(filters)

    if filters.get("from_date") and filters.get("to_date"):
        from_date = filters.get("from_date")
        to_date = filters.get("to_date")      
    else:
        today = datetime.now().strftime('%Y-%m-%d')
        from_date = today
        to_date = today

    label_data_list = []
    lead_dataset = []
    appointment_booked_dataset = []
    label_data = frappe.db.get_list("Branch",
                                    fields=["branch"],
		                            ignore_ifnull=True)
    
    for i in label_data:
        label_data_list.append(i["branch"])
        
        no_of_lead = frappe.db.get_all("Lead",
                                       filters={'lead_assign_to_branch':i['branch']},
                                       fields=['name','creation'])  
        status_lead = frappe.db.get_all("Lead",
                                        filters={'lead_assign_to_branch':i['branch'],
                                                 'status':'Appointment Booked'},
                                        fields=['name','creation'])
                
        date_object1 = datetime.strptime(from_date, '%Y-%m-%d').date()       
        date_object2 = datetime.strptime(to_date, '%Y-%m-%d').date()
        data1 = []
        data2 = []
        for j in no_of_lead:
            new_date1 = j['creation'].date()
            if date_object1 <= new_date1 <= date_object2 :
                data1.append(j)
        lead_dataset.append(len(data1))
        
        for k in status_lead :
            new_date2 = k['creation'].date()
            if date_object1 <= new_date2 <= date_object2 :
                data2.append(k)
        appointment_booked_dataset.append(len(data2))
        
 
    return {
        "labels": label_data_list,
        "datasets":[
            {"name": _("Total Lead"), "values":lead_dataset},
            {"name": _("Appointment Booked"), "values":appointment_booked_dataset}
            ],
        
    }
  
 