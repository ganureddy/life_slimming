frappe.provide('erpnext.queries');

frappe.ui.form.on("Patient Appointment",{
	setup: function(frm) {
        frm.set_query('therapy_plan_1', function() {
            return {
                filters: {
                    'status': ['in', ["Not Started",'In Progress']],
					'patient':frm.doc.patient
                }
            };
        }); 
    },

	therapy_plan_1: function(frm) {
		if (frm.doc.therapy_plan_1) {
			frm.trigger('filter_therapy_types');
		}
	},

	filter_therapy_types: function(frm) {
		frappe.call({
			'method': 'frappe.client.get',
			args: {
				doctype: 'Therapy Plan',
				name: frm.doc.therapy_plan_1
			},
			callback: function(data) {
				let therapy_types = (data.message.therapy_plan_details || []).map(function(d){ return d.therapy_type; });
				frm.set_query('therapy_type1', function() {
					return {
						filters: { 'therapy_type': ['in', therapy_types]}
					};
				});
			}
		});
	},
	// refresh: function(frm) {
	// 	frm.set_query('patient', function() {
	// 		return {
	// 			filters: {
	// 				'status': ['in', ["Active"]],
	// 				'branch_name':"Banjar Hills"
	// 			}
	// 		};
	// 	})
	// }
}),


