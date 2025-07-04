frappe.provide('erpnext.queries');
frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        if(frm.doc.__unsaved!=1){
            frm.add_custom_button(__('Book Appointment'), function() {
                frappe.route_options = {
                    'patient':frm.doc.patient,
                };
                frappe.set_route('Form', 'Patient Appointment','new-patient-appointment-1');
            }).addClass('btn-primary');
        } 
    }
});