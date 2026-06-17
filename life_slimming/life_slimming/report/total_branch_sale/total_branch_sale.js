// Copyright (c) 2023, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Total Branch Sale"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"width": "80"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		// {
		// 	"fieldname":"branch",
		// 	"label": __("Branch"),
		// 	"fieldtype": "Link",
		// 	"options": "Branch"
		// },
		// {
		// 	"fieldname":"type_of",
		// 	"label":__("Type Of"),
		// 	"fieldtype":"Select",
		// 	"options":["",'Service Wise','Customer Wise','Branch Wise']
		// }
		
	]
};
