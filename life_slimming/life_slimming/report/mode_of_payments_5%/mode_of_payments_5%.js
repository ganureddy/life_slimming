frappe.query_reports["Mode of Payments 5%"] = {
	"filters": [
		{

			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.nowdate(), -30), // You can set a default date if needed
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.nowdate(),
		},
		{
			"label": "Mode Of Payment",
			"fieldname": 'mode_of_payment',
			"fieldtype": "Link",
			"options": "Mode of Payment"
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch", // Replace with the actual doctype name for Branch
		}
	],
	onload:()=>{
		let date = new Date();
		let firstDay = new Date(date.getFullYear(), date.getMonth(), 6);
		let lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 5);
		frappe.query_report.set_filter_value("from_date", firstDay);
		frappe.query_report.set_filter_value("to_date",lastDay)
	}
};
