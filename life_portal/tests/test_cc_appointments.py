"""Scheduler boundaries, conflicts and permissions without business writes."""
import unittest
from datetime import datetime
from unittest.mock import Mock, patch
import frappe
from life_slimming.api import cc_appointments as api


class TimeRules(unittest.TestCase):
    def test_minimum_duration(self):
        for duration in [15, 30, 44, 0, -45, 'bad']:
            with self.assertRaises(frappe.ValidationError): api.interval('2030-01-01 10:00:00', duration, datetime(2029,1,1))

    def test_open_and_last_slot(self):
        for stamp, duration in [('2030-01-01 10:00:00',45),('2030-01-01 19:15:00',45),('2030-01-01 19:00:00',60)]:
            start,end=api.interval(stamp,duration,datetime(2029,1,1));self.assertEqual((end-start).total_seconds(),duration*60)

    def test_closed_past_and_non_grid_times(self):
        for stamp in ['2030-01-01 09:45:00','2030-01-01 19:30:00','2030-01-01 20:00:00','2030-01-01 10:01:00','2028-01-01 10:00:00']:
            with self.assertRaises(frappe.ValidationError):api.interval(stamp,45,datetime(2029,1,1))

    def test_overlap_and_adjacent(self):
        dt=lambda h,m:datetime(2030,1,1,h,m)
        self.assertFalse(api.overlaps(dt(10,45),dt(11,30),dt(10,0),dt(10,45)))
        self.assertTrue(api.overlaps(dt(10,15),dt(11,0),dt(10,0),dt(10,45)))
        self.assertTrue(api.overlaps(dt(10,0),dt(11,0),dt(10,15),dt(10,45)))

    def test_role_labels(self):
        for value,expected in [('Area Manager','Area Manager'),('Branch Manager','Manager'),('Sr Dietician','Dietitian'),('Doctor','Doctor'),('Receptionist','')]:self.assertEqual(api.role_group(value),expected)


class BookingRules(unittest.TestCase):
    def setUp(self):
        frappe.local.flags=frappe._dict(in_test=True)
        frappe.local.session=frappe._dict(user='agent')
        self.staff=dict(id='Employee:E1',name='Staff',role='Manager',employee='E1',practitioner='')
        self.doc=frappe._dict(custom_cc_booking=1,status='Open',branch='Branch A',custom_cc_resource='Employee:E1',party='LEAD1',scheduled_time='2030-01-01 10:00:00',duration='45 Minutes',name='NEW')
        self.doc.is_new=lambda:True
        self.db=Mock();self.db.sql.return_value=[]
        for p in [patch.object(api,'authorize'),patch.object(api,'branch_access'),patch.object(api,'staff_for',return_value=[self.staff]),patch.object(api,'lead_access',return_value=frappe._dict(name='LEAD1',lead_name='Client',mobile_no='9876543210',lead_owner='assigned-agent')),patch.object(api,'now_datetime',return_value=datetime(2029,1,1)),patch.object(frappe,'db',self.db)]:p.start();self.addCleanup(p.stop)

    def test_staff_locked_before_conflict_check(self):
        def existing(*args,**kwargs):
            self.assertIn('FOR UPDATE',self.db.sql.call_args_list[0].args[0]);return []
        with patch.object(api,'resource_appointments',side_effect=existing):api.validate_booking(self.doc)
        self.assertEqual(self.doc.appointment_time,datetime(2030,1,1,10,45))
        self.assertEqual(self.doc.lead_owner,'assigned-agent')

    def test_cross_branch_overlap_rejected(self):
        busy=frappe._dict(name='OLD',branch='Other branch',scheduled_time='2030-01-01 10:15:00',appointment_time='2030-01-01 11:00:00')
        with patch.object(api,'resource_appointments',return_value=[busy]):
            with self.assertRaisesRegex(frappe.ValidationError,'already booked'):api.validate_booking(self.doc)

    def test_unmapped_staff_rejected(self):
        self.doc.custom_cc_resource='Employee:OTHER'
        with self.assertRaisesRegex(frappe.ValidationError,'not available'):api.validate_booking(self.doc)
        self.db.sql.assert_not_called()

    def test_short_duration_cannot_bypass_api(self):
        self.doc.duration='30 Minutes'
        with self.assertRaises(frappe.ValidationError):api.validate_booking(self.doc)

    def test_unauthorized_lead_cannot_book(self):
        with patch.object(api,'lead_access',side_effect=frappe.PermissionError):
            with self.assertRaises(frappe.PermissionError):api.validate_booking(self.doc)
        self.db.sql.assert_not_called()

    def test_duplicate_client_overlap(self):
        self.db.sql.side_effect=[[],[],[('EXISTING',)]]
        with patch.object(api,'resource_appointments',return_value=[]):
            with self.assertRaisesRegex(frappe.ValidationError,'lead already'):api.validate_booking(self.doc)


