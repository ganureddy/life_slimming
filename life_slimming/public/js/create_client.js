// create client(patient) using custom button
frappe.ui.form.on('Appointment', {
    refresh: function(frm) {
        if (frm.doc.__unsaved !=1){
            frm.add_custom_button(__('Create Client'), function() {
                frappe.route_options = {
                    'first_name':frm.doc.customer_name,
                    'mobile':frm.doc.customer_phone_number,
                    'sex':frm.doc.sex,
                    'branch_name':frm.doc.branch,
                    'agent_name':frm.doc.full_name
                };
                frappe.set_route('Form', 'Patient','new-patient-1');
            }).addClass('btn-primary');
        }
        
    }
});

// create available Slot
frappe.ui.form.on("Appointment", "refresh", function(frm){
    if (frm.is_new()){
        frm.add_custom_button(__("Appointment Available Slot"), function show_availability (){
           
		let d = new frappe.ui.Dialog({
			title: __('Available slots'),
			fields: [
			    { fieldtype: 'Link', options: 'Branch', reqd: 1, fieldname: 'branch', label: 'Branch'},
			    { fieldtype: 'Column Break' },
			    { fieldtype: 'Link', options: 'Healthcare Service Unit', reqd: 1, fieldname: 'category', label: 'Category'},
			    { fieldtype: 'Column Break' },
			    { fieldtype: 'Link', options: 'Concern', reqd: 1, fieldname: 'concern', label: 'Concern'},
				{ fieldtype: 'Section Break' },
				{ fieldtype: 'Date', reqd: 1, fieldname: 'date', label: 'Date' },
				{ fieldtype: 'Column Break'},
				{ fieldtype: 'Select',options:['15 Minutes','30 Minutes', '45 Minutes', '1 Hour'],reqd: 1, fieldname: 'duration', label: 'Duration'},
				{ fieldtype: 'Column Break' },
				{ fieldtype: 'Time', reqd: 1, fieldname: 'time', label: 'Time' },
		    ],	
		   
			primary_action_label: __('Book'),
			primary_action: function() {
				frm.set_value('branch', d.get_value('branch'));
				frm.set_value('category', d.get_value('category'));
				frm.set_value('concern', d.get_value('concern'));
				frm.set_value('date', d.get_value('date'));
				frm.set_value('duration',d.get_value('duration'));
				frm.set_value('time',d.get_value('time'));
				let schedule = moment(`${d.get_value('date')} ${d.get_value('time')}`, 'YYYY-MM-DD HH:mm').format('YYYY-MM-DD HH:mm');
				frm.set_value('scheduled_time',schedule);
				d.hide();
				frm.enable_save();
				frm.save();
				d.get_primary_btn().attr('disabled', true);
			}
		});
		d.show();
		d.get_primary_btn().attr('disabled', null);
	}
        );
    }
});