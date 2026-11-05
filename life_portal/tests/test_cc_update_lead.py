"""Check-only lead updates must never run save hooks or write records."""
import unittest
from unittest.mock import Mock, patch

import frappe
from life_slimming.api.server_scripts import cc_update_lead as api


class CheckLeadUpdateTests(unittest.TestCase):
    def setUp(self):
        frappe.local.flags = frappe._dict(in_test=True)
        frappe.local.session = frappe._dict(user='agent@example.test')
        frappe.local.response = frappe._dict()
        frappe.local.form_dict = frappe._dict(
            lead='LEAD1', values={'custom_cc_sub_status': 'Callback: Scheduled'},
            expected_modified='v1', validate_only=1)
        self.db = Mock()
        self.db.exists.return_value = True
        self.db.get_value.side_effect = lambda dt, name, field: {
            'modified': 'v1', 'custom_appointment_status': 'Not Booked',
            'source': 'Website'}.get(field)
        self.doc = Mock()
        self.doc.name = 'LEAD1'
        self.doc.modified = 'v2'
        self.roles = ['Sales User']
        def throw(message, exc=frappe.ValidationError):
            raise exc(message)

        for context in [patch.object(frappe, 'db', self.db),
                        patch.object(frappe, 'throw', side_effect=throw),
                        patch.object(frappe, 'get_all', side_effect=lambda *a, **k: self.roles),
                        patch.object(frappe, 'get_doc', return_value=self.doc)]:
            context.start()
            self.addCleanup(context.stop)

    def tearDown(self):
        frappe.destroy()

    def run_update(self, **args):
        frappe.local.form_dict.update(args)
        result = api.run()
        return result if result is not None else frappe.response['message']

    def assert_no_writes(self):
        self.doc.save.assert_not_called()
        self.db.set_value.assert_not_called()
        self.db.commit.assert_not_called()

    def test_check_normalizes_status_without_saving(self):
        result = self.run_update()
        self.assertEqual(result['validation_only'], 1)
        self.assertEqual(result['changed'], 0)
        self.assertEqual(result['modified'], 'v1')
        self.assertEqual(result['values']['status'], 'Call Back')
        self.assertEqual(result['values']['custom_cc_stage'], 'FOLLOW-UP')
        self.assert_no_writes()

    def test_check_rejects_stale_update(self):
        result = self.run_update(expected_modified='old')
        self.assertEqual(result['conflict'], 1)
        self.assertEqual(result['ok'], 0)
        self.assert_no_writes()

    def test_check_keeps_role_and_appointment_guards(self):
        self.roles = []
        with self.assertRaises(frappe.ValidationError):
            self.run_update()
        self.roles = ['Sales User']
        with self.assertRaises(frappe.ValidationError):
            self.run_update(values={'custom_appointment_status': 'Cancelled'})
        self.assert_no_writes()

    def test_check_does_not_approve_only_disallowed_fields(self):
        result = self.run_update(values={'lead_owner': 'other@example.test', 'docstatus': 2})
        self.assertEqual(result['ok'], 0)
        self.assertEqual(set(result['skipped']), {'lead_owner', 'docstatus'})
        self.assert_no_writes()

    def test_false_flag_still_saves(self):
        for flag in (0, '0', False, 'false', None):
            with self.subTest(flag=flag):
                self.doc.reset_mock()
                result = self.run_update(validate_only=flag)
                self.assertEqual(result['ok'], 1)
                self.doc.save.assert_called_once_with(ignore_permissions=True)
                self.assertNotIn('validation_only', result)

    def test_true_flags_do_not_save(self):
        for flag in (1, '1', True, 'true', 'yes', 'on'):
            with self.subTest(flag=flag):
                self.assertEqual(self.run_update(validate_only=flag)['validation_only'], 1)
                self.assert_no_writes()


if __name__ == '__main__':
    unittest.main()
