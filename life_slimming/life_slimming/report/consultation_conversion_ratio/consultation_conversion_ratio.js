// Copyright (c) 2024, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Consultation Conversion Ratio"] = {
	"filters": [
		{
			"fieldname":"branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"default": "All Branch",
			"options": "Branch",
			"reqs":1,
			// "read_only":1
			
		},
		{
			"fieldname":"month",
			"label":__("Month"),
			"fieldtype":"Select",
			"options": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
			"reqs":1
			// "read_only":0

		},
		{
			"fieldname":"fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			// "read_only":1
		},
		{
			"fieldname":"employee_conversion_check",
			"label": __("Employee Conversion Details"),
			"fieldtype": "Check",
			"default":0,
			// "read_only":1
		}
	],
	onload:()=>{

		const Months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
		const d = new Date();
		let name = Months[d.getMonth()];
		frappe.query_report.set_filter_value("month", name);

	}
};
