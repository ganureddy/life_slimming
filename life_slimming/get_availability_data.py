import frappe
from frappe.utils import flt, get_link_to_form, get_time, getdate
from frappe import _
# from healthcare.healthcare.doctype.patient_appointment.patient_appointment import * 
from frappe.model.document import Document
import datetime
from healthcare.healthcare.doctype.patient_appointment.patient_appointment import PatientAppointment,MaximumCapacityError,OverlapError


@frappe.whitelist()
def get_availability_data(date, service_room,branch):
    
    date = getdate(date)
    weekday = date.strftime("%A")
    
    service_doc = frappe.db.get_list("Room Wise Slots",{"service_room":service_room,"branch":branch},['branch','schedule','service_room','service_unit'],ignore_permissions=True)
    

    if len(service_doc)>0:
        slot_details = get_available_slots(service_doc, date)
    else:
        frappe.throw(
            _(
                "{0} does not have a Healthcare Service Room Schedule. Add it in Service Time Slot Master"
            ).format(service_doc[0]['service_room']),
            title=_("Service Room Schedule Not Found"),
        )
    
    if not slot_details:
        # TODO: return available slots in nearby dates
        frappe.throw(
            _("Healthcare Practitioner not available on {0}").format(weekday), title=_("Not Available")
        )

    return {"slot_details": slot_details}


def get_available_slots(service_doc, date):
    available_slots = slot_details = []
    weekday = date.strftime("%A")
    service_room = service_doc[0]['service_room']

    for schedule_entry in service_doc:
        # validate_practitioner_schedules(schedule_entry, service_room)
        
        practitioner_schedule = frappe.get_doc("Practitioner Schedule", schedule_entry.schedule)

        if practitioner_schedule and not practitioner_schedule.disabled:
            available_slots = []
            for time_slot in practitioner_schedule.time_slots:
                if weekday == time_slot.day:
                    available_slots.append(time_slot)

            if available_slots:
                appointments = []
                allow_overlap = 0
                service_unit_capacity = 0
                # fetch all appointments to service room  by service unit
                filters = {
                    "service_room": service_room,
                    "service_unit": schedule_entry.service_unit,
                    "appointment_date": date,
                    "call_back_status": ["not in", ["Cancel"]],
                    "practitioner":''
                }
                # slot_name = f"{schedule_entry.schedule}"
                if schedule_entry.service_unit:
                    slot_name = f"{schedule_entry.schedule}"
                    allow_overlap, service_unit_capacity = frappe.get_value(
                        "Healthcare Service Unit",
                        schedule_entry.service_unit,
                        ["overlap_appointments", "service_unit_capacity"],
                    )
                    if not allow_overlap:
                        # fetch all appointments to service unit
                        filters.pop("practitioner")
                else:
                    slot_name = schedule_entry.schedule
                    # fetch all appointments to practitioner without service unit
                    filters["service_room"] = service_room
                    filters.pop("service_unit")

                appointments = frappe.get_all(
                    "Patient Appointment",
                    filters=filters,
                    fields=["name", "appointment_time", "duration", "call_back_status"],
                )

                slot_details.append(
                    {
                        "slot_name": slot_name,
                        "service_unit": schedule_entry.service_unit,
                        "avail_slot": available_slots,
                        "appointments": appointments,
                        "allow_overlap": allow_overlap,
                        "service_unit_capacity": service_unit_capacity,
                        "tele_conf": practitioner_schedule.allow_video_conferencing,
                    }
                )
    return slot_details

