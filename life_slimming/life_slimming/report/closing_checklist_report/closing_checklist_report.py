# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
import erpnext
from frappe import _
import sys
import traceback



def execute(filters=None):
    try:
        columns = get_columns()
        data = get_data(filters)
        return columns, data
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(
            exc_tb.tb_lineno, traceback.format_exc()), "execute")


def get_columns():
    return[
        {
            "label": _("Closing Checklist"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Closing Checklist",
            "width": 150,
        },
        {
            "label": _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Today's Total Sales"),
            "fieldname": "todays_total_sales",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Sales and petty cash properly locked"),
            "fieldname": "yes5",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Service rooms are perpared for next day"),
            "fieldname": "yes6",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("All the machines are turned off and properly cleaned"),
            "fieldname": "yes7",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Reception cleaned for the next day"),
            "fieldname": "yes8",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Wash rooms are cleaned for the next day"),
            "fieldname": "yes9",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Slimming station is cleaned and arranged properly"),
            "fieldname": "yes10",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Auto timer ON for sinage boards"),
            "fieldname": "yes11",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Daily planning and pipeline is updated"),
            "fieldname": "yes12",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Opening keys handed over to the concern person"),
            "fieldname": "yes13",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Main switch turned off"),
            "fieldname": "yes14",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("All divya and agarbathi are extingushed"),
            "fieldname": "yes15",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("All the dustbins cleaned and garbage kept outside the branch"),
            "fieldname": "yes16",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Duty roaster updated for the next day"),
            "fieldname": "yes17",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Sales cash tally and denomination"),
            "fieldname": "yes",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("500"),
            "fieldname": "count1",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("200"),
            "fieldname": "count2",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("100"),
            "fieldname": "count3",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("50"),
            "fieldname": "count4",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Petty cash tally and denomination"),
            "fieldname": "yes1",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("500"),
            "fieldname": "count6",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("200"),
            "fieldname": "count7",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("100"),
            "fieldname": "count8",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("50"),
            "fieldname": "count9",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("20"),
            "fieldname": "count10",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("10"),
            "fieldname": "count11",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Coins"),
            "fieldname": "coins",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Credit and debit card reconsilation"),
            "fieldname": "yes2",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Appointment reconfirmation for the next day"),
            "fieldname": "yes3",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Service consumption for the same day"),
            "fieldname": "yes4",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Total Amount"),
            "fieldname": "total_amount",
            "fieldtype": "Data",
            "width": 150,
        },

    ]


def get_conditions(filters):
    try:
        conditions = []
        conditions.append(
            f"DATE(creation) BETWEEN '{filters.from_date}' AND '{filters.to_date}'")
        if filters.get("branch"):
            conditions.append(f"and branch ='{filters.branch}'")
        if filters.get("from_date") > filters.get("to_date"):
            frappe.throw(
                _("{0} cannot be future days").format(
                    frappe.bold(_("From Date")))
            )
        return " ".join(conditions) if conditions else ""
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(
            exc_tb.tb_lineno, traceback.format_exc()), "get_conditions")


def get_data(filters):
    try:
        checklist_data = frappe.db.sql("""
									SELECT name,branch,yes,yes1,yes2,
			yes3,yes4,yes5,yes6,
            yes7,yes8,yes9,yes10,yes11,yes12,yes13,yes14,yes15,yes16,yes17,todays_total_sales,
            count1,count2,count3,count4,count6,count7,count8,count9,
            count10,count11,total_amount,coins from `tabClosing Checklist` where 
				{condition} ORDER BY creation 
				DESC""".format(condition=get_conditions(filters)), as_dict=1)
        print(checklist_data, "*****************")

        if len(checklist_data) > 0:
            for i in checklist_data:

                if i.yes == 1:
                    i.update({"yes": "Yes"})
                else:
                    i.update({"yes": "No"})

                if i.yes1 == 1:
                    i.update({"yes1": "Yes"})
                else:
                    i.update({"yes1": "No"})

                if i.yes2 == 1:
                    i.update({"yes2": "Yes"})
                else:
                    i.update({"yes2": "No"})

                if i.yes3 == 1:
                    i.update({"yes3": "Yes"})
                else:
                    i.update({"yes3": "No"})

                if i.yes4 == 1:
                    i.update({"yes4": "Yes"})
                else:
                    i.update({"yes4": "No"})

                if i.yes5 == 1:
                    i.update({"yes5": "Yes"})
                else:
                    i.update({"yes5": "No"})

                if i.yes6 == 1:
                    i.update({"yes6": "Yes"})
                else:
                    i.update({"yes6": "No"})

                if i.yes7 == 1:
                    i.update({"yes7": "Yes"})
                else:
                    i.update({"yes7": "No"})

                if i.yes8 == 1:
                    i.update({"yes8": "Yes"})
                else:
                    i.update({"yes8": "No"})
                if i.yes9 == 1:
                    i.update({"yes9": "Yes"})
                else:
                    i.update({"yes9": "No"})

                if i.yes10 == 1:
                    i.update({"yes10": "Yes"})
                else:
                    i.update({"yes10": "No"})
                if i.yes11 == 1:
                    i.update({"yes11": "Yes"})
                else:
                    i.update({"yes11": "No"})

                if i.yes12 == 1:
                    i.update({"yes12": "Yes"})
                else:
                    i.update({"yes12": "No"})
                if i.yes13 == 1:
                    i.update({"yes13": "Yes"})
                else:
                    i.update({"yes13": "No"})
                if i.yes14 == 1:
                    i.update({"yes14": "Yes"})
                else:
                    i.update({"yes14": "No"})

                if i.yes15 == 1:
                    i.update({"yes15": "Yes"})
                else:
                    i.update({"yes15": "No"})
                if i.yes16 == 1:
                    i.update({"yes16": "Yes"})
                else:
                    i.update({"yes16": "No"})

                if i.yes17 == 1:
                    i.update({"yes17": "Yes"})
                else:
                    i.update({"yes17": "No"})

                for count in ["count1", "count2", "count3", "count4", "count6", "count7", "count8", "count9", "count10", "count11"]:
                    i.update({count: i[count]})

        return checklist_data
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(
            exc_tb.tb_lineno, traceback.format_exc()), "get_data")

