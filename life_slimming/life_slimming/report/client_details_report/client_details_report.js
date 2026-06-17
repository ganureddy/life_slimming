// Copyright (c) 2023, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Client Details Report"] = {
	"filters": [
		// {
		// 	"fieldname":"company",
		// 	"label":"Company",
		// 	"fieldtype":"Link",
		// 	"options":"Company",
		// 	"default": frappe.defaults.get_user_default("Company"),
        //     "reqd": 1
		// },
		// {
		// 	"fieldname":"from_date",
		// 	"label": __("From Date"),
		// 	"fieldtype": "Date",
		// 	"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		// 	// on_change: function(frm) {
		// 	// 	frm.set_value('from_date', frappe.datetime.add_months(frappe.datetime.get_today(), -1));
		// 	// 	frappe.query_reports.refresh();
		// 	// },
		// 	"reqd": 1
		// },
		// {
		// 	"fieldname":"to_date",
		// 	"label": __("To Date"),
		// 	"fieldtype": "Date",
		// 	"default":frappe.datetime.get_today(),
		// 	// on_change: function(frm) {
		// 	// 	frm.set_value('to_date', frappe.datetime.get_today());
		// 	// 	frappe.query_reports.refresh();
		// 	// },
		// 	"reqd": 1
		// },
		// {
        //     "fieldname":"status",
        //     "label": __("Status"),
        //     "fieldtype": "Select",
        //     "default":"Active",
        //     // "options": [
        //     //     { "value": "Active", "label": __("Active") },
        //     //     { "value": "Disabled", "label": __("Disabled") },
        //     // ],
        //     "options":[" ","Active","Disabled"]
        // },
		{
			"label": __("Client Name"),
            "fieldname":"patient_name",
            "fieldtype": "Link",
            "options":"Patient"
        },
		{
            "fieldname":"uid",
            "label": __("Client Id"),
            "fieldtype": "Data"  
        },
        {
            "fieldname":"branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options":"Branch"
        },
		// {
		// 	"fieldname":"sex",
		// 	"label":"Gender",
		// 	"fieldtype":"Link",
		// 	"options":"Gender"
		// }

	]
};


																																														