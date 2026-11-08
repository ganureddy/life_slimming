# Paste this entire file into the LIVE ERP System Console, Type = Python.
# Requires the mobile_otp_bypass Python module to be deployed on that server.
# Backs up billing-v2 privately and patches only its existing OTP flow.

page = frappe.get_doc("Web Page", "billing-v2")
marker = "LIFE_BILLING_V2_OTP_BYPASS_20261108"
endpoint = "life_slimming.mobile_otp_bypass.verify_billing_bypass"

if marker in (page.main_section_html or ""):
    print("Billing v2 already has the bypass code field. No changes made.")
else:
    # Stop before writing if the backend has not been deployed on the live server.
    # An empty mobile must fail validation before any code is read or redeemed.
    # A missing module/method raises a different error and stops this patch.
    validated_endpoint = False
    try:
        frappe.call(endpoint, mobile="", code="")
    except frappe.ValidationError:
        validated_endpoint = True
    if not validated_endpoint:
        frappe.throw("Unexpected billing bypass validation response.")
    script_name = frappe.db.get_value("Server Script", {
        "api_method": "life_mobile_bypass_v5", "disabled": 0
    }, "name")
    if not script_name:
        frappe.throw("Deploy/enable life_mobile_bypass_v5 before updating Billing v2.")

    replacements = [
        (
            "  var OTP_VERIFY_METHOD = 'life_slimming.user_wise_roles.verify_client_otp';",
            "  // " + marker + "\n"
            "  var BILLING_BYPASS_METHOD = '" + endpoint + "';\n"
            "  var OTP_VERIFY_METHOD = 'life_slimming.user_wise_roles.verify_client_otp';"
        ),
        (
            "          '<div class=\"life-otp-error\" id=\"life-otp-error\"></div>' +",
            "          '<div style=\"margin-top:18px;padding-top:14px;border-top:1px solid #d2eadc\">' +\n"
            "            '<label for=\"life-billing-bypass-code\">Billing bypass code</label>' +\n"
            "            '<p style=\"font-size:12px;color:#5f8272\">If the client cannot receive the OTP, enter the single-use billing code from Access Control.</p>' +\n"
            "            '<input id=\"life-billing-bypass-code\" type=\"text\" inputmode=\"numeric\" maxlength=\"6\" autocomplete=\"off\" placeholder=\"Six-digit billing code\" style=\"width:100%;padding:10px;border:1px solid #bbdccb;border-radius:8px\">' +\n"
            "            '<button type=\"button\" class=\"btn btn-green\" id=\"life-billing-bypass-verify\" style=\"margin-top:10px\">Verify bypass code</button>' +\n"
            "          '</div>' +\n"
            "          '<div class=\"life-otp-error\" id=\"life-otp-error\" role=\"alert\"></div>' +"
        ),
        (
            "    document.getElementById('life-otp-resend').onclick = resendOtp;",
            "    document.getElementById('life-otp-resend').onclick = resendOtp;\n"
            "    document.getElementById('life-billing-bypass-verify').onclick = verifyBillingBypass;"
        ),
        (
            "  function resendOtp() {",
            "  function verifyBillingBypass() {\n"
            "    if (otpState.busy) return;\n"
            "    var input = document.getElementById('life-billing-bypass-code');\n"
            "    var code = String(input.value || '').trim();\n"
            "    if (!/^[0-9]{6}$/.test(code)) { otpError('Enter the six-digit billing bypass code.'); return; }\n"
            "    var mobile = otpState.mobile;\n"
            "    if (cleanMobile(value('rg-mobile')) !== mobile) { otpError('Mobile changed. Cancel and verify the new number.'); return; }\n"
            "    otpState.busy = true;\n"
            "    var button = document.getElementById('life-billing-bypass-verify');\n"
            "    button.disabled = true; input.disabled = true;\n"
            "    button.textContent = 'Verifying…';\n"
            "    api(BILLING_BYPASS_METHOD, { mobile: mobile, code: code }).then(function (result) {\n"
            "      if (!result || result.verified !== true || result.mobile !== mobile) throw new Error('Invalid or expired billing code.');\n"
            "      if (!otpState.resolve || otpState.mobile !== mobile || cleanMobile(value('rg-mobile')) !== mobile) throw new Error('Registration changed. Verify the current mobile again.');\n"
            "      otpState.verified = true; input.value = '';\n"
            "      closeOtp(true);\n"
            "    }).catch(function (error) {\n"
            "      otpError(error && error.message ? error.message : 'Billing code verification failed.');\n"
            "    }).finally(function () {\n"
            "      otpState.busy = false; button.disabled = false; input.disabled = false;\n"
            "      button.textContent = 'Verify bypass code';\n"
            "    });\n"
            "  }\n\n"
            "  function resendOtp() {"
        ),
        (
            "      return sendOtp(data.mobile).then(function () {\n"
            "        stopSend();\n"
            "        return requestOtpVerification(data.mobile);\n"
            "      }).catch(function (error) {\n"
            "        stopSend();\n"
            "        throw error;\n"
            "      });",
            "      return sendOtp(data.mobile).then(function () { return ''; }, function () {\n"
            "        return 'WhatsApp OTP could not be sent. Retry sending or enter a billing bypass code.';\n"
            "      }).then(function (sendError) {\n"
            "        stopSend();\n"
            "        var verification = requestOtpVerification(data.mobile);\n"
            "        if (sendError) otpError(sendError);\n"
            "        return verification;\n"
            "      });"
        )
    ]

    updated = page.main_section_html or ""
    for old, new in replacements:
        if updated.count(old) != 1:
            frappe.throw("Billing v2 OTP source changed. No update applied; refresh the patch against the current page.")
        updated = updated.replace(old, new, 1)

    # Preserve an exact private backup before saving the page.
    backup = frappe.get_doc({
        "doctype": "File",
        "file_name": "billing-v2-before-otp-bypass-" + frappe.utils.now().replace(":", "-").replace(" ", "-") + ".json",
        "is_private": 1,
        "attached_to_doctype": "Web Page",
        "attached_to_name": page.name,
        "content": json.dumps(page.as_dict(), default=str, indent=2)
    })
    backup.insert()
    page.main_section_html = updated
    page.save()
    saved = frappe.get_doc("Web Page", "billing-v2")
    if saved.main_section_html != updated:
        frappe.throw("Billing v2 save verification failed.")
    frappe.db.commit()
    print("Updated billing-v2 LIVE. Private backup: " + backup.file_url)
    print("Clear Website Cache and hard-refresh Billing v2. Register client → Verify mobile → Billing bypass code.")
