// Copyright (c) 2023, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Customer Flow"] = {
	"filters": [
		{
			"fieldname": "customer_name",
			"label": __("Customer Name"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "lead_name",
			"label": __("Lead"),
			"fieldtype": "Link",
			"options": "Lead",
		},


	]
};
