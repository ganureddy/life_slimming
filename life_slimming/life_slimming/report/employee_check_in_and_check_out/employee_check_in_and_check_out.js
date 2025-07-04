// Copyright (c) 2023, Ganu Reddy and contributors
// For license information, please see license.txt
/* eslint-disable */

// frappe.query_reports["Employee Check-in and check-out"] = {
// 	"filters": [

// 	]
// };

frappe.query_reports["Employee Check-in and check-out"] = {
    "filters": [
        {
            'label': 'Company',
            'fieldname': 'company',
            'fieldtype': 'Link',
            'options': 'Company',
        },
        {
            'label': 'From Date',
            'fieldname': 'from_date',
            'fieldtype': 'Date',
            'default': frappe.datetime.add_months(frappe.datetime.get_today(), -1), // Default to one month ago
        },
        {
            'label': 'To Date',
            'fieldname': 'to_date',
            'fieldtype': 'Date',
            'default': frappe.datetime.get_today(), // Default to today
        },
        {
            'label': 'Employee',
            'fieldname': 'employee',
            'fieldtype': 'Link',
            'options': 'Employee',
        },
        {
            'label': 'Department',
            'fieldname': 'department',
            'fieldtype': 'Link',
            'options': 'Department',
        }
    ]
};
