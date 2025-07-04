frappe.listview_settings['Patient Appointment'] = {
	add_fields:["call_back_status"],
	get_indicator: function(doc) {
		var colors = {
            "Scheduled":'orange',
            "Not Answering":"red",
            "Re-Confirm":"green",
            "Re-Scheduled":"yellow",
			"Closed":"blue",
			"Cancel":"red"
		};
		return [__(doc.call_back_status), colors[doc.call_back_status], "call_back_status,=," + doc.call_back_status];
	}
};