frappe.ui.form.on("Patient Appointment", "refresh", function(frm){
    let selected_slot = null;
	let service_unit = null;
	let duration = null;
	let add_video_conferencing = null;
	let overlap_appointments = null;


	if(frm.doc.call_back_status == 'Scheduled' && !frm.doc.__islocal){
		frm.add_custom_button(__("ReScheduled"),function show_availability (){  
			let d = new frappe.ui.Dialog({
				title: __('Available slots'),
				fields: [
					{ fieldtype: 'Link', options: 'Branch',reqd: 1, fieldname: 'branch', label: 'Branch'},
					{ fieldtype: 'Column Break' },
					{ fieldtype: 'Link', options: 'Service Room',reqd: 1, fieldname: 'service_room', label: 'Service Room'},
					{ fieldtype: 'Column Break' },
					{ fieldtype: 'Link', options: 'Healthcare Service Unit', reqd: 1, fieldname: 'category', label: 'Category'},
					{ fieldtype: 'Column Break' },
					{ fieldtype: 'Link', options: 'Therapy Type', reqd: 1, fieldname: 'concern', label: 'Concern'},
					{ fieldtype: 'Section Break' },
					{ fieldtype: 'Date', reqd: 1, fieldname: 'appointment_date', label: 'Date', min_date: new Date(frappe.datetime.get_today()) },
					{ fieldtype: 'Section Break' },
					{ fieldtype: 'HTML', fieldname: 'available_slots' }
				],	
			   
				primary_action_label: __('Book'),
				primary_action: function() {
					frm.set_value('appointment_time', selected_slot);
					frm.set_value('service_room', d.get_value('service_room'));
					frm.set_value('service_unit', d.get_value('category'));
					frm.set_value('concern', d.get_value('concern'));
					frm.set_value('appointment_date', d.get_value('appointment_date'));
					frm.set_value('branch', d.get_value('branch'));
					frm.set_value("call_back_status","Re-Scheduled")
		
					d.hide();
					frm.enable_save();
					frm.save();
					d.get_primary_btn().attr('disabled', true);
				}
			});
		
			d.set_values({
				'service_room': frm.doc.service_room,
				'category': frm.doc.service_unit,
				'concern':frm.doc.concern,
				// 'appointment_date': frm.doc.appointment_date,
				'branch':frm.doc.branch
			});
		
			// if (!frm.doc.duration) {
			// 			frm.set_value('duration', duration);
			// 		}
		
			d.show();
		
			let fd = d.fields_dict;
			
			d.fields_dict['appointment_date'].df.onchange = () => {
				show_slots(d, fd);
			};
		
			d.fields_dict['service_room'].df.onchange = () => {
				if (d.get_value('service_room')){
					// selected_practitioner = d.get_value('practitioner');
					show_slots(d, fd);
				}
			};
		
			// show_slots(d,fd)
		
			d.get_primary_btn().attr('disabled', null);
		}
		).removeClass('btn-default').addClass('btn-success');
    	}else{
        frm.page.set_primary_action(__('Save'), () => frm.save());
	};

    if (frm.is_new()){
        frm.add_custom_button(__("Check Slots"), function show_availability (){  
		let d = new frappe.ui.Dialog({
			title: __('Available slots'),
			fields: [
				{ fieldtype: 'Link', options: 'Branch',reqd: 1, fieldname: 'branch', label: 'Branch'},
			    { fieldtype: 'Column Break' },
			    { fieldtype: 'Link', options: 'Service Room',reqd: 1, fieldname: 'service_room', label: 'Service Room'},
			    { fieldtype: 'Column Break' },
			    { fieldtype: 'Link', options: 'Healthcare Service Unit', reqd: 1, fieldname: 'category', label: 'Category'},
			    { fieldtype: 'Column Break' },
			    { fieldtype: 'Link', options: 'Therapy Type', reqd: 1, fieldname: 'concern', label: 'Concern'},
				{ fieldtype: 'Section Break' },
				{ fieldtype: 'Date', reqd: 1, fieldname: 'appointment_date', label: 'Date', min_date: new Date(frappe.datetime.get_today()) },
				{ fieldtype: 'Section Break' },
				{ fieldtype: 'HTML', fieldname: 'available_slots' }
		    ],	
		   
			primary_action_label: __('Book'),
			primary_action: function() {
				frm.set_value('appointment_time', selected_slot);
				frm.set_value('service_room', d.get_value('service_room'));
				frm.set_value('service_unit', d.get_value('category'));
				frm.set_value('concern', d.get_value('concern'));
				frm.set_value('appointment_date', d.get_value('appointment_date'));
				frm.set_value('branch', d.get_value('branch'));

				d.hide();
				frm.enable_save();
				frm.save();
				d.get_primary_btn().attr('disabled', true);
			}
		});

        d.set_values({
			'service_room': frm.doc.service_room,
			'service_unit': frm.doc.service_unit,
			'appointment_date': frm.doc.appointment_date,
			'branch':frm.doc.branch
		});

        if (!frm.doc.duration) {
					frm.set_value('duration', duration);
				}

		d.show();

        let fd = d.fields_dict;
        
        d.fields_dict['appointment_date'].df.onchange = () => {
			show_slots(d, fd);
		};

        d.fields_dict['service_room'].df.onchange = () => {
			if (d.get_value('service_room')){
				// selected_practitioner = d.get_value('practitioner');
				show_slots(d, fd);
			}
		};

        // show_slots(d,fd)

		d.get_primary_btn().attr('disabled', null);
	}
    ).removeClass('btn-default').addClass('btn-success');
    }else{
        frm.page.set_primary_action(__('Save'), () => frm.save());
    };

    function show_slots(d, fd) {
        if (d.get_value('appointment_date') && d.get_value('service_room')) {
            fd.available_slots.html('');
            frappe.call({
                method: 'life_slimming.get_availability_data.get_availability_data',
				args: {
					service_room: d.get_value('service_room'),
					date: d.get_value('appointment_date'),
					branch:d.get_value('branch')
				},
                callback: (r) => {
                    let data = r.message;
                    if (data.slot_details.length > 0) {
                        let $wrapper = d.fields_dict.available_slots.$wrapper;
                        let slot_html = get_slots(data.slot_details, d.get_value('appointment_date'));

                        $wrapper
							.css('margin-bottom', 0)
							.addClass('text-center')
							.html(slot_html);

						// highlight button when clicked
                        // highlight button when clicked
						$wrapper.on('click', 'button', function() {
							let $btn = $(this);
							$wrapper.find('button').removeClass('btn-outline-primary');
							$btn.addClass('btn-outline-primary');
							selected_slot = $btn.attr('data-name');
							service_unit = $btn.attr('data-service-unit');
							duration = $btn.attr('data-duration');
							add_video_conferencing = parseInt($btn.attr('data-tele-conf'));
							overlap_appointments = parseInt($btn.attr('data-overlap-appointments'));
							// show option to opt out of tele conferencing
							if ($btn.attr('data-tele-conf') == 1) {
								if (d.$wrapper.find(".opt-out-conf-div").length) {
									d.$wrapper.find(".opt-out-conf-div").show();
								} else {
									overlap_appointments ?
										d.footer.prepend(
											`<div class="opt-out-conf-div ellipsis text-muted" style="vertical-align:text-bottom;">
												<label>
													<span class="label-area">
													${__("Video Conferencing disabled for group consultations")}
													</span>
												</label>
											</div>`
										)
									:
										d.footer.prepend(
											`<div class="opt-out-conf-div ellipsis" style="vertical-align:text-bottom;">
											<label>
												<input type="checkbox" class="opt-out-check"/>
												<span class="label-area">
												${__("Do not add Video Conferencing")}
												</span>
											</label>
										</div>`
										);
								}
							} else {
								d.$wrapper.find(".opt-out-conf-div").hide();
							}

							// enable primary action 'Book'
							d.get_primary_btn().attr('disabled', null);
						});

                    }
                },
                freeze: true,
				freeze_message: __('Fetching Schedule...')
            });

        }else {
			fd.available_slots.html(__('Appointment date and Service Room are Mandatory').bold());
		}
    }

    function get_slots(slot_details, appointment_date) {
		let slot_html = '';
		let appointment_count = 0;
		let disabled = false;
		let start_str, slot_start_time, slot_end_time, interval, count, count_class, tool_tip, available_slots;

		slot_details.forEach((slot_info) => {
			slot_html += `<div class="slot-info">
				<span><b>
				${__('Schedule: ')} </b> ${slot_info.slot_name}
					${slot_info.tele_conf && !slot_info.allow_overlap ? '<i class="fa fa-video-camera fa-1x" aria-hidden="true"></i>' : ''}
				</span><br>
				<span><b> ${__('Service Unit: ')} </b> ${slot_info.service_unit}</span>`;

			if (slot_info.service_unit_capacity) {
				slot_html += `<br><span> <b> ${__('Maximum Capacity:')} </b> ${slot_info.service_unit_capacity} </span>`;
			}

			slot_html += '</div><br>';

			slot_html += slot_info.avail_slot.map(slot => {
				appointment_count = 0;
				disabled = false;
				count_class = tool_tip = '';
				start_str = slot.from_time;
				slot_start_time = moment(slot.from_time, 'HH:mm:ss');
				slot_end_time = moment(slot.to_time, 'HH:mm:ss');
				interval = (slot_end_time - slot_start_time) / 60000 | 0;

				// restrict past slots based on the current time.
				let now = moment();
				if((now.format("YYYY-MM-DD") == appointment_date) && slot_start_time.isBefore(now)){
					disabled = true;
				} else {
					// iterate in all booked appointments, update the start time and duration
					slot_info.appointments.forEach((booked) => {
						let booked_moment = moment(booked.appointment_time, 'HH:mm:ss');
						let end_time = booked_moment.clone().add(booked.duration, 'minutes');

						// Deal with 0 duration appointments
						if (booked_moment.isSame(slot_start_time) || booked_moment.isBetween(slot_start_time, slot_end_time)) {
							if (booked.duration == 0) {
								disabled = true;
								return false;
							}
						}

						// Check for overlaps considering appointment duration
						if (slot_info.allow_overlap != 1) {
							if (slot_start_time.isBefore(end_time) && slot_end_time.isAfter(booked_moment)) {
								// There is an overlap
								disabled = true;
								return false;
							}
						} else {
							if (slot_start_time.isBefore(end_time) && slot_end_time.isAfter(booked_moment)) {
								appointment_count++;
							}
							if (appointment_count >= slot_info.service_unit_capacity) {
								// There is an overlap
								disabled = true;
								return false;
							}
						}
					});
				}

				if (slot_info.allow_overlap == 1 && slot_info.service_unit_capacity > 1) {
					available_slots = slot_info.service_unit_capacity - appointment_count;
					count = `${(available_slots > 0 ? available_slots : __('Full'))}`;
					count_class = `${(available_slots > 0 ? 'badge-success' : 'badge-danger')}`;
					tool_tip =`${available_slots} ${__('slots available for booking')}`;
				}

				return `
					<button class="btn btn-secondary" data-name=${start_str}
						data-duration=${interval}
						data-service-unit="${slot_info.service_unit || ''}"
						data-tele-conf="${slot_info.tele_conf || 0}"
						data-overlap-appointments="${slot_info.service_unit_capacity || 0}"
						style="margin: 0 10px 10px 0; width: auto;" ${disabled ? 'disabled="disabled"' : ""}
						data-toggle="tooltip" title="${tool_tip || ''}">
						${start_str.substring(0, start_str.length - 3)}
						${slot_info.service_unit_capacity ? `<br><span class='badge ${count_class}'> ${count} </span>` : ''}
					</button>`;

			}).join("");

			if (slot_info.service_unit_capacity) {
				slot_html += `<br/><small>${__('Each slot indicates the capacity currently available for booking')}</small>`;
			}
			slot_html += `<br/><br/>`;
		});

		return slot_html;
	}
	
});