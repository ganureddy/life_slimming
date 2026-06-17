frappe.provide('erpnext.queries');

frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        if (frm.doc.__unsaved != 1) {
            frm.add_custom_button(__('Book Appointment'), function() {
                frappe.route_options = {
                    'patient': frm.doc.patient,
                };
                frappe.set_route('Form', 'Patient Appointment', 'new-patient-appointment-1');
            }).addClass('btn-primary');
        }

        if (frm.doc.docstatus === 1 && frm.doc.outstanding_amount > 0) {
            frm.add_custom_button(__('Pay Now'), function() {
                show_razorpay_payment_dialog(frm);
            }).addClass('btn-primary');
        }
    }
});

function show_razorpay_payment_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Collect Payment'),
        fields: [
            {
                fieldname: 'contact_mobile',
                label: __('Contact Mobile'),
                fieldtype: 'Data',
                default: frm.doc.contact_mobile || ''
            },
            {
                fieldname: 'amount',
                label: __('Amount'),
                fieldtype: 'Currency',
                reqd: 1,
                default: frm.doc.outstanding_amount || frm.doc.grand_total
            },
            {
                fieldname: 'qr_area',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: __('Pay'),
        primary_action: function() {
            start_qr_payment(frm, dialog);
        }
    });

    dialog.add_custom_action(__('Send Payment Link'), function() {
        send_payment_link(frm, dialog);
    });

    dialog.show();
}

function load_razorpay_checkout() {
    return new Promise(function(resolve, reject) {
        if (window.Razorpay) {
            resolve();
            return;
        }
        const script = document.createElement('script');
        script.src = 'https://checkout.razorpay.com/v1/checkout.js';
        script.onload = function() { resolve(); };
        script.onerror = function() { reject(); };
        document.body.appendChild(script);
    });
}

function start_qr_payment(frm, dialog) {
    const values = dialog.get_values();
    if (!values) return;

    const wrapper = dialog.fields_dict.qr_area.$wrapper;
    wrapper.html(`<div class="text-muted" style="padding:10px;">${__('Opening Razorpay...')}</div>`);

    frappe.call({
        method: 'life_slimming.razorpay_payment.create_order',
        args: {
            sales_invoice: frm.doc.name,
            amount: values.amount
        },
        freeze: true,
        freeze_message: __('Creating Razorpay order...'),
        callback: function(r) {
            if (!r.message || !r.message.order_id) {
                show_payment_result(wrapper, 'danger', __('Could not create Razorpay order.'));
                return;
            }
            const data = r.message;

            load_razorpay_checkout().then(function() {
                open_razorpay_checkout(frm, dialog, wrapper, data);
            }).catch(function() {
                show_payment_result(wrapper, 'danger', __('Could not load Razorpay. Check your internet connection.'));
            });
        }
    });
}

function open_razorpay_checkout(frm, dialog, wrapper, data) {
    wrapper.html(`<div class="text-warning" style="padding:10px;">${__('Complete the payment in the Razorpay window. Scan the UPI QR to pay.')}</div>`);

    const options = {
        key: data.key_id,
        order_id: data.order_id,
        amount: data.amount,
        currency: data.currency || 'INR',
        name: 'Life Slimming & Cosmetic',
        description: __('Payment for {0}', [frm.doc.name]),
        prefill: {
            name: data.customer_name || '',
            contact: data.contact_mobile || '',
            email: data.contact_email || ''
        },
        notes: { sales_invoice: frm.doc.name },
        // Default the Razorpay window to UPI so the customer sees the scannable QR
        config: {
            display: {
                blocks: {
                    upi: {
                        name: __('Pay using UPI (Scan QR)'),
                        instruments: [{ method: 'upi' }]
                    }
                },
                sequence: ['block.upi'],
                preferences: { show_default_blocks: true }
            }
        },
        handler: function(response) {
            wrapper.html(`<div class="text-muted" style="padding:10px;">${__('Payment received, recording...')}</div>`);
            frappe.call({
                method: 'life_slimming.razorpay_payment.verify_and_record_payment',
                args: {
                    sales_invoice: frm.doc.name,
                    razorpay_payment_id: response.razorpay_payment_id,
                    razorpay_order_id: response.razorpay_order_id,
                    razorpay_signature: response.razorpay_signature
                },
                freeze: true,
                freeze_message: __('Recording payment...'),
                callback: function(res) {
                    if (res.message && res.message.status === 'paid') {
                        show_payment_result(wrapper, 'success',
                            `${__('Payment Successful!')}<br>${__('Transaction')}: <b>${response.razorpay_payment_id}</b><br>${__('Draft Payment Entry')}: <b>${res.message.payment_entry || ''}</b>`);
                        frm.reload_doc();
                    } else {
                        show_payment_result(wrapper, 'danger', __('Payment captured but could not be recorded. Check error logs.'));
                    }
                }
            });
        },
        modal: {
            ondismiss: function() {
                show_payment_result(wrapper, 'danger', __('Payment window closed before completing payment.'));
            }
        }
    };

    const rzp = new window.Razorpay(options);
    rzp.on('payment.failed', function(response) {
        show_payment_result(wrapper, 'danger',
            `${__('Payment Failed')}: ${(response.error && response.error.description) || ''}`);
    });
    rzp.open();
}

function show_payment_result(wrapper, type, message) {
    const colors = {
        success: '#28a745',
        danger: '#dc3545'
    };
    const icon = type === 'success' ? '&#10004;' : '&#10006;';
    wrapper.html(`
        <div class="text-center" style="padding:24px 10px;">
            <div style="font-size:46px;line-height:1;color:${colors[type]};">${icon}</div>
            <div style="margin-top:12px;font-size:15px;color:${colors[type]};font-weight:600;">
                ${message}
            </div>
        </div>
    `);
}

function send_payment_link(frm, dialog) {
    const values = dialog.get_values();
    if (!values) return;

    if (!values.contact_mobile) {
        frappe.msgprint(__('Please enter a contact mobile number.'));
        return;
    }

    frappe.call({
        method: 'life_slimming.razorpay_payment.send_payment_link',
        args: {
            sales_invoice: frm.doc.name,
            amount: values.amount,
            contact_mobile: values.contact_mobile
        },
        freeze: true,
        freeze_message: __('Creating payment link & sending WhatsApp...'),
        callback: function(r) {
            if (r.message && r.message.short_url) {
                dialog.fields_dict.qr_area.$wrapper.html(`
                    <div class="text-success" style="padding:10px;">
                        ${__('Payment link sent on WhatsApp to')} ${values.contact_mobile}<br>
                        <a href="${r.message.short_url}" target="_blank">${r.message.short_url}</a>
                    </div>
                `);
                frappe.show_alert({
                    message: __('Payment link sent to {0}', [values.contact_mobile]),
                    indicator: 'green'
                }, 7);
            }
        }
    });
}
