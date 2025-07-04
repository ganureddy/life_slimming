// Copyright (c) 2023, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

// frappe.query_reports["Opening Checklist Report"] = {
// 	"filters": [

// 	]
// };



frappe.query_reports["Opening Checklist Report"] = {
	"filters": [
		{
			"label": __("Company"),
			"fieldname":"company",
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"label":__("From Date"),
			"fieldname":"from_date",
			"fieldtype":"Date",
			"default":frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype" : "Date",
			"default" : frappe.datetime.get_today(),
			onload: function(frm) {
				frm.set_value('to_date', frappe.datetime.get_today());
				frappe.query_reports.refresh();
			},
			"reqd":1
		},
		{
			"label": __("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": "Branch"
		},
	]
};
