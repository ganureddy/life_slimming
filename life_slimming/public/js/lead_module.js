
// Keep the standard Lead status, CC sub-status and CC stage aligned in the
// Lead form. The sub-status is the detailed call outcome; it determines the
// standard status and pipeline stage when CC selects an outcome.
const LEAD_SUBSTATUS_MAP = {
    "Appointment Booked": ["Appointment Booked", "SUCCESS"],
    "Walked In & Booked": ["Appointment Booked", "SUCCESS"],
    "Existing Client": ["Existing client", "SUCCESS"],
    "Callback: Scheduled": ["Call Back", "FOLLOW-UP"],
    "Call & Confirm": ["Followup", "FOLLOW-UP"],
    "Price Negotiation": ["Interested", "FOLLOW-UP"],
    "Out Station": ["Get Back", "FOLLOW-UP"],
    "Very Positive": ["Interested", "FOLLOW-UP"],
    "Walked In: Not Booked": ["Not interested", "FOLLOW-UP"],
    "Get Back": ["Get Back", "FOLLOW-UP"],
    "No Response": ["Not Response", "FOLLOW-UP"],
    "Not Reachable": ["Not Reachable", "FOLLOW-UP"],
    "Switch OFF": ["Switch OFF", "FOLLOW-UP"],
    "Call Disconnected": ["Call Disconnected", "FOLLOW-UP"],
    "Appointment no response": ["Appointment no response", "FOLLOW-UP"],
    "Not Interested": ["Not interested", "LOST"],
    "Other clinic": ["Other clinic ", "LOST"],
    "Joined Competition": ["Other clinic ", "LOST"],
    "Do Not Contact": ["Do Not Contact", "LOST"],
    "Invalid Number": ["Wrong number", "INVALID"],
    "Wrong number": ["Wrong number", "INVALID"],
    "Not in Service": ["Not in Service", "INVALID"],
    "Junk/Wrong Call": ["NID", "INVALID"],
    "Not Enquired": ["Not Enquired", "INVALID"],
    "TNA": ["TNA", "INVALID"],
    "NID": ["NID", "INVALID"],
    "Franchise Lead": ["Franchise Lead", "INVALID"],
    "Job enquiry": ["Job enquiry ", "INVALID"],
    "Lead": ["Lead", "UNTOUCHED"]
};
const LEAD_STATUS_SUBSTATUS = {
    "Appointment Booked": "Appointment Booked",
    "Not Enquired": "Not Enquired",
    "Lead": "Lead",
    "Not interested": "Not Interested",
    "Do Not Contact": "Do Not Contact",
    "Not Response": "No Response",
    "Wrong number": "Wrong number",
    "Not Reachable": "Not Reachable",
    "Not in Service": "Not in Service",
    "Switch OFF": "Switch OFF",
    "Call Disconnected": "Call Disconnected",
    "TNA": "TNA",
    "NID": "NID",
    "Franchise Lead": "Franchise Lead",
    "Get Back": "Get Back",
    "Call Back": "Callback: Scheduled",
    "Followup": "Call & Confirm",
    "Converted": "Walked In & Booked"
};
frappe.ui.form.on('Lead', {
    setup(frm) {
        frm.__lifeStatusSync = false;
    },
    refresh(frm) {
        if (frm.is_new() && !frm.doc.custom_cc_sub_status && frm.doc.status) {
            const sub = LEAD_STATUS_SUBSTATUS[frm.doc.status];
            if (sub) frm.set_value('custom_cc_sub_status', sub);
        }
        if (frm.is_new() && !frm.doc.custom_cc_stage) {
            frm.set_value('custom_cc_stage', 'UNTOUCHED');
        }
    },
    before_save(frm) {
        if (!frm.is_new()) return;
        if (!frm.doc.status) frm.set_value('status', 'Lead');
        if (!frm.doc.custom_cc_sub_status) frm.set_value('custom_cc_sub_status', 'Lead');
        if (!frm.doc.custom_cc_stage) frm.set_value('custom_cc_stage', 'UNTOUCHED');
    },
    status(frm) {
        if (frm.__lifeStatusSync) return;
        const sub = LEAD_STATUS_SUBSTATUS[frm.doc.status];
        if (!sub) return;
        frm.__lifeStatusSync = true;
        frm.set_value('custom_cc_sub_status', sub).finally(() => { frm.__lifeStatusSync = false; });
    },
    custom_cc_sub_status(frm) {
        if (frm.__lifeStatusSync) return;
        const mapped = LEAD_SUBSTATUS_MAP[frm.doc.custom_cc_sub_status];
        if (!mapped) return;
        frm.__lifeStatusSync = true;
        Promise.all([
            frm.set_value('status', mapped[0]),
            frm.set_value('custom_cc_stage', mapped[1])
        ]).finally(() => { frm.__lifeStatusSync = false; });
    }
});

// frappe.ui.form.on('Lead', 'dob', function(frm) {
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