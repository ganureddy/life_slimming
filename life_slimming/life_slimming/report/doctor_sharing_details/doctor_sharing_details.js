// Copyright (c) 2024, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Doctor Sharing Details"] = {
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
			"options": "Branch",
			"default":"All Branch"
		},
		{
			"fieldname":"group_by",
			"label": __("Group By"),
			"fieldtype": "Check",
			"default":1
		}
	]
};
