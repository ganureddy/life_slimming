// frappe.ui.form.on('Lead', 'dob', function(frm) {
//     console.log("testTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTs")
// 	if (frm.doc.dob) {
// 		let today = new Date();
// 		let birthDate = new Date(frm.doc.dob);
// 		if (today < birthDate) {
// 			frappe.msgprint(__('Please select a valid Date'));
// 			frappe.model.set_value(frm.doctype,frm.docname, 'dob', '');
// 		} else {
// 			let age_str = get_age(frm.doc.dob);
// 			$(frm.fields_dict['age_html'].wrapper).html(`${__('AGE')} : ${age_str}`);
// 		}
// 	} else {
// 		$(frm.fields_dict['age_html'].wrapper).html('');
// 	}
// });

// let get_age = function (birth) {
// 	let ageMS = Date.parse(Date()) - Date.parse(birth);
// 	let age = new Date();
// 	age.setTime(ageMS);
// 	let years = age.getFullYear() - 1970;
// 	return years + ' Year(s) ' + age.getMonth() + ' Month(s) ' + age.getDate() + ' Day(s)';
// };
// console.log(get_age,"---------------------------")

// frappe.ui.form.on('Lead', {
// 	onload: function (frm) {
// 		if (frm.doc.dob) {
// 			$(frm.fields_dict['age_html'].wrapper).html(`${__('AGE')} : ${get_age(frm.doc.dob)}`);
// 		} else {
// 			$(frm.fields_dict['age_html'].wrapper).html('');
// 		}
// 	}
// });

frappe.ui.form.on('Lead', {
    refresh: function(frm) {
        if(frm.doc.__unsaved !=1){
            frm.add_custom_button(__('Create Appointment'), function() {
                var customer_email = '' ;
                if (frm.doc.email_id){
                    customer_email=frm.doc.email_id;
                } else {
                    customer_email='Not Available';
                }
                frappe.route_options = {
                    'customer_name':frm.doc.lead_name,
                    'customer_email':customer_email,
                    'appointment_with':"Lead",
                    'sex':frm.doc.gender,
                    'party':frm.doc.name,
                    'category':frm.doc.category,
                    'customer_phone_number':frm.doc.mobile_no,
                    'concern':frm.doc.consultant,
                    'branch':frm.doc.lead_assign_to_branch,
                    'lead_owner':frm.doc.lead_owner,
                };
                frappe.set_route('Form', 'Appointment','new-appointment-1');
            }).addClass('btn-primary');
        } 
    }
});


//Consultant filter
frappe.ui.form.on("Lead", {
    setup: function(frm) {
        frm.set_query('consultant', function() {
            return {
                filters: {
                    'category': frm.doc.category
                }
            };
        });
    }
});