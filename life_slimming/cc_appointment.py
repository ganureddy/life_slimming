"""Keep standard appointments intact; CC bookings use staff-specific capacity."""
import frappe
from erpnext.crm.doctype.appointment.appointment import Appointment
from life_slimming.api.cc_appointments import validate_booking


class CCAppointment(Appointment):
    def before_insert(self):
        if not self.get('custom_cc_booking'):
            return super().before_insert()

    def validate(self):
        validate_booking(self)

    def after_insert(self):
        if not self.get('custom_cc_booking'):
            return super().after_insert()
        event = frappe.get_doc(dict(doctype='Event', subject='Consultation: ' + self.customer_name,
            starts_on=self.scheduled_time, ends_on=self.appointment_time,
            event_type='Private', status='Open', send_reminder=0,
            event_participants=[dict(reference_doctype='Lead', reference_docname=self.party)]))
        kind, name = self.custom_cc_resource.split(':', 1)
        if kind == 'Employee': event.append('event_participants', dict(reference_doctype=kind, reference_docname=name))
        event.insert(ignore_permissions=True)
        self.db_set('calendar_event', event.name, update_modified=False)

    def on_change(self):
        if not self.get('custom_cc_booking'):
            return super().on_change()
        if self.calendar_event:
            frappe.db.set_value('Event', self.calendar_event, dict(starts_on=self.scheduled_time,
                ends_on=self.appointment_time, status='Closed' if self.status == 'Closed' else 'Open'))
