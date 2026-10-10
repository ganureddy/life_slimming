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
        self.assertEqual(result['today'], '2026-10-09')

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
