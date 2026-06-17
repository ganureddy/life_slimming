frappe.listview_settings["Lead"] = {
    add_fields: ["status"],
    get_indicator: function(doc) {
        if(doc.status == "Lead") {
            return [__("Lead"), "red", "status,=,Lead"];
        }
        if(doc.status == "Open") {
            return [__("Open"), "red", "status,=,Open"];
        }
        else if(doc.status == "Interested") {
            return [__("Interested"), "blue", "status,=,Interested"];
        }
        else if(doc.status == "Call Back") {
            return [__("Call Back"), "cyan", "status,=,Call Back"];
        }
        else if(doc.status == "Get Back") {
            return [__("Get Back"), "blue", "status,=,Get Back"];
        }
        else if(doc.status == "Consultation Done") {
            return [__("Consultation Done"), "green", "status,=,Consultation Done"];
        }
        else if(doc.status == "DND") {
            return [__("DND"), "purple", "status,=,DND"];
        }
        else if(doc.status == "NID") {
            return [__("NID"), "purple", "status,=,NID"];
        }
        else if(doc.status == "Appointment Booked") {
            return [__("Appointment Booked"), "green", "status,=,Appointment Booked"];
        }
        else if(doc.status == "Not Interested") {
            return [__("Not Interested"), "red", "status,=,Not Interested"];
        }
        else if(doc.status == "Existing Client") {
            return [__("Existing Client"), "blue", "status,=,Existing Client"];
        }
        else if(doc.status == "Wrong Call") {
            return [__("Wrong Call"), "purple", "status,=,Wrong Call"];
        }
        else if(doc.status == "Switch Off") {
            return [__("Switch Off"), "red", "status,=,Switch Off"];
        }
        else if(doc.status == "Not Enquired") {
            return [__("Not Enquired"), "gray", "status,=,Not Enquired"];
        }
        else if(doc.status == "Appointment No Response") {
            return [__("Appointment No Response"), "cyan", "status,=,Appointment No Response"];
        }
        else if(doc.status == "TNA") {
            return [__("TNA"), "orange", "status,=,TNA"];
        }
        
        else if(doc.status == "Not Reachable") {
            return [__("Not Reachable"), "black", "status,=,Not Reachable"];
        }
        else if(doc.status == "Not Response") {
            return [__("Not Response"), "purple", "status,=,Not Response"];
        }
        else if(doc.status == "Joined") {
            return [__("Joined"), "green", "status,=,Joined"];
        }
    },
    // refresh: function(listview) {
    //     frappe.call({
    //         method: "life_slimming.events.update_call_back_status",
    //         args: {
    //             // doc: listview.get_checked_items()
    //         },
    //         callback: function(r) {
    //             let isPopupShown = false;
    //                 setInterval(function() {
    //             let today = new moment().format('YYYY-MM-DD');
    //             let time = new moment().format('HH:mm');
    //                     if (r.message.Data.length > 0) {
    //                 let data= r.message.Data;
    //                 let finalData=[];
    //                     if (isPopupShown) {
    //                         return;
    //                     }
    //                 data.forEach((el)=>{
                        
    //                     let elTime=  moment(el.followup_next_date + ' ' + el.time).format('HH:mm');
    //                     console.log(today,time,el.followup_next_date,elTime);
    //                     if(el.followup_next_date == today && elTime == time){
    //                         finalData.push(el);
    //                     }
    //                 });
    //                 // console.log('----------',finalData);
    //                 // let data = r.message.Data;
    //                 if(finalData.length){
    //                         var leadInfo = finalData.map(function(lead) {
    //                     return lead['name'] + ": " + lead['first_name'] + " (" + lead['mobile_no'] + ")";
    //                     }).join("\n");
    //                     frappe.msgprint("Callback leads:\n" + leadInfo);
    //                     isPopupShown = true;
    //                 }
    //             }
    //                 },60000);
    //         }
    //     });
    // }
};