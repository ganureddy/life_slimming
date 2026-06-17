// Copyright (c) 2023, swathi and contributors
// For license information, please see license.txt

// frappe.ui.form.on('Opening Checklist', {
// 	// refresh: function(frm) {

// 	// }
// });


frappe.ui.form.on('Opening Checklist', {
    onload: function (frm) {
        var currentDate = frappe.datetime.get_today();
        frm.set_value('date',currentDate);
    }
});

function myFunction() { 
    // console.log('--------', document.getElementsByTagName("label"))
    var element2 = document.getElementsByClassName("col-sm-6");
    element2[1].setAttribute("class", "form-column col-sm-10");
    
    setTimeout(() => {             
        var element3 = document.getElementsByClassName("col-sm-6");
        element3[1].setAttribute("class", "col-sm-2");
        let check = document.getElementsByClassName ("checkbox")
        for(let i=0;i<=check.length;i++){
            check[i].style.marginTop="16px"
            check[i].style.marginLeft="20px"
        }
		
    }, 10)
}
myFunction()