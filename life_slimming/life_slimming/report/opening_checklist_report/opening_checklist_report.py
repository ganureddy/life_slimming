# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt


import frappe
import erpnext
from frappe import _
import sys
import traceback

def execute(filters=None):
	try:       
		columns=get_columns()
		data = get_data(filters)
		return columns, data
	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "execute")
def get_columns():
	return[
	 		{
				"label": _("Opening Checklist"),
				"fieldname": "name",
				"fieldtype":"Link",
				"options": "Opening Checklist",
				"width":150,
			},
	   		{
				"label" : _("Branch"),
				"fieldname":"branch",
				"fieldtype": "Data",
				"width":150,
			},
			{
				"label": _("Date"),
				"fieldname":"date",
				"fieldtype" : "Data",
				"width":150,
         	},
		 	{
				"label" : _("Sinage board is clean"),
				"fieldname":"completed1",
				"fieldtype": "Data",
				"width":150,
		 	},
			{
				"label" : _("Area outside the entrance is clean"),
				"fieldname":"completed2",
				"fieldtype": "Data",
				"width":150,
		 	},
			{
				"label" : _("Reception area & treament rooms are neat & Clean"),
				"fieldname":"completed3",
				"fieldtype": "Data",
				"width":150,
		 	},
			{
				"label" : _("Consultation rooms are cleaned & organised for consultation"),
				"fieldname":"completed4",
				"fieldtype": "Data",
				"width":150,
		 	},
			{
				"label" : _("Washrooms are cleaned properly"),
				"fieldname":"completed5",
				"fieldtype": "Data",
				"width":150,
		 	},
			{
				"label": _("Sales & petty cash inhand tallied"),
				"fieldname":"completed6",
				"fieldtype" : "Data",
				"width" :150,
		 	},
			{
				"label": _("Generator is in working condition & is having enough desile"),
				"fieldname":"completed7",
				"fieldtype" : "Data",
				"width" :150,
		 	},
			{
				"label": _("All the machines are checked for working condition"),
				"fieldname":"completed8",
				"fieldtype" : "Data",
				"width" :150,
		 	},
	   ]

def get_conditions(filters):
	try:
		conditions = []
		conditions.append(f"DATE(creation) BETWEEN '{filters.from_date}' AND '{filters.to_date}'")
		if filters.get("branch"):
			conditions.append(f"and branch ='{filters.branch}'")
		if filters.get("from_date") > filters.get("to_date"):
			frappe.throw(
				_("{0} cannot be future days").format(frappe.bold(_("From Date")))
			)
		return " ".join(conditions) if conditions else ""
	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "get_conditions")
def get_data(filters):
	try:
		checklist_data = frappe.db.sql("""
									SELECT name,branch,date,completed1,completed2,
			completed3,completed4,completed5,completed6,
			completed7,completed8 from `tabOpening Checklist` where 
				{condition} ORDER BY creation 
				DESC""".format(condition=get_conditions(filters)), as_dict=1)
		print(checklist_data,"*****************")

		if len(checklist_data) > 0:
			for i in checklist_data:
				
				if i.completed1 == 1 :
					i.update({"completed1":"Yes"})
				else: 
					i.update({"completed1":"No"})
     
				if i.completed2 == 1 :
					i.update({"completed2":"Yes"})
				else: 
					i.update({"completed2":"No"})
     
				if i.completed3 == 1 :
					i.update({"completed3":"Yes"})
				else: 
					i.update({"completed3":"No"})
     
				if i.completed4 == 1 :
					i.update({"completed4":"Yes"})
				else: 
					i.update({"completed4":"No"})
     
				if i.completed5 == 1 :
					i.update({"completed5":"Yes"})
				else: 
					i.update({"completed5":"No"})
     
				if i.completed6 == 1 :
					i.update({"completed6":"Yes"})
				else: 
					i.update({"completed6":"No"})
     
				if i.completed7 == 1 :
					i.update({"completed7":"Yes"})
				else: 
					i.update({"completed7":"No"})
     
				if i.completed8 == 1 :
					i.update({"completed8":"Yes"})
				else: 
					i.update({"completed8":"No"})
     
		return checklist_data
	except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "get_data")
