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

    if filters:
        from_date = filters.get("from_date")
        to_date = filters.get("to_date")

    else:
        today = datetime.now().strftime('%Y-%m-%d')
        from_date = today
        to_date = today

    conditions = f" Date(creation) between '{from_date}' and '{to_date}'"

    raw_data = frappe.db.sql('''Select lead_owner , Count(name) as count from 
                                `tabLead` where {0} Group By lead_owner Order by count desc'''.format(conditions),as_dict =1)


    new_date = []
    if len(raw_data) >0:
        for i in raw_data:
            value = {}
            lead_ower_name = frappe.db.get_list('User',{'email':i['lead_owner']},['full_name'])
            if len(lead_ower_name)>0:
                value['full_name'] = lead_ower_name[0]['full_name']
                value['count'] = i['count']

                new_date.append(value)

    label_data_list = [value['full_name'] for value in new_date]
    lead_dataset = [value['count'] for value in new_date]
    
    return {
        "labels": label_data_list,
        "datasets":[
            {"values":lead_dataset}
            ],
    }
  
 