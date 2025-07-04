frappe.ui.form.on("Clinical Procedure",{
	general_procedure: function(frm) {
		if(frm.doc.general_procedure==1) {
			frm.set_value('pre_procedure',0);
			frm.set_value('post_procedure',0);
			frm.set_query('procedure_template', function(){
				return {
					filters: {
						"procedure_status": "General Procedure"
					}
				}
			})
		}
	},
	
	pre_procedure: function(frm) {
		if(frm.doc.pre_procedure==1) {
			frm.set_value('general_procedure',0);
			frm.set_value('post_procedure',0);
			frm.set_query('procedure_template', function(){
				return {
					filters: {
						"procedure_status": "Pre-Procedure"
					}
				}
			})
		}
	},

	post_procedure: function(frm) {
		if(frm.doc.post_procedure==1) {
			frm.set_value('pre_procedure',0);
			frm.set_value('general_procedure',0);
			frm.set_query('procedure_template', function(){
				return {
					filters: {
						"procedure_status": "Post-Procedure"
					}
				}
			})
		}
	}
})