
frappe.ui.form.on('Patient', {
    validate: function(frm) {

        if (!frm.doc.custom_otp_verified) {

            frappe.validated = false;

            frappe.call({
                method: "life_slimming.user_wise_roles.send_client_whatsapp_otp",
                args: {
                    mobile: frm.doc.mobile
                },
                callback: function(r) {

                    if (r.message) {
                        show_otp_dialog(frm);
                    }

                }
            });

        }

    }
});
function show_otp_dialog(frm){

    let d = new frappe.ui.Dialog({
        title: "Enter Verification Code",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "otp_html"
            }
        ],
        primary_action_label: "Verify",
        primary_action(){

            let otp = "";

            $(".otp-input").each(function(){
                otp += $(this).val();
            });

            if(otp.length != 6){
                frappe.msgprint("Please enter 6 digit OTP");
                return;
            }

            frappe.call({
                method: "life_slimming.user_wise_roles.verify_client_otp",
                args:{
                    otp: otp,
                    mobile: frm.doc.mobile
                },
                callback:function(r){

                    if(r.message == "verified"){

                        frm.set_value("custom_otp_verified",1);
                        d.hide();
                        frm.save();

                    }else{

                        frappe.msgprint("Invalid OTP");

                    }

                }
            });

        }
    });

    d.show();

    // OTP UI
    let html = `
        <div style="text-align:center">

            <p style="margin-bottom:20px;font-size:14px">
                Enter the 6 digit code sent to your WhatsApp
            </p>

            <div class="otp-container">
                <input class="otp-input" maxlength="1">
                <input class="otp-input" maxlength="1">
                <input class="otp-input" maxlength="1">
                <input class="otp-input" maxlength="1">
                <input class="otp-input" maxlength="1">
                <input class="otp-input" maxlength="1">
            </div>

            <div style="margin-top:15px">
                <a id="resend_otp" style="cursor:pointer">Resend</a>
            </div>

        </div>

        <style>

        .otp-container{
            display:flex;
            justify-content:center;
            gap:10px;
        }

        .otp-input{
            width:45px;
            height:50px;
            text-align:center;
            font-size:20px;
            border:2px solid #1f7a7a;
            border-radius:10px;
        }

        .otp-input:focus{
            outline:none;
            border-color:#00a8a8;
            box-shadow:0 0 4px rgba(0,168,168,0.4);
        }

        </style>
    `;

    d.fields_dict.otp_html.$wrapper.html(html);


    // auto focus move
    $(document).on("keyup",".otp-input",function(){

        if(this.value.length == 1){
            $(this).next(".otp-input").focus();
        }

    });


    // resend otp
    $("#resend_otp").click(function(){

        frappe.call({
            method:"life_slimming.user_wise_roles.send_client_whatsapp_otp",
            args:{
                mobile: frm.doc.mobile
            }
        });

        frappe.show_alert("OTP Sent Again");

    });

}