@frappe.whitelist(allow_guest=True)
def get_availability_data_for_frontend(date, service_room,branch):

    slot_details_frontend = get_availability_data(date, service_room,branch)
    slot_details = slot_details_frontend["slot_details"]
    avail_slot = [dict(each.as_dict()) for each in slot_details[0]['avail_slot']]
    
    if len(slot_details[0].get("appointments")) >0:
        for each_slot in avail_slot:
            appointment_date = datetime.datetime.strptime(date,"%Y-%m-%d").date()
            current_date = datetime.datetime.now().date()
            from_time = each_slot.get("from_time")
            end_time = each_slot.get("to_time")
            current_time = datetime.datetime.now().time().replace(second=0,microsecond=0)
            target_timedelta = datetime.timedelta(hours=current_time.hour, minutes=current_time.minute, seconds=current_time.second)

            if appointment_date == current_date and from_time < target_timedelta:
                each_slot.update({
                        "disabled": "Yes"
                    })
            else:
                for data in slot_details[0]['appointments']:
                    booking_time = data.appointment_time
                    duration_timedelta = datetime.timedelta(minutes=int(data["duration"]))
                    end_datetime = booking_time + duration_timedelta
                    
                    if booking_time == from_time:
                        each_slot.update({"disabled": "Yes"})
                        
                    if from_time < end_datetime and from_time > booking_time:
                        each_slot.update({"disabled": "Yes"})
                    
        slot_details[0]['avail_slot'] = avail_slot
         
        return {"slot_details": slot_details}
    else:
        for each_slot in avail_slot:
            appointment_date = datetime.datetime.strptime(date,"%Y-%m-%d").date()
            current_date = datetime.datetime.now().date()
            from_time = each_slot.get("from_time")
            end_time = each_slot.get("to_time")
            current_time = datetime.datetime.now().time().replace(second=0,microsecond=0)
            target_timedelta = datetime.timedelta(hours=current_time.hour, minutes=current_time.minute, seconds=current_time.second)

            if appointment_date == current_date and from_time < target_timedelta:
                each_slot.update({"disabled": "Yes"})
                
        slot_details[0]['avail_slot'] = avail_slot
        
        return {"slot_details": slot_details}

        
        
class Validate_Patient_Appointment(Document):
    def validate_overlaps(self):
        end_time = datetime.datetime.combine(
            getdate(self.appointment_date), get_time(self.appointment_time)
        ) + datetime.timedelta(minutes=flt(self.duration))

        # all appointments for both patient and practitioner overlapping the duration of this appointment
        overlapping_appointments = frappe.db.sql(
            """
            SELECT
                name, practitioner, patient, appointment_time, duration, service_unit
            FROM
                `tabPatient Appointment`
            WHERE
                appointment_date=%(appointment_date)s AND name!=%(name)s AND status NOT IN ("Closed", "Cancelled") AND
                (practitioner=%(practitioner)s OR patient=%(patient)s) AND
                ((appointment_time<%(appointment_time)s AND appointment_time + INTERVAL duration MINUTE>%(appointment_time)s) OR
                (appointment_time>%(appointment_time)s AND appointment_time<%(end_time)s) OR
                (appointment_time=%(appointment_time)s))
            """,
            {
                "appointment_date": self.appointment_date,
                "name": self.name,
                "practitioner": self.practitioner,
                "patient": self.patient,
                "appointment_time": self.appointment_time,
                "end_time": end_time.time(),
            },
            as_dict=True,
        )

        if not overlapping_appointments:
            return  # No overlaps, nothing to validate!

        if self.service_unit:  # validate service unit capacity if overlap enabled
            allow_overlap, service_unit_capacity = frappe.get_value(
                "Healthcare Service Unit", self.service_unit, ["overlap_appointments", "service_unit_capacity"]
            )
            if allow_overlap:
                service_unit_appointments = list(
                    filter(
                        lambda appointment: appointment["service_unit"] == self.service_unit
                        and appointment["patient"] != self.patient,
                        overlapping_appointments,
                    )
                )  # if same patient already booked, it should be an overlap
                if len(service_unit_appointments) >= (service_unit_capacity or 1):
                    frappe.throw(
                        _("Not allowed, {} cannot exceed maximum capacity {}").format(
                            frappe.bold(self.service_unit), frappe.bold(service_unit_capacity or 1)
                        ),
                        MaximumCapacityError,
                    )
                else:  # service_unit_appointments within capacity, remove from overlapping_appointments
                    overlapping_appointments = [
                        appointment
                        for appointment in overlapping_appointments
                        if appointment not in service_unit_appointments
                    ]
                
        self.service_room_restict(self)

        if overlapping_appointments:
            pass
            # frappe.throw(
            #     _("Not allowed, cannot overlap appointment {}").format(
            #         frappe.bold(", ".join([appointment["name"] for appointment in overlapping_appointments]))
            #     ),
            #     OverlapError,
            # )
    

        
        