frappe.listview_settings['Appointment']={
    add_fields: ["status"],
    get_indicator: function(doc) {
        if(doc.status == 'Open'){
            return [__("Open"), "red", "status,=,Open"];
        }
        if(doc.status == 'Join'){
            return [__("Join"), "green", "status,=,Join"];
        }
        if(doc.status == 'Unjoined'){
            return [__("Unjoined"), "red", "status,=,Unjoined"];
        }
    }

}