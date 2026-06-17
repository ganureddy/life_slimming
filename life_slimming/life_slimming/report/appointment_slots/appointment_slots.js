// Copyright (c) 2023, swathi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Appointment Slots"] = {
	"filters": [
		{
			"label": __("Date"),
			"fieldname":"date",
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today()),
			"reqd": 1
		},
		{
			"label": __("Branch"),
			"fieldname":"branch",
			"fieldtype": "Link",
			"options":"Branch"
			// "reqd": 1
		},
		{
			"label": "Create New Appointment",
			"fieldname": "create_appointment",
			"fieldtype": "Button",
			"width": 200,
		}
	],

	after_datatable_render: table_instance => {

		let data = table_instance.datamanager.data;

		var headerCells = table_instance.wrapper.querySelectorAll(".dt-cell--header");
		
		headerCells.forEach(function(cell) {
			cell.style.backgroundColor = "#87CEEB";
		});

		var headerCells = table_instance.wrapper.querySelectorAll(".dt-cell--header");
		headerCells.forEach(function(cell) {
			cell.style.backgroundColor = "#87CEEB";
		});
		
		table_instance.style.setStyle(`.dt-scrollable`, {height: '600px;'});
	}
}
erpnext.utils.add_dimensions('Appointment Slots', 15)


function myfunction(){
    let get_data =document.querySelectorAll(".dt-cell__content [data-doctype='Patient Appointment'], .dt-cell__content [data-doctype='Appointment']")

	get_data.forEach((el)=>{
		let txt = el.innerText
		// console.log(txt.includes("Scheduled"))

		if(txt.includes("Scheduled")){
		el.style.color='Orange'
		}

		if(txt.includes("Not Answering")){
			el.style.color='Red'
		}

		if(txt.includes("Re-Scheduled")){
			el.style.color='Yellow'
		}

		if(txt.includes("Re-Confirm")){
			el.style.color='Green'
		}

		if(txt.includes("Closed")){
			el.style.color='Blue'
		}

		if(txt.includes("Cancel")){
			el.style.color='Red'
		}

	})


}

setInterval(() => {
	myfunction()
}, 0);

$(document).on("click", "button[data-fieldname='create_appointment']", function() {
    // Your code to be executed when the element is clicked
	setPricelist()
});

function setPricelist(frm){
	frappe.route_options = {

	};
	frappe.set_route('Form', 'Patient Appointment','new-patient-appointment');
}
