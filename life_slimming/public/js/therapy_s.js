frappe.provide('erpnext.queries');
frappe.ui.form.on('Therapy Session', {
    refresh: function(frm) {
        if(frm.doc.docstatus !==1){
            frm.add_custom_button(__('Book Appointment'), function() {
                frappe.route_options = {
                    'patient':frm.doc.patient,
                };
                frappe.set_route('Form', 'Patient Appointment','new-patient-appointment-1');
            }).addClass('btn-primary');
        } 
    },
    setup: function(frm) {
        frm.set_query('appointment', function() {
            return {
                filters: {
                    'call_back_status': ['in', ["Re-Confirm"]]
                }
            };
        }); 
    },
    setup: function(frm) {
        frm.set_query('therapy_plan', function() {
            return {
                filters: {
                    'status': ['not in', ["Completed"]]
                }
            };
        }); 
    }

});