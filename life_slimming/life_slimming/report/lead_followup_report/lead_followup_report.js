// Copyright (c) 2023, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Lead Followup Report"]={
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
			"label": __("From Date"),
			"fieldname":"from_date",
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"label": __("To Date"),
			"fieldname":"to_date",
			"fieldtype": "Date",
			"default":frappe.datetime.get_today(),
			onload: function(frm) {
				frm.set_value('to_date', frappe.datetime.get_today());
				frappe.query_reports.refresh();
			},
			"reqd": 1
		},
		{
			"label":__("Followup By User"),
			"fieldname":"followup_by_person",
			"fieldtype":"Link",
			// "default": frappe.session.user,
			"options":"User"
		},
		{
			"label": __("Branch"),
			"fieldname":"lead_assign_to_branch",
			"fieldtype": "Link",
			"default":"",
			"options": "Branch",
		},	
		// {
		// 	"label": __("Lead"),
		// 	"fieldname": "name",
		// 	"fieldtype": "Link",
		// 	"options": "Lead",
		// },
		{
			"fieldname":"gender",
			"label": __("Gender"),
			"fieldtype": "Link",
			"default": "",
			"options": "Gender",
		},
		{
			"label":__("Followup By Next Date"),
			"fieldname":"followup_next_date",
			"fieldtype":"Date",
		},
			
	
	],            
};
