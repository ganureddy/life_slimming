// Copyright (c) 2025, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Branch Wise Sales Report 18% GST"] = {
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
		{
			"fieldname":"branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
		},
		{
			"fieldname":"type_of",
			"label":__("Type Of"),
			"fieldtype":"Select",
			"default":"Branch Wise",
			"options":['Branch Wise','Service Wise','Customer Wise']
		}
		
	],
	onload:()=>{
		let date = new Date();
		let firstDay = new Date(date.getFullYear(), date.getMonth(), 6);
		let lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 5);
		frappe.query_report.set_filter_value("from_date", firstDay);
		frappe.query_report.set_filter_value("to_date",lastDay)
	}
};
