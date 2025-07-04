frappe.ui.form.on('Therapy Plan', {
    refresh(frm){
        if(frm.doc.invoiced!=1){
            frm.add_custom_button(__('Create Sales Invoice'),function(){
                get_doc(cur_frm.doc.name).then(
                    function(result){
                        frappe.model.with_doctype('Sales Invoice',function(){
                            var si = frappe.model.get_new_doc('Sales Invoice');
                            var income_account = ''
                            var expense_account = ''
                            var company_details = frappe.db.get_value("Company",{"name":frm.doc.company},
                                                                ["default_expense_account","default_income_account"])

                            company_details.then((res)=>{
                                if(res.message){
                                    income_account = res.message.default_income_account
                                    expense_account = res.message.default_expense_account
                                    si.patient = cur_frm.doc.patient;
                                    si.ref_practitioner = cur_frm.doc.consultant_name;
                                    si.therapy_plan_reference_id = cur_frm.doc.name;
                                    si.service_unit = cur_frm.doc.category
                                    if (cur_frm.doc.custom_incentive_employee_name != ''){
                                        si.custom_incentive_employee_name = cur_frm.doc.custom_incentive_employee_name;
                                    } 
                                    si.custom_tele_caller = cur_frm.doc.tele_caller;
                                    let count = 0
                                    result.forEach(function(therapy_type){
                                        if(therapy_type.custom_is_offer_ !== 1){
                                            var si_item = frappe.model.add_child(si,'items');
                                            si_item.item_code = therapy_type.item_code;
                                            if (therapy_type.stock_uom === 'Combo'){
                                                si_item.qty = therapy_type.no_of_sessions/therapy_type.no_of_sessions;
                                                si_item.item_name = therapy_type.therapy_type;
                                                si_item.description = therapy_type.description;
                                                si_item.uom = therapy_type.stock_uom;
                                                si_item.stock_uom = therapy_type.stock_uom;
                                                if (count == 0){
                                                    si_item.reference_dn = therapy_type.parent;
                                                    si_item.reference_dt = therapy_type.parenttype;
                                                    count = 1
                                                }
                                                si_item.income_account = income_account;
                                                si_item.expense_account = expense_account;
                                            }else{
                                                si_item.qty = therapy_type.no_of_sessions
                                                si_item.item_name = therapy_type.therapy_type;
                                                si_item.description = therapy_type.description;
                                                si_item.uom = therapy_type.stock_uom;
                                                si_item.stock_uom = therapy_type.stock_uom;
                                                if (count == 0){
                                                    si_item.reference_dn = therapy_type.parent;
                                                    si_item.reference_dt = therapy_type.parenttype;
                                                    count = 1
                                                }
                                                si_item.income_account = income_account;
                                                si_item.expense_account = expense_account;
                                            }
                                        }
                                        
                                    });
                                    frappe.set_route('Form','Sales Invoice',si.name);
                                }
                        })
                    });                       
                });               
            }).addClass('btn-primary');
        }     
    }       
    });
    
    var get_doc = function(mydocname){
        var stk ;
        return new Promise(function(resolve){
            frappe.call({
                'method':'life_slimming.events.create_si_item_from_therapy_type',
                "args":{
                     "name":mydocname
                },
                "callback": function(response){
                    stk = response.message;
                    resolve(stk);
                }
            });
        });
    }
    

frappe.ui.form.on('Therapy Plan Detail', {
    
    therapy_type: function (frm,cdt,cdn) {
        if (cur_frm.doc.therapy_plan_details && cur_frm.doc.therapy_plan_details.length > 0) {
            for (var i = 0; i < cur_frm.doc.therapy_plan_details.length; i++) {
                var d = cur_frm.doc.therapy_plan_details[i];
                var item = d.therapy_type;
                
                frappe.db.get_value("Therapy Type",{"item_code":item}, ["item_code","quantity"], (r) => {
                    frappe.model.set_value(cdt,cdn, "no_of_sessions",r.quantity);
                });
            }
        }
    }
});