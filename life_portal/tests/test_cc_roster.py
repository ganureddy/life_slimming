"""Ho CC roster boundaries, interval coverage and safe HR shift replacement."""
from datetime import date
import unittest
from unittest.mock import Mock, patch

import frappe
from life_slimming.api import cc_roster as api


class RosterDates(unittest.TestCase):
    def test_week_and_leap_month(self):
        self.assertEqual(api.period_for('2026-11-04', 'week'), (date(2026,11,2), date(2026,11,8)))
        self.assertEqual(api.period_for('2024-02-29', 'month'), (date(2024,2,1), date(2024,2,29)))
        with self.assertRaises(frappe.ValidationError): api.period_for('2026-11-04', 'year')

    def test_range_shifts_and_open_ended_shifts_cover_each_day(self):
        shifts = [dict(name='RANGE',employee='E1',start_date='2026-11-01',end_date='2026-11-03',shift_type='Morning',modified='v1'),
                  dict(name='OPEN',employee='E1',start_date='2026-11-04',end_date=None,shift_type='Evening',modified='v2')]
        days, cells = api.build_days([{'name':'E1'}], shifts,
            [dict(employee='E1',attendance_date='2026-11-02',status='Present')],
            [dict(employee='E1',from_date='2026-11-03',to_date='2026-11-04')], date(2026,11,2), date(2026,11,8))
        self.assertEqual(len(days),7)
        self.assertEqual(cells['E1']['2026-11-02']['shifts'][0]['name'],'RANGE')
        self.assertEqual(cells['E1']['2026-11-08']['shifts'][0]['name'],'OPEN')
        self.assertFalse(cells['E1']['2026-11-02']['shifts'][0]['single_day'])
        self.assertTrue(cells['E1']['2026-11-03']['leave'])
        self.assertEqual(cells['E1']['2026-11-02']['attendance'],'Present')
        self.assertEqual(cells['E1']['2026-11-07']['attendance'],'')

    def test_conflicts_are_retained_instead_of_hiding_one_shift(self):
        row = dict(employee='E1',start_date='2026-11-02',end_date='2026-11-02',shift_type='Morning',modified='v1')
        _, cells = api.build_days([{'name':'E1'}], [dict(row,name='S1'),dict(row,name='S2')],[],[],date(2026,11,2),date(2026,11,2))
        self.assertEqual(len(cells['E1']['2026-11-02']['shifts']),2)


class RosterPermissions(unittest.TestCase):
    def setUp(self):
        frappe.local.session=frappe._dict(user='cc@example.test')
        frappe.local.flags=frappe._dict(in_test=True)

    def tearDown(self): frappe.destroy()

    def test_guest_and_module_denial(self):
        frappe.session.user='Guest'
        with patch.object(api,'require_module') as require:
            with self.assertRaises(frappe.AuthenticationError): api.authorize()
            require.assert_not_called()
        frappe.session.user='cc@example.test'
        with patch.object(api,'require_module',side_effect=frappe.PermissionError):
            with self.assertRaises(frappe.PermissionError): api.authorize()

    def test_only_export_and_system_manager_can_edit(self):
        for roles, expected in [(['Call Center Export'], True), (['System Manager'], True),
                                (['HR Manager'], False), (['HR User'], False),
                                (['Sales Manager'], False), (['Sales User'], False),
                                (['Employee'], False), ([], False)]:
            with self.subTest(roles=roles), patch.object(frappe, 'get_roles', return_value=roles), \
                 patch.object(frappe, 'has_permission', return_value=True):
                self.assertEqual(api.can_edit(), expected)

    def test_calendar_always_reads_only_hocc_employees(self):
        db=Mock();db.exists.return_value=False
        with patch.object(api,'authorize'), patch.object(api,'nowdate',return_value='2026-11-04'), patch.object(frappe,'db',db), patch.object(api,'can_edit',return_value=False), \
             patch.object(frappe,'get_all',return_value=[]) as query:
            result=api.calendar_view('2026-11-04','week')
        self.assertEqual(query.call_args_list[0].kwargs['filters'],{'branch':'Ho CC','status':'Active'})
        self.assertEqual(result['employees'],[])
        self.assertEqual(len(result['days']),7)
        self.assertFalse(result['can_edit'])


