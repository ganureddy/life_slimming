// Copyright (c) 2025, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Doctor Sales Therapy wise"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
			width: "60px",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			width: "60px",
		},
		{
			fieldname: "doctor",
			label: __("Doctor"),
			fieldtype: "Link",
			options: "Healthcare Practitioner",
			width: "60px",
		},
		{
			fieldname: "therapy",
			label: __("Therapy"),
			fieldtype: "Link",
			options: "Therapy"
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch"
		}
	]
};
