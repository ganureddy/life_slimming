// Copyright (c) 2023, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Lead Reports"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		// {
		// 	fieldname: 'based_on',
		// 	label: __('Based On'),
		// 	fieldtype: 'Select',
		// 	options: ['Date', 'Weekly','Monthly'],
		// 	default: 'Date',
		// 	reqd: 1,
		// },

		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default":frappe.datetime.get_today(),
			on_change: function(frm) {
				frm.set_value('to_date', frappe.datetime.get_today());
				frappe.query_reports.refresh();
			},
			"reqd": 1
		},
		{
			"fieldname":"status",
			"label": __("Status"),
			"fieldtype": "Select",
			"default":" ",
			"options": ['','Lead', 'Open','Call Back',
						'Get Back','Consultation Done',
						'DND','NID','Interested',
						'Appointment Booked',
						'Not Interested','Not Response',
						'Existing Client','Wrong Call',
						'Switch Off','Not Enquired',
						'Appointment No Response',
						'TNA','Out of Service',
						'Not Reachable','Joined'],
			
		},
		{
			"fieldname":"lead_assign_to_branch",
			"label": __("Lead Assign To Branch"),
			"fieldtype": "Link",
			"default":"",
			"options": "Branch",
		},
		
		{
			"fieldname":"lead_owner",
			"label": __("Lead Owner"),
			"fieldtype":"Link",
			"default":"",
			"options": "User",
		},
		// {
		// 	"label":__("Followup By User"),
		// 	"fieldname":"followup_by_person",
		// 	"fieldtype":"Link",
		// 	// "default": frappe.session.user,
		// 	"options":"User"
		// },		
		{
			"fieldname":"category",
			"label": __("Category"),
			"fieldtype": "Link",
			"default":"",
			"options": "Healthcare Service Unit",
			
		},
		{
			"fieldname":"gender",
			"label": __("Gender"),
			"fieldtype": "Link",
			"default": "",
			"options": "Gender",
		},
		// {
		// 	"fieldname":"followup_next_date",
		// 	"label": __("Followup Next Date"),
		// 	"fieldtype": "Date",
		// 	"default": "",
		// 	on_change: function(frm) {
		// 		frm.set_value('followup_next_date', " ");
		// 		frappe.query_reports.refresh();
		// 	  }	

		// },
		{
			"fieldname":"source",
			"label": __("Source"),
			"fieldtype": "Link",
			"default": "",
			"options": "Lead Source",
		},

	]
};