class DashboardBookingRules(unittest.TestCase):
    def setUp(self):
        frappe.local.session = frappe._dict(user='manager')
        self.db = Mock()
        self.db.get_value.return_value = None
        for mock in [patch.object(api, 'authorize'), patch.object(api, 'lead_access'),
                     patch.object(api, 'branch_access'), patch.object(frappe, 'db', self.db),
                     patch.object(api, 'now_datetime', return_value=datetime(2029, 1, 1))]:
            mock.start()
            self.addCleanup(mock.stop)

    def test_confirmed_booking_updates_dashboard(self):
        doc = Mock(name='appointment')
        doc.name = 'APT1'
        doc.duration = '45 Minutes'
        doc.custom_consultation_taken_by = 'DOCTOR1'
        doc.custom_cc_staff_name = 'Consultation Manager'
        with patch.object(frappe, 'get_doc', return_value=doc):
            result = api.book('LEAD1', 'Branch A', 'Employee:E1', '2030-01-01 10:00:00', 45, 'a' * 32)
        doc.insert.assert_called_once_with(ignore_permissions=True)
        values = self.db.set_value.call_args.args[2]
        self.assertEqual(result['name'], 'APT1')
        self.assertEqual(values['custom_appointment'], 'APT1')
        self.assertEqual(values['custom_cc_sub_status'], 'Appointment Booked')
        self.assertEqual(values['custom_appointment_duration'], '45 Minutes')
        self.assertEqual(values['status'], 'Appointment Booked')
        self.assertNotIn('lead_owner', values)

    def test_manager_retry_uses_booking_creator_not_lead_owner(self):
        self.db.get_value.return_value = frappe._dict(
            name='APT1', party='LEAD1', owner='manager', lead_owner='assigned-agent',
            branch='Branch A', custom_cc_resource='Employee:E1',
            scheduled_time='2030-01-01 10:00:00', duration='45 Minutes')
        result = api.book('LEAD1', 'Branch A', 'Employee:E1', '2030-01-01 10:00:00', 45, 'a' * 32)
        self.assertTrue(result['already_booked'])
        self.db.set_value.assert_not_called()


class StaffBranchRules(unittest.TestCase):
    def setUp(self):
        self.employees = [frappe._dict(name='E1', employee_name='Manager A', designation='Manager', branch='Branch A', custom_branch_list='Branch C')]
        self.practitioners = [frappe._dict(name='P1', practitioner_name='Manager A', employee='E1', branch='Branch B', custom_available_all_branches=1)]
        def get_all(doctype, **kwargs):
            return self.employees if doctype == 'Employee' else self.practitioners
        def branches(doctype, name, primary, table, extra=''):
            return {primary, 'Branch D'} | set((extra or '').split(','))
        for mock in [patch.object(frappe, 'get_all', side_effect=get_all),
                     patch.object(frappe, 'get_meta', return_value=Mock(has_field=lambda field: True)),
                     patch.object(frappe, 'db', Mock()),
                     patch.object(api, 'mapped_branches', side_effect=branches)]:
            mock.start()
            self.addCleanup(mock.stop)

    def test_all_branch_practitioner_cannot_add_employee_from_other_branch(self):
        self.assertEqual(api.staff_for('Branch B'), [])

    def test_employee_primary_and_additional_branches_include_practitioner_conflicts(self):
        for branch in ['Branch A', 'Branch C', 'Branch D']:
            staff = api.staff_for(branch)
            self.assertEqual(len(staff), 1)
            self.assertEqual(staff[0]['id'], 'Employee:E1')
            self.assertEqual(staff[0]['practitioners'], ['P1'])

    def test_unlinked_practitioner_is_not_an_eligible_employee(self):
        self.practitioners[0].employee = ''
        self.practitioners[0].custom_available_all_branches = 0
        self.assertEqual(api.staff_for('Branch B'), [])
        self.assertEqual(api.staff_for('Branch Z'), [])

    def test_inactive_employee_cannot_return_through_practitioner(self):
        self.employees.clear()
        self.assertEqual(api.staff_for('Branch B'), [])


    def test_practitioner_does_not_override_employee_designation(self):
        for designation in ['THERAPIST', 'Dr.Assistant', 'Store Manager', 'Digital Marketing Manager', 'Operation Manager', None]:
            self.employees[0].designation = designation
            self.assertEqual(api.staff_for('Branch A'), [], designation)

    def test_clinical_designations_and_abbreviations(self):
        for designation, group in [('ACM', 'Manager'), ('TACM', 'Manager'), ('TCM', 'Manager'),
                                   ('Assistant Centre Manager', 'Manager'), ('Consultant Doctor', 'Doctor'),
                                   ('DIETICIAN', 'Dietitian'), ('Area Manager (Trainee)', 'Area Manager')]:
            self.employees[0].designation = designation
            staff = api.staff_for('Branch A')
            self.assertEqual(staff[0]['role'], group)
            self.assertEqual(staff[0]['designation'], designation)


class DashboardAppointmentDetails(unittest.TestCase):
    def test_appointment_details_are_scoped_to_the_authorized_lead(self):
        rows = [frappe._dict(name='LEAD1', custom_appointment='APT1'),
                frappe._dict(name='LEAD2', custom_appointment='APT1')]
        appointment = frappe._dict(name='APT1', party='LEAD1', custom_cc_staff_name='Staff A',
            custom_cc_staff_role='ACM', scheduled_time='2030-01-01 10:00:00',
            appointment_time='2030-01-01 10:45:00')
        with patch.object(frappe, 'get_all', return_value=[appointment]):
            api.enrich_lead_appointments(rows)
        self.assertEqual(rows[0]['cc_consultation_employee'], 'Staff A')
        self.assertEqual(rows[0]['cc_consultation_designation'], 'ACM')
        self.assertEqual(rows[0]['cc_appointment_end'], '2030-01-01 10:45:00')
        self.assertNotIn('cc_consultation_employee', rows[1])

    def test_unbooked_leads_do_not_query_appointments(self):
        with patch.object(frappe, 'get_all') as query:
            api.enrich_lead_appointments([frappe._dict(name='LEAD1')])
        query.assert_not_called()