class RosterWrites(unittest.TestCase):
    def setUp(self):
        frappe.local.flags=frappe._dict(in_test=True)
        self.db=Mock();self.db.exists.return_value=True
        self.employee=frappe._dict(name='E1',branch='Ho CC',status='Active',company='Life')
        self.old_doc=Mock();self.new_doc=Mock();self.new_doc.name='NEW'
        self.current=[]
        def get_doc(dt, name=None):
            if isinstance(dt,dict):
                self.created=dt
                return self.new_doc
            return self.employee if dt=='Employee' else self.old_doc
        for context in [patch.object(api,'authorize'),patch.object(api,'can_edit',return_value=True),
                        patch.object(frappe,'db',self.db),patch.object(frappe,'get_doc',side_effect=get_doc),
                        patch.object(api,'assignments',side_effect=lambda *args:self.current)]:
            context.start();self.addCleanup(context.stop)

    def shift(self, **overrides):
        return dict(dict(name='OLD',employee='E1',shift_type='Morning',start_date='2026-11-04',end_date='2026-11-04',modified='v1'),**overrides)

    def test_create_uses_normal_insert_and_submit(self):
        result=api.save_shift('E1','2026-11-04','Morning')
        self.assertEqual(result['name'],'NEW')
        self.new_doc.insert.assert_called_once_with(ignore_permissions=True)
        self.new_doc.submit.assert_called_once_with()
        self.assertEqual(self.created['end_date'],'2026-11-04')
        self.assertIn('FOR UPDATE',self.db.sql.call_args.args[0])

    def test_other_branch_or_inactive_employee_cannot_be_written(self):
        for key,value in [('branch','Other'),('status','Left')]:
            original=self.employee[key];self.employee[key]=value
            with self.assertRaises(frappe.PermissionError): api.save_shift('E1','2026-11-04','Morning')
            self.employee[key]=original
        self.new_doc.insert.assert_not_called()

    def test_viewer_denied_before_database_lock(self):
        with patch.object(api,'can_edit',return_value=False):
            with self.assertRaises(frappe.PermissionError): api.save_shift('E1','2026-11-04','Morning')
        self.db.sql.assert_not_called()

    def test_stale_version_or_newly_added_assignment_is_not_overwritten(self):
        self.current=[self.shift()]
        for assignment,version in [('', ''),('OLD','old-version')]:
            with self.assertRaises(frappe.TimestampMismatchError): api.save_shift('E1','2026-11-04','Evening',assignment,version)
        self.old_doc.cancel.assert_not_called()

    def test_range_and_conflicts_are_not_cancelled(self):
        for rows in [[self.shift(start_date='2026-11-01')],[self.shift(end_date=None)],[self.shift(),self.shift(name='OTHER')]]:
            self.current=rows
            with self.assertRaises(frappe.ValidationError): api.save_shift('E1','2026-11-04','Evening','OLD','v1')
        self.old_doc.cancel.assert_not_called()

    def test_authorized_replacement_uses_scoped_permissions(self):
        self.current=[self.shift()]
        api.save_shift('E1','2026-11-04','Evening','OLD','v1')
        self.assertTrue(self.old_doc.flags.ignore_permissions)
        self.assertTrue(self.new_doc.flags.ignore_permissions)
        self.old_doc.cancel.assert_called_once_with()
        self.new_doc.insert.assert_called_once_with(ignore_permissions=True)

    def test_clear_cancels_without_deleting_or_creating(self):
        self.current=[self.shift()]
        api.save_shift('E1','2026-11-04','','OLD','v1')
        self.old_doc.cancel.assert_called_once_with()
        self.old_doc.delete.assert_not_called();self.new_doc.insert.assert_not_called()


if __name__=='__main__': unittest.main()
