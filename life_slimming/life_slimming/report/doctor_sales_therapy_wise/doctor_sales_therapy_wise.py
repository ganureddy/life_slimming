# Copyright (c) 2025, swathi and contributors
# For license information, please see license.txt

# import frappe

import frappe
from frappe import _
from frappe.query_builder.functions import Sum


def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_column(filters)  # fixed typo
	return columns, data

# def get_data(filters):
# 	se = frappe.qb.DocType("Sales Invoice")
# 	se_item = frappe.qb.DocType("Sales Invoice Item")
# 	se_therapy = frappe.qb.DocType("Therapy Plan Detail")

# 	query = (
# 		frappe.qb.from_(se)
# 		.right_join(se_item)
# 		.on(se_item.parent == se.name)
# 		.right_join(se_therapy)
# 		.on(se_therapy.parent == se.name)
# 		.select(
# 			se.name.as_("sales_invoice"),
# 			se.custom_doctor_id,
# 			se.custom_doctor_name,
# 			se.branch,
# 			se_item.item_code,
# 			se_item.amount,
# 			se_therapy.name.as_("therapy_plan"),
# 			se_therapy.therapy_type,
# 			se.posting_date
# 		)
# 		.where(se.docstatus == 1)
# 	)

# 	if filters.get("from_date"):
# 		query = query.where(se.posting_date >= filters.get("from_date"))

# 	if filters.get("to_date"):
# 		query = query.where(se.posting_date <= filters.get("to_date"))

# 	if filters.get("doctor"):
# 		query = query.where(se.custom_doctor_id == filters.get("doctor"))

# 	if filters.get("therapy"):
# 		query = query.where(se_therapy.therapy_type == filters.get("therapy"))
# 	if filters.get("branch"):
# 		query = query.where(se.branch == filters.get("branch"))

# 	raw_data = query.run(as_dict=True)

# 	# Now filter where item_code == therapy_type
# 	final_data = []
# 	for row in raw_data:
# 		if row.item_code == row.therapy_type:
# 			final_data.append({
# 				"sales_invoice": row.sales_invoice,
# 				"custom_doctor_name": row.custom_doctor_name,
# 				"posting_date": row.posting_date,
# 				"therapy_plan": row.therapy_plan,
# 				"branch": row.branch,
# 				"therapy_type": row.therapy_type,
# 				"amount": row.amount
# 			})

# 	return final_data

# def get_data(filters):
#     se = frappe.qb.DocType("Sales Invoice")
#     se_item = frappe.qb.DocType("Sales Invoice Item")
#     se_therapy = frappe.qb.DocType("Therapy Plan Detail")
#     pe_ref = frappe.qb.DocType("Payment Entry Reference")

#     query = (
#         frappe.qb.from_(se)
#         .right_join(se_item).on(se_item.parent == se.name)
#         .right_join(se_therapy).on(se_therapy.parent == se.name)
#         .left_join(pe_ref).on(pe_ref.reference_name == se.name)
#         .select(
#             se.name.as_("sales_invoice"),
#             se.custom_doctor_id,
#             se.custom_doctor_name,
#             se.branch,
#             se_item.item_code,
#             se_item.amount,
#             se_therapy.name.as_("therapy_plan"),
#             se_therapy.therapy_type,
#             se.posting_date,
#             Sum(pe_ref.allocated_amount).as_("total_allocated_amount")
#         )
#         .where(se.docstatus == 1)
#         .groupby(se.name)
#     )

#     if filters.get("from_date"):
#         query = query.where(se.posting_date >= filters.get("from_date"))

#     if filters.get("to_date"):
#         query = query.where(se.posting_date <= filters.get("to_date"))

#     if filters.get("doctor"):
#         query = query.where(se.custom_doctor_id == filters.get("doctor"))

#     if filters.get("therapy"):
#         query = query.where(se_therapy.therapy_type == filters.get("therapy"))

#     if filters.get("branch"):
#         query = query.where(se.branch == filters.get("branch"))

