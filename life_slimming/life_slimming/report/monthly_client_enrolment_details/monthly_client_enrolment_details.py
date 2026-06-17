# Copyright (c) 2025, swathi and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns, data = [], []
	return columns, data



# import frappe
# from frappe import _
# from frappe.query_builder.functions import Sum


# def execute(filters=None):
# 	columns, data = [], []
# 	data = get_data(filters)
# 	columns = get_column(filters)  # fixed typo
# 	return columns, data

# def get_data(filters):
#     cl = frappe.qb.DocType("Patient")
#     tp = frappe.qb.DocType("Therapy Plan")
#     si = frappe.qb.DocType("Sales Invoice")

#     query = (
#         frappe.qb.from_(cl)
#         .right_join(tp).on(tp.patient == cl.name)
#         .right_join(tp).on(tp.name == si.therapy_plan_reference_id)
#         .select(
#             cl.name.as_("client"),
#             cl.first_name,
#             cl.mobile,
#             cl.branch,
# 			tp.name.as_("therapy_plan"),
#             tp.category,
#             tp.start_date,
#             tp.custom_employee_name,
#             tp.branch,
#             si.grand_total,
#         )
#     )

#     if filters.get("from_date"):
#         query = query.where(tp.start_date >= filters.get("from_date"))

#     if filters.get("to_date"):
#         query = query.where(tp.start_date <= filters.get("to_date"))

#     if filters.get("client"):
#         query = query.where(cl.name == filters.get("client"))

#     if filters.get("category"):
#         query = query.where(tp.category == filters.get("category"))

#     if filters.get("branch"):
#         query = query.where(tp.branch == filters.get("branch"))

#     raw_data = query.run(as_dict=True)

#     # Post-processing: apply item_code == therapy_type and allocated amount logic
#     final_data = []
#     for row in raw_data:
#         final_data.append({
#             "client_name": row.client,
#             "first_name": row.first_name,
#             "mobile": row.mobile,
#             "therapy_plan": row.therapy_plan,
#             "branch": row.branch,
#             "category": row.category,
#             "start_date": row.start_date,
#             "custom_employee_name": row.custom_employee_name,
# 			"branch": row.branch,
# 			"grand_total": row.grand_total
#         })

#     return final_data

# def get_column(filters):
# 	columns = [
# 		{
# 			"fieldname": "client_name",
# 			"fieldtype": "Link",
# 			"label": _("Client"),
# 			"options": "Patient",
# 			"width": 160
# 		},
# 		{
# 			"fieldname": "first_name",
# 			"fieldtype": "Data",
# 			"label": _("Client Name"),
# 			"width": 160
# 		},
# 		{
# 			"fieldname": "mobile",
# 			"fieldtype": "Date",
# 			"label": _("Client Mobile No"),
# 			"width": 140
# 		},
# 		{
# 			"fieldname": "therapy_plan",
# 			"fieldtype": "Link",
# 			"label": _("Therapy Plan"),
# 			"options": "Therapy Plan",
# 			"width": 140
# 		},
# 		{
# 			"fieldname": "category",
# 			"fieldtype": "Link",
# 			"label": _("Service Unit"),
# 			"options": "Healthcare Service Unit",
# 			"width": 140

# 		},
# 		{
# 			"fieldname": "start_date",
# 			"fieldtype": "Date",
# 			"label": _("Enrolment date"),
# 			"width": 140
# 		},
# 		{
# 			"fieldname": "custom_employee_name",
# 			"fieldtype": "Data",
# 			"label": _("Counsellor/consultant name"),
# 			"width": 140
# 		},
# 		{
# 			"fieldname": "branch",
# 			"fieldtype": "Link",
# 			"label": _("Branch"),
# 			"options": "Branch",
# 			"width": 140
# 		},
# 		{
# 			"fieldname": "grand_total",
# 			"fieldtype": "Currency",
# 			"label": _("Enrolment Amount"),
# 			"width": 140
# 		}
# 	]
# 	return columns
