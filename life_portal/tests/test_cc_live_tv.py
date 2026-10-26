"""Isolated permission/query tests; no running Frappe site required."""
import importlib.util
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch


class LiveTVTests(unittest.TestCase):
    def load(self, user='agent', roles=('Sales User',)):
        frappe = types.ModuleType('frappe')
        frappe.whitelist = lambda: lambda fn: fn
        frappe.session = types.SimpleNamespace(user=user)
        frappe.AuthenticationError = type('AuthenticationError', (Exception,), {})
        frappe.PermissionError = type('PermissionError', (Exception,), {})
        frappe.ValidationError = type('ValidationError', (Exception,), {})
        frappe.get_roles = Mock(return_value=roles)
        frappe.get_meta = Mock(return_value=types.SimpleNamespace(has_field=lambda field: True))
        frappe.get_all = Mock(return_value=[])
        utils = types.ModuleType('frappe.utils')
        utils.now_datetime = lambda: datetime(2026, 10, 9, 10)
        utils.get_system_timezone = lambda: 'Asia/Kolkata'
        access = types.ModuleType('life_slimming.portal_access')
        access.require_module = Mock()
        spec = importlib.util.spec_from_file_location('cc_live_tv_test', Path(__file__).parents[2] / 'life_slimming/api/cc_live_tv.py')
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': frappe, 'frappe.utils': utils, 'life_slimming.portal_access': access}):
            spec.loader.exec_module(module)
        return module, frappe, access

    def test_agent_scope_and_untruncated_snapshot(self):
        module, frappe, access = self.load()
        result = module.snapshot()
        access.require_module.assert_called_once_with('leads')
        self.assertTrue(result['restricted_to_owner'])
        self.assertEqual(frappe.get_all.call_args.kwargs['filters'], {'lead_owner': 'agent'})
        self.assertEqual(frappe.get_all.call_args.kwargs['limit_page_length'], 0)
        self.assertIn('custom_appointment_status', frappe.get_all.call_args.kwargs['fields'])
        self.assertNotIn('custom_visit_status', frappe.get_all.call_args.kwargs['fields'])
        self.assertEqual(result['today'], '2026-10-09')

    def test_owner_photo_is_returned_with_name(self):
        module, frappe, _ = self.load()
        class Row(dict):
            __getattr__ = dict.__getitem__
        lead_rows = [Row(lead_owner='agent'), Row(lead_owner='disabled'), Row(lead_owner=None)]
        user_rows = [Row(name='agent', full_name='Agent A', user_image='/files/agent.jpg')]
        frappe.get_all.side_effect = lambda doctype, **kwargs: lead_rows if doctype == 'Lead' else user_rows
        result = module.snapshot()
        self.assertEqual(result['agents'], {'agent': 'Agent A'})
        self.assertEqual(result['agent_images'], {'agent': '/files/agent.jpg'})
        self.assertEqual(len(result['rows']), 3)
        self.assertEqual(frappe.get_all.call_args.kwargs['filters'],
                         {'name': ['in', ['agent', 'disabled']], 'enabled': 1})
        user_rows[0]['user_image'] = None
        self.assertEqual(module.snapshot()['agent_images'], {'agent': ''})
        user_rows.clear()
        self.assertEqual(module.snapshot()['agents'], {})

    def test_month_cycle_boundaries(self):
        for today, start, end in [
            (datetime(2026, 10, 5), '2026-09-06', '2026-10-06'),
            (datetime(2026, 10, 6), '2026-10-06', '2026-11-06'),
            (datetime(2027, 1, 5), '2026-12-06', '2027-01-06'),
            (datetime(2027, 1, 6), '2027-01-06', '2027-02-06'),
            (datetime(2028, 2, 29), '2028-02-06', '2028-03-06'),
        ]:
            with self.subTest(today=today):
                module, frappe, _ = self.load()
                module.now_datetime = lambda: today
                result = module.snapshot()
                self.assertEqual((result['month_start'], result['month_end']), (start, end))
                since = min(start, result['week_start'])
                self.assertTrue(all(item[2] == since for item in frappe.get_all.call_args.kwargs['or_filters']))

    def test_week_can_start_in_previous_month(self):
        module, frappe, _ = self.load()
        module.now_datetime = lambda: datetime(2026, 11, 1, 10)
        result = module.snapshot()
        self.assertEqual(result['week_start'], '2026-10-26')
        self.assertEqual(result['week_end'], '2026-11-02')
        self.assertTrue(all(item[2] == '2026-10-06' for item in frappe.get_all.call_args.kwargs['or_filters']))
        self.assertIn('custom_call_count', frappe.get_all.call_args.kwargs['fields'])
        for field in ['custom_cc_first_touched_at', 'custom_convox_call_count', 'custom_convox_last_call_time', 'custom_cc_sub_status', 'custom_cc_stage', 'custom_next_followup_date']:
            self.assertIn(field, frappe.get_all.call_args.kwargs['fields'])

    def test_manager_scope(self):
        module, frappe, _ = self.load(roles=('Sales Manager',))
        self.assertFalse(module.snapshot()['restricted_to_owner'])
        self.assertEqual(frappe.get_all.call_args.kwargs['filters'], {})

    def test_guest_and_unrelated_role_denied_before_query(self):
        for user, roles in [('Guest', ()), ('other', ('Employee',))]:
            module, frappe, _ = self.load(user, roles)
            with self.assertRaises((frappe.AuthenticationError, frappe.PermissionError)):
                module.snapshot()
            frappe.get_all.assert_not_called()

    def test_module_policy_denial_propagates(self):
        module, frappe, access = self.load()
        access.require_module.side_effect = frappe.PermissionError('Module disabled')
        with self.assertRaises(frappe.PermissionError):
            module.snapshot()
        frappe.get_all.assert_not_called()


if __name__ == '__main__':
    unittest.main()
