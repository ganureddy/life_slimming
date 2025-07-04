// frappe.provide("frappe,dashboards.chart_sources");
// frappe.dashboards.chart_sources["Concern wise Lead"] = {
//     method: "life_slimming.life_slimming.dashboard_chart_source.concern_wise_lead.concern_wise_lead.get_data",
//     filters: [
//         {
//             filedname: "company",
//             label: __("Company"),
//             filedtype: "Link",
//             options: "Company",
//             default: frappe.defaults.get_user_default("Company")
//         },
//         {
//             filedname: "from_date",
//             label: __("From Date"),
//             filedtype: "Date",
//             default: frappe.defaults.get_user_default("year_start_date"),
//             reqd:1,
//         },
//         {
//             fieldname: "to_date",
//             label: __("To Date"),
//             fieldtype: "Date",
//             default: frappe.defaults.get_user_default("year_end_date"),
//         },
//     ]
// };







frappe.provide("frappe.dashboards.chart_sources");
frappe.dashboards.chart_sources["Concern wise Lead"] = {
    method: "life_slimming.life_slimming.dashboard_chart_source.concern_wise_lead.concern_wise_lead.get_data",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_start_date"),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default:  frappe.defaults.get_user_default("year_end_date"),
		},
		
	]
};