#     raw_data = query.run(as_dict=True)

#     # Post-processing: apply item_code == therapy_type and allocated amount logic
#     final_data = []
#     for row in raw_data:
#         if row.item_code == row.therapy_type:
#             paid_amount = row.total_allocated_amount or 0.0
#             # Clamp the paid_amount to not exceed item.amount
#             if paid_amount > row.amount:
#                 paid_amount = row.amount

#             final_data.append({
#                 "sales_invoice": row.sales_invoice,
#                 "custom_doctor_name": row.custom_doctor_name,
#                 "posting_date": row.posting_date,
#                 "therapy_plan": row.therapy_plan,
#                 "branch": row.branch,
#                 "therapy_type": row.therapy_type,
#                 "amount": row.amount,
#                 "paid_amount": paid_amount
#             })

#     return final_data


def get_data(filters):
    se = frappe.qb.DocType("Sales Invoice")
    se_item = frappe.qb.DocType("Sales Invoice Item")
    se_therapy = frappe.qb.DocType("Therapy Plan Detail")
    pe_ref = frappe.qb.DocType("Payment Entry Reference")

    # Step 1: Aggregate Payment Entry amounts
    pe_sum = (
        frappe.qb.from_(pe_ref)
        .select(
            pe_ref.reference_name.as_("invoice"),
            Sum(pe_ref.allocated_amount).as_("total_paid")
        )
        .groupby(pe_ref.reference_name)
    ).as_("pe_sum")

    # Step 2: Main query with correct join
    query = (
        frappe.qb.from_(se)
        .join(se_item).on(se_item.parent == se.name)
        .join(se_therapy)
            .on(
                (se_therapy.parent == se.name) &
                (se_therapy.therapy_type == se_item.item_code)
            )
        .left_join(pe_sum)
            .on(pe_sum.invoice == se.name)
        .select(
            se.name.as_("sales_invoice"),
            se.custom_doctor_name,
            se.branch,
            se_item.item_code,
            se_item.amount.as_("amount"),
            se_therapy.name.as_("therapy_plan"),
            se_therapy.therapy_type,
            se.posting_date,
            pe_sum.total_paid.as_("paid_amount")
        )
        .where(se.docstatus == 1)
    )

    # filters
    if filters.get("from_date"):
        query = query.where(se.posting_date >= filters.get("from_date"))

    if filters.get("to_date"):
        query = query.where(se.posting_date <= filters.get("to_date"))

    if filters.get("doctor"):
        query = query.where(se.custom_doctor_id == filters.get("doctor"))

    if filters.get("therapy"):
        query = query.where(se_therapy.therapy_type == filters.get("therapy"))

    if filters.get("branch"):
        query = query.where(se.branch == filters.get("branch"))

    result = query.run(as_dict=True)

    # Clamp paid amount
    for row in result:
        if row.paid_amount and row.paid_amount > row.amount:
            row.paid_amount = row.amount

    return result


def get_column(filters):
	columns = [
		{
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"label": _("Sales Invoice"),
			"options": "Sales Invoice",
			"width": 160
		},
		{
			"fieldname": "custom_doctor_name",
			"fieldtype": "Data",
			"label": _("Doctor Name"),
			"width": 160
		},
		{
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"label": _("Sales Invoice Date"),
			"width": 140
		},
		{
			"fieldname": "therapy_plan",
			"fieldtype": "Data",
			"label": _("Therapy Plan"),
			"width": 140
		},
		{
			"fieldname": "branch",
			"fieldtype": "Link",
			"label": _("Branch"),
			"options": "Branch",
			"width": 140
		},
		{
			"fieldname": "therapy_type",
			"fieldtype": "Link",
			"label": _("Therapy Type"),
			"options": "Therapy Type",
			"width": 140
		},
		{
			"fieldname": "amount",
			"fieldtype": "Currency",
			"label": _("Amount"),
			"width": 140
		},
		{
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"label": _("Paid Amount"),
			"width": 140
		}
	]
	return columns
