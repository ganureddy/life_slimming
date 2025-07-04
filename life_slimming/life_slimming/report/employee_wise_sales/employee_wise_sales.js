// Copyright (c) 2023, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Employee Wise Sales"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
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
			"options": "Branch"
		},

	],
	onload:()=>{
		let date = new Date();
		let firstDay = new Date(date.getFullYear(), date.getMonth(), 6);
		let lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 5);
		frappe.query_report.set_filter_value("from_date", firstDay);
		frappe.query_report.set_filter_value("to_date",lastDay)
	}
};
