// Copyright (c) 2025, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */




frappe.query_reports["Monthly Client Enrolment Details"] = {
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
			fieldname: "client",
			label: __("Client"),
			fieldtype: "Link",
			options: "Patient",
			width: "60px",
		},
		{
			fieldname: "category",
			label: __("CHealthcare Service Unitategory"),
			fieldtype: "Link",
			options: "Healthcare Service Unit"
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch"
		}
	]
};
